# APF-Shielded Deep RL for Autonomous Racing

A PPO agent races three PID / Pure Pursuit opponents on a Singapore-inspired street circuit in
[F1TENTH Gym](https://github.com/f1tenth/f1tenth_gym). An artificial-potential-field (APF) safety shield sits
between the policy and the car and steps in only when the policy's action is predicted to lead to a crash.

This branch (`gabe-build`) is the working implementation of the project proposal, built incrementally.
The grader's proposal feedback is addressed in code and experiments; see [docs/feedback.md](docs/feedback.md).

## Status at a glance

- Everything in the proposal runs end to end: track, opponents, classical baselines, shielded / unshielded PPO
  with the 3-stage curriculum, race-day evaluation with all six metrics, Mann-Whitney U tests.
- Seed-0 race results, all controllers on the same simulator version (nominal, 20 races x 5 laps; "finished" =
  all 5 laps), full tables and Mann-Whitney tests in [results/final_summary.md](results/final_summary.md):

  | controller | finished | stuck | clean lap | collisions / 10 laps | passes / race |
  |---|---|---|---|---|---|
  | **PPO + action-conditioned shield (ours, final)** | 16/20 | 0 | 34.5 s | 0.44 | **2.95** |
  | PPO + proposal's additive Eq. 2/3 shield | **18/20** | 0 | 47.6 s | **0.21** | 0.85 |
  | PID + APF | 12/20 | 0 | 42.8 s | 1.09 | 1.35 |
  | ResRace-style residual PPO | 10/20 | 0 | **30.4 s** | 1.60 | 2.20 |
  | PPO, no shield | 0/20 | 1 | 32.5 s | 7.35 | 1.35 |
  | Pure Pursuit | 0/20 | 0 | - | 61 | 0 |

  Ours meets all six metric targets; vs the additive shield it finishes as often (p = 0.39) while lapping 13 s
  faster with 3.5x the passes (p < 1e-5); vs no shield it finishes, survives and passes significantly more
  (p < 0.001). The residual policy is the fastest but crashes in half its races.
- **Correction:** earlier versions of this page counted a race as finished whenever there was no collision; many
  shielded races had actually ended *stuck* (the shield deadlocked). Finish counts above are corrected; the
  deadlock and its fix are documented in [docs/experiments.md](docs/experiments.md) (E19) and
  [PROGRESS.md](PROGRESS.md) (problems 22-24).
- **Across seeds the picture is weaker than seed 0 alone** ([results/seed_summary.md](results/seed_summary.md),
  2 seeds so far): final shield 8.5 +- 7.5 races finished, 2.67 +- 2.23 collisions / 10 laps; original shield
  6.5 +- 5.5 finished (10 stuck on average), 0.85 collisions; no shield 2.0 +- 1.0 finished, 4.43 collisions.
  Seed 1 learned a sliding driving style that the shield cannot reliably catch (E20). The shield consistently
  lowers collisions versus no shield; how many races get finished depends strongly on the seed.
  Seeds 1-2, PPO with the proposal's additive shield, shield dropout, an improved-shield training run and two
  timidity fixes are in progress; live status in [RUNS.md](RUNS.md).
- Running log of every step and every problem hit along the way: [PROGRESS.md](PROGRESS.md).

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash); use .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
python -m racing.track_gen        # builds maps/Singapore (already committed)
python -m pytest -q tests         # 23 tests, ~20 s

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

- [docs/results.md](docs/results.md): current results, what works and what does not (living page)
- [docs/architecture.md](docs/architecture.md): how the pieces fit, with every parameter value
- [docs/feedback.md](docs/feedback.md): each proposal comment -> what changed -> evidence
- [docs/design-decisions.md](docs/design-decisions.md): deviations from the proposal and why
- [docs/experiments.md](docs/experiments.md): every experiment, its command, output and result
- [docs/reproduce.md](docs/reproduce.md): rebuild every number from scratch
- [docs/developer-guide.md](docs/developer-guide.md): conventions, how to add controllers / shields / tracks, pitfalls
- [docs/risks.md](docs/risks.md): risk register built from the problems actually hit
- [PROGRESS.md](PROGRESS.md): chronological build log and problems encountered
- [RUNS.md](RUNS.md): run registry (auto-generated)
