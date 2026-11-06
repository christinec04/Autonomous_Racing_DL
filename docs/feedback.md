# Proposal feedback -> what we built -> evidence

The proposal was graded 90/100. This maps each comment to the code that addresses it and the result that tests
it. Numbers are seed 0 unless noted. "Finished" means all 5 laps completed; an earlier version of this page
counted stuck races as finished (corrected; PROGRESS.md problem 22). "Ours (final)" is PPO trained with the
action-conditioned shield, raced with the shield, its deadlock escape (E19) and the stall recovery (E21) on the
post-spin-fixed simulator. Current results in one place: [results.md](results.md).

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
post-spin-fixed simulator (`results/final_summary.md`). On 50 race seeds (E25, `results/headtohead50.md`) ours finishes 43/50
nominal and 35/50 randomised, vs 39/50 and 34/50 for the additive shield (not significant) and 28/50 and 25/50 for
PID+APF; the 20-race finish counts below are on the optimistic side.

Not a target but the most important number: races finished (all 5 laps) - ours (final) 19/20 nominal and 16/20
randomised for seed 0, vs 12/20 for PID+APF, 10/20 for the residual policy, 0/20 for PPO without a shield, and
18/20 for PPO trained with the additive shield, which however laps 13 s slower with twice our collision rate (all on the same simulator,
`results/final_summary.md`). Across three
seeds ours averages 13.0 +- 8.5 finished (seeds 0 and 2: 19/20; seed 1: 1/20, its policy slides), vs 3.0 +- 2.4
without a shield; see `results/seed_summary.md` and E20. Seed 1 retrained with a slip penalty and the escape shield
from the start (`ppo_shield_v2esc_slip_s1`, raced without the stall recovery) finishes 17/20 nominal (0.22 collisions / 10 laps,
32.5 s laps) and 13/20 randomised; it is not in the 3-seed means. Seeds 0 and 2 with this recipe are training (E26).
Targets above are seed 0 only, 20 races: over the 50-race set (E25) ours has 0.31 collisions / 10 laps nominal but 0.77
randomised, which misses the <= 0.5 target.

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
| PPO + our shield (original, v1 simulator) | 12/20 | 5 | 34.3 s | 0.38 | 2.65 | 6% |
| residual PPO + our original shield (v1 simulator) | 4/20 | 14 | 32.7 s | 0.36 | 2.15 | 20% |
| residual PPO + our final shield | 2/20 | 15 | - | 0.52 | 1.70 | 39% |
| residual PPO + our final shield + stall recovery | 2/20 | 14 | - | 0.70 | 1.70 | 37% |
| **residual PPO trained with our shield** (E23) | 15/20 | 0 | 32.1 s | 0.59 | 3.15 | 6% |

What this says:
- The residual structure learns faster laps (the PID+APF base is a strong prior) but the always-on APF does not
  make it safe: it crashes in 10 of 20 races, more than PID+APF (8 of 20).
- Our shield around a policy trained with it finishes the most races (19/20, 0.10 collisions / 10 laps). On 50
  races (E25) it finishes 43/50 nominal, not significantly more than the additive shield (39/50) or the residual
  policy trained with our shield (39/50), and more than PID+APF (28/50, p = 0.002).
- Simply wrapping our shield around the residual policy at race time does **not** work: collisions drop, but
  the car deadlocks (14-15 of 20 races) and, with the escape enabled, slides heavily. A first version of this page
  claimed the two were complementary; that was based on the faulty "finished" metric and is withdrawn.
- So the contribution statement: **the APF acts as an action-conditioned safety shield around a policy that is
  trained with it, intervening only when the policy's own action is predicted unsafe (3-4% of race steps for seed 0; 9.0 +- 9.5% across 3 seeds), instead
  of shaping every command as in ResRace/RaceMOP.** Adding the stall recovery does not help the residual policy either (2/20 finished): its
  stuck races are slides and spins, not nose-to-wall stops. **Training** the residual policy with the shield does
  work (E23): 15/20 finished, 0.59 collisions / 10 laps, 32.1 s laps and 3.15 passes per race, vs 10/20 and 1.60
  for the unshielded residual policy; on 50 races it finishes 39/50 nominal and 37/50 randomised, a tie with ours,
  while lapping 2.5 s faster (`results/headtohead50.md`). So the ResRace structure and our shield are complementary, provided the
  policy is trained with the shield, which is itself part of our contribution: the shield shapes what the policy
  learns, not only what the car does.

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
crashed 2333 times in training, no better than with no shield at all (2295-2769, 3 seeds), while the
action-conditioned shield cut this to 96-313 (3 seeds). On race day the additive-trained policy is safe but timid:
18/20 finished, 0.21 collisions / 10 laps, but 47.6 s clean laps (slower than PID+APF's 42.8 s) and 0.85 passes per
race, vs ours 19/20, 34.7 s and 3.15 passes (`results/final_summary.md`). On 50 races the two finish about equally
often (39/50 vs 43/50, p = 0.44), and ours keeps the 12 s and 2.7x passes advantage (p = 1e-8, nominal; E25). This is the "APF makes the car timid" failure the proposal predicted, and the
clearest case for making the shield action-conditioned.

Even the best variant still has car contacts in traffic, because opponents' future motion is predicted, not
known. The defensible claim is "reduces violations; zero only under its model assumptions" (opponents braking no
harder than 6 m/s^2, static world seen by the lidar or the map). Race day, seed 0: 0.10 collisions / 10 laps for
ours (final) vs 7.35 without a shield; across 3 training seeds 1.63 +- 2.16 vs 4.38 +- 2.12. The shield also
introduced a failure the proposal did not anticipate: deadlock (the car stopped and never released), fixed by the
escape rule (E19); stops caused by the policy itself in the chicane are handled by the stall recovery (E21). The
shield also reacts too late for a policy that slides at the limit (seed 1, E24); stricter settings help that
policy but cost the clean one, so they are a safety/performance dial, not a fix.

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
control. Effect, stock (linear) tyres, too-fast driver (`results/shield_stress_linear.json`): additive shield active
on 98% of steps; action-conditioned shield active on 18% and still prevents every crash. On race day the trained
agent's shield is active on 3-4% of steps for seed 0 (final), but this depends on the seed: seed 1 22%, 3-seed mean
9.0 +- 9.5%.

## Plan (8/10)

> *Add team roles and a risk plan.*

Team roles are for the team to fill in. A risk register built from the risks that actually materialised is in
[risks.md](risks.md); details of each are logged with their fixes in [PROGRESS.md](../PROGRESS.md)
("Problems encountered", 33 entries).

> *Training steps to first clean lap will not test training efficiency because the shield keeps laps free of
> collisions, and the training of the unshielded ablation is not defined given that curriculum stage 1 has the
> shield on.*

- The unshielded ablation is defined as **the same curriculum with the shield off in every stage**
  (`--shield off`), so stage 1 is not shielded for it.
- Training efficiency is measured with the shield **removed**: every 50k steps the policy drives one solo lap
  without the shield (`eval_log.csv`, column `unshielded_clean`). The shield cannot make this look better.
- Result (seed 0, original simulator): both reach their first clean unshielded lap at 200k steps, so the shield did not speed up
  learning to lap. It did change what was learned: the shielded agent overtakes far more (2.65 vs 1.05 passes per
  race) but relies on the shield (with it removed, it finishes only 5/20 races). A shield-dropout run
  (`ppo_shielddrop_s0`: shield on in 100% / 50% / 25% of episodes per stage) makes it safe on its own: 16/20
  finished and 0.45 collisions / 10 laps with no shield at all, at half the unshielded training crashes, but it
  passes almost nobody (0.25 per race) and laps 8 s slower (E10).
- Crashes during training: stage 1 ~1% of episodes with the shield vs 25% without; stage 2 9% vs 46%.
- Training-time safety is where the shield pays off (`results/training_efficiency.md`, 3 seeds each): 8-11 crashes
  before the first clean lap with the shield vs about 1000 without, and about 10x fewer crashes over all of training.
  The proposal's "steps to first clean lap" metric would have missed this; crashes-during-training captures it.
