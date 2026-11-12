"""Race pictures straight from F1TENTH Gym's own renderer (render_mode="rgb_array", drawn off-screen with pygame;
no window opens: SDL's dummy video driver is forced).

Races PPO + our action-conditioned shield (seed-0 policy from the race-day table) against three opponents and saves
frames chosen from the race:
  overview_*.png  whole track (renderer zoom 1.0, no follow)
  closeup_*.png   F1TENTH's follow-the-ego view (zoom 3), at moments the shield intervenes next to an opponent;
                  *_lidar.png adds the ego's LiDAR hits through F1TENTH's own render_points callback
Same race seed for every view (the simulation is deterministic), so the pictures show one race.
    python -m scripts.f1tenth_stills --out <dir> [--seed 10000] [--seconds 60]
"""
from __future__ import annotations

import os
os.environ["SDL_VIDEODRIVER"] = "dummy"  # never open a window
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import argparse
import pathlib

import numpy as np
from PIL import Image

import racing.sim as S
from f1tenth_gym.envs.rendering import renderer as R

VIEW = {}  # filled per run: window_size, zoom_in_factor, focus_on
_orig_from_yaml = R.RenderSpec.from_yaml


def _spec(f):
    spec = _orig_from_yaml(f)
    spec.window_size, spec.zoom_in_factor, spec.focus_on = VIEW["window"], VIEW["zoom"], VIEW["focus"]
    spec.show_info = False  # the mouse/keyboard help text at the top of the window
    return spec


R.RenderSpec.from_yaml = staticmethod(_spec)

# Bug fix for F1TENTH Gym 1.0.0.dev0's renderer on non-square maps: objects.Map passes (rows, cols) to cv2.resize,
# which expects (width, height) = (cols, rows), so a 1445 x 896 map is squashed into 896 x 1445 and the cars and
# LiDAR no longer line up with the drawn walls (square maps hide it). Same code with the size in the right order;
# the renderer's pixel scale (ppus) is then simply 1 / zoom (set in race()).
import cv2  # noqa: E402
import pygame  # noqa: E402
from f1tenth_gym.envs.rendering import objects as O  # noqa: E402


def _map_init(self, map_img, zoom_level):
    rows, cols = map_img.shape
    img = cv2.resize(map_img, dsize=(int(cols * zoom_level), int(rows * zoom_level)), interpolation=cv2.INTER_AREA)
    track_map = np.stack([img, img, img], axis=-1)
    track_map = np.flip(np.rot90(track_map, k=1), axis=0)  # as in the original
    self.track_map = track_map
    self.map_surface = pygame.surfarray.make_surface(self.track_map)


O.Map.__init__ = _map_init
_orig_make = S.gym.make
S.gym.make = lambda *a, **k: _orig_make(*a, render_mode="rgb_array", **k)

from racing.env import EnvConfig, RaceEnv  # noqa: E402  (after the patches)
from racing.evaluate import RECOVER, SHIELD_FOR, make_controller  # noqa: E402
from racing.shield import ShieldConfig  # noqa: E402

CTRL, MODEL = "ppo_apf_rec", "runs/ppo_shield_s0/model_stage3.zip"
FOV = 4.7


def race(seed, seconds, view, want, lidar=False):
    """Run the race; `want(step, info)` says whether to grab a frame. Returns [(t, lam, frame)]."""
    VIEW.update(view)
    cfg = EnvConfig(n_opp=3, random_start=True, shield=ShieldConfig(**SHIELD_FOR[CTRL]), episode_time=seconds,
                    seed=seed, tire="saturated_v2", recover=CTRL in RECOVER)
    env = RaceEnv(cfg)
    f1 = env.sim.unwrapped
    f1.renderer.ppus = {"map": 1 / 0.4, "car": 1 / view["zoom"]}  # matches the size fix above
    if view.get("full_res_map"):  # whole-track view at the renderer's 1:1 zoom level (its map view is fixed at 0.4x)
        f1.renderer.active_map_renderer = "car"
    if lidar:
        def draw_scan(r):
            x, y, yaw = env._states()[0][[0, 1, 4]]
            sc = env.scan
            ang = yaw + np.linspace(-FOV / 2, FOV / 2, len(sc))
            m = sc < 9.5
            pts = np.stack([x + sc[m] * np.cos(ang[m]), y + sc[m] * np.sin(ang[m])], 1)[::3]
            r.render_points(pts, color=(255, 140, 0), size=2)
        f1.add_render_callback(draw_scan)
    rng = np.random.default_rng(seed)
    opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))), opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
    obs, _ = env.reset(seed=seed, options=opts)
    act = make_controller(CTRL, env, MODEL)
    out, k = [], 0
    while True:
        obs, r, term, trunc, info = env.step(act(obs))
        if want(k, info, env):
            out.append((info["t"], float(info["lambda"]), f1.render()))
        k += 1
        if term or trunc:
            break
    return out, info


def near_opp(env):
    st = env._states()
    return float(np.hypot(*(st[1:, :2] - st[0, :2]).T).min())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=10000)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    shots, info = race(a.seed, a.seconds, dict(window=1500, zoom=1.0, focus=None, full_res_map=True), lambda k, i, e: k % 50 == 49)
    for t, lam, fr in shots:
        Image.fromarray(fr).save(out / f"overview_t{t:05.1f}.png")
    print(f"overview: {len(shots)} frames; race passes {info['passes']}")

    last = {"k": -99}

    def close(k, i, e):  # shield active next to an opponent, at most one frame per 0.4 s
        if near_opp(e) < 3.0 and k - last["k"] >= 10:
            last["k"] = k
            return True
        return False
    for lidar in (False, True):
        last["k"] = -99
        shots, _ = race(a.seed, a.seconds, dict(window=900, zoom=3.0, focus="agent_0"), close, lidar=lidar)
        kept = 0
        for t, lam, fr in shots:
            if (fr.min(axis=2) > 250).mean() > 0.97:  # the follow camera lost the car (blank frame): skip
                continue
            kept += 1
            Image.fromarray(fr).save(out / f"closeup_t{t:05.1f}_lam{lam:.2f}{'_lidar' if lidar else ''}.png")
        print(f"close-up{' + lidar' if lidar else ''}: {kept} of {len(shots)} frames kept")
