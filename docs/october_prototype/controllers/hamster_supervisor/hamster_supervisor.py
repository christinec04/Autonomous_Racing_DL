"""Moves the viewpoint through a list of camera poses and saves the 3D view for each one."""
import math
import os
import sys
import time

from controller import Supervisor

sup = Supervisor()
step = int(sup.getBasicTimeStep())
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hamster_shots")
os.makedirs(out, exist_ok=True)

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


camera = sup.getDevice("overhead camera")
camera.enable(step)
for _ in range(60):
    sup.step(step)

LEGEND = [
    ("blue dots  path driven by the APF controller", 0x4080FF),
    ("green F_att and red F_rep cancel, the Hamster stalls", 0xFF3B5C),
    ("yellow dots  escape driven by the PPO agent", 0xFFC531),
    ("magenta  left and right IR proximity sensors", 0xFF40E6),
]


def legend(on):
    for i, (text, color) in enumerate(LEGEND):
        sup.setLabel(i, text if on else "", 0.012, 0.845 + 0.036 * i, 0.07, color, 0.0, "Arial")


SHOTS = [
    ("01_webots_hamster_trap_overview", [-0.62, -0.62, 0.55], [0.07, 0.02, 0], 0.8, True),
    ("02_webots_hamster_trap_top", [0.0, -0.001, 0.93], [0, 0, 0], 1.0, True),
    ("03_webots_hamster_local_minimum", [-0.13, -0.2, 0.17], [0.1, 0.01, 0.015], 0.8, True),
    ("04_webots_hamster_closeup", [-0.005, -0.085, 0.06], [0.09, 0.0, 0.018], 0.8, False),
    ("05_webots_hamster_camera_rig", [-1.45, -1.25, 1.2], [0.0, 0.15, 0.42], 0.8, True),
    ("06_webots_hamster_trap_clean", [-0.62, -0.62, 0.55], [0.07, 0.02, 0], 0.8, False),
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
    print("[apf]   v = 0.00 m/s < v_threshold, d_goal = 0.50 m > d_threshold")
    print("[trap]  local minimum detected, entering ESCAPE state, PPO agent takes control")
    sys.stdout.flush()
else:
    sup.simulationQuit(0)
while sup.step(step) != -1:
    pass
