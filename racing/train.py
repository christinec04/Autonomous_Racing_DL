"""PPO training with the 3-stage curriculum (proposal Sec. III-D).

  stage 1: solo laps                  (n_opp=0, random start position)
  stage 2: slow opponents             (n_opp=3, 0.45-0.6 of the speed profile)
  stage 3: varied opponents/starts    (n_opp=3, 0.5-0.85, random grid gaps)

The shield setting is fixed for the whole run, so the unshielded ablation is
"same curriculum, shield off in every stage" (Plan feedback).

Training efficiency (Plan feedback): every `eval_every` steps we run the current
policy for one solo lap twice, *with* and *without* the shield, and log both.
"Steps to first clean lap" is reported from the unshielded evaluation, so the
shield cannot make it look better than the policy really is.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import time

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor, VecNormalize

from .env import EnvConfig, RaceEnv
from .shield import ShieldConfig

SHIELDS = {
    "off": dict(mode="off"),
    "additive": dict(mode="additive", reach="fixed"),  # proposal Eq. 2/3
    "cond_fb_grip": dict(mode="conditioned_fallback", reach="grip"),
    "cond_fb_fixed": dict(mode="conditioned_fallback", reach="fixed"),
}

STAGES = {
    1: dict(n_opp=0, random_start=True),
    2: dict(n_opp=3, opp_speed=(0.45, 0.6), random_start=False),
    3: dict(n_opp=3, opp_speed=(0.5, 0.85), random_start=True),
}


def make_cfg(stage: int, shield: str, seed: int, tire: str = "saturated", randomize: bool = True,
             curvature_preview: bool = False, residual: bool = False) -> EnvConfig:
    st = STAGES[stage]
    return EnvConfig(n_opp=st["n_opp"], opp_speed=st.get("opp_speed", (0.55, 0.8)),
                     random_start=st["random_start"], shield=ShieldConfig(**SHIELDS[shield]),
                     randomize=randomize, tire=tire, seed=seed, curvature_preview=curvature_preview,
                     residual=residual)


def _env_fn(cfg: EnvConfig, rank: int):
    def f():
        import dataclasses
        c = dataclasses.replace(cfg, seed=cfg.seed * 1000 + rank)
        e = RaceEnv(c)
        e.reset(seed=c.seed)
        return e
    return f


def eval_lap(model, vecnorm, cfg: EnvConfig, shield: str, max_time: float = 60.0, s_ego: float = 3.0):
    """One solo lap from the grid. Returns dict(clean, lap_time, crash, lam_freq, progress)."""
    import dataclasses
    c = dataclasses.replace(cfg, n_opp=0, random_start=False, randomize=False,
                            shield=ShieldConfig(**SHIELDS[shield]), episode_time=max_time)
    env = RaceEnv(c)
    obs, _ = env.reset(seed=0, options={"s_ego": s_ego})
    lams = []
    while True:
        o = vecnorm.normalize_obs(obs[None]) if vecnorm is not None and vecnorm.norm_obs else obs[None]
        a, _ = model.predict(o, deterministic=True)
        obs, r, term, trunc, info = env.step(a[0])
        lams.append(info["lambda"])
        if info["progress"] >= env.cl.length:
            return dict(clean=True, lap_time=info["t"], crash=False, lam_freq=float(np.mean(np.array(lams) > 0)),
                        progress=info["progress"])
        if term or trunc:
            return dict(clean=False, lap_time=None, crash=bool(term), lam_freq=float(np.mean(np.array(lams) > 0)),
                        progress=info["progress"])


class TrainLogger(BaseCallback):
    def __init__(self, out_dir: pathlib.Path, cfg: EnvConfig, eval_every: int, stage_offset: int = 0):
        super().__init__()
        self.out = out_dir
        self.cfg = cfg
        self.eval_every = eval_every
        self.offset = stage_offset
        self.next_eval = eval_every
        self.ep = {"crash": 0, "eps": 0, "lam": [], "fallback": 0, "steps": 0, "passes": 0}
        self.train_f = open(out_dir / "train_log.csv", "a", newline="")
        self.eval_f = open(out_dir / "eval_log.csv", "a", newline="")
        self.tw = csv.writer(self.train_f)
        self.ew = csv.writer(self.eval_f)
        if self.train_f.tell() == 0:
            self.tw.writerow(["step", "episodes", "crashes", "crash_rate", "lam_freq", "lam_mean", "fallback_rate",
                              "passes", "mean_ep_return", "wall_time"])
        if self.eval_f.tell() == 0:
            self.ew.writerow(["step", "shielded_clean", "shielded_lap", "shielded_lam_freq", "unshielded_clean",
                              "unshielded_lap", "unshielded_progress"])
        self.t0 = time.time()
        self.window_steps = 0

    def _on_step(self) -> bool:
        for info, done in zip(self.locals["infos"], self.locals["dones"]):
            self.ep["lam"].append(info["lambda"])
            self.ep["fallback"] += info["fallback"]
            self.ep["passes"] += info["passes"]
            if done:
                self.ep["eps"] += 1
                self.ep["crash"] += int(info["wall"] or info["car"])
        self.window_steps += self.training_env.num_envs
        step = self.num_timesteps + self.offset
        if self.window_steps >= 20000:
            lam = np.array(self.ep["lam"])
            ep_rew = [e["r"] for e in self.model.ep_info_buffer] if self.model.ep_info_buffer else [np.nan]
            self.tw.writerow([step, self.ep["eps"], self.ep["crash"], self.ep["crash"] / max(self.ep["eps"], 1),
                              float(np.mean(lam > 0)), float(lam.mean()), self.ep["fallback"] / len(lam),
                              self.ep["passes"], float(np.mean(ep_rew)), round(time.time() - self.t0)])
            self.train_f.flush()
            self.ep = {"crash": 0, "eps": 0, "lam": [], "fallback": 0, "steps": 0, "passes": 0}
            self.window_steps = 0
        if self.num_timesteps >= self.next_eval:
            self.next_eval += self.eval_every
            vn = self.model.get_vec_normalize_env()
            sh = eval_lap(self.model, vn, self.cfg, "cond_fb_grip")
            un = eval_lap(self.model, vn, self.cfg, "off")
            self.ew.writerow([step, sh["clean"], sh["lap_time"], sh["lam_freq"], un["clean"], un["lap_time"],
                              un["progress"]])
            self.eval_f.flush()
            print(f"[{step}] eval shielded clean={sh['clean']} lap={sh['lap_time']} lam={sh['lam_freq']:.2f} | "
                  f"unshielded clean={un['clean']} lap={un['lap_time']} prog={un['progress']:.0f}", flush=True)
        return True


def _run_info(out: pathlib.Path, **kw):
    """Record provenance (git commit, dirty files, command) and status in run_info.json."""
    import subprocess, sys
    f = out / "run_info.json"
    info = json.load(open(f)) if f.exists() else {}
    if "git_commit" not in info:
        root = pathlib.Path(__file__).resolve().parents[1]
        git = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout.strip()
        info["git_commit"] = git("rev-parse", "--short", "HEAD")
        info["git_dirty"] = [l[3:] for l in git("status", "--porcelain").splitlines() if l[3:].startswith("racing/")]
        info["command"] = "python -m racing.train " + " ".join(sys.argv[1:])
    info.update(kw)
    json.dump(info, open(f, "w"), indent=1)


def train(args):
    torch.set_num_threads(1)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    json.dump(vars(args), open(out / "args.json", "w"), indent=1)
    _run_info(out, status="running", started=time.strftime("%Y-%m-%d %H:%M:%S"))
    model = None
    vec = None
    steps_done = 0
    budgets = dict(zip([1, 2, 3], args.steps))
    for stage in args.stages:
        cfg = make_cfg(stage, args.shield, args.seed, args.tire, not args.no_randomize, args.curvature_preview,
                       args.residual)
        if args.w3 is not None:
            import dataclasses
            cfg = dataclasses.replace(cfg, w3_shield=args.w3)
        if args.shield_prob:
            import dataclasses
            cfg = dataclasses.replace(cfg, shield_prob=dict(zip([1, 2, 3], args.shield_prob))[stage])
        venv = SubprocVecEnv([_env_fn(cfg, r) for r in range(args.n_envs)])
        venv = VecMonitor(venv)
        if vec is None:
            vec = VecNormalize(venv, norm_obs=False, norm_reward=True, gamma=args.gamma)
        else:
            old = vec
            vec = VecNormalize(venv, norm_obs=False, norm_reward=True, gamma=args.gamma)
            vec.ret_rms = old.ret_rms
            old.close()
        if model is None:
            model = PPO("MlpPolicy", vec, learning_rate=args.lr, n_steps=args.n_steps, batch_size=args.batch,
                        n_epochs=10, gamma=args.gamma, gae_lambda=0.95, clip_range=0.2, ent_coef=args.ent,
                        policy_kwargs=dict(net_arch=[256, 256], log_std_init=-0.5), seed=args.seed, verbose=0,
                        device="cpu", tensorboard_log=str(out / "tb"))
        else:
            model.set_env(vec)
        cb = TrainLogger(out, cfg, args.eval_every, stage_offset=steps_done)
        print(f"== stage {stage}: {budgets[stage]} steps, shield={args.shield}", flush=True)
        model.learn(total_timesteps=budgets[stage], callback=cb, reset_num_timesteps=True,
                    tb_log_name=f"stage{stage}")
        steps_done += budgets[stage]
        model.save(out / f"model_stage{stage}.zip")
        vec.save(str(out / f"vecnorm_stage{stage}.pkl"))
        cb.train_f.close(); cb.eval_f.close()
        _run_info(out, stages_done=args.stages[:args.stages.index(stage) + 1], steps_done=steps_done)
    vec.close()
    _run_info(out, status="finished", finished=time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shield", default="cond_fb_grip", choices=list(SHIELDS))
    ap.add_argument("--stages", type=int, nargs="+", default=[1])
    ap.add_argument("--steps", type=int, nargs="+", default=[1_000_000, 1_000_000, 1_000_000])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n_envs", type=int, default=8)
    ap.add_argument("--n_steps", type=int, default=512)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--gamma", type=float, default=0.99)
    ap.add_argument("--ent", type=float, default=0.0)
    ap.add_argument("--eval_every", type=int, default=50_000)
    ap.add_argument("--tire", default="saturated")
    ap.add_argument("--no_randomize", action="store_true")
    ap.add_argument("--curvature_preview", action="store_true")
    ap.add_argument("--residual", action="store_true")
    ap.add_argument("--w3", type=float, default=None, help="intervention penalty weight (default 0.1)")
    ap.add_argument("--shield_prob", type=float, nargs="*", default=None,
                    help="per-stage probability that the shield is on in an episode (shield dropout)")
    ap.add_argument("--out", required=True)
    train(ap.parse_args())
