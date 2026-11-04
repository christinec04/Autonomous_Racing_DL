"""Step 1 check: can classical controllers lap the track? How fast is the sim?"""
import sys, time, numpy as np
from racing.tires import set_tire_model
TIRE = sys.argv[1] if len(sys.argv) > 1 else 'saturated'
set_tire_model(TIRE)
from racing.tires import set_traction_control
TCS = (sys.argv[2] if len(sys.argv) > 2 else 'tcs') == 'tcs'
set_traction_control(TCS)
print('tcs', TCS)
print('tire model:', TIRE)
from racing.sim import make_f110, Centerline
from racing.controllers import PurePursuit, PIDFollower
cl = Centerline.load()
s0 = 5.0
for name, ctor in [("pure_pursuit", lambda: PurePursuit(cl)), ("pid", lambda: PIDFollower(cl, 0.01))]:
    for scale in [0.7, 0.85, 0.95, 1.0, 1.1]:
        env = make_f110(1)
        c = ctor(); c.profile *= scale
        env.reset(options={"poses": cl.pose_at(s0)[None]})
        prog, prev_s, crash, maxv, lap_marks = 0.0, s0, False, 0, []
        maxd = 0; maxslip = 0
        for k in range(8000):
            st = env.unwrapped.sim.agents[0].state
            steer, v = c.act(st[0], st[1], st[4], st[3])
            obs, *_ = env.step(np.array([[steer, v]]))
            _, s, d, _ = cl.project(st[0], st[1], c.hint)
            ds = (s - prev_s + cl.length / 2) % cl.length - cl.length / 2
            prog += ds; prev_s = s; maxd = max(maxd, abs(d))
            if prog >= cl.length * (len(lap_marks) + 1): lap_marks.append(k * 0.01)
            maxv = max(maxv, st[3]); maxslip = max(maxslip, abs(st[6]))
            if obs["collisions"][0]: crash = True; break
            if len(lap_marks) >= 2: break
        lt = np.diff([0] + lap_marks)
        print(f"{name:13s} scale={scale:.2f} crash={crash} laps={len(lap_marks)} lap_times={np.round(lt,2)} max_slip={np.degrees(maxslip):.0f}deg "
              f"vmax={maxv:.1f} max|d|={maxd:.2f}")
