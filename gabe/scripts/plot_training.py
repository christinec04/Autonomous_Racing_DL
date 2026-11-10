"""Training curves for all runs in runs/*: crash rate, shield activity, unshielded lap time."""
import sys, glob, pathlib, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]  # validated categorical order
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

def read(p):
    with open(p) as f:
        return list(csv.DictReader(f))

def main(pattern="runs/ppo_*", out="results/training_curves.png"):
    runs = sorted(d for d in glob.glob(pattern) if pathlib.Path(d, "train_log.csv").exists())
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), facecolor=SURF)
    for ax in axes:
        ax.set_facecolor(SURF)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        for s in ("left", "bottom"): ax.spines[s].set_color(MUTED)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_xlabel("training steps (millions)", color=MUTED, fontsize=9)
        ax.set_xlim(0, 3.55)
    for k, d in enumerate(runs):
        c = SERIES[k % len(SERIES)]
        name = pathlib.Path(d).name
        tr = read(pathlib.Path(d, "train_log.csv"))
        x = np.array([float(r["step"]) for r in tr]) / 1e6
        axes[0].plot(x, [float(r["crash_rate"]) for r in tr], color=c, lw=2, label=name)
        axes[1].plot(x, [float(r["lam_freq"]) for r in tr], color=c, lw=2, label=name)
        ev = read(pathlib.Path(d, "eval_log.csv"))
        xe = np.array([float(r["step"]) for r in ev]) / 1e6
        lap = [float(r["unshielded_lap"]) if r["unshielded_clean"] == "True" else np.nan for r in ev]
        axes[2].plot(xe, lap, color=c, lw=2, marker="o", ms=4, label=name)
    axes[0].set_title("Crash rate per training episode", color=INK, fontsize=11, loc="left")
    axes[1].set_title("Share of steps the shield intervened", color=INK, fontsize=11, loc="left")
    axes[2].set_title("Solo lap time, shield removed (s)", color=INK, fontsize=11, loc="left")
    for st in (1.5, 2.5):
        for ax in axes:
            ax.axvline(st, color=GRID, lw=1, ls="--")
    for ax in axes:
        for xm, lab in ((0.75, "stage 1 solo"), (2.0, "stage 2"), (3.0, "stage 3")):
            ax.text(xm, 0.97, lab, transform=ax.get_xaxis_transform(), color=MUTED, fontsize=8, ha="center", va="top")
    axes[0].legend(frameon=False, fontsize=9, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=130, facecolor=SURF)
    print("wrote", out)

if __name__ == "__main__":
    main(*sys.argv[1:])
