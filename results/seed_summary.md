# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + shield (ours) | PPO, no shield |
|---|---|---|
| finished / 20 | 17.0 (n=1) | 2.0 (n=1) |
| clean lap (s) | 34.32 (n=1) | 36.82 (n=1) |
| collisions / 10 laps | 0.38 (n=1) | 5.53 (n=1) |
| passes / race | 2.65 (n=1) | 1.05 (n=1) |
| overtake success | 88% (n=1) | 72% (n=1) |
| shield active | 6.1% (n=1) | 0.0% (n=1) |
| time > 90% grip | 16.7% (n=1) | 31.9% (n=1) |
| time > 15 deg slip | 0.0% (n=1) | 1.6% (n=1) |

## randomized

| metric | PPO + shield (ours) | PPO, no shield |
|---|---|---|
| finished / 20 | 16.0 (n=1) | 1.0 (n=1) |
| clean lap (s) | 34.49 (n=1) | 35.71 (n=1) |
| collisions / 10 laps | 0.63 (n=1) | 6.75 (n=1) |
| passes / race | 2.50 (n=1) | 1.10 (n=1) |
| overtake success | 85% (n=1) | 79% (n=1) |
| shield active | 10.5% (n=1) | 0.0% (n=1) |
| time > 90% grip | 14.6% (n=1) | 27.7% (n=1) |
| time > 15 deg slip | 0.9% (n=1) | 2.7% (n=1) |
