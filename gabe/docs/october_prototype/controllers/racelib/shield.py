"""Safety shields that filter a driving command before it reaches the car.

  none       passthrough, still reports how much of the friction circle the command asks for
  geometric  classic artificial potential field (Khatib 1986) as used in course self driving work.
             Barrier and opponent potentials on a fixed 15 m preview, override by adding steering
             along the negative gradient and braking in proportion to the potential. Knows nothing about grip.
  friction   friction aware shield. Horizon sized by stopping distance, opponent field stretched by
             closing speed, a braking envelope from the track speed map, and every correction is
             expressed as an acceleration and allocated inside the friction circle grip(v).

  sh = make_shield(kind, track)
  steer, throttle, brake, info = sh.filter(state, opponents, steer, throttle, brake)
"""
import math

import numpy as np

from pilot import (CAR_HALF_WIDTH, CAR_LENGTH, REAR_TO_CENTER, STEER_MAX, corner_speed, gap_ahead,
                   lat_accel, long_accel, pedals, steer_for)
from track import G, HALF, MU, WHEELBASE, grip


def body_center(st):
    return st["x"] + REAR_TO_CENTER * math.cos(st["yaw"]), st["y"] + REAR_TO_CENTER * math.sin(st["yaw"])


def ctrv(x, y, yaw, steer, dist, c=None):
    """Point reached after driving dist metres on an arc, by default the kinematic arc of the steering angle."""
    if c is None:
        c = math.tan(STEER_MAX * steer) / WHEELBASE
    if abs(c) < 1e-4:
        return x + dist * math.cos(yaw), y + dist * math.sin(yaw), yaw
    return (x + (math.sin(yaw + c * dist) - math.sin(yaw)) / c,
            y - (math.cos(yaw + c * dist) - math.cos(yaw)) / c, yaw + c * dist)


def local_lat(track, x, y, i_guess, window=12):
    """Signed lateral offset and index of a point near index i_guess."""
    w = (i_guess + np.arange(-window, window + 1)) % track.n
    d = track.center[w] - (x, y)
    k = int(w[np.argmin(np.einsum("ij,ij->i", d, d))])
    lat = (x - track.center[k, 0]) * track.nrm[k, 0] + (y - track.center[k, 1]) * track.nrm[k, 1]
    return lat, k


def wall_potential(lat, eta, d0):
    """Khatib barrier potential on the clearance between the car side and the nearer barrier.
    Returns U and dU/dlat."""
    c = max(HALF - abs(lat) - CAR_HALF_WIDTH, 0.05)
    if c >= d0:
        return 0.0, 0.0
    u = 0.5 * eta * (1 / c - 1 / d0) ** 2
    return u, eta * (1 / c - 1 / d0) / c ** 2 * math.copysign(1.0, lat)


def ellipse_potential(dx, dy, a, b, eta):
    """Repulsive bump inside an ellipse with semi axes a, b. Returns U, dU/ddx, dU/ddy."""
    r = math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
    if r >= 1.0:
        return 0.0, 0.0, 0.0
    r = max(r, 0.1)
    du_dr = -2 * eta * (1 / r - 1) / r ** 2
    return eta * (1 / r - 1) ** 2, du_dr * dx / (a * a * r), du_dr * dy / (b * b * r)


def lat_rate(track, st):
    """Speed across the track, positive to the left, from heading and body slip."""
    beta = math.atan2(st.get("vy", 0.0), max(st.get("vx", st["speed"]), 1.0))
    return st["speed"] * math.sin(st["yaw"] + beta - track.heading(track.at(st["s"])))


class Shield:
    """Passthrough. Subclasses override correct()."""
    kind = "none"
    V_CREEP = 3.0   # below this speed a shield may only steer, so it can never park the car for good

    def __init__(self, track):
        self.t = track

    def filter(self, st, opponents, steer, throttle, brake):
        v = st["speed"]
        steer2, throttle2, brake2, reason, u = self.correct(st, opponents, steer, throttle, brake)
        if v < self.V_CREEP:
            throttle2, brake2 = throttle, brake
        ax = long_accel(v, throttle2, brake2)
        ay = lat_accel(v, steer2)
        changed = abs(ax - long_accel(v, throttle, brake)) > 0.5 or abs(steer2 - steer) > 0.005
        info = {"intervened": reason != "" and changed, "reason": reason, "u": u,
                "grip_used": math.hypot(ax, ay) / grip(v), "ax_cmd": ax, "ay_cmd": ay}
        return steer2, throttle2, brake2, info

    def correct(self, st, opponents, steer, throttle, brake):
        return steer, throttle, brake, "", 0.0


class GeometricShield(Shield):
    """Fixed size potential field with a fixed preview time."""
    kind = "geometric"
    PREVIEW = (0.0, 0.25, 0.5)   # seconds along the current steering arc, 30 m ahead at 60 m/s
    WALL_ETA, WALL_D0 = 1.47, 2.0   # U reaches U_SAFE at 0.6 m clearance
    OPP_A, OPP_B, OPP_ETA = 10.0, 3.0, 16.0   # U reaches U_SAFE at 0.8 of the ellipse
    U_SAFE = 1.0
    K_STEER, STEER_ADD_MAX = 0.02, 0.15  # steer per unit gradient, at most 0.15 of full lock (3.9 deg)
    K_BRAKE, A_BRAKE_MAX = 4.0, 0.8 * MU * G  # m/s^2 per unit of potential above U_SAFE

    def correct(self, st, opponents, steer, throttle, brake):
        t, v = self.t, max(st["speed"], 0.5)
        cx, cy = body_center(st)
        worst = (0.0, 0.0, 0.0)
        for tau in self.PREVIEW:
            d = v * tau
            px, py, _ = ctrv(cx, cy, st["yaw"], steer, d)
            lat, k = local_lat(t, px, py, t.ahead(st["i"], d))
            u, du = wall_potential(lat, self.WALL_ETA, self.WALL_D0)
            gx, gy = du * t.nrm[k, 0], du * t.nrm[k, 1]
            for o in opponents:
                ox = o["x"] + REAR_TO_CENTER * math.cos(o["yaw"]) + o["speed"] * tau * math.cos(o["yaw"])
                oy = o["y"] + REAR_TO_CENTER * math.sin(o["yaw"]) + o["speed"] * tau * math.sin(o["yaw"])
                c, s = math.cos(o["yaw"]), math.sin(o["yaw"])
                dx, dy = (px - ox) * c + (py - oy) * s, -(px - ox) * s + (py - oy) * c
                uo, gdx, gdy = ellipse_potential(dx, dy, self.OPP_A, self.OPP_B, self.OPP_ETA)
                u += uo
                gx += gdx * c - gdy * s
                gy += gdx * s + gdy * c
            if u > worst[0]:
                worst = (u, gx, gy)
        u, gx, gy = worst
        if u <= self.U_SAFE:
            return steer, throttle, brake, "", u
        yaw = st["yaw"]
        push_left = -(-gx * math.sin(yaw) + gy * math.cos(yaw))
        steer += max(-self.STEER_ADD_MAX, min(self.STEER_ADD_MAX, self.K_STEER * push_left))
        decel = min(self.A_BRAKE_MAX, self.K_BRAKE * (u - self.U_SAFE))
        brake, throttle = max(brake, pedals(v, -decel)[1]), 0.0
        return max(-1.0, min(1.0, steer)), throttle, brake, "apf", u


class FrictionShield(Shield):
    """Grip aware shield. All corrections are accelerations allocated inside grip(v)."""
    kind = "friction"
    MARGIN = 0.9            # use 90 % of the modelled friction circle
    T_REACT = 0.3           # s, actuation and estimation delay
    BRAKE_FRAC = 0.8        # braking deceleration assumed for horizons, fraction of grip
    K_ENV = 6.0             # 1/s, speed error to deceleration gain on the envelope
    WALL_ETA, WALL_D0 = 1.47, 2.0
    OPP_A0, OPP_B, OPP_ETA = 10.0, 3.0, 16.0   # same base ellipse as the geometric shield
    U_SAFE = 1.0
    K_AY = 6.0              # m/s^2 of lateral correction per unit potential above U_SAFE
    MIN_BRAKE_FRAC = 0.3    # always allow this much braking even in a corner

    def horizon(self, v):
        """Distance to stop from v with reaction time, d = v t_react + v^2 / (2 a_brake)."""
        return v * self.T_REACT + v * v / (2 * self.BRAKE_FRAC * grip(v))

    def envelope(self, st):
        """Highest speed from which every point of the speed map ahead can still be reached by braking,
        and the deceleration of the braking curve that binds (0 when the car is in the slow section itself)."""
        t, v = self.t, st["speed"]
        dist = np.arange(0.0, max(self.horizon(v), 40.0) + 4.0, 4.0)
        idx = t.ahead(st["i"], dist)
        shift = st["lat"] - t.offset[st["i"]]
        k = t.kappa[idx] / np.maximum(1 - t.kappa[idx] * shift, 0.2)
        vp = np.minimum(t.v[idx], corner_speed(k))
        a_b = self.BRAKE_FRAC * grip(vp)
        reach = np.sqrt(vp ** 2 + 2 * a_b * dist)
        k = int(np.argmin(reach))
        return float(reach[k]), float(a_b[k]) if k > 0 else 0.0

    def correct(self, st, opponents, steer, throttle, brake):
        t, v = self.t, max(st["speed"], 0.5)
        g = self.MARGIN * grip(v)
        ax = long_accel(v, throttle, brake)
        ay = lat_accel(v, steer)
        ax0, ay0 = ax, ay
        reasons, u_max = [], 0.0
        priority = None

        # (b) braking envelope from the speed map
        v_allow, a_curve = self.envelope(st)
        cap = self.K_ENV * (v_allow - v) - (a_curve if v > v_allow - 2.0 else 0.0)
        if ax > cap:
            ax = max(cap, -g)
            if v > v_allow + 0.5:
                reasons.append("envelope")
                priority = "x"

        # (a) barriers, preview time grows with the lateral speed that has to be cancelled
        cx, cy = body_center(st)
        vn = abs(lat_rate(t, st))
        tau = self.T_REACT + vn / g
        u, du = 0.0, 0.0
        # the path the tyres can actually hold, curvature limited by understeer and by grip
        c = lat_accel(v, steer) / (v * v)
        c = math.copysign(min(abs(c), g / (v * v)), c)
        for d in (0.5 * v * tau, v * tau):
            lat, _ = local_lat(t, *ctrv(cx, cy, st["yaw"], steer, d, c)[:2], t.ahead(st["i"], d))
            u, du = max((u, du), wall_potential(lat, self.WALL_ETA, self.WALL_D0))
        u_max = u
        if u > self.U_SAFE:
            ay += -math.copysign(1.0, du) * min(self.K_AY * (u - self.U_SAFE), 2 * g)
            reasons.append("wall")
            priority = "y"

        # (a) opponents, ellipse stretched behind each car by the closing stopping distance
        s_c = (st["s"] + REAR_TO_CENTER) % t.length
        for o in opponents:
            gap = gap_ahead(t, s_c, o["s"] + REAR_TO_CENTER)
            if gap < -2.0:
                continue
            closing = max(v - o["speed"], 0.0)
            a = self.OPP_A0 + closing * self.T_REACT + closing ** 2 / (2 * self.BRAKE_FRAC * grip(v))
            # also look T_REACT ahead with both cars' lateral speed across the track
            drift = lat_rate(t, st) - lat_rate(t, o)
            dlat = st["lat"] - o["lat"]
            dlat_next = dlat + drift * self.T_REACT
            if abs(dlat_next) < abs(dlat) and gap < CAR_LENGTH + 4.0:
                dlat = dlat_next if dlat * dlat_next > 0 else 0.0
            uo, _, _ = ellipse_potential(max(gap, 0.0), dlat, a, self.OPP_B, self.OPP_ETA)
            u_max = max(u_max, uo)
            if uo <= self.U_SAFE:
                continue
            free = max(gap - CAR_LENGTH - 1.0, 0.5)
            t_hit = free / max(closing, 0.5)
            need_y = max(2 * CAR_HALF_WIDTH + 0.5 - abs(dlat), 0.0)
            side = math.copysign(1.0, dlat) if abs(dlat) > 0.3 else (1.0 if st["lat"] < 0 else -1.0)
            room_after = HALF - CAR_HALF_WIDTH - 0.5 - side * (st["lat"] + side * need_y)
            ay_need = 2 * need_y / t_hit ** 2
            if gap < CAR_LENGTH + 1.0:
                # already overlapping, braking cannot help, push sideways with what the tyres have left
                ay += side * min(self.K_AY * (uo - self.U_SAFE), max(g - abs(ay), 0.3 * g))
                priority = "y"
                reasons.append("opp_side")
            elif ay_need < g - abs(ay) and room_after > 0:
                ay += side * ay_need * 1.2
                priority = priority or "y"
                reasons.append("opp_steer")
            else:
                ax = min(ax, -min(closing ** 2 / (2 * max(free - 2.0, 0.5)) + 2.0, g))
                priority = "x"
                reasons.append("opp_brake")

        over = math.hypot(ax, ay) > g and ax > -self.MIN_BRAKE_FRAC * g
        if not reasons and ax == ax0 and not over:
            return steer, throttle, brake, "", u_max
        if over and not reasons:
            reasons.append("circle")   # the command alone leaves the friction circle, trim the pedals

        # (c) allocate inside the friction circle, keep the axis the manoeuvre needs
        if priority in ("y", None):
            ay = max(-max(g, abs(ay0)), min(max(g, abs(ay0)), ay))
            room = math.sqrt(max(g * g - min(ay * ay, g * g), 0.0))
            ax = max(min(ax, room), -max(room, self.MIN_BRAKE_FRAC * g))
        else:
            ax = max(ax, -g)
            room = math.sqrt(max(g * g - ax * ax, 0.0))
            if abs(ay) > max(room, abs(ay0)):
                ay = math.copysign(max(room, abs(ay0)), ay)
            if ax < 0:
                # trail braking, keep the path the driver asked for and brake with what is left
                ax = max(ax, -max(math.sqrt(max(g * g - min(ay0 * ay0, g * g), 0.0)), self.MIN_BRAKE_FRAC * g))
        if ay != ay0:
            steer = max(-1.0, min(1.0, steer_for(v, ay)))
        throttle, brake = pedals(v, ax)
        return steer, throttle, brake, "+".join(reasons) or "cap", u_max


def make_shield(kind, track, **params):
    cls = {"none": Shield, "geometric": GeometricShield, "friction": FrictionShield}[kind]
    sh = cls(track)
    for k, val in params.items():
        setattr(sh, k.upper(), val)
    return sh
