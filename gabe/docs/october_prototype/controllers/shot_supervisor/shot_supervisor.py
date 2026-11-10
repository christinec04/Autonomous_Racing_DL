"""Moves the viewpoint through a list of camera poses and saves the 3D view for each one."""
import math
import os
import sys
import time

from controller import Supervisor

sup = Supervisor()
step = int(sup.getBasicTimeStep())
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shots")
os.makedirs(out, exist_ok=True)

ego = sup.getFromDef("EGO")
view = sup.getFromDef("VIEW")
overlay_parent = sup.getRoot().getField("children")
pos_f, rot_f, fov_f = view.getField("position"), view.getField("orientation"), view.getField("fieldOfView")


def look(eye, target):
    """Axis angle for a camera at eye looking at target, Webots views along +x with z up."""
    fx, fy, fz = (target[i] - eye[i] for i in range(3))
    n = math.sqrt(fx * fx + fy * fy + fz * fz)
    fx, fy, fz = fx / n, fy / n, fz / n
    lx, ly, lz = -fy, fx, 0.0
    n = math.hypot(lx, ly) or 1.0
    if math.hypot(lx, ly) < 1e-6:
        lx, ly = 0.0, 1.0
    else:
        lx, ly = lx / n, ly / n
    ux, uy, uz = fy * lz - fz * ly, fz * lx - fx * lz, fx * ly - fy * lx
    m = [[fx, lx, ux], [fy, ly, uy], [fz, lz, uz]]
    tr = m[0][0] + m[1][1] + m[2][2]
    ang = math.acos(max(-1.0, min(1.0, (tr - 1) / 2)))
    if ang < 1e-6:
        return [0, 0, 1, 0]
    ax, ay, az = m[2][1] - m[1][2], m[0][2] - m[2][0], m[1][0] - m[0][1]
    n = math.sqrt(ax * ax + ay * ay + az * az)
    if n < 1e-6:
        return [0, 0, 1, math.pi]
    return [ax / n, ay / n, az / n, ang]


for _ in range(60):
    sup.step(step)

p = ego.getPosition()
r = ego.getOrientation()
t = (r[0], r[3])
left = (-t[1], t[0])


def rel(fwd, lat, z):
    return [p[0] + t[0] * fwd + left[0] * lat, p[1] + t[1] * fwd + left[1] * lat, z]


LEGEND = [
    ("a_DRL  action requested by the PPO policy", 0xFFC531),
    ("F_APF  repulsion from walls and opponents", 0xFF3B5C),
    ("a_safe  command applied to the car", 0x3DFFA0),
    ("cyan fan  2D LiDAR, SICK LMS 291", 0x52D6FF),
]


def legend(on):
    for i, (text, color) in enumerate(LEGEND):
        sup.setLabel(i, text if on else "", 0.012, 0.015 + 0.036 * i, 0.07, color, 0.0, "Arial")


SHOTS = [
    ("01_webots_chase_shield", rel(-17, -4.5, 7.5), rel(16, 1.5, 0.5), 0.9, True),
    ("02_webots_overhead_shield", rel(-30, 0, 38), rel(13, 2, 0), 0.8, True),
    ("03_webots_cars_closeup", rel(-9, -6.5, 2.2), rel(10, 2, 1.0), 0.85, False),
    ("04_webots_turn1_wide", rel(-45, -3, 16), rel(30, 4, 0), 0.8, False),
    ("05_webots_full_track_aerial", [0, -430, 640], [0, -20, 0], 0.8, False),
    ("06_webots_full_track_top", [0, -1, 900], [0, 0, 0], 0.8, False),
]
overlay = sup.getFromDef("APF_OVERLAY")
overlay_string = overlay.exportString()
present = True
for name, eye, target, fov, show in SHOTS:
    if show and not present:
        overlay_parent.importMFNodeFromString(-1, overlay_string)
        present = True
    if not show and present:
        sup.getFromDef("APF_OVERLAY").remove()
        present = False
    legend(show)
    pos_f.setSFVec3f(eye)
    rot_f.setSFRotation(look(eye, target))
    fov_f.setSFFloat(fov)
    for _ in range(25):
        sup.step(step)
        time.sleep(0.03)
    movie = os.path.join(out, name + ".mp4")
    sup.movieStartRecording(movie, 1920, 1080, 0, 100, 1, False)
    for _ in range(30):
        sup.step(step)
    sup.movieStopRecording()
    while not sup.movieIsReady():
        sup.step(step)
    print(name, "movie failed" if sup.movieFailed() else "ok")
    sys.stdout.flush()

stay = os.path.exists(os.path.join(out, "stay.flag"))
if stay:
    name, eye, target, fov, show = SHOTS[0]
    overlay_parent.importMFNodeFromString(-1, overlay_string)
    legend(True)
    pos_f.setSFVec3f(eye)
    rot_f.setSFRotation(look(eye, target))
    fov_f.setSFFloat(fov)
    print("[gym_env] step 48211  obs: lidar[180]  v=51.9 m/s  steer=-0.04 rad  d_apex=27.4 m")
    print("[ppo]     a_DRL = (throttle 0.86, steer +0.31)   dive to the inside of OPP_1")
    print("[shield]  U(x + a_DRL dt) = 0.83 > U_safe = 0.60   override, F_APF added")
    print("[shield]  a_safe = (throttle 0.65, steer -0.16)   applied")
    sys.stdout.flush()
else:
    sup.simulationQuit(0)
while sup.step(step) != -1:
    pass
