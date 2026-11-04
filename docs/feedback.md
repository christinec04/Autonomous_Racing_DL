# Proposal feedback -> what we built -> evidence

The proposal was graded 90/100. This maps each comment to the code that addresses it and the result that tests
it. Numbers are seed 0 unless noted; see [RUNS.md](../RUNS.md) for seeds in progress.

## Introduction (16/20)

> *The metrics are listed without target values.*

Targets are defined in code (`racing/evaluate.py`, `TARGETS`) and checked automatically by `scripts/analyze.py`:

| metric | target | seed 0, nominal | seed 0, randomised |
|---|---|---|---|
| clean-lap time vs PID+APF | <= 0.95x | 0.78x | 0.78x |
| collisions per 10 laps | <= 0.5 | 0.38 | **0.63 (missed)** |
| overtake success | >= 70% | 88% | 85% |
| shield active on race day | <= 10% of steps | 6% | **10.5% (missed)** |
| time above 90% of mu g | >= 10% | 16.7% | 14.6% |
| time above 15 deg body slip | <= 1% | 0.0% | 0.9% |

> *APF with PPO already exists in ResRace and RaceMOP. State what is different about yours.*

The difference, made testable:

| | ResRace / RaceMOP | ours |
|---|---|---|
| role of the APF | base controller; PPO learns a residual on top, so the APF shapes **every** command | a shield; the policy drives, the APF acts **only when the policy's action is predicted unsafe** |
| what decides an intervention | nothing (always on) | an exact-model rollout of the policy's own action plus a braking backup |
| safety layer | none beyond the APF | fallback replaces the action when no blend is predicted safe |

Both are implemented under identical conditions: `EnvConfig(residual=True)` reproduces the ResRace structure
(`final = PID+APF base action + 0.3 x policy`), run `ppo_residual_s0`. Race results (nominal, 20 races x 5 laps):

| controller | finished | clean lap | collisions / 10 laps | passes / race | shield active |
|---|---|---|---|---|---|
| ResRace-style residual PPO | 9/20 | **30.4 s** | 1.77 | 2.75 | - |
| PPO + our shield | 17/20 | 34.3 s | 0.38 | 2.65 | 6% |
| **residual PPO + our shield on top** | **18/20** | 32.7 s | **0.36** | 2.15 (43/43 attempts) | 20% |

The residual structure learns faster laps (the APF base gives it a sensible prior), but the always-on APF does not
make it safe: it crashes in 11 of 20 races, about as often as PID+APF. Our shield is what removes the crashes, and it
also works on top of the residual policy. So the contribution is better stated as **an action-conditioned safety
shield that can wrap any racing policy**, including APF-residual ones like ResRace/RaceMOP, rather than as a
replacement for them. Cost of combining: the shield is active on 20% of steps and the car slides (> 15 deg) 5% of
the time, so two of the six targets are missed.

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

Even the best variant still has car contacts in traffic, because opponents' future motion is predicted, not
known. The defensible claim is "reduces violations; zero only under its model assumptions" (opponents braking no
harder than 6 m/s^2, static world seen by the lidar or the map). Race day: 0.38 collisions / 10 laps with the shield
vs 5.53 without.

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
active on 18% and still prevents every crash. On race day the trained agent's shield is active on 6% of steps.

## Plan (8/10)

> *Add team roles and a risk plan.*

Team roles are for the team to fill in. A risk register built from the risks that actually materialised is in [risks.md](risks.md); details of each are logged with
their fixes in [PROGRESS.md](../PROGRESS.md) ("Problems encountered", 18 entries), which is a ready source for a
risk table (simulator realism, simulator speed, controller stability at 25 Hz, shield model mismatch).

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
