"""Why does the shielded agent top out at ~8.4 m/s? Compare commanded vs executed speed on the main straight."""
import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from stable_baselines3 import PPO
for mode in ["conditioned_fallback", "off"]:
    env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode=mode, reach="grip"), episode_time=80))
    obs, _ = env.reset(seed=0, options={"s_ego": 3.0})
    m = PPO.load("runs/ppo_shield_s0/model_stage3.zip", device="cpu")
    rows = []
    while True:
        a, _ = m.predict(obs[None], deterministic=True)
        obs, r, te, tr, info = env.step(a[0])
        L = env.cl.length
        if L + 2 < info["progress"] < L + 32:
            rows.append((info["progress"] - L, info["state"][3], info["a_rl"][1], info["a_final"][1], info["lambda"]))
        if te or tr or info["progress"] > L + 40: break
    R = np.array(rows)
    print(f"shield={mode}: main straight, lap 2: v mean {R[:,1].mean():.2f} max {R[:,1].max():.2f} | policy speed cmd mean {R[:,2].mean():.2f} max {R[:,2].max():.2f} | executed cmd mean {R[:,3].mean():.2f} | shield active {np.mean(R[:,4]>0):.0%}")
