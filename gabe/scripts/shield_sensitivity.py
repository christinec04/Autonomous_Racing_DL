"""Race the seed-0 shield-trained policy under different shield settings (10 nominal races each)."""
import json, sys
from multiprocessing import Pool
import numpy as np
from racing.evaluate import run_race, summarize

MODEL = "runs/ppo_shield_s0/model_stage3.zip"
BASE = dict(mode="conditioned_fallback", reach="grip")
VARIANTS = {
    "default (grip, c_safe 0.05, opp_brake 6)": {},
    "fixed reach (6 m/s^2)": dict(reach="fixed"),
    "c_safe 0.02": dict(c_safe=0.02),
    "c_safe 0.10": dict(c_safe=0.10),
    "opp_brake 3": dict(opp_brake=3.0),
    "opp_brake 9": dict(opp_brake=9.0),
    "no fallback (conditioned only)": dict(mode="conditioned"),
    "additive Eq. 2/3": dict(mode="additive", reach="fixed"),
}

def job(args):
    name, seed = args
    sh = dict(BASE); sh.update(VARIANTS[name])
    return run_race(("ppo_apf", MODEL, 10_000 + seed, False, 5, sh, name))

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    jobs = [(v, s) for v in VARIANTS for s in range(n)]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    json.dump(dict(races=res), open("results/shield_sensitivity.json", "w"))
    S = summarize(res)
    lines = ["| shield setting | finished | clean lap | collisions / 10 laps (wall, car) | passes / race | shield active |",
             "|---|---|---|---|---|---|"]
    for v in VARIANTS:
        s = S[v]
        lines.append(f"| {v} | {s['finished']}/{s['races']} | {s['lap_mean'] and round(s['lap_mean'], 2)} | "
                     f"{s['collisions_per_10_laps']:.2f} ({s['wall']}, {s['car']}) | {s['passes_per_race']:.2f} | {s['shield_freq']:.0%} |")
    open("results/shield_sensitivity.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
