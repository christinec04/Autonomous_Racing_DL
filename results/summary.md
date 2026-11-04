# Race results

Sources: `final_v2_others.json`, `eval_escape_v4.json`, `eval_escape_v4_s1.json`. 20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 (lap 1 is a standing start).

## nominal

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO + shield with deadlock escape (ours, final; v2 sim) | 16/20 | 0 | 34.47 | 32.64 | 0.44 (3, 1) | 2.95 | 86% (59/69) | 3% | 17.1% | 0.0% |
| PPO + final shield (seed 1) | 1/20 | 2 | 37.12 | 31.16 | 4.91 (14, 3) | 1.70 | 69% (34/49) | 20% | 41.6% | 9.1% |
| PPO, no shield (seed 0) | 0/20 | 1 | 32.50 | 28.32 | 7.35 (18, 1) | 1.35 | 90% (27/30) | 0% | 32.1% | 1.9% |
| PPO, no shield (seed 1) | 3/20 | 0 | 34.89 | 32.08 | 3.23 (14, 3) | 2.15 | 91% (43/47) | 0% | 41.0% | 0.1% |
| PPO + shield, original, on v2 sim | 11/20 | 8 | 34.61 | 32.68 | 0.14 (0, 1) | 2.10 | 74% (42/57) | 8% | 16.7% | 0.0% |
| residual PPO on PID+APF (ResRace-style) | 10/20 | 0 | 30.37 | 29.20 | 1.60 (1, 9) | 2.20 | 81% (44/54) | 0% | 12.3% | 1.6% |
| PPO + additive Eq.2/3 shield | 18/20 | 0 | 47.57 | 40.44 | 0.21 (2, 0) | 0.85 | 71% (17/24) | 7% | 8.5% | 0.0% |
| PID + APF | 12/20 | 0 | 42.84 | 36.00 | 1.09 (3, 5) | 1.35 | 66% (27/41) | 89% | 2.4% | 0.6% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.35 (0, 20) | 0.00 | - (0/0) | 0% | 11.8% | 0.0% |
| residual PPO + escape shield (v2 sim) | 2/20 | 15 | 102.09 | 31.36 | 0.52 (0, 3) | 1.70 | 94% (34/36) | 39% | 61.7% | 60.6% |

Targets for PPO + shield with deadlock escape (ours, final; v2 sim) (nominal):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.805 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.443 | <= 0.5 | yes |
| PPO+APF completed passes / attempts | 0.855 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.032 | <= 0.1 | yes |
| fraction of time above 90% of mu*g (uses the grip) | 0.171 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.000 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield with deadlock escape (ours, final; v2 sim) vs each controller (per-race values):

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| PPO + final shield (seed 1) | 2.34e-06 | 5.15e-05 | 0.00104 | 3.71e-05 | 0.491 |
| PPO, no shield (seed 0) | 3.71e-07 | 2.34e-06 | 0.000118 | 2.06e-06 | - |
| PPO, no shield (seed 1) | 5.15e-05 | 5.15e-05 | 0.0608 | 0.00123 | 0.0325 |
| PPO + shield, original, on v2 sim | 0.0989 | 0.164 | 0.0472 | 0.144 | 0.79 |
| residual PPO on PID+APF (ResRace-style) | 0.0515 | 0.0515 | 0.0872 | 0.0179 | 1.86e-06 |
| PPO + additive Eq.2/3 shield | 0.394 | 0.394 | 9.32e-06 | 0.409 | 2.21e-07 |
| PID + APF | 0.178 | 0.178 | 0.000866 | 0.0499 | 4.03e-06 |
| Pure Pursuit | 3.71e-07 | 3.71e-07 | 6.76e-09 | 6.8e-08 | - |
| residual PPO + escape shield (v2 sim) | 1.2e-05 | 0.696 | 0.00392 | 5.25e-05 | 0.00115 |

## randomized

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO + shield with deadlock escape (ours, final; v2 sim) | 14/20 | 0 | 34.36 | 32.40 | 0.75 (3, 3) | 2.60 | 75% (52/69) | 4% | 15.9% | 0.0% |
| PPO + final shield (seed 1) | 1/20 | 2 | 32.46 | 30.48 | 6.18 (16, 1) | 1.20 | 60% (24/40) | 17% | 31.1% | 2.8% |
| PPO, no shield (seed 0) | 1/20 | 0 | 38.42 | 28.96 | 7.13 (19, 0) | 0.95 | 70% (19/27) | 0% | 27.3% | 2.4% |
| PPO, no shield (seed 1) | 4/20 | 0 | 34.36 | 32.72 | 3.48 (15, 1) | 1.75 | 80% (35/44) | 0% | 33.3% | 1.2% |
| PPO + shield, original, on v2 sim | 11/20 | 8 | 34.43 | 32.40 | 0.15 (0, 1) | 2.25 | 75% (45/60) | 9% | 14.2% | 0.0% |
| residual PPO on PID+APF (ResRace-style) | 8/20 | 0 | 30.21 | 28.92 | 1.94 (5, 7) | 2.10 | 95% (42/44) | 0% | 12.5% | 1.1% |
| PPO + additive Eq.2/3 shield | 16/20 | 0 | 47.11 | 40.60 | 0.45 (3, 1) | 0.95 | 95% (19/20) | 10% | 7.5% | 0.1% |
| PID + APF | 12/20 | 0 | 44.04 | 35.48 | 1.18 (1, 7) | 1.40 | 74% (28/38) | 93% | 2.2% | 0.6% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.52 (0, 20) | 0.00 | - (0/0) | 0% | 8.5% | 0.0% |
| residual PPO + escape shield (v2 sim) | 5/20 | 8 | 55.86 | 31.24 | 1.04 (5, 2) | 2.55 | 96% (51/53) | 26% | 30.1% | 27.1% |

Targets for PPO + shield with deadlock escape (ours, final; v2 sim) (randomized):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.780 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.753 | <= 0.5 | no |
| PPO+APF completed passes / attempts | 0.754 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.038 | <= 0.1 | yes |
| fraction of time above 90% of mu*g (uses the grip) | 0.159 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.000 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield with deadlock escape (ours, final; v2 sim) vs each controller (per-race values):

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| PPO + final shield (seed 1) | 2.96e-05 | 0.000544 | 0.00486 | 0.000305 | 0.0227 |
| PPO, no shield (seed 0) | 2.96e-05 | 2.96e-05 | 0.000786 | 0.000275 | - |
| PPO, no shield (seed 1) | 0.00179 | 0.00179 | 0.096 | 0.0114 | 0.35 |
| PPO + shield, original, on v2 sim | 0.341 | 0.042 | 0.508 | 0.425 | 0.965 |
| residual PPO on PID+APF (ResRace-style) | 0.0619 | 0.0619 | 0.341 | 0.0223 | 5.66e-06 |
| PPO + additive Eq.2/3 shield | 0.482 | 0.482 | 0.00109 | 0.508 | 1.06e-06 |
| PID + APF | 0.523 | 0.523 | 0.0203 | 0.14 | 1.75e-05 |
| Pure Pursuit | 4.97e-06 | 4.97e-06 | 2.71e-08 | 6.8e-08 | - |
| residual PPO + escape shield (v2 sim) | 0.00514 | 0.751 | 1 | 0.081 | 0.528 |
