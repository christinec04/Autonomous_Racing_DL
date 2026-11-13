"""Friction-limited tyres and traction control for F1TENTH Gym.

The stock F1TENTH single-track model has linear tyres, so the lateral force grows without limit with the
slip angle and a car can corner at more than 2 g. Evans et al. (2023) found that agents exploit this by sliding.

Our model is the same single-track model with each axle's lateral force capped by a friction circle,
|Fy| <= sqrt((mu Fz)^2 - Fx^2) with Fx = Fz * a / g. Below the limit it matches the stock model exactly.
"""
from __future__ import annotations

import numpy as np
from numba import njit

from f1tenth_gym.envs import action as _act
from f1tenth_gym.envs import dynamic_models as _dm


@njit(cache=True)
def _st_friction_circle(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I, s_min, s_max,
                        sv_min, sv_max, v_switch, a_max, v_min, v_max, fix_spin):
    """Single-track dynamics with friction-circle tyres.

    With fix_spin, the slip angle is wrapped to [-pi, pi] and relaxes to its kinematic value at low speed.
    Without it, a car that has spun keeps a slip angle such as -262 deg and moves sideways when it restarts.
    """
    DELTA = x[2]
    V = x[3]
    PSI = x[4]
    PSI_DOT = x[5]
    BETA = np.arctan2(np.sin(x[6]), np.cos(x[6])) if fix_spin else x[6]
    g = 9.81
    STEER_VEL = _dm.steering_constraint(DELTA, u_init[0], s_min, s_max, sv_min, sv_max)
    ACCL = _dm.accl_constraints(V, u_init[1], v_switch, a_max, v_min, v_max)
    lwb = lf + lr
    if V < 0.5:
        # kinematic model at low speed, as in the stock model
        BETA_HAT = np.arctan(np.tan(DELTA) * lr / lwb)
        BETA_DOT = (1 / (1 + (np.tan(DELTA) * (lr / lwb)) ** 2)) * (lr / (lwb * np.cos(DELTA) ** 2)) * STEER_VEL
        if fix_spin:
            err = BETA_HAT - BETA
            err = np.arctan2(np.sin(err), np.cos(err))
            BETA_DOT = BETA_DOT + 20.0 * err
        return np.array([
            V * np.cos(PSI + BETA_HAT), V * np.sin(PSI + BETA_HAT), STEER_VEL, ACCL,
            V * np.cos(BETA_HAT) * np.tan(DELTA) / lwb,
            (1 / lwb) * (ACCL * np.cos(BETA) * np.tan(DELTA) - V * np.sin(BETA) * np.tan(DELTA) * BETA_DOT
                         + ((V * np.cos(BETA) * STEER_VEL) / (np.cos(DELTA) ** 2))),
            BETA_DOT])
    Fzf = m * (g * lr - ACCL * h) / lwb
    Fzr = m * (g * lf + ACCL * h) / lwb
    alpha_f = DELTA - BETA - lf * PSI_DOT / V
    alpha_r = -BETA + lr * PSI_DOT / V
    Fyf = mu * C_Sf * Fzf * alpha_f
    Fyr = mu * C_Sr * Fzr * alpha_r
    ax = ACCL / g
    capf = np.sqrt(max((mu * Fzf) ** 2 - (Fzf * ax) ** 2, 0.0))
    capr = np.sqrt(max((mu * Fzr) ** 2 - (Fzr * ax) ** 2, 0.0))
    Fyf = min(max(Fyf, -capf), capf)
    Fyr = min(max(Fyr, -capr), capr)
    return np.array([
        V * np.cos(PSI + BETA), V * np.sin(PSI + BETA), STEER_VEL, ACCL, PSI_DOT,
        (lf * Fyf - lr * Fyr) / I,
        (Fyf + Fyr) / (m * V) - PSI_DOT])


@njit(cache=True)
def vehicle_dynamics_st_sat(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I, s_min, s_max,
                            sv_min, sv_max, v_switch, a_max, v_min, v_max):
    """Tyre model "saturated"."""
    return _st_friction_circle(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I, s_min, s_max,
                               sv_min, sv_max, v_switch, a_max, v_min, v_max, False)


@njit(cache=True)
def vehicle_dynamics_st_sat2(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I, s_min, s_max,
                             sv_min, sv_max, v_switch, a_max, v_min, v_max):
    """Tyre model "saturated_v2", the same with the fixes after a spin."""
    return _st_friction_circle(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I, s_min, s_max,
                               sv_min, sv_max, v_switch, a_max, v_min, v_max, True)


_STOCK = _dm.vehicle_dynamics_st
TIRE_MODELS = {"saturated": vehicle_dynamics_st_sat, "saturated_v2": vehicle_dynamics_st_sat2, "linear": _STOCK}


def set_tire_model(kind: str = "saturated"):
    """Sets the tyre model F1TENTH Gym uses in this process."""
    _dm.vehicle_dynamics_st = TIRE_MODELS[kind]


# Traction control for every car. F1TENTH's speed loop brakes and accelerates at up to 9.51 m/s^2, about 92%
# of mu*g, so any steering on top of that spins a car with friction-limited tyres. Like a real car's traction
# control, we limit the acceleration to the grip left after the current lateral acceleration.
_STOCK_SPEED_ACT = _act.SpeedAction.act
TCS_MARGIN = 0.95  # use at most 95% of the friction circle
SLIDE_BETA = 0.26  # about 15 deg of body slip, the car is sliding


def _speed_act_tcs(self, action, state, params):
    a = _act.pid_accl(action, state[3], params["a_max"], params["v_max"], params["v_min"])
    if len(state) >= 7 and abs(state[6]) > SLIDE_BETA:
        return a  # already sliding, so full braking is allowed
    if len(state) >= 6:
        mg = TCS_MARGIN * params["mu"] * 9.81
        a_lat = state[3] * state[5]
        a_avail = max(np.sqrt(max(mg * mg - a_lat * a_lat, 0.0)), 0.5)  # always allow a little
        a = min(max(a, -a_avail), a_avail)
    return a


def set_traction_control(on: bool = True):
    _act.SpeedAction.act = _speed_act_tcs if on else _STOCK_SPEED_ACT
