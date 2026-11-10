"""Analysis of the jobs that finished on Nov 8 (lanes P, S, M, Q): E34b relaxed opponent check, E35 online friction
estimate, E33 remaining stress tests, residual baseline seed 2. Prints and writes results/analysis/2026-11-09.md.
"""
import json
import pathlib

import numpy as np
from scipy.stats import fisher_exact

OUT = pathlib.Path("results/analysis/2026-11-09.md")
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def fin(r):
    return not r["dnf"] and not r["stuck"]


def load(*fs):
    return [r for f in fs for r in json.load(open(f))["races"]]


def counts(R, rz):
    X = list({(r["controller"], r["seed"]): r for r in R if r["randomize"] == rz}.values())
    laps = [t for r in X for t in r["lap_times"][1:]]
    return dict(n=len(X), fin=sum(map(fin, X)), wall=sum(r["wall"] for r in X), car=sum(r["car"] for r in X),
                stuck=sum(r["stuck"] for r in X), lap=np.mean(laps) if laps else float("nan"),
                passes=np.mean([r["overtake_successes"] for r in X]),
                slip=np.mean([r["slip_above_15"] for r in X]), shield=np.mean([r["shield_freq"] for r in X]))


def row(tag, R):
    for rz in (False, True):
        c = counts(R, rz)
        if c["n"]:
            say(f"| {tag} | {'randomised' if rz else 'nominal'} | {c['fin']}/{c['n']} | {c['wall']} | {c['car']} | "
                f"{c['stuck']} | {c['lap']:.2f} | {c['passes']:.2f} | {c['shield']:.3f} | {c['slip']:.3f} |")


def p(a, na, b, nb):
    return fisher_exact([[a, na - a], [b, nb - b]])[1]


HDR = "| controller | condition | finished | wall | car | stuck | lap s | passes | shield | slip>15 |\n|---|---|---|---|---|---|---|---|---|---|"

say("# Analysis 2026-11-09 (jobs finished Nov 8)")
say()
say("## E34b relaxed two-hypothesis opponent check, final controller, 3 seeds x 50 races")
base = [r for r in load("results/eval_residual_shield_s0.json", "results/eval_extra30_residual.json",
                        "results/eval_residual_shield_s1.json", "results/eval_residual_shield_s2.json",
                        "results/eval_extra30_residual_s12.json")
        if r["controller"].startswith("ppo_residual_apf_rec@trained")]
ob = load(*[f"results/eval_oppboth_s{s}.json" for s in range(3)])
ox = load(*[f"results/eval_opprelax_s{s}.json" for s in range(3)])
say(HDR)
row("original shield (E29)", base)
row("both hypotheses (E34)", ob)
row("both, relaxed fallback (E34b)", ox)
for s in range(3):
    row(f"relaxed, seed {s}", load(f"results/eval_opprelax_s{s}.json"))
say()
tot = lambda R, k: sum(counts(R, rz)[k] for rz in (False, True))
for name, R in (("both", ob), ("relaxed", ox)):
    say(f"- {name} vs original, pooled 300 races: finished {tot(base,'fin')} -> {tot(R,'fin')} "
        f"(p = {p(tot(base,'fin'),300,tot(R,'fin'),300):.3g}), car {tot(base,'car')} -> {tot(R,'car')} "
        f"(p = {p(tot(base,'car'),300,tot(R,'car'),300):.2g}), wall {tot(base,'wall')} -> {tot(R,'wall')} "
        f"(p = {p(tot(base,'wall'),300,tot(R,'wall'),300):.2g})")
say(f"- relaxed vs both: finished {tot(ob,'fin')} -> {tot(ox,'fin')} (p = {p(tot(ob,'fin'),300,tot(ox,'fin'),300):.3g}), "
    f"wall {tot(ob,'wall')} -> {tot(ox,'wall')} (p = {p(tot(ob,'wall'),300,tot(ox,'wall'),300):.2g})")
say()

say("## E35 online friction estimate vs nominal model vs true friction (final controller, 3 seeds x 20 races)")
say("| friction | shield model | finished | per seed | slip>15 | estimate at race end (mean) |")
say("|---|---|---|---|---|---|")
for mu in ("0.8", "0.7"):
    for tag, f in (("nominal", f"results/stress_mu{mu}.json"), ("true (oracle)", f"results/stress_mu{mu}_oracle.json"),
                   ("estimated", f"results/stress_mu{mu}_muest.json")):
        R = [r for r in load(f) if "residual_apf_rec" in r["controller"]]
        per = [sum(fin(r) for r in R if r["controller"] == c) for c in sorted({r["controller"] for r in R})]
        est = f"{np.mean([r['mu_hat'][-1] for r in R]):.3f}" if "mu_hat" in R[0] else "-"
        say(f"| x{mu} | {tag} | {sum(per)}/{len(R)} | {per} | {np.mean([r['slip_above_15'] for r in R]):.3f} | {est} |")
say()
say("Main protocol, 20 races per seed (does the estimate cost anything in normal conditions?)")
say(HDR)
row("original shield, first 20 seeds", [r for r in base if r["seed"] < 10020])
m = load("results/eval_muest.json")
row("with friction estimate", m)
for rz in (False, True):
    e = np.array([(r["mu_hat"][-1], r["mu_true"]) for r in m if r["randomize"] == rz])
    say(f"- {'randomised' if rz else 'nominal'}: estimate at race end {e[:,0].mean():.3f} (min {e[:,0].min():.3f}), "
        f"true {e[:,1].mean():.3f}, mean error {np.mean(e[:,0]-e[:,1]):+.3f}")
say()

say("## E33 remaining stress tests (20 races each)")
for f in ("stress_opp5", "stress_opp1", "stress_mu0.6", "stress_mu1.3"):
    path = pathlib.Path(f"results/{f}.json")
    if not path.exists():
        say(f"- {f}: missing")
        continue
    say(f"### {f}")
    say(HDR)
    R = load(path)
    for c in sorted({r["controller"] for r in R}):
        row(c, [r for r in R if r["controller"] == c])
    say()

say("## Residual baseline (no shield) seed 2")
say(HDR)
for mp in ("Singapore", "Track2"):
    for s in range(3):
        f = pathlib.Path(f"results/eval_ppo_residual_s{s}_{mp}.json")
        if f.exists():
            row(f"{mp} seed {s}", load(f))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
