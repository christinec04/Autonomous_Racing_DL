"""Single track model with saturating Pacejka tyres and a friction circle per axle, as a gym plug in.

The released f1tenth_gym ST model has linear tyres, lateral force grows with slip angle without
bound and the acceleration command is applied whatever the car is doing, so it has no friction circle.
The dev-dynamics MB model has PAC2002 combined slip but runs away at race grip (see calib.py notes).
This is the ForzaETH style STP model Gym-Khana describes, written against the gym's dynamics interface
f(x, u, params) with the same 7 element ST state, so the gym's map, LiDAR, collisions and multi agent
stepping are unchanged.

  state  x y delta V yaw yaw_rate beta, position at the centre of mass
  input  steering rate, longitudinal acceleration command (the gym's accl action)
Each axle gets its share of the commanded longitudinal force (drive split T_se, brake split T_sb as the
gym's MB model uses them), capped at mu Fz. Lateral force is Pacejka on what the circle leaves,
Fy = sqrt((mu Fz)^2 - Fx^2) sin(C atan(B alpha)), so a locked or spinning axle cannot corner.
"""
import math

import numpy as np

from f1tenth_gym.envs.dynamic_models.utils import accl_constraints, steering_constraint

B_TYRE, C_TYRE = 10.0, 1.4      # B C mu = 22 per rad of slip per unit load, the gym's full scale C_S times mu
G = 9.81
V_KIN = 3.0


def vehicle_dynamics_stp(x, u_init, p):
    delta, V, yaw, r, beta = x[2], x[3], x[4], x[5], x[6]
    sv = steering_constraint(delta, u_init[0], p["s_min"], p["s_max"], p["sv_min"], p["sv_max"])
    acc = accl_constraints(V, u_init[1], p["v_switch"], p["a_max"], p["v_min"], p["v_max"])
    lf, lr, h, m, mu = p["lf"], p["lr"], p["h"], p["m"], p["mu"]
    L = lf + lr
    f = np.zeros(7)
    f[2] = sv
    if V < V_KIN:
        # kinematic at walking pace, the slip angles are ill conditioned there
        bh = math.atan(math.tan(delta) * lr / L)
        f[0] = V * math.cos(yaw + bh)
        f[1] = V * math.sin(yaw + bh)
        f[3] = acc
        f[4] = V * math.cos(bh) * math.tan(delta) / L
        # relax yaw rate and slip onto the kinematic values so the switch to dynamics is smooth
        f[5] = (f[4] - r) / 0.05
        f[6] = (bh - beta) / 0.05
        return f
    vx, vy = V * math.cos(beta), V * math.sin(beta)
    fx = m * acc
    if fx >= 0:
        dem_f, dem_r = p["T_se"] * fx, (1 - p["T_se"]) * fx
    else:
        dem_f, dem_r = p["T_sb"] * fx, (1 - p["T_sb"]) * fx
    # load transfer follows the acceleration the tyres actually deliver, two fixed point passes
    a_eff = max(-mu * G, min(mu * G, acc))
    for _ in range(2):
        fz_f = m * (G * lr - a_eff * h) / L
        fz_r = m * (G * lf + a_eff * h) / L
        cap_f, cap_r = mu * max(fz_f, 0.0), mu * max(fz_r, 0.0)
        fx_f = max(-cap_f, min(cap_f, dem_f))
        fx_r = max(-cap_r, min(cap_r, dem_r))
        a_eff = (fx_f + fx_r) / m
    af = delta - math.atan2(vy + lf * r, vx)
    ar = -math.atan2(vy - lr * r, vx)
    room_f = math.sqrt(max(cap_f * cap_f - fx_f * fx_f, (0.02 * cap_f) ** 2))
    room_r = math.sqrt(max(cap_r * cap_r - fx_r * fx_r, (0.02 * cap_r) ** 2))
    fy_f = room_f * math.sin(C_TYRE * math.atan(B_TYRE * af))
    fy_r = room_r * math.sin(C_TYRE * math.atan(B_TYRE * ar))
    cd, sd = math.cos(delta), math.sin(delta)
    dvx = (fx_r + fx_f * cd - fy_f * sd) / m + vy * r
    dvy = (fy_r + fy_f * cd + fx_f * sd) / m - vx * r
    f[0] = V * math.cos(yaw + beta)
    f[1] = V * math.sin(yaw + beta)
    f[3] = (vx * dvx + vy * dvy) / V
    f[4] = r
    f[5] = (lf * (fy_f * cd + fx_f * sd) - lr * fy_r) / p["I"]
    f[6] = (vx * dvy - vy * dvx) / (V * V)
    return f


class STPModel:
    """Stands in for DynamicModel.ST on a gym RaceCar, only the dynamics function differs."""

    def __init__(self, base):
        self.base = base

    def get_initial_state(self, pose=None, params=None):
        return self.base.get_initial_state(pose=pose, params=params)

    @property
    def f_dynamics(self):
        return vehicle_dynamics_stp

    def get_standardized_state_fn(self):
        return self.base.get_standardized_state_fn()
