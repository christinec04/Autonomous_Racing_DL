"""Merge race-evaluation files, check metric targets, Mann-Whitney U tests. Writes results/summary.md.

python -m scripts.analyze results/eval_baselines.json results/eval_ppo_s0.json [...]
"""
import json, sys, pathlib
import numpy as np
from scipy.stats import mannwhitneyu
from racing.evaluate import summarize, check_targets

OURS = "ppo_apf"
ORDER = ["ppo_apf", "ppo", "ppo@shieldtrained_noshield", "ppo_apf@noshieldtrained_withshield", "ppo_residual",
         "ppo_residual_apf", "ppo_additive", "pid_apf", "pure_pursuit"]
NAMES = {
    "ppo_apf": "PPO + shield (ours)",
    "ppo": "PPO, no shield",
    "ppo@shieldtrained_noshield": "shield-trained PPO, shield removed",
    "ppo_apf@noshieldtrained_withshield": "unshielded PPO + shield at race time",
    "ppo_residual": "residual PPO on PID+APF (ResRace-style)",
    "ppo_residual_apf": "residual PPO + our shield at race time",
    "ppo_additive": "PPO + additive Eq.2/3 shield",
    "pid_apf": "PID + APF",
    "pure_pursuit": "Pure Pursuit",
}


def per_race(r, key):
    if key == "collided":
        return float(r["dnf"])
    if key == "passes":
        return float(r["overtake_successes"])
    if key == "laps_done":
        return r["laps_done"]
    if key == "clean_lap":
        t = r["lap_times"][1:]
        return float(np.mean(t)) if t else None
    raise KeyError(key)


def mwu(res, a, b, key):
    xa = [v for v in (per_race(r, key) for r in res if r["controller"] == a) if v is not None]
    xb = [v for v in (per_race(r, key) for r in res if r["controller"] == b) if v is not None]
    if len(xa) < 3 or len(xb) < 3 or len(set(xa + xb)) == 1:
        return None
    return float(mannwhitneyu(xa, xb, alternative="two-sided").pvalue)


def fmt(v, f="{:.2f}"):
    return "-" if v is None else f.format(v)


def main(files, out="results/summary.md"):
    races = []
    for f in files:
        races += json.load(open(f))["races"]
    lines = ["# Race results", "", f"Sources: {', '.join('`' + pathlib.Path(f).name + '`' for f in files)}. "
             "20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 "
             "(lap 1 is a standing start).", ""]
    for cond in ("nominal", "randomized"):
        R = [r for r in races if r["randomize"] == (cond == "randomized")]
        S = summarize(R)
        ctrls = [c for c in ORDER if c in S] + [c for c in S if c not in ORDER]
        lines += [f"## {cond}", "",
                  "| controller | finished | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for c in ctrls:
            s = S[c]
            lines.append(f"| {NAMES.get(c, c)} | {s['finished']}/{s['races']} | {fmt(s['lap_mean'])} | {fmt(s['lap_best'])} | "
                         f"{s['collisions_per_10_laps']:.2f} ({s['wall']}, {s['car']}) | {s['passes_per_race']:.2f} | "
                         f"{fmt(s['overtake_success'], '{:.0%}')} ({s['overtake_successes']}/{s['overtake_attempts']}) | "
                         f"{s['shield_freq']:.0%} | {s['grip_above_90']:.1%} | {s['slip_above_15']:.1%} |")
        if OURS in S and "pid_apf" in S:
            T = check_targets(S)
            lines += ["", f"Targets for {NAMES[OURS]} ({cond}):", "", "| metric | value | target | met |", "|---|---|---|---|"]
            for k, t in T.items():
                lines.append(f"| {t['desc']} | {fmt(t['value'], '{:.3f}')} | {t['target']} | "
                             f"{'yes' if t['met'] else ('no' if t['met'] is False else '-')} |")
        if OURS in S:
            lines += ["", f"Mann-Whitney U p-values, {NAMES[OURS]} vs each controller (per-race values):", "",
                      "| vs | collided (0/1) | passes | laps completed | clean lap time |", "|---|---|---|---|---|"]
            for c in ctrls:
                if c == OURS:
                    continue
                lines.append(f"| {NAMES.get(c, c)} | " + " | ".join(fmt(mwu(R, OURS, c, k), "{:.3g}") for k in
                                                                     ("collided", "passes", "laps_done", "clean_lap")) + " |")
        lines.append("")
    out = pathlib.Path("results/summary.md")
    out.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    args = sys.argv[1:]
    out = "results/summary.md"
    if "--out" in args:
        i = args.index("--out"); out = args[i + 1]; args = args[:i] + args[i + 2:]
    main(args, out)
