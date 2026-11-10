"""E38 lane AA: E37 B (wide friction range, seeds 0-2) vs E29 (seeds 0-2), both raced with the combined shield,
on the unseen Track2 and with five opponents. 20 race seeds x nominal + randomised per policy.
Writes results/analysis/2026-11-10.md.
"""
import json
import pathlib

from scipy.stats import fisher_exact

fin = lambda r: not r["dnf"] and not r["stuck"]
lines = []


def say(s=""):
    print(s)
    lines.append(s)


say("# Analysis 2026-11-10: E37 B vs E29 on Track2 and with five opponents (combined shield)")
say()
say("| setting | policies | finished | races with wall hit | races with car contact | passes / race | lap (s) | shield active | above 90% grip |")
say("|---|---|---|---|---|---|---|---|---|")
for f, label in (("eval_widemu_Track2", "Track2"), ("stress_opp5_widemu", "5 opponents")):
    races = json.load(open(f"results/{f}.json"))["races"]
    groups = {"E29": [r for r in races if "@trained" in r["controller"]],
              "E37 B": [r for r in races if "@widemu" in r["controller"]]}
    counts = []
    for g, v in groups.items():
        n, k = len(v), sum(map(fin, v))
        laps = [t for r in v for t in r["lap_times"]]
        counts.append((k, n))
        say(f"| {label} | {g} | {k}/{n} | {sum(r['wall'] > 0 for r in v)} | {sum(r['car'] > 0 for r in v)} | "
            f"{sum(r['overtake_successes'] for r in v) / n:.2f} | {sum(laps) / len(laps):.2f} | "
            f"{sum(r['shield_freq'] for r in v) / n:.3f} | {sum(r['grip_above_90'] for r in v) / n:.3f} |")
    (a, na), (b, nb) = counts
    say(f"| {label} | Fisher exact, finished | p = {fisher_exact([[a, na - a], [b, nb - b]]).pvalue:.3f} | | | | | | |")
pathlib.Path("results/analysis").mkdir(parents=True, exist_ok=True)
open("results/analysis/2026-11-10.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
