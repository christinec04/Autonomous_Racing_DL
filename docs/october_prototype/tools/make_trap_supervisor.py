"""Derive controllers/trap_supervisor from the racing shot supervisor, with its own cameras and legend."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "controllers", "shot_supervisor", "shot_supervisor.py"), encoding="utf-8").read()
head = src[:src.index("for _ in range(60):")]
head = head.replace('"shots")', '"trap_shots")').replace('ego = sup.getFromDef("EGO")\n', "")
tail = src[src.index("overlay = sup.getFromDef"):]
a, b = tail.index('    print("[gym_env]'), tail.index("    sys.stdout.flush()\nelse:")
tail = tail[:a] + (
    '    print("[apf]   v = 0.00 m/s < v_threshold, d_goal = 2.02 m > d_threshold")\n'
    '    print("[trap]  local minimum detected, entering ESCAPE state, PPO agent takes control")\n'
) + tail[b:]
mid = '''for _ in range(60):
    sup.step(step)

LEGEND = [
    ("blue dots  path driven by the APF controller", 0x4080FF),
    ("green F_att and red F_rep cancel, the robot stalls", 0xFF3B5C),
    ("yellow dots  escape driven by the PPO agent", 0xFFC531),
    ("cyan  LDS-01 2D LiDAR scan", 0x52D6FF),
]


def legend(on):
    for i, (text, color) in enumerate(LEGEND):
        sup.setLabel(i, text if on else "", 0.012, 0.015 + 0.036 * i, 0.07, color, 0.0, "Arial")


SHOTS = [
    ("01_webots_trap_overview", [-2.6, -2.3, 2.3], [0.35, 0.1, 0], 0.8, True),
    ("02_webots_trap_top", [0, -0.01, 5.6], [0, 0, 0], 0.8, True),
    ("03_webots_trap_local_minimum", [-0.75, -0.85, 0.75], [0.4, 0.05, 0.08], 0.8, True),
    ("04_webots_turtlebot_closeup", [-0.2, -0.5, 0.32], [0.3, 0.02, 0.08], 0.8, False),
    ("05_webots_trap_clean", [-2.6, -2.3, 2.3], [0.35, 0.1, 0], 0.8, False),
]
'''
out = os.path.join(HERE, "..", "controllers", "trap_supervisor")
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "trap_supervisor.py"), "w", encoding="utf-8").write(head + mid + tail)
print("ok")
