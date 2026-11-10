"""g-g diagrams (lateral vs longitudinal acceleration) per controller, nominal races, with the friction circle."""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scripts.analyze import NAMES

INK, MUTED, GRID, SURF, DOT = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6"
MG = 1.0489 * 9.81


def main(files, out="results/gg_diagrams.png"):
    races = [r for f in files for r in json.load(open(f))["races"] if not r["randomize"]]
    order = [c for c in ["ppo_apf", "ppo", "ppo_apf@noshieldtrained_withshield", "pid_apf", "ppo_residual", "pure_pursuit"]
             if any(r["controller"] == c for r in races)]
    fig, axes = plt.subplots(1, len(order), figsize=(3.3 * len(order), 3.8), facecolor=SURF, sharex=True, sharey=True)
    th = np.linspace(0, 2 * np.pi, 200)
    for ax, c in zip(np.atleast_1d(axes), order):
        lat = np.concatenate([r["gg"][0] for r in races if r["controller"] == c])
        lon = np.concatenate([r["gg"][1] for r in races if r["controller"] == c])
        ax.set_facecolor(SURF)
        ax.scatter(lat / MG, lon / MG, s=2, color=DOT, alpha=0.15, linewidths=0)
        ax.plot(np.cos(th), np.sin(th), color=INK, lw=1)
        ax.plot(0.9 * np.cos(th), 0.9 * np.sin(th), color=MUTED, lw=0.8, ls="--")
        frac = np.mean(np.hypot(lat, lon) / MG > 0.9)
        ax.set_title(f"{NAMES.get(c, c)}\n{frac:.0%} of time > 90% grip", fontsize=9, color=INK, loc="left")
        ax.set_aspect("equal"); ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3)
        ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
        for s in ax.spines.values(): s.set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.set_xlabel("lateral / mu g", color=MUTED, fontsize=8)
    np.atleast_1d(axes)[0].set_ylabel("longitudinal / mu g", color=MUTED, fontsize=8)
    fig.suptitle("g-g diagrams, nominal races (solid = friction limit, dashed = 90%)", x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=130, facecolor=SURF)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1:])
