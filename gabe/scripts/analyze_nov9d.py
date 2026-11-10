"""E37 with three seeds (lane Y added seed 2): E29 policies vs E37 A (retrained with the combined shield, usual friction
range) vs E37 B (retrained with it on x0.65-1.15), all raced with the combined shield. Writes
results/analysis/2026-11-09d.md.
"""
import json
import pathlib

import numpy as np
from scipy.stats import fisher_exact

lines = []
fin = lambda r: not r["dnf"] and not r["stuck"]
load = lambda f: json.load(open(f"results/{f}.json"))["races"]


def say(s=""):
    print(s)
    lines.append(s)


def group(kind):
    out = {}
    for st, f in (("main (50 seeds x nom+rand)", "eval"), ("x0.8", "stress_mu0.8"), ("x0.7", "stress_mu0.7")):
        out[st] = load(f + "_oxmu") if kind == "E29" else [r for s in range(3) for r in load(f"{f}_ppo_residual_{kind}_s{s}")]
    return out


G = {"E29 (old shield in training)": group("E29"), "E37 A (x0.85-1.15)": group("oxmu"),
     "E37 B (x0.65-1.15)": group("oxmu_widemu")}
say("# Analysis 2026-11-09d: E37 with three seeds")
say()
say("| policies (3 seeds) | setting | finished | per seed | car | wall | lap s | passes | shield | >90% grip |")
say("|---|---|---|---|---|---|---|---|---|---|")
for k, g in G.items():
    for st, R in g.items():
        laps = [t for r in R for t in r["lap_times"][1:]]
        ctrls = sorted({r["controller"] for r in R}) if "E29" in k else None
        per = ([sum(map(fin, [r for r in R if r["controller"] == c])) for c in ctrls] if ctrls else
               [sum(map(fin, R[i * len(R) // 3:(i + 1) * len(R) // 3])) for i in range(3)])
        say(f"| {k} | {st} | {sum(map(fin, R))}/{len(R)} | {per} | {sum(r['car'] for r in R)} | {sum(r['wall'] for r in R)} | "
            f"{np.mean(laps):.2f} | {np.mean([r['overtake_successes'] for r in R]):.2f} | "
            f"{np.mean([r['shield_freq'] for r in R]):.3f} | {np.mean([r['grip_above_90'] for r in R]):.3f} |")
say()
base = list(G)[0]
for k in list(G)[1:]:
    for st in G[base]:
        a, b = sum(map(fin, G[base][st])), sum(map(fin, G[k][st]))
        n = len(G[base][st])
        say(f"- {k} vs E29, {st}: {a} -> {b} of {n}, Fisher p = {fisher_exact([[a, n - a], [b, n - b]])[1]:.2g}")
pathlib.Path("results/analysis/2026-11-09d.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
