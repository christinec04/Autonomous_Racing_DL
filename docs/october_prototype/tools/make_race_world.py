"""Generate the racing worlds from the shared track geometry in controllers/racelib/track.py.

  python tools/make_race_world.py                    probe.wbt, race_train.wbt and race.wbt
  python tools/make_race_world.py --kind train --ego-controller shield_test --ego-args "kind=friction" --out worlds/shield_test.wbt

The Road is visual only. Cars drive on the GROUND plane whose contactMaterial is "asphalt",
and WorldInfo pairs "asphalt" with the "slick" tyres at coulombFriction MU.
"""
import argparse
import math
import os
import random
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "controllers", "racelib"))
from track import HALF, MU, WIDTH, Track  # noqa: E402

BASE = "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/"
TRACK_PROTOS = ["objects/road/protos/Road.proto"]
PRETTY_PROTOS = [
    "objects/backgrounds/protos/TexturedBackground.proto",
    "objects/backgrounds/protos/TexturedBackgroundLight.proto",
    "objects/buildings/protos/SimpleBuilding.proto",
    "objects/traffic/protos/StreetLight.proto",
]
LIDAR = 'Lidar { name "lidar" fieldOfView 3.14159 horizontalResolution 180 numberOfLayers 1 maxRange 80 }'
GRID_FRONT = 200.0  # Turn 1 braking starts near s 220, its apex is near s 320
GRID = [("OPP_3", 0.0, 2.5, "0.85 0.87 0.9"), ("OPP_2", -10.0, -2.5, "0.45 0.1 0.75"),
        ("OPP_1", -20.0, 2.5, "0.05 0.2 0.85"), ("EGO", -30.0, -2.5, "0.95 0.35 0.02")]
PACE = {"OPP_1": 0.80, "OPP_2": 0.86, "OPP_3": 0.92}


def f(v):
    return f"{v:.5g}" if abs(v) >= 1e-5 else "0"


def mfstring(args):
    return "[ " + " ".join(f'"{a}"' for a in args) + " ]" if args else "[ ]"


def header(protos, title, dt, mu, fds, ground):
    lines = ["#VRML_SIM R2025a utf8", ""]
    lines += [f'EXTERNPROTO "{BASE}{p}"' for p in protos]
    lines.append('EXTERNPROTO "../protos/RaceCar.proto"')
    slip = f" forceDependentSlip [ {fds} ]" if fds else ""
    lines.append(f"""
WorldInfo {{
  title "{title}"
  basicTimeStep {dt}
  contactProperties [
    ContactProperties {{ material1 "asphalt" material2 "slick" coulombFriction [ {mu} ]{slip} }}
  ]
}}
Viewpoint {{
  orientation -0.3 0.3 0.9 1.7
  position 0 -60 40
  near 1
  far 4000
  follow "ego"
}}
DEF GROUND Solid {{
  translation 0 0 0
  children [
    Shape {{
      appearance PBRAppearance {{ baseColor 0.16 0.17 0.19 roughness 1 metalness 0 }}
      geometry Plane {{ size {ground} {ground} }}
    }}
  ]
  name "ground"
  contactMaterial "asphalt"
  boundingObject Plane {{ size {ground} {ground} }}
  locked TRUE
}}""")
    return lines


def car(name, x, y, yaw, color, controller, args, sensors=""):
    slot = f"\n  sensorsSlotFront [ {sensors} ]" if sensors else ""
    return f"""DEF {name} RaceCar {{
  translation {f(x)} {f(y)} 0.36
  rotation 0 0 1 {f(yaw)}
  name "{name.lower()}"
  color {color}
  controller "{controller}"
  controllerArgs {mfstring(args)}{slot}
}}"""


def road(t):
    way = [t.center[i] for i in range(0, t.n, 2)] + [t.center[0]]
    wp = ", ".join(f"{f(x)} {f(y)} 0.01" for x, y in way)
    return f"""DEF TRACK Road {{
  name "circuit"
  width {WIDTH}
  numberOfLanes 1
  lines [ ]
  roadBorderHeight 0.2
  roadBorderWidth [ 1.6 ]
  rightBarrier TRUE
  leftBarrier TRUE
  wayPoints [ {wp} ]
  splineSubdivision -1
}}"""


def scenery(t):
    """Kerbs, start line, street lights and city blocks for the pretty world."""
    out = ["""TexturedBackground {
  texture "dusk"
  luminosity 0.55
}
TexturedBackgroundLight {
  texture "dusk"
  luminosity 1.3
  castShadows FALSE
}"""]
    x, y, yaw = t.pose(GRID_FRONT + 20, 0)
    out.append(f"""DEF START_LINE Pose {{
  translation {f(x)} {f(y)} 0.025
  rotation 0 0 1 {f(yaw)}
  children [ Shape {{ appearance PBRAppearance {{ baseColor 1 1 1 roughness 1 metalness 0 }} geometry Box {{ size 0.8 {WIDTH} 0.01 }} castShadows FALSE }} ]
}}""")
    kerbs = ["DEF KERBS Group {", "  children ["]
    first = [True, True]
    for i in range(t.n):
        k = t.kappa_center[i]
        if abs(k) < 0.012:
            continue
        side = 1 if k > 0 else -1
        c = i % 2
        px, py = t.center[i] + t.nrm[i] * side * (HALF - 0.75)
        if first[c]:
            col = "0.85 0.05 0.05" if c else "0.95 0.95 0.95"
            shape = (f"DEF KERB{c} Shape {{ appearance PBRAppearance {{ baseColor {col} roughness 0.9 metalness 0 }} "
                     "geometry Box { size 2.3 1.5 0.05 } castShadows FALSE }")
            first[c] = False
        else:
            shape = f"USE KERB{c}"
        kerbs.append(f"    Pose {{ translation {f(px)} {f(py)} 0.02 rotation 0 0 1 {f(t.heading(i))} children [ {shape} ] }}")
    kerbs += ["  ]", "}"]
    out.append("\n".join(kerbs))
    for k, d in enumerate([-40, -8, 24, 52, 84]):
        side = 1 if k % 2 else -1
        x, y, yaw = t.pose(GRID_FRONT + d, side * (HALF + 2.6))
        yaw += -math.pi / 2 if side > 0 else math.pi / 2
        out.append(f"""StreetLight {{
  translation {f(x)} {f(y)} 0
  rotation 0 0 1 {f(yaw)}
  name "street light {k}"
  intensity 45
}}""")
    random.seed(4)
    walls = ["glass building", "gray glass building", "blue glass building", "glass highrise",
             "transparent highrise", "highrise", "windowed building"]
    pts = t.center[::3]
    b = 0
    for gx in range(-420, 430, 42):
        for gy in range(-250, 260, 42):
            x, y = gx + random.uniform(0, 8), gy + random.uniform(0, 8)
            hw, hd = random.uniform(11, 16), random.uniform(11, 16)
            if min(math.hypot(px - x, py - y) for px, py in pts) < HALF + 26:
                continue
            r = random.random()
            floors = random.randint(26, 46) if r > 0.86 else random.randint(10, 20) if r > 0.45 else random.randint(4, 8)
            out.append(f"""SimpleBuilding {{
  translation {f(x)} {f(y)} 0
  name "block {b}"
  floorNumber {floors}
  corners [ {f(hw)} {f(hd)}, {f(hw)} {f(-hd)}, {f(-hw)} {f(-hd)}, {f(-hw)} {f(hd)} ]
  wallType "{random.choice(walls)}"
  roofShape "flat roof"
  roofType "bitumen"
  enableBoundingObject FALSE
}}""")
            b += 1
    return out


def probe_world(a):
    w = header([], "RaceCar physics probe", a.dt, a.mu, a.fds, a.ground)
    w.append(car("EGO", 0, 0, 0, "0.95 0.35 0.02", a.ego_controller or "race_probe", shlex.split(a.ego_args)))
    return w


def race_world(a, pretty):
    t = Track()
    w = header(TRACK_PROTOS + (PRETTY_PROTOS if pretty else []), "Street circuit race", a.dt, a.mu, a.fds, 1600)
    w.append(road(t))
    if pretty:
        w += scenery(t)
    for name, ds, lat, color in GRID:
        x, y, yaw = t.pose(GRID_FRONT + ds, lat)
        if name == "EGO":
            w.append(car(name, x, y, yaw, color, a.ego_controller or "race_ego", shlex.split(a.ego_args), LIDAR))
        else:
            args = [f"pace={PACE[name]:.2f}"] + shlex.split(a.opp_args)
            w.append(car(name, x, y, yaw, color, a.opp_controller or "opponent_pid", args))
    return w


def write(lines, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote", os.path.relpath(path, ROOT))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["all", "probe", "train", "race"], default="all")
    p.add_argument("--out", help="output .wbt, only with a single --kind")
    p.add_argument("--ego-controller", default="")
    p.add_argument("--ego-args", default="")
    p.add_argument("--opp-controller", default="")
    p.add_argument("--opp-args", default="")
    p.add_argument("--dt", type=int, default=8)
    p.add_argument("--mu", type=float, default=MU)
    p.add_argument("--ground", type=float, default=6000)
    p.add_argument("--fds", type=float, default=0.0, help="forceDependentSlip, 0 leaves pure Coulomb")
    a = p.parse_args()
    worlds = os.path.join(ROOT, "worlds")
    build = {"probe": probe_world, "train": lambda a: race_world(a, False), "race": lambda a: race_world(a, True)}
    names = {"probe": "probe.wbt", "train": "race_train.wbt", "race": "race.wbt"}
    kinds = list(build) if a.kind == "all" else [a.kind]
    if a.out and len(kinds) > 1:
        p.error("--out needs a single --kind")
    for k in kinds:
        write(build[k](a), a.out or os.path.join(worlds, names[k]))


if __name__ == "__main__":
    main()
