"""Generate worlds/hamster_trap.wbt, a Hamster robot stuck in a U shaped obstacle on the way to its goal.

Webots has no Hamster model, so the robot is built here from primitives at the real size
(about 35 x 30 x 40 mm, two wheels, two front IR proximity sensors) with an ArUco marker on top
for the overhead camera the course uses for tracking.
"""
import math
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WORLDS = os.path.join(HERE, "..", "worlds")
OUT = os.path.join(WORLDS, "hamster_trap.wbt")
BASE = "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/"
PROTOS = [
    "objects/backgrounds/protos/TexturedBackground.proto",
    "objects/backgrounds/protos/TexturedBackgroundLight.proto",
    "objects/floors/protos/RectangleArena.proto",
]
START, ROBOT, GOAL = (-0.58, 0.0), (0.085, 0.0), (0.58, 0.0)
# wall boxes as (centre x, centre y, size x, size y)
WALLS = [(0.165, 0, 0.015, 0.355), (0.02, 0.17, 0.305, 0.015), (0.02, -0.17, 0.305, 0.015)]
BLOCKS = [(-0.33, 0.27, "0.85 0.25 0.2"), (-0.25, -0.3, "0.2 0.45 0.85"), (0.42, -0.26, "0.95 0.75 0.1"), (0.4, 0.33, "0.25 0.7 0.35")]
# ArUco DICT_4X4_50 id 0
ARUCO = ["1011", "0101", "0011", "0010"]


def aruco_texture():
    cell, n = 32, 8
    img = Image.new("RGB", (cell * n, cell * n), "white")
    px = img.load()
    for r in range(n):
        for c in range(n):
            if r in (0, n - 1) or c in (0, n - 1):
                continue
            inner_r, inner_c = r - 2, c - 2
            black = not (0 <= inner_r < 4 and 0 <= inner_c < 4 and ARUCO[inner_r][inner_c] == "1")
            if black:
                for y in range(r * cell, (r + 1) * cell):
                    for x in range(c * cell, (c + 1) * cell):
                        px[x, y] = (0, 0, 0)
    os.makedirs(os.path.join(WORLDS, "textures"), exist_ok=True)
    img.save(os.path.join(WORLDS, "textures", "aruco_4x4_0.png"))


def emissive(col, tr=0):
    return f"PBRAppearance {{ baseColor {col} emissiveColor {col} transparency {tr} roughness 1 metalness 0 }}"


def matte(col, rough=0.5):
    return f"PBRAppearance {{ baseColor {col} roughness {rough} metalness 0 }}"


def wheel(side, y):
    return f"""    HingeJoint {{
      jointParameters HingeJointParameters {{ axis 0 1 0 anchor 0 {y} 0.0165 }}
      device [ RotationalMotor {{ name "{side} wheel motor" maxVelocity 20 }} PositionSensor {{ name "{side} wheel sensor" }} ]
      endPoint Solid {{
        translation 0 {y} 0.0165
        rotation 1 0 0 1.5708
        children [
          Shape {{ appearance {matte('0.06 0.06 0.07', 0.8)} geometry DEF WHEEL_{side.upper()} Cylinder {{ height 0.004 radius 0.0165 subdivision 32 }} }}
          Shape {{ appearance {matte('0.8 0.8 0.82', 0.4)} geometry Cylinder {{ height 0.0044 radius 0.008 subdivision 20 }} }}
        ]
        name "{side} wheel"
        boundingObject USE WHEEL_{side.upper()}
        physics Physics {{ density -1 mass 0.003 }}
      }}
    }}"""


def hamster(x, y, yaw):
    return f"""DEF HAMSTER Robot {{
  translation {x} {y} 0
  rotation 0 0 1 {yaw}
  children [
    Pose {{ translation 0 0 0.0205 children [ Shape {{ appearance {matte('0.96 0.96 0.97', 0.25)} geometry Box {{ size 0.034 0.026 0.029 }} }} ] }}
    Pose {{ translation 0.0172 0 0.021 children [ Shape {{ appearance {matte('0.1 0.1 0.12', 0.3)} geometry Box {{ size 0.001 0.022 0.014 }} }} ] }}
    Pose {{ translation 0.0178 0.008 0.03 children [ DEF EYE Shape {{ appearance {emissive('0.3 0.8 1')} geometry Sphere {{ radius 0.0022 subdivision 2 }} }} ] }}
    Pose {{ translation 0.0178 -0.008 0.03 children [ USE EYE ] }}
    Pose {{ translation 0 0 0.0352 children [ Shape {{ appearance PBRAppearance {{ baseColorMap ImageTexture {{ url [ "textures/aruco_4x4_0.png" ] filtering 0 }} roughness 1 metalness 0 }} geometry Plane {{ size 0.03 0.03 }} }} ] }}
{wheel('left', 0.0155)}
{wheel('right', -0.0155)}
    DistanceSensor {{ translation 0.0175 0.009 0.016 rotation 0 0 1 0.18 name "left proximity" type "infra-red" lookupTable [ 0 255 0, 0.3 0 0 ] }}
    DistanceSensor {{ translation 0.0175 -0.009 0.016 rotation 0 0 1 -0.18 name "right proximity" type "infra-red" lookupTable [ 0 255 0, 0.3 0 0 ] }}
    DistanceSensor {{ translation 0.012 0.006 0.006 rotation 0 1 0 1.5708 name "left floor" type "infra-red" lookupTable [ 0 255 0, 0.02 0 0 ] }}
    DistanceSensor {{ translation 0.012 -0.006 0.006 rotation 0 1 0 1.5708 name "right floor" type "infra-red" lookupTable [ 0 255 0, 0.02 0 0 ] }}
    Accelerometer {{ }}
  ]
  name "Hamster"
  boundingObject Group {{
    children [
      Pose {{ translation 0 0 0.0205 children [ Box {{ size 0.034 0.026 0.029 }} ] }}
      Pose {{ translation 0.013 0 0.003 children [ Sphere {{ radius 0.003 }} ] }}
      Pose {{ translation -0.013 0 0.003 children [ Sphere {{ radius 0.003 }} ] }}
    ]
  }}
  physics Physics {{ density -1 mass 0.03 }}
  controller "hamster_hybrid_apf_drl"
}}"""


def arrow(x1, y1, x2, y2, z, col, r):
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    head = r * 6
    rot = f"{-uy:.4f} {ux:.4f} 0 1.5708"
    sx, sy = x1 + ux * (L - head) / 2, y1 + uy * (L - head) / 2
    hx, hy = x1 + ux * (L - head / 2), y1 + uy * (L - head / 2)
    return (f"    Pose {{ translation {sx:.4f} {sy:.4f} {z} rotation {rot} children [ Shape {{ appearance {emissive(col)} geometry Cylinder {{ height {L - head:.4f} radius {r} }} castShadows FALSE }} ] }}\n"
            f"    Pose {{ translation {hx:.4f} {hy:.4f} {z} rotation {rot} children [ Shape {{ appearance {emissive(col)} geometry Cone {{ height {head:.4f} bottomRadius {r * 2.6:.4f} }} castShadows FALSE }} ] }}")


def dots(points, col, name, spacing=0.024, radius=0.006):
    out, carry, first = [], 0.0, True
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        d = carry
        while d < L:
            x, y = x1 + (x2 - x1) * d / L, y1 + (y2 - y1) * d / L
            shape = f"DEF {name} Shape {{ appearance {emissive(col)} geometry Cylinder {{ height 0.001 radius {radius} }} castShadows FALSE }}" if first else f"USE {name}"
            first = False
            out.append(f"    Pose {{ translation {x:.4f} {y:.4f} 0.001 children [ {shape} ] }}")
            d += spacing
        carry = d - L
    return "\n".join(out)


def blocked(x, y):
    return any(abs(x - cx) < sx / 2 and abs(y - cy) < sy / 2 for cx, cy, sx, sy in WALLS)


def beam(x, y, yaw, half):
    """Triangle from an IR emitter out to the first wall it meets."""
    pts = []
    for a in (yaw - half, yaw + half):
        r = 0.0
        while r < 0.3 and not blocked(x + math.cos(a) * r, y + math.sin(a) * r):
            r += 0.002
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    coords = f"{x:.4f} {y:.4f} 0.016, {pts[0][0]:.4f} {pts[0][1]:.4f} 0.016, {pts[1][0]:.4f} {pts[1][1]:.4f} 0.016"
    return f"""    Shape {{
      appearance {emissive('1 0.25 0.9', 0.45)}
      geometry IndexedFaceSet {{ coord Coordinate {{ point [ {coords} ] }} coordIndex [ 0 1 2 -1 0 2 1 -1 ] }}
      castShadows FALSE
    }}"""


def main():
    aruco_texture()
    w = ["#VRML_SIM R2025a utf8", ""] + [f'EXTERNPROTO "{BASE}{p}"' for p in PROTOS]
    w.append("""
WorldInfo {
  info [
    "Escaping local minima, a hybrid APF and deep reinforcement learning local navigator"
    "The Hamster follows the potential field until it stalls in the U shaped obstacle, then a PPO agent drives it out."
  ]
  title "Hamster APF local minimum trap"
  basicTimeStep 16
}
DEF VIEW Viewpoint {
  orientation 0 0 1 0
  position -1 0 0.5
  near 0.01
}
TexturedBackground {
}
TexturedBackgroundLight {
}
RectangleArena {
  floorSize 1.5 1
  floorTileSize 0.25 0.25
  wallHeight 0.04
  wallThickness 0.01
}""")
    for k, (cx, cy, sx, sy) in enumerate(WALLS):
        w.append(f"""DEF TRAP_WALL_{k} Solid {{
  translation {cx} {cy} 0.03
  children [ Shape {{ appearance {matte('0.86 0.87 0.9', 0.8)} geometry DEF WALL_{k} Box {{ size {sx} {sy} 0.06 }} }} ]
  name "trap wall {k}"
  boundingObject USE WALL_{k}
}}""")
    for k, (x, y, col) in enumerate(BLOCKS):
        w.append(f"""Solid {{
  translation {x} {y} 0.03
  children [ Shape {{ appearance {matte(col, 0.6)} geometry DEF BLOCK_{k} Box {{ size 0.06 0.06 0.06 }} }} ]
  name "block {k}"
  boundingObject USE BLOCK_{k}
}}""")
    w.append(f"""DEF GOAL Pose {{
  translation {GOAL[0]} {GOAL[1]} 0
  children [
    Pose {{ translation 0 0 0.0008 children [ Shape {{ appearance {emissive('0.1 0.9 0.4', 0.35)} geometry Cylinder {{ height 0.001 radius 0.06 }} castShadows FALSE }} ] }}
    Pose {{ translation 0 0 0.05 children [ Shape {{ appearance {matte('0.9 0.9 0.9')} geometry Cylinder {{ height 0.1 radius 0.002 }} }} ] }}
    Pose {{ translation 0.018 0 0.088 children [ Shape {{ appearance {emissive('0.1 0.9 0.4')} geometry Box {{ size 0.036 0.001 0.024 }} }} ] }}
  ]
}}""")
    w.append(hamster(ROBOT[0], ROBOT[1], 0))

    rx, ry = ROBOT
    ov = ["DEF APF_OVERLAY Group {", "  children ["]
    # path the potential field drove, straight at the goal and into the trap
    ov.append(dots([START, (rx - 0.03, ry)], "0.25 0.5 1", "DOT_APF"))
    # escape driven by the PPO agent, then the potential field takes over again
    turn = [(-0.2 - 0.135 * math.sin(math.radians(a)), 0.135 - 0.135 * math.cos(math.radians(a))) for a in range(15, 181, 15)]
    escape = [(rx - 0.03, 0.0), (-0.2, 0.0)] + turn + [(0.1, 0.27), (0.23, 0.25)]
    ov.append(dots(escape, "1 0.77 0.1", "DOT_DRL"))
    ov.append(dots([(0.23, 0.25), (0.38, 0.16), GOAL], "0.25 0.5 1", "DOT_APF2"))
    # the two forces that cancel at the local minimum
    ov.append(arrow(rx, ry + 0.007, rx + 0.13, ry + 0.007, 0.055, "0.15 1 0.55", 0.003))
    ov.append(arrow(rx, ry - 0.007, rx - 0.13, ry - 0.007, 0.055, "1 0.15 0.3", 0.003))
    # the two front IR proximity beams
    ov.append(beam(rx + 0.0175, ry + 0.009, 0.18, 0.16))
    ov.append(beam(rx + 0.0175, ry - 0.009, -0.18, 0.16))
    ov += ["  ]", "}"]
    w.append("\n".join(ov))

    # overhead webcam on a stand, the course tracks the robot pose from an ArUco marker
    grey = matte("0.2 0.2 0.22", 0.5)
    w.append(f"""DEF SUPERVISOR Robot {{
  translation 0 0.56 0
  children [
    Pose {{ translation 0 0 0.5 children [ Shape {{ appearance {grey} geometry Cylinder {{ height 1 radius 0.008 }} }} ] }}
    Pose {{ translation 0 0 0.004 children [ Shape {{ appearance {grey} geometry Cylinder {{ height 0.008 radius 0.07 }} }} ] }}
    Pose {{ translation 0 -0.28 1 children [ Shape {{ appearance {grey} geometry Box {{ size 0.012 0.56 0.012 }} }} ] }}
    Camera {{
      translation 0 -0.56 0.985
      rotation 0 1 0 1.5708
      children [ Pose {{ translation -0.012 0 0 children [ Shape {{ appearance {matte('0.08 0.08 0.09', 0.4)} geometry Box {{ size 0.03 0.07 0.03 }} }} ] }} ]
      name "overhead camera"
      fieldOfView 1.2
      width 320
      height 240
    }}
  ]
  name "overhead_tracker"
  controller "hamster_supervisor"
  supervisor TRUE
}}""")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
