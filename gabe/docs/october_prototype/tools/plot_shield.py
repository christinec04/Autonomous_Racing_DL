"""Figures for the shield experiment from runs/shield_test/results.csv and traj/*.npz.

  python tools/plot_shield.py [run dir, default runs/shield_test/sweep]
writes crash_rate.png, lap_time.png, grip_used.png, failure_corner.png and table.md into the run dir.
"""
import csv
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "controllers", "racelib"))
from track import HALF, Track  # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "runs", "shield_test", "sweep")
SHIELDS = ["none", "geometric", "friction"]
COLOR = {"none": "#8c8c8c", "geometric": "#d1495b", "friction": "#2e86ab"}
LABEL = {"none": "no shield", "geometric": "geometric APF", "friction": "friction aware"}

rows = list(csv.DictReader(open(os.path.join(RUN, "results.csv"))))
regimes = [r for r in ("road", "race") if any(x["regime"] == r for x in rows)]


def pick(**kw):
    return [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]


def aggrs(regime):
    return sorted({float(r["aggression"]) for r in pick(regime=regime)})


# crash rate versus aggression
fig, axes = plt.subplots(1, len(regimes), figsize=(5.2 * len(regimes), 3.8), squeeze=False)
for ax, regime in zip(axes[0], regimes):
    xs = aggrs(regime)
    width = 0.8 * (xs[1] - xs[0] if len(xs) > 1 else 0.1) / 3
    for k, sh in enumerate(SHIELDS):
        rate, n = [], []
        for a in xs:
            ep = [r for r in pick(regime=regime, shield=sh) if abs(float(r["aggression"]) - a) < 1e-6]
            rate.append(np.mean([int(r["crash"]) for r in ep]) if ep else np.nan)
            n.append(len(ep))
        ax.bar(np.array(xs) + (k - 1) * width, rate, width, color=COLOR[sh], label=LABEL[sh])
    pace = pick(regime=regime)[0]["pace"]
    ax.set_title(f"{regime} regime, pace {float(pace):.2f}")
    ax.set_xlabel("driver aggression (target speed scale)")
    ax.set_ylabel("crash rate per episode")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(xs)
    ax.grid(axis="y", alpha=0.3)
axes[0][0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(RUN, "crash_rate.png"), dpi=150)

# time to finish the episode distance for clean runs
fig, axes = plt.subplots(1, len(regimes), figsize=(5.2 * len(regimes), 3.8), squeeze=False)
for ax, regime in zip(axes[0], regimes):
    for sh in SHIELDS:
        xs, ys = [], []
        for a in aggrs(regime):
            ok = [float(r["time"]) for r in pick(regime=regime, shield=sh, outcome="ok")
                  if abs(float(r["aggression"]) - a) < 1e-6]
            if ok:
                xs.append(a)
                ys.append(np.mean(ok))
        ax.plot(xs, ys, "o-", color=COLOR[sh], label=LABEL[sh])
    dist = float(pick(regime=regime)[0]["distance"]) if pick(regime=regime, outcome="ok") else 0
    ax.set_title(f"{regime} regime, clean episodes only")
    ax.set_xlabel("driver aggression")
    ax.set_ylabel(f"time for the episode distance (s)")
    ax.grid(alpha=0.3)
axes[0][0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(RUN, "lap_time.png"), dpi=150)

# distribution of commanded and measured friction circle use
fig, axes = plt.subplots(2, len(regimes), figsize=(5.2 * len(regimes), 6.4), squeeze=False)
edges = np.linspace(0, 2, 41)
for col, regime in enumerate(regimes):
    for row, key in enumerate(("hist_cmd", "hist_meas")):
        ax = axes[row][col]
        for sh in SHIELDS:
            h = np.sum([json.loads(r[key]) for r in pick(regime=regime, shield=sh)], axis=0)
            if np.sum(h) == 0:
                continue
            ax.step(edges[:-1], h / np.sum(h), where="post", color=COLOR[sh], label=LABEL[sh])
        ax.axvline(1.0, color="k", lw=0.8, ls="--")
        ax.set_xlim(0, 2)
        ax.set_yscale("log")
        what = "commanded |a| / grip(v)" if key == "hist_cmd" else "measured |a| / grip(v)"
        ax.set_xlabel(what)
        ax.set_ylabel("fraction of steps")
        ax.set_title(f"{regime} regime")
        ax.grid(alpha=0.3)
axes[0][0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(RUN, "grip_used.png"), dpi=150)


# one geometric failure next to the friction shield on the same configuration
def load(name):
    d = np.load(os.path.join(RUN, "traj", name + ".npz"))
    return {c: d["traj"][:, k] for k, c in enumerate(d["cols"])}


fails = [r for r in pick(regime="race", shield="geometric") if r["crash"] == "1"]
pair = None
# prefer a grip failure (barrier or spin) over a car contact, which can be a passing artefact of the scripted driver
for r in sorted(fails, key=lambda r: (r["outcome"] == "car", float(r["aggression"]))):
    twin = [q for q in pick(regime="race", shield="friction", s0=r["s0"])
            if abs(float(q["aggression"]) - float(r["aggression"])) < 1e-6]
    if twin and twin[0]["crash"] == "0":
        pair = (r, twin[0])
        break
if pair:
    g, f = pair
    tag = f'a{float(g["aggression"]):.2f}_s{int(float(g["s0"]))}'
    tg, tf = load(f"race_geometric_{tag}"), load(f"race_friction_{tag}")
    t = Track()
    s_end = tg["s"][-1]
    fig = plt.figure(figsize=(11, 6.5))
    ax = fig.add_subplot(1, 2, 1)
    i0 = t.at(s_end - 160)
    idx = (i0 + np.arange(110)) % t.n
    for side in (-1, 1):
        edge = t.center[idx] + t.nrm[idx] * side * HALF
        ax.plot(edge[:, 0], edge[:, 1], "k", lw=1.5)
    ax.plot(t.line[idx, 0], t.line[idx, 1], color="0.7", ls="--", lw=1, label="racing line")

    def window(tr):
        ds = (tr["s"] - (s_end - 160) + t.length / 2) % t.length - t.length / 2
        return (ds > 0) & (ds < 220)

    for tr, sh in ((tg, "geometric"), (tf, "friction")):
        m = window(tr)
        ax.plot(tr["x"][m], tr["y"][m], color=COLOR[sh], lw=2, label=LABEL[sh])
        iv = m & (tr["intervened"] > 0.5)
        ax.scatter(tr["x"][iv], tr["y"][iv], s=6, color=COLOR[sh], alpha=0.5)
    ax.plot(tg["x"][-1], tg["y"][-1], "x", color=COLOR["geometric"], ms=12, mew=3)
    ax.set_aspect("equal")
    ax.set_title(f'same corner, aggression {float(g["aggression"]):.2f}, geometric ends in {g["outcome"]}')
    ax.legend(frameon=False, fontsize=8, loc="best")
    for k, (key, lab) in enumerate((("v", "speed (m/s)"), ("grip_cmd", "commanded |a| / grip"),
                                    ("steer", "steer command"), ("brake", "brake command"))):
        a2 = fig.add_subplot(4, 2, 2 * k + 2)
        for tr, sh in ((tg, "geometric"), (tf, "friction")):
            m = window(tr)
            a2.plot(tr["s"][m], tr[key][m], color=COLOR[sh], lw=1.2)
        if key == "grip_cmd":
            a2.axhline(1.0, color="k", lw=0.8, ls="--")
        a2.set_ylabel(lab, fontsize=8)
        a2.grid(alpha=0.3)
    a2.set_xlabel("arc length s (m)")
    fig.tight_layout()
    fig.savefig(os.path.join(RUN, "failure_corner.png"), dpi=150)
else:
    print("no geometric failure with a clean friction twin, skipped failure_corner.png")

# results table and crash list for the report
lines = ["| regime | shield | aggression | episodes | crashes | mean time clean (s) | intervention | grip cmd p95 | grip meas p95 |",
         "|---|---|---|---|---|---|---|---|---|"]
for regime in regimes:
    for sh in SHIELDS:
        for a in aggrs(regime):
            ep = [r for r in pick(regime=regime, shield=sh) if abs(float(r["aggression"]) - a) < 1e-6]
            if not ep:
                continue
            ok = [float(r["time"]) for r in ep if r["outcome"] == "ok"]
            clean = f"{np.mean(ok):.1f}" if ok else "n/a"
            mean = {k: np.mean([float(r[k]) for r in ep]) for k in ("intervention_rate", "grip_cmd_p95", "grip_meas_p95")}
            lines.append(f"| {regime} | {sh} | {a:.2f} | {len(ep)} | {sum(int(r['crash']) for r in ep)} | {clean} | "
                         f"{mean['intervention_rate']:.3f} | {mean['grip_cmd_p95']:.2f} | {mean['grip_meas_p95']:.2f} |")
lines += ["", "| regime | shield | aggression | s0 | outcome | crash s | heading deg | mean speed m/s |",
          "|---|---|---|---|---|---|---|---|"]
for r in rows:
    if r["outcome"] != "ok":
        lines.append(f"| {r['regime']} | {r['shield']} | {r['aggression']} | {r['s0']} | {r['outcome']} | "
                     f"{r.get('crash_s', '')} | {r.get('crash_heading_deg', '')} | {r['mean_speed']} |")
with open(os.path.join(RUN, "table.md"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
print("figures in", os.path.abspath(RUN))
