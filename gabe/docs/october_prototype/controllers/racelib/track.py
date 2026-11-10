"""Track geometry shared by the world generator and every controller.

The centerline is the same 22 corner street circuit the proposal world used.
On top of it we compute a minimum curvature racing line and a speed profile
that respects the friction circle with aerodynamic downforce.
"""
import json
import math
import os

import numpy as np

CORNERS = [
    (-300, 150), (40, 150), (80, 100), (40, 60), (120, 20), (300, 20), (330, -40), (250, -60),
    (250, -150), (120, -150), (120, -90), (40, -90), (40, -160), (-120, -160), (-140, -100),
    (-240, -100), (-240, -170), (-330, -170), (-330, -40), (-250, -40), (-250, 40), (-330, 40),
]
WIDTH = 14.0
HALF = WIDTH / 2
DS = 2.0
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "track.json")

# vehicle model used by the planner and the shield, matches protos/RaceCar.proto
G = 9.81
MASS = 860.0
MU = 1.6
RHO = 1.2
CLA = 3.0          # downforce coefficient times frontal area
CDA = 0.9          # drag coefficient times frontal area
P_MAX = 450e3      # motor power in W
WHEELBASE = 3.0
V_TOP = 85.0


def grip(v):
    """Maximum total tyre acceleration at speed v, downforce adds normal load."""
    return MU * (G + 0.5 * RHO * CLA * v * v / MASS)


def drive_accel(v):
    return min(MU * G, P_MAX / (MASS * max(v, 1.0))) - 0.5 * RHO * CDA * v * v / MASS


def _centerline():
    n = len(CORNERS)

    def cut(i):
        v, a, b = CORNERS[i], CORNERS[i - 1], CORNERS[(i + 1) % n]
        la, lb = math.dist(v, a), math.dist(v, b)
        c = min(24, 0.45 * la, 0.45 * lb)
        A = (v[0] - (v[0] - a[0]) / la * c, v[1] - (v[1] - a[1]) / la * c)
        B = (v[0] + (b[0] - v[0]) / lb * c, v[1] + (b[1] - v[1]) / lb * c)
        return A, v, B

    raw = []
    for i in range(n):
        _, _, b0 = cut(i)
        a1, v1, b1 = cut((i + 1) % n)
        for t in np.linspace(0, 1, 50, endpoint=False):
            raw.append((b0[0] + (a1[0] - b0[0]) * t, b0[1] + (a1[1] - b0[1]) * t))
        for t in np.linspace(0, 1, 50, endpoint=False):
            u = 1 - t
            raw.append((u * u * a1[0] + 2 * u * t * v1[0] + t * t * b1[0], u * u * a1[1] + 2 * u * t * v1[1] + t * t * b1[1]))
    raw = np.array(raw)
    raw[:, 1] *= -1  # z up world, flip y so the layout matches the plan view
    return resample(raw)


def resample(xy, ds=DS):
    closed = np.vstack([xy, xy[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    count = int(round(s[-1] / ds))
    q = np.linspace(0, s[-1], count, endpoint=False)
    return np.stack([np.interp(q, s, closed[:, 0]), np.interp(q, s, closed[:, 1])], axis=1)


def frame(xy):
    d = np.roll(xy, -1, axis=0) - np.roll(xy, 1, axis=0)
    t = d / np.linalg.norm(d, axis=1, keepdims=True)
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)
    return t, nrm


def curvature(xy):
    a, b, c = np.roll(xy, 1, axis=0), xy, np.roll(xy, -1, axis=0)
    ab, bc = b - a, c - b
    cross = ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]
    den = np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(c - a, axis=1)
    return 2 * cross / np.maximum(den, 1e-9)


def racing_line(center, nrm, margin=2.2, iters=4000):
    """Minimum curvature line by relaxing lateral offsets inside the track."""
    off = np.zeros(len(center))
    lim = HALF - margin
    for _ in range(iters):
        p = center + nrm * off[:, None]
        mid = 0.5 * (np.roll(p, 1, axis=0) + np.roll(p, -1, axis=0))
        off += 0.5 * np.sum((mid - p) * nrm, axis=1)
        off = np.clip(off, -lim, lim)
    return off


def speed_profile(kappa, ds, v_top=V_TOP):
    """Forward backward pass, combined slip limited by the friction circle."""
    n = len(kappa)
    k = np.maximum(np.abs(kappa), 1e-6)
    v = np.minimum(v_top, np.sqrt(MU * G / np.maximum(k - MU * 0.5 * RHO * CLA / MASS, 1e-6)))
    v = np.where(k * MASS < MU * 0.5 * RHO * CLA, v_top, v)
    for _ in range(2):
        for i in range(2 * n):
            a, b = i % n, (i + 1) % n
            lat = v[a] ** 2 * k[a]
            room = max(grip(v[a]) ** 2 - lat ** 2, 0.0) ** 0.5
            v[b] = min(v[b], math.sqrt(v[a] ** 2 + 2 * min(room, drive_accel(v[a])) * ds))
        for i in range(2 * n, 0, -1):
            a, b = i % n, (i - 1) % n
            lat = v[a] ** 2 * k[a]
            room = max(grip(v[a]) ** 2 - lat ** 2, 0.0) ** 0.5
            v[b] = min(v[b], math.sqrt(v[a] ** 2 + 2 * room * 0.92 * ds))
    return v


def build():
    center = _centerline()
    _, nrm = frame(center)
    off = racing_line(center, nrm)
    # the racing line stays indexed like the centerline so one s works for both
    line = center + nrm * off[:, None]
    kappa_c = curvature(center)
    kappa = np.convolve(np.tile(curvature(line), 3), np.ones(5) / 5, "same")[len(line):2 * len(line)]
    v = speed_profile(kappa, DS)
    data = {"center": center.tolist(), "offset": off.tolist(), "kappa": kappa.tolist(),
            "kappa_center": kappa_c.tolist(), "v": v.tolist(), "ds": DS}
    with open(CACHE, "w") as fh:
        json.dump(data, fh)
    return data


class Track:
    """Fast lookups against the cached track."""

    def __init__(self):
        if not os.path.exists(CACHE):
            build()
        with open(CACHE) as fh:
            d = json.load(fh)
        self.center = np.array(d["center"])
        self.offset = np.array(d["offset"])
        self.kappa = np.array(d["kappa"])
        self.kappa_center = np.array(d["kappa_center"])
        self.v = np.array(d["v"])
        self.ds = d["ds"]
        self.n = len(self.center)
        self.length = self.n * self.ds
        self.tan, self.nrm = frame(self.center)
        self.line = self.center + self.nrm * self.offset[:, None]
        self._last = {}

    def project(self, x, y, key=None):
        """Index, arc length and signed lateral offset of a point, positive to the left."""
        last = self._last.get(key)
        if last is None:
            i = int(np.argmin(np.sum((self.center - (x, y)) ** 2, axis=1)))
        else:
            w = (last + np.arange(-40, 41)) % self.n
            i = int(w[np.argmin(np.sum((self.center[w] - (x, y)) ** 2, axis=1))])
            if np.sum((self.center[i] - (x, y)) ** 2) > 30 ** 2:
                i = int(np.argmin(np.sum((self.center - (x, y)) ** 2, axis=1)))
        self._last[key] = i
        dx, dy = x - self.center[i, 0], y - self.center[i, 1]
        along = dx * self.tan[i, 0] + dy * self.tan[i, 1]
        lat = dx * self.nrm[i, 0] + dy * self.nrm[i, 1]
        return i, (i * self.ds + along) % self.length, lat

    def heading(self, i):
        return math.atan2(self.tan[i, 1], self.tan[i, 0])

    def at(self, s):
        return int(round(s / self.ds)) % self.n

    def pose(self, s, lat):
        i = self.at(s)
        p = self.center[i] + self.nrm[i] * lat
        return float(p[0]), float(p[1]), self.heading(i)

    def ahead(self, i, metres):
        return (i + np.round(np.asarray(metres) / self.ds).astype(int)) % self.n


if __name__ == "__main__":
    d = build()
    t = Track()
    v = t.v
    lap = float(np.sum(t.ds / v))
    print(f"length {t.length:.0f} m, {t.n} points, v min {v.min():.1f} max {v.max():.1f} m/s, ideal lap {lap:.1f} s")
    print(f"racing line offset range {t.offset.min():.2f} .. {t.offset.max():.2f} m")
