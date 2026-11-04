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
statement: shield only when needed vs APF shaping every command. Raced alone (`results/eval_residual_s0.json`) and
with our shield added at race time (`results/eval_residual_apf_s0.json`).
Result: fastest clean laps of any controller (30.4 s) but only 9/20 finishes; with our shield on top 18/20 finishes,
32.7 s laps, 0.36 collisions / 10 laps, 43/43 overtakes. The shield and the residual structure are complementary.

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

## E15. Confirmation of E14 on the full protocol (20 races, nominal + randomised)
`python -m scripts.shield_confirm`, then `python -m scripts.analyze results/shield_confirm.json --out results/shield_confirm_summary.md`.

| shield setting | finished (nom / rand) | collisions / 10 laps (nom / rand) | passes / race (nom / rand) | shield active |
|---|---|---|---|---|
| default: grip reach, c_safe 0.05 | 17 / 16 | 0.38 / 0.63 | 2.65 / 2.50 | 6% / 10% |
| grip reach, c_safe 0.10 | 18 / 18 | 0.30 / 0.33 | 2.35 / 2.35 | 8% / 10% |
| fixed reach 6 m/s^2, c_safe 0.05 | 20 / 18 | 0.00 / 0.29 | 2.00 / 2.30 | 10% / 9% |
| fixed reach, c_safe 0.10 | 19 / 20 | 0.16 / 0.00 | 2.05 / 1.90 | 12% / 13% |

A safety-vs-aggressiveness dial: the more conservative settings remove most collisions but cost overtakes and use
the shield more (missing the <= 10% target). Only "fixed, c_safe 0.10" vs default under randomisation is significant
for collisions (Mann-Whitney p = 0.04); 20 races are not enough to separate the others. On grader comment 2: grip
reach is the more aggressive and fixed reach the more conservative choice; neither dominates. Note: the default row
reproduces E7 exactly (same seeds, deterministic evaluation).

## E16. Training efficiency and training-time safety
`python -m scripts.training_efficiency` -> `results/training_efficiency.md` (updates as runs finish). All laps with
the shield removed. So far: first clean lap at 200k steps with or without the shield (residual: 50k thanks to its
PID+APF prior), but the shield cuts crashes before that point from about 1000 to 8-9, and crashes over all of
training by about 10x (234 vs 2318 at seed 0).

## E17. Telemetry: where is time lost?
`python -m scripts.telemetry` -> `results/telemetry_speed.png`, `results/telemetry_sectors.md`. Solo flying lap.
Residual PPO 29.2 s, ours 32.6 s, Pure Pursuit 35.2 s, PID+APF 36.1 s; unshielded PPO crashed. Ours is slower than
the residual policy in every sector (0.4-0.9 s each) and never exceeds about 8.4 m/s, even on the main straight
(Pure Pursuit 12 m/s, residual 10 m/s).

`python -m scripts.diag_topspeed`: on the main straight the shield is active on only 2% of steps and the policy
itself commands about 7.8 m/s, with or without the shield. The policy learned to be timid; the shield is not
capping it. Candidate causes, tested in E18: the intervention penalty (going fast near the chicane triggers the
shield, so "always slow" is the easy solution) and the 10 m lidar clip (the chicane is not visible early enough).

## E18. Timidity tests (queued, lane E)
`runs/ppo_shield_w3low_s0` (w3 = 0.02 instead of 0.1) and `runs/ppo_shield_preview_s0` (curvature preview in the
observation). Compared against `ppo_shield_s0` on lap time, top speed and collisions.

## Videos
`python -m scripts.make_videos batch1|batch2|batch3` picks the seed with no crash and the most passes in 20 s and
renders to `~/Downloads/racing_videos/` (not committed). Blue = ego, red = shield intervening, grey = opponents.
