"""Classical controllers: Pure Pursuit (baseline + opponents) and PID."""
from __future__ import annotations

import numpy as np

from .sim import DEFAULT_PARAMS, G, Centerline


def curvature_speed_profile(cl: Centerline, mu: float, v_max: float, a_long: float = 6.0,
                            safety: float = 0.85, smooth: int = 15) -> np.ndarray:
    """Max speed at each centerline point: lateral grip limit + forward/backward accel passes."""
    k = np.abs(np.convolve(np.concatenate([cl.curvature[-smooth:], cl.curvature, cl.curvature[:smooth]]),
                           np.ones(smooth) / smooth, mode="same")[smooth:-smooth])
    v = np.minimum(v_max, np.sqrt(safety * mu * G / np.maximum(k, 1e-4)))
    ds = cl.seg_len
    n = len(v)
    for _ in range(2):  # two laps so the wrap-around is consistent
        for i in range(n):  # acceleration limit (forward)
            j = (i + 1) % n
            v[j] = min(v[j], np.sqrt(v[i] ** 2 + 2 * a_long * ds[i]))
        for i in range(n - 1, -1, -1):  # braking limit (backward)
            j = (i + 1) % n
            v[i] = min(v[i], np.sqrt(v[j] ** 2 + 2 * a_long * ds[i]))
    return v


class PurePursuit:
    """Pure Pursuit on the centerline (optionally with a lateral offset) [Coulter 1992]."""

    def __init__(self, cl: Centerline, speed_scale: float = 1.0, v_cap: float = 20.0,
                 lookahead_base: float = 0.8, lookahead_gain: float = 0.25,
                 offset: float = 0.0, mu: float = DEFAULT_PARAMS["mu"]):
        self.cl = cl
        self.wb = DEFAULT_PARAMS["lf"] + DEFAULT_PARAMS["lr"]
        self.profile = curvature_speed_profile(cl, mu, v_cap) * speed_scale
        self.lb, self.lg = lookahead_base, lookahead_gain
        self.offset = offset
        self.hint = None

    def reset(self):
        self.hint = None

    def target_speed(self, x, y):
        i, *_ = self.cl.project(x, y, self.hint)
        return float(self.profile[i])

    def act(self, x, y, yaw, v):
        i, s, d, _ = self.cl.project(x, y, self.hint)
        self.hint = i
        ld = self.lb + self.lg * max(v, 0.0)
        tx, ty, _ = self.cl.pose_at(s + ld, self.offset)
        dx, dy = tx - x, ty - y
        ly = -dx * np.sin(yaw) + dy * np.cos(yaw)
        L2 = dx * dx + dy * dy
        steer = np.arctan(2 * self.wb * ly / max(L2, 1e-6))
        steer = float(np.clip(steer, DEFAULT_PARAMS["s_min"], DEFAULT_PARAMS["s_max"]))
        return steer, float(self.profile[i])


class PID:
    def __init__(self, kp, ki, kd, dt, i_lim=1.0):
        self.kp, self.ki, self.kd, self.dt, self.i_lim = kp, ki, kd, dt, i_lim
        self.reset()

    def reset(self):
        self.i = 0.0
        self.prev = None

    def __call__(self, err):
        self.i = float(np.clip(self.i + err * self.dt, -self.i_lim, self.i_lim))
        d = 0.0 if self.prev is None else (err - self.prev) / self.dt
        self.prev = err
        return self.kp * err + self.ki * self.i + self.kd * d


class PIDFollower:
    """PID steering on centerline cross-track + heading error, with a speed profile.

    Used for the PID opponents and (wrapped by the APF) for the PID+APF baseline.
    """

    def __init__(self, cl: Centerline, dt: float, speed_scale: float = 1.0, v_cap: float = 20.0,
                 offset: float = 0.0, mu: float = DEFAULT_PARAMS["mu"], preview: float = 0.6):
        self.cl = cl
        self.pid = PID(kp=0.9, ki=0.05, kd=0.08, dt=dt)
        self.profile = curvature_speed_profile(cl, mu, v_cap) * speed_scale
        self.offset = offset
        self.preview = preview
        self.hint = None

    def reset(self):
        self.pid.reset()
        self.hint = None

    def act(self, x, y, yaw, v):
        i, s, d, _ = self.cl.project(x, y, self.hint)
        self.hint = i
        # preview point ahead to absorb steering lag
        j = int((i + max(1, int((self.preview + 0.1 * v) / 0.1))) % len(self.cl.xy))
        h_err = (self.cl.heading[j] - yaw + np.pi) % (2 * np.pi) - np.pi
        e = (self.offset - d)  # +: need to go left
        steer = self.pid(e) + 0.9 * h_err
        steer = float(np.clip(steer, DEFAULT_PARAMS["s_min"], DEFAULT_PARAMS["s_max"]))
        return steer, float(self.profile[i])
