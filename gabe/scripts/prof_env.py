import cProfile, pstats, numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
env = RaceEnv(EnvConfig(n_opp=3, shield=ShieldConfig(mode="off")))
env.reset(seed=1)
for _ in range(20): env.step(np.array([0.0, -0.8]))
env.reset(seed=1)
pr = cProfile.Profile(); pr.enable()
for _ in range(150):
    o, r, te, tr, i = env.step(np.array([0.0, -0.8]))
    if te: env.reset()
pr.disable()
pstats.Stats(pr).sort_stats("cumtime").print_stats(18)
