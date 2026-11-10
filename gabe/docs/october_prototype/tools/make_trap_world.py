"""Generate worlds/apf_trap.wbt, a TurtleBot3 Burger stuck in a U shaped obstacle on the way to its goal."""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "worlds", "apf_trap.wbt")
BASE = "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/"
PROTOS = [
    "objects/backgrounds/protos/TexturedBackground.proto",
    "objects/backgrounds/protos/TexturedBackgroundLight.proto",
    "objects/floors/protos/RectangleArena.proto",
    "objects/factory/containers/protos/WoodenBox.proto",
    "robots/robotis/turtlebot/protos/TurtleBot3Burger.proto",
]
START, ROBOT, GOAL = (-2.3, 0.0), (0.28, 0.0), (2.3, 0.0)
# wall boxes as (centre x, centre y, size x, size y)
WALLS = [(0.65, 0, 0.1, 1.5), (0.1, 0.7, 1.2, 0.1), (0.1, -0.7, 1.2, 0.1)]
BOXES = [(-1.3, 1.1), (-1.0, -1.2), (1.6, -1.0), (1.5, 1.35)]


def emissive(col, tr=0):
    return f"PBRAppearance {{ baseColor {col} emissiveColor {col} transparency {tr} roughness 1 metalness 0 }}"


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


def dots(points, col, name, spacing=0.09, radius=0.022):
    out, carry, first = [], 0.0, True
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        d = carry
        while d < L:
            x, y = x1 + (x2 - x1) * d / L, y1 + (y2 - y1) * d / L
            shape = f"DEF {name} Shape {{ appearance {emissive(col)} geometry Cylinder {{ height 0.004 radius {radius} }} castShadows FALSE }}" if first else f"USE {name}"
            first = False
            out.append(f"    Pose {{ translation {x:.4f} {y:.4f} 0.004 children [ {shape} ] }}")
            d += spacing
        carry = d - L
    return "\n".join(out)


def blocked(x, y):
    for cx, cy, sx, sy in WALLS:
        if abs(x - cx) < sx / 2 and abs(y - cy) < sy / 2:
            return True
    for bx, by in BOXES:
        if abs(x - bx) < 0.15 and abs(y - by) < 0.15:
            return True
    return abs(x) > 3 or abs(y) > 2


def main():
    w = ["#VRML_SIM R2025a utf8", ""] + [f'EXTERNPROTO "{BASE}{p}"' for p in PROTOS]
    w.append("""
WorldInfo {
  info [
    "Escaping local minima, a hybrid APF and deep reinforcement learning local navigator"
    "The TurtleBot3 Burger follows the potential field until it stalls in the U shaped obstacle, then a PPO agent drives it out."
  ]
  title "APF local minimum trap"
  basicTimeStep 16
}
DEF VIEW Viewpoint {
  orientation 0 0 1 0
  position -4 0 2
}
TexturedBackground {
}
TexturedBackgroundLight {
}
RectangleArena {
  floorSize 6 4
  floorTileSize 0.5 0.5
  wallHeight 0.15
}""")
    for k, (cx, cy, sx, sy) in enumerate(WALLS):
        w.append(f"""DEF TRAP_WALL_{k} Solid {{
  translation {cx} {cy} 0.11
  children [ Shape {{ appearance PBRAppearance {{ baseColor 0.82 0.83 0.86 roughness 0.8 metalness 0 }} geometry DEF WALL_{k} Box {{ size {sx} {sy} 0.22 }} }} ]
  name "trap wall {k}"
  boundingObject USE WALL_{k}
}}""")
    for k, (x, y) in enumerate(BOXES):
        w.append(f'WoodenBox {{ translation {x} {y} 0.15 size 0.3 0.3 0.3 name "box {k}" }}')
    w.append(f"""DEF GOAL Pose {{
  translation {GOAL[0]} {GOAL[1]} 0
  children [
    Pose {{ translation 0 0 0.003 children [ Shape {{ appearance {emissive('0.1 0.9 0.4', 0.35)} geometry Cylinder {{ height 0.004 radius 0.22 }} castShadows FALSE }} ] }}
    Pose {{ translation 0 0 0.2 children [ Shape {{ appearance PBRAppearance {{ baseColor 0.9 0.9 0.9 roughness 0.5 metalness 0 }} geometry Cylinder {{ height 0.4 radius 0.008 }} }} ] }}
    Pose {{ translation 0.07 0 0.35 children [ Shape {{ appearance {emissive('0.1 0.9 0.4')} geometry Box {{ size 0.14 0.004 0.09 }} }} ] }}
  ]
}}
DEF ROBOT TurtleBot3Burger {{
  translation {ROBOT[0]} {ROBOT[1]} 0
  rotation 0 0 1 0
  name "TurtleBot3Burger"
  controller "hybrid_apf_drl"
}}""")

    rx, ry = ROBOT
    ov = ["DEF APF_OVERLAY Group {", "  children ["]
    # path the potential field drove, straight at the goal and into the trap
    ov.append(dots([START, (rx - 0.1, ry)], "0.25 0.5 1", "DOT_APF"))
    # escape driven by the PPO agent, then the potential field takes over again
    turn = [(-0.45 - 0.5 * math.sin(math.radians(a)), 0.5 - 0.5 * math.cos(math.radians(a))) for a in range(15, 181, 15)]
    escape = [(rx - 0.1, 0.0), (-0.45, 0.0)] + turn + [(0.55, 1.0), (0.95, 0.95)]
    ov.append(dots(escape, "1 0.77 0.1", "DOT_DRL"))
    ov.append(dots([(0.95, 0.95), (1.5, 0.62), GOAL], "0.25 0.5 1", "DOT_APF2"))
    # the two forces that cancel at the local minimum
    ov.append(arrow(rx, ry + 0.035, rx + 0.5, ry + 0.035, 0.23, "0.15 1 0.55", 0.012))
    ov.append(arrow(rx, ry - 0.035, rx - 0.5, ry - 0.035, 0.23, "1 0.15 0.3", 0.012))
    # LDS-01 scan, 360 degrees out to 3.5 m
    coords, idx = [f"{rx} {ry} 0.172,"], []
    for k in range(120):
        a = math.radians(3 * k)
        r = 0.12
        while r < 3.5 and not blocked(rx + math.cos(a) * r, ry + math.sin(a) * r):
            r += 0.01
        coords.append(f"{rx + math.cos(a) * r:.3f} {ry + math.sin(a) * r:.3f} 0.172,")
        idx.append(f"0 {k + 1} -1")
    ov.append(f"""    Shape {{
      appearance Appearance {{ material Material {{ diffuseColor 0.3 0.85 1 emissiveColor 0.3 0.85 1 }} }}
      geometry IndexedLineSet {{ coord Coordinate {{ point [ {' '.join(coords)} ] }} coordIndex [ {' '.join(idx)} ] }}
      castShadows FALSE
    }}""")
    ov += ["  ]", "}"]
    w.append("\n".join(ov))
    w.append("""DEF SUPERVISOR Robot {
  name "gym_env_bridge"
  controller "trap_supervisor"
  supervisor TRUE
}""")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
