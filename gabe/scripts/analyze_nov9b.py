"""Analysis of the jobs that finished on Nov 9 midday (lanes T, U): five opponents after the counter fix, E35b
smoother estimate on the main protocol, E36 combined shield at x0.7. Writes results/analysis/2026-11-09b.md.
"""
import json
import pathlib

import numpy as np

OUT = pathlib.Path("results/analysis/2026-11-09b.md")
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def fin(r):
    return not r["dnf"] and not r["stuck"]


def load(*fs):
    return [r for f in fs for r in json.load(open(f))["races"]]


def stats(X):
    laps = [t for r in X for t in r["lap_times"][1:]]
    return f"{sum(map(fin, X))}/{len(X)} | {sum(r['car'] for r in X)} | {sum(r['wall'] for r in X)} | {np.mean(laps):.2f}"


say("# Analysis 2026-11-09b (lanes T and U, finished at midday)")
say()
say("## E33 five opponents after the overtake-counter fix")
a, b = load("results/stress_opp5.json"), load("results/stress_opp5_v2.json")
key = lambda r: (r["controller"], r["seed"], r["randomize"], r["dnf"], r["stuck"], r["car"], r["wall"])
say(f"- finishes, contacts and wall hits identical race by race to the original file: {sorted(map(key, a)) == sorted(map(key, b))}")
say(f"- passes per race, final controller: {np.mean([r['overtake_successes'] for r in a if 'residual' in r['controller']]):.2f}"
    f" (old counter) -> {np.mean([r['overtake_successes'] for r in b if 'residual' in r['controller']]):.2f}")
say()

say("## Main protocol, same 20 race seeds, final controller 3 seeds")
say("| shield | condition | finished | car | wall | lap s |")
say("|---|---|---|---|---|---|")
seeds = {r["seed"] for r in load("results/eval_mu2.json")}
sets = {
    "original (E29)": [r for s in range(3) for r in load(f"results/eval_residual_shield_s{s}.json")
                       if r["controller"].startswith("ppo_residual_apf_rec@")],
    "friction estimate (E35)": load("results/eval_muest.json"),
    "smoother estimate (E35b)": load("results/eval_mu2.json"),
    "relaxed check + estimate (E36)": load("results/eval_oxmu.json"),
}
for name, R in sets.items():
    for rz in (False, True):
        X = [r for r in R if r["seed"] in seeds and r["randomize"] == rz]
        say(f"| {name} | {'randomised' if rz else 'nominal'} | {stats(X)} |")
say()

say("## Friction x0.7, final controller 3 seeds x 20 races")
say("| shield | finished | car | wall | lap s | per seed |")
say("|---|---|---|---|---|---|")
for name, f in (("nominal model", "stress_mu0.7"), ("true friction (oracle)", "stress_mu0.7_oracle"),
                ("estimate (E35)", "stress_mu0.7_muest"), ("smoother estimate (E35b)", "stress_mu0.7_mu2"),
                ("relaxed check + estimate (E36)", "stress_mu0.7_oxmu")):
    R = [r for r in load(f"results/{f}.json") if "residual" in r["controller"]]
    per = [sum(map(fin, [r for r in R if r["controller"].split("@")[1] == c])) for c in ("trained", "trained_s1", "trained_s2")]
    say(f"| {name} | {stats(R)} | {per} |")
say()

say("## Why E36 hits walls at x0.7: the estimate drifts back up")
say("| shield | races | estimate, 2nd half mean | lowest estimate | estimate samples (every 25 steps) |")
say("|---|---|---|---|---|")
for name, f in (("E35", "stress_mu0.7_muest"), ("E35b", "stress_mu0.7_mu2"), ("E36", "stress_mu0.7_oxmu")):
    R = load(f"results/{f}.json")
    for kind, X in (("wall hit", [r for r in R if r["wall"]]), ("finished", [r for r in R if fin(r)])):
        if X:
            say(f"| {name} | {kind} ({len(X)}) | {np.mean([np.mean(r['mu_hat'][len(r['mu_hat']) // 2:]) for r in X]):.3f} | "
                f"{np.mean([min(r['mu_hat']) for r in X]):.3f} | {np.mean([len(r['mu_hat']) for r in X]):.0f} |")
say()
say("True friction is 0.70. With the first estimate (rise 0.05) the races that end in the wall carry an estimate above")
say("the truth and end early; the smoother estimate (rise 0.02) stays below it. Lane W tests the combined shield with")
say("the smoother estimate (E36b).")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
