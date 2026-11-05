# Current results (living page)

Updated as runs finish. Raw tables: [results/summary.md](../results/summary.md) (seed 0, every controller),
[results/seed_summary.md](../results/seed_summary.md) (across seeds),
[results/training_efficiency.md](../results/training_efficiency.md). Experiment details: [experiments.md](experiments.md).

## What works

| finding | evidence |
|---|---|
| The action-conditioned shield prevents crashes that an additive APF (proposal Eq. 2/3) cannot | stress test E4: additive 100% crash in every scripted scenario; conditioned + fallback 0-12% solo/random |
| Shielded training is ~10x safer | E16: 234-313 vs 2318-2769 training crashes (seeds 0-1); 8-9 vs ~1000 before the first clean lap; the proposal's additive shield: 2286, no better than none |
| The shield lowers race collisions | seed 0: 0.38-0.44 vs 5.53 collisions / 10 laps without; across 2 seeds 0.85 (original) vs 4.43 |
| The shield intervenes rarely once trained | 3-6% of race steps (seed 0), vs 93% for the always-on APF in PID+APF |
| Stall recovery fixes the chicane stops | E21: seeds 0 and 2 finish 19/20 (from 16 and 8), 0.10 collisions / 10 laps each; seed 0 meets all 6 targets nominal and randomised |
| The deadlock escape removes stuck races | E19: seed 0 from 5-8 stuck to 0; 16/20 races finished (best of all controllers) |
| Action-conditioned beats additive as a training shield | PPO trained with the proposal's additive shield: 15/20 finished but 48.8 s laps, 0.55 passes / race (timid); ours 16/20, 34.5 s, 2.95 passes |
| Learned driving beats classical | seed 0 clean laps 34.5 s vs 42.8 s PID+APF; residual PPO 30.4 s |
| Training with the final shield from the start gives the same picture | `ppo_shield_v2esc_s0` (escape shield, v2 sim from step 0): 14/20 finished, 1 stuck, 0.62 collisions / 10 laps, 3.45 passes / race (most of any controller) |
| Final comparison (one simulator version) | `results/final_summary.md`: ours 19/20 finished, 0.10 collisions, all 6 targets met; additive-shield PPO 18/20 but 47.6 s laps; PID+APF 12/20; residual 10/20; no shield 0/20 |
| Friction-limited tyres close the sliding loophole | stock tyres corner at 2.4 g; with ours, seed 0 spends 0% of race time above 15 deg slip |

## What does not (yet)

| finding | evidence | next step |
|---|---|---|
| Strong seed dependence | final shield, nominal: seed 0 16/20, seed 1 1/20 (sliding style the shield cannot catch), seed 2 8/20 (7 stuck); mean 8.3 +- 6.1 vs 3.0 +- 2.4 without a shield; with stall recovery 13.0 +- 8.5 (seed 1 still 1/20) | slip penalty run (`ppo_shield_v2esc_slip_s1`); chicane fine-tuning backfired (E22: 8/20, slides), gentler retry E22b queued |
| Failures concentrate in the chicane | `results/failure_map.png`: 61% of our shield's race-ending events (3 seeds) are in the 2.5 m chicane (84-126 m); seed 2's stuck races are the policy steering into the outer wall at crawling speed | stall recovery (E21) fixed most of it; fine-tuning on the chicane made seed 2 slide (E22) |
| Shield-trained policies lean on the shield | seed 0 with the shield removed: 5/20 finished | shield dropout run (`ppo_shielddrop_s0`) |
| The shielded policy is timid | top speed ~8.4 m/s even on the main straight (E17); the policy, not the shield, caps it | curvature preview (E18, training). A lower intervention penalty made it worse: faster laps but the shield active 35% of the time and 0/20 finished |
| Shield + residual policy at race time | deadlocks (4/20 finished) or slides with the escape (2/20) | would need training the residual policy with the shield |
| The shield reacts too late for a policy that drives at the limit | E24: on seed 1 the predicted clearance shrinks for 6 steps while staying above the 5 cm margin, then braking in the corner spins the car. A stricter slip limit lifts seed 1 from 1/20 to 9-10/20 but costs seed 0 (19 -> 16/20) | a safety/performance dial; possibly train with the stricter shield |
| Car contacts in traffic remain | opponents' future motion is predicted (worst-case braking), not known | - |
| Training efficiency (steps to first clean lap) unchanged | 200k with or without the shield | - |

## Figures

- [failure map](../results/failure_map.png): where on the lap each controller's races end (wall / car / stuck)
- [safety vs speed](../results/tradeoff.png): every controller on one chart (final comparison, seed 0)
- [training curves](../results/training_curves.png): crash rate, shield activity and unshielded solo lap time over training
- [g-g diagrams](../results/gg_diagrams.png): how each controller uses the tyres
- [shield map](../results/shield_map.png): where on the track the shield intervenes
- [telemetry](../results/telemetry_speed.png): speed along a flying lap, per controller

## Videos

`~/Downloads/racing_videos/` on the build machine (not in the repo); regenerate with `python -m scripts.make_videos batchN`.
