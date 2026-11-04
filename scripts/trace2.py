import sys, numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig, BODY
from racing.controllers import PurePursuit
pol = sys.argv[1]
env = RaceEnv(EnvConfig(n_opp=0 if pol == "fast" else 3, shield=ShieldConfig(mode="conditioned_fallback")))
env.reset(seed=0); rng = np.random.default_rng(0)
pp = PurePursuit(env.cl, speed_scale=1.1)
rows = []
for k in range(2000):
    e = env._states()[0]
    if pol == "fast": a = env.to_normalized(pp.act(e[0], e[1], e[4], e[3]))
    else: a = rng.uniform(-1, 1, 2) if k % 10 == 0 else a
    minc = (env.scan - BODY).min()
    o, r, te, tr, info = env.step(a)
    rows.append(f"k={k} s={info['progress']:.1f} v={e[3]:.2f} steer={e[2]:+.2f} beta={np.degrees(e[6]):+.0f} r={e[5]:+.2f} lat={env.lat[0]:+.2f} minclr={minc:.2f} rl={np.round(info['a_rl'],2)} fin={np.round(info['a_final'],2)} lam={info['lambda']:.2f} fb={info['fallback']}")
    if te or tr: break
print("\n".join(rows[-14:])); print("wall", info["wall"], "car", info["car"])
