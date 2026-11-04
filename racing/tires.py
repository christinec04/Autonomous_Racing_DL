"""Friction-limited single-track dynamics for F1TENTH Gym.

Stock F1TENTH 'st' uses linear tyres: lateral force grows without bound with slip
angle, so a car can corner at > 2 g (we measured ~24 m/s^2 at 8 m/s against
mu*g = 10.3). Evans et al. (2023) showed agents exploit this by sliding.

This is the same CommonRoad single-track model rewritten in slip-angle form,
with each axle's lateral force capped by a friction circle:
    |Fy_axle| <= sqrt((mu Fz_axle)^2 - Fx_axle^2),   Fx_axle = Fz_axle * a / g.
Below the limit it is algebraically identical to the stock model.
"""
from __future__ import annotations

import numpy as np
from numba import njit

from f1tenth_gym.envs import dynamic_models as _dm


@njit(cache=True)
def vehicle_dynamics_st_sat(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I, s_min, s_max,
                            sv_min, sv_max, v_switch, a_max, v_min, v_max):
    DELTA = x[2]; V = x[3]; PSI = x[4]; PSI_DOT = x[5]; BETA = x[6]
    g = 9.81
    STEER_VEL = _dm.steering_constraint(DELTA, u_init[0], s_min, s_max, sv_min, sv_max)
    ACCL = _dm.accl_constraints(V, u_init[1], v_switch, a_max, v_min, v_max)
    lwb = lf + lr
    if V < 0.5:
        BETA_HAT = np.arctan(np.tan(DELTA) * lr / lwb)
        BETA_DOT = (1 / (1 + (np.tan(DELTA) * (lr / lwb)) ** 2)) * (lr / (lwb * np.cos(DELTA) ** 2)) * STEER_VEL
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


_STOCK = _dm.vehicle_dynamics_st


def set_tire_model(kind: str = "saturated"):
    """Swap the ST dynamics used by F1TENTH Gym in this process."""
    if kind == "saturated":
        _dm.vehicle_dynamics_st = vehicle_dynamics_st_sat
    elif kind == "linear":
        _dm.vehicle_dynamics_st = _STOCK
    else:
        raise ValueError(kind)


# ---------------------------------------------------------------------------
# Traction control (TCS/ABS) for every car.
# F1TENTH's speed loop accelerates/brakes at up to a_max = 9.51 m/s^2, i.e. ~92%
# of mu*g. With friction-limited tyres any steering on top of that spins the car.
# We clamp the longitudinal command to the friction circle left after the
# current lateral acceleration (v * yaw_rate), like a real car's TCS/ABS.
# ---------------------------------------------------------------------------
from f1tenth_gym.envs import action as _act  # noqa: E402

_STOCK_SPEED_ACT = _act.SpeedAction.act
TCS_MARGIN = 0.95  # use at most 95% of the friction circle
SLIDE_BETA = 0.26  # ~15 deg body slip: car is sliding, v*yaw_rate no longer measures lateral load


def _speed_act_tcs(self, action, state, params):
    a = _act.pid_accl(action, state[3], params["a_max"], params["v_max"], params["v_min"])
    if len(state) >= 7 and abs(state[6]) > SLIDE_BETA:
        return a  # already sliding: wheels may lock, full braking allowed (ABS off)
    if len(state) >= 6:
        mg = TCS_MARGIN * params["mu"] * 9.81
        a_lat = state[3] * state[5]
        a_avail = np.sqrt(max(mg * mg - a_lat * a_lat, 0.0))
        a_avail = max(a_avail, 0.5)  # always allow some braking/throttle
        a = min(max(a, -a_avail), a_avail)
    return a


def set_traction_control(on: bool = True):
    _act.SpeedAction.act = _speed_act_tcs if on else _STOCK_SPEED_ACT
