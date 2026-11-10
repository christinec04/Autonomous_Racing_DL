"""g-g diagrams, E29 policies vs E37 B (trained on friction x0.65-1.15), seeds 0 and 1, both raced with the combined
shield: nominal races of the main protocol and the x0.7 stress test. Circles: the friction limit (solid) and 90% of it.
-> results/gg_e37.png
"""
import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
COLOR = {"E29": "#52514e", "E37 B": "#2a78d6"}
MG = 1.0489 * 9.81  # nominal friction x g


def races(f, pick=None):
    R = json.load(open(f"results/{f}.json"))["races"]
    keep = lambda r: ("stress" in f or not r["randomize"]) and (pick is None or pick(r))  # stress runs are randomised
    return [r for r in R if keep(r)]


E29 = lambda r: r["controller"].split("@")[1] in ("trained", "trained_s1")
SETS = {
    ("E29", 1.0): races("eval_oxmu", E29),
    ("E37 B", 1.0): races("eval_ppo_residual_oxmu_widemu_s0") + races("eval_ppo_residual_oxmu_widemu_s1"),
    ("E29", 0.7): races("stress_mu0.7_oxmu", E29),
    ("E37 B", 0.7): races("stress_mu0.7_ppo_residual_oxmu_widemu_s0") + races("stress_mu0.7_ppo_residual_oxmu_widemu_s1"),
}

fig, axes = plt.subplots(2, 2, figsize=(6.4, 6.6), facecolor=SURF, sharex=True, sharey=True)
th = np.linspace(0, 2 * np.pi, 200)
for ax, ((who, mu), R) in zip(axes.flat, SETS.items()):
    lat = np.concatenate([r["gg"][0] for r in R]) / MG
    lon = np.concatenate([r["gg"][1] for r in R]) / MG
    fin = sum(not r["dnf"] and not r["stuck"] for r in R)
    ax.set_facecolor(SURF)
    ax.scatter(lat, lon, s=2, color=COLOR[who], alpha=0.12, linewidths=0)
    ax.plot(mu * np.cos(th), mu * np.sin(th), color=INK, lw=1)
    ax.plot(0.9 * mu * np.cos(th), 0.9 * mu * np.sin(th), color=MUTED, lw=0.8, ls="--")
    frac = np.mean(np.hypot(lat, lon) > 0.9 * mu)
    ax.set_title(f"{who}, friction x{mu}\n{frac:.1%} of time > 90% grip, {fin}/{len(R)} finished",
                 fontsize=8.5, color=INK, loc="left")
    ax.set_aspect("equal"); ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2)
    ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(labelsize=7, colors=MUTED)
for ax in axes[1]:
    ax.set_xlabel("lateral acceleration / (nominal mu g)", fontsize=7.5, color=MUTED)
for ax in axes[:, 0]:
    ax.set_ylabel("longitudinal / (nominal mu g)", fontsize=7.5, color=MUTED)
fig.suptitle("E29 policies vs E37 B (wide friction training), seeds 0+1, combined shield", fontsize=9.5, color=INK, x=0.02,
             ha="left")
fig.tight_layout()
fig.savefig("results/gg_e37.png", dpi=180, facecolor=SURF)
print("results/gg_e37.png")
