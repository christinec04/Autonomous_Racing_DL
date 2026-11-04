"""Race-day evaluation (proposal Sec. III-F) with explicit metric targets.

Controllers (ego), identical scenarios from one shared seed list:
  pure_pursuit   Pure Pursuit on the centerline (classical floor)
  pid_apf        PID + APF, the APF always on (= the proposal's additive Eq. 2/3 layer)
  ppo            PPO, no shield (ablation)
  ppo_apf        PPO + action-conditioned APF shield (ours)

Each race: 3 opponents, 5 laps (or DNF on the first collision), random grid gaps
and opponent speeds from the shared seed. Run nominal and with randomised
friction + lidar noise.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
from multiprocessing import Pool

import numpy as np

from .controllers import PIDFollower, PurePursuit
from .env import EnvConfig, RaceEnv
from .shield import ShieldConfig
from .sim import G

# Target values for each metric (Introduction feedback). Our proposals; edit freely.
TARGETS = {
    "lap_time_vs_pid_apf": ("<=", 0.95, "mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster)"),
    "collisions_per_10_laps": ("<=", 0.5, "PPO+APF collisions per 10 laps"),
    "overtake_success": (">=", 0.7, "PPO+APF completed passes / attempts"),
    "shield_freq_race": ("<=", 0.10, "fraction of race steps with lambda > 0"),
    "grip_above_90": (">=", 0.10, "fraction of time above 90% of mu*g (uses the grip)"),
    "slip_above_15": ("<=", 0.01, "fraction of time with body slip > 15 deg (no sliding exploit)"),
}

CAR_LEN = 0.58


class OvertakeTracker:
    """Attempt: within 3 m behind an opponent, closing, and moving off its line.
    Success: ego > 1 car length ahead and holds it for 2 s without contact."""

    def __init__(self, n_opp):
        self.state = [dict(attempt=False, lat0=None, ahead_t=None) for _ in range(n_opp)]
        self.attempts = 0
        self.successes = 0

    def update(self, t, prog, lat, v, opp_prog, opp_lat, opp_v, contact, L):
        for i, s in enumerate(self.state):
            g = (prog - opp_prog[i] + L / 2) % L - L / 2  # + = ego ahead
            if not s["attempt"]:
                if -3.0 <= g <= -CAR_LEN and v > opp_v[i]:
                    if s["lat0"] is None:
                        s["lat0"] = abs(lat - opp_lat[i])
                    elif abs(lat - opp_lat[i]) > s["lat0"] + 0.3:
                        s["attempt"] = True; s["ahead_t"] = None
                        self.attempts += 1
                else:
                    s["lat0"] = None
            else:
                if contact or g < -6.0:
                    s["attempt"] = False; s["lat0"] = None
                elif g > CAR_LEN:
                    if s["ahead_t"] is None:
                        s["ahead_t"] = t
                    elif t - s["ahead_t"] >= 2.0:
                        self.successes += 1
                        s["attempt"] = False; s["lat0"] = None
                else:
                    s["ahead_t"] = None


def make_controller(name, env, model_path=None):
    if name == "pure_pursuit":
        pp = PurePursuit(env.cl, speed_scale=0.85, mu=env.mu)
        return lambda obs: env.to_normalized(pp.act(*_ego(env)))
    if name == "pid_apf":
        pid = PIDFollower(env.cl, env.cfg.control_dt, speed_scale=0.85, mu=env.mu)
        return lambda obs: env.to_normalized(pid.act(*_ego(env)))
    if name.startswith("ppo"):
        from stable_baselines3 import PPO
        model = PPO.load(model_path, device="cpu")
        return lambda obs: model.predict(obs[None], deterministic=True)[0][0]
    raise ValueError(name)


def _ego(env):
    e = env._states()[0]
    return e[0], e[1], e[4], e[3]


SHIELD_FOR = {
    "pure_pursuit": dict(mode="off"),
    "pid_apf": dict(mode="additive", reach="fixed", k_steer=0.3, k_speed=1.5, d_min=0.3, smooth=0.8),  # tuned, scripts/tune_apf.py
    "ppo": dict(mode="off"),
    "ppo_apf": dict(mode="conditioned_fallback", reach="grip"),
    "ppo_residual": dict(mode="off"),  # ResRace-style: APF base inside the env
    "ppo_additive": dict(mode="additive", reach="fixed"),  # PPO trained with the proposal's Eq. 2/3 shield
}


def run_race(job):
    ctrl, model_path, seed, randomize, laps, shield_override = job[:6]
    label = job[6] if len(job) > 6 else ctrl
    sh = shield_override or SHIELD_FOR[ctrl]
    cfg = EnvConfig(n_opp=3, opp_speed=(0.5, 0.75), random_start=True, randomize=randomize,
                    shield=ShieldConfig(**sh), episode_time=laps * 70.0, seed=seed,
                    residual=(ctrl == "ppo_residual"))
    env = RaceEnv(cfg)
    rng = np.random.default_rng(seed)
    opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))),
                opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
    obs, _ = env.reset(seed=seed, options=opts)
    act = make_controller(ctrl, env, model_path)
    L = env.cl.length
    ot = OvertakeTracker(3)
    lap_marks, lams, glat, glon, slip = [], [], [], [], []
    e0 = env._states()[0]
    prev_vel = np.array([e0[3] * np.cos(e0[4] + e0[6]), e0[3] * np.sin(e0[4] + e0[6])])
    wall = car = False
    while True:
        a = act(obs)
        obs, r, term, trunc, info = env.step(a)
        st = info["state"]
        lams.append(info["lambda"])
        v = st[3]
        # true CoG acceleration from the velocity vector (v * yaw_rate is wrong while sliding)
        hd = st[4] + st[6]
        vel = np.array([v * np.cos(hd), v * np.sin(hd)])
        acc = (vel - prev_vel) / cfg.control_dt; prev_vel = vel
        glon.append(float(acc @ [np.cos(st[4]), np.sin(st[4])]))
        glat.append(float(acc @ [-np.sin(st[4]), np.cos(st[4])]))
        slip.append(abs(st[6]))
        ot.update(info["t"], info["progress"], info["lat"], v * np.cos(info["hdg_err"]), info["opp_prog"],
                  info["opp_lat"], info["opp_v"], info["car"], L)
        if info["progress"] >= L * (len(lap_marks) + 1):
            lap_marks.append(info["t"])
        if term:
            wall, car = info["wall"], info["car"]
            break
        if len(lap_marks) >= laps or trunc:
            break
    laps_done = info["progress"] / L
    lap_times = list(np.diff([0.0] + lap_marks))
    mg = env.mu * G
    comb = np.hypot(np.array(glat), np.array(glon)) / mg
    return dict(controller=label, seed=seed, randomize=randomize, laps_done=float(laps_done),
                lap_times=lap_times, wall=bool(wall), car=bool(car), dnf=bool(wall or car),
                overtake_attempts=ot.attempts, overtake_successes=ot.successes,
                shield_freq=float(np.mean(np.array(lams) > 0)), lam_mean=float(np.mean(lams)),
                grip_above_90=float(np.mean(comb > 0.9)), grip_above_100=float(np.mean(comb > 1.0)),
                slip_above_15=float(np.mean(np.array(slip) > np.radians(15))),
                gg=[list(np.round(glat[::5], 2)), list(np.round(glon[::5], 2))])


def summarize(res):
    out = {}
    for c in sorted(set(r["controller"] for r in res)):
        R = [r for r in res if r["controller"] == c]
        laps = [t for r in R for t in r["lap_times"][1:]]  # skip the standing-start lap
        first = [r["lap_times"][0] for r in R if r["lap_times"]]
        tot_laps = sum(r["laps_done"] for r in R)
        coll = sum(r["dnf"] for r in R)
        att = sum(r["overtake_attempts"] for r in R)
        suc = sum(r["overtake_successes"] for r in R)
        out[c] = dict(
            races=len(R), finished=sum(not r["dnf"] for r in R),
            lap_mean=float(np.mean(laps)) if laps else None, lap_std=float(np.std(laps)) if laps else None,
            lap_best=float(np.min(laps)) if laps else None,
            first_lap_mean=float(np.mean(first)) if first else None,
            collisions_per_10_laps=10 * coll / max(tot_laps, 1e-9),
            wall=sum(r["wall"] for r in R), car=sum(r["car"] for r in R),
            overtake_attempts=att, overtake_successes=suc, overtake_success=suc / att if att else None,
            passes_per_race=suc / len(R),
            shield_freq=float(np.mean([r["shield_freq"] for r in R])),
            lam_mean=float(np.mean([r["lam_mean"] for r in R])),
            grip_above_90=float(np.mean([r["grip_above_90"] for r in R])),
            grip_above_100=float(np.mean([r["grip_above_100"] for r in R])),
            slip_above_15=float(np.mean([r["slip_above_15"] for r in R])),
        )
    return out


def mann_whitney(res, a, b, key):
    from scipy.stats import mannwhitneyu
    xa = [r[key] for r in res if r["controller"] == a]
    xb = [r[key] for r in res if r["controller"] == b]
    if not xa or not xb or (len(set(xa + xb)) == 1):
        return None
    return float(mannwhitneyu(xa, xb, alternative="two-sided").pvalue)


def check_targets(summary, ours="ppo_apf", ref="pid_apf"):
    s, r = summary.get(ours), summary.get(ref)
    if s is None:
        return {}
    vals = {
        "lap_time_vs_pid_apf": (s["lap_mean"] / r["lap_mean"]) if (s["lap_mean"] and r and r["lap_mean"]) else None,
        "collisions_per_10_laps": s["collisions_per_10_laps"],
        "overtake_success": s["overtake_success"],
        "shield_freq_race": s["shield_freq"],
        "grip_above_90": s["grip_above_90"],
        "slip_above_15": s["slip_above_15"],
    }
    out = {}
    for k, (op, tgt, desc) in TARGETS.items():
        v = vals[k]
        ok = None if v is None else (v <= tgt if op == "<=" else v >= tgt)
        out[k] = dict(value=v, target=f"{op} {tgt}", met=ok, desc=desc)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--controllers", nargs="+", default=["pure_pursuit", "pid_apf"])
    ap.add_argument("--models", nargs="*", default=[], help="name=path pairs for ppo controllers")
    ap.add_argument("--races", type=int, default=20)
    ap.add_argument("--laps", type=int, default=5)
    ap.add_argument("--procs", type=int, default=14)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    models = dict(m.split("=", 1) for m in args.models)
    jobs = []
    for randomize in (False, True):
        for c in args.controllers:
            base = c.split("@")[0]
            for seed in range(args.races):
                jobs.append((base if base in SHIELD_FOR else c, models.get(c), 10_000 + seed, randomize, args.laps, None, c))
    with Pool(args.procs) as p:
        res = p.map(run_race, jobs, chunksize=1)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    report = {}
    for randomize in (False, True):
        R = [r for r in res if r["randomize"] == randomize]
        key = "randomized" if randomize else "nominal"
        summ = summarize(R)
        report[key] = dict(summary=summ, targets=check_targets(summ))
        print(f"\n=== {key} ===")
        for c, s in summ.items():
            print(f"{c:13s} finished {s['finished']}/{s['races']}  lap {s['lap_mean'] and round(s['lap_mean'],2)}"
                  f" (best {s['lap_best'] and round(s['lap_best'],2)})  coll/10laps {s['collisions_per_10_laps']:.2f}"
                  f" (wall {s['wall']}, car {s['car']})  passes/race {s['passes_per_race']:.2f}"
                  f" ot {s['overtake_successes']}/{s['overtake_attempts']}  shield {s['shield_freq']:.2f}"
                  f"  grip>90% {s['grip_above_90']:.3f} (>100% {s['grip_above_100']:.3f})  slip>15 {s['slip_above_15']:.3f}")
    json.dump(dict(report=report, races=res), open(args.out, "w"))
