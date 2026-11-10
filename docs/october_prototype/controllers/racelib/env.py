"""Gymnasium env for shielded racing, on Webots or on the offline bicycle model.

The policy outputs [steer, accel] in [-1, 1], accel above zero is throttle and
below zero asks for that fraction of the grip as braking. The command passes through a shield before the car. The
reward is metres of progress along the centerline, minus a small cost on how
hard the shield had to correct, minus a crash penalty, plus an overtake bonus that is paid back if the opponent repasses.
"""
import math

import gymnasium as gym
import numpy as np

from pilot import lat_accel, long_accel, pedals
from track import HALF, V_TOP, grip

PREVIEW = np.array([10, 20, 35, 50, 70, 100, 140, 200])
LIDAR_BINS = 24
LIDAR_RANGE = 80.0
SCALE = 0.1          # reward units per metre
W_INT = 1.0          # metres of progress lost per step for a correction the size of the friction circle
CRASH = 100.0        # metres of progress lost on a crash
OVERTAKE = 30.0      # metres of progress gained per pass
PACES = (0.80, 0.86, 0.92)


class _Passthrough:
    def filter(self, state, opponents, steer, throttle, brake):
        return steer, throttle, brake, {"intervened": False, "reason": "", "grip_used": 0.0, "u": 0.0}


def load_shield(kind, track):
    if kind == "none":
        try:
            from shield import make_shield
            return make_shield("none", track)
        except ImportError:
            return _Passthrough()
    from shield import make_shield
    return make_shield(kind, track)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class RaceEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, backend, track, shield="none", opponents=0, max_steps=2500, start_speed=(0.3, 0.8),
                 seed=None):
        self.b = backend
        self.track = track
        self.shield_kind = shield
        self.shield = load_shield(shield, track)
        self.n_opp = opponents
        self.max_steps = max_steps
        self.start_speed = start_speed
        self.rng = np.random.default_rng(seed)
        n_obs = 8 + 3 * len(PREVIEW) + LIDAR_BINS + 8
        self.observation_space = gym.spaces.Box(-5.0, 5.0, (n_obs,), np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, (2,), np.float32)
        self.prev_act = np.zeros(2)
        self.state = None
        self.rel = {}

    def set_opponents(self, k):
        self.n_opp = int(k)

    # state helpers

    def _state(self):
        e = self.b.ego
        i, s, lat = self.track.project(e.x, e.y, "ego")
        return {"x": e.x, "y": e.y, "yaw": e.yaw, "vx": e.vx, "vy": e.vy, "speed": e.speed,
                "yaw_rate": e.yaw_rate, "i": i, "s": s, "lat": lat}

    def _opponents(self):
        out = []
        for k, o in enumerate(self.b.opponents()):
            i, s, lat = self.track.project(o["x"], o["y"], f"opp{k}")
            out.append({**o, "i": i, "s": s, "lat": lat})
        return out

    def _rel_s(self, o):
        L = self.track.length
        return (o["s"] - self.state["s"] + L / 2) % L - L / 2

    def _obs(self):
        st, t = self.state, self.track
        i = st["i"]
        herr = wrap(st["yaw"] - t.heading(i))
        idx = t.ahead(i, PREVIEW)
        head = np.array([wrap(t.heading(j) - st["yaw"]) for j in idx])
        base = [st["speed"] / V_TOP, st["vy"] / 10.0, st["yaw_rate"] / 2.0, st["lat"] / HALF, herr,
                (st["lat"] - t.offset[i]) / HALF, *self.prev_act]
        prev = np.concatenate([t.kappa[idx] * 30.0, t.v[idx] / V_TOP, head])
        rays = np.asarray(self.b.lidar(), dtype=float)
        rays = np.where(np.isfinite(rays), rays, LIDAR_RANGE)
        bins = rays[: len(rays) // LIDAR_BINS * LIDAR_BINS].reshape(LIDAR_BINS, -1).min(axis=1)
        opp = []
        ahead = sorted([o for o in self.opps if self._rel_s(o) >= 0], key=self._rel_s)[:1]
        behind = sorted([o for o in self.opps if self._rel_s(o) < 0], key=lambda o: -self._rel_s(o))[:1]
        for group in (ahead, behind):
            if group:
                o = group[0]
                ds = self._rel_s(o)
                opp += [1.0, np.clip(ds / 100.0, -1, 1), (o["lat"] - st["lat"]) / HALF, (st["speed"] - o["speed"]) / 20.0]
            else:
                opp += [0.0, 1.0 if group is ahead else -1.0, 0.0, 0.0]
        obs = np.concatenate([base, prev, np.minimum(bins, LIDAR_RANGE) / LIDAR_RANGE, opp])
        return np.clip(obs, -5, 5).astype(np.float32)

    # gym api

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        t = self.track
        s0 = self.rng.uniform(0, t.length)
        i0 = t.at(s0)
        lat0 = float(np.clip(t.offset[i0] + self.rng.normal(0, 1.0), -HALF + 2, HALF - 2))
        x, y, yaw = t.pose(s0, lat0)
        v0 = float(t.v[i0] * self.rng.uniform(*self.start_speed))
        opps = []
        if self.n_opp:
            gaps = self.rng.permutation([-25.0, 30.0, 60.0, 90.0])[: self.n_opp]
            for k, gap in enumerate(gaps):
                opps.append(((s0 + gap) % t.length, float(t.offset[t.at(s0 + gap)]) + self.rng.uniform(-1, 1),
                             PACES[k % len(PACES)]))
        self.b.reset((x, y, yaw, v0), opps)
        if hasattr(self.shield, "reset"):
            self.shield.reset()
        for key in [k for k in t._last if k == "ego" or k.startswith("opp")]:
            t._last.pop(key)
        self.prev_act = np.zeros(2)
        self.state = self._state()
        self.opps = self._opponents()
        self.rel = {k: self._rel_s(o) for k, o in enumerate(self.opps)}
        self.steps = self.slow = 0
        self.progress = 0.0
        self.ep = {"return": 0.0, "interventions": 0, "int_mag": 0.0, "overtakes": 0, "crash": ""}
        return self._obs(), {}

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=float), -1, 1)
        v = self.state["speed"]
        # negative accel asks for that fraction of the grip as deceleration, brake by wire on damping brakes
        steer, throttle = float(a[0]), max(0.0, float(a[1]))
        brake = pedals(v, float(a[1]) * grip(v))[1] if a[1] < 0 else 0.0
        s_steer, s_thr, s_brk, info = self.shield.filter(self.state, self.opps, steer, throttle, brake)
        # correction size as a fraction of the friction circle
        g = grip(v)
        mag = math.hypot(long_accel(v, s_thr, s_brk) - long_accel(v, throttle, brake),
                         lat_accel(v, s_steer) - lat_accel(v, steer)) / g
        self.b.command(s_steer, s_thr, s_brk)
        alive = self.b.step()
        s_old = self.state["s"]
        self.state = self._state()
        self.opps = self._opponents()
        L = self.track.length
        ds = (self.state["s"] - s_old + L / 2) % L - L / 2
        self.progress += ds
        self.steps += 1
        self.prev_act = np.array([s_steer, np.clip(long_accel(v, s_thr, s_brk) / g, -1, 1)])

        passes = 0
        for k, o in enumerate(self.opps):
            r = self._rel_s(o)
            if abs(r) < 30:
                # being passed back costs the same, so swapping places cannot farm the bonus
                passes += int(self.rel.get(k, 0) > 0 >= r) - int(self.rel.get(k, 0) < 0 <= r)
            self.rel[k] = r
        crash = self._crash()
        if self.state["speed"] < 2.0 and self.steps > 30:
            self.slow += 1
        else:
            self.slow = 0
        stuck = self.slow > 60
        truncated = self.steps >= self.max_steps or not alive

        # stopping costs as much as crashing, or the policy learns to park before hard corners
        reward = ds - W_INT * mag + OVERTAKE * passes - (CRASH if crash or stuck else 0.0)
        reward *= SCALE
        self.ep["return"] += reward
        self.ep["interventions"] += int(bool(info.get("intervened")))
        self.ep["int_mag"] += mag
        self.ep["overtakes"] += passes
        self.ep["crash"] = crash or ("stuck" if stuck else "")
        out = {"progress": self.progress, "laps": self.progress / L, "crash": crash, "intervened": bool(info.get("intervened")),
               "int_mag": mag, "reason": info.get("reason", ""), "grip_used": info.get("grip_used", 0.0),
               "speed": self.state["speed"], "s": self.state["s"], "lat": self.state["lat"], "overtakes": passes}
        if crash or stuck or truncated:
            out["episode_stats"] = {**self.ep, "steps": self.steps, "progress": self.progress, "laps": self.progress / L,
                                    "int_rate": self.ep["interventions"] / self.steps}
        return self._obs(), reward, bool(crash or stuck), bool(truncated), out

    def _crash(self):
        st = self.state
        c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
        for o in self.opps:
            dx, dy = o["x"] - st["x"], o["y"] - st["y"]
            if abs(dx * c + dy * s) < 4.5 and abs(-dx * s + dy * c) < 1.9:
                return "car"
        hit = self.b.contact()
        if hit:
            return hit
        if abs(st["lat"]) > HALF + 0.5:
            return "offtrack"
        if getattr(self.b.ego, "up_z", 1.0) < 0.7:
            return "flip"
        herr = wrap(st["yaw"] - self.track.heading(st["i"]))
        beta = math.atan2(st["vy"], max(st["vx"], 0.1))
        if abs(herr) > 1.3 or (st["speed"] > 8 and abs(beta) > 0.45):
            return "spin"
        return ""


class WebotsBackend:
    """Drives the ego through car.Car and moves the opponents with the supervisor."""

    def __init__(self, car, track, substeps=4, n_opp=3, lidar_left_first=True):
        self.car = car
        self.car_track = track
        self.ego = car
        self.substeps = substeps
        self.dt = car.dt
        period = int(round(car.dt * 1000)) * substeps
        self.lidar_dev = car.d.getDevice("lidar")
        if self.lidar_dev:
            self.lidar_dev.enable(period)
        self.left_first = lidar_left_first
        self.opp_nodes = [n for n in (car.d.getFromDef(f"OPP_{k}") for k in range(1, n_opp + 1)) if n]
        self.active = []
        self.contacts = False
        try:
            car.node.enableContactPointsTracking(period, True)
            self.contacts = True
        except AttributeError:
            pass

    def reset(self, ego, opps):
        x, y, yaw, v = ego
        self.car.command(0, 0, 0)
        self.car.place(x, y, yaw)
        moving = [(self.car.node, yaw, v)]
        self.active = []
        for k, node in enumerate(self.opp_nodes):
            if k < len(opps):
                s, lat, _ = opps[k]
                ox, oy, oyaw = self.car_track.pose(s, lat)
                self._put(node, ox, oy, oyaw)
                moving.append((node, oyaw, 0.7 * self.car_track.v[self.car_track.at(s)]))
                self.active.append(node)
            else:
                self._park(k)
        # resetPhysics zeroes velocities on the next step, so set them after it
        self.car.d.step()
        for node, h, speed in moving:
            node.setVelocity([speed * math.cos(h), speed * math.sin(h), 0, 0, 0, 0])
        self.car.d.step()
        self.car.v_prev = None
        self.car.read()

    def _put(self, node, x, y, yaw):
        node.getField("translation").setSFVec3f([x, y, 0.36])
        node.getField("rotation").setSFRotation([0, 0, 1, yaw])
        node.resetPhysics()

    def _park(self, k):
        self._put(self.opp_nodes[k], 2000.0 + 20 * k, 2000.0, 0.0)

    def command(self, steer, throttle, brake):
        self.car.command(steer, throttle, brake)

    def step(self):
        for _ in range(self.substeps):
            self.car.aero()
            if self.car.d.step() == -1:
                return False
        self.car.read()
        for k, node in enumerate(self.opp_nodes):
            if node not in self.active:
                self._park(k)
        return True

    def time(self):
        return self.car.d.getTime()

    def opponents(self):
        out = []
        for node in self.active:
            p, R, v = node.getPosition(), node.getOrientation(), node.getVelocity()
            out.append({"x": p[0], "y": p[1], "yaw": math.atan2(R[3], R[0]), "speed": math.hypot(v[0], v[1])})
        return out

    def lidar(self):
        if not self.lidar_dev:
            return np.full(180, LIDAR_RANGE)
        r = np.array(self.lidar_dev.getRangeImage(), dtype=float)
        return r[::-1] if self.left_first else r

    def contact(self):
        if not self.contacts:
            return ""
        for cp in self.car.node.getContactPoints(True):
            if cp.point[2] > 0.15:
                return "barrier"
        return ""
