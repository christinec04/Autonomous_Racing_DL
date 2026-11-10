"""Races finished per training seed, one row per recipe -> results/seed_spread.png, report/figs/seed_spread.pdf.

Each dot is one training seed (20 races x 5 laps): filled = nominal, hollow = randomised. Shows how consistent each
recipe is across seeds, which is why the residual policy trained with our shield is the final controller (E29).
"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from racing.evaluate import summarize
from scripts.seed_summary import CANONICAL, GROUPS

ROWS = [("PPO, no shield", "PPO, no shield (v2 sim)"),
        ("PPO + additive APF", "PPO + additive Eq. 2/3 shield (E31)"),
        ("Residual PPO (ResRace)", "residual PPO, no shield (E31)"),
        ("PPO + slip pen. + our shield", "PPO + slip penalty + shield + recovery (E26)"),
        ("PPO + our shield", "PPO + shield + escape + stall recovery (final, v2 sim)"),
        ("Residual + our shield (final)", "residual PPO trained with shield + recovery (E23)")]
INK, MUTED, GRID = "#1f2328", "#6e7781", "#d8dee4"


def main(reduced=False):
    """reduced=True: the reduced-scope draft's version (PPO + our shield is the method, bold; residual = variant)."""
    rows = ROWS
    if reduced:
        rows = [r for r in ROWS if r[0] not in ("PPO + our shield", "Residual + our shield (final)")]
        rows += [("Residual + our shield (variant)", ROWS[-1][1]), ("PPO + our shield (ours)", ROWS[-2][1])]
    races = [r for f in CANONICAL if pathlib.Path(f).exists() for r in json.load(open(f)).get("races", [])]
    S = {rz: summarize([r for r in races if r["randomize"] == rz]) for rz in (False, True)}
    pid = S[False].get("pid_apf", {}).get("finished")
    fig, ax = plt.subplots(figsize=(3.5, 2.3))
    for y, (name, group) in enumerate(rows):
        for rz, off in ((False, 0.12), (True, -0.12)):
            xs = [S[rz][l]["finished"] for l in GROUPS[group] if l in S[rz]]
            ys = [y + off + 0.09 * xs[:i].count(x) * (1 if not rz else -1) for i, x in enumerate(xs)]  # stack ties
            ax.scatter(xs, ys, s=22, facecolors=INK if not rz else "white", edgecolors=INK,
                       linewidths=1.0, zorder=3)
    if pid is not None:
        ax.axvline(pid, color=MUTED, ls="--", lw=1)
        ax.text(pid + 0.3, len(rows) - 0.35, f"PID+APF ({pid})", color=MUTED, fontsize=6, ha="left", va="center")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([n for n, _ in rows], fontsize=7)
    ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.set_xlim(-0.5, 20.5)
    ax.set_ylim(-0.6, len(rows) - 0.15)
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("races finished / 20 (dot = training seed)", fontsize=7)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.scatter([], [], s=22, facecolors=INK, edgecolors=INK, label="nominal")
    ax.scatter([], [], s=22, facecolors="white", edgecolors=INK, label="randomised")
    ax.legend(fontsize=6.5, loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=2, frameon=False, borderaxespad=0.2)
    fig.tight_layout(pad=0.3)
    pathlib.Path("report/figs").mkdir(parents=True, exist_ok=True)
    if reduced:
        fig.savefig("report/figs/seed_spread_reduced.pdf", bbox_inches="tight")
        print("wrote report/figs/seed_spread_reduced.pdf")
        return
    fig.savefig("results/seed_spread.png", dpi=200, bbox_inches="tight")
    fig.savefig("report/figs/seed_spread.pdf", bbox_inches="tight")
    print("wrote results/seed_spread.png, report/figs/seed_spread.pdf")


if __name__ == "__main__":
    main()
