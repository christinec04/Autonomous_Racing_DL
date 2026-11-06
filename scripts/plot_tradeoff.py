"""Safety vs speed for every controller (final comparison, nominal): collisions / 10 laps vs clean-lap time."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from racing.evaluate import summarize

FILES = ["results/final_v2_others.json", "results/eval_recover.json"]
SHOW = {"ppo_apf_rec@s0": "PPO + action-conditioned shield (ours)", "ppo_additive": "PPO + additive Eq. 2/3 shield",
        "pid_apf": "PID + APF", "ppo_residual": "ResRace-style residual PPO", "ppo@s0": "PPO, no shield"}
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

races = [r for f in FILES for r in json.load(open(f))["races"] if not r["randomize"]]
S = summarize(races)
fig, ax = plt.subplots(figsize=(8.5, 5.2), facecolor=SURF)
ax.set_facecolor(SURF)
for (k, name), col in zip(SHOW.items(), COLORS):
    s = S[k]
    ax.scatter(s["lap_mean"], s["collisions_per_10_laps"], s=60 + 40 * s["finished"], color=col, edgecolor=SURF,
               linewidth=2, zorder=3, label=f"{name}: {s['finished']}/20 finished")
    ax.annotate(f"{s['finished']}/20", (s["lap_mean"], s["collisions_per_10_laps"]), textcoords="offset points",
                xytext=(14, -4), color=INK, fontsize=9)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
for sp in ("left", "bottom"): ax.spines[sp].set_color(MUTED)
ax.tick_params(colors=MUTED, labelsize=9)
ax.grid(color=GRID, lw=0.8)
ax.set_xlabel("mean clean-lap time (s)  <- faster", color=MUTED)
ax.set_ylabel("collisions per 10 laps  <- safer", color=MUTED)
ax.set_title("Safety vs speed, seed 0, 20 races x 5 laps (point size = races finished)", color=INK, loc="left", fontsize=11)
ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.14), ncol=2)
fig.tight_layout(); fig.savefig("results/tradeoff.png", dpi=130, facecolor=SURF)
print("wrote results/tradeoff.png")
