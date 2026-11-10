"""Scripted driver used by the opponents and as the stand in policy for the shield experiment.

Pure pursuit on the racing line with a speed dependent lookahead, plus a PI tracker on
pace times the friction circle speed profile. aggression scales the target speed, so
aggression a asks the tyres for about a squared times the grip the profile was built on.
That makes the driver brake later and carry more speed into corners than is possible.
"""
import math

import numpy as np

from track import CDA, CLA, G, HALF, MASS, MU, P_MAX, RHO, V_TOP, WHEELBASE, grip

STEER_MAX = 0.45                          # rad at steer = 1, matches RaceCar.proto
REAR_TO_CENTER = 1.5                      # car origin is the rear axle, the body centre is 1.5 m ahead
CAR_HALF_WIDTH = 0.9
CAR_LENGTH = 4.4
# Actuator map fitted to runs/shield_test/calib/calib.json (flat plane, shield_test regime=calib).
BRAKE_A = 32.0                            # m/s^2 of braking per unit brake intensity, saturates at the tyres
MOTOR_A = 8.5                             # m/s^2 at full throttle before the power limit
ROLL_K = 0.095                            # 1/s, wheel damping drag when coasting, linear in speed
K_US = 8e-4                               # s^2/m, understeer, ay = v^2 tan(delta) / (L + K_US v^2)
TRACTION = 0.55                           # drive acceleration limit as a fraction of grip, rear wheel drive
COUNTER_STEER = 0.8                       # fraction of the excess body slip angle steered against
SLIP_FREE = math.radians(2.5)             # body slip that normal cornering produces, no counter steer below it
BRAKE_FRAC = 0.7                          # braking deceleration as a fraction of grip, beyond this the rear axle locks
MIN_BRAKE = 0.3                           # a driver always keeps this much braking, even at full cornering load
PASS_GAP = 3.5                            # centre to centre lateral spacing when passing or alongside, m


def coast(v):
    """Deceleration with no pedal, wheel damping plus aerodynamic drag."""
    return ROLL_K * v + 0.5 * RHO * CDA * v * v / MASS


def motor(v):
    return min(MOTOR_A, P_MAX / (MASS * max(v, 1.0)))


def long_accel(v, throttle, brake):
    """Longitudinal acceleration a pedal command gives at speed v."""
    return throttle * motor(v) - min(BRAKE_A * brake, grip(v)) - coast(v)


def pedals(v, a):
    """Inverse of long_accel, returns throttle and brake for a wanted acceleration."""
    a += coast(v)
    if a >= 0:
        return min(1.0, a / motor(v)), 0.0
    return 0.0, min(1.0, -a / BRAKE_A)


def lat_accel(v, steer):
    """Lateral acceleration the steering asks for, positive to the left, bicycle model with understeer."""
    return v * v * math.tan(STEER_MAX * steer) / (WHEELBASE + K_US * v * v)


def steer_for(v, ay):
    v = max(v, 1.0)
    return math.atan(ay * (WHEELBASE + K_US * v * v) / (v * v)) / STEER_MAX


def corner_speed(kappa):
    """Steady state cornering speed with downforce for curvature kappa, as in track.speed_profile."""
    k = np.maximum(np.abs(kappa), 1e-6)
    aero = MU * 0.5 * RHO * CLA / MASS
    return np.where(k > aero, np.sqrt(MU * G / np.maximum(k - aero, 1e-9)), V_TOP)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def gap_ahead(track, s_from, s_to):
    """Arc length from s_from forward to s_to on the closed track, in [-L/2, L/2)."""
    return (s_to - s_from + 0.5 * track.length) % track.length - 0.5 * track.length


class Pilot:
    """Pure pursuit plus speed profile tracker. act(state, opponents) returns (steer, throttle, brake)."""

    def __init__(self, track, pace=1.0, aggression=1.0, dive=False, kp=2.0, ki=0.6):
        self.t = track
        self.pace, self.aggression, self.dive = pace, aggression, dive
        self.kp, self.ki = kp, ki
        self.goal = np.minimum(V_TOP, pace * aggression * track.v)
        self.a_brake = BRAKE_FRAC * (pace * aggression) ** 2   # fraction of grip the driver uses when braking
        self.offset = 0.0                                # lateral shift from the racing line, metres
        self.integral = 0.0
        self.mode, self.side, self.target, self.lat_abs = "line", 0.0, None, None

    def reset(self):
        self.offset, self.integral, self.mode, self.side, self.target, self.lat_abs = 0.0, 0.0, "line", 0.0, None, None

    # lateral plan

    def follow_speed(self, o, gap, keep=12.0):
        """Fastest speed from which the driver can still brake down to the car ahead before the gap shrinks to keep."""
        a = 0.4 * grip(o["speed"])
        return math.sqrt(max(o["speed"] ** 2 + 2 * a * (gap - keep), 0.0))

    def plan_offset(self, st, opponents, j, dt):
        """Lateral plan against the closest car ahead. Picks a side once per overtake and keeps it.
        Targets are absolute lateral positions, kept as an offset from the line at the pursuit point j.
        Returns a speed cap while the driver is still behind and not yet clear on its side."""
        t, i = self.t, st["i"]
        line_j = t.offset[j]
        room = HALF - 2.0
        want, cap = None, None
        ahead = [(gap_ahead(t, st["s"], o["s"]), k, o) for k, o in enumerate(opponents)]
        ahead = [a for a in ahead if -6 < a[0] < 70]
        if not ahead:
            self.mode, self.side, self.target = "line", 0.0, None
        else:
            gap, k, o = min(ahead, key=lambda a: a[0])
            if self.target != k:
                self.side, self.target = 0.0, k
            hairpin = np.max(np.abs(t.kappa[t.ahead(i, np.arange(0, 60, 4))])) > 0.04
            lunge = self.dive and self.aggression > 1.05      # only an aggressive driver dives into a hairpin
            if not self.side and gap > 0 and (st["speed"] > o["speed"] - 0.5 or gap < 20) and (lunge or not hairpin):
                if lunge:
                    first = 1.0 if np.sum(t.kappa[t.ahead(i, np.arange(0, 80, 4))]) > 0 else -1.0
                else:
                    first = -1.0 if o["lat"] > 0 else 1.0
                for side in (first, -first):
                    if room - side * o["lat"] >= PASS_GAP - 0.4:
                        self.side = side
                        break
            if self.side:
                want = max(-room, min(room, o["lat"] + self.side * PASS_GAP))
                self.mode = "pass"
                if gap > 0 and self.side * (st["lat"] - o["lat"]) < PASS_GAP - 0.6:
                    cap = self.follow_speed(o, gap)   # not clear on our side yet, do not run into its gearbox
                    if self.side * (want - o["lat"]) < PASS_GAP - 0.4:
                        self.mode = "follow"          # squeezed against the edge, wait behind
            elif gap > 0:
                self.mode = "follow"
                cap = self.follow_speed(o, gap)
        # leave a car width to anyone alongside, whoever is ahead, whatever the plan
        for o in opponents:
            gap = gap_ahead(t, st["s"], o["s"])
            dlat = st["lat"] - o["lat"]
            if -8 < gap < CAR_LENGTH + 2 and abs(dlat) < PASS_GAP:
                side = math.copysign(1.0, dlat)
                bound = max(-(HALF - 2.0), min(HALF - 2.0, o["lat"] + side * PASS_GAP))
                base = line_j if want is None else want
                want = max(base, bound) if side > 0 else min(base, bound)
        # the lateral target moves at most 2.5 m/s, back to the racing line when there is nothing to do
        step = 2.5 * dt
        if want is None:
            self.offset += max(-step, min(step, -self.offset))
        else:
            now = self.lat_abs if self.lat_abs is not None else line_j + self.offset
            self.offset = now + max(-step, min(step, want - now)) - line_j
        self.lat_abs = line_j + self.offset
        return cap

    # main entry

    def act(self, st, opponents=(), dt=0.008):
        t = self.t
        v, i = st["speed"], st["i"]
        # pure pursuit from the rear axle on the shifted racing line
        ld = max(6.0, 4.0 + 0.25 * v)
        j = t.ahead(i, ld)
        cap = self.plan_offset(st, opponents, j, dt)
        lat_j = max(-HALF + 1.6, min(HALF - 1.6, t.offset[j] + self.offset))
        tx, ty = t.center[j] + t.nrm[j] * lat_j
        dx, dy = tx - st["x"], ty - st["y"]
        alpha = wrap(math.atan2(dy, dx) - st["yaw"])
        dist = max(math.hypot(dx, dy), 1.0)
        steer = math.atan(2 * WHEELBASE * math.sin(alpha) / dist) / STEER_MAX
        # catch a sliding rear like a driver would, counter steer by most of the slip beyond normal cornering
        beta = math.atan2(st["vy"], max(st["vx"], 1.0))
        if v > 5 and abs(beta) > SLIP_FREE:
            steer += COUNTER_STEER * (beta - math.copysign(SLIP_FREE, beta)) / STEER_MAX

        # target speed, the slowest point ahead still reachable at the braking level this driver uses
        dist_ahead = np.arange(0.0, 200.0, 4.0)
        ahead = t.ahead(i, dist_ahead)
        vc = self.goal[ahead]
        if abs(self.offset) > 0.3:
            k = t.kappa[ahead] / np.maximum(1 - t.kappa[ahead] * self.offset, 0.2)
            vc = np.minimum(vc, self.pace * self.aggression * corner_speed(k))
        a_b = self.a_brake * grip(vc)
        reach = np.sqrt(vc ** 2 + 2 * a_b * dist_ahead)
        k = int(np.argmin(reach))
        goal = float(reach[k])
        a_ff = -float(a_b[k]) if k > 0 and v > goal - 2.0 else 0.0   # on a braking curve, brake at its rate
        if cap is not None and cap < goal:
            goal, a_ff = max(cap, 3.0), 0.0

        err = goal - v
        self.integral = max(-3.0, min(3.0, self.integral + self.ki * err * dt))
        a = a_ff + self.kp * err + self.integral
        if err < -0.5:
            self.integral = min(self.integral, 0.0)
        # traction control and brake modulation inside the friction circle the driver believes in,
        # the rear axle carries about half the load and also has to corner
        steer = max(-1.0, min(1.0, steer))
        g = grip(v)
        ay = min(v * v * abs(t.kappa[i]), g)
        room = math.sqrt(g * g - ay * ay)
        a = max(-max(max(0.5, min(1.0, 1.4 * self.a_brake)) * room, MIN_BRAKE * g), min(a, TRACTION * room))
        throttle, brake = pedals(v, a)
        return steer, throttle, brake


def node_state(track, node, key):
    """State dict of any car from supervisor ground truth, same keys as the ego state."""
    x, y, _ = node.getPosition()
    R = node.getOrientation()
    vel = node.getVelocity()
    i, s, lat = track.project(x, y, key)
    return {"x": x, "y": y, "yaw": math.atan2(R[3], R[0]),
            "vx": vel[0] * R[0] + vel[1] * R[3], "vy": vel[0] * R[1] + vel[1] * R[4],
            "speed": math.hypot(vel[0], vel[1]), "i": i, "s": s, "lat": lat}
