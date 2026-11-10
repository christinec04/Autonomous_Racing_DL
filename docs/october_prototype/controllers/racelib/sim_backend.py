"""Pure Python stand in for Webots so the RL env can be debugged offline.

A dynamic bicycle model with Pacejka lateral tyres, a friction circle per axle,
downforce and drag from track.py, plus a pedal map from pilot.py, a ray cast LiDAR against barriers at the
road edge and kinematic opponents that follow the racing line at a fixed pace.
It quacks like the Webots backend in env.py.
"""
import math

import numpy as np

from pilot import BRAKE_A, ROLL_K, motor
from track import CDA, CLA, G, HALF, MASS, MU, RHO, WHEELBASE

LF = LR = WHEELBASE / 2
IZ = 1100.0
B_TYRE, C_TYRE = 12.0, 1.4
STEER_MAX = 0.45
CAR_LEN, CAR_W = 4.4, 1.8
LIDAR_X, LIDAR_RANGE, LIDAR_RAYS = 3.55, 80.0, 180
BARRIER = HALF   # Webots smoke test shows contact at |lat| about 5.5 and LiDAR walls about 7 m out


class Body:
    """Ground truth state with the same attribute names as Car."""

    def __init__(self):
        self.x = self.y = self.yaw = 0.0
        self.vx = self.vy = self.yaw_rate = self.speed = 0.0
        self.ax = self.ay = 0.0
        self.up_z = 1.0


class SimBackend:
    def __init__(self, track, dt=0.008, substeps=4, sub=4, seed=None):
        self.track = track
        self.dt = dt
        self.substeps = substeps
        self.sub = sub
        self.ego = Body()
        self.cmd = (0.0, 0.0, 0.0)
        self.opps = []
        self.t = 0.0
        self.rng = np.random.default_rng(seed)
        self.left = track.center + track.nrm * BARRIER
        self.right = track.center - track.nrm * BARRIER
        ang = np.linspace(-math.pi / 2, math.pi / 2, LIDAR_RAYS)
        self.ray_c, self.ray_s = np.cos(ang), np.sin(ang)

    def reset(self, ego, opps):
        """ego is (x, y, yaw, speed), opps a list of (s, lat, pace) or empty."""
        e = self.ego
        e.x, e.y, e.yaw, v = ego
        e.vx, e.vy, e.yaw_rate, e.speed, e.ax, e.ay = v, 0.0, 0.0, v, 0.0, 0.0
        self.opps = [dict(s=s, lat=lat, pace=pace, speed=pace * self.track.v[self.track.at(s)]) for s, lat, pace in opps]
        for o in self.opps:
            self._opp_pose(o)
        self.cmd = (0.0, 0.0, 0.0)

    def command(self, steer, throttle, brake):
        self.cmd = (max(-1.0, min(1.0, steer)), max(0.0, min(1.0, throttle)), max(0.0, min(1.0, brake)))

    def step(self):
        """One control period, returns False when the simulation ended (never here)."""
        h = self.dt / self.sub
        vx0, vy0 = self.ego.vx, self.ego.vy
        for _ in range(self.substeps * self.sub):
            self._integrate(h)
        T = self.substeps * self.dt
        self.ego.ax = (self.ego.vx - vx0) / T
        self.ego.ay = (self.ego.vy - vy0) / T
        for o in self.opps:
            o["speed"] = o["pace"] * self.track.v[self.track.at(o["s"])]
            o["s"] = (o["s"] + o["speed"] * T) % self.track.length
            self._opp_pose(o)
        self.t += T
        return True

    def time(self):
        return self.t

    def _opp_pose(self, o):
        x, y, yaw = self.track.pose(o["s"], o["lat"])
        o["x"], o["y"], o["yaw"] = x, y, yaw

    def _integrate(self, h):
        e = self.ego
        steer, throttle, brake = self.cmd
        d = STEER_MAX * steer
        vx = max(e.vx, 0.0)
        fz = MASS * G + 0.5 * RHO * CLA * vx * vx
        fz_f = fz_r = 0.5 * fz
        # traction control keeps the driven axle inside 70 percent of its grip
        drive = min(throttle * motor(vx) * MASS, 0.7 * MU * fz_r)
        # pedal map calibrated on Webots in pilot.py, wheel damping drag included
        stop = min(BRAKE_A * brake * MASS, MU * fz) + ROLL_K * vx * MASS
        fx_f, fx_r = -0.5 * stop, drive - 0.5 * stop
        if vx < 3.0:
            # kinematic below walking pace, the slip angles are ill conditioned there
            ax = (fx_f + fx_r - 0.5 * RHO * CDA * vx * vx) / MASS
            e.vx = max(0.0, vx + ax * h)
            e.yaw_rate = e.vx * math.tan(d) / WHEELBASE
            e.vy = e.yaw_rate * LR
        else:
            af = d - math.atan2(e.vy + LF * e.yaw_rate, vx)
            ar = -math.atan2(e.vy - LR * e.yaw_rate, vx)
            fy_f = self._lat(af, fz_f, fx_f)
            fy_r = self._lat(ar, fz_r, fx_r)
            fx_f = math.copysign(min(abs(fx_f), 0.98 * MU * fz_f), fx_f)
            fx_r = math.copysign(min(abs(fx_r), 0.98 * MU * fz_r), fx_r)
            cd, sd = math.cos(d), math.sin(d)
            drag = 0.5 * RHO * CDA * vx * vx
            dvx = (fx_r + fx_f * cd - fy_f * sd - drag) / MASS + e.vy * e.yaw_rate
            dvy = (fy_r + fy_f * cd + fx_f * sd) / MASS - vx * e.yaw_rate
            dr = (LF * (fy_f * cd + fx_f * sd) - LR * fy_r) / IZ
            e.vx = max(0.0, vx + dvx * h)
            e.vy += dvy * h
            e.yaw_rate += dr * h
        c, s = math.cos(e.yaw), math.sin(e.yaw)
        e.x += (e.vx * c - e.vy * s) * h
        e.y += (e.vx * s + e.vy * c) * h
        e.yaw = (e.yaw + e.yaw_rate * h + math.pi) % (2 * math.pi) - math.pi
        e.speed = math.hypot(e.vx, e.vy)

    @staticmethod
    def _lat(alpha, fz, fx):
        """Pacejka lateral force shrunk by the longitudinal force already on the axle."""
        cap = MU * fz
        room = math.sqrt(max(cap * cap - fx * fx, (0.05 * cap) ** 2))
        return room * math.sin(C_TYRE * math.atan(B_TYRE * alpha))

    def opponents(self):
        return [dict(x=o["x"], y=o["y"], yaw=o["yaw"], speed=o["speed"]) for o in self.opps]

    def lidar(self):
        """180 ranges over a half circle, index 0 points right, positive angles to the left."""
        e = self.ego
        c, s = math.cos(e.yaw), math.sin(e.yaw)
        ox, oy = e.x + LIDAR_X * c, e.y + LIDAR_X * s
        dx = c * self.ray_c - s * self.ray_s
        dy = s * self.ray_c + c * self.ray_s
        i, _, _ = self.track.project(e.x, e.y, "sim_lidar")
        w = (i + np.arange(-45, 46)) % self.track.n
        best = np.full(LIDAR_RAYS, LIDAR_RANGE)
        for wall in (self.left, self.right):
            a, b = wall[w[:-1]], wall[w[1:]]
            ex, ey = b[:, 0] - a[:, 0], b[:, 1] - a[:, 1]
            qx, qy = a[:, 0] - ox, a[:, 1] - oy
            den = dx[:, None] * ey[None] - dy[:, None] * ex[None]
            den = np.where(np.abs(den) < 1e-9, 1e-9, den)
            t = (qx[None] * ey[None] - qy[None] * ex[None]) / den
            u = (qx[None] * dy[:, None] - qy[None] * dx[:, None]) / den
            t = np.where((t > 0) & (u >= 0) & (u <= 1), t, LIDAR_RANGE)
            best = np.minimum(best, t.min(axis=1))
        for o in self.opps:
            px, py = o["x"] + 1.5 * math.cos(o["yaw"]) - ox, o["y"] + 1.5 * math.sin(o["yaw"]) - oy
            along = px * dx + py * dy
            miss = (px - along * dx) ** 2 + (py - along * dy) ** 2
            hit = (along > 0) & (miss < 1.3 ** 2)
            best = np.where(hit, np.minimum(best, along - np.sqrt(np.maximum(1.3 ** 2 - miss, 0))), best)
        return best

    def contact(self):
        """Collision reason or an empty string, from the corners of the body box."""
        e = self.ego
        c, s = math.cos(e.yaw), math.sin(e.yaw)
        for fwd in (-0.7, CAR_LEN - 0.7):
            for side in (-CAR_W / 2, CAR_W / 2):
                px, py = e.x + fwd * c - side * s, e.y + fwd * s + side * c
                _, _, lat = self.track.project(px, py, "sim_corner")
                if abs(lat) > BARRIER:
                    return "barrier"
        for o in self.opps:
            dx, dy = o["x"] - e.x, o["y"] - e.y
            fx, fy = dx * c + dy * s, -dx * s + dy * c
            if abs(fx) < CAR_LEN and abs(fy) < CAR_W:
                return "car"
        return ""
