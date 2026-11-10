# Reproduce from scratch

Tested on Windows 11, Python 3.11, 16 cores. No GPU needed (PPO runs on CPU). Memory: each training run uses about
2.5 GB; run at most 2-3 trainings at once.

```bash
git clone -b gabe-build https://github.com/christinec04/Autonomous_Racing_DL
cd Autonomous_Racing_DL
python -m venv .venv && source .venv/Scripts/activate   # Linux/macOS: .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests                                # 25 tests
```

## 1. Track, simulator checks, shield stress test

| step | command | time (16 cores) | output |
|---|---|---|---|
| track | `python -m racing.track_gen` | seconds | `maps/Singapore/` |
| classical controllers | `python -m scripts.probe_sim saturated tcs` | 1 min | stdout |
| shield stress test | `python -m scripts.shield_stress 8 saturated` (and `linear`) | about 10 min each | `results/shield_stress_*.json` |

## 2. Training

All runs: `python -m racing.train --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --seed <s> --out runs/<run>`
plus the flags below. About 2 h each (1.3-2.6 h for 3.5M steps). The exact command of every run is in `runs/<run>/run_info.json` and
[RUNS.md](../RUNS.md).

| run | extra flags | seeds | used for |
|---|---|---|---|
| `ppo_shield_s<s>` | `--shield cond_fb_grip` | 0, 1, 2 | ours (final) and the 3-seed summary |
| `ppo_noshield_s<s>` | `--shield off` | 0, 1, 2 | no-shield ablation |
| `ppo_additive_s0` | `--shield additive` | 0 | proposal's additive Eq. 2/3 shield |
| `ppo_residual_s0` | `--shield off --residual` | 0 | ResRace-style residual policy |
| `ppo_residual_shield_s0` | `--residual --shield cond_fb_grip_esc --tire saturated_v2` | 0 | residual policy trained with our shield (E23) |

## 3. Race-day evaluation (all on the v2 simulator)

Every evaluation is `python -m racing.evaluate ... --races 20 --laps 5 --tire saturated_v2 --out <file>`; 20 races
nominal and 20 randomised per controller, about 40 min per controller on 16 cores. Lower `--procs` if memory is tight.

| output | controllers (`--controllers`, models via `--models label=runs/<run>/model_stage3.zip`) |
|---|---|
| `results/final_v2_others.json` | `bash scripts/final_eval_v2.sh` (Pure Pursuit, PID+APF, no shield s0/s1, residual, additive) |
| `results/final_v2_noshield_s2.json` | `bash scripts/queue_eval_noshield_s2_v2.sh` (no shield, seed 2) |
| `results/eval_escape_v4.json`, `_s1`, `_s2` | `ppo_apf_esc@s<s>` = `ppo_shield_s<s>` (escape shield, no stall recovery); `scripts/queue_eval_s2_final.sh` for seed 2 |
| `results/eval_recover.json` | `ppo_apf_rec@s0`, `ppo_apf_rec@s1`, `ppo_apf_rec@s2` = `ppo_shield_s0/1/2` (plain PPO + our shield) |
| `results/eval_residual_shield_s1.json`, `_s2` | final controller seeds 1-2 (`scripts/queue_lane_h.sh`) |
| `results/eval_extra30_residual_s12.json` | final controller seeds 1-2 with `--first 20 --races 30` |
| `results/eval_track2_residual_s12.json`, `eval_track2_ours_s12.json` | Track2 (`--map Track2`), seeds 1-2 of the final controller and of plain PPO + shield |
| `results/eval_residual_norec_s12.json` | final controller seeds 1-2 without the stall recovery (`ppo_residual_apf_esc`) |
| `results/eval_residual_shield_s0.json` | `ppo_residual_apf_rec@trained` etc. = `ppo_residual_shield_s0` (exact command in `scripts/queue_lane_g.sh`) |
| `results/eval_extra30.json` | `ppo_apf_rec@s0 ppo_additive pid_apf` with `--first 20 --races 30` (race seeds 10020-10049) |
| `results/eval_extra30_residual.json` | `ppo_residual_apf_rec@trained` with `--first 20 --races 30` |

## 4. Tables and figures

| step | command | output |
|---|---|---|
| final 20-race tables, targets, Mann-Whitney | `bash scripts/final_tables.sh` | `results/final_summary.md` |
| 50-race head-to-head | `python -m scripts.headtohead` | `results/headtohead50.md` |
| across seeds | `python -m scripts.seed_summary` | `results/seed_summary.md` |
| training efficiency | `python -m scripts.training_efficiency` | `results/training_efficiency.md` |
| training curves | `python -m scripts.plot_training` | `results/training_curves.png` |
| failure map, trade-off | `python -m scripts.plot_failures`, `python -m scripts.plot_tradeoff` | `results/failure_map.png`, `results/tradeoff.png` |
| report figures | `python -m scripts.report_figs` | `report/figs/*.pdf` |
| registry | `python -m scripts.update_registry` | `RUNS.md` |

## 5. Mid-term report

The report draft is `report/midterm.tex` (IEEE format). It is built with [Tectonic](https://tectonic-typesetting.github.io/),
which is not in the repo: on the build machine it is `C:\Users\shore\gabe\tools\tectonic.exe`, one level above the repo.
From the repo root:

```bash
python -m scripts.report_figs                      # report/figs/*.pdf
../tools/tectonic.exe -X compile report/midterm.tex   # report/midterm.pdf
```

Any other Tectonic or LaTeX install works the same way.

PPO is not bit-for-bit deterministic across machines (parallel environments), so expect the same trends, not
identical numbers. Evaluation is deterministic for a given model and race seed.
