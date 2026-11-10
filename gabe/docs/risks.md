# Risk register (from what actually happened while building)

The Plan feedback asked for a risk plan beyond the compute fallback. These are the technical risks that
materialised, how they were handled in code, and what is still open. Problem numbers refer to
[PROGRESS.md](../PROGRESS.md).

| risk | happened? | impact | mitigation (in code) | still open |
|---|---|---|---|---|
| Simulator not realistic at the limit | yes (4) | stock tyres corner at > 2 g; RL exploits it; grip metric meaningless | friction-circle tyres (`racing/tires.py`), stock kept as an option; slip > 15 deg logged | single-track model has no sliding drag; rear axle saturates first (limit oversteer) |
| Simulator too slow for PPO | yes (3) | 35 steps/s, millions of steps needed | patched lidar ray casting (~10x) | shield predictor costs 2-5x per step when active |
| Classical baseline unstable or unfair | yes (13, 14) | a broken baseline flatters our method | PID redesigned for 25 Hz, APF gains grid-tuned (`scripts/tune_*.py`) | PID+APF finishes only 12/20 races (28/50 on 50 races) |
| Shield model mismatch | yes (7-12) | shield approves unsafe actions or brakes for nothing | exact-model predictor (tested < 2 cm), map walls, conservative opponent braking, loss-of-control check, recursive-feasible fallback | opponents' intent is unknown: car contacts remain |
| Shield cannot guarantee safety | yes (grader comment 1) | claim in the proposal is wrong | claim softened; residual collisions measured on every evaluation | final, seed 0: 0.10 / 0.47 collisions / 10 laps (nominal / randomised); 1.63 +- 2.16 across 3 seeds |
| Policy depends on the shield | yes (step 4) | shield-trained policy finishes only 5/20 races without it | shield dropout (`--shield_prob`, E10): 16/20 with no shield at all | the dropout policy is timid (0.25 passes / race, 42 s laps) |
| Training efficiency metric invalid | yes (grader comment) | shield guarantees clean laps | measure laps with the shield removed | none |
| Results from one seed | yes | can't report variance | 3 training seeds per main configuration (`results/seed_summary.md`) | strong seed dependence: 13.0 +- 8.5 finished; seed 1 slides (1/20). A slip penalty fixed it (17/20, one run); not yet tested on seeds 0 and 2 |
| Too few races to separate controllers | yes (E25) | 19/20 vs 18/20 is not significant | 50-race head-to-head (`results/headtohead50.md`) | ours vs additive shield still not significant on finishing (43/50 vs 39/50) |
| Shield deadlock | yes (22, 23, 26) | the car stops and never moves again; looked like a finish under the old metric | deadlock escape (E19), stall recovery (E21), stuck races counted separately | none seen for seed 0 (0 stuck in 20 races) |
| Simulator artifact after a spin | yes (24) | a car could stay stuck with nothing nearby | post-spin-fixed tyre model `saturated_v2`; all final results re-raced on it | runs trained on the old model are raced on the new one |
| Code changes during long runs | yes (see notes in RUNS.md) | runs mix code versions | provenance in `run_info.json`; behaviour changes are opt-in flags | none |
| Memory pressure on one laptop | yes | background jobs were stopped by the OS | max 2 training runs + 4 eval processes at once | none |
| Compute (proposal's original risk) | partly | about 2 h per run on 7 cores | runs queued in lanes, auto-synced; IU cluster remains a fallback | none |
