# APF-Shielded Deep RL for Autonomous Racing

A PPO agent races three PID / Pure Pursuit opponents on a Singapore-inspired street circuit in
[F1TENTH Gym](https://github.com/f1tenth/f1tenth_gym). An artificial-potential-field (APF) safety shield sits
between the policy and the car and steps in only when the policy's action is predicted to lead to a crash.

This branch (`gabe-build`) is the working implementation of the project proposal, built incrementally.
The grader's proposal feedback is addressed in code and experiments; see [docs/feedback.md](docs/feedback.md).

## Status at a glance

- Everything in the proposal runs end to end: track, opponents, classical baselines, shielded / unshielded PPO
  with the 3-stage curriculum, race-day evaluation with all six metrics, Mann-Whitney U tests.
- Seed-0 race results (nominal, 20 races x 5 laps), full tables in [results/summary.md](results/summary.md):

  | controller | finished | clean lap | collisions / 10 laps | passes / race |
  |---|---|---|---|---|
  | **PPO + shield (ours)** | **17/20** | **34.3 s** | **0.38** | **2.65** |
  | PPO, no shield | 2/20 | 36.8 s | 5.53 | 1.05 |
  | PID + APF | 9/20 | 43.9 s | 1.75 | 1.25 |
  | Pure Pursuit | 0/20 | - | 61 | 0 |

- More seeds, a ResRace-style residual comparison, PPO with the proposal's original additive shield, and a
  shield-dropout experiment are in progress; live status in [RUNS.md](RUNS.md).
- Running log of every step and every problem hit along the way: [PROGRESS.md](PROGRESS.md).

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash); use .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
python -m racing.track_gen        # builds maps/Singapore (already committed)
python -m pytest -q tests         # 18 tests, ~20 s

# classical baselines in races
python -m racing.evaluate --controllers pure_pursuit pid_apf --races 20 --out results/eval_baselines.json

# train PPO + shield (3 stages, ~2 h on 7 cores)
python -m racing.train --shield cond_fb_grip --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --out runs/my_run

# race it, then render a replay
python -m racing.evaluate --controllers ppo_apf --models ppo_apf=runs/my_run/model_stage3.zip --out results/eval_mine.json
python -m racing.render --controller ppo_apf --model runs/my_run/model_stage3.zip --seconds 20 --out replay.mp4
```

Full from-scratch reproduction: [docs/reproduce.md](docs/reproduce.md).

## Repository layout

| path | what |
|---|---|
| `racing/track_gen.py` | Singapore-inspired circuit (199 m, 2.8 m wide, 19 corners) -> occupancy grid + centerline |
| `racing/sim.py` | F1TENTH Gym wrapper, local maps, centerline/Frenet utilities, simulator speed patches |
| `racing/tires.py` | friction-circle tyre model and traction control (closes the linear-tyre loophole) |
| `racing/controllers.py` | Pure Pursuit, PID path follower, grip-limited speed profile |
| `racing/env.py` | Gymnasium race environment: ego + 3 opponents, observation, action, reward, shield hook |
| `racing/shield.py` | APF field and the shield variants (additive Eq. 2/3, action-conditioned, fallback) |
| `racing/predict.py` | exact-model rollouts (numba) used by the action-conditioned shield |
| `racing/train.py` | PPO training with the curriculum, fair training-efficiency evaluation, provenance |
| `racing/evaluate.py` | race-day protocol, six metrics, overtake detector, metric targets |
| `racing/render.py` | top-down replay videos |
| `scripts/` | experiments (stress test, tuning, calibration, analysis, plots, registry, queues) |
| `tests/` | unit tests incl. "predictor matches simulator" |
| `runs/` | every training run: config, provenance, logs, checkpoints (index: `RUNS.md`) |
| `results/` | evaluation outputs, summary tables, plots |
| `docs/` | architecture, feedback response, design decisions, experiments, reproduction |

## Documentation

- [docs/architecture.md](docs/architecture.md): how the pieces fit, with every parameter value
- [docs/feedback.md](docs/feedback.md): each proposal comment -> what changed -> evidence
- [docs/design-decisions.md](docs/design-decisions.md): deviations from the proposal and why
- [docs/experiments.md](docs/experiments.md): every experiment, its command, output and result
- [docs/reproduce.md](docs/reproduce.md): rebuild every number from scratch
- [docs/developer-guide.md](docs/developer-guide.md): conventions, how to add controllers / shields / tracks, pitfalls
- [PROGRESS.md](PROGRESS.md): chronological build log and problems encountered
- [RUNS.md](RUNS.md): run registry (auto-generated)
