"""Learning curves for the shielded PPO runs in runs/rl.

  python tools/plot_rl.py                       every run that has a train_log.csv
  python tools/plot_rl.py wb_friction wb_none   just these, in this order
  python tools/plot_rl.py --tag=sim sim_friction sim_geometric sim_none   files get a sim_ prefix

Writes runs/rl/plots/learning_curves.png (return, lap fraction, crashes per 1k steps,
intervention rate against env steps) and runs/rl/plots/crashes_cumulative.png.
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs", "rl")
COLORS = {"friction": "#1b7837", "geometric": "#c2410c", "none": "#4d4d4d"}


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for k in rows[0] if rows else []:
        try:
            out[k] = np.array([float(r[k]) for r in rows])
        except ValueError:
            out[k] = np.array([r[k] for r in rows])
    return out


def smooth(y, w):
    if len(y) < 2:
        return y
    w = max(1, min(w, len(y)))
    c = np.cumsum(np.insert(y, 0, 0.0))
    head = c[1:w] / np.arange(1, w)
    return np.concatenate([head, (c[w:] - c[:-w]) / w])


def shield_of(run):
    for k in COLORS:
        if k in run:
            return k
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--tag=")]
    tag = next((a[6:] + "_" for a in sys.argv[1:] if a.startswith("--tag=")), "")
    runs = args or sorted(d for d in os.listdir(ROOT) if os.path.exists(os.path.join(ROOT, d, "train_log.csv")))
    out = os.path.join(ROOT, "plots")
    os.makedirs(out, exist_ok=True)
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    styles = ["-", "--", ":", "-."]
    seen = {}
    for run in runs:
        log = load(os.path.join(ROOT, run, "train_log.csv"))
        ep = load(os.path.join(ROOT, run, "episodes.csv"))
        if not log:
            continue
        kind = shield_of(run)
        n = seen.get(kind, 0)
        seen[kind] = n + 1
        style = dict(color=COLORS.get(kind), ls=styles[n % len(styles)], lw=1.6, label=run)
        k = 1000.0
        if ep:
            ax[0, 0].plot(ep["step"] / k, smooth(ep["return"], 50), **style)
            ax[0, 1].plot(ep["step"] / k, smooth(ep["laps"], 50), **style)
        ax[1, 0].plot(log["step"] / k, smooth(log["crashes"], 10), **style)
        ax[1, 1].plot(log["step"] / k, smooth(log["int_rate"], 10), **style)
        ax2.plot(log["step"] / k, np.cumsum(log["crashes"]), **style)
        if "opponents" in log and np.any(log["opponents"] > 0):
            on = log["step"][np.argmax(log["opponents"] > 0)] / k
            for a in ax.flat:
                a.axvline(on, color=style["color"], alpha=0.25, lw=1)
    titles = [("episode return (50 episode mean)", "return"), ("lap fraction per episode (50 episode mean)", "laps"),
              ("training crashes per 1k env steps (10k step mean)", "crashes / 1k steps"),
              ("shield intervention rate (fraction of steps)", "rate")]
    for a, (t, y) in zip(ax.flat, titles):
        a.set_title(t, fontsize=10)
        a.set_ylabel(y)
        a.grid(alpha=0.3)
    for a in ax[1]:
        a.set_xlabel("env steps (thousands)")
    ax[0, 0].legend(fontsize=8)
    fig.suptitle("PPO learning curves by shield (faint vertical lines mark opponents joining)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"{tag}learning_curves.png"), dpi=130)
    ax2.set_title("cumulative training crashes", fontsize=10)
    ax2.set_xlabel("env steps (thousands)")
    ax2.set_ylabel("crashes")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=8)
    fig2.tight_layout()
    fig2.savefig(os.path.join(out, f"{tag}crashes_cumulative.png"), dpi=130)
    print("wrote", os.path.join(out, f"{tag}learning_curves.png"), os.path.join(out, f"{tag}crashes_cumulative.png"))


if __name__ == "__main__":
    main()
