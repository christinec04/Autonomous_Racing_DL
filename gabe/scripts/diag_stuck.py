"""Replay a race that ended 'stuck' and show what the shield was doing in the last seconds.

usage: python -m scripts.diag_stuck <label> <model.zip> <results.json> [escape] [tire=saturated_v2] [k=<index>]
The shield comes from evaluate.SHIELD_FOR for the label's controller type (the 'escape' flag forces escape on).
"""
import json, sys
import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from stable_baselines3 import PPO
from racing.evaluate import SHIELD_FOR

ctrl, model, fjson = sys.argv[1], sys.argv[2], sys.argv[3]
extra = sys.argv[4:]
escape = "escape" in extra
kv = dict(a.split("=", 1) for a in extra if "=" in a)
tire, k = kv.get("tire", "saturated"), int(kv.get("k", 0))
res = json.load(open(fjson))["races"]
stuck = [r for r in res if r["controller"] == ctrl and not r["randomize"] and not r["dnf"] and len(r["lap_times"]) < 5]
if not stuck: sys.exit("no stuck race")
print("stuck races (nominal):", [r["seed"] for r in stuck])
r0 = stuck[k]; seed = r0["seed"]
print("stuck race seed", seed, "laps_done", round(r0["laps_done"], 2))
cfg = EnvConfig(n_opp=3, opp_speed=(0.5, 0.75), random_start=True, randomize=False,
                shield=ShieldConfig(**{**SHIELD_FOR[ctrl.split("@")[0]], **({"escape": True} if escape else {})}),
                episode_time=350.0, seed=seed, residual=ctrl.startswith("ppo_residual"), tire=tire)
env = RaceEnv(cfg)
rng = np.random.default_rng(seed)
opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))), opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
obs, _ = env.reset(seed=seed, options=opts)
m = PPO.load(model, device="cpu")
log = []
while True:
    a, _ = m.predict(obs[None], deterministic=True)
    obs, r, te, tr, info = env.step(a[0])
    st = env._states()
    gaps = (st[1:, 0] - st[0, 0], st[1:, 1] - st[0, 1])
    log.append(f"beta={np.degrees(st[0,6]):+6.1f} t={info['t']:6.2f} prog={info['progress']:6.1f} v={st[0,3]:4.2f} lat={info['lat']:+.2f} hdg={np.degrees(info['hdg_err']):+5.0f} "
               f"rl=({info['a_rl'][0]:+.2f},{info['a_rl'][1]:4.1f}) fin=({info['a_final'][0]:+.2f},{info['a_final'][1]:4.1f}) "
               f"lam={info['lambda']:.2f} fb={int(info['fallback'])} opp_v={np.round(st[1:,3],1)} "
               f"opp_dist={np.round(np.hypot(*gaps),1)} opp_gap_track={np.round(info['opp_prog']-info['progress'],1)}")
    if te or tr: break
win = int(kv.get("window", 130))  # control steps shown (25 per second)
print("\n".join(log[-win::max(1, win // 13)])); print("end:", "crash" if te else "truncated (stuck or time)")
