"""Replay the k-th crashed race of a controller and print the last seconds before the crash.

usage: python -m scripts.trace_crash <label> <model.zip> <results.json> [tire=saturated_v2] [k=0] [window=75]
"""
import json, sys
import numpy as np
from stable_baselines3 import PPO
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.evaluate import SHIELD_FOR, RECOVER

label, model, fjson = sys.argv[1:4]
kv = dict(a.split("=", 1) for a in sys.argv[4:] if "=" in a)
tire, k, win = kv.get("tire", "saturated_v2"), int(kv.get("k", 0)), int(kv.get("window", 75))
ctrl = label.split("@")[0]
races = [r for r in json.load(open(fjson))["races"] if r["controller"] == label and not r["randomize"] and r["dnf"]]
print("crashed races (nominal):", [(r["seed"], "wall" if r["wall"] else "car", round(r["laps_done"] % 1 * 199)) for r in races])
seed = races[k]["seed"]
cfg = EnvConfig(n_opp=3, opp_speed=(0.5, 0.75), random_start=True, shield=ShieldConfig(**SHIELD_FOR[ctrl]),
                episode_time=350.0, seed=seed, tire=tire, recover=ctrl in RECOVER)
env = RaceEnv(cfg); rng = np.random.default_rng(seed)
opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))), opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
obs, _ = env.reset(seed=seed, options=opts)
m = PPO.load(model, device="cpu")
log = []
while True:
    a, _ = m.predict(obs[None], deterministic=True)
    obs, r, te, tr, info = env.step(a[0]); st = info["state"]
    log.append(f"t={info['t']:6.2f} s={info['progress'] % 199:5.1f} v={st[3]:5.2f} beta={np.degrees(st[6]):+6.1f} "
               f"r={st[5]:+5.2f} lat={info['lat']:+.2f} hdg={np.degrees(info['hdg_err']):+4.0f} "
               f"rl=({info['a_rl'][0]:+.2f},{info['a_rl'][1]:4.1f}) fin=({info['a_final'][0]:+.2f},{info['a_final'][1]:4.1f}) "
               f"lam={info['lambda']:.2f} fb={int(info['fallback'])} cpred={info['c_pred']:+.2f} scan={env.scan.min():.2f}")
    if te or tr:
        break
print("\n".join(log[-win::max(1, win // 25)]))
print("end:", "wall" if info["wall"] else "car" if info["car"] else "truncated")
