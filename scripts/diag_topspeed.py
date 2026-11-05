"""Is the shielded agent timid? Commanded vs executed speed on a solo flying lap (lap 2), shield on.

usage: python -m scripts.diag_topspeed [model.zip ...]   (default: the seed-0 shielded policy)
E17 found the seed-0 policy tops out at ~8.4 m/s even on the main straight because it never asks for more.
"""
import sys
import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from stable_baselines3 import PPO

for path in sys.argv[1:] or ["runs/ppo_shield_s0/model_stage3.zip"]:
    m = PPO.load(path, device="cpu")
    env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="conditioned_fallback", reach="grip"), episode_time=90,
                            curvature_preview=m.observation_space.shape[0] > 77))
    obs, _ = env.reset(seed=0, options={"s_ego": 3.0})
    L = env.cl.length
    rows, t_lap = [], None
    while True:
        a, _ = m.predict(obs[None], deterministic=True)
        obs, r, te, tr, info = env.step(a[0])
        if L <= info["progress"] < 2 * L:
            t_lap = t_lap or info["t"]
            rows.append((info["progress"] - L, info["state"][3], info["a_rl"][1], info["lambda"]))
        if te or tr or info["progress"] >= 2 * L:
            break
    if not rows:
        print(f"{path}: did not reach lap 2 ({'crashed' if te else 'stopped'} at {info['progress']:.0f} m)")
        continue
    R = np.array(rows)
    straight = (R[:, 0] > 2) & (R[:, 0] < 32)
    print(f"{path}: lap-2 time {info['t'] - t_lap:.2f} s | v max {R[:, 1].max():.2f}, main straight mean "
          f"{R[straight, 1].mean():.2f} | policy speed cmd max {R[:, 2].max():.2f} | shield active {np.mean(R[:, 3] > 0):.0%}"
          + ("  (crashed)" if te else ""))
