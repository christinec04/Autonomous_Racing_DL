"""Measure the f1tenth car like runs/probe measured the Webots car.

  brake    straight line, a fixed deceleration command for 1 s, achieved deceleration and wheel lock
  skidpad  hold speed, ramp the steering slowly, peak lateral acceleration and the understeer gradient K_US
  combined hold a corner at 60 % of the peak lateral acceleration and brake, the friction circle in action
Writes runs/f1tenth/calib.json.
"""
import json
import math
import os

import numpy as np

import sys

import bridge
import vehicle
from f1t_backend import F1tBackend

OUT = os.path.join(bridge.HERE, "..", "runs", "f1tenth")


def straight(b, v):
    b.reset((0.0, 60.0, 0.0, v), [])


def run(b, seconds, accel, delta, log=None):
    """Raw gym inputs, accel in m/s^2 and a target road wheel angle."""
    a = b.sim.agents[0]
    u = np.zeros((b.n, 2))
    for _ in range(int(seconds / b.dt)):
        x = a.state
        u[0, 0] = max(-vehicle.STEER_RATE, min(vehicle.STEER_RATE, 40.0 * (delta(x) - x[2])))
        u[0, 1] = accel(x)
        b.sim.step(u)
        if log is not None:
            log.append(x.copy())


def body_vel(x):
    if x.shape[1] == 29:
        return x[:, 3], x[:, 10]
    return x[:, 3] * np.cos(x[:, 6]), x[:, 3] * np.sin(x[:, 6])


def lateral_accel(x, dt, win=25):
    """Body frame lateral acceleration from the world frame velocity, smoothed over win steps."""
    c, s = np.cos(x[:, 4]), np.sin(x[:, 4])
    vx, vy = body_vel(x)
    vxw, vyw = vx * c - vy * s, vx * s + vy * c
    axw, ayw = np.gradient(vxw, dt), np.gradient(vyw, dt)
    a = -axw * s + ayw * c
    return np.convolve(a, np.ones(win) / win, "same")


def main():
    os.makedirs(OUT, exist_ok=True)
    model = sys.argv[1] if len(sys.argv) > 1 else "stp"
    b = F1tBackend(bridge.make_track(), n_cars=1, dt=0.004, substeps=1, model=model)
    b.sim.agents[0].check_ttc = lambda scan: False   # open plane, no walls
    g = vehicle.MU * 9.81
    res = {"brake": [], "skidpad": [], "combined": [], "throttle": []}
    for v in (20.0, 40.0):
        for dec in (5.0, 10.0, 14.0, 18.0, 25.0):
            straight(b, v)
            run(b, 0.3, lambda x: 0.0, lambda x: 0.0)
            v0 = b.sim.agents[0].state[3]
            log = []
            run(b, 0.8, lambda x, d=dec: -d, lambda x: 0.0, log)
            x = np.array(log)
            v1 = x[-1, 3]
            lock = float(np.min(x[:, 23:27] * vehicle.P["R_w"] / np.maximum(x[:, 3:4], 1.0))) if model == "mb" else None
            res["brake"].append({"v": v, "cmd": dec, "decel": (v0 - v1) / 0.8, "min_wheel_ratio": lock,
                                 "yaw_rate_max": float(np.abs(x[:, 5]).max())})
            print(f"brake v={v} cmd={dec} got {(v0 - v1) / 0.8:.2f} wheel ratio {lock}")
    pads = {}
    for v in (15.0, 30.0, 45.0):
        straight(b, v)
        log = []
        hold = lambda x, v=v: 3.0 * (v - x[3])
        run(b, 10.0, hold, lambda x: min(0.25, 0.0005 + 0.02 * (len(log) * b.dt)), log)
        x = np.array(log)
        a_lat = lateral_accel(x, b.dt)
        vx, vy = body_vel(x)
        beta = np.degrees(np.arctan2(vy, np.maximum(vx, 1)))
        lost = np.nonzero(np.abs(beta) > 8)[0]
        ok = (np.abs(x[:, 3] - v) < 0.1 * v) & (np.arange(len(x)) < (lost[0] if len(lost) else len(x)))
        k = int(np.argmax(np.where(ok, np.abs(a_lat), 0)))
        lin = ok & (np.abs(a_lat) > 0.15 * g) & (np.abs(a_lat) < 0.6 * g)
        kus = float(np.median((x[lin, 3] ** 2 * np.tan(x[lin, 2]) / a_lat[lin] - vehicle.WHEELBASE) / x[lin, 3] ** 2)) if lin.any() else None
        pads[v] = (x, a_lat)
        res["skidpad"].append({"v": v, "ay_peak": float(abs(a_lat[k])), "ay_peak_over_mu_g": float(abs(a_lat[k]) / g),
                               "delta_at_peak": float(x[k, 2]), "beta_at_peak_deg": float(beta[k]), "K_US": kus,
                               "spin_at_delta": float(x[lost[0], 2]) if len(lost) else None})
        print(f"skidpad v={v} peak ay {abs(a_lat[k]):.2f} = {abs(a_lat[k]) / g:.2f} mu g at delta {x[k, 2]:.3f} "
              f"beta {beta[k]:.1f} K_US {kus} spin at delta {res['skidpad'][-1]['spin_at_delta']}")
    for v in (30.0,):
        x, a_lat = pads[v]
        peak = [r for r in res["skidpad"] if r["v"] == v][0]
        j = int(np.argmax(np.abs(a_lat) > 0.6 * peak["ay_peak"]))
        delta = float(x[j, 2])
        for dec in (4.0, 8.0, 12.0, 18.0):
            straight(b, v)
            run(b, 2.5, lambda x, v=v: 3.0 * (v - x[3]), lambda x: delta)
            log = []
            run(b, 0.6, lambda x, d=dec: -d, lambda x: delta, log)
            x = np.array(log)
            ay = np.abs(lateral_accel(x, b.dt))
            vx, vy = body_vel(x)
            beta = np.degrees(np.arctan2(vy, np.maximum(vx, 1)))
            dec_got = float((x[0, 3] - x[-1, 3]) / 0.6)
            res["combined"].append({"v": v, "ay0": float(ay[5]), "brake_cmd": dec, "ay_mean": float(ay[20:].mean()),
                                    "decel": dec_got, "beta_max_deg": float(np.abs(beta).max()),
                                    "combined_over_mu_g": float(math.hypot(ay[20:].mean(), dec_got) / g)})
            print(f"combined v={v} ay0 {ay[5]:.1f} brake {dec} -> ay {ay[20:].mean():.1f} decel {dec_got:.1f} "
                  f"beta max {np.abs(beta).max():.1f} total/mu g {res['combined'][-1]['combined_over_mu_g']:.2f}")
    for v in (5.0, 15.0, 30.0, 50.0):
        straight(b, v)
        log = []
        run(b, 0.5, lambda x: 25.0, lambda x: 0.0, log)
        x = np.array(log)
        res["throttle"].append({"v": v, "accel": float((x[-1, 3] - x[0, 3]) / 0.5)})
        print(f"full throttle v={v} accel {(x[-1, 3] - x[0, 3]) / 0.5:.2f}")
    with open(os.path.join(OUT, f"calib_{model}.json"), "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
