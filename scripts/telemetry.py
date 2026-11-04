"""Solo flying-lap telemetry: speed vs track distance and sector times per controller."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from racing.render import record
from scripts.analyze import NAMES

CTRLS = [("ppo_apf", "runs/ppo_shield_s0/model_stage3.zip"), ("ppo", "runs/ppo_noshield_s0/model_stage3.zip"),
         ("ppo_residual", "runs/ppo_residual_s0/model_stage3.zip"), ("pid_apf", None), ("pure_pursuit", None)]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SECTORS = [0, 34, 58, 95, 120, 150, 199]  # m along the centerline: straight, chicane, back straight, 90s, hairpin, bay


def main():
    fig, ax = plt.subplots(figsize=(12, 4.6), facecolor=SURF)
    ax.set_facecolor(SURF)
    rows = []
    for (c, m), col in zip(CTRLS, COLORS):
        env, fr = record(c, m, 0, 80.0, solo=True)
        L = env.cl.length
        prog = np.array([f["prog"] for f in fr]); v = np.array([f["v"] for f in fr]); t = np.array([f["t"] for f in fr])
        lap2 = (prog >= L) & (prog < 2 * L)  # flying lap
        if lap2.sum() < 10:
            rows.append((c, None, [None] * (len(SECTORS) - 1), fr[-1]["crash"]))
            continue
        s = prog[lap2] - L
        ax.plot(s, v[lap2], color=col, lw=2, label=NAMES.get(c, c))
        st = [np.interp(L + b, prog, t) for b in SECTORS]
        rows.append((c, st[-1] - st[0], list(np.diff(st)), False))
    for b in SECTORS[1:-1]:
        ax.axvline(b, color=GRID, lw=1)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_xlabel("distance along the lap (m)", color=MUTED); ax.set_ylabel("speed (m/s)", color=MUTED)
    ax.set_title("Solo flying lap: speed trace (vertical lines = sector boundaries)", color=INK, loc="left")
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper left", bbox_to_anchor=(0, -0.13))
    fig.tight_layout(); fig.savefig("results/telemetry_speed.png", dpi=130, facecolor=SURF)
    names = ["S1 straight", "S2 chicane", "S3 back straight", "S4 90s", "S5 hairpin", "S6 bay"]
    out = ["| controller | lap (s) | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for c, lap, secs, crashed in rows:
        out.append(f"| {NAMES.get(c, c)} | {'crash' if lap is None else f'{lap:.2f}'} | " +
                   " | ".join("-" if x is None else f"{x:.2f}" for x in secs) + " |")
    open("results/telemetry_sectors.md", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
