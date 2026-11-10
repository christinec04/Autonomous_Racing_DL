"""Generate worlds/street_circuit.wbt, a Singapore styled street circuit with five BMW X5 cars."""
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "worlds", "street_circuit.wbt")
BASE = "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/"
PROTOS = [
    "objects/backgrounds/protos/TexturedBackground.proto",
    "objects/backgrounds/protos/TexturedBackgroundLight.proto",
    "objects/road/protos/Road.proto",
    "objects/buildings/protos/SimpleBuilding.proto",
    "objects/traffic/protos/StreetLight.proto",
    "vehicles/protos/bmw/BmwX5.proto",
    "devices/sick/protos/SickLms291.proto",
]

CORNERS = [
    (-300, 150), (40, 150), (80, 100), (40, 60), (120, 20), (300, 20), (330, -40), (250, -60),
    (250, -150), (120, -150), (120, -90), (40, -90), (40, -160), (-120, -160), (-140, -100),
    (-240, -100), (-240, -170), (-330, -170), (-330, -40), (-250, -40), (-250, 40), (-330, 40),
]
WIDTH, HALF = 14.0, 7.0


def build_track():
    n = len(CORNERS)

    def cut(i):
        v, a, b = CORNERS[i], CORNERS[i - 1], CORNERS[(i + 1) % n]
        la, lb = math.dist(v, a), math.dist(v, b)
        c = min(24, 0.45 * la, 0.45 * lb)
        A = (v[0] - (v[0] - a[0]) / la * c, v[1] - (v[1] - a[1]) / la * c)
        B = (v[0] + (b[0] - v[0]) / lb * c, v[1] + (b[1] - v[1]) / lb * c)
        return A, v, B

    raw, corner_s, acc = [], {}, 0.0

    def push(x, y):
        nonlocal acc
        if raw:
            acc += math.hypot(x - raw[-1][0], y - raw[-1][1])
        raw.append((x, y, acc))

    for i in range(n):
        _, _, b0 = cut(i)
        a1, v1, b1 = cut((i + 1) % n)
        for k in range(50):
            t = k / 50
            push(b0[0] + (a1[0] - b0[0]) * t, b0[1] + (a1[1] - b0[1]) * t)
        corner_s[(i + 1) % n] = acc
        for k in range(50):
            t = k / 50
            u = 1 - t
            push(u * u * a1[0] + 2 * u * t * v1[0] + t * t * b1[0], u * u * a1[1] + 2 * u * t * v1[1] + t * t * b1[1])
    total = acc + math.hypot(raw[0][0] - raw[-1][0], raw[0][1] - raw[-1][1])
    count = round(total / 2)
    pts, j = [], 0
    for k in range(count):
        s = k * total / count
        while j < len(raw) - 2 and raw[j + 1][2] < s:
            j += 1
        a, b = raw[j], raw[j + 1]
        t = min(1.0, (s - a[2]) / max(1e-6, b[2] - a[2]))
        # flip y so the layout matches the plan view in a z up world
        pts.append({"x": a[0] + (b[0] - a[0]) * t, "y": -(a[1] + (b[1] - a[1]) * t), "s": s})
    N = len(pts)
    for i, p in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % N]
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        L = math.hypot(dx, dy)
        p["tx"], p["ty"] = dx / L, dy / L
        p["nx"], p["ny"] = -p["ty"], p["tx"]  # left of travel
    for i, p in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % N]
        d = math.atan2(b["ty"], b["tx"]) - math.atan2(a["ty"], a["tx"])
        d = (d + math.pi) % (2 * math.pi) - math.pi
        p["k"] = d / 4.0
    for i, p in enumerate(pts):
        p["ks"] = sum(pts[(i + j) % N]["k"] for j in range(-6, 7)) / 13
    return pts, total, corner_s


PTS, LEN, CORNER_S = build_track()
N = len(PTS)


def pose(s, lat):
    p = PTS[int(round((s % LEN) / LEN * N)) % N]
    return {"x": p["x"] + p["nx"] * lat, "y": p["y"] + p["ny"] * lat, "tx": p["tx"], "ty": p["ty"],
            "nx": p["nx"], "ny": p["ny"], "yaw": math.atan2(p["ty"], p["tx"])}


def nearest(x, y):
    best = min(PTS, key=lambda p: (p["x"] - x) ** 2 + (p["y"] - y) ** 2)
    return best, (x - best["x"]) * best["nx"] + (y - best["y"]) * best["ny"]


S0 = CORNER_S[1] - 22
# lateral offsets are positive to the left of travel. Turn 1 is a left hander.
CARS = [
    ("EGO", S0, -0.6, (0.95, 0.35, 0.02)),
    ("OPP_1", S0 + 12.5, 3.3, (0.05, 0.2, 0.85)),
    ("OPP_2", S0 + 36, -2.4, (0.45, 0.1, 0.75)),
    ("OPP_3", S0 + 58, 0.8, (0.85, 0.87, 0.9)),
    ("OPP_4", S0 - 26, 2.0, (0.9, 0.75, 0.05)),
]
CARS = [dict(name=n, color=c, **pose(s, lat)) for n, s, lat, c in CARS]
EGO = CARS[0]


def f(v):
    return f"{v:.4g}" if abs(v) >= 1e-4 else "0"


def arrow(x1, y1, x2, y2, z, color, radius):
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    head = radius * 7
    rot = f"{f(-uy)} {f(ux)} 0 1.5708"
    app = f"PBRAppearance {{ baseColor {color} emissiveColor {color} roughness 1 metalness 0 }}"
    sx, sy = x1 + ux * (L - head) / 2, y1 + uy * (L - head) / 2
    hx, hy = x1 + ux * (L - head / 2), y1 + uy * (L - head / 2)
    return f"""    Pose {{ translation {f(sx)} {f(sy)} {z} rotation {rot} children [ Shape {{ appearance {app} geometry Cylinder {{ height {f(L - head)} radius {radius} }} castShadows FALSE }} ] }}
    Pose {{ translation {f(hx)} {f(hy)} {z} rotation {rot} children [ Shape {{ appearance {app} geometry Cone {{ height {f(head)} bottomRadius {f(radius * 2.6)} }} castShadows FALSE }} ] }}
"""


def strip(points_a, points_b, z, color, transparency):
    coords = " ".join(f"{f(x)} {f(y)} {z}," for x, y in points_a + points_b)
    m = len(points_a)
    idx = " ".join(f"{i} {i + 1} {m + i + 1} {m + i} -1" for i in range(m - 1))
    return f"""    Shape {{
      appearance PBRAppearance {{ baseColor {color} emissiveColor {color} transparency {transparency} roughness 1 metalness 0 }}
      geometry IndexedFaceSet {{ coord Coordinate {{ point [ {coords} ] }} coordIndex [ {idx} ] }}
      castShadows FALSE
    }}
"""


def main():
    random.seed(4)
    w = ["#VRML_SIM R2025a utf8", ""]
    w += [f'EXTERNPROTO "{BASE}{p}"' for p in PROTOS]
    w.append("""
WorldInfo {
  info [
    "APF shielded deep reinforcement learning for autonomous racing"
    "Ego BMW X5 is driven by a PPO policy, the artificial potential field shield overrides unsafe actions."
  ]
  title "Singapore styled street circuit"
  basicTimeStep 16
  lineScale 1
}
DEF VIEW Viewpoint {
  orientation 0 0 1 0
  position 0 0 30
  near 1
  far 3000
}
TexturedBackground {
  texture "dusk"
  luminosity 0.55
}
TexturedBackgroundLight {
  texture "dusk"
  luminosity 1.3
  castShadows FALSE
}
DEF GROUND Solid {
  translation 0 0 -0.02
  children [
    Shape {
      appearance PBRAppearance { baseColor 0.16 0.17 0.19 roughness 1 metalness 0 }
      geometry Plane { size 1400 1100 }
    }
  ]
  boundingObject Plane { size 1400 1100 }
  locked TRUE
}""")

    # the circuit itself, one closed Road with crash barriers on both sides
    step = 3
    way = [PTS[i] for i in range(0, N, step)] + [PTS[0]]
    wp = ", ".join(f"{f(p['x'])} {f(p['y'])} 0.01" for p in way)
    w.append(f"""DEF TRACK Road {{
  name "street circuit"
  width {WIDTH}
  numberOfLanes 1
  lines [ ]
  roadBorderHeight 0.2
  roadBorderWidth [ 1.6 ]
  rightBarrier TRUE
  leftBarrier TRUE
  wayPoints [ {wp} ]
  splineSubdivision -1
}}""")

    # start finish line and red white kerbs on the inside of every corner
    sf = pose(S0 - 60, 0)
    w.append(f"""DEF START_LINE Pose {{
  translation {f(sf['x'])} {f(sf['y'])} 0.025
  rotation 0 0 1 {f(sf['yaw'])}
  children [ Shape {{ appearance PBRAppearance {{ baseColor 1 1 1 roughness 1 metalness 0 }} geometry Box {{ size 0.8 {WIDTH} 0.01 }} castShadows FALSE }} ]
}}""")
    kerbs = ["DEF KERBS Group {", "  children ["]
    first = [True, True]
    for i in range(0, N):
        p = PTS[i]
        if abs(p["ks"]) < 0.012:
            continue
        side = 1 if p["ks"] > 0 else -1
        c = i % 2
        x, y = p["x"] + p["nx"] * side * (HALF - 0.75), p["y"] + p["ny"] * side * (HALF - 0.75)
        if first[c]:
            col = "0.85 0.05 0.05" if c else "0.95 0.95 0.95"
            shape = f"DEF KERB{c} Shape {{ appearance PBRAppearance {{ baseColor {col} roughness 0.9 metalness 0 }} geometry Box {{ size 2.3 1.5 0.05 }} castShadows FALSE }}"
            first[c] = False
        else:
            shape = f"USE KERB{c}"
        kerbs.append(f"    Pose {{ translation {f(x)} {f(y)} 0.02 rotation 0 0 1 {f(math.atan2(p['ty'], p['tx']))} children [ {shape} ] }}")
    kerbs += ["  ]", "}"]
    w.append("\n".join(kerbs))

    # waypoints that feed the APF attraction term
    wps = ["DEF WAYPOINTS Group {", "  children ["]
    for k, s in enumerate(range(0, int(LEN), 10)):
        p = pose(s, 0)
        shape = ("DEF WP Shape { appearance PBRAppearance { baseColor 0.2 0.8 1 emissiveColor 0.2 0.8 1 roughness 1 metalness 0 } "
                 "geometry Cylinder { height 0.02 radius 0.3 } castShadows FALSE }") if k == 0 else "USE WP"
        wps.append(f"    Pose {{ translation {f(p['x'])} {f(p['y'])} 0.03 children [ {shape} ] }}")
    wps += ["  ]", "}"]
    w.append("\n".join(wps))

    # cars from the Webots vehicle library, Ackermann steering
    for c in CARS:
        ego = c["name"] == "EGO"
        sensors = """
  sensorsSlotFront [
    SickLms291 { translation 0.06 0 0 name "lidar2d" }
  ]
  sensorsSlotCenter [
    GPS { }
    InertialUnit { }
  ]""" if ego else ""
        w.append(f"""DEF {c['name']} BmwX5 {{
  translation {f(c['x'])} {f(c['y'])} 0.4
  rotation 0 0 1 {f(c['yaw'])}
  color {c['color'][0]} {c['color'][1]} {c['color'][2]}
  name "{c['name'].lower()}"
  completeInterior FALSE
  controller "{'ego_shielded_ppo' if ego else 'pid_lane_follow'}"{sensors}
}}""")

    # street lights near the scene, kept few because each one is a real spot light
    for k, d in enumerate([-40, -8, 24, 52, 84]):
        side = 1 if k % 2 else -1
        p = pose(S0 + d, side * (HALF + 2.6))
        yaw = p["yaw"] + (-math.pi / 2 if side > 0 else math.pi / 2)
        w.append(f"""StreetLight {{
  translation {f(p['x'])} {f(p['y'])} 0
  rotation 0 0 1 {f(yaw)}
  name "street light {k}"
  intensity 45
}}""")

    # city blocks
    walls = ["glass building", "gray glass building", "blue glass building", "glass highrise", "transparent highrise", "highrise", "windowed building"]
    b = 0
    for gx in range(-420, 430, 42):
        for gy in range(-250, 260, 42):
            x, y = gx + random.uniform(0, 8), gy + random.uniform(0, 8)
            hw, hd = random.uniform(11, 16), random.uniform(11, 16)
            if min(math.hypot(p["x"] - x, p["y"] - y) for p in PTS[::3]) < HALF + 26:
                continue
            r = random.random()
            floors = random.randint(26, 46) if r > 0.86 else random.randint(10, 20) if r > 0.45 else random.randint(4, 8)
            w.append(f"""SimpleBuilding {{
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

    # APF overlay, the same shapes a supervisor would draw at run time
    ov = ["DEF APF_OVERLAY Group {", "  children ["]
    rings = [(11.0, 3.6, "0.55 0.15 0.65", 0.8), (7.6, 2.6, "0.95 0.15 0.4", 0.74), (4.4, 1.7, "1 0.55 0.15", 0.66)]
    for c in CARS[1:]:
        for k, (a, bb, col, tr) in enumerate(rings):
            ov.append(f"""    Transform {{ translation {f(c['x'] + c['tx'])} {f(c['y'] + c['ty'])} {0.035 + 0.006 * k} rotation 0 0 1 {f(c['yaw'])} scale {a} {bb} 1 children [ Shape {{ appearance PBRAppearance {{ baseColor {col} emissiveColor {col} transparency {tr} roughness 1 metalness 0 }} geometry Cylinder {{ height 0.004 radius 1 subdivision 48 }} castShadows FALSE }} ] }}""")
    i0 = int(round((S0 % LEN) / LEN * N))
    for side in (-1, 1):
        seg = [PTS[(i0 + d) % N] for d in range(-30, 46)]
        outer = [(p["x"] + p["nx"] * side * (HALF - 0.05), p["y"] + p["ny"] * side * (HALF - 0.05)) for p in seg]
        inner = [(p["x"] + p["nx"] * side * (HALF - 1.3), p["y"] + p["ny"] * side * (HALF - 2.4)) for p in seg]
        ov.append(strip(outer, inner, 0.03, "1 0.1 0.2", 0.78))
    # the three action vectors
    ang = math.radians(23)
    L = 15.0
    drl = ((EGO["tx"] * math.cos(ang) + EGO["nx"] * math.sin(ang)) * L, (EGO["ty"] * math.cos(ang) + EGO["ny"] * math.sin(ang)) * L)
    o = CARS[1]
    dx, dy = EGO["x"] - o["x"], EGO["y"] - o["y"]
    lx, ly = dx * o["tx"] + dy * o["ty"], dx * o["nx"] + dy * o["ny"]
    gx, gy = lx / 100.0, ly / (3.6 ** 2)
    gn = math.hypot(gx, gy)
    R = 8.5
    apf = ((o["tx"] * gx + o["nx"] * gy) / gn * R, (o["ty"] * gx + o["ny"] * gy) / gn * R)
    z = 2.5
    ex, ey = EGO["x"], EGO["y"]
    ov.append(arrow(ex, ey, ex + drl[0], ey + drl[1], z, "1 0.77 0.1", 0.2))
    ov.append(arrow(ex + drl[0], ey + drl[1], ex + drl[0] + apf[0], ey + drl[1] + apf[1], z, "1 0.15 0.3", 0.2))
    ov.append(arrow(ex, ey, ex + drl[0] + apf[0], ey + drl[1] + apf[1], z, "0.15 1 0.55", 0.26))
    # LiDAR fan, 180 degrees ahead of the front bumper like the SICK LMS 291
    fx, fy = ex + EGO["tx"] * 3.9, ey + EGO["ty"] * 3.9
    coords, idx = [f"{f(fx)} {f(fy)} 0.75,"], []
    for k in range(61):
        a = EGO["yaw"] + math.radians(-90 + 3 * k)
        r = 1.0
        while r < 40:
            px, py = fx + math.cos(a) * r, fy + math.sin(a) * r
            _, lat = nearest(px, py)
            hit = abs(lat) > HALF
            for c in CARS[1:]:
                qx, qy = px - c["x"] - c["tx"] * 1.4, py - c["y"] - c["ty"] * 1.4
                if abs(qx * c["tx"] + qy * c["ty"]) < 2.4 and abs(qx * c["nx"] + qy * c["ny"]) < 1.0:
                    hit = True
            if hit:
                break
            r += 0.25
        coords.append(f"{f(fx + math.cos(a) * r)} {f(fy + math.sin(a) * r)} 0.75,")
        idx.append(f"0 {k + 1} -1")
    ov.append(f"""    Shape {{
      appearance Appearance {{ material Material {{ diffuseColor 0.3 0.85 1 emissiveColor 0.3 0.85 1 }} }}
      geometry IndexedLineSet {{ coord Coordinate {{ point [ {' '.join(coords)} ] }} coordIndex [ {' '.join(idx)} ] }}
      castShadows FALSE
    }}
""")
    ov += ["  ]", "}"]
    w.append("\n".join(ov))

    w.append("""DEF SUPERVISOR Robot {
  name "gym_env_bridge"
  controller "shot_supervisor"
  supervisor TRUE
}""")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")
    print(f"track {LEN:.0f} m, {N} points, {b} buildings, ego at ({EGO['x']:.1f}, {EGO['y']:.1f}) yaw {EGO['yaw']:.2f}")


if __name__ == "__main__":
    main()
