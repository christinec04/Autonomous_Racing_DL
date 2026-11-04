"""E15: confirm the best E14 shield settings on the full protocol (20 races, nominal + randomised)."""
import json
from multiprocessing import Pool
from racing.evaluate import run_race

MODEL = "runs/ppo_shield_s0/model_stage3.zip"
VARIANTS = {
    "ppo_apf": dict(mode="conditioned_fallback", reach="grip"),
    "ppo_apf c_safe0.10": dict(mode="conditioned_fallback", reach="grip", c_safe=0.10),
    "ppo_apf fixed": dict(mode="conditioned_fallback", reach="fixed"),
    "ppo_apf fixed c_safe0.10": dict(mode="conditioned_fallback", reach="fixed", c_safe=0.10),
}

def job(a):
    name, seed, rnd = a
    return run_race(("ppo_apf", MODEL, 10_000 + seed, rnd, 5, VARIANTS[name], name))

if __name__ == "__main__":
    jobs = [(v, s, r) for r in (False, True) for v in VARIANTS for s in range(20)]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    json.dump(dict(races=res), open("results/shield_confirm.json", "w"))
    print("done")
