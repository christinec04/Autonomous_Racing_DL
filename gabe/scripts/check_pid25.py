import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.controllers import PIDFollower, PurePursuit
for name in ["pid", "pp"]:
  for scale in [0.75, 0.85]:
    env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="off"), episode_time=80))
    obs, _ = env.reset(seed=0, options={"s_ego": 3.0})
    c = PIDFollower(env.cl, env.cfg.control_dt, speed_scale=scale) if name == "pid" else PurePursuit(env.cl, speed_scale=scale)
    marks = []; maxslip = 0
    while True:
        e = env._states()[0]
        obs, r, te, tr, info = env.step(env.to_normalized(c.act(e[0], e[1], e[4], e[3])))
        maxslip = max(maxslip, abs(e[6]))
        if info["progress"] >= env.cl.length * (len(marks) + 1): marks.append(info["t"])
        if te or tr or len(marks) >= 2: break
    print(name, scale, "crash" if te else "ok", "laps", np.round(np.diff([0] + marks), 2), "prog", round(info["progress"]), "maxslip", round(np.degrees(maxslip)))
