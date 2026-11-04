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

from .predict import rollout_clearance, backup_steer, current_clearance
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
    c_safe: float = 0.05  # predicted clearance below this counts as a collision (model-error margin)
    pred_dt: float = 0.05
    commit_time: float = 0.04  # one control step: how long the policy action is held before the backup starts
    max_pred_time: float = 3.0
    blend_levels: tuple = (0.25, 0.5, 0.75, 1.0)
    beam_stride: int = 3
    beta_max: float = 0.35  # predicted body slip above ~20 deg = loss of control
    use_map: bool = True  # add known track walls (lidar is occluded by opponents)
    backup_lookahead: float = 1.2
    escape: bool = False  # deadlock fix: near/inside the margin, accept actions predicted to stay out of contact
    escape_tol: float = 0.02  # how much predicted clearance may shrink [m] while escaping
    escape_v: float = 0.5  # escape only applies below this speed [m/s] (deadlock recovery, not normal driving)
    opp_brake: float = 6.0  # worst-case opponent deceleration assumed in prediction [m/s^2]


def available_decel(cfg: ShieldConfig, v: float, yaw_rate: float) -> float:
    if cfg.reach == "fixed":
        return cfg.a_brake_fixed
    mg = cfg.mu * G
    a_lat = abs(v * yaw_rate)
    return float(np.clip(np.sqrt(max(mg * mg - a_lat * a_lat, 0.0)), 1.0, cfg.a_max))


class APFShield:
    def __init__(self, cfg: ShieldConfig, control_dt: float, centerline=None, half_width: float = 1.4):
        self.cfg = cfg
        self.dt = control_dt
        self.cl = centerline
        self.p = np.array([P[k] for k in ("mu", "C_Sf", "C_Sr", "lf", "lr", "h", "m", "I", "s_min", "s_max",
                                          "sv_min", "sv_max", "v_switch", "a_max", "v_min", "v_max")], float)
        self.sat = True
        self.tcs = True
        if centerline is not None:
            n = np.stack([-np.sin(centerline.heading), np.cos(centerline.heading)], 1)
            self.walls = np.concatenate([centerline.xy + half_width * n, centerline.xy - half_width * n])
            self.half_width = half_width
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

    def brake_cmd(self, v, a):
        """Speed command that makes F1TENTH's speed P-loop (gain ~19/s) brake at ~a m/s^2."""
        return max(0.0, v - a / 19.0 - a * self.dt)

    @staticmethod
    def clip_action(a, v_lo=0.0, v_hi=20.0):
        return np.array([np.clip(a[0], -S_MAX, S_MAX), np.clip(a[1], v_lo, v_hi)])

    # ------------------------------------------------------------- prediction
    def predict_clearance(self, cands, x7, steer_buf, scan, opps_world):
        """Min predicted clearance for each candidate (K,2) action, exact vehicle model."""
        cfg = self.cfg
        x0, y0, yaw0, v0 = x7[0], x7[1], x7[4], x7[3]
        idx = slice(None, None, cfg.beam_stride)
        r = scan[idx]
        keep = r < 25.0
        ang = BEAM_ANG[idx][keep] + yaw0
        pts = np.stack([x0 + r[keep] * np.cos(ang), y0 + r[keep] * np.sin(ang)], 1)
        reach = v0 * 1.5 + 2.0
        pts = pts[np.hypot(pts[:, 0] - x0, pts[:, 1] - y0) < reach]
        for o in opps_world:  # lidar hits on opponents are handled as moving obstacles
            if len(pts):
                pts = pts[np.hypot(pts[:, 0] - o[0], pts[:, 1] - o[1]) > 0.5]
        lane_xy = np.zeros((60, 2)); la = 12
        if cfg.use_map and self.cl is not None:
            w = self.walls[np.hypot(self.walls[:, 0] - x0, self.walls[:, 1] - y0) < reach]
            pts = np.concatenate([pts, w]) if len(pts) else w
            ci, _, lat0, _ = self.cl.project(x0, y0)
            lane = float(np.clip(lat0, -self.half_width + 0.4, self.half_width - 0.4))
            win = (ci + np.arange(-10, int(reach / 0.1) + 40)) % len(self.cl.xy)
            ch = self.cl.heading[win]
            lane_xy = self.cl.xy[win] + lane * np.stack([-np.sin(ch), np.cos(ch)], 1)
            la = int(cfg.backup_lookahead / 0.1)
        if len(pts) == 0:
            pts = np.full((1, 2), 1e6)
        opp = np.array([[o[0], o[1], o[2], o[3], o[4] / max(o[3], 0.3)] for o in opps_world]).reshape(-1, 5)
        buf = np.zeros(2)
        sb = np.asarray(steer_buf, float)
        if len(sb) >= 1: buf[0] = sb[0]
        if len(sb) >= 2: buf[1] = sb[1]
        fixed = cfg.a_brake_fixed if cfg.reach == "fixed" else 0.0
        self._lane = (np.ascontiguousarray(lane_xy, dtype=np.float64), la)
        self._now = (np.ascontiguousarray(pts, dtype=np.float64), opp)
        return rollout_clearance(
            np.ascontiguousarray(cands, dtype=np.float64), np.asarray(x7, np.float64), buf, self.p,
            self.sat, self.tcs, 0.95, fixed, np.ascontiguousarray(pts, dtype=np.float64),
            np.ascontiguousarray(lane_xy, dtype=np.float64), la, opp, cfg.opp_brake,
            int(round(cfg.commit_time / 0.01)), int(cfg.max_pred_time / 0.01), 0.01, 2,
            CIRC_OFF, CIRC_R, WB, cfg.beta_max)

    # ------------------------------------------------------------------- main
    def __call__(self, a_rl, x7, steer_buf, scan, opps_ego, opps_world):
        """x7 = F1TENTH ST state (x, y, delta, v, yaw, yaw_rate, beta). Returns (a_final, lambda, info)."""
        cfg = self.cfg
        x, y, steer, v, yaw, yaw_rate, beta = x7
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

        pc = lambda c: self.predict_clearance(c, x7, steer_buf, scan, opps_world)
        c_rl = pc(a_rl[None])[0]
        thr = cfg.c_safe
        if cfg.escape:
            pts, opp = self._now
            c_now = current_clearance(np.asarray(x7, np.float64), pts, opp, CIRC_OFF, CIRC_R)
            # Only when (nearly) stopped: applying the relaxed rule while driving lets the clearance shrink by
            # escape_tol every step and ratchets the car into the wall (escape v2 did exactly that).
            if c_now < cfg.c_safe + 0.02 and v < cfg.escape_v:
                # Escape mode (stopped near or inside the margin). Every way out shrinks the clearance a little (the rear
                # swings out when turning away from a wall) and the 3-circle body model is ~3 cm fatter than the
                # car, so the usual threshold deadlocks. Allow at most escape_tol of shrinkage, and prefer slow
                # "creep" manoeuvres that keep the most clearance over the policy's (often aggressive) action.
                thr = min(cfg.c_safe, c_now - cfg.escape_tol)
                if c_rl >= thr:
                    return a_rl, 0.0, {"rho": 0.0, "fallback": False, "c_pred": float(c_rl), "escape": True}
                st_ = np.array([-S_MAX / 4, -S_MAX / 8, 0.0, S_MAX / 8, S_MAX / 4])
                creep = np.array([[a, sp] for sp in (1.0, 2.0) for a in st_])
                cc = pc(creep)
                ok = np.nonzero(cc >= thr)[0]
                if len(ok):
                    j = ok[np.argmax(cc[ok])]
                    return creep[j], 1.0, {"rho": 0.0, "fallback": True, "c_pred": float(cc[j]), "escape": True}
        if c_rl >= thr:
            return a_rl, 0.0, {"rho": rho, "fallback": False, "c_pred": float(c_rl)}

        # corrective direction: APF steering + braking (traction control limits the rate)
        a_corr = self.clip_action(np.array([a_rl[0] + a_apf[0], min(a_rl[1] + a_apf[1], 0.0)]))
        lams = np.array(cfg.blend_levels)
        cands = (1 - lams)[:, None] * a_rl[None] + lams[:, None] * a_corr[None]
        cl = pc(cands)
        ok = np.nonzero(cl >= thr)[0]
        if len(ok):
            i = ok[0]
            return cands[i], float(lams[i]), {"rho": rho, "fallback": False, "c_pred": float(cl[i])}
        if cfg.mode == "conditioned":
            return a_corr, 1.0, {"rho": rho, "fallback": False, "c_pred": float(cl[-1])}

        # fallback: replace the action. First candidate (NaN steer) is the backup
        # manoeuvre itself (brake + hold lane), which keeps the safety check
        # recursively feasible; the rest are fixed-steer braking manoeuvres.
        steers = np.array([np.nan, a_corr[0], -S_MAX, -S_MAX / 2, 0.0, S_MAX / 2, S_MAX, steer])
        fb = np.stack([steers, np.zeros_like(steers)], 1)
        fb_cl = pc(fb)
        j = 0 if fb_cl[0] >= thr else int(np.argmax(fb_cl))
        a = fb[j].copy()
        if np.isnan(a[0]):
            lane_xy, la = self._lane
            a[0] = float(np.clip(backup_steer(np.asarray(x7, np.float64), lane_xy, la, WB), -S_MAX, S_MAX))
        return a, 1.0, {"rho": rho, "fallback": True, "c_pred": float(fb_cl[j])}
