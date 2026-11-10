"""Run any race_ego mode on the offline bicycle model, same key=value args as the controller.

  python sim_train.py mode=train run=sim_friction shield=friction minutes=20
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "racelib"))
sys.path.insert(0, HERE)
from env import RaceEnv  # noqa: E402
from sim_backend import SimBackend  # noqa: E402
from track import Track  # noqa: E402

import rl  # noqa: E402

args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
track = Track()
env = RaceEnv(SimBackend(track, seed=int(args.get("seed", 0))), track, shield=args.get("shield", "none"),
              max_steps=int(args.get("max_steps", 2500)), seed=int(args.get("seed", 0)))
rl.run(args, env, os.path.abspath(os.path.join(HERE, "..", "..", "runs", "rl", args.get("run", "sim"))))
