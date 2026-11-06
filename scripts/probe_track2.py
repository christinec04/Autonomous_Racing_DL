"""Can the classical controllers lap a track solo? Default: the unseen Track2.

  python -m scripts.probe_track2 [map_name] [tire]

Runs Pure Pursuit (no shield) and PID+APF (the evaluate.py settings) through RaceEnv with no opponents, 25 Hz
control, 3 laps, and prints lap times, collisions and the largest lateral offset.
"""
import sys

import numpy as np

from racing.env import EnvConfig, RaceEnv
from racing.evaluate import SHIELD_FOR, make_controller
from racing.shield import ShieldConfig

MAP = sys.argv[1] if len(sys.argv) > 1 else "Track2"
TIRE = sys.argv[2] if len(sys.argv) > 2 else "saturated_v2"
LAPS = 3

for ctrl in ["pure_pursuit", "pid_apf"]:
    env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(**SHIELD_FOR[ctrl]), episode_time=LAPS * 70.0,
                            tire=TIRE, map_name=MAP))
    obs, _ = env.reset(seed=0, options=dict(s_ego=3.0))
    act = make_controller(ctrl, env)
    L = env.cl.length
    marks, maxd, vmax, lams = [], 0.0, 0.0, []
    while True:
        obs, r, term, trunc, info = env.step(act(obs))
        maxd = max(maxd, abs(info["lat"])); vmax = max(vmax, info["state"][3]); lams.append(info["lambda"])
        if info["progress"] >= L * (len(marks) + 1):
            marks.append(info["t"])
        if term or trunc or len(marks) >= LAPS:
            break
    print(f"{MAP} {ctrl:13s} laps={len(marks)}/{LAPS} lap_times={np.round(np.diff([0.0] + marks), 2)} "
          f"crash={term} (wall {info['wall']}) max|d|={maxd:.2f} vmax={vmax:.1f} "
          f"shield_freq={np.mean(np.array(lams) > 0):.2f}  track length {L:.1f} m")
