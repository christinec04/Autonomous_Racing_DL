# Race results

Sources: `eval_baselines.json`, `eval_ppo_s0.json`, `eval_residual_s0.json`, `eval_residual_apf_s0.json`, `eval_ppo_shield_s1.json`, `eval_escape_v4.json`. 20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 (lap 1 is a standing start).

## nominal

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO + shield (ours) | 12/20 | 5 | 34.32 | 32.64 | 0.38 (0, 3) | 2.65 | 88% (53/60) | 6% | 16.7% | 0.0% |
| PPO, no shield | 1/20 | 1 | 36.82 | 28.24 | 5.53 (18, 0) | 1.05 | 72% (21/29) | 0% | 31.9% | 1.6% |
| shield-trained PPO, shield removed | 5/20 | 0 | 34.94 | 32.44 | 4.72 (7, 8) | 1.00 | 62% (20/32) | 0% | 17.2% | 0.0% |
| unshielded PPO + shield at race time | 1/20 | 19 | 36.66 | 30.56 | 0.00 (0, 0) | 1.25 | 81% (25/31) | 16% | 29.4% | 2.4% |
| residual PPO on PID+APF (ResRace-style) | 9/20 | 0 | 30.35 | 29.20 | 1.77 (3, 8) | 2.75 | 93% (55/59) | 0% | 12.8% | 1.4% |
| residual PPO + our shield at race time | 4/20 | 14 | 32.70 | 31.32 | 0.36 (0, 2) | 2.15 | 100% (43/43) | 20% | 13.7% | 5.0% |
| PID + APF | 9/20 | 0 | 43.91 | 36.04 | 1.75 (4, 7) | 1.25 | 66% (25/38) | 93% | 2.5% | 0.6% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.35 (0, 20) | 0.00 | - (0/0) | 0% | 11.8% | 0.0% |
| ppo_apf@s0v2 | 11/20 | 8 | 34.61 | 32.68 | 0.14 (0, 1) | 2.10 | 74% (42/57) | 8% | 16.7% | 0.0% |
| ppo_apf@s1 | 1/20 | 15 | 32.71 | 31.16 | 1.31 (3, 1) | 1.75 | 70% (35/50) | 24% | 30.3% | 4.0% |
| ppo_apf_esc@s0 | 16/20 | 0 | 34.47 | 32.64 | 0.44 (3, 1) | 2.95 | 86% (59/69) | 3% | 17.1% | 0.0% |
| ppo_residual_apf_esc | 2/20 | 15 | 102.09 | 31.36 | 0.52 (0, 3) | 1.70 | 94% (34/36) | 39% | 61.7% | 60.6% |

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

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| PPO, no shield | 0.000262 | 2.95e-06 | 0.00232 | 0.000921 | 0.793 |
| shield-trained PPO, shield removed | 0.0282 | 0.000177 | 0.00233 | 0.00364 | 0.563 |
| unshielded PPO + shield at race time | 0.000262 | 0.0804 | 0.00592 | 0.0028 | 0.719 |
| residual PPO on PID+APF (ResRace-style) | 0.356 | 0.00926 | 0.869 | 0.0499 | 5.66e-06 |
| residual PPO + our shield at race time | 0.0113 | 0.654 | 0.36 | 0.0114 | 5.05e-05 |
| PID + APF | 0.356 | 0.00926 | 0.00829 | 0.0859 | 2.16e-05 |
| Pure Pursuit | 4.68e-05 | 8.64e-08 | 3.28e-07 | 6.8e-08 | - |
| ppo_apf@s0v2 | 0.764 | 0.31 | 0.29 | 0.675 | 0.739 |
| ppo_apf@s1 | 0.000262 | 0.696 | 0.0662 | 0.000563 | 0.00165 |
| ppo_apf_esc@s0 | 0.178 | 0.696 | 0.59 | 0.337 | 0.535 |
| ppo_residual_apf_esc | 0.00113 | 1 | 0.0749 | 0.00306 | 0.00162 |

## randomized

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO + shield (ours) | 9/20 | 7 | 34.49 | 32.44 | 0.63 (2, 2) | 2.50 | 85% (50/59) | 10% | 14.6% | 0.9% |
| PPO, no shield | 1/20 | 0 | 35.71 | 26.88 | 6.75 (18, 1) | 1.10 | 79% (22/28) | 0% | 27.7% | 2.7% |
| shield-trained PPO, shield removed | 6/20 | 0 | 34.51 | 32.24 | 3.54 (7, 7) | 1.45 | 69% (29/42) | 0% | 14.0% | 0.1% |
| unshielded PPO + shield at race time | 0/20 | 18 | 32.29 | 30.36 | 0.97 (2, 0) | 1.05 | 88% (21/24) | 24% | 23.1% | 3.3% |
| residual PPO on PID+APF (ResRace-style) | 8/20 | 0 | 30.28 | 28.92 | 2.10 (6, 6) | 1.90 | 93% (38/41) | 0% | 12.7% | 1.3% |
| residual PPO + our shield at race time | 5/20 | 12 | 32.43 | 31.36 | 0.61 (0, 3) | 2.45 | 96% (49/51) | 20% | 12.1% | 4.9% |
| PID + APF | 12/20 | 0 | 44.02 | 35.48 | 1.18 (2, 6) | 1.40 | 70% (28/40) | 93% | 2.3% | 0.8% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.52 (0, 20) | 0.00 | - (0/0) | 0% | 8.5% | 0.0% |
| ppo_apf@s0v2 | 11/20 | 8 | 34.43 | 32.40 | 0.15 (0, 1) | 2.25 | 75% (45/60) | 9% | 14.2% | 0.0% |
| ppo_apf@s1 | 0/20 | 14 | - | - | 3.36 (4, 2) | 1.15 | 72% (23/32) | 22% | 24.6% | 2.9% |
| ppo_apf_esc@s0 | 14/20 | 0 | 34.36 | 32.40 | 0.75 (3, 3) | 2.60 | 75% (52/69) | 4% | 15.9% | 0.0% |
| ppo_residual_apf_esc | 5/20 | 8 | 55.86 | 31.24 | 1.04 (5, 2) | 2.55 | 96% (51/53) | 26% | 30.1% | 27.1% |

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

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| PPO, no shield | 0.00415 | 2.34e-06 | 0.0101 | 0.0207 | 0.202 |
| shield-trained PPO, shield removed | 0.341 | 0.00179 | 0.0554 | 0.0439 | 0.183 |
| unshielded PPO + shield at race time | 0.000819 | 0.394 | 0.0073 | 0.00397 | 0.102 |
| residual PPO on PID+APF (ResRace-style) | 0.764 | 0.0113 | 0.248 | 0.543 | 1.65e-05 |
| residual PPO + our shield at race time | 0.196 | 0.696 | 0.826 | 0.561 | 0.000175 |
| PID + APF | 0.356 | 0.178 | 0.0386 | 0.695 | 5.07e-05 |
| Pure Pursuit | 0.000819 | 3.71e-07 | 1.05e-06 | 7.9e-08 | - |
| ppo_apf@s0v2 | 0.543 | 0.164 | 0.651 | 0.617 | 1 |
| ppo_apf@s1 | 0.000819 | 0.482 | 0.0111 | 0.00364 | - |
| ppo_apf_esc@s0 | 0.118 | 0.482 | 0.869 | 0.133 | 0.983 |
| ppo_residual_apf_esc | 0.196 | 0.302 | 0.989 | 0.989 | 0.586 |
