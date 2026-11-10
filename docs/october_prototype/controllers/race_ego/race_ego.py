"""Webots ego controller for the shielded PPO experiments.

Args come from controllerArgs and from the RACE_EGO_ARGS environment variable, which wins,
so one world file serves every run. See rl.py for the modes.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "racelib"))
sys.path.insert(0, HERE)
from car import Car, out_dir  # noqa: E402
from env import RaceEnv, WebotsBackend  # noqa: E402
from track import Track  # noqa: E402

import rl  # noqa: E402

car = Car()
args = {**car.args, **dict(a.split("=", 1) for a in os.environ.get("RACE_EGO_ARGS", "").split() if "=" in a)}
print("[race_ego] args", args)
track = Track()
backend = WebotsBackend(car, track, lidar_left_first=args.get("lidar_left_first", "1") == "1")
env = RaceEnv(backend, track, shield=args.get("shield", "none"), opponents=0,
              max_steps=int(args.get("max_steps", 2500)), seed=int(args.get("seed", 0)))
try:
    rl.run(args, env, out_dir("rl", args.get("run", "smoke")))
finally:
    car.d.simulationQuit(0)
