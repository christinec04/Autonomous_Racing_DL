"""Column-width (3.5 in) figures for the IEEE report -> report/figs/*.pdf.

python -m scripts.report_figs
"""
import csv
import json
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from racing.evaluate import summarize
from racing.sim import Centerline

OUT = pathlib.Path("report/figs"); OUT.mkdir(parents=True, exist_ok=True)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "legend.fontsize": 6.5,
                     "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "font.family": "serif",
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(color=GRID, lw=0.5)
    ax.set_axisbelow(True)


def load(files):
    return [r for f in files for r in json.load(open(f))["races"]]


# 1. safety vs speed (seed 0, nominal, 20 races)
races = [r for r in load(["results/final_v2_others.json", "results/eval_recover.json",
                          "results/eval_residual_shield_s0.json"]) if not r["randomize"]]
S = summarize(races)
SHOW = [("ppo_apf_rec@s0", "PPO + our shield"), ("ppo_residual_apf_rec@trained", "Residual PPO trained w/ our shield"),
        ("ppo_additive", "PPO + additive APF (Eq. 2-3)"), ("pid_apf", "PID + APF"),
        ("ppo_residual", "Residual PPO (ResRace-style)"), ("ppo@s0", "PPO, no shield")]
fig, ax = plt.subplots(figsize=(3.5, 2.35))
for (k, name), col in zip(SHOW, C):
    s = S[k]
    ax.scatter(s["lap_mean"], s["collisions_per_10_laps"], s=12 + 5 * s["finished"], color=col, edgecolor="white",
               lw=0.8, zorder=3, label=f"{name} ({s['finished']}/20)")
style(ax)
ax.set_xlabel("mean clean-lap time (s)  (left = faster)")
ax.set_ylabel("collisions / 10 laps")
leg = ax.legend(loc="upper right", frameon=False, handletextpad=0.3, borderaxespad=0.2, labelspacing=0.4)
for h in leg.legend_handles:  # same marker size in the legend; size on the plot encodes races finished
    h.set_sizes([30])
ax.set_ylim(-0.3, 8.2)
fig.tight_layout(pad=0.3)
fig.savefig(OUT / "tradeoff.pdf")
plt.close(fig)

# 2. cumulative crashes during training (shield removed only in the solo eval laps, not here)
GR = [("our shield (3 seeds)", ["ppo_shield_s0", "ppo_shield_s1", "ppo_shield_s2"], C[0]),
      ("no shield (3 seeds)", ["ppo_noshield_s0", "ppo_noshield_s1", "ppo_noshield_s2"], C[4]),
      ("additive APF, Eq. 2 (1 seed)", ["ppo_additive_s0"], C[1])]
fig, ax = plt.subplots(figsize=(3.5, 2.0))
for name, runs, col in GR:
    for i, r in enumerate(runs):
        rows = list(csv.DictReader(open(f"runs/{r}/train_log.csv")))
        st = np.array([float(x["step"]) for x in rows]) / 1e6
        cr = np.cumsum([float(x["crashes"]) for x in rows])
        ax.plot(st, cr, color=col, lw=1.2, label=name if i == 0 else None)
for x in (1.5, 2.5):
    ax.axvline(x, color=MUTED, lw=0.5, ls="--")
ax.text(0.75, 2900, "stage 1 (solo)", ha="center", color=MUTED, fontsize=6)
ax.text(2.0, 2900, "stage 2", ha="center", color=MUTED, fontsize=6)
ax.text(3.0, 2900, "stage 3", ha="center", color=MUTED, fontsize=6)
style(ax)
ax.set_ylim(0, 3100)
ax.set_xlabel("training steps (millions)")
ax.set_ylabel("cumulative crashes")
ax.legend(loc="lower right", frameon=False, bbox_to_anchor=(1.0, 0.14), handlelength=1.2, handletextpad=0.4,
          borderaxespad=0.1)
fig.tight_layout(pad=0.3)
fig.savefig(OUT / "training_crashes.pdf")
plt.close(fig)

# 3. where races end (3 training seeds pooled, nominal + randomised)
cl = Centerline.load(); L = cl.length
GROUPS = [("PID + APF", [("final_v2_others.json", "pid_apf")]),
          ("PPO, no shield", [("final_v2_others.json", "ppo@s0"), ("final_v2_others.json", "ppo@s1"),
                              ("final_v2_noshield_s2.json", "ppo@s2v2")]),
          ("PPO + shield, no stall recovery", [("eval_escape_v4.json", "ppo_apf_esc@s0"),
                                               ("eval_escape_v4_s1.json", "ppo_apf_esc@s1v4"),
                                               ("eval_escape_v4_s2.json", "ppo_apf_esc@s2")]),
          ("PPO + shield + stall recovery", [("eval_recover.json", "ppo_apf_rec@s0"), ("eval_recover.json", "ppo_apf_rec@s1"),
                                             ("eval_recover.json", "ppo_apf_rec@s2")])]
edges = np.arange(0, L + 10, 10.0)
fig, axes = plt.subplots(len(GROUPS), 1, figsize=(3.5, 3.3), sharex=True)
cache = {}
for ax, (name, srcs) in zip(axes, GROUPS):
    ev = {"wall": [], "car": [], "stuck": []}; n = 0
    for f, c in srcs:
        rr = cache.setdefault(f, json.load(open("results/" + f))["races"])
        for r in rr:
            if r["controller"] != c:
                continue
            n += 1
            s = (r["laps_done"] % 1.0) * L
            if r["wall"]: ev["wall"].append(s)
            elif r["car"]: ev["car"].append(s)
            elif len(r["lap_times"]) < r.get("laps_target", 5): ev["stuck"].append(s)
    bottom = np.zeros(len(edges) - 1)
    for (key, lab), col in zip([("wall", "wall crash"), ("car", "car crash"), ("stuck", "stuck")], C[:3]):
        h = np.histogram(ev[key], edges)[0]
        ax.bar(edges[:-1], h, width=9, bottom=bottom, align="edge", color=col, lw=0, label=lab)
        bottom += h
    ax.axvspan(84, 126, color=GRID, alpha=0.7, lw=0, zorder=0)
    ax.set_ylim(0, 26)
    ax.set_yticks([0, 10, 20])
    ax.set_title(f"{name}: {int(bottom.sum())} of {n} races ended early", loc="left", fontsize=6.5, color=INK,
                 pad=1.5)
    style(ax); ax.grid(False)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", frameon=False, ncol=3, fontsize=6.5, borderaxespad=0.1, handlelength=1.2,
           columnspacing=1.5)
axes[-1].set_xlabel("lap distance (m); shaded = 2.5 m-radius chicane")
axes[-1].set_xlim(0, L)
fig.tight_layout(pad=0.3, h_pad=0.2, rect=(0, 0, 1, 0.955))
fig.savefig(OUT / "failure_map.pdf")
plt.close(fig)
print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
