"""Render short top-down race replays to MP4.

  python -m racing.render --controller ppo_apf --model runs/ppo_shield_s0/model_stage3.zip \
      --seed 10003 --seconds 20 --out ~/Downloads/racing_videos/ppo_shield_race.mp4

Ego = blue; opponents = grey. The ego turns red on steps where the shield intervened
(lambda > 0). HUD: time, speed, lap, shield state.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.patches import Polygon
import numpy as np
from PIL import Image

from .env import EnvConfig, RaceEnv
from .evaluate import RECOVER, SHIELD_FOR, make_controller
from .shield import ShieldConfig
from .sim import MAPS_DIR, DEFAULT_PARAMS

EGO, EGO_SHIELD, OPP, INK, SURF = "#2a78d6", "#e34948", "#8a8984", "#0b0b0b", "#fcfcfb"
L, W = DEFAULT_PARAMS["length"], DEFAULT_PARAMS["width"]


def record(controller, model, seed, seconds, n_opp=3, solo=False, tire="saturated", map_name="Singapore"):
    sh = SHIELD_FOR[controller]
    cfg = EnvConfig(n_opp=0 if solo else n_opp, random_start=not solo, shield=ShieldConfig(**sh),
                    episode_time=seconds, seed=seed, residual=controller.startswith("ppo_residual"), tire=tire,
                    recover=controller in RECOVER, map_name=map_name)
    env = RaceEnv(cfg)
    rng = np.random.default_rng(seed)
    opts = dict(s_ego=3.0)
    if not solo:
        opts.update(opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, n_opp))), opp_speeds=list(rng.uniform(0.5, 0.75, n_opp)))
    obs, _ = env.reset(seed=seed, options=opts)
    act = make_controller(controller, env, model)
    frames = []
    while True:
        a = act(obs)
        obs, r, term, trunc, info = env.step(a)
        st = env._states()
        frames.append(dict(t=info["t"], poses=st[:, [0, 1, 4]].copy(), v=float(st[0, 3]), lam=info["lambda"],
                           prog=info["progress"], crash=bool(term), passes=info["passes"],
                           rec=bool(info.get("recovering", False))))
        if term or trunc:
            break
    return env, frames


def car_poly(x, y, yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    pts = np.array([[L / 2, W / 2], [L / 2, -W / 2], [-L / 2, -W / 2], [-L / 2, W / 2]])
    return pts @ np.array([[c, s], [-s, c]]) + [x, y]


def render(env, frames, out, title, follow=True, fps=25, view=14.0):
    name = env.cfg.map_name
    spec = (MAPS_DIR / name / f"{name}_map.yaml").read_text().splitlines()
    res = float([l for l in spec if l.startswith("resolution")][0].split(":")[1])
    ox, oy = [float(v) for v in [l for l in spec if l.startswith("origin")][0].split("[")[1].split(",")[:2]]
    img = np.array(Image.open(MAPS_DIR / name / f"{name}_map.png"))
    h, w = img.shape
    extent = [ox, ox + w * res, oy, oy + h * res]
    fig, ax = plt.subplots(figsize=(7.2, 7.2) if follow else (10, 6.4), dpi=110, facecolor=SURF)
    ax.set_facecolor("#2b2b2b")
    ax.imshow(np.where(img > 128, 235, 43), cmap="gray", vmin=0, vmax=255, extent=extent, origin="upper")
    ax.plot(env.cl.xy[:, 0], env.cl.xy[:, 1], color="#c3c2b7", lw=0.6, ls=(0, (4, 4)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    trail, = ax.plot([], [], color=EGO, lw=1.5, alpha=0.6)
    cars = [Polygon(car_poly(0, 0, 0), closed=True, fc=EGO if i == 0 else OPP, ec=INK, lw=0.6, zorder=5)
            for i in range(len(frames[0]["poses"]))]
    for c in cars:
        ax.add_patch(c)
    hud = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", ha="left", fontsize=10, color=INK,
                  family="monospace", bbox=dict(fc=SURF, ec="none", alpha=0.9, pad=4))
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    xs, ys = [], []

    def update(k):
        f = frames[k]
        for i, c in enumerate(cars):
            c.set_xy(car_poly(*f["poses"][i]))
        cars[0].set_facecolor(EGO_SHIELD if f["lam"] > 0 else EGO)
        xs.append(f["poses"][0, 0]); ys.append(f["poses"][0, 1])
        trail.set_data(xs[-150:], ys[-150:])
        if follow:
            x, y = f["poses"][0, :2]
            ax.set_xlim(x - view, x + view); ax.set_ylim(y - view, y + view)
        lap = int(f["prog"] // env.cl.length) + 1
        shield = "INTERVENING" if f["lam"] > 0 else "-"
        if f.get("rec"):
            shield += "  (stall recovery)"
        hud.set_text(f"t {f['t']:5.1f} s   lap {lap}\nspeed {f['v']:4.1f} m/s\nshield {shield}"
                     + ("\nCRASH" if f["crash"] else ""))
        return cars + [trail, hud]

    if not follow:
        ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal")
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.93)
    anim = animation.FuncAnimation(fig, update, frames=len(frames), blit=False)
    out = pathlib.Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    # write to a temp file, then move into place only when complete (a half-written mp4 will not play)
    tmp = pathlib.Path(tempfile.gettempdir()) / ("render_" + out.name)
    writer = animation.FFMpegWriter(fps=fps, codec="libx264", bitrate=1200,
                                    extra_args=["-pix_fmt", "yuv420p", "-profile:v", "main", "-movflags", "+faststart"])
    anim.save(str(tmp), writer=writer)
    plt.close(fig)
    # verify it decodes before publishing
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(tmp)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"rendered video failed to decode: {r.stderr}")
    shutil.move(str(tmp), str(out))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--controller", required=True)
    ap.add_argument("--model")
    ap.add_argument("--seed", type=int, default=10003)
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--solo", action="store_true")
    ap.add_argument("--overview", action="store_true", help="whole track instead of a follow camera")
    ap.add_argument("--title", default="")
    ap.add_argument("--map", default="Singapore")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    env, frames = record(a.controller, a.model, a.seed, a.seconds, solo=a.solo, map_name=a.map)
    p = render(env, frames, a.out, a.title or a.controller, follow=not a.overview)
    print(f"wrote {p}  ({len(frames)} frames, crash={frames[-1]['crash']}, distance={frames[-1]['prog']:.0f} m)")
