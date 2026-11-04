import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="conditioned_fallback"), shield_prob=0.5))
on = []
for s in range(10):
    env.reset(seed=s); on.append(env.shield_on)
    for _ in range(5): env.step(np.array([0.0, 0.5]))
print("shield on per episode:", on)
