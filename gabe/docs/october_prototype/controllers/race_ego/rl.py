"""PPO training, evaluation and the scripted stub, shared by the Webots controller and the offline sim.

Every mode takes key=value args.
  mode=train run=NAME shield=friction minutes=40 steps=2000000 opp_after=300000 init=PATH
  mode=eval  run=NAME shield=friction episodes=10 opponents=3 ckpt=PATH tag=NAME
  mode=stub  seconds=120 pace=0.9
Training resumes from runs/rl/NAME/model.zip when it exists and stops after `minutes`
of wall time so the Webots lock can be shared between agents.
"""
import csv
import json
import math
import os
import time

import numpy as np

EP_FIELDS = ["episode", "step", "wall_s", "chunk", "return", "steps", "progress", "laps", "crash", "interventions",
             "int_rate", "int_mag", "overtakes", "opponents"]
BIN_FIELDS = ["step", "wall_s", "sim_s", "chunk", "steps_per_s", "env_steps_per_s", "crashes", "stuck", "int_rate",
              "int_mag", "speed", "episodes", "progress", "opponents"]
BIN = 1000


def _append(path, fields, row):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


class Timed:
    """Measures time spent inside env.step so env throughput can be told apart from PPO update time."""

    def __init__(self, env):
        self.env = env
        self.busy = 0.0

    def step(self, a):
        t = time.perf_counter()
        out = self.env.step(a)
        self.busy += time.perf_counter() - t
        return out


def _ppo_kwargs(seed):
    return dict(n_steps=2048, batch_size=128, n_epochs=10, learning_rate=3e-4, gamma=0.99, gae_lambda=0.95,
                clip_range=0.2, ent_coef=0.0, max_grad_norm=0.5, seed=seed, device="cpu", verbose=0,
                policy_kwargs=dict(net_arch=[256, 256], log_std_init=-0.5))


def train(args, env, run_dir):
    import gymnasium as gym
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv

    torch.set_num_threads(int(args.get("threads", 4)))
    minutes = float(args.get("minutes", 40))
    total = int(float(args.get("steps", 2e6)))
    opp_after = int(float(args.get("opp_after", 3e5)))
    n_opp = int(args.get("opponents", 3))
    dt = float(args.get("dt_ctrl", 0.032))
    state_path = os.path.join(run_dir, "state.json")
    model_path = os.path.join(run_dir, "model.zip")
    state = {"steps": 0, "episodes": 0, "chunk": 0, "wall_s": 0.0, "args": args}
    if os.path.exists(state_path):
        with open(state_path) as fh:
            state.update(json.load(fh))
    state["chunk"] += 1
    chunk = state["chunk"]
    if state["steps"] >= total:
        print(f"[rl] {run_dir} already has {state['steps']} steps, nothing to do")
        return state

    timer = Timed(env)

    class Wrap(gym.Wrapper):
        def step(self, a):
            return timer.step(a)

    wrapped = Monitor(Wrap(env), os.path.join(run_dir, f"chunk{chunk:02d}"), info_keywords=("progress", "crash"))
    venv = DummyVecEnv([lambda: wrapped])
    if os.path.exists(model_path):
        model = PPO.load(model_path, env=venv, device="cpu")
        print(f"[rl] resumed {model_path} at step {state['steps']}")
    else:
        model = PPO("MlpPolicy", venv, **_ppo_kwargs(int(args.get("seed", 0))))
        if args.get("init"):
            model.set_parameters(args["init"], exact_match=True, device="cpu")
            print(f"[rl] initialised from {args['init']}")
    env.set_opponents(n_opp if state["steps"] >= opp_after else 0)

    class Log(BaseCallback):
        def _on_training_start(self):
            self.t0 = self.t_bin = time.time()
            self.busy0 = timer.busy
            self.wall0 = state["wall_s"]
            self.acc = dict(crashes=0, stuck=0, interventions=0, int_mag=0.0, speed=0.0, episodes=0, progress=0.0)

        def _on_step(self):
            info = self.locals["infos"][0]
            state["steps"] += 1
            a = self.acc
            a["crashes"] += int(bool(info["crash"]))
            a["interventions"] += int(info["intervened"])
            a["int_mag"] += info["int_mag"]
            a["speed"] += info["speed"]
            stats = info.get("episode_stats")
            now = time.time()
            state["wall_s"] = self.wall0 + now - self.t0
            if stats:
                state["episodes"] += 1
                a["episodes"] += 1
                a["progress"] += stats["progress"]
                a["stuck"] += int(stats["crash"] == "stuck")
                _append(os.path.join(run_dir, "episodes.csv"), EP_FIELDS,
                        {**stats, "episode": state["episodes"], "step": state["steps"], "wall_s": round(state["wall_s"], 1),
                         "chunk": chunk, "opponents": env.n_opp, "return": round(stats["return"], 3),
                         "progress": round(stats["progress"], 1), "laps": round(stats["laps"], 4),
                         "int_rate": round(stats["int_rate"], 4), "int_mag": round(stats["int_mag"], 2)})
                if state["steps"] >= opp_after and env.n_opp != n_opp:
                    env.set_opponents(n_opp)
                    print(f"[rl] curriculum adds {n_opp} opponents at step {state['steps']}")
            if state["steps"] % BIN == 0:
                span = max(now - self.t_bin, 1e-6)
                busy = max(timer.busy - self.busy0, 1e-6)
                _append(os.path.join(run_dir, "train_log.csv"), BIN_FIELDS, {
                    "step": state["steps"], "wall_s": round(state["wall_s"], 1), "sim_s": round(state["steps"] * dt, 1),
                    "chunk": chunk, "steps_per_s": round(BIN / span, 1), "env_steps_per_s": round(BIN / busy, 1),
                    "crashes": a["crashes"], "stuck": a["stuck"], "int_rate": a["interventions"] / BIN,
                    "int_mag": round(a["int_mag"] / BIN, 4), "speed": round(a["speed"] / BIN, 2),
                    "episodes": a["episodes"], "progress": round(a["progress"] / max(a["episodes"], 1), 1),
                    "opponents": env.n_opp})
                if state["steps"] % (10 * BIN) == 0:
                    print(f"[rl] step {state['steps']} {BIN / span:.0f} steps/s crashes/1k {a['crashes']} "
                          f"progress {a['progress'] / max(a['episodes'], 1):.0f} m int {a['interventions'] / BIN:.3f}")
                self.t_bin, self.busy0 = now, timer.busy
                self.acc = dict(crashes=0, stuck=0, interventions=0, int_mag=0.0, speed=0.0, episodes=0, progress=0.0)
            if state["steps"] % 10000 == 0:
                # frequent saves so a guard kill loses at most 10k steps
                save()
            if state["steps"] % 50000 == 0:
                self.model.save(os.path.join(run_dir, f"ckpt_{state['steps']}.zip"))
            return now - self.t0 < minutes * 60 and state["steps"] < total

    def save():
        model.save(model_path)
        with open(state_path, "w") as fh:
            json.dump(state, fh, indent=2)

    t0 = time.time()
    model.learn(total_timesteps=total, callback=Log(), reset_num_timesteps=False, progress_bar=False)
    save()
    print(f"[rl] chunk {chunk} done, {state['steps']} steps total, {time.time() - t0:.0f} s this chunk")
    return state


def evaluate(args, env, run_dir):
    from stable_baselines3 import PPO

    ckpt = args.get("ckpt") or os.path.join(run_dir, "model.zip")
    model = PPO.load(ckpt, device="cpu")
    tag = args.get("tag", "eval_" + env.shield_kind)
    episodes = int(args.get("episodes", 10))
    env.set_opponents(int(args.get("opponents", 3)))
    env.start_speed = (0.5, 0.5)
    dt = float(args.get("dt_ctrl", 0.032))
    tele, laps = [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=1000 + ep)
        lap_time, done, info = None, False, {}
        while not done:
            a, _ = model.predict(obs, deterministic=True)
            obs, _, term, trunc, info = env.step(a)
            done = term or trunc
            if lap_time is None and info["laps"] >= 1.0:
                lap_time = env.steps * dt
                done = True
            tele.append({"ep": ep, "step": env.steps, "t": round(env.steps * dt, 3), "s": round(info["s"], 1),
                         "lat": round(info["lat"], 2), "speed": round(info["speed"], 2), "steer": round(float(a[0]), 3),
                         "accel": round(float(a[1]), 3), "intervened": int(info["intervened"]),
                         "int_mag": round(info["int_mag"], 3), "grip_used": round(info["grip_used"], 3),
                         "reason": info["reason"], "crash": info["crash"]})
        st = info.get("episode_stats") or {**env.ep, "steps": env.steps, "progress": env.progress,
                                             "int_rate": env.ep["interventions"] / env.steps}
        laps.append({"ep": ep, "completed": int(lap_time is not None), "lap_time": lap_time and round(lap_time, 2),
                     "crash": st["crash"] if lap_time is None else "", "steps": env.steps,
                     "progress": round(env.progress, 1), "int_rate": round(st["interventions"] / env.steps, 4),
                     "overtakes": st["overtakes"]})
        print(f"[rl] eval ep {ep} {laps[-1]}")
    for name, rows in ((f"{tag}_telemetry.csv", tele), (f"{tag}_laps.csv", laps)):
        with open(os.path.join(run_dir, name), "w", newline="") as fh:
            w = csv.DictWriter(fh, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    done = [r["lap_time"] for r in laps if r["completed"]]
    km = sum(r["progress"] for r in laps) / 1000
    crashes = sum(1 for r in laps if r["crash"] and r["crash"] != "stuck")
    summary = {"ckpt": ckpt, "shield": env.shield_kind, "episodes": episodes, "opponents": env.n_opp,
               "laps_completed": len(done), "lap_time_mean": float(np.mean(done)) if done else None,
               "lap_time_best": float(np.min(done)) if done else None, "crashes": crashes,
               "crashes_per_km": crashes / max(km, 1e-6), "km": km,
               "car_collisions": sum(1 for r in laps if r["crash"] == "car"),
               "int_rate": float(np.mean([r["intervened"] for r in tele])),
               "overtakes_net": int(sum(r["overtakes"] for r in laps)),
               "mean_speed": float(np.mean([r["speed"] for r in tele]))}
    with open(os.path.join(run_dir, f"{tag}_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print("[rl] eval summary", json.dumps(summary))
    return summary


def pursuit(track, state, pace):
    """Pure pursuit on the racing line plus the speed profile, the fallback when pilot.py is missing."""
    i = state["i"]
    j = track.ahead(i, max(8.0, 0.5 * state["speed"]))
    dx, dy = track.line[j, 0] - state["x"], track.line[j, 1] - state["y"]
    alpha = (math.atan2(dy, dx) - state["yaw"] + math.pi) % (2 * math.pi) - math.pi
    steer = math.atan(6.0 * math.sin(alpha) / max(math.hypot(dx, dy), 1.0)) / 0.45
    vt = pace * min(track.v[track.ahead(i, d)] for d in range(0, 60, 4))
    acc = max(-1.0, min(1.0, 0.5 * (vt - state["speed"])))
    return steer, max(acc, 0.0), max(-acc, 0.0)


def stub(args, env, run_dir):
    """Drive the scripted pilot through the env so the world, shield and logging can be smoke tested."""
    pace = float(args.get("pace", 0.9))
    dt = float(args.get("dt_ctrl", 0.032))
    try:
        from pilot import Pilot
        pilot = Pilot(env.track, pace, float(args.get("aggression", 1.0)))
        drive = lambda st: pilot.act(st, env.opps, dt)  # noqa: E731
    except ImportError:
        drive = lambda st: pursuit(env.track, st, pace)  # noqa: E731
    env.set_opponents(int(args.get("opponents", 3)))
    seconds = float(args.get("seconds", 120))
    obs, _ = env.reset(seed=int(args.get("seed", 0)))
    rows, n, wall0, sim0 = [], 0, time.time(), env.b.time()
    while env.b.time() - sim0 < seconds:
        steer, thr, brk = drive(env.state)
        obs, r, term, trunc, info = env.step([steer, thr - brk])
        n += 1
        rows.append({"t": round(env.b.time(), 3), "s": round(info["s"], 1), "lat": round(info["lat"], 2),
                     "speed": round(info["speed"], 2), "crash": info["crash"], "intervened": int(info["intervened"]),
                     "lidar_left": round(float(obs[-9]), 3), "lidar_right": round(float(obs[-32]), 3)})
        if term or trunc:
            print(f"[rl] stub episode end {info['episode_stats']}")
            obs, _ = env.reset()
    wall = time.time() - wall0
    with open(os.path.join(run_dir, "stub.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {"env_steps": n, "wall_s": wall, "env_steps_per_s": n / wall, "rtf": (env.b.time() - sim0) / wall}
    with open(os.path.join(run_dir, "stub_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print("[rl] stub", json.dumps(summary))
    return summary


def run(args, env, run_dir):
    os.makedirs(run_dir, exist_ok=True)
    mode = args.get("mode", "stub")
    return {"train": train, "eval": evaluate, "stub": stub}[mode](args, env, run_dir)
