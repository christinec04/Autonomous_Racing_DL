import time, numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.controllers import PurePursuit
for mode in ["off", "additive", "conditioned_fallback"]:
    env = RaceEnv(EnvConfig(n_opp=3, shield=ShieldConfig(mode=mode)))
    obs, _ = env.reset(seed=1)
    pp = PurePursuit(env.cl, speed_scale=1.0)
    t = time.time(); k = 0; R = 0; lams = []
    while True:
        e = env._states()[0]
        a = env.to_normalized(pp.act(e[0], e[1], e[4], e[3]))
        obs, r, term, trunc, info = env.step(a); R += r; k += 1; lams.append(info["lambda"])
        if term or trunc: break
    print(f"{mode:22s} steps={k} t={info['t']:.1f}s prog={info['progress']:.0f}m wall={info['wall']} car={info['car']} "
          f"R={R:.1f} lam>0={np.mean(np.array(lams)>0):.2f} {k/(time.time()-t):.0f} ctrl steps/s obs={obs.shape}")
