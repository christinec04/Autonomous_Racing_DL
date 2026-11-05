# Experiments

Finish counts in early entries were corrected after the stuck-race fix (PROGRESS.md problem 22): "finished"
means all 5 laps; stuck races are counted separately.

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
Result: fastest clean laps of any controller (30.4 s) but only 9/20 finishes (11 crashes). With our shield added at
race time collisions drop (0.36 / 10 laps) but 14 of 20 races end stuck: 4/20 finished. (An earlier version said
18/20 and called the two complementary; that used the faulty "finished" metric and is withdrawn.)

## E9. PPO with the proposal's original additive shield
`runs/ppo_additive_s0`, raced with the same shield (`results/eval_ppo_additive_s0.json`). Training: 2286 crashes,
no better than no shield. Race: 15/20 finished (nominal), 17/20 (randomised), 0.61 / 0.22 collisions per 10 laps,
but 48.8 s clean laps and 0.55 passes per race: it learned to crawl. Ours (final): 16/20, 34.5 s, 2.95 passes.

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

## E18. Timidity tests
`runs/ppo_shield_w3low_s0` (w3 = 0.02 instead of 0.1) and `runs/ppo_shield_preview_s0` (curvature preview in the
observation). Compared against `ppo_shield_s0` on lap time, top speed and collisions.

**Lower intervention penalty (w3 = 0.02), seed 0, 20 races x 5 laps, nominal:**

| | finished | stuck | clean lap | collisions / 10 laps | shield active | time > 15 deg slip |
|---|---|---|---|---|---|---|
| w3 = 0.1 (ours), original shield | 12/20 | 5 | 34.3 s | 0.38 | 6% | 0% |
| w3 = 0.02, original shield (v1 sim) | 0/20 | 18 | 31.3 s | 1.19 | 35% | 12% |
| w3 = 0.02, escape shield (v2 sim) | 0/20 | 12 | - | 3.47 | 38% | 47% |

Faster when it moves, but the policy hands braking to the shield (35-38% of steps) and gets stuck. On the
post-spin-fixed simulator it slides most of the time: it learned on the v1 tyre artifact (PROGRESS.md problem 24).
Conclusion: the intervention penalty is what keeps the shield rare and the policy self-reliant; lowering it is
not the way to fix timidity. The curvature-preview run is training.

## E19. Shield deadlock: diagnosis and fixes
After fixing the "finished" metric (problem 22), the biggest failure of every shielded controller turned out to be
getting *stuck*: the shield stops the car and never lets it go.
`python -m scripts.diag_stuck <controller> <model> <eval json> [escape]` replays the first stuck race.

Two deadlock types were found:
1. **Wall deadlock:** the car stops ~12 cm from a wall; with the 3-circle body model (about 3 cm fatter than the
   car) the current clearance already reads below the margin, so every action, including standing still, is
   "unsafe" and the fallback holds the car forever.
2. **Mutual deadlock with an opponent:** the ego stops half a metre from an opponent; the opponent's gap keeping
   will not move while the ego is right ahead of it, and the ego's shield will not move next to the opponent.

Fix attempts (`ShieldConfig(escape=True)`, evaluated as `ppo_apf_esc`):

| version | rule | seed 0 nominal: finished / stuck / crashed | verdict |
|---|---|---|---|
| none | - | 12 / 5 / 3 | deadlocks |
| v1 | allow 2 cm of clearance shrinkage near the margin | (not evaluated; unit test still deadlocked) | circle model reads negative clearance |
| v2 | v1 + slow creep manoeuvres, whenever within 7 cm of anything | 7 / 0 / 13 | worse: the relaxed rule applied while driving and ratcheted the car into walls 2 cm per step |
| v3 | v2, but only when nearly stopped (< 0.5 m/s) | 14 / 0 / 6 | deadlocks gone, some crashes |
| v4 | v3 + reverse creep, on the post-spin-fixed simulator (`saturated_v2`, problem 24) | **16 / 0 / 4** | adopted as the final shield |

Same policy, v2 simulator, no escape: 11 / 8 / 1, so v4's gain is the escape, not the simulator change.
Randomised: v4 14 / 0 / 6. The residual policy does not benefit (2/20 finished, heavy sliding) and seed 1's
original-shield policy is weak with or without escape (0-2/20).

Raw results: `results/eval_escape_v2.json`, `results/eval_escape_v3.json`, `results/eval_escape_v4.json`.

## E20. Seed sensitivity
`python -m scripts.seed_summary` -> `results/seed_summary.md`. With the final shield (escape v4, v2 simulator):
seed 0 finishes 16/20 (nominal), seed 1 only 1/20 (14 wall crashes, 9% of the time sliding above 15 deg).
Seed 1's policy learned a much more aggressive, sliding style (42% of the time above 90% grip vs 17% for seed 0);
the shield predicts and avoids loss of control from a stable state, but cannot reliably recover a car that is
already sliding. Without the shield, seeds 0 and 1 finish 1/20 and 3/20. Seed 2: 8/20 with the final shield (7 stuck, E21), 6/20
without (2.55 vs 0.77 collisions / 10 laps). Across 3 seeds: 8.3 +- 6.1 vs 3.0 +- 2.4 finished. Conclusion:
the shield consistently reduces collisions, but how many races are finished depends strongly on the training seed.

## E21. Stall recovery (seed 2 chicane stops)
Seed 2 with the final shield still had 7/20 stuck races. `diag_stuck` (with `tire=saturated_v2 k=<i>`) showed a new
cause: the policy itself crawls at 1 m/s through the 2.5 m chicane (lap distance 84-125 m) and steers the wrong way,
nose 40-45 deg into the outer wall; the shield stops it there correctly and the policy keeps asking for the same.
6 of 7 stuck races stopped at lap distance ~94 m or ~120 m.

`EnvConfig(recover=True)` adds a stall recovery like a real car's limp mode, outside the policy:
- trigger: < 0.3 m progress in 1.5 s while > 20 deg off the track direction or near the edge, or slow (< 1.5 m/s),
  near the edge and pointing outward;
- reverse at 1 m/s with full steering toward the heading error (reversing turns the nose back) until aligned within
  9 deg or 1.5 s; then follow the centerline at 2 m/s for 1 s; then hand back (1 s cooldown);
- every recovery command still goes through the shield (`ShieldConfig(allow_reverse=True)`).

Spot check on the 7 stuck seed-2 races: all 7 finish all 5 laps, using 1-5 recoveries per race; laps behind slow
traffic are ~50 s. Two fixes were needed first (PROGRESS.md problem 27): the shield clamped the reverse command to
0, and a car creeping along the wall nose-out never triggered the stall test.

Full evaluation, same models and race seeds as E19/E20 (`results/eval_recover.json`, 20 races x 5 laps):

| seed | finished, nominal (before -> with recovery) | collisions / 10 laps | randomised finished | races using recovery |
|---|---|---|---|---|
| 0 | 16 -> **19** | 0.44 -> **0.10** | 14 -> 16 (0.47 collisions) | 3/20 (once each) |
| 1 | 1 -> 1 | 4.68 | 3 | 9/20 |
| 2 | 8 -> **19** | 0.77 -> **0.10** | 5 -> 14 | 14/20 (1.6 per race) |

Seed 0 now meets all six targets in both conditions. In seed 0 the recovery also turned 3 crashes into finishes:
those were escape-mode scrapes after a stall. Seed 1 is untouched (its failures are high-speed slides). Chicane
failures, 3 seeds pooled: 46 -> 17 (`results/failure_map.png`). Cost: seed-2 laps behind slow traffic stay slow
(mean clean lap 43 s), because the policy still crawls through the chicane and needs a recovery there most laps.
Inspect one race: `python -m scripts.trace_recover <race seed>`.

## E22. Chicane fine-tuning (running, lane F2)
The recovery treats the symptom. E22 tries to fix the policy: fine-tune the seed-2 and seed-1 policies for 500k steps
(`python -m racing.train --init runs/ppo_shield_s<k>/model_stage3.zip --stages 4 --shield cond_fb_grip_esc
--tire saturated_v2`), where stage 4 is stage-3 traffic with half the episodes starting from rest just before the
chicane (lap distance 55-90 m, random lateral offset +-0.6 m and heading +-0.3 rad, opponents 3-10 m ahead;
`EnvConfig.hotspot_prob`). Raced with and without the recovery (`results/eval_ft_chicane_s<k>.json`).

## Videos
`python -m scripts.make_videos batch1|batch2|batch3` picks the seed with no crash and the most passes in 20 s and
renders to `~/Downloads/racing_videos/` (not committed). Blue = ego, red = shield intervening, grey = opponents.
