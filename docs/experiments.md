# Experiments

Each experiment: question, command, output, result. Status of training runs: [RUNS.md](../RUNS.md).

## E1. Can classical controllers lap the track? (step 1)
`python -m scripts.probe_sim <saturated|linear> <tcs|notcs>`, `python -m scripts.check_pid25`.
Pure Pursuit laps cleanly up to 0.85x the grip-limited profile with real tyres (35.2 s), and up to 1.1x on stock
tyres (27.9 s). PID needed a redesign for 25 Hz (E5).

## E2. How fast is the simulator?
`python -m scripts.prof_env`. Stock: about 35 control steps/s with 4 cars. Patched: about 400 without the shield,
100-500 with it, depending on how often it intervenes.

## E3. Does the shield's model match the simulator?
`python -m scripts.calib_pred <tyre>`: the kinematic-bicycle prediction was metres off. Replaced with the
exact-model predictor; `tests/test_predictor.py` checks clearance agreement to < 2 cm in 8 cases.

## E4. Shield stress test (no learning)
`python -m scripts.shield_stress 8 <saturated|linear>` -> `results/shield_stress_<tyre>.json`.
Additive Eq. 2/3 crashes in almost every case; the action-conditioned fallback shield brings solo and random-action
crashes to 0-12%; car contacts in traffic remain (12-38%). Table in [feedback.md](feedback.md).

## E5. Baseline tuning
`python -m scripts.tune_pid` (PID gains at 25 Hz, 54 settings: 5 stable, best 35.3 s laps) and
`python -m scripts.tune_apf` (APF gains on top of PID, 36 settings) -> `results/tune_apf.json`.

## E6. Race-day baselines
`python -m racing.evaluate --controllers pure_pursuit pid_apf --races 20 --laps 5` -> `results/eval_baselines.json`.

## E7. PPO with vs without the shield (seed 0)
Training: `runs/ppo_shield_s0`, `runs/ppo_noshield_s0`; curves in `results/training_curves.png`.
Racing: `results/eval_ppo_s0.json`, merged in `results/summary.md`. Also the cross-combinations: the
shield-trained policy raced without the shield, and the unshielded policy raced with the shield added.

## E8. ResRace-style residual policy
`runs/ppo_residual_s0`: PPO residual (scale 0.3) on top of the tuned PID+APF controller. Tests the contribution
statement: shield only when needed vs APF shaping every command.

## E9. PPO with the proposal's original additive shield
`runs/ppo_additive_s0`.

## E10. Shield dropout
`runs/ppo_shielddrop_s0`: shield on in 100% / 50% / 25% of episodes in stages 1 / 2 / 3. Question: can the policy
keep the shield's training safety but end up safe without it?

## E11. Seeds 1-2
`runs/ppo_shield_s{1,2}`, `runs/ppo_noshield_s{1,2}`, for mean and spread across seeds as in the proposal.

## Videos
`python -m scripts.make_videos batch1|batch2|batch3` picks the seed with no crash and the most passes in 20 s and
renders to `~/Downloads/racing_videos/` (not committed). Blue = ego, red = shield intervening, grey = opponents.
