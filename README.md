# APF-Shielded Deep RL for Autonomous Racing

A PPO agent races three PID / Pure Pursuit opponents on a Singapore-inspired street circuit in
[F1TENTH Gym](https://github.com/f1tenth/f1tenth_gym). An artificial-potential-field (APF) safety shield sits
between the policy and the car and steps in only when the policy's action is predicted to lead to a crash.

This branch (`gabe-build`) is the working implementation of the project proposal, built incrementally.
The grader's proposal feedback is addressed in code and experiments; see [docs/feedback.md](docs/feedback.md).

## Status at a glance

Final controller ("ours"): PPO trained with the action-conditioned shield, raced with the shield, its deadlock
escape and the stall recovery, on the post-spin-fixed ("v2") simulator. Seed 0, all controllers on the same
simulator, nominal conditions. "Finished" = all 5 laps. Sources: [results/final_summary.md](results/final_summary.md)
(20 races, all metrics, Mann-Whitney tests) and [results/headtohead50.md](results/headtohead50.md) (50 races).

| controller | finished, 20 races | finished, 50 races (nominal / randomised) | clean lap | collisions / 10 laps | passes / race |
|---|---|---|---|---|---|
| **PPO + action-conditioned shield + stall recovery (ours, final)** | **19/20** | **43/50** / 35/50 | 34.7 s | **0.10** | 3.15 |
| same, without the stall recovery | 16/20 | - | 34.5 s | 0.44 | 2.95 |
| PPO + proposal's additive Eq. 2/3 shield | 18/20 | 39/50 / 34/50 | 47.6 s | 0.21 | 0.85 |
| PID + APF | 12/20 | 28/50 / 25/50 | 42.8 s | 1.09 | 1.35 |
| ResRace-style residual PPO trained with our shield (E23) | 15/20 | 39/50 / **37/50** | 32.1 s | 0.59 | 3.15 |
| ResRace-style residual PPO | 10/20 | - | **30.4 s** | 1.60 | 2.20 |
| PPO, no shield | 0/20 (1 stuck) | - | 32.5 s | 7.35 | 1.35 |
| Pure Pursuit | 0/20 | - | - | 61 | 0 |

- Ours meets all six metric targets, nominal and randomised, on the 20-race seed-0 protocol. Over 50 races the
  randomised collision rate is 0.77 / 10 laps, which misses the <= 0.5 target (nominal: 0.31).
- On 50 races ours and the additive shield finish about equally often (p = 0.44 nominal), but ours laps 12 s
  faster with 2.7x the passes (p = 1e-8, nominal). Ours finishes more than PID+APF (p = 0.002 nominal). The residual policy
  trained with our shield ties ours on finishing and laps 2.5 s faster. The 20-race counts are on the optimistic side.
- The stall recovery (E21) reverses the car out when the policy stops nose-to-wall. It fires in 3 of 20 seed-0
  races and cut chicane failures from 46 to 17 (3 seeds, nominal + randomised).
- **Across 3 training seeds the result is weaker** ([results/seed_summary.md](results/seed_summary.md), nominal):
  13.0 +- 8.5 races finished with the final setup vs 3.0 +- 2.4 without a shield; collisions 1.63 +- 2.16 vs
  4.38 +- 2.12 per 10 laps. Seeds 0 and 2 finish 19/20, seed 1 only 1/20: it learned to slide (E20, E24).
  Seed 1 retrained with a slip penalty (`--w6 1`) and the escape shield from the start (`ppo_shield_v2esc_slip_s1`,
  raced without the stall recovery) finishes 17/20 nominal and 13/20 randomised, 0.22 collisions / 10 laps, 32.5 s
  laps. But seed 0 with the same recipe finishes only 11/20 (E26), so the penalty is not a general fix. Residual
  PPO trained with our shield is the most consistent recipe so far: 15 and 16 of 20 on seeds 0 and 1 (E23).
- What did not work: fine-tuning on the chicane (E22, E22b), a lower intervention penalty (E18), stricter shield
  settings (E24: help seed 1, cost seed 0). Shield dropout (E10) gives a policy that is safe without the shield but
  timid. Full list: [docs/results.md](docs/results.md).
- **Correction:** early versions of these docs counted a race as finished whenever there was no collision; many
  shielded races had actually ended *stuck* (shield deadlock). All counts here are corrected (E19, PROGRESS.md
  problems 22-24).
- Still running: seed 2 of the residual + shield recipe (E23) and of the slip-penalty recipe (E26). Live status: [RUNS.md](RUNS.md).
- Mid-term report draft: [report/midterm.tex](report/midterm.tex) (build: [docs/reproduce.md](docs/reproduce.md)).
- Build log with every step and the 33 problems hit along the way: [PROGRESS.md](PROGRESS.md).

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash); use .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
python -m racing.track_gen        # builds maps/Singapore (already committed)
python -m pytest -q tests         # 25 tests

# classical baselines in races
python -m racing.evaluate --controllers pure_pursuit pid_apf --races 20 --out results/eval_baselines.json

# train PPO + shield (3 stages, ~2 h on 7 cores)
python -m racing.train --shield cond_fb_grip --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --out runs/my_run

# race it with the final setup (escape shield + stall recovery, v2 simulator), then render a replay
python -m racing.evaluate --controllers ppo_apf_rec --models ppo_apf_rec=runs/my_run/model_stage3.zip --tire saturated_v2 --out results/eval_mine.json
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
