import sys, numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig, BODY
from racing.controllers import PurePursuit
mode = sys.argv[1] if len(sys.argv) > 1 else "conditioned_fallback"
env = RaceEnv(EnvConfig(n_opp=3, shield=ShieldConfig(mode=mode)))
env.reset(seed=1)
pp = PurePursuit(env.cl, speed_scale=1.0)
for k in range(400):
    st = env._states()
    e = st[0]
    a = env.to_normalized(pp.act(e[0], e[1], e[4], e[3]))
    minc = (env.scan - BODY).min()
    obs, r, term, trunc, info = env.step(a)
    if k > 45 or term:
        print(f"k={k} v={e[3]:.2f} lat={env.lat[0]:+.2f} minclr={minc:.2f} rl={np.round(info['a_rl'],2)} fin={np.round(info['a_final'],2)} "
              f"lam={info['lambda']:.2f} fb={info['fallback']} gaps={np.round(info['opp_prog']-info['progress'],1)} opp_lat={np.round(info['opp_lat'],2)}")
    if term or trunc: print("wall", info["wall"], "car", info["car"]); break
