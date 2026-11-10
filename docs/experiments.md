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
`runs/ppo_additive_s0`, raced with the same shield (`results/eval_ppo_additive_s0.json`). Training: 2333 crashes (2286 in an earlier count; `results/training_efficiency.md` has 2333),
no better than no shield. Race: 15/20 finished (nominal), 17/20 (randomised), 0.61 / 0.22 collisions per 10 laps,
but 48.8 s clean laps and 0.55 passes per race: it learned to crawl. Ours (final): 16/20, 34.5 s, 2.95 passes.

## E10. Shield dropout
`runs/ppo_shielddrop_s0`: shield on in 100% / 50% / 25% of episodes in stages 1 / 2 / 3. Question: can the policy
keep the shield's training safety but end up safe without it?

Result (`results/eval_ppo_shielddrop_s0.json`, 20 races x 5 laps, original simulator):

| seed-0 policy, raced... | finished nominal | collisions / 10 laps | randomised finished | passes / race | clean lap |
|---|---|---|---|---|---|
| trained without shield, no shield | 0/20 | 5.53 | - | 1.05 | 32.5 s |
| trained with shield, shield removed | 5/20 | - | - | - | - |
| **shield dropout, shield removed** | **16/20** | **0.45** | 13/20 | 0.25 | 42.0 s |
| shield dropout, with the shield | 11/20 (5 stuck) | 0.61 | 14/20 | 0.30 | 44.4 s |
| trained with shield, with shield (ours, original) | 12/20 (5 stuck) | 0.38 | - | 2.65 | 34.3 s |

Dropout works for safety: the policy is safe on its own (16/20 without any shield, vs 0/20 for the unshielded
ablation and 5/20 for the shield-trained policy with its shield removed). Training cost: 0% / 23% / 19% of episodes
crashed in stages 1-3 (shield always on: 1% / 9% / 7%; no shield: 25% / 46% / 21%). But it learned the timid way:
it follows traffic (0.25 passes per race) and laps 8 s slower. With the shield back on it gets stuck like the
original shield (no escape in this protocol). So there is a three-way trade: always-on shield = fast + safe but
dependent on the shield; dropout = safe on its own but timid; no shield = fast but crashes.

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
not the way to fix timidity.

**Curvature preview** (10 centerline curvatures 1-20 m ahead in the observation; `runs/ppo_shield_preview_s0`,
same shield and simulator as the original seed-0 run), 20 races x 5 laps, nominal:

| | finished | stuck | clean lap | collisions / 10 laps | passes / race |
|---|---|---|---|---|---|
| original seed 0 (no preview) | 12/20 | 5 | 34.3 s | 0.38 | 2.65 |
| with curvature preview | 13/20 | 5 | **33.4 s** | **0.25** | **3.50** |

Solo flying lap (`python -m scripts.diag_topspeed <models>`): 31.2 s vs 32.7 s, top speed 8.8 vs 8.4 m/s. Knowing
the road ahead helps a little everywhere, but the cap near 8.5 m/s remains (the v2esc run also tops out at 8.45),
so timidity is not mainly a perception problem. Raced with the final configuration (escape + stall recovery, v2 simulator;
`results/eval_preview_rec.json`): 17/20 finished nominal (14/20 randomised), 0.22 collisions / 10 laps, 3.80 passes
per race (the most of any controller), best lap 30.8 s; vs 19/20, 0.10 and 3.15 for the final seed-0 policy.
Comparable, not clearly better, on one seed.

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

## E22. Chicane fine-tuning
The recovery treats the symptom. E22 tries to fix the policy: fine-tune the shielded seed-2 policy for 500k steps
(`python -m racing.train --init runs/ppo_shield_s2/model_stage3.zip --stages 4 --shield cond_fb_grip_esc
--tire saturated_v2`), where stage 4 is stage-3 traffic with half the episodes starting from rest just before the
chicane (lap distance 55-90 m, random lateral offset +-0.6 m and heading +-0.3 rad, opponents 3-10 m ahead;
`EnvConfig.hotspot_prob`). Training crash rate fell from 32% to ~14% and solo laps got faster (32.1 s vs ~34 s).

**Result: worse on race day** (`results/eval_ft_chicane_s2.json`, 20 races x 5 laps, nominal):

| seed-2 policy | finished | stuck | collisions / 10 laps | time > 15 deg slip |
|---|---|---|---|---|
| original + final shield + recovery (E21) | **19/20** | 0 | **0.10** | 0.0% |
| fine-tuned + final shield | 7/20 | 2 | 1.83 | 10.9% |
| fine-tuned + final shield + recovery | 8/20 | 4 | 1.18 | 16.6% |

The fine-tuned policy learned to slide (grip use > 90% of mu g half the time, 11-17% of the time above 15 deg slip),
the same style that sinks seed 1. Likely causes: a full learning rate (3e-4) for 500k steps moved the policy far,
and nothing in the reward discourages sliding. The seed-1 fine-tune was cancelled (seed 1 already slides).
**E22b**: gentler retry, lr 5e-5 (6x lower), slip penalty `--w6 1.0`, 300k steps (`runs/ppo_shield_ft2_chicane_s2`,
`results/eval_ft2_chicane_s2.json`): no sliding this time (0-2% above 15 deg), but not better than the original
either: 16/20 finished with the recovery (19/20 before), 10/20 without (8/20 before), 0.95 passes per race (1.35
before). Fine-tuning on the failure spot does not beat simply catching the failure with the stall recovery.

## E23. Residual policy trained with our shield
Racing the ResRace-style residual policy with our shield added only at race time fails three ways: deadlock (original
shield, 14/20 stuck), slides (escape shield, 15/20 stuck) and, with the stall recovery too, still 2/20 finished,
14 stuck, 56% of the time above 15 deg slip (`results/eval_residual_rec.json`). `runs/ppo_residual_shield_s0` trains
the residual policy with the final shield from the start (`--residual --shield cond_fb_grip_esc --tire
saturated_v2`, same curriculum) and races it three ways (`results/eval_residual_shield_s0.json`, 20 races x 5 laps):

| residual policy | finished nominal | collisions / 10 laps | clean lap | passes / race | randomised finished |
|---|---|---|---|---|---|
| trained without shield, no shield (E8) | 10/20 | 1.60 | **30.4 s** | 2.20 | - |
| trained without shield, our shield added at race time | 2/20 (14 stuck) | 0.70 | - | 1.70 | 6/20 |
| **trained with our shield, raced with it** (+ recovery) | **15/20** | **0.59** | 32.1 s | **3.15** | **16/20** |
| trained with our shield, raced without it | 10/20 | 1.54 | 31.6 s | 2.40 | 14/20 |
| (plain PPO + our shield, final, for reference) | 19/20 | 0.10 | 34.7 s | 3.15 | 16/20 |

Training the residual policy with the shield turns the combination from the worst shielded controller into a good
one: +5 finishes and a third of the collisions of the unshielded residual policy, 2.6 s faster laps than plain PPO
with our shield and as many passes. Its remaining crashes are car contacts (5 of 5 nominal). The stall recovery
never fired. So ResRace-style residual learning and our action-conditioned shield are complementary *if the policy
is trained with the shield*; adding the shield afterwards does not work. Training was also much safer: 133 crashed episodes over 3.5M steps and 1
before the first clean lap, vs 995 and 259 for the residual policy trained without the shield
(`results/training_efficiency.md`).

**Seed 1** (`runs/ppo_residual_shield_s1`, `results/eval_residual_shield_s1.json`): with the shield 16/20 nominal
(0.47 collisions / 10 laps, 32.1 s, 3.25 passes) and 17/20 randomised (0.35). Raced *without* the shield this seed
does even better nominally (19/20, 0.10) but worse randomised (16/20, 0.44): it learned to stay safe on its own.
**Seed 2** (`results/eval_residual_shield_s2.json`): 17/20 nominal and 17/20 randomised with the shield (0.34 / 0.33
collisions, 32.3 s, 4.05 passes / race, shield active 3% of the time); 17/20 and 16/20 without it.

**Three seeds** (`results/seed_summary.md`, with shield + recovery): finished 16.0 +- 0.8 nominal and 16.7 +- 0.5
randomised, collisions 0.47 +- 0.10 / 0.38 +- 0.05 per 10 laps, laps 32.16 +- 0.11 s, 3.48 passes / race, never stuck.
Plain PPO + our shield: 13.0 +- 8.5 and 11.0 +- 5.7 finished, 1.63 +- 2.16 collisions, 38.1 s. The residual recipe
is the most reliable thing we have trained: a tenth of the seed spread, faster on every seed, more passes. Its
best seed is still below plain PPO's best (19/20, 0.10 collisions): residual learning removes the bad seeds rather
than raising the ceiling. On seeds 1 and 2 the trained policy is about as good without the shield nominally, and
the shield helps slightly in randomised races: once trained with it, the policy needs it rarely (3-6% of steps).

## E24. Why the shield cannot save seed 1, and stricter settings
`python -m scripts.trace_crash ppo_apf_rec@s1 runs/ppo_shield_s1/model_stage3.zip results/eval_recover.json k=3`
replays a seed-1 wall crash at 7.5 m/s. The shield's predicted clearance for the policy's actions shrinks over six
steps (0.38, 0.30, 0.18, 0.11, 0.06 m) and each is accepted because it is above the 5 cm margin; one step later the
best braking manoeuvre is predicted to leave 1 cm, and from then on every option is predicted to spin (> 20 deg slip).
The car slides into the wall with the fallback braking. Two reasons: the rollout samples clearance every 0.02 s
(15 cm of travel at 7.5 m/s), so a fixed 5 cm margin is below the estimate's own jitter at speed; and by the time
the clearance test fires, braking in the corner already destabilises the car.

Race-time variants on seed 1 (same model, 20 races x 5 laps; `results/eval_margin_s1.json`, `eval_beta_s1.json`,
`eval_robust.json`):

| shield (all with escape + stall recovery) | seed 1 nominal finished | collisions / 10 laps | randomised finished | seed 0 nominal / randomised |
|---|---|---|---|---|
| final (5 cm margin, 20 deg slip limit) | 1/20 | 4.68 | 3/20 | **19/20** / **16/20** |
| + speed margin 1 cm per m/s | 1/20 | 4.78 | 3/20 | - |
| + speed margin 2 cm per m/s (m2) | 3/20 | 3.81 | 3/20 | - |
| m2 + slip limit 14 deg | 9/20 | 1.75 | 1/20 | 16/20 / 16/20 |
| m2 + slip limit 10 deg | 5/20 | 2.73 | 3/20 | - |
| m2 + 14 deg + predictor assumes 0.85 x friction | **10/20** | **1.59** | 2/20 | 16/20 / 15/20 |

The speed margin alone barely helps; it mostly makes the shield brake more, and the sliding gets worse (35% of time
above 15 deg). Treating smaller predicted slip as loss of control helps the sliding policy most (1 -> 9-10 of 20)
but costs the clean seed-0 policy 3 finishes and raises its collisions (0.10 -> 0.45). Assuming worst-case friction
did not fix seed 1 in randomised races. So these are a safety/performance dial, not a free improvement; the final
configuration keeps the original settings. The options stay available: `ShieldConfig(c_safe_v=..., beta_max=...,
mu_scale=...)`.

## E25. 50-race head-to-head
20 races per condition cannot separate 19/20 from 18/20. `python -m racing.evaluate ... --first 20 --races 30`
adds race seeds 10020-10049 for ours (final), the additive-shield PPO and PID+APF; `python -m scripts.headtohead`
pools them with the first 20 (`results/headtohead50.md`, Wilson 95% intervals, Fisher / Mann-Whitney tests).

| (50 races each) | finished nominal | finished randomised | clean lap | passes / race |
|---|---|---|---|---|
| ours (final) | **43** (74-93%) | **35** (56-81%) | **34.7 s** | **2.98** |
| PPO + additive shield | 39 (65-87%) | 34 (54-79%) | 46.6 s | 1.10 |
| PID + APF | 28 (42-69%) | 25 (37-63%) | 42.6 s | 1.34 |
| residual PPO trained with our shield (E23) | 39 (65-87%) | **37** (60-84%) | **32.2 s** | **3.42** |

Ours vs additive: no significant difference in finishing or crashing (p = 0.44 nominal, 1.0 randomised), but 12 s
faster laps and 2.7x the passes (p = 1e-8 nominal, 5e-8 randomised). Ours vs PID+APF: more races finished (p = 0.002 nominal, 0.07
randomised). The 20-race numbers were optimistic (19/20 vs 43/50; 16/20 vs 35/50 randomised); conclusions about
finishing rates should use these. Collisions per 10 laps over the 50 races: ours 0.31 nominal and **0.77 randomised, which misses
the 0.5 target** (it is met on the first 20 races only). The residual policy trained with our shield ties ours on finishing (p = 0.44 / 0.82)
and laps 2.5 s faster (p < 1e-27): the strongest controller overall on seed 0.

## E26. Slip penalty: a fix for the sliding seed?
`runs/ppo_shield_v2esc_slip_s1`: seed 1 retrained with the final shield (escape) on the v2 simulator and a slip
penalty in the reward, `--w6 1.0` (per step: `w6 * max(|beta| - 0.15 rad, 0)`). Raced with the escape shield
(`results/eval_ppo_shield_v2esc_slip_s1.json`, 20 races x 5 laps):

| seed 1 | finished nominal | collisions / 10 laps | clean lap | passes / race | randomised finished |
|---|---|---|---|---|---|
| original recipe, final shield + recovery | 1/20 | 4.68 | 36.6 s | 1.80 | 3/20 |
| **slip penalty**, escape shield | **17/20** | **0.22** | **32.5 s** | 2.55 | **13/20** |
| **slip penalty**, escape shield + stall recovery | **18/20** | **0.11** | **32.5 s** | 2.75 | **17/20** |

The penalty removes the sliding style that the shield could not catch, and the policy is also faster. Because seed 1
alone could be luck, lane I (`scripts/queue_lane_i.sh`) trains seeds 0 and 2 with the same recipe.

**Seed 0** (`runs/ppo_shield_v2esc_slip_s0`, `results/eval_slip_rec_slip_s0.json`, with recovery): only 11/20
nominal (2 stuck, 0.92 collisions / 10 laps, 6 of 7 contacts with cars) and 6/20 randomised (1.63), against 19/20 for
seed 0 without the penalty. It also spends 8% of the race above 15 deg slip, so the penalty did not even remove
sliding here. The slip penalty is **not** a general fix: it rescued seed 1 and hurt seed 0 (two seeds: 14.5 +- 3.5
nominal). **Seed 2** (`results/eval_slip_rec_slip_s2.json`): 11/20 nominal, 8/20 randomised, 1.01 collisions / 10 laps,
11% of the time above 15 deg slip. Three seeds: 13.3 +- 3.3 finished, no better than without the penalty
(13.0 +- 8.5) and slower. Lesson: one rescued seed was luck as much as a recipe; the penalty is dropped (E29).

## E27. Does PPO exploit stock tyres?
`runs/ppo_shield_linear_s0`: the seed-0 recipe (original shield, no escape) trained and raced on the stock F1TENTH
linear tyres, which have no grip limit (`results/eval_ppo_shield_linear_s0.json`, 20 races x 5 laps):

| seed 0, original shield | finished nominal | stuck | clean lap | collisions / 10 laps | time > 100% of mu g | time > 15 deg slip |
|---|---|---|---|---|---|---|
| friction-circle tyres (E7) | 12/20 | 5 | 34.3 s | 0.38 | 0.0% | 0.0% |
| stock linear tyres | 13/20 | 6 | **29.3 s** | 0.13 | **9.7%** | 0.0% |

On stock tyres the agent laps 5 s faster by cornering above the friction limit for 9.7% of the race (physically
impossible; best lap 26.5 s). It does not slide (0% above 15 deg): the exploit Evans et al. report as sliding
shows up here as over-the-limit cornering. This is why the friction-circle tyre model is part of the simulator
and why the grip metric counts time above 100% of mu g.

## E28. Generalisation to an unseen track (Track2)
Every policy was trained on Singapore only. `docs/track2.md` describes Track2 (228 m, 55 m straight, fast sweeper,
2.5 m hairpin). Full protocol on Track2 (`python -m racing.evaluate --map Track2 ...`, `results/eval_track2.json`,
20 races x 5 laps, v2 simulator):

| controller (trained on Singapore) | finished nominal | finished randomised | clean lap | collisions / 10 laps | passes / race |
|---|---|---|---|---|---|
| PPO + slip penalty (seed 1) + our shield + recovery | **19/20** | 18/20 | 32.2 s | **0.10** | 2.25 |
| residual PPO trained with our shield | 17/20 | 18/20 | **31.3 s** | 0.33 | **3.60** |
| PPO + our shield + recovery (seed 0) | 16/20 | 18/20 | 36.7 s | 0.46 | 1.25 |
| PPO + additive shield | 18/20 | 19/20 | 45.9 s | 0.21 | 0.00 |
| PID + APF | 15/20 | 15/20 | 39.3 s | 0.60 | 0.80 |
| PPO, no shield | 1/20 | 1/20 | 33.6 s | 4.86 | 0.75 |
| Pure Pursuit | 0/20 | 0/20 | - | 48.0 | 0 |

The shielded learned policies transfer: all finish at least as often as PID+APF and lap 2.6-8.0 s faster. The
seed-0 policy's lap-time edge shrinks (0.93x PID+APF here vs 0.81x on Singapore; the 5-race smoke test even
showed none), while the slip-penalty and residual policies keep theirs. The additive-shield policy is safe but
never passes anyone. Without a shield the policy crashes in 19 of 20 races. The shield is active on 2-12% of steps
on Track2, similar to Singapore. One training seed per controller.

## E29. Choosing the final controller: residual PPO trained with our shield
Every residual + shield seed now has 50 races per condition (`results/eval_extra30_residual_s12.json` adds races
10020-10049 for seeds 1-2; `results/headtohead50.md`):

| 50 races, v2 simulator | finished nominal | finished randomised | clean lap | passes / race |
|---|---|---|---|---|
| PPO + our shield + recovery, seed 0 (best plain seed) | **43** | 35 | 34.7 s | 2.98 |
| residual PPO trained with our shield, seed 0 | 39 | 37 | 32.2 s | 3.42 |
| residual PPO trained with our shield, seed 1 | 42 | 39 | 32.2 s | 3.64 |
| residual PPO trained with our shield, seed 2 | 41 | **40** | 32.4 s | **4.10** |
| PID + APF | 28 | 25 | 42.6 s | 1.34 |

Pooled over the three residual seeds (150 races per condition): 122/150 (81%) finished nominal and 116/150 (77%)
randomised, vs PID+APF 28/50 and 25/50 (Fisher p = 6e-4 and 5e-4); against plain PPO's best seed the finish rate
is tied (p = 0.68 / 0.19) and laps are 1.9-2.5 s faster on every seed (Mann-Whitney p < 1e-27). Targets on the 150
pooled races, nominal / randomised: lap 0.76x / 0.74x PID+APF (<= 0.95, met), collisions 0.43 / 0.53 per 10 laps
(<= 0.5, met / just missed), overtake success 91% / 90% (>= 70%, met), shield active on 5.2% / 5.7% of steps
(<= 10%, met), time above 90% of mu g 8.8% / 9.2% (>= 10%, **missed**: it is fast while using less of the tyre),
time above 15 deg slip 0.0% / 0.8% (<= 1%, met).

On Track2 (unseen) seeds 1 and 2 finish 19/20 each nominal (0.10 collisions / 10 laps, 31.0 / 31.4 s) and 17/20
and 14/20 randomised (`results/eval_track2_residual_s12.json`); with seed 0 (17/20, E28) that is 18.3 +- 0.9 of 20.
Plain PPO + our shield on Track2, three seeds (`results/eval_track2_ours_s12.json` for seeds 1-2):

| Track2, 20 races | seed 0 | seed 1 | seed 2 | mean |
|---|---|---|---|---|
| residual + shield: finished nominal / randomised | 17 / 18 | 19 / 17 | 19 / 14 | **18.3 / 16.3** |
| residual + shield: clean lap, passes / race | 31.3 s, 3.6 | 31.0 s, 3.9 | 31.4 s, 4.0 | **31.2 s, 3.8** |
| plain PPO + shield: finished nominal / randomised | 16 / 18 | 15 / **5** | 19 / 19 | 16.7 / 14.0 |
| plain PPO + shield: clean lap, passes / race | 36.7 s, 1.3 | 33.2 s, 2.2 | 42.5 s, 0.05 | 37.5 s, 1.2 |

On the unseen track plain PPO's seeds fail in different ways: seed 1 crashes in most randomised races (2.61
collisions / 10 laps), seed 2 finishes by sitting behind the opponents (42.5 s laps, one pass in 20 races, slower
than PID+APF's 39.3 s). The residual recipe keeps its speed and passing on every seed.

**Ablation: stall recovery.** Seeds 1-2 of the final controller raced without the stall recovery (escape shield
only, `results/eval_residual_norec_s12.json`): 16 / 17 of 20 nominal, identical to with it, and 17 / 16
randomised (with it 17 / 17). With seed 0 (15 / 14 without, 15 / 16 with) the recovery adds 1.0 race per 20
randomised and nothing nominal: the residual policy, whose PID base always steers back to the centre line, almost
never stalls. It stays in the final controller because it is free (never fires otherwise) and it matters a lot for
plain PPO (E21).

**Decision.** The final controller is residual PPO trained with our action-conditioned shield and stall recovery.
Plain PPO + shield has the best single seed (43/50, 0.10 collisions on the 20-race protocol) but one seed in three
fails (1/20); the residual recipe never fails, is 2 s faster and passes more. Plain PPO + shield stays in the final
evaluation as the second learned controller. The slip penalty (E26) is dropped.

## E30. A wider residual: does letting the policy add more raise grip use?
The final controller (E29) misses one target: it spends under 10% of the race above 90% of mu g. Its policy may only
add `residual_scale = 0.3` of the action range to the PID+APF base, which could cap how hard it drives.
`runs/ppo_residual_wide_s0`, `_s1`: the same recipe with `--residual_scale 0.5` (lane J, `scripts/queue_lane_j.sh`;
`results/eval_residual_wide_s0.json`, `_s1`, 20 races x 5 laps, v2 simulator, with shield + recovery):

| seed 0 | finished nominal / randomised | collisions / 10 laps | clean lap | passes / race | time > 90% of mu g | shield active |
|---|---|---|---|---|---|---|
| scale 0.3 (final, E23) | 15 / 16 | 0.59 / 0.44 | 32.1 s | 3.15 | 13% | 6% |
| **scale 0.5** | **19 / 18** | **0.10 / 0.21** | 32.5 s | **4.05** | 6% | 3% |
| scale 0.5, raced without the shield | 19 / 18 | 0.11 / 0.21 | 32.2 s | 3.80 | 5% | - |

| seed 1 | finished nominal / randomised | stuck | collisions / 10 laps | clean lap | passes / race | time > 15 deg slip | shield active |
|---|---|---|---|---|---|---|---|
| scale 0.3 (final, E23) | 16 / 17 | 0 / 0 | 0.47 / 0.35 | 32.1 s | 3.25 | 0% | 6% |
| scale 0.5 | 14 / 11 | 2 / 5 | 0.47 / 0.51 | 34.9 s | 2.55 | 11% / 19% | 19% / 22% |
| scale 0.5, raced without the shield | 8 / 10 | 0 / 0 | 2.05 / 1.58 | 29.9 s | 1.55 | 0% | - |

Training was as safe (65 crashed episodes vs 133; `results/training_efficiency.md`). The wider residual does not
raise grip use, the target it was meant for: it halves it (13% -> 6%; scale 0.3 seeds 1-2 were at 7%, which is why
the pooled E29 number missed). It drives a smoother line at the same lap time. On seed 0 it is clearly safer and
passes more, but **seed 1 brings back the failure mode of plain PPO**: on its own it laps 2 s faster than any
residual policy and crashes in half the races, and with the shield it leans on it (active on 20% of steps), slides
(11-19% of the time above 15 deg) and gets stuck. With more authority the policy can again learn to drive at the
limit, so the residual scale is the dial between consistency and peak performance. Two seeds: 16.5 +- 2.5 vs 15.5 +-
0.5 finished nominal, 14.5 +- 3.5 vs 16.5 +- 0.5 randomised. **Decision: keep 0.3**; consistency is why the residual
recipe was chosen. The grip target stays missed (8.8% pooled) and is reported as such.

## E31. Baselines on three training seeds (lane K, running)
The additive-shield and residual (no shield) baselines only had seed 0. `scripts/queue_lane_k.sh` trains seeds 1-2
with the seed-0 recipe and races each on Singapore and Track2 (`results/eval_<run>_<map>.json`, 20 races x 5 laps):

| PPO + additive Eq. 2/3 shield | Singapore finished nom / rand | lap | passes / race | Track2 finished nom / rand | Track2 lap |
|---|---|---|---|---|---|
| seed 0 | 18 / 16 | 47.6 s | 0.85 | 18 / 19 | 45.9 s |
| seed 1 | 13 / 15 | 50.4 s | 0.00 | 10 / 13 | 46.7 s |
| seed 2 | 12 / 12 | 50.2 s | 0.10 | 14 / 14 | 45.7 s |

Seed 1 confirms the timid style the proposal feedback predicted for an always-on APF (no passes at all in 20
races), and it is less safe than seed 0 (0.92 collisions / 10 laps). Seed 2 is the same: 0.10 passes per race,
1.06 collisions / 10 laps, 50 s laps. Over three seeds the additive shield gives 14.3 of 20 finished, slower than
PID+APF (42.8 s) on every seed.

| Residual PPO, no shield (ResRace-style) | Singapore finished nom / rand | lap | collisions / 10 laps | passes / race | Track2 finished nom / rand | Track2 lap |
|---|---|---|---|---|---|---|
| seed 0 | 10 / 8 | 30.4 s | 1.60 | 2.20 | - | - |
| seed 1 | 7 / 5 | 30.3 s | 1.89 | 2.15 | 11 / 7 | 29.3 s |
| seed 2 | (running) | | | | | |

The residual baseline is the fastest recipe (30.3 s, about 2 s faster than the residual trained with our shield)
but crashes into opponents: 11 of seed 1's 13 DNFs are car contacts. Training with our shield costs about 2 s per
lap and doubles the finish rate (E29: 16.0 of 20 per seed).

**Update 2026-11-09.** Residual baseline seed 2 finished (lane Q; its first attempt crashed with the laptop, kept as
`runs/ppo_residual_s2_attempt1_crashed`). Singapore 15 / 10 of 20 at 31.3 s with 3.65 passes, Track2 10 / 14 at
30.4 s. Over three seeds the residual baseline without a shield finishes 10.7 / 7.7 of 20 on Singapore (seeds
10/8, 7/5, 15/10), against 16.0 / 16.7 for the same recipe trained with our shield (E29). It stays the fastest
recipe (30.3-31.3 s), and 34 of its 43 non-finishes on seeds 1-2 are car contacts.

## E32. Does the residual policy need *our* shield, or would any shield do?
`scripts/queue_lane_l.sh`: the E29 recipe (residual, scale 0.3, v2 simulator) trained with the proposal's additive
Eq. 2/3 shield instead of ours, seeds 0-1, raced with the same shield (`results/eval_ppo_residual_additive_s*.json`).

| residual policy trained and raced with | finished nom / rand | lap | collisions / 10 laps | shield on | crashes in training |
|---|---|---|---|---|---|
| our shield (E29, 3 seeds) | 16.0 / 16.7 of 20 | 32.2 s | 0.47 | 5% | 81-133 |
| additive Eq. 2/3 shield, seed 0 | 0 / 0 | 37.9 s | 9.07 | 71% | 5717 |
| additive Eq. 2/3 shield, seed 1 | 1 / 0 | 36.8 s | 7.44 | 68% | 4845 |

It fails completely: training crashes twice as often as PPO with no shield at all (2295-2769 episodes), and no race is finished.
**Control with no learning** (`results/eval_zero_residual.json`, residual output fixed at 0, `--models X=zero`):

| base controller (PID + tuned APF) with | finished nom / rand | lap | collisions / 10 laps | passes / race |
|---|---|---|---|---|
| nothing (= PID+APF) | 10 / 11 | 43.3 s | 1.50 | 1.20 |
| + additive Eq. 2/3 shield | **0 / 0** | - | 68.4 (all walls) | 0.05 |
| + our shield + stall recovery | **20 / 16** | 42.5 s | **0.00** / 0.47 | 2.10 |

So the failure is in the composition, not the learning: the residual base already contains a tuned APF
(k_steer 0.3) and the additive shield adds a second, untuned one (k_steer 2.0) on top. The two fields push the car
into oscillation and slides (22% of time above 15 deg slip), and the learned residual (at most 0.3 of the action
range) cannot cancel them. Our shield leaves a safe action alone, so it composes with any controller.

The second row is also a result in its own right: **our shield alone turns the classical PID+APF into the safest
controller in the study** (20/20 nominal, no collision), without any learning, but it laps 10 s slower than the
final controller. Learning buys the speed; the shield keeps it safe. Extended to the 50 race seeds
(`results/eval_extra30_zero.json`), the base with our shield finishes 47/50 nominal and 36/50 randomised. That is
more nominal finishes than any single seed of the final controller (39-42 of 50) at 42 s instead of 32 s per lap.
In randomised races the final controller is level with it (37-40 of 50).

## E33. Stress tests outside the training conditions (lanes M and O)
`scripts/queue_lane_m.sh` races six controllers on the 20 race seeds at one fixed friction scale (training
randomised x0.85-1.15), no lidar noise. `python -m scripts.stress_summary` writes `results/stress.md` and
`report/figs/stress.pdf`. Races finished:

| friction scale | final controller (3 seeds) | PPO + our shield, seed 0 | PID + APF | PPO + additive APF |
|---|---|---|---|---|
| x0.7 | 27% (25, 55, 0) | 35% | 30% | 5% |
| x0.8 | 52% (65, 65, 25) | 85% | 50% | 15% |
| x1.0 | 80% (75, 80, 85) | 95% | 60% | 90% |
| x1.2 | 83% (95, 90, 65) | 80% | 70% | 75% |

Below the training range the final controller loses its lead and drops to PID+APF's level, while plain PPO with
the shield holds up better at x0.8. More grip than in training costs nobody much. At x0.8 the final controller
spends 4-8% of the race above 15 deg slip (0-2% at nominal friction), so it is driving past a limit it does not
know about.

**Is it the shield's friction model?** The shield predicts with the nominal friction. Lane O
(`scripts/queue_lane_o.sh`, `--shield_mu`) tells the shield's predictor the true friction and reruns x0.8:

| races finished | shield assumes nominal friction | shield told the true friction | Fisher p |
|---|---|---|---|
| x0.8, final controller, 3 seeds | 31/60 (13, 13, 5) | **50/60** (17, 19, 14) | 4e-4 |
| x0.8, PPO + our shield, seed 0 | 17/20 | 16/20 | 1.0 |
| x0.7, final controller, 3 seeds | 16/60 (5, 11, 0) | **40/60** (14, 19, 7) | 2e-5 |
| x0.7, PPO + our shield, seed 0 | 7/20 | **18/20** | 8e-4 |

The residual policy drives closer to the limit and relies on the shield to catch it, so it needs the shield's
model to be right already at x0.8. Plain PPO keeps its own margin, which is enough at x0.8 but not at x0.7. With
the true friction, slip above 15 deg at x0.7 falls from 9-14% to 1-2% for seeds 0-1. Seed 2 still slides (16%)
and finishes 7/20, so part of its drop is the policy itself. This motivates E35, where the shield estimates the
friction instead of being told.

**Update 2026-11-09.** The remaining settings (lane M, `results/stress_mu0.6.json`, `stress_mu1.3.json`,
`stress_opp5.json`; races finished of 20):

| setting | final controller (3 seeds) | PPO + our shield s0 | PID + APF | PPO + additive |
|---|---|---|---|---|
| x0.6 | 5 / 60 (1, 4, 0) | 5 | 4 | 1 |
| x1.3 | 52 / 60 (17, 17, 18) | 20 | 17 | 17 |
| 5 opponents, nominal | 50 / 60 (17, 16, 17) | 13 | 9 | 11 |
| 5 opponents, randomised | 42 / 60 (13, 14, 15) | 13 | 10 | 11 |

At x0.6 every controller fails, mostly into walls, so that is beyond what any of them handles. More grip is easy
for all. With five opponents the final controller finishes as often as with three (83% vs 80% nominal on these
20 seeds), while PID+APF drops from 60% to 45%. The one-opponent test crashed on a bug in the
overtake counter, which also undercounted passes with five opponents (PROGRESS 40). Both rerun in lane T
(`results/stress_opp1_v2.json`, `stress_opp5_v2.json`); the original opp5 file is kept.

**Update 2026-11-09, one opponent** (`results/stress_opp1_v2.json`, after the counter fix). Races finished of 20,
nominal / randomised:

| controller | 1 opponent | 3 opponents (E29 / E33 seeds) | 5 opponents |
|---|---|---|---|
| final controller, 3 seeds | 57 / 59 of 60 | 48 / 50 of 60 | 50 / 42 of 60 |
| PPO + our shield, seed 0 | 17 / 17 | 19 / 16 | 13 / 13 |
| PID + APF | 19 / 20 | 12 / 10 | 9 / 10 |
| PPO + additive APF | 17 / 17 | 18 / 16 | 11 / 11 |

Alone with one car, every controller finishes almost every race. Traffic is what separates them. PID+APF falls
from 95% to 50% with more cars, the final controller from 97% to 77%. With one opponent the final controller laps at
32 s, PID+APF at 41 s.

*Correction 2026-11-09:* the PID + APF 3-opponent randomised entry above should read 12, not 10
(`results/final_v2_others.json`, seeds 10000-10019), so PID+APF falls from 98% to 60% with three cars.

**Update 2026-11-09, five opponents rerun** (`results/stress_opp5_v2.json`, lane T). Finishes, car contacts and wall
hits are identical race by race to the original `stress_opp5.json`, so the counter bug only touched the pass count:
the final controller makes 5.7 passes per race with five opponents, not the 3.9 the old counter reported. The table
above stands.

## E34. What still ends the final controller's races? (contact classification)
`python -m scripts.classify_contacts` replays every car-contact DNF and classifies the contact at the contact step
(`results/contacts.md`). Final controller seed 0, 50 race seeds, nominal + randomised: 24 contacts; the final
controller has 2 wall hits in 300 races over three seeds, all other DNFs are car contacts.

| class | count | meaning |
|---|---|---|
| ego just ahead (~0.5 m) | 15 | cutting back in front of the car it just passed (ego still faster in 12 of 15) |
| side by side | 5 | squeezed: opponents follow the centreline and never yield sideways |
| rear-end | 4 | ego closing on a car ahead |

15 of 24 contacts happen on the first lap (the field is bunched; the first tight corner at s = 39 m alone has 5).
The shield was active in the last second before all 24, with a fallback, so it saw the danger and could not
resolve it. Likely cause: the shield predicts every opponent braking at 6 m/s^2 (`opp_brake`), which is the worst case
for a car ahead but the *best* case for a car just passed, which in fact holds its speed (opponents only slow
for a car in their own lane, within 0.7 m). Lane N races the final controller with a shield that checks both hypotheses (`ShieldConfig.opp_both`, below).

**Two-hypothesis opponent check** (`ShieldConfig.opp_both`, controller `ppo_residual_apf_rec_ob`). The shield
accepts an action only if it is safe whether each opponent brakes or holds its speed. Same three trained policies,
same 50 race seeds (`results/eval_oppboth_s<seed>.json`):

| 3 seeds x 50 races | finished nom / rand | races ended by a car | races ended by a wall | lap | passes / race |
|---|---|---|---|---|---|
| original shield (E29) | 122 / 116 of 150 | 60 | 2 | 32.3 s | 3.7 |
| two-hypothesis check | **133 / 123** of 150 | **25** | 17 | 32.8 s | 4.0 |

Car contacts fall by more than half (Fisher p = 6e-5) at a cost of 0.5 s per lap, and the car passes slightly more.
Wall hits rise from 2 to 17 (p = 6e-4), 13 of them in randomised races. Finishes go up from 238 to 256 of 300
(p = 0.07). A replay of one new wall hit (seed 10043, randomised) shows the cause. With a car alongside, sometimes no candidate action is
safe under both hypotheses, and the fallback then steers away from the car into the wall. `opp_relax`
(controller `ppo_residual_apf_rec_ox`) falls back to the original braking-only check in that case. It is queued in
lane P (via lane R after the shutdown, PROGRESS 38).

**Update 2026-11-09, relaxed check (E34b, lane P, `results/eval_opprelax_s<seed>.json`).** Same 3 policies x 50
race seeds:

| 3 seeds x 50 races | finished nom / rand | car | wall | lap | passes / race |
|---|---|---|---|---|---|
| original shield (E29) | 122 / 116 | 60 | 2 | 32.3 s | 3.7 |
| both hypotheses (E34) | 133 / 123 | 25 | 17 | 32.8 s | 4.0 |
| both, relaxed fallback (E34b) | 131 / 125 | 38 | 4 | 32.5 s | 3.9 |

The relaxed fallback removes the wall hits the two-hypothesis check introduced (17 -> 4, p = 0.006) and keeps the
same 256 of 300 finishes. Against the original shield it cuts car contacts from 60 to 38 (p = 0.02) with no
significant change in wall hits (2 -> 4). Per seed 43/39, 45/43, 43/43 of 50. It replaces the original check in
the candidate final shield (E36). Full tables: `results/analysis/2026-11-09.md`.

## E35. Can the shield estimate the friction itself? (lane S, running)
E33 showed the final controller needs the shield to know the friction. `ShieldConfig.mu_est` (controller
`ppo_residual_apf_rec_mu`) starts from nominal friction and updates an estimate from the car's own state each step.
When a tyre's slip angle passes the point where its force saturates (|alpha| C >= 0.95 of the friction circle left
after braking), the car is at the grip limit and the measured acceleration / g is the friction. If only one axle
saturates this reads low, which is the safe side. Below the limit, acceleration above the estimate slowly raises it.
The estimate sets both the predictor's friction and the APF reach, and each race records it once a second.

First check, one lap each, seed 0 policy: at x0.8 the estimate falls from 1.0 to 0.70-0.81 within the lap and all 3
races finish. At x1.2 it stays at 0.9-1.1, since the car never reaches the higher limit, so the shield does not
become overconfident. Lane S (`scripts/queue_lane_s.sh`) races all three seeds at x0.8 and x0.7 and on the main
protocol, which checks that the estimate costs nothing in normal conditions.

**Update 2026-11-09, results (lane S, `results/stress_mu0.8_muest.json`, `stress_mu0.7_muest.json`,
`eval_muest.json`).** Final controller, 3 seeds x 20 races:

| friction | shield assumes nominal | shield told the truth | shield estimates it |
|---|---|---|---|
| x0.8 | 31 / 60 | 50 / 60 | **54 / 60** (20, 18, 16) |
| x0.7 | 16 / 60 | 40 / 60 | 32 / 60 (10, 18, 4) |

At x0.8 the estimate does as well as knowing the truth. Its estimate ends near 0.78. At x0.7 it recovers half of the
gap to the oracle. On the main protocol it is level with the original (nominal 51 vs 48 of 60, randomised 45 vs
50, neither significant), with the shield active a little more often (8% vs 5% of steps). The trace explains the
remaining gap. The estimate swings by about +-0.2 within a race (at x0.7 between 0.53 and 1.0, at nominal friction
between 0.78 and 1.15), so it is sometimes too optimistic right when it matters. A smoother version (`mu2`, readings
at the limit weigh 0.2 instead of 0.5) is running in lane T, and the combination with the relaxed opponent check
(E36) in lane U.

**Update 2026-11-09, smoother estimate (E35b, lane T, `results/stress_mu0.7_mu2.json`).** Readings at the limit
weigh 0.2 instead of 0.5, readings that prove more grip 0.02 instead of 0.05 (`ppo_residual_apf_rec_mu2`). At x0.7
the final controller finishes **47 / 60** (15, 19, 13), against 32 with the first estimate, 40 when the shield is
told the true friction and 16 with the nominal model. Beating the oracle is plausible: the estimate reads a little
low (single-axle saturation), so the shield keeps a margin the oracle does not. The main-protocol check of this
version (`results/eval_mu2.json`) is running.

**Update 2026-11-09, smoother estimate on the main protocol** (`results/eval_mu2.json`, lane T, 20 race seeds,
same seeds as the original). Finished nominal / randomised of 60: original 48 / 50, first estimate 51 / 45,
smoother estimate 49 / 52, 0 wall hits for all, lap +0.2 to 0.3 s. So the smoother estimate costs nothing in normal
races and wins at x0.7 (47 vs 16 of 60).

## E36. Candidate final shield: relaxed opponent check + friction estimate (lane U)
`ppo_residual_apf_rec_oxmu` = the final controller's shield with both fixes (E34b relaxed two-hypothesis opponent
check, E35 friction estimate, first version), same three trained policies, `results/eval_oxmu.json` (50 race
seeds) and `results/stress_mu0.8_oxmu.json`:

| 3 seeds x 50 races | finished nom / rand | car | wall | lap |
|---|---|---|---|---|
| original shield (E29) | 122 / 116 | 60 | 2 | 32.3 s |
| relaxed opponent check (E34b) | 131 / 125 | 38 | 4 | 32.5 s |
| relaxed check + friction estimate (E36) | **139 / 130** | **30** | **0** | 32.7 s |

269 of 300 finished against 238 (Fisher p = 7e-4), no wall hit in 300 races, half the car contacts, for 0.5 s per
lap. Per seed 46/45, 45/42, 48/43 of 50. At x0.8 it finishes 55 / 60 (nominal model 31, estimate alone 54). The
two fixes add up: the estimate also helps in normal races because randomised friction goes down to x0.85. x0.7 is
running; lane V retrains the policy with this shield on during training (E37).

**Update 2026-11-09, E36 at x0.7** (`results/stress_mu0.7_oxmu.json`, lane U). 41 / 60 (9, 20, 12), 6 car
contacts but 12 wall hits, below the smoother estimate alone (47, 4 wall hits). The wall hits are not slow
convergence at the start: the estimate falls below 0.72 within 5 to 17 readings (every 25 steps) in every race.
Before each wall hit it climbs back to about 0.92 (true 0.70). Races that end in the wall spend 16% of their
readings above 0.85, races that finish 1.5%; with the smoother estimate 5% and 1%. Many of these crashes come at
the same point of a lap (x.17 laps done). The rise rule takes any single below-limit reading above the estimate as
proof of more grip, and a reading is a finite difference of speed and slip angle, so noise can push it up on a
stretch where no tyre saturates. Analysis: `results/analysis/2026-11-09b.md` (`scripts/analyze_nov9b.py`).

## E36b / E35c. Combined shield with a steadier estimate (lanes W and X, running)
- E36b (lane W): E36 with the smoother estimate (rate 0.2, rise 0.02), `ppo_residual_apf_rec_oxmu2`. x0.7, then
  50 races main protocol, then x0.8.
- E35c (lane X, after W): new option `mu_est_med` (shield.py, default 1 = unchanged): a rise needs the median of
  the last 9 readings above the estimate, so one noisy reading cannot raise it. Tried with both rise rates at x0.7
  (`ppo_residual_apf_rec_oxmed`, `_oxmu2med`), then 50 races main protocol for the smoother one. A one-race smoke
  test at x0.7 kept the estimate between 0.61 and 0.72.

*Correction 2026-11-09 evening* to the E36 x0.7 explanation above (estimate drifting up before wall hits). The
last ten readings of every wall-hit race (`results/analysis/2026-11-09c.md`) show the estimate near the true 0.70
right before the wall. It jumps to about 0.9 in one reading at the impact, then stays flat while the car is stopped
(no reading below 2 m/s). The share of readings above 0.85 counted that flat stretch after the crash, so it measured
the crash, not its cause. The noise explanation does not hold either: the median gate leaves wall-hit races just as
high. The x0.7 wall hits happen with a correct estimate, like the 13 of the oracle shield (E33).

**Update 2026-11-09 evening, results** (lanes W and X, same three trained policies):

| shield | main, of 300 | car / wall | x0.8, of 60 | x0.7, of 60 | x0.7 wall |
|---|---|---|---|---|---|
| E36 (estimate rate 0.5, rise 0.05) | 269 | 30 / 0 | 55 | 41 | 12 |
| E36b smoother (0.2 / 0.02) | 257 | 40 / 3 | 57 | 47 | 7 |
| E35c median gate, rise 0.05 | | | | 40 | 9 |
| E35c smoother + median gate | 265 | 33 / 1 | | 49 | 4 |

On the main protocol the three are level (269 vs 257, p = 0.17; vs 265, p = 0.7). At x0.7 the smoother estimate
is what helps (41 -> 47 -> 49), the median gate on its own does nothing (40). Per seed at x0.7 the smoother +
median gate version finishes 14, 20, 15 of 20. Laps within 0.2 s of each other.

## E37. Retraining the policy with the combined shield on (lane V; seed 2 in lane Y, running)
Same recipe as the final controller (residual PPO, saturated_v2, 3.5M steps) but trained with
`cond_fb_grip_esc_oxmu` on, and raced with it. A: the usual friction randomisation x0.85-1.15. B: wider,
x0.65-1.15 (`--mu_range`, train.py). Compared with the E29 policies (trained with the old shield) raced with the
same shield (E36). Same 50 race seeds (main protocol), 20 for the stress tests.

| policy | main, of 100 | car / wall | lap s | passes | shield | x0.8 | x0.7 |
|---|---|---|---|---|---|---|---|
| E29 seed 0 | 91 | 9 / 0 | 32.6 | 3.9 | 0.106 | 20 | 9 |
| E29 seed 1 | 87 | 12 / 0 | 33.1 | 4.0 | 0.097 | 19 | 20 |
| E37 A seed 0 | 94 | 5 / 0 | 33.7 | 3.0 | 0.072 | 17 | 12 |
| E37 A seed 1 | 82 | 12 / 1 | 35.5 | 3.5 | 0.093 | 12 | 14 |
| E37 B seed 0 | 96 | 4 / 0 | 33.4 | 4.0 | 0.035 | 15 | 20 |

So far: retraining with the usual friction range does not help (176 vs 178 of 200) and laps get 1 to 2 s slower.
The wide range on seed 0 is the best single policy yet on the main protocol (96 of 100, 0 car contacts
randomised) and finishes all 20 at x0.7, with the shield acting on 3.5% of steps (10.6% for E29 seed 0). One seed
is not enough, the E29 seed-1 policy also finishes 20 of 20 at x0.7. B seed 1 is being raced; lane Y trains
seed 2 of A and B. Analysis: `results/analysis/2026-11-09c.md` (`scripts/analyze_nov9c.py`).

**Update 2026-11-09 evening, B seed 1** (`results/*_ppo_residual_oxmu_widemu_s1.json`): 92 of 100 main protocol
(7 car contacts, 0 wall hits, lap 33.5 s), 20 of 20 at x0.8, 19 of 20 at x0.7. Seeds 0 and 1 together, against the
E29 policies of the same seeds raced with the same shield:

| | main, of 200 | x0.8, of 40 | x0.7, of 40 | lap s |
|---|---|---|---|---|
| E29 policies | 178 | 39 | 29 | 32.6-33.1 |
| E37 A (usual range) | 176 | 29 | 26 | 33.7-35.5 |
| E37 B (wide range) | 188 (p = 0.11) | 35 (p = 0.20) | **39 (p = 0.003)** | 33.4-33.5 |

Training on low friction is what helps at low friction; training with the new shield alone does not. B costs
about 0.5 s per lap against E29 and leans on the shield less (3.5-6% of steps, 10-11% for E29). Seed 2 of A and B
trains in lane Y. Clips 17 and 18 (`scripts/make_videos.py batch11`): race seed 10003 at x0.7, the E29 policy turns
in tight at the chicane and hits the inside wall at 44 s, the E37 B policy takes a wider line at 4.5 m/s.

**Update 2026-11-09 night, how B drives** (`results/gg_e37.png`, `scripts/gg_e37.py`, seeds 0+1, combined shield).
B leaves more margin: in nominal races it is above 90% of the friction limit 5.3% of the time against 12.4% for
E29, at x0.7 26.9% against 37.2%, and the E29 points outside the x0.7 circle (slides after a lost corner) are
almost absent for B. Shield interventions 4.9% of steps against 10.2%, passes per race about the same (762 of 801
attempts against 780 of 813). It gives up some lap time for margin rather than learning to rely on the shield.

**Update 2026-11-09 23:10, three seeds** (lane Y added seed 2 of A and B; `results/analysis/2026-11-09d.md`,
`scripts/analyze_nov9d.py`). All raced with the combined shield, E29 = the current final policies:

| policies, 3 seeds | main, of 300 | car / wall | x0.8, of 60 | x0.7, of 60 | x0.7 wall | lap s | >90% grip | shield |
|---|---|---|---|---|---|---|---|---|
| E29 | 269 (91, 87, 91) | 30 / 0 | 55 | 41 (9, 20, 12) | 12 | 32.74 | 10.3% | 9.0% |
| E37 A | 272 (94, 82, 96) | 20 / 1 | 48 | 44 | 7 | 34.29 | 9.1% | 7.5% |
| E37 B | **283** (96, 92, 95) | **15 / 0** | 52 | **59** (20, 19, 20) | **0** | 33.30 | 5.9% | 5.1% |

B against E29: main p = 0.049, x0.7 p = 9e-6, x0.8 p = 0.56 (level). No wall hit for B in 420 races. A against
E29: p = 0.78 / 0.11 / 0.69, and 1.5 s per lap slower, so training with the new shield alone does nothing; the
wide friction range is what helps. B is now the candidate final controller (residual PPO trained on x0.65-1.15
with the combined shield, raced with it), at 0.56 s per lap slower than E29. Lanes Z (control: wide range, old
shield) and AA (Track2, five opponents) decide it.

## E38. Is it the friction range or the new shield? (lanes Z and AA, queued 2026-11-09 21:35)
- Lane Z, control for E37 B: same wide range x0.65-1.15 but trained with the old shield (`cond_fb_grip_esc`, as
  E29), seeds 0 and 1 (`runs/ppo_residual_widemu_s<seed>`), raced with the combined shield like E37 (50 races, x0.8,
  x0.7). If it matches E37 B, the range does the work; if it falls back to E29, the new shield during training
  matters once the range is wide. Starts when lane Y's trainings finish.
- Lane AA, generalisation: E37 B seeds 0-2 against E29 seeds 0-2, both raced with the combined shield, on the
  unseen Track2 (`results/eval_widemu_Track2.json`) and with five opponents (`results/stress_opp5_widemu.json`),
  20 race seeds nominal + randomised. Starts after lane Y.
- Lane AB (queued 2026-11-10 09:20, after AA): the remaining stress settings for the same comparison, friction
  x0.6 and x1.3 and one opponent (`results/stress_mu0.6_widemu.json`, `stress_mu1.3_widemu.json`,
  `stress_opp1_widemu.json`).
- Note 2026-11-10: the laptop slept overnight, so lanes Z and AA paused and resumed on their own around 09:10.
  The pause start is estimated, not logged: lane Z was at 1.15M of 3.5M steps at 09:12, about one hour of training
  after its 22:05 start, and Track2 went from 50 to 80 of 240 races between 23:06 and 09:12.
- **Result 2026-11-10, Track2 (unseen track, lane AA, `results/eval_widemu_Track2.json`):** E37 B finishes 110 of
  120 races (3 seeds x 20 race seeds x nominal + randomised), E29 106 of 120 (Fisher p = 0.52, no real difference).
  Wall hits 1 vs 2, laps about the same (31.7-33.4 s vs 31.4-33.1 s), shield active 4-9% of steps vs 8-14%, time
  above 90% grip 4-10% vs 7-12%. So the wide-friction policy keeps its lead in grip margin on a track it never
  saw, and does not lose anything there, but Track2 at normal friction does not separate the two.
- **Crash 2026-11-10 ~10:23:** the laptop went down (PROGRESS 43) and killed all three lanes. Lane Z had saved
  stage 1 (1.5M steps) of both trainings and was at 2.3M of 3.5M (stage 2 not saved). Lane AA was at 210 of 240
  races of `stress_opp5_widemu`, which saves only at the end, so those races are lost (log kept as
  `runs/_stress_opp5_widemu_crashed_2026-11-10.log`). Lane AB had not started.
- **Recovery (lane AC, `scripts/queue_lane_ac.sh`, started 11:13):** with the report due Nov 13, stages 2-3 are
  trained from the saved stage-1 model (`--init`, which restores the policy, the Adam state and the reward
  normalisation; same constant learning rate) into new folders `runs/ppo_residual_widemu_s<seed>_from_stage1`. The
  crashed folders stay as they were. Differences from an uninterrupted run: the random state at the start of stage
  2, and step counts in the new logs restart at 0 (add 1.5M). Results are reported under the `_from_stage1` names.
  Lanes AA (five opponents, from scratch) and AB (x0.6, x1.3, one opponent) were restarted unchanged.

## Videos
`python -m scripts.make_videos batch1|batch2|batch3` picks the seed with no crash and the most passes in 20 s and
renders to `~/Downloads/racing_videos/` (not committed). `batch9` renders clip 12, slip-penalty PPO + our shield on
the unseen Track2 (seed 10004: no crash, 3 passes, shield active 3% of the time). Blue = ego, red = shield intervening, grey = opponents.

**Update 2026-11-09, batch10** (same race seed before and after, final controller seed 0). The HUD shows the
shield's friction estimate next to the true value.
- 13 / 14: friction x0.7, seed 10018. Shield assuming normal grip crashes after 99 m. Shield estimating the grip
  finishes the 25 s clip (130 m), its estimate reads 0.71 against the true 0.70 by 12 s.
- 15 / 16: seed 10026, nominal. The original opponent check (opponents brake) hits a car after 83 m. The relaxed
  two-hypothesis check (E34b) drives through (115 m in 20 s).

