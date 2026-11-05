# Proposal feedback -> what we built -> evidence

The proposal was graded 90/100. This maps each comment to the code that addresses it and the result that tests
it. Numbers are seed 0 unless noted; see [RUNS.md](../RUNS.md) for seeds in progress. "Finished" means all 5
laps completed; an earlier version of this page counted stuck races as finished (corrected; PROGRESS.md
problem 22). "Ours (final)" is the shield with the deadlock escape on the post-spin-fixed simulator (E19).

## Introduction (16/20)

> *The metrics are listed without target values.*

Targets are defined in code (`racing/evaluate.py`, `TARGETS`) and checked automatically by `scripts/analyze.py`:

| metric | target | ours (final), nominal | ours (final), randomised | without stall recovery, nominal / randomised |
|---|---|---|---|---|
| clean-lap time vs PID+APF | <= 0.95x | 0.81x | 0.78x | 0.79x / 0.78x |
| collisions per 10 laps | <= 0.5 | 0.10 | 0.47 | 0.44 / **0.75 (missed)** |
| overtake success | >= 70% | 85% | 78% | 86% / 75% |
| shield active on race day | <= 10% of steps | 3% | 4% | 3% / 4% |
| time above 90% of mu g | >= 10% | 16.8% | 15.6% | 17.1% / 15.9% |
| time above 15 deg body slip | <= 1% | 0.0% | 0.0% | 0.0% / 0.0% |

"Ours (final)" = PPO + action-conditioned shield + deadlock escape + stall recovery (E19, E21), seed 0, all on the
post-spin-fixed simulator (`results/final_summary.md`).

Not a target but the most important number: races finished (all 5 laps) - ours (final) 19/20 nominal and 16/20
randomised for seed 0, vs 12/20 for PID+APF, 10/20 for the residual policy, 0/20 for PPO without a shield, and
18/20 for PPO trained with the additive shield, which however laps 13 s slower with twice our collision rate (all on the same simulator,
`results/final_summary.md`). Across three
seeds ours averages 13.0 +- 8.5 finished (seeds 0 and 2: 19/20; seed 1: 1/20, its policy slides), vs 3.0 +- 2.4
without a shield; see `results/seed_summary.md` and E20. Targets above are seed 0 only.

> *APF with PPO already exists in ResRace and RaceMOP. State what is different about yours.*

The difference, made testable:

| | ResRace / RaceMOP | ours |
|---|---|---|
| role of the APF | base controller; PPO learns a residual on top, so the APF shapes **every** command | a shield; the policy drives, the APF acts **only when the policy's action is predicted unsafe** |
| what decides an intervention | nothing (always on) | an exact-model rollout of the policy's own action plus a braking backup |
| safety layer | none beyond the APF | fallback replaces the action when no blend is predicted safe |

Both are implemented under identical conditions: `EnvConfig(residual=True)` reproduces the ResRace structure
(`final = PID+APF base action + 0.3 x policy`), run `ppo_residual_s0`. Race results (nominal, 20 races x 5 laps):

| controller | finished | stuck | clean lap | collisions / 10 laps | passes / race | shield active |
|---|---|---|---|---|---|---|
| ResRace-style residual PPO | 10/20 | 0 | **30.4 s** | 1.60 | 2.20 | - |
| **PPO + our shield (final, with stall recovery)** | **19/20** | 0 | 34.7 s | 0.10 | **3.15** | 3% |
| PPO + our shield (escape, no stall recovery) | 16/20 | 0 | 34.5 s | 0.44 | 2.95 | 3% |
| PPO + our shield (original) | 12/20 | 5 | 34.3 s | 0.38 | 2.65 | 6% |
| residual PPO + our original shield | 4/20 | 14 | 32.7 s | 0.36 | 2.15 | 20% |
| residual PPO + our final shield | 2/20 | 15 | - | 0.52 | 1.70 | 39% |
| residual PPO + our final shield + stall recovery | 2/20 | 14 | - | 0.70 | 1.70 | 37% |

What this says:
- The residual structure learns faster laps (the PID+APF base is a strong prior) but the always-on APF does not
  make it safe: it crashes in 10 of 20 races, more than PID+APF (8 of 20).
- Our shield around a policy trained with it finishes the most races (16/20) with few collisions.
- Simply wrapping our shield around the residual policy at race time does **not** work: collisions drop, but
  the car deadlocks (14-15 of 20 races) and, with the escape enabled, slides heavily. A first version of this page
  claimed the two were complementary; that was based on the faulty "finished" metric and is withdrawn.
- So the contribution statement: **the APF acts as an action-conditioned safety shield around a policy that is
  trained with it, intervening only when the policy's own action is predicted unsafe (3-6% of race steps), instead
  of shaping every command as in ResRace/RaceMOP.** Adding the stall recovery does not help the residual policy either (2/20 finished): its
  stuck races are slides and spins (56% of race time above 15 deg body slip), not nose-to-wall stops. Whether our
  shield can wrap an APF-residual policy therefore needs that policy to be *trained* with the shield: run
  `ppo_residual_shield_s0` (E23, queued).

## Content (16/20)

> *An additive, clipped APF correction (Eq. 2) cannot guarantee no violations, yet Section II says the shield
> does not permit violations.*

Confirmed experimentally, so the claim must be softened. `scripts/shield_stress.py` drives scripted bad policies
(too fast, ignoring traffic, random actions) with each shield and no learning:

| shield (friction-circle tyres) | too-fast solo | ignores traffic | random actions |
|---|---|---|---|
| none | 100% crash | 100% | 100% |
| additive Eq. 2/3, fixed reach | 100% | 100% | 100% |
| action-conditioned + fallback, fixed reach | 0% | 12% | 0% |
| action-conditioned + fallback, grip reach | 0% | 38% | 12% |

The same holds during learning (`results/training_efficiency.md`): PPO trained with the proposal's additive shield
crashed 2286 times in training, no better than with no shield at all (2318-2769), while the action-conditioned
shield cut this to 234-313. On race day the additive-trained policy is safe but timid: 15/20 finished,
0.61 collisions / 10 laps, but 48.8 s clean laps (slower than PID+APF's 43.9 s) and 0.55 passes per race, vs
ours 16/20, 34.5 s and 2.95 passes. This is the "APF makes the car timid" failure the proposal predicted, and the
clearest case for making the shield action-conditioned.

Even the best variant still has car contacts in traffic, because opponents' future motion is predicted, not
known. The defensible claim is "reduces violations; zero only under its model assumptions" (opponents braking no
harder than 6 m/s^2, static world seen by the lidar or the map). Race day: 0.44 collisions / 10 laps with the final
shield (0.38 original) vs 5.53 without. The shield also introduced a failure the proposal did not anticipate:
deadlock (the car stopped and never released), fixed by the escape rule (E19).

> *Section II says the shield reach depends on the grip left after cornering, but Section III-C uses braking
> distance with a fixed assumed deceleration.*

Both are implemented and compared (`ShieldConfig(reach="fixed" | "grip")`). Making "grip left over" meaningful
required fixing the simulator first: stock F1TENTH tyres have no grip limit (we measured ~24 m/s^2 of lateral
acceleration at 8 m/s against mu g = 10.3), so we added a friction-circle tyre model (`racing/tires.py`) and
traction control. With that, grip reach = `sqrt((mu g)^2 - (v yaw_rate)^2)`, consistent with the tyre model the car
actually has. Finding so far: fixed 6 m/s^2 is more conservative and safer in traffic (12% vs 38% crashes in the
traffic stress test); grip reach lets the car go further when it is safe to. The trained agent uses grip reach.

> *w(d) in Eq. 3 depends only on obstacle distance and speed, never on the agent action, which does not match
> "the APF steps in only when the policy action is unsafe".*

The `conditioned` shield makes the decision depend on the action: it simulates the policy's action (then a
braking backup) with the simulator's own vehicle model and intervenes only if that rollout hits something or loses
control. Effect, stock tyres, too-fast driver: additive shield active on 98% of steps; action-conditioned shield
active on 18% and still prevents every crash. On race day the trained agent's shield is active on 3-6% of steps.

## Plan (8/10)

> *Add team roles and a risk plan.*

Team roles are for the team to fill in. A risk register built from the risks that actually materialised is in
[risks.md](risks.md); details of each are logged with their fixes in [PROGRESS.md](../PROGRESS.md)
("Problems encountered", 24 entries).

> *Training steps to first clean lap will not test training efficiency because the shield keeps laps free of
> collisions, and the training of the unshielded ablation is not defined given that curriculum stage 1 has the
> shield on.*

- The unshielded ablation is defined as **the same curriculum with the shield off in every stage**
  (`--shield off`), so stage 1 is not shielded for it.
- Training efficiency is measured with the shield **removed**: every 50k steps the policy drives one solo lap
  without the shield (`eval_log.csv`, column `unshielded_clean`). The shield cannot make this look better.
- Result (seed 0): both reach their first clean unshielded lap at 200k steps, so the shield did not speed up
  learning to lap. It did change what was learned: the shielded agent overtakes far more (2.65 vs 1.05 passes per
  race) but relies on the shield (with it removed, it crashes in 15/20 races). A shield-dropout run
  (`ppo_shielddrop_s0`: shield on in 100% / 50% / 25% of episodes per stage) tests whether the policy can be made
  safe on its own.
- Crashes during training: stage 1 ~1% of episodes with the shield vs 25% without; stage 2 9% vs 46%.
- Training-time safety is where the shield pays off (`results/training_efficiency.md`): 8-9 crashes before the
  first clean lap with the shield vs about 1000 without, and about 10x fewer crashes over all of training.
  The proposal's "steps to first clean lap" metric would have missed this; crashes-during-training captures it.
