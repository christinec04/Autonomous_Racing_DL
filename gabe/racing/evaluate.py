"""Race-day evaluation with a target for every metric.

Every controller drives the same races, picked from one shared list of seeds.
Each race has 3 opponents and lasts 5 laps, or ends at the first collision.
All races run once in nominal conditions and once with randomised friction and lidar noise.

Controllers
  pure_pursuit                Pure Pursuit on the centerline
  pid_apf                     PID with the proposal's additive APF always on
  ppo                         PPO without a shield
  ppo_additive                PPO trained and raced with the additive APF shield
  ppo_apf                     PPO with our action-conditioned shield
  ppo_apf_rec                 the same plus deadlock escape and stall recovery (our method)
  ppo_residual                residual PPO on top of PID+APF, no shield
  ppo_residual_apf_rec        residual PPO with our shield and stall recovery
  ppo_residual_apf_rec_oxmu   the same with the two-hypothesis opponent check and the friction estimate
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool

import numpy as np

from .controllers import PIDFollower, PurePursuit
from .env import EnvConfig, RaceEnv
from .shield import ShieldConfig
from .sim import G

# metric name -> (comparison, target, description)
TARGETS = {
    "lap_time_vs_pid_apf": ("<=", 0.95, "mean clean-lap time relative to PID+APF (at least 5% faster)"),
    "collisions_per_10_laps": ("<=", 0.5, "collisions per 10 laps"),
    "overtake_success": (">=", 0.7, "completed passes / attempts"),
    "shield_freq_race": ("<=", 0.10, "fraction of race steps with lambda > 0"),
    "grip_above_90": (">=", 0.10, "fraction of time above 90% of mu*g"),
    "slip_above_15": ("<=", 0.01, "fraction of time with body slip above 15 deg"),
}

CAR_LEN = 0.58

_ESC = dict(mode="conditioned_fallback", reach="grip", escape=True, allow_reverse=True)
SHIELD_FOR = {
    "pure_pursuit": dict(mode="off"),
    "pid_apf": dict(mode="additive", reach="fixed", k_steer=0.3, k_speed=1.5, d_min=0.3, smooth=0.8),
    "ppo": dict(mode="off"),
    "ppo_additive": dict(mode="additive", reach="fixed"),
    "ppo_apf": dict(mode="conditioned_fallback", reach="grip"),
    "ppo_apf_rec": _ESC,
    "ppo_residual": dict(mode="off"),
    "ppo_residual_apf_rec": _ESC,
    "ppo_residual_apf_rec_oxmu": dict(_ESC, opp_both=True, opp_relax=True, mu_est=True),
}
# controllers that use the stall recovery in the environment
RECOVER = {name for name in SHIELD_FOR if "_rec" in name}


class OvertakeTracker:
    """Counts overtake attempts and successes.

    An attempt starts when the ego is within 3 m behind a slower opponent and moves off its line.
    It succeeds when the ego stays more than one car length ahead for 2 s without contact.
    """

    def __init__(self, n_opp):
        self.state = [dict(attempt=False, lat0=None, ahead_t=None) for _ in range(n_opp)]
        self.attempts = 0
        self.successes = 0

    def update(self, t, prog, lat, v, opp_prog, opp_lat, opp_v, contact, L):
        for i, s in enumerate(self.state):
            gap = (prog - opp_prog[i] + L / 2) % L - L / 2  # positive when the ego is ahead
            if not s["attempt"]:
                if -3.0 <= gap <= -CAR_LEN and v > opp_v[i]:
                    if s["lat0"] is None:
                        s["lat0"] = abs(lat - opp_lat[i])
                    elif abs(lat - opp_lat[i]) > s["lat0"] + 0.3:
                        s["attempt"] = True
                        s["ahead_t"] = None
                        self.attempts += 1
                else:
                    s["lat0"] = None
            elif contact or gap < -6.0:
                s["attempt"] = False
                s["lat0"] = None
            elif gap > CAR_LEN:
                if s["ahead_t"] is None:
                    s["ahead_t"] = t
                elif t - s["ahead_t"] >= 2.0:
                    self.successes += 1
                    s["attempt"] = False
                    s["lat0"] = None
            else:
                s["ahead_t"] = None


def make_controller(name, env, model_path=None, model=None):
    """Returns a function that maps an observation to a normalised action."""
    if name == "pure_pursuit":
        pp = PurePursuit(env.cl, speed_scale=0.85, mu=env.base_mu())
        return lambda obs: env.to_normalized(pp.act(*_ego(env)))
    if name == "pid_apf":
        pid = PIDFollower(env.cl, env.cfg.control_dt, speed_scale=0.85, mu=env.base_mu())
        return lambda obs: env.to_normalized(pid.act(*_ego(env)))
    if name.startswith("ppo"):
        if model is None:
            from stable_baselines3 import PPO
            model = PPO.load(model_path, device="cpu")
        return lambda obs: model.predict(obs[None], deterministic=True)[0][0]
    raise ValueError(name)


def _ego(env):
    e = env._states()[0]
    return e[0], e[1], e[4], e[3]


def residual_scale_for(model_path, default=0.3):
    """Residual scale the policy was trained with, read from args.json next to the model."""
    if not model_path:
        return default
    f = pathlib.Path(model_path).parent / "args.json"
    if f.exists():
        return json.load(open(f)).get("residual_scale", default)
    return default


def run_race(job):
    """Runs one race and returns its metrics.

    job = (controller, model_path, seed, randomize, laps, shield_override, label, tire, map_name, extra).
    The last four entries are optional.
    """
    ctrl, model_path, seed, randomize, laps, shield_override = job[:6]
    label = job[6] if len(job) > 6 else ctrl
    tire = job[7] if len(job) > 7 else "saturated"
    map_name = job[8] if len(job) > 8 else "Singapore"
    extra = job[9] if len(job) > 9 else {}
    n_opp = extra.get("n_opp", 3)
    mu_scale = extra.get("mu_scale")

    sh = shield_override or SHIELD_FOR[ctrl]
    if extra.get("shield_mu") and mu_scale is not None and sh.get("mode") not in ("off", "additive"):
        # stress test where the shield is told the true friction
        sh = dict(sh, mu_scale=mu_scale, mu=ShieldConfig().mu * mu_scale)
    model = None
    if ctrl.startswith("ppo") and model_path:
        from stable_baselines3 import PPO
        model = PPO.load(model_path, device="cpu")
    env_extra = {}
    if mu_scale is not None:
        # stress test with one fixed friction and no lidar noise
        randomize = True
        env_extra = dict(mu_range=(mu_scale, mu_scale), lidar_noise=(0.0, 0.0))
    cfg = EnvConfig(n_opp=n_opp, opp_speed=(0.5, 0.75), random_start=True, randomize=randomize,
                    shield=ShieldConfig(**sh), episode_time=laps * 70.0, seed=seed,
                    residual=ctrl.startswith("ppo_residual"), tire=tire, recover=ctrl in RECOVER,
                    map_name=map_name, residual_scale=residual_scale_for(model_path),
                    base_mu=extra.get("base_mu", "true"), **env_extra)
    env = RaceEnv(cfg)

    rng = np.random.default_rng(seed)
    opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))),
                opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
    if n_opp != 3:
        # scale the gaps so every opponent fits on the track
        gaps = list(np.cumsum(rng.uniform(5.0, 15.0, n_opp)))
        rng2 = np.random.default_rng(seed + 777)
        opts = dict(s_ego=3.0, opp_gaps=[g * min(1.0, 160.0 / gaps[-1]) for g in gaps],
                    opp_speeds=list(rng2.uniform(0.5, 0.75, n_opp)))
    obs, _ = env.reset(seed=seed, options=opts)
    act = make_controller(ctrl, env, model_path, model)

    L = env.cl.length
    tracker = OvertakeTracker(n_opp)
    lap_marks, lams, glat, glon, slip, mu_trace = [], [], [], [], [], []
    e0 = env._states()[0]
    prev_vel = np.array([e0[3] * np.cos(e0[4] + e0[6]), e0[3] * np.sin(e0[4] + e0[6])])
    wall = car = False
    while True:
        obs, r, term, trunc, info = env.step(act(obs))
        st = info["state"]
        lams.append(info["lambda"])
        v = st[3]
        # acceleration of the centre of gravity from the velocity vector, which stays correct while sliding
        heading = st[4] + st[6]
        vel = np.array([v * np.cos(heading), v * np.sin(heading)])
        acc = (vel - prev_vel) / cfg.control_dt
        prev_vel = vel
        glon.append(float(acc @ [np.cos(st[4]), np.sin(st[4])]))
        glat.append(float(acc @ [-np.sin(st[4]), np.cos(st[4])]))
        slip.append(abs(st[6]))
        if cfg.shield.mu_est and len(lams) % 25 == 1:
            mu_trace.append(round(env.shield.mu_hat, 3))
        tracker.update(info["t"], info["progress"], info["lat"], v * np.cos(info["hdg_err"]), info["opp_prog"],
                       info["opp_lat"], info["opp_v"], info["car"], L)
        if info["progress"] >= L * (len(lap_marks) + 1):
            lap_marks.append(info["t"])
        if term:
            wall, car = info["wall"], info["car"]
            break
        if len(lap_marks) >= laps or trunc:
            break

    lap_times = list(np.diff([0.0] + lap_marks))
    comb = np.hypot(np.array(glat), np.array(glon)) / (env.mu * G)
    out = dict(controller=label, map=map_name, seed=seed, randomize=randomize,
               laps_done=float(info["progress"] / L), laps_target=laps,
               stuck=bool(not (wall or car) and len(lap_marks) < laps),
               lap_times=lap_times, wall=bool(wall), car=bool(car), dnf=bool(wall or car),
               overtake_attempts=tracker.attempts, overtake_successes=tracker.successes,
               shield_freq=float(np.mean(np.array(lams) > 0)), lam_mean=float(np.mean(lams)),
               grip_above_90=float(np.mean(comb > 0.9)), grip_above_100=float(np.mean(comb > 1.0)),
               slip_above_15=float(np.mean(np.array(slip) > np.radians(15))),
               n_recover=int(info.get("n_recover", 0)),
               gg=[list(np.round(glat[::5], 2)), list(np.round(glon[::5], 2))])
    if cfg.shield.mu_est:
        out.update(mu_true=float(env.mu / ShieldConfig().mu), mu_hat=mu_trace)
    return out


def summarize(res):
    """Totals and means per controller."""
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
            races=len(R),
            finished=sum((not r["dnf"]) and len(r["lap_times"]) >= r.get("laps_target", 5) for r in R),
            stuck=sum((not r["dnf"]) and len(r["lap_times"]) < r.get("laps_target", 5) for r in R),
            lap_mean=float(np.mean(laps)) if laps else None,
            lap_std=float(np.std(laps)) if laps else None,
            lap_best=float(np.min(laps)) if laps else None,
            first_lap_mean=float(np.mean(first)) if first else None,
            collisions_per_10_laps=10 * coll / max(tot_laps, 1e-9),
            wall=sum(r["wall"] for r in R),
            car=sum(r["car"] for r in R),
            overtake_attempts=att,
            overtake_successes=suc,
            overtake_success=suc / att if att else None,
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
    if not xa or not xb or len(set(xa + xb)) == 1:
        return None
    return float(mannwhitneyu(xa, xb, alternative="two-sided").pvalue)


def check_targets(summary, ours="ppo_apf", ref="pid_apf"):
    s, r = summary.get(ours), summary.get(ref)
    if s is None:
        return {}
    lap_ratio = None
    if s["lap_mean"] and r and r["lap_mean"]:
        lap_ratio = s["lap_mean"] / r["lap_mean"]
    vals = {
        "lap_time_vs_pid_apf": lap_ratio,
        "collisions_per_10_laps": s["collisions_per_10_laps"],
        "overtake_success": s["overtake_success"],
        "shield_freq_race": s["shield_freq"],
        "grip_above_90": s["grip_above_90"],
        "slip_above_15": s["slip_above_15"],
    }
    out = {}
    for k, (op, target, desc) in TARGETS.items():
        v = vals[k]
        met = None if v is None else (v <= target if op == "<=" else v >= target)
        out[k] = dict(value=v, target=f"{op} {target}", met=met, desc=desc)
    return out


def _job_key(job):
    """Controller label, race seed and condition identify a race."""
    return [job[6], job[2], job[3]]


def _load_partial(partial, header, jobs):
    """Loads races saved by an earlier run of the same command that was interrupted.

    A partial file written by a different command is moved aside instead of being mixed in.
    """
    res = [None] * len(jobs)
    p = pathlib.Path(partial)
    if not p.exists():
        return res
    lines = p.read_text().splitlines()
    if not lines or json.loads(lines[0]).get("header") != header:
        aside = p.with_name(p.name + f".mismatch_{time.strftime('%Y%m%d_%H%M%S')}")
        p.rename(aside)
        print(f"partial results from a different command moved to {aside}", file=sys.stderr, flush=True)
        return res
    index = {json.dumps(_job_key(j)): i for i, j in enumerate(jobs)}
    for line in lines[1:]:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # the last line can be cut off by a crash
        i = index.get(json.dumps(rec["key"]))
        if i is not None:
            res[i] = rec["race"]
    n = sum(r is not None for r in res)
    print(f"resuming with {n}/{len(jobs)} races already saved in {p}", file=sys.stderr, flush=True)
    return res


def run_all(jobs, procs, tries=3, partial=None, header=None):
    """Races all jobs in parallel and returns the results in job order.

    If a worker process dies, the missing races are run again.
    With a partial file, every finished race is saved right away and is not rerun after a crash.
    """
    res = _load_partial(partial, header, jobs) if partial else [None] * len(jobs)
    pf = None
    if partial:
        new = not pathlib.Path(partial).exists()
        pf = open(partial, "a")
        if new:
            pf.write(json.dumps({"header": header}) + "\n")
            pf.flush()
    for _ in range(tries):
        todo = [i for i, r in enumerate(res) if r is None]
        if not todo:
            break
        try:
            with ProcessPoolExecutor(procs) as ex:
                futs = {ex.submit(run_race, jobs[i]): i for i in todo}
                for f in as_completed(futs):
                    i = futs[f]
                    res[i] = f.result()
                    if pf:
                        pf.write(json.dumps({"key": _job_key(jobs[i]), "race": res[i]}) + "\n")
                        pf.flush()
                        os.fsync(pf.fileno())
                    done = sum(r is not None for r in res)
                    if done % 10 == 0 or done == len(jobs):
                        print(f"{done}/{len(jobs)} races", file=sys.stderr, flush=True)
        except BrokenProcessPool:
            print(f"a worker died, rerunning {sum(r is None for r in res)} races", file=sys.stderr, flush=True)
    if pf:
        pf.close()
    if any(r is None for r in res):
        raise RuntimeError("races still missing after retries")
    return res


def _print_summary(summary):
    for c, s in summary.items():
        lap = s["lap_mean"] and round(s["lap_mean"], 2)
        best = s["lap_best"] and round(s["lap_best"], 2)
        print(f"{c:13s} finished {s['finished']}/{s['races']} (stuck {s['stuck']})  lap {lap} (best {best})"
              f"  coll/10laps {s['collisions_per_10_laps']:.2f} (wall {s['wall']}, car {s['car']})"
              f"  passes/race {s['passes_per_race']:.2f}  ot {s['overtake_successes']}/{s['overtake_attempts']}"
              f"  shield {s['shield_freq']:.2f}  grip>90% {s['grip_above_90']:.3f}"
              f" (>100% {s['grip_above_100']:.3f})  slip>15 {s['slip_above_15']:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--controllers", nargs="+", default=["pure_pursuit", "pid_apf"])
    ap.add_argument("--models", nargs="*", default=[], help="name=path pairs for the PPO controllers")
    ap.add_argument("--races", type=int, default=20)
    ap.add_argument("--first", type=int, default=0, help="first race index, to extend a study")
    ap.add_argument("--laps", type=int, default=5)
    ap.add_argument("--procs", type=int, default=14)
    ap.add_argument("--tire", default="saturated", choices=["saturated", "saturated_v2", "linear"])
    ap.add_argument("--map", default="Singapore", help="track in maps/ (Track2 is the unseen track)")
    ap.add_argument("--mu_scale", type=float, default=None, help="race at this fixed friction scale")
    ap.add_argument("--shield_mu", action="store_true", help="with --mu_scale, tell the shield the true friction")
    ap.add_argument("--n_opp", type=int, default=3, help="number of opponents")
    ap.add_argument("--base_mu", default="true", choices=["true", "nominal", "estimate"],
                    help="friction the classical controllers plan with")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    models = dict(m.split("=", 1) for m in args.models)
    conds = (True,) if args.mu_scale is not None else (False, True)
    extra = dict(n_opp=args.n_opp, mu_scale=args.mu_scale, shield_mu=args.shield_mu)
    header = dict(controllers=args.controllers, models=args.models, races=args.races, first=args.first,
                  laps=args.laps, tire=args.tire, map=args.map, mu_scale=args.mu_scale, shield_mu=args.shield_mu,
                  n_opp=args.n_opp)
    if args.base_mu != "true":
        # only added when set, so the header of older commands stays the same
        extra["base_mu"] = args.base_mu
        header["base_mu"] = args.base_mu
    jobs = []
    for randomize in conds:
        for c in args.controllers:
            base = c.split("@")[0]  # "name@tag" races controller "name" under the label "name@tag"
            for seed in range(args.first, args.first + args.races):
                jobs.append((base if base in SHIELD_FOR else c, models.get(c), 10_000 + seed, randomize, args.laps,
                             None, c, args.tire, args.map, extra))
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    partial = args.out + ".partial.jsonl"
    res = run_all(jobs, args.procs, partial=partial, header=header)

    report = {}
    for randomize in conds:
        key = "randomized" if randomize else "nominal"
        summ = summarize([r for r in res if r["randomize"] == randomize])
        report[key] = dict(summary=summ, targets=check_targets(summ))
        print(f"\n=== {key} ===")
        _print_summary(summ)
    with open(args.out, "w") as f:
        json.dump(dict(map=args.map, mu_scale=args.mu_scale, n_opp=args.n_opp, base_mu=args.base_mu, report=report,
                       races=res), f)
    os.remove(partial)
