"""Shield sweep on f1tenth_gym, the same protocol as controllers/shield_test on Webots.

  road  ego pace 0.45, three cars at pace 0.30 ahead, aggression 1.0 and 1.3, half a lap
  race  ego pace 0.95 with dive bomb passes, cars at pace 0.80 0.86 0.92 ahead, aggression 1.0 1.15 1.3, one lap
Shields none, geometric, friction, starts at s = 118, 944, 1248, 1692. The ego and the three opponents are
gym agents on the chosen dynamics, every car is driven by racelib Pilot, the ego command goes through the shield.
Control period 8 ms like the Webots controller, physics 4 ms RK4.

  python sweep.py model=stp tag=stp     results in runs/f1tenth/sweep_<tag>/results.csv, resumes
  python sweep.py model=stp tag=stp_tuned regime=race shields=friction sp=brake_frac:0.6
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np

import bridge
from f1t_backend import F1tBackend
from pilot import CAR_HALF_WIDTH, CAR_LENGTH, REAR_TO_CENTER, Pilot, gap_ahead
from shield import local_lat, make_shield
from track import HALF, grip

A = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
MODEL = A.get("model", "stp")
TAG = A.get("tag", MODEL)
REGIMES = A.get("regime", "road,race").split(",")
SHIELDS = A.get("shields", "none,geometric,friction").split(",")
PACE = {"road": 0.45, "race": float(A.get("race_pace", 0.95))}
AGGR = {"road": [1.0, 1.3], "race": [1.0, 1.15, 1.3]}
STARTS = [float(s) for s in A.get("starts", "118,944,1248,1692").split(",")]
DIST = {"road": 1050.0, "race": 2100.0}
OPP_PACE = {"road": [0.30, 0.30, 0.30], "race": [0.80, 0.86, 0.92]}
OPP_GAP = {"road": [60.0, 300.0, 600.0], "race": [80.0, 300.0, 550.0]}
OPP_LAT = [2.0, -2.0, 1.0]
SPIN_DEG = 25.0
DT, SUB = 0.004, 2
# shield constants retuned for this platform, e.g. sp=brake_frac:0.6 (friction shield only)
SP = {k: float(v) for k, v in (kv.split(":") for kv in A["sp"].split(","))} if A.get("sp") else {}
OUT = os.path.join(bridge.HERE, "..", "runs", "f1tenth", f"sweep_{TAG}")
os.makedirs(OUT, exist_ok=True)

track = bridge.make_track()
b = F1tBackend(track, n_cars=4, dt=DT, substeps=SUB, model=MODEL)


def log(msg):
    with open(os.path.join(OUT, "log.txt"), "a") as fh:
        fh.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def line_pose(s):
    i = track.at(s)
    p, q = track.line[(i - 1) % track.n], track.line[(i + 1) % track.n]
    x, y = track.line[i]
    return float(x), float(y), math.atan2(q[1] - p[1], q[0] - p[0])


def ego_state():
    e = b.ego
    i, s, lat = track.project(e.x, e.y, "ego")
    return {"x": e.x, "y": e.y, "yaw": e.yaw, "vx": e.vx, "vy": e.vy, "speed": e.speed, "i": i, "s": s, "lat": lat}


def box(st):
    c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
    cx, cy = st["x"] + REAR_TO_CENTER * c, st["y"] + REAR_TO_CENTER * s
    h, w = CAR_LENGTH / 2, CAR_HALF_WIDTH
    return [(cx + a * h * c - q * w * s, cy + a * h * s + q * w * c) for a, q in ((1, 1), (1, -1), (-1, -1), (-1, 1))]


def overlap(p, q):
    for poly in (p, q):
        for k in range(4):
            ex, ey = poly[(k + 1) % 4][0] - poly[k][0], poly[(k + 1) % 4][1] - poly[k][1]
            nx, ny = -ey, ex
            a = [nx * x + ny * y for x, y in p]
            c = [nx * x + ny * y for x, y in q]
            if max(a) < min(c) or max(c) < min(a):
                return False
    return True


def crash_check(st, opps):
    """Same rules as shield_test, plus the gym's own collision flags and a blown up integrator."""
    c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
    lat_c, _ = local_lat(track, st["x"] + REAR_TO_CENTER * c, st["y"] + REAR_TO_CENTER * s, st["i"])
    if abs(lat_c) > HALF - CAR_HALF_WIDTH or b.sim.agents[0].in_collision:
        return "wall", lat_c
    if b.blown(0) or (st["speed"] > 8 and abs(math.degrees(math.atan2(st["vy"], max(st["vx"], 0.1)))) > SPIN_DEG):
        return "spin", lat_c
    mine = None
    for o in opps:
        if abs(gap_ahead(track, st["s"], o["s"])) < 8 and abs(o["lat"] - st["lat"]) < 4:
            mine = mine or box(st)
            if overlap(mine, box(o)):
                return "car", lat_c
    return "", lat_c


def episode(regime, kind, aggr, s0):
    pace = PACE[regime]
    pilot = Pilot(track, pace, aggr, dive=(regime == "race"))
    sh = make_shield(kind, track, **(SP if kind == "friction" else {}))
    opps = []
    for k in range(3):
        s = s0 + OPP_GAP[regime][k]
        x, y, _ = track.pose(s, OPP_LAT[k])
        opps.append((x, y, line_pose(s)[2], OPP_PACE[regime][k] * track.v[track.at(s)] * 0.9))
    x, y, yaw = line_pose(s0)
    track._last.clear()
    b.place_all((x, y, yaw, min(pace * aggr, 1.0) * track.v[track.at(s0)] * 0.9), opps, OPP_PACE[regime])
    dt = DT * SUB
    t_sim, travelled, s_prev = 0.0, 0.0, None
    steps = interventions = 0
    reasons, gu_cmd, gu_meas = {}, [], []
    a_meas, outcome, min_clear, slow_t = 0.0, "ok", 99.0, 0.0
    ahead0 = None
    t_limit = 3.0 * DIST[regime] / max(pace * 25.0, 5.0)
    w0 = time.time()
    while True:
        st = ego_state()
        ops = b.opp_states()
        if s_prev is not None:
            travelled += gap_ahead(track, s_prev, st["s"])
        s_prev = st["s"]
        if ahead0 is None:
            ahead0 = [gap_ahead(track, st["s"], o["s"]) > 0 for o in ops]
        why, lat_c = crash_check(st, ops)
        min_clear = min(min_clear, HALF - CAR_HALF_WIDTH - abs(lat_c))
        slow_t = slow_t + dt if st["speed"] < 1.0 else 0.0
        if why:
            outcome = why
            log(f"{regime} {kind} a={aggr} s0={s0} {why} at s={st['s']:.1f} lat={st['lat']:.2f} v={st['speed']:.1f} mode={pilot.mode}")
            break
        if travelled >= DIST[regime]:
            break
        if t_sim > t_limit or slow_t > 5.0:
            outcome = "stall"
            break
        cmd = pilot.act(st, ops, dt)
        steer, throttle, brake, info = sh.filter(st, ops, *cmd)
        b.command(steer, throttle, brake)
        b.step()
        t_sim += dt
        steps += 1
        interventions += info["intervened"]
        if info["intervened"]:
            reasons[info["reason"]] = reasons.get(info["reason"], 0) + 1
        a_meas = 0.9 * a_meas + 0.1 * math.hypot(b.ego.ax, b.ego.ay)
        gu_cmd.append(info["grip_used"])
        gu_meas.append(a_meas / grip(st["speed"]))
    wall = time.time() - w0
    ops = b.opp_states()
    passed = sum(1 for k, o in enumerate(ops) if ahead0 and ahead0[k] and gap_ahead(track, s_prev, o["s"]) < 0)
    gu_cmd, gu_meas = np.array(gu_cmd or [0.0]), np.array(gu_meas or [0.0])
    return {
        "model": MODEL, "regime": regime, "shield": kind, "pace": pace, "aggression": aggr, "s0": s0, "outcome": outcome,
        "crash": int(outcome in ("wall", "spin", "car")), "time": round(t_sim, 3), "distance": round(travelled, 1),
        "lap_time": round(t_sim, 3) if outcome == "ok" else "", "mean_speed": round(travelled / max(t_sim, 1e-3), 2),
        "intervention_rate": round(interventions / max(steps, 1), 4), "reasons": json.dumps(reasons), "passed": passed,
        "min_wall_clearance": round(min_clear, 3), "grip_cmd_p95": round(float(np.percentile(gu_cmd, 95)), 4),
        "grip_meas_p95": round(float(np.percentile(gu_meas, 95)), 4), "steps": steps, "wall_s": round(wall, 2),
        "ctrl_steps_per_s": round(steps / max(wall, 1e-6), 1), "rtf": round(t_sim / max(wall, 1e-6), 2),
    }


def main():
    path = os.path.join(OUT, "results.csv")
    done = set()
    if os.path.exists(path):
        with open(path) as fh:
            done = {(r["regime"], r["shield"], float(r["aggression"]), float(r["s0"])) for r in csv.DictReader(fh)}
    for regime in REGIMES:
        for kind in SHIELDS:
            for aggr in AGGR[regime]:
                for s0 in STARTS:
                    if (regime, kind, aggr, s0) in done:
                        continue
                    r = episode(regime, kind, aggr, s0)
                    new = not os.path.exists(path)
                    with open(path, "a", newline="") as fh:
                        w = csv.DictWriter(fh, list(r))
                        if new:
                            w.writeheader()
                        w.writerow(r)
                    log(f'{regime:4s} {kind:9s} a={aggr:.2f} s0={s0:5.0f} {r["outcome"]:5s} t={r["time"]:7.2f} '
                        f'd={r["distance"]:6.0f} int={r["intervention_rate"]:.3f} grip95={r["grip_cmd_p95"]:.2f} '
                        f'passed={r["passed"]} rtf={r["rtf"]} steps/s={r["ctrl_steps_per_s"]}')
    print("SWEEP_DONE", OUT)


if __name__ == "__main__":
    main()
