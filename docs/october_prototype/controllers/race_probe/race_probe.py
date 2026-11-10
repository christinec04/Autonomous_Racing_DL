"""Physics probe. Answers "can Webots simulate a race car at the limit?" with measurements.

mode=probe (worlds/probe.wbt, flat slick ground) runs
  steer     sign check, steer > 0 must turn left
  accel     full throttle from rest, 0 to 100 km/h time and top speed
  brake     full braking from 60 and 80 m/s
  skidpad   fixed steering, slowly rising speed, lateral grip limit with and without downforce
  slide     car sliding with locked wheels in several world directions, friction circle versus pyramid
  combined  steady cornering then braking, total acceleration versus the friction circle
mode=barrier (race train world) drives into the crash barrier at 20 degrees and checks for tunnelling
mode=cruise follows the racing line, the EGO with lidar=1 reads the lidar and reports the real time factor
mode=train runs barrier, then puts the EGO back on the grid and cruises from sim time start
mode=idle holds the brakes

Other args  tag=name (file suffix)  T=seconds (cruise)  pace=0.8  start=seconds  tests=steer,accel,...
"""
import csv
import json
import math
import os
import sys
import time
import traceback

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs", "probe", "progress.log")


def _crash(kind, value, tb):
    with open(LOG, "a") as fh:
        fh.write("".join(traceback.format_exception(kind, value, tb)))
    sys.__excepthook__(kind, value, tb)


sys.excepthook = _crash
with open(LOG, "a") as fh:
    fh.write(f"{time.strftime('%H:%M:%S')} controller python {sys.version.split()[0]} args {sys.argv[1:]}\n")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "racelib"))
from car import Car, out_dir  # noqa: E402
from track import CDA, G, HALF, MU, RHO, WHEELBASE, Track, grip  # noqa: E402

car = Car()
ARGS = car.args
MODE = ARGS.get("mode", "probe")
TAG = ARGS.get("tag", "")
OUT = out_dir("probe")
rows = []
TESTS = ARGS.get("tests", "steer,accel,brake,skid,slide,combined,variants").split(",")
summary = {"dt_ms": round(car.dt * 1000, 3), "mu_track_py": MU, "mu_world": float(ARGS.get("mu", MU)),
           "fds_world": float(ARGS.get("fds", 0))}
aero_on = car.aero
VARIANT = ""


def progress(msg):
    with open(os.path.join(OUT, "progress.log"), "a") as fh:
        fh.write(f"{time.strftime('%H:%M:%S')} sim {car.d.getTime():.1f} {MODE} {TAG} {msg}\n")


progress("start")


def drag_only():
    vel = car.node.getVelocity()
    q = 0.5 * RHO * CDA * car.speed
    car.node.addForce([-q * vel[0], -q * vel[1], 0], False)


def no_aero():
    pass


def set_aero(fn):
    car.aero = fn
    progress(f"aero {fn.__name__} after {list(summary)[-1]}")


def log(test, t, extra=None):
    rows.append({"test": test + VARIANT, "t": round(t, 4), "vx": car.vx, "vy": car.vy, "ax": car.ax, "ay": car.ay,
                 "yaw_rate": car.yaw_rate, "x": car.x, "y": car.y, "up": car.up_z, **(extra or {})})


def settle(n=40):
    car.command(0, 0, 1)
    for _ in range(n):
        car.step()


def run_up(v_goal, steer=0.0, limit=60.0):
    t = 0.0
    while car.vx < v_goal and t < limit:
        car.command(steer, 1, 0)
        car.step()
        t += car.dt


def steer_check():
    for name in ("right_rear_wheel", "left_rear_wheel"):
        try:
            m = car.d.getDevice(name)
            summary[f"motor_{name}"] = {"max_velocity": m.getMaxVelocity(), "acceleration": m.getAcceleration(),
                                        "max_torque": m.getMaxTorque()}
        except Exception as e:
            summary[f"motor_{name}"] = str(e)
    car.place(-2000, 2000, 0)
    settle()
    run_up(10)
    yaw0 = car.yaw
    for _ in range(int(1.5 / car.dt)):
        car.command(0.3, 0.3, 0)
        car.step()
    turn = (car.yaw - yaw0 + math.pi) % (2 * math.pi) - math.pi
    summary["steer_plus_turns"] = "left" if turn > 0 else "right"
    summary["steer_plus_yaw_change_rad"] = turn


def accel(tag="accel"):
    car.place(-2800, -2000 if tag == "accel" else -1500, 0)
    settle()
    t, t100, t200 = 0.0, None, None
    while t < 30:
        car.command(0, 1, 0)
        car.step()
        t += car.dt
        log(tag, t)
        if t100 is None and car.vx > 27.78:
            t100 = t
        if t200 is None and car.vx > 55.56:
            t200 = t
    pre = "" if tag == "accel" else tag + "_"
    summary[pre + "t_0_100_s"] = t100
    summary[pre + "t_0_200_s"] = t200
    summary[pre + "v_top_ms"] = max(r["vx"] for r in rows if r["test"] == tag)
    summary[pre + "accel_max_ms2"] = max(r["ax"] for r in rows if r["test"] == tag and r["t"] > 0.2)


def brake(v0):
    tag = f"brake{v0}"
    car.place(-2800, -1000 + 10 * v0, 0)
    settle()
    run_up(v0)
    t, decel, x0, v_start = 0.0, [], car.x, car.vx
    while car.vx > 1 and t < 20:
        car.command(0, 0, 1)
        car.step()
        t += car.dt
        log(tag, t)
        if t > 0.1:
            decel.append((car.vx, -car.ax))
    hi = [a for v, a in decel if v0 - 8 < v < v0 - 2] or [float("nan")]
    lo = [a for v, a in decel if 15 < v < 25] or [float("nan")]
    summary[tag] = {"v0": v_start, "time_s": t, "dist_m": car.x - x0, "decel_high_v": sum(hi) / len(hi),
                    "decel_at_20": sum(lo) / len(lo), "model_grip_high_v": grip(v0 - 5), "model_grip_20": grip(20)}


def skidpad(steer, tag, ramp=0.3):
    car.place(0, 0, 0)
    settle()
    t, target, best, best_v, lost = 0.0, 5.0, 0.0, 0.0, None
    window = []
    while t < 200:
        target += ramp * car.dt
        err = target - car.vx
        car.command(steer, max(0.0, min(1.0, 0.3 * err)), max(0.0, min(1.0, -0.3 * err)))
        car.step()
        t += car.dt
        beta = math.degrees(math.atan2(car.vy, max(car.vx, 0.1)))
        log(tag, t, {"ay_ss": car.vx * car.yaw_rate, "beta_deg": beta, "steer": steer})
        # measured lateral acceleration averaged over one second, v times yaw rate overshoots during snaps
        window = (window + [car.ay])[-int(1.0 / car.dt):]
        avg = abs(sum(window) / len(window))
        if t > 3 and avg > best:
            best, best_v = avg, car.vx
        if t > 3 and (abs(beta) > 12 or car.up_z < 0.8):
            lost = car.vx
            break
        if car.vx < target - 8 and t > 10:
            lost = car.vx
            break
    summary[tag] = {"steer": steer, "ay_max": best, "ay_max_g": best / G, "at_v": best_v,
                    "model_grip_at_v": grip(best_v), "ratio_to_model": best / grip(best_v), "lost_at_v": lost,
                    "flipped": car.up_z < 0.8}


def slide(yaw_deg, beta_deg, v0=30.0):
    """Car pointing at yaw slides along yaw + beta with brakes on and no aero."""
    tag = f"slide_y{yaw_deg}_b{beta_deg}"
    yaw = math.radians(yaw_deg)
    car.place(2000, -2000 + 30 * len(summary), yaw)
    settle()
    d = math.radians(yaw_deg + beta_deg)
    car.node.setVelocity([v0 * math.cos(d), v0 * math.sin(d), 0, 0, 0, 0])
    car.v_prev = None
    acc, t = [], 0.0
    prev = None
    for _ in range(int(0.6 / car.dt)):
        car.command(0, 0, 1)
        car.step()
        t += car.dt
        vel = car.node.getVelocity()
        if prev is not None and t > 0.15:
            acc.append(((vel[0] - prev[0]) / car.dt, (vel[1] - prev[1]) / car.dt, vel[0], vel[1]))
        prev = vel
        log(tag, t)
    ax = sum(a[0] for a in acc) / len(acc)
    ay = sum(a[1] for a in acc) / len(acc)
    vx = sum(a[2] for a in acc) / len(acc)
    vy = sum(a[3] for a in acc) / len(acc)
    ang = math.degrees(math.atan2(-vy, -vx) - math.atan2(ay, ax))
    summary[tag] = {"world_dir_deg": yaw_deg + beta_deg, "decel": math.hypot(ax, ay), "decel_over_mu_g": math.hypot(ax, ay) / (summary["mu_world"] * G),
                    "force_vs_minus_v_deg": (ang + 180) % 360 - 180, "world_ax": ax, "world_ay": ay}


def combined(steer, brake_level, tag):
    """Hold a corner near the limit, then brake while still turning."""
    car.place(0, 0, 0)
    settle()
    v_goal = summary["skid_r25"]["at_v"] * 0.95
    t = 0.0
    while car.vx < v_goal and t < 60:
        car.command(steer, max(0.0, min(1.0, 0.3 * (v_goal - car.vx))), 0)
        car.step()
        t += car.dt
    for _ in range(int(1.5 / car.dt)):
        car.command(steer, max(0.0, min(1.0, 0.3 * (v_goal - car.vx) + 0.1)), 0)
        car.step()
    pre = car.ay
    peak, t, win = (0.0, 0.0, 0.0, 1.0), 0.0, []
    for _ in range(int(0.8 / car.dt)):
        car.command(steer, 0, brake_level)
        car.step()
        t += car.dt
        win = (win + [(car.ax, car.ay)])[-8:]
        ax = sum(a for a, _ in win) / len(win)
        ay = sum(b for _, b in win) / len(win)
        tot = math.hypot(ax, ay)
        log(tag, t, {"ay_ss": ay, "steer": steer, "brake": brake_level})
        if t > 0.1 and tot / grip(car.vx) > peak[0] / grip(peak[3]):
            peak = (tot, ax, ay, car.vx)
    summary[tag] = {"brake": brake_level, "v": v_goal, "ay_before": pre, "peak_total": peak[0], "ax": peak[1],
                    "ay": peak[2], "at_v": peak[3], "circle_limit": grip(peak[3]), "ratio_to_circle": peak[0] / grip(peak[3]),
                    "angle_deg": math.degrees(math.atan2(abs(peak[1]), abs(peak[2])))}


def contact():
    root = car.d.getRoot().getField("children")
    for k in range(root.getCount()):
        n = root.getMFNode(k)
        if n.getTypeName() == "WorldInfo":
            return n.getField("contactProperties").getMFNode(0)


def set_contact(mu, fds):
    """Change the slick asphalt pair at run time, the slide test then shows whether it took effect."""
    cp = contact()
    cp.getField("coulombFriction").setMFFloat(0, mu)
    f = cp.getField("forceDependentSlip")
    if f.getCount():
        f.setMFFloat(0, fds)
    else:
        f.insertMFFloat(0, fds)
    summary["mu_world"], summary["fds_world"] = mu, fds
    car.step()
    progress(f"contact mu {mu} fds {fds}")


def save(name):
    progress(f"save {name}")
    path = os.path.join(OUT, f"{name}{'_' + TAG if TAG else ''}")
    if rows:
        with open(path + ".csv", "w", newline="") as fh:
            keys = sorted({k for r in rows for k in r})
            w = csv.DictWriter(fh, keys)
            w.writeheader()
            w.writerows(rows)
    with open(path + ".json", "w") as fh:
        json.dump(summary, fh, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(summary, indent=2, default=str))


def probe():
    global VARIANT
    wall0, sim0 = time.time(), car.d.getTime()
    if "steer" in TESTS:
        steer_check()
    if "accel" in TESTS:
        accel()
    if "brake" in TESTS:
        brake(60)
        brake(70)
    if "skid" in TESTS:
        set_aero(drag_only)
        skidpad(0.06, "skid_r100_noaero")
        skidpad(0.12, "skid_r50_noaero")
        skidpad(0.25, "skid_r25_noaero")
        set_aero(aero_on)
        skidpad(0.06, "skid_r100")
        skidpad(0.12, "skid_r50")
    if "skid" in TESTS or "skid25" in TESTS:
        skidpad(0.25, "skid_r25")
    if "slide" in TESTS:
        set_aero(no_aero)
        for yaw, beta in ((0, 0), (0, 30), (0, 45), (0, 90), (45, 0), (30, 0), (45, 45)):
            slide(yaw, beta)
        set_aero(aero_on)
    if "combined" in TESTS:
        for b in (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0):
            combined(0.25, b, f"combined_b{int(b * 100)}")
    if "topnoaero" in TESTS:
        set_aero(no_aero)
        accel("accel_noaero")
        set_aero(aero_on)
    if "asym" in TESTS:
        # two coulombFriction values switch Webots to asymmetric friction with fdir1 taken from the wheel
        cp = contact().getField("coulombFriction")
        if cp.getCount() < 2:
            cp.insertMFFloat(1, MU)
        car.step()
        VARIANT = "_asym"
        set_aero(no_aero)
        base = dict(summary)
        summary.clear()
        summary["mu_world"] = MU
        for yaw, beta in ((0, 0), (0, 45), (0, 90), (45, 0), (30, 0), (45, 45)):
            slide(yaw, beta)
        base["variant_asym"] = dict(summary)
        summary.clear()
        summary.update(base)
        set_aero(aero_on)
        cp.removeMF(1)
        car.step()
        VARIANT = ""
    if "variants" in TESTS:
        # same tests at mu 1.0, then with force dependent slip, results go in their own blocks
        base = dict(summary)
        for mu, fds, name in ((1.0, 0.0, "mu10"), (MU, 0.0005, "fds"), (MU, 0.005, "fds5")):
            summary.clear()
            summary.update({"mu_track_py": MU})
            set_contact(mu, fds)
            VARIANT = "_" + name
            skidpad(0.25, "skid_r25")
            set_aero(no_aero)
            slide(0, 0)
            slide(0, 45)
            set_aero(aero_on)
            base[f"variant_{name}"] = dict(summary)
        VARIANT = ""
        summary.clear()
        summary.update(base)
        set_contact(MU, 0.0)
    summary["rtf"] = (car.d.getTime() - sim0) / (time.time() - wall0)
    save("summary")


def barrier():
    """Aim at the right barrier of the s 460 to 650 straight and see whether the car comes out the other side."""
    track = Track()
    wall_lat = HALF + 0.06 + 0.05 * 14.0
    for v0 in (30, 50, 70):
        x, y, yaw = track.pose(470, 3.0)
        aim = yaw - math.radians(20)
        car.place(x, y, aim)
        settle(10)
        car.node.setVelocity([v0 * math.cos(aim), v0 * math.sin(aim), 0, 0, 0, 0])
        car.v_prev = None
        t, lat_min, hit_v, end = 0.0, 0.0, None, None
        while t < 2.5:
            car.command(0, 0.6, 0)
            car.step()
            t += car.dt
            # body centre, 1.5 m ahead of the rear axle origin
            bx, by = car.x + 1.5 * car.fwd[0], car.y + 1.5 * car.fwd[1]
            _, s, lat = track.project(bx, by)
            fx, fy = car.x + 3.7 * car.fwd[0], car.y + 3.7 * car.fwd[1]
            _, _, lat_front = track.project(fx, fy)
            lat_min = min(lat_min, lat)
            if hit_v is None and lat_front < -wall_lat + 0.3:
                hit_v = car.speed
            log(f"barrier{v0}", t, {"lat": lat, "lat_front": lat_front, "s": s})
            end = (lat, car.speed, car.up_z, car.z)
        summary[f"v{v0}"] = {"impact_speed": hit_v, "body_lat_min": lat_min, "wall_lat": -wall_lat,
                             "tunnelled": lat_min < -wall_lat - 0.5, "lat_end": end[0], "speed_end": end[1],
                             "up_end": end[2], "z_end": end[3]}
    save("barrier")


def pursuit(track, pace):
    i, s, lat = track.project(car.x, car.y, "me")
    L = max(8.0, 0.7 * car.speed)
    j = int(track.ahead(i, L))
    tx, ty = track.line[j]
    dx, dy = tx - car.x, ty - car.y
    yl = -dx * car.fwd[1] + dy * car.fwd[0]
    steer = math.atan(2 * WHEELBASE * yl / (L * L)) / 0.45
    look = track.ahead(i, range(0, int(max(car.speed, 10) * 1.5), 2))
    v_t = pace * min(track.v[look])
    err = v_t - car.speed
    return steer, max(0.0, min(1.0, 0.5 * err)), max(0.0, min(1.0, -0.3 * err)), s


def cruise(start=0.0):
    """Hold the brakes until sim time start, then follow the racing line. The EGO with lidar=1 times the run and quits."""
    track = Track()
    pace = float(ARGS.get("pace", 0.8))
    T = float(ARGS.get("T", 60))
    lidar = None
    if ARGS.get("lidar") == "1":
        lidar = car.d.getDevice("lidar")
        lidar.enable(int(car.dt * 1000))
    while car.d.getTime() < start and car.step() != -1:
        car.command(0, 0, 1)
    wall0, sim0, dist, hits, s_prev = time.time(), car.d.getTime(), 0.0, 0, None
    while car.step() != -1:
        steer, th, br, s = pursuit(track, pace)
        car.command(steer, th, br)
        if lidar is not None:
            r = lidar.getRangeImage()
            hits += sum(1 for d in r if d < 80)
        if s_prev is not None:
            dist += (s - s_prev + track.length / 2) % track.length - track.length / 2
        s_prev = s
        if lidar is not None and car.d.getTime() - sim0 >= T:
            sim = car.d.getTime() - sim0
            summary.update({"sim_s": sim, "wall_s": time.time() - wall0, "rtf": sim / (time.time() - wall0),
                            "ego_progress_m": dist, "ego_up_end": car.up_z, "lidar_points": len(r),
                            "lidar_hits_last": sum(1 for d in r if d < 80), "lidar_hit_mean": hits / (sim / car.dt)})
            save("rtf")
            car.d.simulationQuit(0)
            break


START = float(ARGS.get("start", 0))
if MODE == "probe":
    probe()
    car.d.simulationQuit(0)
elif MODE == "train":
    # barrier test first while the opponents wait on the grid, then everyone races for the timing run
    home = (car.x, car.y, car.yaw)
    barrier()
    rows.clear()
    for k in [k for k in summary if k.startswith("v")]:
        summary.pop(k)
    car.place(*home)
    cruise(START)
elif MODE == "cruise":
    cruise(START)
else:
    while car.step() != -1:
        car.command(0, 0, 1)
