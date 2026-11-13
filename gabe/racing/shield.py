"""APF safety shield.

Modes
  additive              The proposal's Eq. 2-3. The APF correction is added with a weight that depends
                        only on obstacle distance and speed, never on the agent's action.
  conditioned           Our action-conditioned shield. It predicts the agent's action followed by a braking
                        manoeuvre and steps in only if that prediction hits something. It then blends toward
                        the APF-corrected action with the smallest weight lambda that is predicted safe.
  conditioned_fallback  The same, but if no blend is safe the action is replaced by the safest of a few
                        braking manoeuvres.

Reach
  fixed   the APF reach assumes a fixed braking deceleration
  grip    the APF reach uses the grip left after cornering, sqrt((mu g)^2 - (v * yaw_rate)^2)

Actions here are physical, (steering angle in rad, target speed in m/s).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .predict import backup_steer, current_clearance, rollout_clearance
from .sim import DEFAULT_PARAMS as P, G

WB = P["lf"] + P["lr"]
L, W = P["length"], P["width"]
S_MAX = P["s_max"]
N_BEAMS, FOV = 1080, 4.7
BEAM_ANG = np.linspace(-FOV / 2, FOV / 2, N_BEAMS)
D_THETA = FOV / (N_BEAMS - 1)
COS_B, SIN_B = np.cos(BEAM_ANG), np.sin(BEAM_ANG)
# distance from the car centre to the edge of the body along each beam
BODY = np.minimum((L / 2) / np.maximum(np.abs(COS_B), 1e-6), (W / 2) / np.maximum(np.abs(SIN_B), 1e-6))
# three circles cover the body in the collision check
CIRC_OFF = np.array([-L / 3, 0.0, L / 3])
CIRC_R = float(np.hypot(W / 2, L / 6))


@dataclass
class ShieldConfig:
    mode: str = "off"  # off, additive, conditioned or conditioned_fallback
    reach: str = "grip"  # fixed or grip
    a_brake_fixed: float = 6.0  # braking deceleration assumed by reach="fixed"
    mu: float = P["mu"]
    a_max: float = P["a_max"]
    d_min: float = 0.30  # clearance in m where the field starts at zero closing speed
    d_crit: float = 0.05  # clearance in m where the correction takes over fully
    k_steer: float = 2.0  # steering correction in rad per unit of lateral force
    k_speed: float = 2.0  # fraction of speed removed per unit of backward force
    opp_a: float = 0.6  # extra length of the opponent ellipse in m
    opp_b: float = 0.15  # extra width of the opponent ellipse in m
    smooth: float = 0.5  # smoothing of the additive correction
    c_safe: float = 0.05  # predicted clearance below this counts as a collision
    mu_scale: float = 1.0  # friction the predictor assumes, as a fraction of nominal
    commit_time: float = 0.04  # how long the agent's action is held before the braking manoeuvre
    max_pred_time: float = 3.0
    blend_levels: tuple = (0.25, 0.5, 0.75, 1.0)
    beam_stride: int = 3  # use every third lidar beam in the prediction
    beta_max: float = 0.35  # predicted body slip above about 20 deg counts as loss of control
    use_map: bool = True  # also check the known track walls
    backup_lookahead: float = 1.2
    # deadlock escape when stopped next to an obstacle
    escape: bool = False
    escape_tol: float = 0.02  # clearance in m the car may lose while escaping
    escape_v: float = 0.5  # escape only below this speed
    allow_reverse: bool = False  # let negative target speeds through for the stall recovery
    opp_brake: float = 6.0  # deceleration the prediction assumes for opponents
    # also check opponents that keep their speed and use the lower clearance
    opp_both: bool = False
    # with opp_both, if nothing is safe under both checks, decide with the braking check alone
    opp_relax: bool = False
    # online friction estimate
    mu_est: bool = False
    mu_est_rate: float = 0.5  # weight of a reading taken at the grip limit
    mu_est_rise: float = 0.05  # weight of a reading below the limit that shows more grip


def available_decel(cfg: ShieldConfig, v: float, yaw_rate: float, mu: float | None = None) -> float:
    if cfg.reach == "fixed":
        return cfg.a_brake_fixed
    mg = (cfg.mu if mu is None else mu) * G
    a_lat = abs(v * yaw_rate)
    return float(np.clip(np.sqrt(max(mg * mg - a_lat * a_lat, 0.0)), 1.0, cfg.a_max))


class APFShield:
    def __init__(self, cfg: ShieldConfig, control_dt: float, centerline=None, half_width: float = 1.4):
        self.cfg = cfg
        self.dt = control_dt
        self.cl = centerline
        self.p = np.array([P[k] for k in ("mu", "C_Sf", "C_Sr", "lf", "lr", "h", "m", "I", "s_min", "s_max",
                                          "sv_min", "sv_max", "v_switch", "a_max", "v_min", "v_max")], float)
        self.p[0] *= cfg.mu_scale
        self.sat = 1  # tyre model of the prediction, 0 linear, 1 saturated, 2 saturated_v2
        self.tcs = True
        self.braking_only = False  # set while deciding with the braking check alone
        if centerline is not None:
            n = np.stack([-np.sin(centerline.heading), np.cos(centerline.heading)], 1)
            self.walls = np.concatenate([centerline.xy + half_width * n, centerline.xy - half_width * n])
            self.half_width = half_width
        self.reset()

    def reset(self):
        self.corr = np.zeros(2)
        self.mu_hat = self.cfg.mu_scale  # friction estimate as a fraction of nominal
        self._prev = None
        self._set_mu(self.mu_hat)

    def _set_mu(self, scale):
        self.p[0] = P["mu"] * scale
        self.mu_now = self.cfg.mu / self.cfg.mu_scale * scale if self.cfg.mu_scale else self.cfg.mu

    def update_mu(self, x7):
        """Updates the friction estimate from two consecutive states.

        When a tyre's slip angle passes the point where its force saturates, the car is at the grip limit
        and the measured acceleration divided by g is the friction. Below the limit, an acceleration above
        the estimate shows there is more grip.
        """
        cfg = self.cfg
        prev = self._prev
        self._prev = np.array(x7, float)
        v = x7[3]
        if prev is None or v < 2.0 or prev[3] < 2.0:
            return
        r, b, d = x7[5], x7[6], x7[2]
        ax = (v - prev[3]) / self.dt
        ay = v * (r + np.arctan2(np.sin(b - prev[6]), np.cos(b - prev[6])) / self.dt)
        m = float(np.hypot(ax, ay)) / (P["mu"] * G)  # friction used, as a fraction of nominal
        if m > 1.6:
            return  # a contact or a spin, not a reading
        alpha_f = d - b - P["lf"] * r / v
        alpha_r = -b + P["lr"] * r / v
        room = np.sqrt(max(1.0 - (ax / (self.mu_hat * P["mu"] * G)) ** 2, 0.0))
        at_limit = max(abs(alpha_f) * P["C_Sf"], abs(alpha_r) * P["C_Sr"]) >= 0.95 * room
        if at_limit:
            self.mu_hat += cfg.mu_est_rate * (m - self.mu_hat)
        elif m > self.mu_hat:
            self.mu_hat += cfg.mu_est_rise * (m - self.mu_hat)
        self.mu_hat = float(np.clip(self.mu_hat, 0.5, 1.3))
        self._set_mu(self.mu_hat)

    def field(self, scan, v, yaw_rate, opps):
        """Repulsive force in the ego frame and the largest risk rho in [0, 1].

        Each opponent is a dict with ego-frame 'pos', relative 'vel' and relative 'yaw'.
        """
        cfg = self.cfg
        ab = available_decel(cfg, v, yaw_rate, self.mu_now)
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
            # ego centre in the opponent's frame
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
                # gradient of the ellipse, pointing away from the opponent
                gx, gy = ex / A ** 2, ey / B ** 2
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

    def predict_clearance(self, cands, x7, steer_buf, scan, opps_world):
        """Smallest predicted clearance for each candidate action (K x 2) with the exact vehicle model."""
        cfg = self.cfg
        x0, y0, yaw0, v0 = x7[0], x7[1], x7[4], x7[3]
        idx = slice(None, None, cfg.beam_stride)
        r = scan[idx]
        keep = r < 25.0
        ang = BEAM_ANG[idx][keep] + yaw0
        pts = np.stack([x0 + r[keep] * np.cos(ang), y0 + r[keep] * np.sin(ang)], 1)
        reach = v0 * 1.5 + 2.0
        pts = pts[np.hypot(pts[:, 0] - x0, pts[:, 1] - y0) < reach]
        for o in opps_world:
            # lidar hits on opponents are dropped, opponents are checked as moving cars instead
            if len(pts):
                pts = pts[np.hypot(pts[:, 0] - o[0], pts[:, 1] - o[1]) > 0.5]
        lane_xy = np.zeros((60, 2))
        lookahead = 12
        if cfg.use_map and self.cl is not None:
            w = self.walls[np.hypot(self.walls[:, 0] - x0, self.walls[:, 1] - y0) < reach]
            pts = np.concatenate([pts, w]) if len(pts) else w
            # the braking manoeuvre follows the current lane
            ci, _, lat0, _ = self.cl.project(x0, y0)
            lane = float(np.clip(lat0, -self.half_width + 0.4, self.half_width - 0.4))
            win = (ci + np.arange(-10, int(reach / 0.1) + 40)) % len(self.cl.xy)
            ch = self.cl.heading[win]
            lane_xy = self.cl.xy[win] + lane * np.stack([-np.sin(ch), np.cos(ch)], 1)
            lookahead = int(cfg.backup_lookahead / 0.1)
        if len(pts) == 0:
            pts = np.full((1, 2), 1e6)
        # opponents as (x, y, yaw, speed, curvature)
        opp = np.array([[o[0], o[1], o[2], o[3], o[4] / max(o[3], 0.3)] for o in opps_world]).reshape(-1, 5)
        # the last two steering commands, still in the servo's delay line
        buf = np.zeros(2)
        sb = np.asarray(steer_buf, float)
        n = min(len(sb), 2)
        buf[:n] = sb[:n]
        fixed = cfg.a_brake_fixed if cfg.reach == "fixed" else 0.0
        pts = np.ascontiguousarray(pts, dtype=np.float64)
        lane_xy = np.ascontiguousarray(lane_xy, dtype=np.float64)
        self._lane = (lane_xy, lookahead)
        self._now = (pts, opp)

        def run(opp_brake, op):
            return rollout_clearance(
                np.ascontiguousarray(cands, dtype=np.float64), np.asarray(x7, np.float64), buf, self.p,
                self.sat, self.tcs, 0.95, fixed, pts, lane_xy, lookahead, np.ascontiguousarray(op, dtype=np.float64),
                opp_brake, int(round(cfg.commit_time / 0.01)), int(cfg.max_pred_time / 0.01), 0.01, 2,
                CIRC_OFF, CIRC_R, WB, cfg.beta_max)

        c = run(cfg.opp_brake, opp)
        if cfg.opp_both and len(opp) and not self.braking_only:
            c = np.minimum(c, run(0.0, opp))
        return c

    def __call__(self, a_rl, x7, steer_buf, scan, opps_ego, opps_world):
        """Returns (final action, lambda, info).

        x7 is the F1TENTH single-track state (x, y, steering, v, yaw, yaw_rate, slip angle).
        """
        cfg = self.cfg
        steer, v, yaw_rate = x7[2], x7[3], x7[5]
        if cfg.mu_est and not self.braking_only:
            self.update_mu(x7)
        a_rl = self.clip_action(np.asarray(a_rl, float), v_lo=-1.0 if cfg.allow_reverse else 0.0)
        if cfg.mode == "off":
            return a_rl, 0.0, {"rho": 0.0, "fallback": False}

        F, rho, _ = self.field(scan, v, yaw_rate, opps_ego)
        a_apf = self.apf_correction(F, v)

        if cfg.mode == "additive":
            w = rho  # the weight of Eq. 3
            self.corr = cfg.smooth * self.corr + (1 - cfg.smooth) * w * a_apf
            a = self.clip_action(a_rl + self.corr)
            return a, float(np.clip(w, 0, 1)), {"rho": rho, "fallback": False}

        def predict(cands):
            return self.predict_clearance(cands, x7, steer_buf, scan, opps_world)

        c_rl = predict(a_rl[None])[0]
        thr = cfg.c_safe
        if cfg.escape:
            pts, opp = self._now
            c_now = current_clearance(np.asarray(x7, np.float64), pts, opp, CIRC_OFF, CIRC_R)
            if c_now < cfg.c_safe + 0.02 and v < cfg.escape_v:
                # Stopped inside the margin. Every way out loses a little clearance, so allow a small loss
                # and prefer slow creeping or reversing over the agent's action.
                thr = min(cfg.c_safe, c_now - cfg.escape_tol)
                if c_rl >= thr:
                    return a_rl, 0.0, {"rho": 0.0, "fallback": False, "c_pred": float(c_rl), "escape": True}
                steers = np.array([-S_MAX / 4, -S_MAX / 8, 0.0, S_MAX / 8, S_MAX / 4])
                creep = np.array([[a, sp] for sp in (1.0, 2.0, -1.0) for a in steers])
                cc = predict(creep)
                ok = np.nonzero(cc >= thr)[0]
                if len(ok):
                    j = ok[np.argmax(cc[ok])]
                    return creep[j], 1.0, {"rho": 0.0, "fallback": True, "c_pred": float(cc[j]), "escape": True}
        if c_rl >= thr:
            return a_rl, 0.0, {"rho": rho, "fallback": False, "c_pred": float(c_rl)}

        # blend toward the APF correction, steering plus braking
        a_corr = self.clip_action(np.array([a_rl[0] + a_apf[0], min(a_rl[1] + a_apf[1], 0.0)]))
        lams = np.array(cfg.blend_levels)
        cands = (1 - lams)[:, None] * a_rl[None] + lams[:, None] * a_corr[None]
        cl = predict(cands)
        ok = np.nonzero(cl >= thr)[0]
        if len(ok):
            i = ok[0]
            return cands[i], float(lams[i]), {"rho": rho, "fallback": False, "c_pred": float(cl[i])}
        if cfg.mode == "conditioned":
            return a_corr, 1.0, {"rho": rho, "fallback": False, "c_pred": float(cl[-1])}

        # Fallback braking manoeuvres. The first one (NaN steering) brakes while holding the lane,
        # which is the manoeuvre every prediction ends with. The others brake with a fixed steering angle.
        steers = np.array([np.nan, a_corr[0], -S_MAX, -S_MAX / 2, 0.0, S_MAX / 2, S_MAX, steer])
        fb = np.stack([steers, np.zeros_like(steers)], 1)
        fb_cl = predict(fb)
        if cfg.opp_both and cfg.opp_relax and not self.braking_only and fb_cl.max() < thr:
            # nothing is safe if opponents may also keep their speed, so decide with the braking check alone
            self.braking_only = True
            try:
                return self(a_rl, x7, steer_buf, scan, opps_ego, opps_world)
            finally:
                self.braking_only = False
        j = 0 if fb_cl[0] >= thr else int(np.argmax(fb_cl))
        a = fb[j].copy()
        if np.isnan(a[0]):
            lane_xy, lookahead = self._lane
            a[0] = float(np.clip(backup_steer(np.asarray(x7, np.float64), lane_xy, lookahead, WB), -S_MAX, S_MAX))
        return a, 1.0, {"rho": rho, "fallback": True, "c_pred": float(fb_cl[j])}
