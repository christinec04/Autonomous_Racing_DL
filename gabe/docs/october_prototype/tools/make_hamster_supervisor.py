"""Derive controllers/hamster_supervisor from the racing shot supervisor, with its own cameras and legend."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "controllers", "shot_supervisor", "shot_supervisor.py"), encoding="utf-8").read()
head = src[:src.index("for _ in range(60):")]
head = head.replace('"shots")', '"hamster_shots")').replace('ego = sup.getFromDef("EGO")\n', "")
tail = src[src.index("overlay = sup.getFromDef"):]
a, b = tail.index('    print("[gym_env]'), tail.index("    sys.stdout.flush()\nelse:")
tail = tail[:a] + (
    '    print("[apf]   v = 0.00 m/s < v_threshold, d_goal = 0.50 m > d_threshold")\n'
    '    print("[trap]  local minimum detected, entering ESCAPE state, PPO agent takes control")\n'
) + tail[b:]
mid = '''camera = sup.getDevice("overhead camera")
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
'''
out = os.path.join(HERE, "..", "controllers", "hamster_supervisor")
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "hamster_supervisor.py"), "w", encoding="utf-8").write(head + mid + tail)
print("ok")
