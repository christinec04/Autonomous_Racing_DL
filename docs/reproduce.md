# Reproduce from scratch

Tested on Windows 11, Python 3.11, 16 cores. No GPU needed (PPO runs on CPU).

```bash
git clone -b gabe-build https://github.com/christinec04/Autonomous_Racing_DL
cd Autonomous_Racing_DL
python -m venv .venv && source .venv/Scripts/activate   # Linux/macOS: .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests                                # 18 tests
```

| step | command | time (16 cores) | output |
|---|---|---|---|
| track | `python -m racing.track_gen` | seconds | `maps/Singapore/` |
| classical controllers | `python -m scripts.probe_sim saturated tcs` | 1 min | stdout |
| shield stress test | `python -m scripts.shield_stress 8 saturated` (and `linear`) | about 10 min each | `results/shield_stress_*.json` |
| baselines in races | `python -m racing.evaluate --controllers pure_pursuit pid_apf --out results/eval_baselines.json` | about 30 min | json + stdout |
| train ours | `python -m racing.train --shield cond_fb_grip --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --seed 0 --out runs/ppo_shield_s0` | about 2 h | `runs/ppo_shield_s0/` |
| train ablation | same with `--shield off --out runs/ppo_noshield_s0` | about 1.5 h | |
| train residual | same with `--shield off --residual --out runs/ppo_residual_s0` | about 2 h | |
| race the policies | `python -m racing.evaluate --controllers ppo_apf ppo --models ppo_apf=runs/ppo_shield_s0/model_stage3.zip ppo=runs/ppo_noshield_s0/model_stage3.zip --out results/eval_ppo_s0.json` | about 40 min | json |
| tables + tests | `python -m scripts.analyze results/eval_baselines.json results/eval_ppo_s0.json` | seconds | `results/summary.md` |
| curves | `python -m scripts.plot_training` | seconds | `results/training_curves.png` |
| registry | `python -m scripts.update_registry` | seconds | `RUNS.md` |

Exact commands and git commits for every run are in `runs/<run>/run_info.json`. PPO is not bit-for-bit
deterministic across machines (parallel environments), so expect the same trends, not identical numbers.
