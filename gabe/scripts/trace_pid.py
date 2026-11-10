import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.controllers import PIDFollower
env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="off"), episode_time=80))
env.reset(seed=0, options={"s_ego": 3.0})
c = PIDFollower(env.cl, env.cfg.control_dt, speed_scale=0.85, kp=0.6, kd=0.0, k_head=0.7)
for k in range(400):
    e = env._states()[0]
    a = c.act(e[0], e[1], e[4], e[3])
    _, _, te, tr, info = env.step(env.to_normalized(a))
    if k % 5 == 0 or te: print(f"k={k} s={info['progress']:.1f} v={e[3]:.1f} lat={info['lat']:+.2f} herr={info['hdg_err']:+.2f} steer_cmd={a[0]:+.2f} vcmd={a[1]:.1f} beta={np.degrees(e[6]):+.0f}")
    if te or tr: break
