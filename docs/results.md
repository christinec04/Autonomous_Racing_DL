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
| The deadlock escape removes stuck races | E19: seed 0 from 5-8 stuck to 0; 16/20 races finished (best of all controllers) |
| Action-conditioned beats additive as a training shield | PPO trained with the proposal's additive shield: 15/20 finished but 48.8 s laps, 0.55 passes / race (timid); ours 16/20, 34.5 s, 2.95 passes |
| Learned driving beats classical | seed 0 clean laps 34.5 s vs 43.9 s PID+APF; residual PPO 30.4 s |
| Friction-limited tyres close the sliding loophole | stock tyres corner at 2.4 g; with ours, seed 0 spends 0% of race time above 15 deg slip |

## What does not (yet)

| finding | evidence | next step |
|---|---|---|
| Strong seed dependence | final shield: seed 0 16/20 finished, seed 1 1/20 (sliding style the shield cannot catch) | seed 2 training; slip penalty run (`ppo_shield_v2esc_slip_s1`) |
| Shield-trained policies lean on the shield | seed 0 with the shield removed: 5/20 finished | shield dropout run (`ppo_shielddrop_s0`) |
| The shielded policy is timid | top speed ~8.4 m/s even on the main straight (E17); the policy, not the shield, caps it | lower intervention penalty, curvature preview (E18) |
| Shield + residual policy at race time | deadlocks (4/20 finished) or slides with the escape (2/20) | would need training the residual policy with the shield |
| Car contacts in traffic remain | opponents' future motion is predicted (worst-case braking), not known | - |
| Training efficiency (steps to first clean lap) unchanged | 200k with or without the shield | - |

## Figures

- [training curves](../results/training_curves.png): crash rate, shield activity and unshielded solo lap time over training
- [g-g diagrams](../results/gg_diagrams.png): how each controller uses the tyres
- [shield map](../results/shield_map.png): where on the track the shield intervenes
- [telemetry](../results/telemetry_speed.png): speed along a flying lap, per controller

## Videos

`~/Downloads/racing_videos/` on the build machine (not in the repo); regenerate with `python -m scripts.make_videos batchN`.
