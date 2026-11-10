"""Scripted opponent. Holds the racing line at pace times the speed profile and passes slower cars mildly.

controllerArgs  pace=0.80   fraction of the friction circle speed profile
A car moved more than 25 m off the circuit by a supervisor parks with the brakes on.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "racelib"))
from car import Car  # noqa: E402
from pilot import Pilot, gap_ahead, node_state  # noqa: E402
from track import Track  # noqa: E402

car = Car()
track = Track()
pilot = Pilot(track, pace=float(car.args.get("pace", 0.85)), aggression=1.0)
me = car.node.getDef()
others = [n for n in (car.d.getFromDef(d) for d in ("EGO", "OPP_1", "OPP_2", "OPP_3", "OPP_4") if d != me) if n]

s_prev = None
while car.step() != -1:
    i, s, lat = track.project(car.x, car.y, me)
    if s_prev is not None and abs(gap_ahead(track, s_prev, s)) > 30:
        pilot.reset()  # a supervisor teleported this car
    s_prev = s
    if abs(lat) > 25:
        pilot.reset()
        car.command(0, 0, 1)
        continue
    st = {"x": car.x, "y": car.y, "yaw": car.yaw, "vx": car.vx, "vy": car.vy, "speed": car.speed,
          "i": i, "s": s, "lat": lat}
    car.command(*pilot.act(st, [node_state(track, n, id(n)) for n in others], car.dt))
