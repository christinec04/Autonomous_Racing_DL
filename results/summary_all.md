# Race results

Sources: `eval_baselines.json`, `eval_ppo_s0.json`, `eval_residual_s0.json`, `eval_residual_apf_s0.json`, `eval_ppo_additive_s0.json`, `eval_ppo_noshield_s1.json`, `eval_ppo_noshield_s2.json`, `eval_ppo_shield_preview_s0.json`, `eval_ppo_shield_s1.json`, `eval_ppo_shield_s2.json`, `eval_ppo_shield_v2esc_s0.json`, `eval_ppo_shield_v2esc_slip_s1.json`, `eval_ppo_shield_w3low_s0.json`, `eval_ppo_shielddrop_s0.json`. 20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 (lap 1 is a standing start).

## nominal

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO, no shield (seed 1) | 3/20 | 0 | 35.42 | 32.88 | 3.33 (15, 2) | 2.25 | 82% (45/55) | 0% | 40.2% | 0.1% |
| PPO + shield, original (ours) | 12/20 | 5 | 34.32 | 32.64 | 0.38 (0, 3) | 2.65 | 88% (53/60) | 6% | 16.7% | 0.0% |
| PPO + shield, original, seed 1 | 1/20 | 15 | 32.71 | 31.16 | 1.31 (3, 1) | 1.75 | 70% (35/50) | 24% | 30.3% | 4.0% |
| PPO, no shield | 1/20 | 1 | 36.82 | 28.24 | 5.53 (18, 0) | 1.05 | 72% (21/29) | 0% | 31.9% | 1.6% |
| shield-trained PPO, shield removed | 5/20 | 0 | 34.94 | 32.44 | 4.72 (7, 8) | 1.00 | 62% (20/32) | 0% | 17.2% | 0.0% |
| unshielded PPO + shield at race time | 1/20 | 19 | 36.66 | 30.56 | 0.00 (0, 0) | 1.25 | 81% (25/31) | 16% | 29.4% | 2.4% |
| residual PPO on PID+APF (ResRace-style) | 9/20 | 0 | 30.35 | 29.20 | 1.77 (3, 8) | 2.75 | 93% (55/59) | 0% | 12.8% | 1.4% |
| residual PPO + our shield at race time | 4/20 | 14 | 32.70 | 31.32 | 0.36 (0, 2) | 2.15 | 100% (43/43) | 20% | 13.7% | 5.0% |
| PPO + additive Eq.2/3 shield | 15/20 | 0 | 48.82 | 40.56 | 0.61 (2, 3) | 0.55 | 65% (11/17) | 8% | 8.8% | 0.2% |
| PID + APF | 9/20 | 0 | 43.91 | 36.04 | 1.75 (4, 7) | 1.25 | 66% (25/38) | 93% | 2.5% | 0.6% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.35 (0, 20) | 0.00 | - (0/0) | 0% | 11.8% | 0.0% |
| ppo@drop_noshield | 16/20 | 0 | 42.02 | 30.28 | 0.45 (2, 2) | 0.25 | 83% (5/6) | 0% | 9.4% | 0.1% |
| ppo@s2 | 5/20 | 0 | 48.23 | 33.40 | 2.79 (12, 3) | 0.30 | 67% (6/9) | 0% | 9.2% | 0.0% |
| ppo_apf@drop | 11/20 | 5 | 44.35 | 32.56 | 0.61 (2, 2) | 0.30 | 75% (6/8) | 4% | 9.9% | 0.3% |
| ppo_apf@preview | 13/20 | 5 | 33.36 | 31.36 | 0.25 (0, 2) | 3.50 | 85% (70/82) | 6% | 24.6% | 0.3% |
| ppo_apf@s2 | 7/20 | 10 | 41.93 | 32.00 | 0.52 (0, 3) | 0.85 | 85% (17/20) | 5% | 43.9% | 0.3% |
| ppo_apf@w3low | 0/20 | 18 | 31.26 | 31.08 | 1.19 (0, 2) | 1.70 | 85% (34/40) | 35% | 41.1% | 11.9% |
| ppo_apf_esc@slip_s1 | 17/20 | 1 | 32.53 | 30.92 | 0.22 (1, 1) | 2.55 | 93% (51/55) | 8% | 28.1% | 0.4% |
| ppo_apf_esc@v2esc | 14/20 | 1 | 36.26 | 34.44 | 0.62 (1, 4) | 3.45 | 92% (69/75) | 4% | 15.0% | 0.0% |

Targets for PPO + shield, original (ours) (nominal):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.782 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.382 | <= 0.5 | yes |
| PPO+APF completed passes / attempts | 0.883 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.061 | <= 0.1 | yes |
| fraction of time above 90% of mu*g (uses the grip) | 0.167 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.000 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield, original (ours) vs each controller (per-race values):

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| PPO, no shield (seed 1) | 0.0039 | 1.33e-05 | 0.482 | 0.00905 | 0.00204 |
| PPO + shield, original, seed 1 | 0.000262 | 0.696 | 0.0662 | 0.000563 | 0.00165 |
| PPO, no shield | 0.000262 | 2.95e-06 | 0.00232 | 0.000921 | 0.793 |
| shield-trained PPO, shield removed | 0.0282 | 0.000177 | 0.00233 | 0.00364 | 0.563 |
| unshielded PPO + shield at race time | 0.000262 | 0.0804 | 0.00592 | 0.0028 | 0.719 |
| residual PPO on PID+APF (ResRace-style) | 0.356 | 0.00926 | 0.869 | 0.0499 | 5.66e-06 |
| residual PPO + our shield at race time | 0.0113 | 0.654 | 0.36 | 0.0114 | 5.05e-05 |
| PPO + additive Eq.2/3 shield | 0.325 | 0.447 | 0.000105 | 0.776 | 1.54e-06 |
| PID + APF | 0.356 | 0.00926 | 0.00829 | 0.0859 | 2.16e-05 |
| Pure Pursuit | 4.68e-05 | 8.64e-08 | 3.28e-07 | 6.8e-08 | - |
| ppo@drop_noshield | 0.178 | 0.696 | 7.58e-06 | 0.903 | 5.7e-06 |
| ppo@s2 | 0.0282 | 0.000177 | 1.14e-05 | 0.0155 | 0.000186 |
| ppo_apf@drop | 0.764 | 0.696 | 1.2e-05 | 0.239 | 1.91e-05 |
| ppo_apf@preview | 0.759 | 0.654 | 0.164 | 0.735 | 0.00049 |
| ppo_apf@s2 | 0.122 | 1 | 0.0008 | 0.072 | 0.000106 |
| ppo_apf@w3low | 4.68e-05 | 0.654 | 0.0505 | 7.41e-05 | - |
| ppo_apf_esc@slip_s1 | 0.0835 | 0.654 | 0.762 | 0.0962 | 7.37e-07 |
| ppo_apf_esc@v2esc | 0.523 | 0.447 | 0.17 | 0.903 | 2.64e-05 |

## randomized

| controller | finished all 5 laps | stuck (no crash, stopped) | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|---|
| PPO, no shield (seed 1) | 8/20 | 0 | 34.37 | 31.56 | 2.33 (9, 3) | 1.90 | 86% (38/44) | 0% | 32.9% | 0.9% |
| PPO + shield, original (ours) | 9/20 | 7 | 34.49 | 32.44 | 0.63 (2, 2) | 2.50 | 85% (50/59) | 10% | 14.6% | 0.9% |
| PPO + shield, original, seed 1 | 0/20 | 14 | - | - | 3.36 (4, 2) | 1.15 | 72% (23/32) | 22% | 24.6% | 2.9% |
| PPO, no shield | 1/20 | 0 | 35.71 | 26.88 | 6.75 (18, 1) | 1.10 | 79% (22/28) | 0% | 27.7% | 2.7% |
| shield-trained PPO, shield removed | 6/20 | 0 | 34.51 | 32.24 | 3.54 (7, 7) | 1.45 | 69% (29/42) | 0% | 14.0% | 0.1% |
| unshielded PPO + shield at race time | 0/20 | 18 | 32.29 | 30.36 | 0.97 (2, 0) | 1.05 | 88% (21/24) | 24% | 23.1% | 3.3% |
| residual PPO on PID+APF (ResRace-style) | 8/20 | 0 | 30.28 | 28.92 | 2.10 (6, 6) | 1.90 | 93% (38/41) | 0% | 12.7% | 1.3% |
| residual PPO + our shield at race time | 5/20 | 12 | 32.43 | 31.36 | 0.61 (0, 3) | 2.45 | 96% (49/51) | 20% | 12.1% | 4.9% |
| PPO + additive Eq.2/3 shield | 17/20 | 1 | 46.81 | 40.48 | 0.22 (2, 0) | 0.90 | 86% (18/21) | 9% | 7.6% | 0.1% |
| PID + APF | 12/20 | 0 | 44.02 | 35.48 | 1.18 (2, 6) | 1.40 | 70% (28/40) | 93% | 2.3% | 0.8% |
| Pure Pursuit | 0/20 | 0 | - | - | 61.52 (0, 20) | 0.00 | - (0/0) | 0% | 8.5% | 0.0% |
| ppo@drop_noshield | 13/20 | 0 | 45.38 | 30.04 | 0.96 (2, 5) | 0.45 | 75% (9/12) | 0% | 8.1% | 0.1% |
| ppo@s2 | 6/20 | 0 | 48.41 | 33.24 | 2.71 (9, 5) | 0.35 | 64% (7/11) | 0% | 8.5% | 0.2% |
| ppo_apf@drop | 14/20 | 5 | 44.80 | 31.80 | 0.13 (0, 1) | 0.60 | 86% (12/14) | 4% | 8.3% | 0.1% |
| ppo_apf@preview | 6/20 | 13 | 32.81 | 31.16 | 0.19 (1, 0) | 2.55 | 84% (51/61) | 13% | 20.6% | 0.5% |
| ppo_apf@s2 | 4/20 | 14 | 42.23 | 32.40 | 0.44 (0, 2) | 0.60 | 86% (12/14) | 8% | 32.7% | 0.3% |
| ppo_apf@w3low | 1/20 | 18 | 31.49 | 30.68 | 0.45 (1, 0) | 1.65 | 73% (33/45) | 36% | 30.2% | 7.3% |
| ppo_apf_esc@slip_s1 | 13/20 | 4 | 32.77 | 30.92 | 0.38 (2, 1) | 2.75 | 93% (55/59) | 9% | 24.9% | 0.2% |
| ppo_apf_esc@v2esc | 11/20 | 2 | 36.37 | 34.24 | 0.95 (5, 2) | 2.60 | 71% (52/73) | 5% | 13.5% | 0.1% |

Targets for PPO + shield, original (ours) (randomized):

| metric | value | target | met |
|---|---|---|---|
| mean clean-lap time of PPO+APF relative to PID+APF (>= 5% faster) | 0.783 | <= 0.95 | yes |
| PPO+APF collisions per 10 laps | 0.634 | <= 0.5 | no |
| PPO+APF completed passes / attempts | 0.847 | >= 0.7 | yes |
| fraction of race steps with lambda > 0 | 0.105 | <= 0.1 | no |
| fraction of time above 90% of mu*g (uses the grip) | 0.146 | >= 0.1 | yes |
| fraction of time with body slip > 15 deg (no sliding exploit) | 0.009 | <= 0.01 | yes |

Mann-Whitney U p-values, PPO + shield, original (ours) vs each controller (per-race values):

| vs | finished (0/1) | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|---|
| PPO, no shield (seed 1) | 0.764 | 0.0113 | 0.265 | 0.351 | 0.163 |
| PPO + shield, original, seed 1 | 0.000819 | 0.482 | 0.0111 | 0.00364 | - |
| PPO, no shield | 0.00415 | 2.34e-06 | 0.0101 | 0.0207 | 0.202 |
| shield-trained PPO, shield removed | 0.341 | 0.00179 | 0.0554 | 0.0439 | 0.183 |
| unshielded PPO + shield at race time | 0.000819 | 0.394 | 0.0073 | 0.00397 | 0.102 |
| residual PPO on PID+APF (ResRace-style) | 0.764 | 0.0113 | 0.248 | 0.543 | 1.65e-05 |
| residual PPO + our shield at race time | 0.196 | 0.696 | 0.826 | 0.561 | 0.000175 |
| PPO + additive Eq.2/3 shield | 0.00926 | 0.394 | 0.00347 | 0.0764 | 3.11e-06 |
| PID + APF | 0.356 | 0.178 | 0.0386 | 0.695 | 5.07e-05 |
| Pure Pursuit | 0.000819 | 3.71e-07 | 1.05e-06 | 7.9e-08 | - |
| ppo@drop_noshield | 0.215 | 0.302 | 0.000158 | 0.365 | 3.34e-05 |
| ppo@s2 | 0.341 | 0.00179 | 5.87e-05 | 0.473 | 0.000106 |
| ppo_apf@drop | 0.118 | 0.164 | 0.000466 | 0.394 | 2.77e-05 |
| ppo_apf@preview | 0.341 | 0.164 | 1 | 0.598 | 0.00174 |
| ppo_apf@s2 | 0.0989 | 0.394 | 0.000498 | 0.181 | 0.000401 |
| ppo_apf@w3low | 0.00415 | 0.164 | 0.0894 | 0.0028 | 0.00357 |
| ppo_apf_esc@slip_s1 | 0.215 | 0.696 | 0.72 | 0.351 | 0.000118 |
| ppo_apf_esc@v2esc | 0.543 | 0.302 | 0.88 | 0.273 | 0.000149 |
