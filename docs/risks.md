# Risk register (from what actually happened while building)

The Plan feedback asked for a risk plan beyond the compute fallback. These are the technical risks that
materialised, how they were handled in code, and what is still open. Problem numbers refer to
[PROGRESS.md](../PROGRESS.md).

| risk | happened? | impact | mitigation (in code) | still open |
|---|---|---|---|---|
| Simulator not realistic at the limit | yes (4) | stock tyres corner at > 2 g; RL exploits it; grip metric meaningless | friction-circle tyres (`racing/tires.py`), stock kept as an option; slip > 15 deg logged | single-track model has no sliding drag; rear axle saturates first (limit oversteer) |
| Simulator too slow for PPO | yes (3) | 35 steps/s, millions of steps needed | patched lidar ray casting (~10x) | shield predictor costs 2-5x per step when active |
| Classical baseline unstable or unfair | yes (13, 14) | a broken baseline flatters our method | PID redesigned for 25 Hz, APF gains grid-tuned (`scripts/tune_*.py`) | PID+APF still DNFs 8-11 of 20 races |
| Shield model mismatch | yes (7-12) | shield approves unsafe actions or brakes for nothing | exact-model predictor (tested < 2 cm), map walls, conservative opponent braking, loss-of-control check, recursive-feasible fallback | opponents' intent is unknown: car contacts remain |
| Shield cannot guarantee safety | yes (grader comment 1) | claim in the proposal is wrong | claim softened; residual collisions measured on every evaluation | 0.38-0.63 collisions / 10 laps |
| Policy depends on the shield | yes (step 4) | shield-trained policy crashes 15/20 races without it | shield dropout experiment (`--shield_prob`) | result pending |
| Training efficiency metric invalid | yes (grader comment) | shield guarantees clean laps | measure laps with the shield removed | none |
| Results from one seed | yes | can't report variance | seeds 1-2 queued (3 per configuration) | running |
| Code changes during long runs | yes (see notes in RUNS.md) | runs mix code versions | provenance in `run_info.json`; behaviour changes are opt-in flags | none |
| Memory pressure on one laptop | yes | background jobs were stopped by the OS | max 2 training runs + 4 eval processes at once | none |
| Compute (proposal's original risk) | partly | about 2 h per run on 7 cores | runs queued in lanes, auto-synced; IU cluster remains a fallback | none |
