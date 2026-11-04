"""APF safety shield.

Variants (addressing the proposal feedback):

  mode="additive"      Proposal Eq. 2/3: a = clip(a_rl + w(d) * a_apf), with w(d) from
                       obstacle distance and speed only. Cannot guarantee safety; the
                       weight never looks at the agent's action.
  mode="conditioned"   Action-conditioned trigger: roll out the policy's action, then a
                       braking backup manoeuvre. Intervene only if that rollout is
                       predicted to hit something. Then blend towards the APF-corrected
                       action with the smallest weight lambda that is predicted safe.
  mode="conditioned_fallback"
                       As above, but if no blend is predicted safe, *replace* the action
                       with the safest of a small set of braking manoeuvres.

  reach="fixed"        Influence distance uses a fixed assumed braking deceleration.
  reach="grip"         Uses the deceleration left inside the friction circle after
                       cornering: a_brake = sqrt((mu g)^2 - (v * yaw_rate)^2).

All actions here are physical: (steering angle [rad], target speed [m/s]).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .sim import DEFAULT_PARAMS as P, G

WB = P["lf"] + P["lr"]
L, W = P["length"], P["width"]
S_MAX = P["s_max"]
SV_MAX = P["sv_max"]
N_BEAMS, FOV = 1080, 4.7
BEAM_ANG = np.linspace(-FOV / 2, FOV / 2, N_BEAMS)
D_THETA = FOV / (N_BEAMS - 1)
COS_B, SIN_B = np.cos(BEAM_ANG), np.sin(BEAM_ANG)
# distance from car centre to the body edge along each beam
BODY = np.minimum((L / 2) / np.maximum(np.abs(COS_B), 1e-6), (W / 2) / np.maximum(np.abs(SIN_B), 1e-6))
CIRC_OFF = np.array([-L / 3, 0.0, L / 3])  # 3 circles cover the body
CIRC_R = float(np.hypot(W / 2, L / 6))


@dataclass
class ShieldConfig:
    mode: str = "off"  # off | additive | conditioned | conditioned_fallback
    reach: str = "grip"  # fixed | grip
    a_brake_fixed: float = 6.0  # assumed deceleration for reach="fixed" (proposal Sec. III-C)
    mu: float = P["mu"]
    a_max: float = P["a_max"]
    d_min: float = 0.30  # clearance [m] at which the field starts, at zero closing speed
    d_crit: float = 0.05  # clearance [m] at which the correction fully dominates
    k_steer: float = 2.0  # steering correction per unit lateral force [rad]
    k_speed: float = 2.0  # fraction of speed removed per unit longitudinal force
    opp_a: float = 0.6  # opponent ellipse extra length along its heading [m]
    opp_b: float = 0.15  # opponent ellipse extra width [m]
    smooth: float = 0.5  # EMA on the additive correction (anti-oscillation)
    c_safe: float = 0.03  # predicted clearance below this counts as a collision
    pred_dt: float = 0.05
    commit_time: float = 0.08  # how long the policy action is held before the backup starts
    max_pred_time: float = 3.0
    blend_levels: tuple = (0.25, 0.5, 0.75, 1.0)
    beam_stride: int = 3


def available_decel(cfg: ShieldConfig, v: float, yaw_rate: float) -> float:
    if cfg.reach == "fixed":
        return cfg.a_brake_fixed
    mg = cfg.mu * G
    a_lat = abs(v * yaw_rate)
    return float(np.clip(np.sqrt(max(mg * mg - a_lat * a_lat, 0.0)), 1.0, cfg.a_max))


class APFShield:
    def __init__(self, cfg: ShieldConfig, control_dt: float):
        self.cfg = cfg
        self.dt = control_dt
        self.reset()

    def reset(self):
        self.corr = np.zeros(2)
        self.last = {}

    # ------------------------------------------------------------------ APF field
    def field(self, scan, v, yaw_rate, opps):
        """Repulsive force (ego frame, normalised) and risk rho in [0,1].

        opps: list of dicts with ego-frame 'pos', 'vel' (relative), 'yaw' (relative heading).
        """
        cfg = self.cfg
        ab = available_decel(cfg, v, yaw_rate)
        c = scan - BODY
        v_close = np.maximum(v * COS_B, 0.0)
        d0 = cfg.d_min + v_close ** 2 / (2 * ab)
        rho_i = np.clip((d0 - c) / (d0 - cfg.d_crit), 0.0, 1.0)
        m = rho_i ** 2 * D_THETA
        F = -np.array([np.dot(m, COS_B), np.dot(m, SIN_B)])
        rho = float(rho_i.max())
        for o in opps:
            px, py = o["pos"]
            cy, sy = np.cos(o["yaw"]), np.sin(o["yaw"])
            # ego centre relative to opponent, in opponent frame
            ex = -(px * cy + py * sy)
            ey = -(-px * sy + py * cy)
            A, B = L + cfg.opp_a, W + cfg.opp_b
            e = np.hypot(ex / A, ey / B)
            c_o = (e - 1.0) * B
            dist = np.hypot(px, py) + 1e-6
            v_cl = max(-(px * o["vel"][0] + py * o["vel"][1]) / dist, 0.0)
            d0o = cfg.d_min + v_cl ** 2 / (2 * ab)
            r = float(np.clip((d0o - c_o) / (d0o - cfg.d_crit), 0.0, 1.0))
            if r > 0:
                gx, gy = ex / A ** 2, ey / B ** 2  # gradient of e, opponent frame (points away)
                gw = np.array([gx * cy - gy * sy, gx * sy + gy * cy])
                gw /= np.linalg.norm(gw) + 1e-9
                F += r ** 2 * 0.5 * gw
            rho = max(rho, r)
        return F, rho, ab

    def apf_correction(self, F, v):
        cfg = self.cfg
        d_steer = float(np.clip(cfg.k_steer * F[1], -2 * S_MAX, 2 * S_MAX))
        d_speed = -v * float(np.clip(cfg.k_speed * max(-F[0], 0.0), 0.0, 1.0))
        return np.array([d_steer, d_speed])

    @staticmethod
    def clip_action(a, v_lo=0.0, v_hi=20.0):
        return np.array([np.clip(a[0], -S_MAX, S_MAX), np.clip(a[1], v_lo, v_hi)])

    # ------------------------------------------------------------- prediction
    def predict_clearance(self, cands, state, scan, opps_world, ab_fn):
        """Min predicted clearance for each candidate (K,2) action.

        Candidate action is held for commit_time, then a braking backup takes over:
        brake at the available deceleration while keeping the APF-style steering
        away from the nearest points.
        """
        cfg = self.cfg
        x0, y0, yaw0, v0, d0_ = state
        K = len(cands)
        # static points (world frame) from the current scan
        idx = slice(None, None, cfg.beam_stride)
        r = scan[idx]
        keep = r < 25.0
        ang = BEAM_ANG[idx][keep] + yaw0
        pts = np.stack([x0 + r[keep] * np.cos(ang), y0 + r[keep] * np.sin(ang)], 1)
        reach = v0 * cfg.max_pred_time + 2.0
        pts = pts[np.hypot(pts[:, 0] - x0, pts[:, 1] - y0) < reach]

        x = np.full(K, x0); y = np.full(K, y0); yaw = np.full(K, yaw0)
        v = np.full(K, v0); dl = np.full(K, d0_)
        clear = np.full(K, np.inf)
        T = int(cfg.max_pred_time / cfg.pred_dt)
        n_commit = max(1, int(round(cfg.commit_time / cfg.pred_dt)))
        dt = cfg.pred_dt
        for t in range(T):
            if t < n_commit:
                steer_cmd, v_cmd = cands[:, 0], cands[:, 1]
                acc = np.clip(10 * cfg.a_max / 20 * (v_cmd - v), -cfg.a_max, cfg.a_max)
                acc = np.where(v_cmd < v, np.clip(19.0 * (v_cmd - v), -cfg.a_max, 0), acc)
            else:
                steer_cmd = dl  # hold steering during the backup
                ab = np.array([ab_fn(vi, vi * np.tan(di) / WB) for vi, di in zip(v, dl)])
                acc = -ab
            dl = dl + np.clip(steer_cmd - dl, -SV_MAX * dt, SV_MAX * dt)
            v = np.maximum(v + acc * dt, 0.0)
            yaw = yaw + v / WB * np.tan(dl) * dt
            x = x + v * np.cos(yaw) * dt
            y = y + v * np.sin(yaw) * dt
            cx = x[:, None] + CIRC_OFF[None] * np.cos(yaw)[:, None]  # (K,3)
            cy = y[:, None] + CIRC_OFF[None] * np.sin(yaw)[:, None]
            if len(pts):
                d = np.hypot(cx[..., None] - pts[:, 0], cy[..., None] - pts[:, 1])  # (K,3,P)
                clear = np.minimum(clear, d.min(axis=(1, 2)) - CIRC_R)
            tt = (t + 1) * dt
            for o in opps_world:
                ox, oy, oyaw, ov, ow = o
                if abs(ow) > 1e-3:
                    oyaw_t = oyaw + ow * tt
                    ox_t = ox + ov / ow * (np.sin(oyaw_t) - np.sin(oyaw))
                    oy_t = oy - ov / ow * (np.cos(oyaw_t) - np.cos(oyaw))
                else:
                    oyaw_t = oyaw
                    ox_t, oy_t = ox + ov * np.cos(oyaw) * tt, oy + ov * np.sin(oyaw) * tt
                ocx = ox_t + CIRC_OFF * np.cos(oyaw_t)
                ocy = oy_t + CIRC_OFF * np.sin(oyaw_t)
                d = np.hypot(cx[..., None] - ocx, cy[..., None] - ocy)  # (K,3,3)
                clear = np.minimum(clear, d.min(axis=(1, 2)) - 2 * CIRC_R)
            if np.all(v < 0.05):
                break
        return clear

    # ------------------------------------------------------------------- main
    def __call__(self, a_rl, state, scan, opps_ego, opps_world):
        """state = (x, y, yaw, v, steer, yaw_rate). Returns (a_final, lambda, info)."""
        cfg = self.cfg
        x, y, yaw, v, steer, yaw_rate = state
        a_rl = self.clip_action(np.asarray(a_rl, float))
        if cfg.mode == "off":
            return a_rl, 0.0, {"rho": 0.0, "fallback": False}

        F, rho, ab = self.field(scan, v, yaw_rate, opps_ego)
        a_apf = self.apf_correction(F, v)

        if cfg.mode == "additive":
            w = rho  # Eq. 3 (per-beam speed-dependent d0)
            self.corr = cfg.smooth * self.corr + (1 - cfg.smooth) * w * a_apf
            a = self.clip_action(a_rl + self.corr)
            lam = float(np.clip(w, 0, 1))
            return a, lam, {"rho": rho, "fallback": False}

        ab_fn = lambda vi, yr: available_decel(cfg, vi, yr)
        st = (x, y, yaw, v, steer)
        c_rl = self.predict_clearance(a_rl[None], st, scan, opps_world, ab_fn)[0]
        if c_rl >= cfg.c_safe:
            return a_rl, 0.0, {"rho": rho, "fallback": False, "c_pred": float(c_rl)}

        # corrective direction: APF steering + strong braking
        a_corr = self.clip_action(np.array([
            a_rl[0] + (a_apf[0] if abs(a_apf[0]) > 1e-3 else 0.0),
            min(a_rl[1] + a_apf[1], v - ab * self.dt * 2),
        ]))
        lams = np.array(cfg.blend_levels)
        cands = (1 - lams)[:, None] * a_rl[None] + lams[:, None] * a_corr[None]
        cl = self.predict_clearance(cands, st, scan, opps_world, ab_fn)
        ok = np.nonzero(cl >= cfg.c_safe)[0]
        if len(ok):
            i = ok[0]
            return cands[i], float(lams[i]), {"rho": rho, "fallback": False, "c_pred": float(cl[i])}
        if cfg.mode == "conditioned":
            return a_corr, 1.0, {"rho": rho, "fallback": False, "c_pred": float(cl[-1])}

        # fallback: replace with the safest braking manoeuvre
        steers = np.clip(np.array([a_corr[0], -S_MAX, -S_MAX / 2, 0.0, S_MAX / 2, S_MAX, steer]), -S_MAX, S_MAX)
        fb = np.stack([steers, np.zeros_like(steers)], 1)
        fb_cl = self.predict_clearance(fb, st, scan, opps_world, ab_fn)
        j = int(np.argmax(fb_cl))
        return fb[j], 1.0, {"rho": rho, "fallback": True, "c_pred": float(fb_cl[j])}
