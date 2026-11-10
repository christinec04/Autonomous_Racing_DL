"""Tune the PID+APF baseline's APF gains so the course baseline is fair (laps cleanly)."""
import itertools, json, numpy as np
from multiprocessing import Pool
from racing.evaluate import run_race
GRID = list(itertools.product([0.3, 0.7, 1.2], [0.5, 1.5, 3.0], [0.15, 0.3], [0.5, 0.8]))  # k_steer, k_speed, d_min, smooth
def job(g):
    ks, kv, dm, sm = g
    sh = dict(mode="additive", reach="fixed", k_steer=ks, k_speed=kv, d_min=dm, smooth=sm)
    rs = [run_race(("pid_apf", None, 20_000 + s, False, 3, sh)) for s in range(4)]
    return dict(g=g, finished=sum(not r["dnf"] for r in rs), laps=float(np.mean([r["laps_done"] for r in rs])),
                lap=float(np.mean([t for r in rs for t in r["lap_times"][1:]])) if any(len(r["lap_times"]) > 1 for r in rs) else None,
                wall=sum(r["wall"] for r in rs), car=sum(r["car"] for r in rs), shield=float(np.mean([r["shield_freq"] for r in rs])))
if __name__ == "__main__":
    with Pool(4) as p:
        res = p.map(job, GRID, chunksize=1)
    res.sort(key=lambda r: (-r["finished"], -r["laps"], r["lap"] or 1e9))
    for r in res[:12]: print(r)
    json.dump(res, open("results/tune_apf.json", "w"))
