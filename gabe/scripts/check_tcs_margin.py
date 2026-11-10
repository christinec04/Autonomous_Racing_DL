import sys, numpy as np
import racing.tires as T
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.controllers import PIDFollower, PurePursuit
for m in [0.95, 0.85, 0.75, 0.65]:
    T.TCS_MARGIN = m
    out = []
    for name, kw in [("pid", dict(kp=0.6, kd=0.0, k_head=0.7)), ("pid", dict(kp=0.3, kd=0.03, k_head=0.4, preview=1.0)), ("pp", {})]:
        env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="off"), episode_time=80))
        env.reset(seed=0, options={"s_ego": 3.0})
        c = PIDFollower(env.cl, 0.04, speed_scale=0.85, **kw) if name == "pid" else PurePursuit(env.cl, speed_scale=0.85)
        marks = []
        while True:
            e = env._states()[0]
            _, _, te, tr, info = env.step(env.to_normalized(c.act(e[0], e[1], e[4], e[3])))
            if info["progress"] >= env.cl.length * (len(marks) + 1): marks.append(info["t"])
            if te or tr or len(marks) >= 2: break
        out.append(f"{name}:{'crash@%dm' % info['progress'] if te else np.round(np.diff([0]+marks),1)}")
    print("TCS margin", m, " | ".join(out))
