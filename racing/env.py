"""Multi-car racing environment (Gymnasium) for the ego PPO agent.

Ego + up to 3 opponents (PID or Pure Pursuit, each at a fixed fraction of the
grip-limited speed profile, with simple gap keeping so they do not rear-end
each other). Observation, action and reward follow proposal Sec. III-B.
The APF shield (racing/shield.py) sits between the policy and the simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import gymnasium as gym
import numpy as np

from .controllers import PIDFollower, PurePursuit, curvature_speed_profile
from .shield import APFShield, ShieldConfig, BEAM_ANG
from .tires import set_tire_model, set_traction_control
from .sim import DEFAULT_PARAMS, Centerline, make_f110, set_scan_flags

S_MAX = DEFAULT_PARAMS["s_max"]
N_LIDAR_OBS = 60
LIDAR_CLIP = 10.0


_PROFILES = {}


def _profile(cl, mu, v_cap=20.0):
    """Grip-limited speed profile, cached by track and friction rounded to 0.005 (E39 base_mu="estimate")."""
    key = (id(cl), round(mu / 0.005))
    if key not in _PROFILES:
        _PROFILES[key] = curvature_speed_profile(cl, round(mu / 0.005) * 0.005, v_cap)
    return _PROFILES[key]


@dataclass
class EnvConfig:
    n_opp: int = 3
    opp_speed: tuple = (0.55, 0.8)  # fraction of the grip-limited profile
    opp_types: tuple = ("pid", "pp")
    random_start: bool = False  # stage 3: random grid order / gaps
    ego_v_min: float = 1.0
    ego_v_max: float = 16.0
    phys_dt: float = 0.01
    control_dt: float = 0.04
    episode_time: float = 40.0  # fixed-duration episodes -> more distance = more reward
    randomize: bool = False  # friction + lidar noise
    mu_range: tuple = (0.85, 1.15)
    lidar_noise: tuple = (0.0, 0.05)
    # reward weights (Eq. 1)
    w1_speed: float = 0.002
    w2_progress: float = 0.1
    w3_shield: float = 0.1
    w4_collision: float = 10.0
    w5_pass: float = 2.0
    w6_slip: float = 0.0  # optional: penalty per step for body slip beyond 0.15 rad (discourages sliding)
    shield: ShieldConfig = field(default_factory=ShieldConfig)
    curvature_preview: bool = False  # optional extra observation (experiment)
    # ResRace/RaceMOP-style residual policy: final = PID+APF base action + scale * policy action.
    # The APF shapes every command (contrast with our shield, which acts only when needed).
    residual: bool = False
    residual_scale: float = 0.3
    # shield dropout: per-episode probability that the shield is active (1.0 = always)
    shield_prob: float = 1.0
    tcs: bool = True  # traction control on all cars
    tire: str = "saturated"  # saturated (friction circle) | saturated_v2 (+ post-spin fixes) | linear (stock)
    # stall recovery (opt-in): if the ego makes < recover_dist progress in recover_window s while pointing more than
    # recover_hdg off the track direction (or within 0.5 m of the edge), take over: reverse with the steering that
    # swings the nose back toward the track direction, then follow the centerline forward, then hand back.
    # Every recovery command still goes through the shield.
    # E39: what friction the classical base controllers (residual base PID, stall-recovery PID, and in evaluate.py the
    # Pure Pursuit / PID+APF baselines) plan their speed profile with. "true" = the car's actual friction (as built
    # on Nov 4: privileged knowledge a real car would not have), "nominal" = the nominal value, "estimate" = the
    # shield's online friction estimate (needs ShieldConfig.mu_est; the profile is recomputed when it moves by > 0.02).
    base_mu: str = "true"
    recover: bool = False
    recover_window: float = 1.5
    recover_dist: float = 0.3
    recover_hdg: float = 0.35
    recover_rev_time: float = 1.5
    recover_fwd_time: float = 1.0
    # hotspot practice (opt-in, fine-tuning): with this probability an episode starts from rest at a random point in
    # hotspot_s (default: just before the chicane), with a random lateral offset and heading error
    hotspot_prob: float = 0.0
    hotspot_s: tuple = (55.0, 90.0)
    hotspot_d: float = 0.6
    hotspot_hdg: float = 0.3
    # track (maps/<map_name>/, built by racing/track_gen.py); "Track2" is the unseen generalisation track
    map_name: str = "Singapore"
    seed: int = 0


class RaceEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, cfg: EnvConfig | None = None):
        super().__init__()
        self.cfg = cfg or EnvConfig()
        set_tire_model(self.cfg.tire)
        set_traction_control(self.cfg.tcs)
        self.cl = Centerline.load(self.cfg.map_name)
        self.n = 1 + self.cfg.n_opp
        self.sim = make_f110(self.n, timestep=self.cfg.phys_dt, seed=self.cfg.seed, map_name=self.cfg.map_name)
        self.sub = int(round(self.cfg.control_dt / self.cfg.phys_dt))
        self.shield = APFShield(self.cfg.shield, self.cfg.control_dt, self.cl)
        self.shield.sat = {"linear": 0, "saturated": 1, "saturated_v2": 2}[self.cfg.tire]
        self.shield.tcs = self.cfg.tcs
        self.rng = np.random.default_rng(self.cfg.seed)
        n_obs = N_LIDAR_OBS + 5 + 2 * 5 + 2 + (10 if self.cfg.curvature_preview else 0)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (n_obs,), np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, (2,), np.float32)
        self.mu = DEFAULT_PARAMS["mu"]
        if self.cfg.residual:
            self.base_apf = APFShield(ShieldConfig(mode="additive", reach="fixed", k_steer=0.3, k_speed=1.5,
                                                   d_min=0.3, smooth=0.8), self.cfg.control_dt, self.cl)

    # ------------------------------------------------------------- helpers
    def _states(self):
        return np.array([a.state for a in self.sim.unwrapped.sim.agents])  # (n,7)

    def to_physical(self, a):
        a = np.clip(np.asarray(a, float), -1, 1)
        c = self.cfg
        return np.array([a[0] * S_MAX, c.ego_v_min + (a[1] + 1) / 2 * (c.ego_v_max - c.ego_v_min)])

    def to_normalized(self, a_phys):
        c = self.cfg
        return np.array([a_phys[0] / S_MAX, 2 * (a_phys[1] - c.ego_v_min) / (c.ego_v_max - c.ego_v_min) - 1])

    def _update_progress(self, st):
        for i in range(self.n):
            idx, s, d, h = self.cl.project(st[i, 0], st[i, 1], self.hints[i])
            self.hints[i] = idx
            ds = (s - self.s_prev[i] + self.cl.length / 2) % self.cl.length - self.cl.length / 2
            self.prog[i] += ds
            self.s_prev[i] = s
            self.lat[i] = d
            self.hdg_err[i] = (st[i, 4] - h + np.pi) % (2 * np.pi) - np.pi

    def _opponents_rel(self, st, k=2):
        """Nearest k opponents in ego frame: pos, relative vel, relative yaw."""
        e = st[0]
        ce, se = np.cos(e[4]), np.sin(e[4])
        ve = np.array([e[3] * np.cos(e[4]), e[3] * np.sin(e[4])])
        out = []
        for i in range(1, self.n):
            o = st[i]
            dx, dy = o[0] - e[0], o[1] - e[1]
            vo = np.array([o[3] * np.cos(o[4]), o[3] * np.sin(o[4])])
            dv = vo - ve
            out.append({
                "i": i, "dist": float(np.hypot(dx, dy)),
                "pos": np.array([dx * ce + dy * se, -dx * se + dy * ce]),
                "vel": np.array([dv[0] * ce + dv[1] * se, -dv[0] * se + dv[1] * ce]),
                "yaw": float((o[4] - e[4] + np.pi) % (2 * np.pi) - np.pi),
            })
        out.sort(key=lambda d: d["dist"])
        return out[:k], out

    def _obs(self, st, scan):
        e = st[0]
        pooled = scan[: N_LIDAR_OBS * (len(scan) // N_LIDAR_OBS)].reshape(N_LIDAR_OBS, -1).min(1)
        lid = np.clip(pooled, 0, LIDAR_CLIP) / LIDAR_CLIP
        own = [e[3] / 10.0, e[5] / 5.0, e[2] / S_MAX, self.lat[0] / 1.4, self.hdg_err[0] / np.pi]
        near, _ = self._opponents_rel(st, 2)
        opp = []
        for j in range(2):
            if j < len(near) and near[j]["dist"] < 20:
                o = near[j]
                opp += [o["pos"][0] / 10, o["pos"][1] / 10, o["vel"][0] / 10, o["vel"][1] / 10, 1.0]
            else:
                opp += [0, 0, 0, 0, 0]
        parts = [lid, own, opp, self.prev_action]
        if self.cfg.curvature_preview:
            i = self.hints[0]
            ahead = [(i + int(m / 0.1)) % len(self.cl.xy) for m in np.linspace(1, 20, 10)]
            parts.append(np.clip(self.cl.curvature[ahead] * 2, -1, 1))
        return np.concatenate(parts).astype(np.float32)

    # --------------------------------------------------------------- gym API
    def base_mu(self):
        """Friction the classical base controllers plan with (EnvConfig.base_mu, E39)."""
        if self.cfg.base_mu == "true":
            return self.mu
        if self.cfg.base_mu == "nominal":
            return DEFAULT_PARAMS["mu"]
        if self.cfg.base_mu == "estimate":
            return DEFAULT_PARAMS["mu"] * self.shield.mu_hat
        raise ValueError(self.cfg.base_mu)

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        options = options or {}
        c = self.cfg
        # domain randomisation
        self.mu = DEFAULT_PARAMS["mu"] * (self.rng.uniform(*c.mu_range) if c.randomize else 1.0)
        self.noise = self.rng.uniform(*c.lidar_noise) if c.randomize else 0.0
        p = dict(DEFAULT_PARAMS); p["mu"] = self.mu
        self.sim.unwrapped.configure({"params": p})

        # grid: ego at the back; opponents ahead
        s_ego = options.get("s_ego", 3.0 if not c.random_start else self.rng.uniform(0, self.cl.length))
        if "opp_gaps" in options:
            gaps = list(options["opp_gaps"])
        elif c.random_start:
            gaps = list(np.cumsum(self.rng.uniform(4.0, 15.0, c.n_opp)))
        else:
            gaps = [6.0 * (j + 1) for j in range(c.n_opp)]
        hot = "s_ego" not in options and c.hotspot_prob > 0 and self.rng.random() < c.hotspot_prob
        if hot:
            s_ego = self.rng.uniform(*c.hotspot_s)
            gaps = list(np.cumsum(self.rng.uniform(3.0, 10.0, c.n_opp)))  # traffic close ahead, into the chicane
            x, y, yaw = self.cl.pose_at(s_ego, self.rng.uniform(-c.hotspot_d, c.hotspot_d))
            poses = [(x, y, yaw + self.rng.uniform(-c.hotspot_hdg, c.hotspot_hdg))]
        else:
            poses = [self.cl.pose_at(s_ego, 0.0)]
        for j, g in enumerate(gaps):
            poses.append(self.cl.pose_at(s_ego + g, 0.0))
        self.sim.reset(options={"poses": np.array(poses)})

        speeds = options.get("opp_speeds", self.rng.uniform(*c.opp_speed, c.n_opp))
        self.opp_speeds = np.array(speeds, float)
        self.opps = []
        for j in range(c.n_opp):
            kind = c.opp_types[j % len(c.opp_types)]
            ctl = PIDFollower(self.cl, c.control_dt, mu=self.mu) if kind == "pid" else PurePursuit(self.cl, mu=self.mu)
            ctl.profile = ctl.profile * self.opp_speeds[j]
            self.opps.append(ctl)

        st = self._states()
        self.hints = [None] * self.n
        self.prog = np.zeros(self.n)
        self.s_prev = np.array([self.cl.project(st[i, 0], st[i, 1])[1] for i in range(self.n)])
        self.lat = np.zeros(self.n); self.hdg_err = np.zeros(self.n)
        self._update_progress(st)
        self.prog[:] = [0.0] + list(gaps)
        self.t = 0.0
        self.prev_action = np.zeros(2)
        self.prog_hist = []
        self.rec_phase, self.rec_t0, self.rec_cooldown, self.n_recover = None, 0.0, 0.0, 0
        self.shield.reset()
        self.shield_on = c.shield_prob >= 1.0 or self.rng.random() < c.shield_prob
        if c.residual:
            self.base_pid = PIDFollower(self.cl, c.control_dt, speed_scale=0.85, mu=self.base_mu())
            self._base_mu_used = self.base_mu()
            self.base_apf.reset()
        self.pass_state = {i: {"ahead_since": None, "rewarded": False} for i in range(1, self.n)}
        self.scan = self.sim.unwrapped.sim.agent_scans[0].copy()
        return self._obs(st, self.scan), {}

    def _recover(self, a_rl, e):
        """Stall recovery state machine (EnvConfig.recover). Returns the physical action to send to the shield."""
        c = self.cfg
        n = int(round(c.recover_window / c.control_dt))
        h = self.hdg_err[0]
        stalled = len(self.prog_hist) > n and self.prog[0] - self.prog_hist[-n] < c.recover_dist             and (abs(h) > c.recover_hdg or abs(self.lat[0]) > 0.9)
        # slow, near the edge and pointing outward: the policy is steering into the wall at crawling speed
        nose_out = e[3] < 1.5 and abs(self.lat[0]) > 0.95 and np.sign(h) == np.sign(self.lat[0]) and abs(h) > c.recover_hdg
        if self.rec_phase is None and self.t >= self.rec_cooldown and (stalled or nose_out):
            self.rec_phase, self.rec_t0 = "rev", self.t
            self.n_recover += 1
        if self.rec_phase == "rev":
            if abs(h) < 0.15 or self.t - self.rec_t0 >= c.recover_rev_time:
                self.rec_phase, self.rec_t0 = "fwd", self.t
                self.rec_pid = PIDFollower(self.cl, c.control_dt, mu=self.base_mu())
            else:
                # reversing (v < 0) turns the nose the opposite way to the steering, so steer toward the error
                return np.array([np.sign(h) * S_MAX, -1.0])
        if self.rec_phase == "fwd":
            if self.t - self.rec_t0 >= c.recover_fwd_time:
                self.rec_phase, self.rec_cooldown = None, self.t + 1.0
            else:
                steer, _ = self.rec_pid.act(e[0], e[1], e[4], e[3])
                return np.array([steer, 2.0])
        return a_rl

    def _opp_actions(self, st):
        acts = []
        for j, ctl in enumerate(self.opps):
            i = j + 1
            o = st[i]
            steer, v = ctl.act(o[0], o[1], o[4], o[3])
            # gap keeping to any car ahead in roughly the same lane
            for k in range(self.n):
                if k == i:
                    continue
                gap = (self.prog[k] - self.prog[i]) % self.cl.length
                if 0 < gap < 1.0 + 0.6 * o[3] and abs(self.lat[k] - self.lat[i]) < 0.7:
                    v = min(v, st[k, 3] + 1.5 * (gap - 1.0))
            acts.append([steer, max(v, 0.0)])
        return acts

    def step(self, action):
        c = self.cfg
        st = self._states()
        near, allopp = self._opponents_rel(st, 3)
        opps_world = [(st[i, 0], st[i, 1], st[i, 4], st[i, 3], st[i, 5]) for i in range(1, self.n)]
        if c.residual:
            e = st[0]
            if c.base_mu == "estimate" and abs(self.base_mu() - self._base_mu_used) > 0.02 * DEFAULT_PARAMS["mu"]:
                self._base_mu_used = self.base_mu()
                self.base_pid.profile = _profile(self.cl, self._base_mu_used) * 0.85
            base = np.array(self.base_pid.act(e[0], e[1], e[4], e[3]))
            base, _, _ = self.base_apf(base, e.copy(), None, self.scan, near, opps_world)
            act = np.clip(np.asarray(action, float), -1, 1)
            a_rl = base + c.residual_scale * np.array([act[0] * S_MAX, act[1] * (c.ego_v_max - c.ego_v_min) / 2])
        else:
            a_rl = self.to_physical(action)
        if c.recover:
            a_rl = self._recover(a_rl, st[0])
        ego = self.sim.unwrapped.sim.agents[0]
        if self.shield_on:
            a_final, lam, sinfo = self.shield(a_rl, st[0].copy(), ego.steer_buffer.copy(), self.scan, near, opps_world)
        else:
            a_final, lam, sinfo = self.shield.clip_action(np.asarray(a_rl, float)), 0.0, {}
        opp_a = self._opp_actions(st)
        acts = np.array([a_final] + opp_a)

        wall = car = False
        prog0 = self.prog[0]
        for k in range(self.sub):
            set_scan_flags(self.sim, last_substep=(k == self.sub - 1))
            obs, *_ = self.sim.step(acts)
            sim = self.sim.unwrapped.sim
            if sim.agents[0].in_collision:
                wall = True
            if sim.collision_idx[0] != -1:
                car = True
            if wall or car:
                break  # episode terminates; final obs is not bootstrapped
        st = self._states()
        self._update_progress(st)
        self.t += c.control_dt
        scan = self.sim.unwrapped.sim.agent_scans[0].copy()
        if self.noise > 0:
            scan = scan + self.rng.normal(0, self.noise, scan.shape)
        self.scan = np.maximum(scan, 0.0)

        # passes: ego ahead of an opponent by > 1 car length for 2 s without contact
        passes = 0
        for i, ps in self.pass_state.items():
            g = self.prog[0] - self.prog[i]
            if g > 0.6 and g < self.cl.length / 2:
                if ps["ahead_since"] is None:
                    ps["ahead_since"] = self.t
                elif not ps["rewarded"] and self.t - ps["ahead_since"] >= 2.0 and not (wall or car):
                    ps["rewarded"] = True; passes += 1
            elif g < 0:
                ps["ahead_since"] = None; ps["rewarded"] = False

        dprog = self.prog[0] - prog0
        v_par = st[0, 3] * np.cos(self.hdg_err[0])
        collided = wall or car
        r = (c.w1_speed * v_par + c.w2_progress * dprog + c.w5_pass * passes
             - c.w3_shield * lam - c.w4_collision * collided
             - c.w6_slip * max(abs(np.arctan2(np.sin(st[0, 6]), np.cos(st[0, 6]))) - 0.15, 0.0))
        self.prev_action = self.to_normalized(a_final)
        terminated = collided
        # stuck (e.g. shield stopped the car and the policy does not recover): end the episode
        self.prog_hist.append(self.prog[0])
        stuck = len(self.prog_hist) > 125 and self.prog[0] - self.prog_hist[-125] < 1.0
        truncated = self.t >= c.episode_time - 1e-9 or stuck
        info = {
            "lambda": lam, "wall": wall, "car": car, "passes": passes, "progress": float(self.prog[0]),
            "rho": sinfo.get("rho", 0.0), "fallback": sinfo.get("fallback", False),
            "a_rl": a_rl, "a_final": a_final, "t": self.t,
            "state": st[0].copy(), "opp_prog": self.prog[1:].copy(), "opp_lat": self.lat[1:].copy(),
            "lat": float(self.lat[0]), "mu": self.mu, "opp_v": st[1:, 3].copy(),
            "hdg_err": float(self.hdg_err[0]),
            "recovering": self.rec_phase is not None, "n_recover": self.n_recover,
            "c_pred": sinfo.get("c_pred", float("nan")),
        }
        return self._obs(st, self.scan), float(r), terminated, truncated, info
