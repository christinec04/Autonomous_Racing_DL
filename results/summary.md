# Race results

Sources: `eval_baselines.json`, `eval_ppo_s0.json`, `eval_residual_s0.json`. 20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 (lap 1 is a standing start).

## nominal

| controller | finished | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|
| PPO + shield (ours) | 17/20 | 34.32 | 32.64 | 0.38 (0, 3) | 2.65 | 88% (53/60) | 6% | 16.7% | 0.0% |
| PPO, no shield | 2/20 | 36.82 | 28.24 | 5.53 (18, 0) | 1.05 | 72% (21/29) | 0% | 31.9% | 1.6% |
| shield-trained PPO, shield removed | 5/20 | 34.94 | 32.44 | 4.72 (7, 8) | 1.00 | 62% (20/32) | 0% | 17.2% | 0.0% |
| unshielded PPO + shield at race time | 20/20 | 36.66 | 30.56 | 0.00 (0, 0) | 1.25 | 81% (25/31) | 16% | 29.4% | 2.4% |
| residual PPO on PID+APF (ResRace-style) | 9/20 | 30.35 | 29.20 | 1.77 (3, 8) | 2.75 | 93% (55/59) | 0% | 12.8% | 1.4% |
| PID + APF | 9/20 | 43.91 | 36.04 | 1.75 (4, 7) | 1.25 | 66% (25/38) | 93% | 2.5% | 0.6% |
| Pure Pursuit | 0/20 | - | - | 61.35 (0, 20) | 0.00 | - (0/0) | 0% | 11.8% | 0.0% |

Targets for PPO + shield (ours) (nominal):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.782 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.382 | <= 0.5 | yes |
| PPO+APF completed passes / attempts | 0.883 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.061 | <= 0.1 | yes |
| fraction of time above 90% of mu*g (uses the grip) | 0.167 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.000 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield (ours) vs each controller (per-race values):

| vs | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|
| PPO, no shield | 2.95e-06 | 0.00232 | 0.000921 | 0.793 |
| shield-trained PPO, shield removed | 0.000177 | 0.00233 | 0.00364 | 0.563 |
| unshielded PPO + shield at race time | 0.0804 | 0.00592 | 0.0028 | 0.719 |
| residual PPO on PID+APF (ResRace-style) | 0.00926 | 0.869 | 0.0499 | 5.66e-06 |
| PID + APF | 0.00926 | 0.00829 | 0.0859 | 2.16e-05 |
| Pure Pursuit | 8.64e-08 | 3.28e-07 | 6.8e-08 | - |

## randomized

| controller | finished | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|
| PPO + shield (ours) | 16/20 | 34.49 | 32.44 | 0.63 (2, 2) | 2.50 | 85% (50/59) | 10% | 14.6% | 0.9% |
| PPO, no shield | 1/20 | 35.71 | 26.88 | 6.75 (18, 1) | 1.10 | 79% (22/28) | 0% | 27.7% | 2.7% |
| shield-trained PPO, shield removed | 6/20 | 34.51 | 32.24 | 3.54 (7, 7) | 1.45 | 69% (29/42) | 0% | 14.0% | 0.1% |
| unshielded PPO + shield at race time | 18/20 | 32.29 | 30.36 | 0.97 (2, 0) | 1.05 | 88% (21/24) | 24% | 23.1% | 3.3% |
| residual PPO on PID+APF (ResRace-style) | 8/20 | 30.28 | 28.92 | 2.10 (6, 6) | 1.90 | 93% (38/41) | 0% | 12.7% | 1.3% |
| PID + APF | 12/20 | 44.02 | 35.48 | 1.18 (2, 6) | 1.40 | 70% (28/40) | 93% | 2.3% | 0.8% |
| Pure Pursuit | 0/20 | - | - | 61.52 (0, 20) | 0.00 | - (0/0) | 0% | 8.5% | 0.0% |

Targets for PPO + shield (ours) (randomized):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.783 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.634 | <= 0.5 | no |
| PPO+APF completed passes / attempts | 0.847 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.105 | <= 0.1 | no |
| fraction of time above 90% of mu*g (uses the grip) | 0.146 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.009 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield (ours) vs each controller (per-race values):

| vs | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|
| PPO, no shield | 2.34e-06 | 0.0101 | 0.0207 | 0.202 |
| shield-trained PPO, shield removed | 0.00179 | 0.0554 | 0.0439 | 0.183 |
| unshielded PPO + shield at race time | 0.394 | 0.0073 | 0.00397 | 0.102 |
| residual PPO on PID+APF (ResRace-style) | 0.0113 | 0.248 | 0.543 | 1.65e-05 |
| PID + APF | 0.178 | 0.0386 | 0.695 | 5.07e-05 |
| Pure Pursuit | 3.71e-07 | 1.05e-06 | 7.9e-08 | - |
