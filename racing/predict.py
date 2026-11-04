"""Exact-model rollouts for the action-conditioned shield (numba).

Uses the same vehicle model as the simulator: single-track ODE (stock linear or
friction-circle tyres), RK4 at the physics step, F1TENTH's bang-bang steering
servo with its 2-step delay, the speed P-loop and traction control. The only
remaining model error is the opponents' future motion (assumed: constant
curvature while braking at opp_brake) and lidar points we cannot see.

Rollout for each candidate action:
  1. hold the candidate (steer, speed) for `commit_steps` physics steps,
  2. then a backup: brake to a stop (speed command 0, so traction control/ABS
     sets the deceleration, or a fixed assumed deceleration) while tracking the
     current lane with pure pursuit.
Returns the minimum clearance to walls/lidar points and opponents.
"""
from __future__ import annotations

import numpy as np
from numba import njit

from f1tenth_gym.envs.dynamic_models import vehicle_dynamics_st as _st_linear

from .tires import vehicle_dynamics_st_sat as _st_sat, vehicle_dynamics_st_sat2 as _st_sat2

G = 9.81


@njit(cache=True)
def _f(x, u, sat, p):
    if sat == 2:
        return _st_sat2(x, u, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], p[13], p[14], p[15])
    if sat == 1:
        return _st_sat(x, u, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], p[13], p[14], p[15])
    return _st_linear(x, u, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], p[13], p[14], p[15])


@njit(cache=True)
def _accel(v_cmd, x, p, tcs, tcs_margin, fixed_decel):
    # F1TENTH speed P-loop (pid_accl), forward driving
    a_max, v_max, v_min = p[13], p[15], p[14]
    dv = v_cmd - x[3]
    if x[3] > 0.0:
        if dv > 0:
            a = 10.0 * a_max / v_max * dv
        else:
            a = 10.0 * a_max / (-v_min) * dv
    else:
        a = 2.0 * a_max / v_max * dv if dv > 0 else 10.0 * a_max / v_max * dv
    if tcs and abs(x[6]) <= 0.26:
        mg = tcs_margin * p[0] * G
        alat = x[3] * x[5]
        av = np.sqrt(max(mg * mg - alat * alat, 0.0))
        av = max(av, 0.5)
        a = min(max(a, -av), av)
    if fixed_decel > 0.0 and a < -fixed_decel:
        a = -fixed_decel
    return a


@njit(cache=True)
def backup_steer(x, lane_xy, lookahead_pts, wb):
    best = 1e18; li = 0
    for j in range(0, lane_xy.shape[0] - lookahead_pts - 1):
        d = (lane_xy[j, 0] - x[0]) ** 2 + (lane_xy[j, 1] - x[1]) ** 2
        if d < best:
            best = d; li = j
    tx = lane_xy[li + lookahead_pts, 0]; ty = lane_xy[li + lookahead_pts, 1]
    hd = x[4] + x[6]
    dx = tx - x[0]; dy = ty - x[1]
    ly = -dx * np.sin(hd) + dy * np.cos(hd)
    return np.arctan(2 * wb * ly / max(dx * dx + dy * dy, 1e-6))


@njit(cache=True)
def rollout_clearance(cands, x0, steer_buf0, p, sat, tcs, tcs_margin, fixed_decel,
                      pts, lane_xy, lookahead_pts, opp0, opp_brake,
                      commit_steps, total_steps, dt, check_every, circ_off, circ_r, wb, beta_max):
    K = cands.shape[0]
    out = np.full(K, 1e9)
    n_opp = opp0.shape[0]
    W = lane_xy.shape[0]
    for k in range(K):
        x = x0.copy()
        buf0 = steer_buf0[0]; buf1 = steer_buf0[1]  # delay line (oldest = buf1)
        opp = opp0.copy()
        li = 0
        clear = 1e9
        for t in range(total_steps):
            if t < commit_steps and not np.isnan(cands[k, 0]):
                steer_cmd = cands[k, 0]; v_cmd = cands[k, 1]
            else:
                # backup: brake, pure pursuit on the lane
                best = 1e18
                j0 = li
                for j in range(max(0, j0 - 5), min(W - lookahead_pts - 1, j0 + 40)):
                    d = (lane_xy[j, 0] - x[0]) ** 2 + (lane_xy[j, 1] - x[1]) ** 2
                    if d < best:
                        best = d; li = j
                tx = lane_xy[li + lookahead_pts, 0]; ty = lane_xy[li + lookahead_pts, 1]
                hd = x[4] + x[6]
                dx = tx - x[0]; dy = ty - x[1]
                ly = -dx * np.sin(hd) + dy * np.cos(hd)
                L2 = max(dx * dx + dy * dy, 1e-6)
                steer_cmd = np.arctan(2 * wb * ly / L2)
                v_cmd = 0.0
            # steering delay buffer (2 steps), bang-bang steering servo
            delayed = buf1
            buf1 = buf0; buf0 = steer_cmd
            diff = delayed - x[2]
            sv = 0.0
            if abs(diff) > 1e-4:
                sv = p[11] if diff > 0 else -p[11]
            acc = _accel(v_cmd, x, p, tcs, tcs_margin, fixed_decel if t >= commit_steps else 0.0)
            u = np.array([sv, acc])
            k1 = _f(x, u, sat, p)
            k2 = _f(x + dt * k1 / 2, u, sat, p)
            k3 = _f(x + dt * k2 / 2, u, sat, p)
            k4 = _f(x + dt * k3, u, sat, p)
            x = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            if x[3] < 0.0:
                x[3] = 0.0
            # opponents: constant curvature, braking
            for o in range(n_opp):
                ov = max(opp[o, 3] - opp_brake * dt, 0.0)
                opp[o, 2] += ov * opp[o, 4] * dt
                opp[o, 0] += ov * np.cos(opp[o, 2]) * dt
                opp[o, 1] += ov * np.sin(opp[o, 2]) * dt
                opp[o, 3] = ov
            if abs(x[6]) > beta_max and x[3] > 1.0:  # loss of control counts as a violation (slip is meaningless when nearly stopped)
                clear = min(clear, -1.0)
                break
            if t % check_every == 0:
                c, s = np.cos(x[4]), np.sin(x[4])
                for ci in range(3):
                    cx = x[0] + circ_off[ci] * c
                    cy = x[1] + circ_off[ci] * s
                    for q in range(pts.shape[0]):
                        d = np.sqrt((cx - pts[q, 0]) ** 2 + (cy - pts[q, 1]) ** 2) - circ_r
                        if d < clear:
                            clear = d
                    for o in range(n_opp):
                        oc, os_ = np.cos(opp[o, 2]), np.sin(opp[o, 2])
                        for cj in range(3):
                            ox = opp[o, 0] + circ_off[cj] * oc
                            oy = opp[o, 1] + circ_off[cj] * os_
                            d = np.sqrt((cx - ox) ** 2 + (cy - oy) ** 2) - 2 * circ_r
                            if d < clear:
                                clear = d
            if t >= commit_steps and x[3] < 0.05:
                break
        out[k] = clear
    return out


@njit(cache=True)
def current_clearance(x0, pts, opp0, circ_off, circ_r):
    """Clearance right now (same geometry as rollout_clearance, no motion)."""
    clear = 1e9
    c, s = np.cos(x0[4]), np.sin(x0[4])
    for ci in range(3):
        cx = x0[0] + circ_off[ci] * c
        cy = x0[1] + circ_off[ci] * s
        for q in range(pts.shape[0]):
            d = np.sqrt((cx - pts[q, 0]) ** 2 + (cy - pts[q, 1]) ** 2) - circ_r
            if d < clear:
                clear = d
        for o in range(opp0.shape[0]):
            oc, os_ = np.cos(opp0[o, 2]), np.sin(opp0[o, 2])
            for cj in range(3):
                ox = opp0[o, 0] + circ_off[cj] * oc
                oy = opp0[o, 1] + circ_off[cj] * os_
                d = np.sqrt((cx - ox) ** 2 + (cy - oy) ** 2) - 2 * circ_r
                if d < clear:
                    clear = d
    return clear
