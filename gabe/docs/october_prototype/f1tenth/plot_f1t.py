"""Plots for the f1tenth comparison, written to runs/f1tenth.

  crash_rate.png       crash fraction per regime and aggression, one panel per platform, bars per shield
  learning_curves.png  PPO with the friction shield and without on the stp car
"""
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "runs")
OUT = os.path.join(RUNS, "f1tenth")
SHIELDS = ["none", "geometric", "friction"]
COLOR = {"none": "#2a78d6", "geometric": "#eb6834", "friction": "#1baf7a"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
PANELS = [
    ("Webots (ODE pyramid friction)", os.path.join(RUNS, "shield_test", "sweep", "results.csv")),
    ("f1tenth stp (Pacejka, friction circle)", os.path.join(OUT, "sweep_stp", "results.csv")),
    ("f1tenth st (gym linear tyres)", os.path.join(OUT, "sweep_st", "results.csv")),
    ("f1tenth stp, race pace 0.85", os.path.join(OUT, "sweep_stp_pace085", "results.csv")),
    ("f1tenth stp, friction shield retuned (brake_frac 0.5, margin 0.8)", os.path.join(OUT, "sweep_stp_tuned", "results.csv")),
]


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def crash_rates():
    panels = [(t, p) for t, p in PANELS if os.path.exists(p)]
    fig, axes = plt.subplots(len(panels), 1, figsize=(8, 2.4 * len(panels)), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (title, path) in zip(axes, panels):
        rows = list(csv.DictReader(open(path)))
        cfgs = sorted({(r["regime"], float(r["aggression"])) for r in rows}, key=lambda c: (c[0] != "road", c[1]))
        x = np.arange(len(cfgs))
        w = 0.26
        for k, sh in enumerate(SHIELDS):
            rate, n = [], []
            for reg, ag in cfgs:
                sel = [r for r in rows if r["regime"] == reg and float(r["aggression"]) == ag and r["shield"] == sh]
                n.append(len(sel))
                rate.append(np.mean([int(r["crash"]) for r in sel]) if sel else np.nan)
            ax.bar(x + (k - 1) * w, rate, w - 0.03, color=COLOR[sh], label=sh)
        ax.set_xticks(x, [f"{reg} x{ag:.2f}" for reg, ag in cfgs])
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("crash fraction", color=MUTED, fontsize=8)
        ax.set_title(title, loc="left", fontsize=9, color=INK)
        style(ax)
    axes[0].legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    fig.suptitle("Crash fraction per shield, 4 starts per bar", x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "crash_rate.png"), dpi=130)


def roll(y, k):
    if len(y) < k:
        return y
    return np.convolve(y, np.ones(k) / k, "valid")


def learning_curves():
    runs = [(sh, os.path.join(OUT, "rl", f"stp_{sh}", "train_log.csv")) for sh in ("none", "friction")]
    runs = [(sh, p) for sh, p in runs if os.path.exists(p)]
    if not runs:
        return
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for sh, path in runs:
        rows = list(csv.DictReader(open(path)))
        step = np.array([float(r["step"]) for r in rows])
        crashes = np.array([float(r["crashes"]) for r in rows])
        prog = np.array([float(r["progress"]) if float(r["episodes"]) else np.nan for r in rows])
        speed = np.array([float(r["speed"]) for r in rows])
        k = 20
        ok = ~np.isnan(prog)
        axes[0].plot(step[ok][k - 1:] if ok.sum() >= k else step[ok], roll(prog[ok], k), color=COLOR[sh], lw=2, label=sh)
        axes[1].plot(step[k - 1:], roll(crashes, k), color=COLOR[sh], lw=2, label=sh)
        axes[2].plot(step[k - 1:], roll(speed, k), color=COLOR[sh], lw=2, label=sh)
        opp = next((s for s, r in zip(step, rows) if int(r["opponents"])), None)
        for ax in axes:
            if opp:
                ax.axvline(opp, color=MUTED, lw=0.8, ls=":")
    titles = ["metres per episode", "crashes per 1000 steps", "mean speed, m/s"]
    for ax, t in zip(axes, titles):
        ax.set_title(t, loc="left", fontsize=9, color=INK)
        ax.set_xlabel("env steps (dotted line, three opponents join)", color=MUTED, fontsize=8)
        style(ax)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("PPO on f1tenth stp car, rolling mean over 20k steps", x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "learning_curves.png"), dpi=130)


if __name__ == "__main__":
    crash_rates()
    learning_curves()
