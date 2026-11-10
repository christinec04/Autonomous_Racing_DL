"""Import the shared racelib code unchanged, with the vehicle constants of the f1tenth car.

track.py constants are patched before pilot, shield and env import them, so every module sees the
same car. Nothing in controllers/racelib is edited and track.json is not rewritten, the speed
profile is rebuilt in memory for a car without downforce.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RACELIB = os.path.abspath(os.path.join(HERE, "..", "controllers", "racelib"))
if RACELIB not in sys.path:
    sys.path.insert(0, RACELIB)

import vehicle  # noqa: E402
import track  # noqa: E402

track.MU = vehicle.MU
track.CLA = 0.0
track.MASS = vehicle.MASS
track.WHEELBASE = vehicle.WHEELBASE
track.P_MAX = vehicle.P_MAX

import pilot  # noqa: E402

pilot.ROLL_K = 0.01     # the gym has no wheel damping, only the rolling loss the backend adds
pilot.K_US = 1.0e-3      # understeer gradient fitted by calib.py on the stp car, 0.8e-3 to 1.2e-3 from 30 to 45 m/s

import shield  # noqa: E402
import env  # noqa: E402

from pilot import Pilot  # noqa: E402,F401
from shield import make_shield  # noqa: E402,F401


def make_track():
    t = track.Track()
    t.v = track.speed_profile(t.kappa, t.ds)
    return t
