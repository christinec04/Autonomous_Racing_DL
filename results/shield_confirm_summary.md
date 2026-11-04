# Race results

Sources: `shield_confirm.json`. 20 races x 5 laps per controller, 3 opponents, DNF on first collision. Clean lap = mean over laps 2-5 (lap 1 is a standing start).

## nominal

| controller | finished | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|
| PPO + shield (ours) | 17/20 | 34.32 | 32.64 | 0.38 (0, 3) | 2.65 | 88% (53/60) | 6% | 16.7% | 0.0% |
| ppo_apf c_safe0.10 | 18/20 | 34.80 | 32.72 | 0.30 (0, 2) | 2.35 | 70% (47/67) | 8% | 17.5% | 0.0% |
| ppo_apf fixed | 20/20 | 34.72 | 32.76 | 0.00 (0, 0) | 2.00 | 77% (40/52) | 10% | 16.5% | 0.0% |
| ppo_apf fixed c_safe0.10 | 19/20 | 34.70 | 32.88 | 0.16 (0, 1) | 2.05 | 84% (41/49) | 12% | 16.5% | 0.1% |

Mann-Whitney U p-values, PPO + shield (ours) vs each controller (per-race values):

| vs | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|
| ppo_apf c_safe0.10 | 0.654 | 0.592 | 0.072 | 0.406 |
| ppo_apf fixed | 0.0804 | 0.216 | 0.441 | 0.693 |
| ppo_apf fixed c_safe0.10 | 0.31 | 0.231 | 0.102 | 0.593 |

## randomized

| controller | finished | clean lap (s) | best lap | collisions / 10 laps (wall, car) | passes / race | overtake success | shield active | time > 90% grip | time > 15 deg slip |
|---|---|---|---|---|---|---|---|---|---|
| PPO + shield (ours) | 16/20 | 34.49 | 32.44 | 0.63 (2, 2) | 2.50 | 85% (50/59) | 10% | 14.6% | 0.9% |
| ppo_apf c_safe0.10 | 18/20 | 34.31 | 32.48 | 0.33 (0, 2) | 2.35 | 76% (47/62) | 10% | 14.3% | 0.3% |
| ppo_apf fixed | 18/20 | 34.28 | 32.64 | 0.29 (0, 2) | 2.30 | 74% (46/62) | 9% | 14.0% | 0.2% |
| ppo_apf fixed c_safe0.10 | 20/20 | 34.51 | 32.56 | 0.00 (0, 0) | 1.90 | 78% (38/49) | 13% | 14.6% | 0.7% |

Mann-Whitney U p-values, PPO + shield (ours) vs each controller (per-race values):

| vs | collided (0/1) | passes | laps completed | clean lap time |
|---|---|---|---|---|
| ppo_apf c_safe0.10 | 0.394 | 0.74 | 0.543 | 0.344 |
| ppo_apf fixed | 0.394 | 0.669 | 0.946 | 0.61 |
| ppo_apf fixed c_safe0.10 | 0.0398 | 0.289 | 0.968 | 1 |
