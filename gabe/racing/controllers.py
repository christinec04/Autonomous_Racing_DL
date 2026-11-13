"""Classical controllers, Pure Pursuit and PID, used for the baselines and the opponents."""
from __future__ import annotations

import numpy as np

from .sim import DEFAULT_PARAMS, G, Centerline

WB = DEFAULT_PARAMS["lf"] + DEFAULT_PARAMS["lr"]
S_MIN, S_MAX = DEFAULT_PARAMS["s_min"], DEFAULT_PARAMS["s_max"]


def curvature_speed_profile(cl: Centerline, mu: float, v_max: float, a_long: float = 6.0,
                            safety: float = 0.85, smooth: int = 15) -> np.ndarray:
    """Highest speed at each centerline point from the grip limit in corners and the acceleration limit."""
    k = np.abs(np.convolve(np.concatenate([cl.curvature[-smooth:], cl.curvature, cl.curvature[:smooth]]),
                           np.ones(smooth) / smooth, mode="same")[smooth:-smooth])
    v = np.minimum(v_max, np.sqrt(safety * mu * G / np.maximum(k, 1e-4)))
    ds = cl.seg_len
    n = len(v)
    for _ in range(2):  # two laps so the profile is consistent where the lap wraps around
        for i in range(n):
            j = (i + 1) % n
            v[j] = min(v[j], np.sqrt(v[i] ** 2 + 2 * a_long * ds[i]))  # accelerating forward
        for i in range(n - 1, -1, -1):
            j = (i + 1) % n
            v[i] = min(v[i], np.sqrt(v[j] ** 2 + 2 * a_long * ds[i]))  # braking, going backward
    return v


class PurePursuit:
    """Pure Pursuit on the centerline [Coulter 1992]."""

    def __init__(self, cl: Centerline, speed_scale: float = 1.0, v_cap: float = 20.0,
                 lookahead_base: float = 0.8, lookahead_gain: float = 0.25,
                 offset: float = 0.0, mu: float = DEFAULT_PARAMS["mu"]):
        self.cl = cl
        self.profile = curvature_speed_profile(cl, mu, v_cap) * speed_scale
        self.lb, self.lg = lookahead_base, lookahead_gain
        self.offset = offset
        self.hint = None

    def act(self, x, y, yaw, v):
        i, s, d, _ = self.cl.project(x, y, self.hint)
        self.hint = i
        ld = self.lb + self.lg * max(v, 0.0)
        tx, ty, _ = self.cl.pose_at(s + ld, self.offset)
        dx, dy = tx - x, ty - y
        ly = -dx * np.sin(yaw) + dy * np.cos(yaw)
        steer = np.arctan(2 * WB * ly / max(dx * dx + dy * dy, 1e-6))
        return float(np.clip(steer, S_MIN, S_MAX)), float(self.profile[i])


class PID:
    def __init__(self, kp, ki, kd, dt, i_lim=1.0):
        self.kp, self.ki, self.kd, self.dt, self.i_lim = kp, ki, kd, dt, i_lim
        self.i = 0.0
        self.prev = None

    def __call__(self, err):
        self.i = float(np.clip(self.i + err * self.dt, -self.i_lim, self.i_lim))
        d = 0.0 if self.prev is None else (err - self.prev) / self.dt
        self.prev = err
        return self.kp * err + self.ki * self.i + self.kd * d


class PIDFollower:
    """PID steering on the cross-track and heading error, plus curvature feed-forward and a speed profile.

    Used for the PID opponents and, with the APF added, for the PID+APF baseline.
    """

    def __init__(self, cl: Centerline, dt: float, speed_scale: float = 1.0, v_cap: float = 20.0,
                 offset: float = 0.0, mu: float = DEFAULT_PARAMS["mu"], preview: float = 0.3,
                 kp: float = 0.3, ki: float = 0.05, kd: float = 0.0, k_head: float = 0.6):
        self.cl = cl
        self.k_head = k_head
        self.pid = PID(kp=kp, ki=ki, kd=kd, dt=dt)
        self.profile = curvature_speed_profile(cl, mu, v_cap) * speed_scale
        self.offset = offset
        self.preview = preview
        self.hint = None

    def act(self, x, y, yaw, v):
        i, s, d, h = self.cl.project(x, y, self.hint)
        self.hint = i
        # curvature feed-forward, averaged over a short window ahead
        j0 = int(self.preview / 0.1)
        idx = (i + j0 + np.arange(-3, 4)) % len(self.cl.xy)
        kappa = float(np.mean(self.cl.curvature[idx]))
        ff = np.arctan(WB * kappa)
        h_err = (h - yaw + np.pi) % (2 * np.pi) - np.pi
        e = self.offset - d  # positive when the car must move left
        steer = ff + self.pid(e) + self.k_head * h_err
        return float(np.clip(steer, S_MIN, S_MAX)), float(self.profile[i])
