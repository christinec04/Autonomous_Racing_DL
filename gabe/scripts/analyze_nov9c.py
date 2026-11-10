"""Analysis of the jobs that finished on Nov 9 afternoon and evening (lanes W, X, V): E36b combined shield with the
smoother estimate, E35c median-gated estimate, E37 policy retrained with the combined shield (normal and wide
friction range). Writes results/analysis/2026-11-09c.md.
"""
import json
import pathlib

import numpy as np
from scipy.stats import fisher_exact

OUT = pathlib.Path("results/analysis/2026-11-09c.md")
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def fin(r):
    return not r["dnf"] and not r["stuck"]


def load(f):
    p = pathlib.Path(f"results/{f}.json")
    return json.load(open(p))["races"] if p.exists() else None


def stats(X):
    laps = [t for r in X for t in r["lap_times"][1:]]
    return (f"{sum(map(fin, X))}/{len(X)} | {sum(r['car'] for r in X)} | {sum(r['wall'] for r in X)} | "
            f"{np.mean(laps):.2f} | {np.mean([r['overtake_successes'] for r in X]):.2f} | "
            f"{np.mean([r['shield_freq'] for r in X]):.3f}")


HDR = "| {} | finished | car | wall | lap s | passes | shield |\n|---|---|---|---|---|---|---|"

say("# Analysis 2026-11-09c (lanes W, X, V)")
say()
say("## Shield variants on the same three trained policies (3 seeds)")
say("Main protocol 50 race seeds nominal + randomised (300 races), stress tests 20 race seeds (60 races).")
say()
say(HDR.format("shield, setting"))
for name, v in (("relaxed check + estimate (E36)", "oxmu"), ("+ smoother estimate (E36b)", "oxmu2"),
                ("+ median gate, rise 0.05 (E35c)", "oxmed"), ("+ smoother + median gate (E35c)", "oxmu2med")):
    for setting, f in (("main", f"eval_{v}"), ("x0.8", f"stress_mu0.8_{v}"), ("x0.7", f"stress_mu0.7_{v}")):
        R = load(f)
        if R:
            say(f"| {name}, {setting} | {stats(R)} |")
base = load("eval_oxmu")
for v in ("oxmu2", "oxmu2med"):
    R = load(f"eval_{v}")
    a, b = sum(map(fin, base)), sum(map(fin, R))
    say(f"\n- E36 vs {v}, main protocol: {a} vs {b} of 300, Fisher p = {fisher_exact([[a, 300 - a], [b, 300 - b]])[1]:.2g}")
say()

say("## The estimate at a wall hit (x0.7): the last 10 readings (every 25 steps) of each wall-hit race")
for v in ("oxmu", "oxmu2med"):
    say(f"\n{v}:")
    for r in [r for r in load(f"stress_mu0.7_{v}") if r["wall"]]:
        say(f"- {[round(x, 2) for x in r['mu_hat'][-10:]]}")
say()
say("Right before the wall the estimate sits near the true 0.70; it jumps to about 0.9 in one reading at the impact")
say("and then stays flat because the car is stopped (no reading below 2 m/s). The high values after the crash are a")
say("result of the crash, not its cause.")
say()

say("## E37: residual PPO retrained with the combined shield on (3.5M steps, then raced with that shield)")
say(HDR.format("policy, setting"))
old = {0: "trained", 1: "trained_s1"}
for s in (0, 1):
    for setting, f in (("main", "eval_oxmu"), ("x0.8", "stress_mu0.8_oxmu"), ("x0.7", "stress_mu0.7_oxmu")):
        say(f"| E29 policy seed {s}, {setting} | "
            f"{stats([r for r in load(f) if r['controller'].endswith('@' + old[s])])} |")
for tag in ("oxmu", "oxmu_widemu"):
    for s in (0, 1):
        for setting, f in (("main", "eval_{}"), ("x0.8", "stress_mu0.8_{}"), ("x0.7", "stress_mu0.7_{}")):
            R = load(f.format(f"ppo_residual_{tag}_s{s}"))
            if R:
                say(f"| E37 {'wide friction 0.65-1.15' if 'wide' in tag else 'friction 0.85-1.15'} seed {s}, {setting} | {stats(R)} |")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
