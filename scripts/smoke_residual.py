import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
env = RaceEnv(EnvConfig(n_opp=3, residual=True, shield=ShieldConfig(mode="off")))
env.reset(seed=1)
for k in range(400):
    o, r, te, tr, info = env.step(np.zeros(2))
    if te or tr: break
print("residual zero-action:", k, info["progress"], info["wall"], info["car"])
