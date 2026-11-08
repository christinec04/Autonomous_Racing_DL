# Current results (living page)

Updated as runs finish. Raw tables: [results/final_summary.md](../results/final_summary.md) (seed 0, every
controller, one simulator version, targets and Mann-Whitney tests), [results/headtohead50.md](../results/headtohead50.md)
(50 races per condition), [results/seed_summary.md](../results/seed_summary.md) (3 training seeds),
[results/training_efficiency.md](../results/training_efficiency.md). Experiment details: [experiments.md](experiments.md).

"Ours (final)" = PPO trained with the action-conditioned shield (`cond_fb_grip`), raced with the shield, its deadlock
escape (E19) and the stall recovery (E21) on the post-spin-fixed v2 simulator (eval label `ppo_apf_rec@s0`).
Numbers are seed 0, nominal, 20 races x 5 laps unless noted.

## What works

| finding | evidence |
|---|---|
| Final comparison (one simulator version) | `results/final_summary.md`: ours 19/20 finished, 34.7 s laps, 0.10 collisions / 10 laps, 3.15 passes, all 6 targets met nominal and randomised on these 20 races (over 50 races the randomised collision rate is 0.77 / 10 laps, missing the <= 0.5 target; nominal 0.31); additive-shield PPO 18/20 but 47.6 s laps; PID+APF 12/20; residual 10/20; no shield 0/20; Pure Pursuit 0/20 |
| The result holds on 50 races, with a smaller margin | E25, `results/headtohead50.md`: ours 43/50 nominal, 35/50 randomised; additive shield 39/50, 34/50 (no significant difference, p = 0.44 nominal); PID+APF 28/50, 25/50 (p = 0.002 nominal); ours 12 s faster than the additive shield with 2.7x the passes (p = 1e-8, nominal) |
| The action-conditioned shield prevents crashes that an additive APF (proposal Eq. 2/3) cannot | stress test E4 (friction-circle tyres): additive 100% crash in every scripted scenario; conditioned + fallback 0% / 12% / 0% (too fast / traffic / random) with fixed reach, 0% / 38% / 12% with grip reach (what the agent uses) |
| Action-conditioned beats additive as a training shield | PPO trained with the proposal's additive shield finishes about as often (18/20, 39/50) but is timid: 47.6 s laps and 0.85 passes / race, vs ours 34.7 s and 3.15 |
| Shielded training is ~10x safer | E16: 96-313 vs 2295-2769 training crashes (3 seeds each); 8-11 vs about 1000 crashes before the first clean lap; the proposal's additive shield: 2333, no better than none |
| The shield lowers race collisions | seed 0: 0.10 vs 7.35 collisions / 10 laps without a shield; 3 seeds: 1.63 +- 2.16 vs 4.38 +- 2.12 |
| The shield intervenes rarely once trained | seed 0: 3% of race steps nominal, 4% randomised, vs 89-93% for the always-on APF in PID+APF. Seed-dependent: seed 1 22%; 3-seed mean 9.0 +- 9.5% |
| The deadlock escape removes stuck races | E19: seed 0 from 5-8 stuck to 0; 16/20 finished before the stall recovery was added |
| Stall recovery fixes the chicane stops | E21: seeds 0 and 2 finish 19/20 (from 16 and 8), 0.10 collisions / 10 laps each; chicane failures 46 -> 17 (3 seeds, nominal + randomised) |
| Residual policy + our shield work together when trained together | E23: seeds 0 / 1 finish 15 / 16 of 20 (17 / 16 randomised), seed 0: 0.59 collisions / 10 laps, 32.1 s laps, 3.15 passes, vs 10/20 and 1.60 for the residual policy without the shield; on 50 races 39/50 nominal and 37/50 randomised, a tie with ours (E25) |
| A slip penalty fixes the sliding seed 1 | `ppo_shield_v2esc_slip_s1` (`--w6 1`, escape shield and v2 simulator from the start; raced with the escape shield, no stall recovery; `results/eval_ppo_shield_v2esc_slip_s1.json`): 17/20 finished nominal (1 stuck), 13/20 randomised (4 stuck), 0.22 / 0.38 collisions / 10 laps, 32.5 s laps, 0.4% of time above 15 deg slip; with the stall recovery 18/20 nominal, 17/20 randomised, 0.11 collisions / 10 laps (`results/eval_slip_rec_slip_s1.json`); seed 1 before: 1/20, 4.91 collisions. Two things changed at once (slip penalty, shield and simulator during training); one seed only |
| Final controller: residual PPO trained with our shield | E29: 3 seeds x 50 races, 122/150 finished nominal (81%), 116/150 randomised (77%), vs PID+APF 28/50 and 25/50 (p < 0.001); 32.2 s laps, 3.7 passes / race; meets 5 of 6 targets nominal (misses time above 90% of mu g: 8.8%) |
| The final controller generalises best | Track2, 3 seeds (E29): residual + shield 18.3 / 16.3 of 20 finished (nominal / randomised), 31.2 s, 3.8 passes; plain PPO + shield 16.7 / 14.0, 37.5 s, 1.2 passes (one seed 5/20 randomised, one never passes); stall recovery barely matters for it (+1 randomised finish in 20) |
| Shielded learned policies generalise to an unseen track | E28 (Track2, 20 races): slip-penalty PPO 19/20, 32.2 s, 0.10 collisions; residual + shield 17/20, 31.3 s; ours seed 0 16/20, 36.7 s; PID+APF 15/20, 39.3 s; no shield 1/20 |
| Our shield composes with a classical controller; the additive one does not | E32: PID+APF + our shield, no learning (`results/eval_zero_residual.json`): 20/20 finished, 0 collisions (16/20, 0.47 randomised), 42.5 s laps; PID+APF + the additive Eq. 2/3 shield: 0/20, 68 collisions / 10 laps (two APF fields stack). The residual policy trained with the additive shield therefore fails (0-1/20, 4845-5717 training crashes) while the one trained with ours is the final controller |
| The final controller corners harder instead of braking harder | `results/grip_use.md`, Fig. 6: residual + shield corners above 0.6 mu g 14% of the time (PPO + shield 5%, PID+APF 5%) and brakes harder than 0.5 mu g 14% (PPO + shield 31%, with a bang-bang throttle clipped by traction control). The 'time above 90% of mu g' target rewards that throttle |
| Learned driving beats classical | seed 0 clean laps 34.7 s (ours) vs 42.8 s PID+APF; residual PPO 30.4 s |
| Curvature preview gives a small gain | E18: raced with the final setup 17/20, 0.22 collisions, 3.80 passes / race vs ours 19/20, 0.10, 3.15; solo lap 31.2 s vs 32.7 s. Comparable, not clearly better, one seed |
| Training with the escape shield from the start gives the same picture | `ppo_shield_v2esc_s0` (escape shield, v2 sim from step 0, no stall recovery): 14/20 finished, 1 stuck, 0.62 collisions / 10 laps, 3.45 passes / race |
| Friction-limited tyres close the grip loophole | stock tyres corner at 2.4 g. E27: the same recipe trained on stock tyres laps 5 s faster (29.3 s) by cornering above 100% of mu g for 9.7% of the race; with friction-circle tyres 0%, and seed 0 spends 0% of race time above 15 deg slip |

## What does not (yet)

| finding | evidence | next step |
|---|---|---|
| Strong seed dependence | final setup, nominal: seeds 0 and 2 19/20, seed 1 1/20 (sliding style the shield cannot catch); mean 13.0 +- 8.5 vs 3.0 +- 2.4 without a shield | the slip penalty fixed seed 1 (18/20) but hurt seed 0 (11/20 vs 19/20, E26); residual PPO trained with the shield is consistent across seeds: 16.0 +- 0.8 finished, 0.47 +- 0.10 collisions, 32.2 s (E23, 3 seeds) |
| Fine-tuning on the chicane backfired | E22: seed 2 fine-tuned on chicane starts learned to slide, 19/20 -> 8/20 (with recovery); E22b, a gentler retry (lr 5e-5, slip penalty): 16/20 | none; the stall recovery handles the chicane better |
| Failures concentrate in the chicane | `results/failure_map.png`: 61% of our shield's race-ending events (3 seeds) are in the 2.5 m chicane (84-126 m); seed 2's stuck races were the policy steering into the outer wall at crawling speed | stall recovery (E21) fixed most of it |
| Shield-trained policies lean on the shield | seed 0 with the shield removed: 5/20 finished. Shield dropout (E10) makes it safe on its own (16/20, 0.45 collisions with no shield at all) but timid: 0.25 passes / race, 42 s laps | dropout with a pass reward boost, or a dropout schedule that ends higher |
| The shielded policy is timid | top speed ~8.4 m/s even on the main straight (E17); the policy, not the shield, caps it. E18: a lower intervention penalty (w3 = 0.02) made it worse: faster laps but the shield active 35% of the time and 0/20 finished. Curvature preview helps only a little | - |
| Shield added to a residual policy only at race time | deadlocks (4/20 finished) or slides (2/20), with or without the stall recovery | train it with the shield: done, E23 (15/20); seeds 1-2 running |
| The shield reacts too late for a policy that drives at the limit | E24: on seed 1 the predicted clearance shrinks for 6 steps while staying above the 5 cm margin, then braking in the corner spins the car. Stricter settings lift seed 1 from 1/20 to 9-10/20 but cost seed 0 (19 -> 16/20) | a safety/performance dial; the final setup keeps the original settings |
| 20 races cannot separate close controllers | 19/20 vs 18/20 (ours vs additive) is not significant; on 50 races ours 43/50 vs 39/50, still not significant (E25) | use the 50-race numbers for finishing rates |
| Car contacts in traffic remain | E34 (`results/contacts.md`): 60 of the final controller's 62 DNFs in 300 races are car contacts, half in the first half lap; of seed 0's 24, 15 are cutting back in after a pass, 5 side-by-side squeezes, 4 rear-ends; the shield intervened before all of them. It predicts opponents braking at 6 m/s^2, the best case for a car just passed | checking both braking and holding speed (`opp_both`, E34) cuts car contacts from 60 to 25 in 300 races but adds 15 wall hits; a relaxed version (`opp_relax`) is running |
| Below the training friction the final controller loses its lead | E33: at x0.8 it finishes 52% of races (PPO + shield 85%, PID+APF 50%) and slides above 15 deg 4-8% of the time. Telling the shield the true friction lifts it to 83% (p = 4e-4) and does nothing for plain PPO, so the shield's nominal friction model is the weak point | estimate friction online for the shield's predictor |
| Missed grip target | the final controller spends 8.8% of the race above 90% of mu g (target 10%) | the target measures throttle style, not cornering (row above); report cornering grip instead |
| Training efficiency (steps to first clean lap) unchanged | 150-200k with or without the shield (3 seeds each); the shield's gain is in crashes during training (above) | - |

## Running now

Restarted after the laptop shut down on Nov 8 (PROGRESS 38).

- Lane R (`scripts/queue_lane_r.sh`): x0.7 with the true friction (E33), the relaxed two-hypothesis check
  (`opp_relax`, E34, 3 seeds x 50 races), then the remaining stress tests (5 and 1 opponents, x0.6, x1.3).
- Lane S (`scripts/queue_lane_s.sh`, E35): the shield estimates the friction online, final controller at x0.8,
  x0.7 and on the main protocol.
- Lane Q (`scripts/queue_lane_q.sh`): residual baseline seed 2, trained from scratch, raced on Singapore and Track2.

Status: [RUNS.md](../RUNS.md).

## Figures

- [grip use](../results/grip_use.png): g-g diagrams, PID+APF vs PPO + shield vs final controller (`python -m scripts.plot_grip`)
- [seed spread](../results/seed_spread.png): races finished per training seed for each recipe (why the final controller was chosen; `python -m scripts.plot_seeds`)
- [failure map](../results/failure_map.png): where on the lap each controller's races end (wall / car / stuck)
- [safety vs speed](../results/tradeoff.png): every controller on one chart (final comparison, seed 0)
- [training curves](../results/training_curves.png): crash rate, shield activity and unshielded solo lap time over training
- [g-g diagrams](../results/gg_diagrams.png): how each controller uses the tyres
- [shield map](../results/shield_map.png): where on the track the shield intervenes
- [telemetry](../results/telemetry_speed.png): speed along a flying lap, per controller
- report figures: `report/figs/` (`python -m scripts.report_figs`)

## Videos

`~/Downloads/racing_videos/` on the build machine (not in the repo); regenerate with `python -m scripts.make_videos batchN`.
