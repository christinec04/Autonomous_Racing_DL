"""Where on the lap do races end? Race-ending events (wall crash, car crash, stuck) by lap distance.

Pools nominal + randomised races and the training seeds of each controller from the final-comparison files
(v2 simulator). Output: results/failure_map.png and a text summary on stdout.
"""
import json
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from racing.sim import Centerline

R = pathlib.Path("results")
GROUPS = [  # (name, [(file, controller label), ...])
    ("Pure Pursuit", [("final_v2_others.json", "pure_pursuit")]),
    ("PID+APF", [("final_v2_others.json", "pid_apf")]),
    ("Residual PPO (ResRace-style)", [("final_v2_others.json", "ppo_residual")]),
    ("PPO, no shield (3 seeds)", [("final_v2_others.json", "ppo@s0"), ("final_v2_others.json", "ppo@s1"),
                                  ("final_v2_noshield_s2.json", "ppo@s2v2")]),
    ("PPO + additive shield", [("final_v2_others.json", "ppo_additive")]),
    ("PPO + our shield (3 seeds)", [("eval_escape_v4.json", "ppo_apf_esc@s0"), ("eval_escape_v4_s1.json", "ppo_apf_esc@s1v4"),
                                    ("eval_escape_v4_s2.json", "ppo_apf_esc@s2")]),
    ("PPO + our shield + stall recovery (3 seeds)", [("eval_recover.json", "ppo_apf_rec@s0"), ("eval_recover.json", "ppo_apf_rec@s1"),
                                                      ("eval_recover.json", "ppo_apf_rec@s2")]),
]
KINDS = [("wall", "wall crash", "#2a78d6"), ("car", "car crash", "#eb6834"), ("stuck", "stuck", "#1baf7a")]
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BIN = 10.0
CHICANE = (84.0, 126.0)

cl = Centerline.load()
L = cl.length
cache = {}


def races(f):
    if f not in cache:
        p = R / f
        cache[f] = json.load(open(p))["races"] if p.exists() else None
    return cache[f]


rows = []
for name, srcs in GROUPS:
    ev, n = {k: [] for k, _, _ in KINDS}, 0
    ok = True
    for f, c in srcs:
        rr = races(f)
        if rr is None:
            ok = False; break
        sel = [r for r in rr if r["controller"] == c]
        if not sel:
            ok = False; break
        n += len(sel)
        for r in sel:
            s = (r["laps_done"] % 1.0) * L
            if r["wall"]:
                ev["wall"].append(s)
            elif r["car"]:
                ev["car"].append(s)
            elif len(r["lap_times"]) < r.get("laps_target", 5):
                ev["stuck"].append(s)
    if ok:
        rows.append((name, ev, n))

edges = np.arange(0, L + BIN, BIN)
ymax = max(max(sum(np.histogram(ev[k], edges)[0] for k, _, _ in KINDS)) for _, ev, _ in rows)

fig, axes = plt.subplots(len(rows) + 1, 1, figsize=(9, 1.25 * len(rows) + 1.6), sharex=True, facecolor=SURF,
                         gridspec_kw=dict(height_ratios=[0.8] + [1] * len(rows), hspace=0.35))
k = np.abs(np.convolve(cl.curvature, np.ones(9) / 9, mode="same"))
ax = axes[0]
ax.fill_between(cl.s, 0, k, color=MUTED, lw=0, alpha=0.5)
ax.set_ylabel("|curvature|\n(1/m)", color=MUTED, fontsize=8, rotation=0, ha="right", va="center")
ax.set_title("Where races end, by lap distance (20 races x 5 laps x nominal + randomised, per seed)", color=INK,
             fontsize=10, loc="left")
print(f"{'controller':45s} races  ends  in chicane {CHICANE[0]:.0f}-{CHICANE[1]:.0f} m")
for ax, (name, ev, n) in zip(axes[1:], rows):
    bottom = np.zeros(len(edges) - 1)
    for key, lab, col in KINDS:
        h = np.histogram(ev[key], edges)[0]
        ax.bar(edges[:-1], h, width=BIN - 1.0, bottom=bottom, align="edge", color=col, edgecolor=SURF, lw=0,
               label=lab)
        bottom += h
    tot = int(bottom.sum())
    inch = sum(int(np.sum((np.array(ev[kk]) >= CHICANE[0]) & (np.array(ev[kk]) < CHICANE[1]))) for kk in ev)
    print(f"{name:45s} {n:5d} {tot:5d}  {inch:3d} ({inch / max(tot, 1):.0%})")
    ax.set_ylim(0, ymax * 1.1)
    ax.text(0.005, 0.95, f"{name}: {tot} of {n} races ended early", transform=ax.transAxes, color=INK, fontsize=8.5,
            va="top")
for ax in axes:
    ax.set_facecolor(SURF)
    ax.axvspan(*CHICANE, color=GRID, alpha=0.6, lw=0, zorder=0)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
axes[0].text(np.mean(CHICANE), axes[0].get_ylim()[1] * 0.85, "chicane", ha="center", color=INK, fontsize=8)
axes[1].legend(loc="upper right", fontsize=8, frameon=False, ncol=3, labelcolor=INK)
axes[-1].set_xlabel("lap distance (m)", color=MUTED)
axes[-1].set_xlim(0, L)
fig.savefig(R / "failure_map.png", dpi=130, bbox_inches="tight", facecolor=SURF)
print("wrote results/failure_map.png")
