"""Compare the shield's internal prediction model with the F1TENTH dynamic model."""
import sys, numpy as np
from racing.tires import set_tire_model
set_tire_model(sys.argv[1] if len(sys.argv)>1 else 'saturated')
from racing.sim import make_f110, Centerline
from racing.shield import APFShield, ShieldConfig, available_decel
cl = Centerline.load()
sh = APFShield(ShieldConfig(mode="conditioned", use_map=False), 0.04)
env = make_f110(1)
for v0, steer, vcmd in [(4, -0.42, 0), (4, -0.42, 4), (8, -0.42, 0), (8, -0.2, 8), (12, -0.1, 12), (12, 0.0, 0), (12, -0.42, 0)]:
    env.reset(options={"poses": np.array([[0.0, -100.0, 0.0]])})  # far from walls? use open area check below
    a = env.unwrapped.sim.agents[0]
    a.state[:] = 0; a.state[0] = 30; a.state[1] = 0.0; a.state[3] = v0; a.state[2] = 0.0
    a.steer_buffer = np.empty((0,))
    a.in_collision = False
    traj = []
    for k in range(int(1.0 / 0.01)):
        a.state[:2] = a.state[:2]  # noop
        env.unwrapped.sim.agents[0]._scan_now = False
        env.unwrapped.sim.agents[0]._rays_now = False
        env.unwrapped.sim.step(np.array([[steer, vcmd]]))
        traj.append(a.state[[0, 1, 4, 3, 6]].copy())
    traj = np.array(traj)
    # shield prediction: candidate held for the whole second (commit_time = 1 s)
    sh.cfg.commit_time = 1.0; sh.cfg.max_pred_time = 1.0
    xs = []
    import racing.shield as S
    # re-run prediction loop manually to get the end pose
    x, y, yaw, v, dl = 30.0, 0.0, 0.0, float(v0), 0.0
    for t in range(20):
        dt = 0.05
        acc = np.clip(19.0 * (vcmd - v), -9.51, 9.51) if vcmd < v else min(9.51 / 2 * (vcmd - v), 9.51)
        dl = dl + np.clip(steer - dl, -3.2 * dt, 3.2 * dt)
        v = max(v + acc * dt, 0)
        kap = np.clip(np.tan(dl) / S.WB, -sh.cfg.mu * 9.81 / max(v * v, 1e-3), sh.cfg.mu * 9.81 / max(v * v, 1e-3))
        yaw += v * kap * dt; x += v * np.cos(yaw) * dt; y += v * np.sin(yaw) * dt
    e = traj[-1]
    print(f"v0={v0:4.1f} steer={steer:+.2f} vcmd={vcmd:4.1f} | sim end x={e[0]-30:5.2f} y={e[1]:+5.2f} yaw={np.degrees(e[2]) if e[2]<np.pi else np.degrees(e[2])-360:+6.1f} v={e[3]:4.1f} max|slip|={np.degrees(np.abs(traj[:,4]).max()):4.1f}deg"
          f" | pred x={x-30:5.2f} y={y:+5.2f} yaw={np.degrees(yaw):+6.1f}")
