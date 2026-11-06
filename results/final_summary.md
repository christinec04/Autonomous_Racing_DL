# Race results

Sources: `final_v2_others.json`, `eval_escape_v4.json`, `eval_escape_v4_s1.json`, `eval_escape_v4_s2.json`, `eval_recover.json`. 20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 (lap 1 is a standing start).

## nominal

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO + shield + escape + stall recovery (ours, final; v2 sim) | 19/20 | 0 | 34.67 | 32.64 | 0.10 (0, 1) | 3.15 | 85% (63/74) | 3% | 16.8% | 0.0% |
| same, training seed 1 | 1/20 | 1 | 36.62 | 31.12 | 4.68 (14, 4) | 1.80 | 68% (36/53) | 22% | 43.6% | 14.7% |
| same, training seed 2 | 19/20 | 0 | 43.05 | 32.40 | 0.10 (1, 0) | 1.35 | 87% (27/31) | 2% | 46.2% | 0.0% |
| PPO + shield with deadlock escape (no stall recovery; v2 sim) | 16/20 | 0 | 34.47 | 32.64 | 0.44 (3, 1) | 2.95 | 86% (59/69) | 3% | 17.1% | 0.0% |
| PPO + final shield (seed 1) | 1/20 | 2 | 37.12 | 31.16 | 4.91 (14, 3) | 1.70 | 69% (34/49) | 20% | 41.6% | 9.1% |
| ppo_apf_esc@s2 | 8/20 | 7 | 40.97 | 32.48 | 0.77 (5, 0) | 0.80 | 89% (16/18) | 3% | 44.4% | 0.0% |
| PPO, no shield (seed 0) | 0/20 | 1 | 32.50 | 28.32 | 7.35 (18, 1) | 1.35 | 90% (27/30) | 0% | 32.1% | 1.9% |
| PPO, no shield (seed 1) | 3/20 | 0 | 34.89 | 32.08 | 3.23 (14, 3) | 2.15 | 91% (43/47) | 0% | 41.0% | 0.1% |
| PPO + shield, original, on v2 sim | 11/20 | 8 | 34.61 | 32.68 | 0.14 (0, 1) | 2.10 | 74% (42/57) | 8% | 16.7% | 0.0% |
| residual PPO on PID+APF (ResRace-style) | 10/20 | 0 | 30.37 | 29.20 | 1.60 (1, 9) | 2.20 | 81% (44/54) | 0% | 12.3% | 1.6% |
| PPO + additive Eq.2/3 shield | 18/20 | 0 | 47.57 | 40.44 | 0.21 (2, 0) | 0.85 | 71% (17/24) | 7% | 8.5% | 0.0% |
| PID + APF | 12/20 | 0 | 42.84 | 36.00 | 1.09 (3, 5) | 1.35 | 66% (27/41) | 89% | 2.4% | 0.6% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.35 (0, 20) | 0.00 | - (0/0) | 0% | 11.8% | 0.0% |
| residual PPO + escape shield (v2 sim) | 2/20 | 15 | 102.09 | 31.36 | 0.52 (0, 3) | 1.70 | 94% (34/36) | 39% | 61.7% | 60.6% |

Targets for PPO + shield + escape + stall recovery (ours, final; v2 sim) (nominal):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.809 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.105 | <= 0.5 | yes |
| PPO+APF completed passes / attempts | 0.851 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.030 | <= 0.1 | yes |
| fraction of time above 90% of mu*g (uses the grip) | 0.168 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.000 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield + escape + stall recovery (ours, final; v2 sim) vs each controller (per-race values):

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| same, training seed 1 | 2.08e-08 | 1.16e-07 | 0.000433 | 1.25e-05 | 0.221 |
| same, training seed 2 | 1 | 1 | 0.000181 | 0.156 | 3.94e-07 |
| PPO + shield with deadlock escape (no stall recovery; v2 sim) | 0.164 | 0.164 | 0.526 | 0.417 | 0.37 |
| PPO + final shield (seed 1) | 2.08e-08 | 5.57e-07 | 0.000208 | 9.75e-06 | 0.489 |
| ppo_apf_esc@s2 | 0.000262 | 0.0842 | 2.97e-06 | 0.000305 | 2.44e-05 |
| PPO, no shield (seed 0) | 3.13e-09 | 2.08e-08 | 3.35e-05 | 9.13e-07 | - |
| PPO, no shield (seed 1) | 5.57e-07 | 5.57e-07 | 0.0205 | 0.0002 | 0.216 |
| PPO + shield, original, on v2 sim | 0.00415 | 1 | 0.0149 | 0.0452 | 0.299 |
| residual PPO on PID+APF (ResRace-style) | 0.00175 | 0.00175 | 0.0385 | 0.00234 | 1.39e-06 |
| PPO + additive Eq.2/3 shield | 0.573 | 0.573 | 4.87e-06 | 0.0439 | 1.48e-07 |
| PID + APF | 0.00936 | 0.00936 | 0.00022 | 0.00711 | 2.84e-06 |
| Pure Pursuit | 3.13e-09 | 3.13e-09 | 6.36e-09 | 6.8e-08 | - |
| residual PPO + escape shield (v2 sim) | 1.16e-07 | 0.31 | 0.000866 | 3.07e-06 | 0.000982 |

## randomized

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO + shield + escape + stall recovery (ours, final; v2 sim) | 16/20 | 0 | 34.43 | 32.40 | 0.47 (1, 3) | 2.95 | 78% (59/76) | 4% | 15.6% | 0.0% |
| same, training seed 1 | 3/20 | 0 | 32.78 | 30.48 | 4.89 (16, 1) | 1.35 | 59% (27/46) | 18% | 34.2% | 7.8% |
| same, training seed 2 | 14/20 | 0 | 43.77 | 32.40 | 0.74 (4, 2) | 1.10 | 76% (22/29) | 2% | 35.8% | 0.1% |
| PPO + shield with deadlock escape (no stall recovery; v2 sim) | 14/20 | 0 | 34.36 | 32.40 | 0.75 (3, 3) | 2.60 | 75% (52/69) | 4% | 15.9% | 0.0% |
| PPO + final shield (seed 1) | 1/20 | 2 | 32.46 | 30.48 | 6.18 (16, 1) | 1.20 | 60% (24/40) | 17% | 31.1% | 2.8% |
| ppo_apf_esc@s2 | 5/20 | 1 | 41.44 | 32.40 | 2.50 (12, 2) | 0.80 | 76% (16/21) | 3% | 34.9% | 0.0% |
| PPO, no shield (seed 0) | 1/20 | 0 | 38.42 | 28.96 | 7.13 (19, 0) | 0.95 | 70% (19/27) | 0% | 27.3% | 2.4% |
| PPO, no shield (seed 1) | 4/20 | 0 | 34.36 | 32.72 | 3.48 (15, 1) | 1.75 | 80% (35/44) | 0% | 33.3% | 1.2% |
| PPO + shield, original, on v2 sim | 11/20 | 8 | 34.43 | 32.40 | 0.15 (0, 1) | 2.25 | 75% (45/60) | 9% | 14.2% | 0.0% |
| residual PPO on PID+APF (ResRace-style) | 8/20 | 0 | 30.21 | 28.92 | 1.94 (5, 7) | 2.10 | 95% (42/44) | 0% | 12.5% | 1.1% |
| PPO + additive Eq.2/3 shield | 16/20 | 0 | 47.11 | 40.60 | 0.45 (3, 1) | 0.95 | 95% (19/20) | 10% | 7.5% | 0.1% |
| PID + APF | 12/20 | 0 | 44.04 | 35.48 | 1.18 (1, 7) | 1.40 | 74% (28/38) | 93% | 2.2% | 0.6% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.52 (0, 20) | 0.00 | - (0/0) | 0% | 8.5% | 0.0% |
| residual PPO + escape shield (v2 sim) | 5/20 | 8 | 55.86 | 31.24 | 1.04 (5, 2) | 2.55 | 96% (51/53) | 26% | 30.1% | 27.1% |

Targets for PPO + shield + escape + stall recovery (ours, final; v2 sim) (randomized):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.782 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.470 | <= 0.5 | yes |
| PPO+APF completed passes / attempts | 0.776 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.036 | <= 0.1 | yes |
| fraction of time above 90% of mu*g (uses the grip) | 0.156 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.000 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield + escape + stall recovery (ours, final; v2 sim) vs each controller (per-race values):

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| same, training seed 1 | 5.15e-05 | 5.15e-05 | 0.00372 | 0.000375 | 0.000911 |
| same, training seed 2 | 0.482 | 0.482 | 0.000963 | 0.25 | 5.19e-06 |
| PPO + shield with deadlock escape (no stall recovery; v2 sim) | 0.482 | 0.482 | 0.544 | 0.424 | 0.614 |
| PPO + final shield (seed 1) | 2.34e-06 | 5.15e-05 | 0.00141 | 8.29e-05 | 0.00702 |
| ppo_apf_esc@s2 | 0.000618 | 0.00179 | 0.000104 | 0.0028 | 0.000139 |
| PPO, no shield (seed 0) | 2.34e-06 | 2.34e-06 | 0.000252 | 5.25e-05 | - |
| PPO, no shield (seed 1) | 0.00019 | 0.00019 | 0.0312 | 0.00256 | 0.666 |
| PPO + shield, original, on v2 sim | 0.0989 | 0.164 | 0.221 | 0.148 | 0.691 |
| residual PPO on PID+APF (ResRace-style) | 0.0113 | 0.0113 | 0.12 | 0.00334 | 4.15e-06 |
| PPO + additive Eq.2/3 shield | 1 | 1 | 0.00035 | 0.0962 | 7.05e-07 |
| PID + APF | 0.178 | 0.178 | 0.00565 | 0.0207 | 1.29e-05 |
| Pure Pursuit | 3.71e-07 | 3.71e-07 | 2.75e-08 | 6.8e-08 | - |
| residual PPO + escape shield (v2 sim) | 0.000618 | 0.302 | 0.474 | 0.0133 | 0.558 |
