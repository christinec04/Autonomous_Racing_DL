"""Shield experiment without RL. Answers question 2 with a scripted driver.

The ego is driven by Pilot with an aggression sweep and every command goes through one shield.
Two regimes
  road   ego pace 0.45, slow traffic at pace 0.30 to overtake, typical self driving speeds
  race   ego pace RACE_PACE with a dive bomb pass, opponents at pace 0.80, 0.86, 0.92 ahead
Each episode starts on a straight, runs DIST metres or until a crash, then the supervisor resets.

controllerArgs (all optional, comma separated lists)
  regime=road,race  shields=none,geometric,friction  aggr=1.0,1.1,1.2,1.3  starts=118,1248
  dist=2100  race_pace=0.95  road_pace=0.45  tag=name (results in runs/shield_test/<tag>)
  wall_budget=660  stop starting episodes after this many wall seconds, a relaunch resumes
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "racelib"))
from car import Car, out_dir  # noqa: E402
from pilot import CAR_HALF_WIDTH, CAR_LENGTH, REAR_TO_CENTER, Pilot, gap_ahead, node_state, steer_for  # noqa: E402
from shield import local_lat, make_shield  # noqa: E402
from track import HALF, Track, grip  # noqa: E402

car = Car()
track = Track()
A = car.args


def floats(key, default):
    return [float(v) for v in A.get(key, default).split(",")]


REGIMES = A.get("regime", "road,race").split(",")
SHIELDS = A.get("shields", "none,geometric,friction").split(",")
DIST = float(A.get("dist", 2100))
PACE = {"road": float(A.get("road_pace", 0.45)), "race": float(A.get("race_pace", 0.95))}
AGGR = {"road": floats("aggr_road", A.get("aggr", "1.0,1.15,1.3")),
        "race": floats("aggr_race", A.get("aggr", "1.0,1.1,1.2,1.3"))}
STARTS = {"road": floats("starts_road", A.get("starts", "118")),
          "race": floats("starts_race", A.get("starts", "118,1248"))}
OPP_PACE = {"road": [0.30, 0.30, 0.30], "race": [0.80, 0.86, 0.92]}
OPP_GAP = {"road": [60.0, 300.0, 600.0], "race": [80.0, 300.0, 550.0]}
OPP_LAT = [2.0, -2.0, 1.0]
SPIN_DEG = 25.0
LOG_EVERY = 5
WALL_BUDGET = float(A.get("wall_budget", 1e9))   # seconds of wall clock before a chunk stops starting episodes
OUT = out_dir("shield_test", A["tag"]) if "tag" in A else out_dir("shield_test")
os.makedirs(os.path.join(OUT, "traj"), exist_ok=True)

opp_nodes = [car.d.getFromDef(f"OPP_{k}") for k in (1, 2, 3)]
opp_nodes = [n for n in opp_nodes if n]
opp_args = [None] * len(opp_nodes)


def line_pose(s):
    """Pose on the racing line with the line heading, not the centreline heading."""
    i = track.at(s)
    p, q = track.line[(i - 1) % track.n], track.line[(i + 1) % track.n]
    x, y = track.line[i]
    return float(x), float(y), math.atan2(q[1] - p[1], q[0] - p[0])


def place(node, x, y, yaw):
    node.getField("translation").setSFVec3f([x, y, 0.36])
    node.getField("rotation").setSFRotation([0, 0, 1, yaw])
    node.resetPhysics()


def launch(node, yaw, speed):
    """Initial speed, set one step after resetPhysics or Webots drops it."""
    node.setVelocity([speed * math.cos(yaw), speed * math.sin(yaw), 0, 0, 0, 0])


def log(msg):
    with open(os.path.join(OUT, "log.txt"), "a") as fh:
        fh.write(f"{time.strftime('%H:%M:%S')} pid {os.getpid()} {msg}\n")


def set_opponent_pace(regime):
    """Restart opponent controllers with the regime pace, only when it changes."""
    for k, n in enumerate(opp_nodes):
        args = [f"pace={OPP_PACE[regime][k]:.2f}"]
        if opp_args[k] != args:
            field = n.getField("controllerArgs")
            while field.getCount():
                field.removeMF(0)
            field.insertMFString(0, args[0])
            n.restartController()
            opp_args[k] = args


def ego_state():
    i, s, lat = track.project(car.x, car.y, "ego")
    return {"x": car.x, "y": car.y, "yaw": car.yaw, "vx": car.vx, "vy": car.vy, "speed": car.speed,
            "i": i, "s": s, "lat": lat}


def box(st):
    """Corners of the car footprint, the bounding box is 4.4 x 1.8 centred 1.5 m ahead of the rear axle."""
    c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
    cx, cy = st["x"] + REAR_TO_CENTER * c, st["y"] + REAR_TO_CENTER * s
    h, w = CAR_LENGTH / 2, CAR_HALF_WIDTH
    return [(cx + a * h * c - b * w * s, cy + a * h * s + b * w * c) for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1))]


def overlap(p, q):
    """Separating axis test for two convex quads."""
    for poly in (p, q):
        for k in range(4):
            ex, ey = poly[(k + 1) % 4][0] - poly[k][0], poly[(k + 1) % 4][1] - poly[k][1]
            nx, ny = -ey, ex
            a = [nx * x + ny * y for x, y in p]
            b = [nx * x + ny * y for x, y in q]
            if max(a) < min(b) or max(b) < min(a):
                return False
    return True


def crash_check(st, opps):
    c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
    lat_c, _ = local_lat(track, st["x"] + REAR_TO_CENTER * c, st["y"] + REAR_TO_CENTER * s, st["i"])
    if abs(lat_c) > HALF - CAR_HALF_WIDTH:
        return "wall", lat_c
    if st["speed"] > 8 and abs(math.degrees(math.atan2(st["vy"], max(st["vx"], 0.1)))) > SPIN_DEG:
        return "spin", lat_c
    mine = None
    for o in opps:
        if abs(gap_ahead(track, st["s"], o["s"])) < 8 and abs(o["lat"] - st["lat"]) < 4:
            mine = mine or box(st)
            if overlap(mine, box(o)):
                return "car", lat_c
    return "", lat_c


def settle_controllers(steps=3):
    for _ in range(steps):
        car.command(0, 0, 1)
        car.step()


def episode(regime, kind, aggr, s0):
    pace = PACE[regime]
    pilot = Pilot(track, pace, aggr, dive=(regime == "race"))
    sh = make_shield(kind, track)
    set_opponent_pace(regime)
    starts = []
    for k, n in enumerate(opp_nodes):
        s = s0 + OPP_GAP[regime][k]
        x, y, _ = track.pose(s, OPP_LAT[k])
        yaw = line_pose(s)[2]
        place(n, x, y, yaw)
        starts.append((n, yaw, OPP_PACE[regime][k] * track.v[track.at(s)] * 0.9))
    x, y, yaw = line_pose(s0)
    place(car.node, x, y, yaw)
    starts.append((car.node, yaw, min(pace * aggr, 1.0) * track.v[track.at(s0)] * 0.9))
    car.command(0, 0, 0)
    car.step()
    for n, yaw, v in starts:
        launch(n, yaw, v)
    car.v_prev = None
    track._last.clear()
    car.step()

    t0, travelled, s_prev = car.d.getTime(), 0.0, None
    steps = interventions = 0
    reasons = {}
    gu_cmd, gu_meas, rows = [], [], []
    a_meas = 0.0
    outcome, min_clear, slow_t = "ok", 99.0, 0.0
    where = {"crash_s": "", "crash_x": "", "crash_y": "", "crash_heading_deg": ""}
    peak = (-1.0, 0.0, 0.0)   # measured |a| / grip, s, world heading, the pyramid friction depends on heading
    ahead0 = None
    t_limit = 3.0 * DIST / max(pace * 25.0, 5.0)
    while True:
        st = ego_state()
        opps = [node_state(track, n, f"o{k}") for k, n in enumerate(opp_nodes)]
        if s_prev is not None:
            travelled += gap_ahead(track, s_prev, st["s"])
        s_prev = st["s"]
        if ahead0 is None:
            ahead0 = [gap_ahead(track, st["s"], o["s"]) > 0 for o in opps]
        if not all(math.isfinite(st[k]) for k in ("x", "y", "speed")) or st["speed"] > 120:
            outcome = "blowup"   # physics went unstable, not a driving result
            log(f"blowup at s={st['s']} v={st['speed']}")
            break
        why, lat_c = crash_check(st, opps)
        min_clear = min(min_clear, HALF - CAR_HALF_WIDTH - abs(lat_c))
        el = car.d.getTime() - t0
        if steps % 3750 == 0 and steps:
            log(f"  t={el:.0f} s={st['s']:.0f} travelled={travelled:.0f} v={st['speed']:.1f} mode={pilot.mode}")
        slow_t = slow_t + car.dt if st["speed"] < 1.0 else 0.0
        if why:
            outcome = why
            where = {"crash_s": round(st["s"], 1), "crash_x": round(st["x"], 1), "crash_y": round(st["y"], 1),
                     "crash_heading_deg": round(math.degrees(st["yaw"]) % 360, 1)}
            near = sorted(opps, key=lambda o: abs(gap_ahead(track, st["s"], o["s"])))[:1]
            log(f"{why} at s={st['s']:.1f} lat={st['lat']:.2f} v={st['speed']:.1f} mode={pilot.mode} " +
                " ".join(f"opp gap={gap_ahead(track, st['s'], o['s']):.1f} lat={o['lat']:.2f} v={o['speed']:.1f}" for o in near))
            break
        if travelled >= DIST:
            break
        if el > t_limit or slow_t > 5.0:
            outcome = "stall"
            break
        cmd = pilot.act(st, opps, car.dt)
        steer, throttle, brake, info = sh.filter(st, opps, *cmd)
        car.command(steer, throttle, brake)
        steps += 1
        interventions += info["intervened"]
        if info["intervened"]:
            reasons[info["reason"]] = reasons.get(info["reason"], 0) + 1
        g = grip(st["speed"])
        a_meas = 0.9 * a_meas + 0.1 * math.hypot(car.ax, car.ay)   # 80 ms smoothing of the measured acceleration
        gu_cmd.append(info["grip_used"])
        gu_meas.append(a_meas / g)
        if a_meas / g > peak[0]:
            peak = (a_meas / g, st["s"], math.degrees(st["yaw"]) % 360)
        if steps % LOG_EVERY == 0:
            near = min(opps, key=lambda o: abs(gap_ahead(track, st["s"], o["s"]))) if opps else None
            rows.append((el, st["x"], st["y"], st["s"], st["lat"], st["speed"], cmd[0], steer, cmd[1], throttle,
                         cmd[2], brake, info["intervened"], info["grip_used"], a_meas / g, info["u"],
                         gap_ahead(track, st["s"], near["s"]) if near else 99.0, near["lat"] if near else 0.0,
                         near["speed"] if near else 0.0))
        if car.step() == -1:
            sys.exit(0)
    el = car.d.getTime() - t0
    opps = [node_state(track, n, f"o{k}") for k, n in enumerate(opp_nodes)]
    passed = sum(1 for k, o in enumerate(opps) if ahead0 and ahead0[k] and gap_ahead(track, s_prev, o["s"]) < 0)
    name = f"{regime}_{kind}_a{aggr:.2f}_s{int(s0)}"
    np.savez_compressed(os.path.join(OUT, "traj", name + ".npz"), traj=np.array(rows, dtype=np.float32),
                        cols=np.array(["t", "x", "y", "s", "lat", "v", "steer_in", "steer", "throttle_in", "throttle",
                                       "brake_in", "brake", "intervened", "grip_cmd", "grip_meas", "u",
                                       "opp_gap", "opp_lat", "opp_v"]))
    gu_cmd, gu_meas = np.array(gu_cmd or [0.0]), np.array(gu_meas or [0.0])
    return {
        "regime": regime, "shield": kind, "pace": pace, "aggression": aggr, "s0": s0, "outcome": outcome,
        "crash": int(outcome in ("wall", "spin", "car")), "time": round(el, 3), "distance": round(travelled, 1),
        "lap_time": round(el, 3) if outcome == "ok" else "", "mean_speed": round(travelled / max(el, 1e-3), 2),
        "intervention_rate": round(interventions / max(steps, 1), 4),
        "reasons": json.dumps(reasons), "passed": passed, "min_wall_clearance": round(min_clear, 3),
        "grip_cmd_mean": round(float(gu_cmd.mean()), 4), "grip_cmd_p95": round(float(np.percentile(gu_cmd, 95)), 4),
        "grip_cmd_max": round(float(gu_cmd.max()), 4), "grip_meas_p95": round(float(np.percentile(gu_meas, 95)), 4),
        "grip_meas_max": round(float(gu_meas.max()), 4),
        **where, "peak_grip_s": round(peak[1], 1), "peak_grip_heading_deg": round(peak[2], 1),
        "hist_cmd": json.dumps(np.histogram(np.clip(gu_cmd, 0, 1.99), bins=40, range=(0, 2))[0].tolist()),
        "hist_meas": json.dumps(np.histogram(np.clip(gu_meas, 0, 1.99), bins=40, range=(0, 2))[0].tolist()),
    }


def summarise(rows):
    out = {}
    for r in rows:
        key = f'{r["regime"]}/{r["shield"]}/{float(r["aggression"]):.2f}'
        d = out.setdefault(key, {"episodes": 0, "crashes": 0, "times": [], "intervention": [], "grip_cmd_p95": []})
        d["episodes"] += 1
        d["crashes"] += int(r["crash"])
        if r["outcome"] == "ok":
            d["times"].append(float(r["time"]))
        d["intervention"].append(float(r["intervention_rate"]))
        d["grip_cmd_p95"].append(float(r["grip_cmd_p95"]))
    for d in out.values():
        d["crash_rate"] = d["crashes"] / d["episodes"]
        d["mean_lap_time"] = float(np.mean(d["times"])) if d["times"] else None
        d["intervention"] = float(np.mean(d["intervention"]))
        d["grip_cmd_p95"] = float(np.mean(d["grip_cmd_p95"]))
    return out


def calibrate():
    """Actuator map on a flat plane, brake and throttle versus measured acceleration, steer versus lateral acceleration."""
    out = {"brake": [], "throttle": [], "steer": []}

    def start(v):
        place(car.node, 0, 0, 0)
        car.command(0, 0, 0)
        car.step()
        launch(car.node, 0, v)
        car.v_prev = None
        for _ in range(10):
            car.step()

    def hold(v_goal, steer, seconds):
        for _ in range(int(seconds / car.dt)):
            err = v_goal - car.vx
            car.command(steer, max(0.0, min(1.0, 0.3 * err + 0.2)), max(0.0, min(1.0, -0.05 * err)))
            car.step()

    def measure(cmd, seconds):
        v0, t0, beta = car.vx, car.d.getTime(), 0.0
        for _ in range(int(seconds / car.dt)):
            car.command(*cmd)
            car.step()
            beta = max(beta, abs(math.degrees(math.atan2(car.vy, max(car.vx, 0.1)))))
        return v0, car.vx, car.d.getTime() - t0, beta

    for v in (15.0, 30.0, 50.0):
        for b in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
            start(v)
            v0, v1, dt, beta = measure((0, 0, b), 0.4)
            out["brake"].append({"v": (v0 + v1) / 2, "brake": b, "decel": (v0 - v1) / dt, "beta_max": beta})
            log(f"brake v={v0:.1f} b={b} decel={(v0 - v1) / dt:.2f} grip={grip(v0):.1f} beta={beta:.1f}")
        for b in (0.2, 0.5, 1.0):
            start(v)
            st = steer_for(v, 0.5 * grip(v))      # cornering at half the grip, then brake
            hold(v, st, 1.5)
            v0, v1, dt, beta = measure((st, 0, b), 0.4)
            out.setdefault("brake_turn", []).append({"v": (v0 + v1) / 2, "brake": b, "decel": (v0 - v1) / dt, "beta_max": beta})
            log(f"brake in turn v={v0:.1f} b={b} decel={(v0 - v1) / dt:.2f} beta={beta:.1f}")
        for th in (0.0, 0.25, 0.5, 1.0):
            start(v)
            v0, v1, dt, _ = measure((0, th, 0), 0.4)
            out["throttle"].append({"v": (v0 + v1) / 2, "throttle": th, "accel": (v1 - v0) / dt})
    for v in (15.0, 30.0, 50.0):
        for st in (0.01, 0.02, 0.04, 0.08, 0.15, 0.3):
            start(v)
            hold(v, st, 3.0)
            ay = car.vx * car.yaw_rate
            beta = math.degrees(math.atan2(car.vy, max(car.vx, 0.1)))
            out["steer"].append({"v": car.vx, "steer": st, "ay": ay, "ay_kinematic": car.vx ** 2 * math.tan(0.45 * st) / 3.0,
                                 "beta_deg": beta, "grip": grip(car.vx)})
            log(f"steer v={car.vx:.1f} st={st} ay={ay:.2f} kin={out['steer'][-1]['ay_kinematic']:.2f} beta={beta:.1f}")
    with open(os.path.join(OUT, "calib.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    car.d.simulationQuit(0)


path = os.path.join(OUT, "results.csv")
log(f"controller start args {A}")
done = set()
if os.path.exists(path):   # resume, a chunk killed by the guard timeout keeps its finished episodes
    with open(path) as fh:
        done = {(r["regime"], r["shield"], float(r["aggression"]), float(r["s0"])) for r in csv.DictReader(fh)}
wall0 = time.time()
sim0 = car.d.getTime()
settle_controllers()
if REGIMES == ["calib"]:
    calibrate()
    while car.step() != -1:
        pass
DEMO = A.get("demo") == "1"   # loop forever with an on screen label, for watching in the Webots window


def chase_camera():
    """Smoothed chase camera driven every step, the built in follow jumps on every reset."""
    root = car.d.getRoot().getField("children")
    view = next(root.getMFNode(i) for i in range(root.getCount()) if root.getMFNode(i).getTypeName() == "Viewpoint")
    view.getField("follow").setSFString("")
    pos_f, rot_f = view.getField("position"), view.getField("orientation")
    cam = {"eye": None, "aim": None}
    raw_step = car.step

    def look(eye, aim):
        fx, fy, fz = (aim[i] - eye[i] for i in range(3))
        n = math.sqrt(fx * fx + fy * fy + fz * fz)
        fx, fy, fz = fx / n, fy / n, fz / n
        h = math.hypot(fx, fy)
        lx, ly = -fy / h, fx / h
        ux, uy, uz = -fz * ly, fz * lx, fx * ly - fy * lx
        m = [[fx, lx, ux], [fy, ly, uy], [fz, 0.0, uz]]
        ang = math.acos(max(-1.0, min(1.0, (m[0][0] + m[1][1] + m[2][2] - 1) / 2)))
        ax, ay, az = m[2][1] - m[1][2], m[0][2] - m[2][0], m[1][0] - m[0][1]
        n = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
        return [ax / n, ay / n, az / n, ang]

    def step():
        r = raw_step()
        fx, fy = car.fwd
        eye = [car.x - 16 * fx, car.y - 16 * fy, car.z + 6.5]
        aim = [car.x + 14 * fx, car.y + 14 * fy, car.z + 0.5]
        if cam["eye"] is None or math.dist(eye, cam["eye"]) > 25:
            cam["eye"], cam["aim"] = eye, aim   # snap after a reset teleport
        else:
            cam["eye"] = [p + 0.06 * (q - p) for p, q in zip(cam["eye"], eye)]
            cam["aim"] = [p + 0.12 * (q - p) for p, q in zip(cam["aim"], aim)]
        pos_f.setSFVec3f(cam["eye"])
        rot_f.setSFRotation(look(cam["eye"], cam["aim"]))
        return r

    car.step = step


if DEMO:
    chase_camera()
NAMES = {"none": "NO SHIELD", "geometric": "GEOMETRIC APF SHIELD", "friction": "FRICTION-AWARE SHIELD"}
COLORS = {"none": 0xEF6A52, "geometric": 0xE3A63D, "friction": 0x3CC2B2}
configs = [(g, k, a, s) for g in REGIMES for k in SHIELDS for a in AGGR[g] for s in STARTS[g]]
while True:
    for regime, kind, aggr, s0 in configs:
                if (regime, kind, aggr, s0) in done and not DEMO:
                    continue
                if time.time() - wall0 > WALL_BUDGET:
                    continue   # this chunk is out of wall time, the next launch resumes here
                log(f"start {regime} {kind} {aggr} {s0}")
                if DEMO:
                    car.d.setLabel(0, f"{NAMES[kind]}   {regime} pace, aggression {aggr:.2f}", 0.02, 0.03, 0.11, COLORS[kind], 0, "Arial")
                r = episode(regime, kind, aggr, s0)
                if DEMO:
                    verdict = "CRASH" if r["crash"] else f"LAP {r['lap_time']:.1f} s" if r["lap_time"] else "OK"
                    car.d.setLabel(1, f"{NAMES[kind]}: {verdict}", 0.02, 0.09, 0.11, COLORS[kind], 0, "Arial")
                new = not os.path.exists(path)
                with open(path, "a", newline="") as fh:
                    w = csv.DictWriter(fh, list(r))
                    if new:
                        w.writeheader()
                    w.writerow(r)
                log(f'{regime:4s} {kind:9s} a={aggr:.2f} s0={s0:5.0f} {r["outcome"]:5s} t={r["time"]:7.2f} '
                      f'd={r["distance"]:6.0f} int={r["intervention_rate"]:.3f} grip95={r["grip_cmd_p95"]:.2f} '
                      f'passed={r["passed"]} rtf={(car.d.getTime() - sim0) / (time.time() - wall0):.1f}')
    if not DEMO:
        break

with open(path) as fh:
    rows = list(csv.DictReader(fh))
with open(os.path.join(OUT, "summary.json"), "w") as fh:
    json.dump({"rtf": (car.d.getTime() - sim0) / (time.time() - wall0), "configs": summarise(rows)}, fh, indent=2)
car.d.simulationQuit(0)
