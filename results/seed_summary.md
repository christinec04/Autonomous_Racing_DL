# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + shield (ours) | PPO, no shield |
|---|---|---|
| finished / 20 | 16.5 +- 0.5 (n=2) | 2.0 (n=1) |
| clean lap (s) | 33.51 +- 0.80 (n=2) | 36.82 (n=1) |
| collisions / 10 laps | 0.85 +- 0.46 (n=2) | 5.53 (n=1) |
| passes / race | 2.20 +- 0.45 (n=2) | 1.05 (n=1) |
| overtake success | 79% +- 9% (n=2) | 72% (n=1) |
| shield active | 15.2% +- 9.0% (n=2) | 0.0% (n=1) |
| time > 90% grip | 23.5% +- 6.8% (n=2) | 31.9% (n=1) |
| time > 15 deg slip | 2.0% +- 2.0% (n=2) | 1.6% (n=1) |

## randomized

| metric | PPO + shield (ours) | PPO, no shield |
|---|---|---|
| finished / 20 | 15.0 +- 1.0 (n=2) | 1.0 (n=1) |
| clean lap (s) | 34.49 (n=1) | 35.71 (n=1) |
| collisions / 10 laps | 2.00 +- 1.36 (n=2) | 6.75 (n=1) |
| passes / race | 1.82 +- 0.68 (n=2) | 1.10 (n=1) |
| overtake success | 78% +- 6% (n=2) | 79% (n=1) |
| shield active | 16.0% +- 5.5% (n=2) | 0.0% (n=1) |
| time > 90% grip | 19.6% +- 5.0% (n=2) | 27.7% (n=1) |
| time > 15 deg slip | 1.9% +- 1.0% (n=2) | 2.7% (n=1) |
