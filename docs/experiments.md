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

## E12. How do the controllers use the tyres? (g-g)
`python -m scripts.plot_gg results/eval_baselines.json results/eval_ppo_s0.json` -> `results/gg_diagrams.png`.
All PPO variants drive bang-bang longitudinally (dense bands at the traction-control limit, about 0.92 mu g, for
both throttle and braking) but mostly stay below 0.5 mu g laterally: they gain time on straights and braking zones,
not by cornering at the limit. PID+APF barely uses the grip (1% of time above 90%).

## E13. Where does the shield intervene?
`python -m scripts.plot_shield_map` -> `results/shield_map.png`. 3.2% of steps over 4 races; clustered at the
chicane after the main straight, the hairpin, and on the main straight in traffic.

## E14. Shield settings with the trained agent (10 nominal races each)
`python -m scripts.shield_sensitivity 10` -> `results/shield_sensitivity.md` / `.json`. Same shield-trained policy
(seed 0), only the shield changes at race time.

| shield setting | finished | clean lap | collisions / 10 laps | passes / race | shield active |
|---|---|---|---|---|---|
| default (grip reach, c_safe 0.05, opp_brake 6) | 8/10 | 33.7 | 0.57 | 2.5 | 7% |
| fixed reach 6 m/s^2 | 10/10 | 33.4 | 0.00 | 1.7 | 13% |
| c_safe 0.02 | 8/10 | 34.2 | 0.51 | 2.4 | 6% |
| c_safe 0.10 | 10/10 | 34.4 | 0.00 | 2.8 | 8% |
| opp_brake 3 | 9/10 | 33.5 | 0.38 | 1.5 | 11% |
| opp_brake 9 | 9/10 | 33.8 | 0.36 | 1.9 | 10% |
| no fallback | 8/10 | 34.1 | 0.85 | 1.4 | 11% |
| additive Eq. 2/3 | 3/10 | 34.9 | 3.15 | 1.5 | 74% |

Reading: a 10 cm prediction margin looks strictly better than 5 cm (no collisions, as many passes); fixed reach is
also collision-free but more timid (fewer passes, shield on more). The fallback matters; the proposal's additive
form fails with a learned driver too. 10 races is a small sample: confirmation run E15.

## Videos
`python -m scripts.make_videos batch1|batch2|batch3` picks the seed with no crash and the most passes in 20 s and
renders to `~/Downloads/racing_videos/` (not committed). Blue = ego, red = shield intervening, grey = opponents.
