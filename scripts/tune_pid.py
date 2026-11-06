"""Retune PID gains for the 25 Hz control rate used in the race env."""
import itertools, json, numpy as np
from multiprocessing import Pool
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.controllers import PIDFollower
GRID = list(itertools.product([0.3, 0.6, 1.0], [0.0, 0.05], [0.3, 0.6, 1.0], [0.0, 0.3, 0.6]))
def job(g):
    kp, kd, kh, pv = g
    env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="off"), episode_time=80))
    env.reset(seed=0, options={"s_ego": 3.0})
    c = PIDFollower(env.cl, env.cfg.control_dt, speed_scale=0.85, kp=kp, kd=kd, k_head=kh, preview=pv)
    marks = []; maxd = 0
    while True:
        e = env._states()[0]
        _, _, te, tr, info = env.step(env.to_normalized(c.act(e[0], e[1], e[4], e[3])))
        maxd = max(maxd, abs(info["lat"]))
        if info["progress"] >= env.cl.length * (len(marks) + 1): marks.append(info["t"])
        if te or tr or len(marks) >= 2: break
    return dict(g=g, ok=not te and len(marks) >= 2, prog=info["progress"], laps=list(np.round(np.diff([0] + marks), 2)), maxd=maxd)
if __name__ == "__main__":
    with Pool(3) as p: res = p.map(job, GRID, chunksize=2)
    good = sorted([r for r in res if r["ok"]], key=lambda r: (r["maxd"]))
    print(len(good), "stable of", len(res))
    for r in good[:8]: print(r)
