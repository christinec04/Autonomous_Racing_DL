# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield | PPO, no shield |
|---|---|---|---|
| finished all laps / 20 | 19.0 +- 18.0 (n=2) | 6.5 +- 5.5 (n=2) | 2.0 +- 1.0 (n=2) |
| stuck / 20 | 1.0 +- 1.0 (n=2) | 10.0 +- 5.0 (n=2) | 0.5 +- 0.5 (n=2) |
| clean lap (s) | 35.83 +- 1.29 (n=2) | 33.51 +- 0.80 (n=2) | 36.12 +- 0.70 (n=2) |
| collisions / 10 laps | 2.96 +- 1.95 (n=2) | 0.85 +- 0.46 (n=2) | 4.43 +- 1.10 (n=2) |
| passes / race | 2.08 +- 0.38 (n=2) | 2.20 +- 0.45 (n=2) | 1.65 +- 0.60 (n=2) |
| overtake success | 76% +- 6% (n=2) | 79% +- 9% (n=2) | 77% +- 5% (n=2) |
| shield active | 12.0% +- 8.3% (n=2) | 15.2% +- 9.0% (n=2) | 0.0% +- 0.0% (n=2) |
| time > 90% grip | 29.7% +- 11.9% (n=2) | 23.5% +- 6.8% (n=2) | 36.1% +- 4.1% (n=2) |
| time > 15 deg slip | 4.6% +- 4.6% (n=2) | 2.0% +- 2.0% (n=2) | 0.9% +- 0.7% (n=2) |

## randomized

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield | PPO, no shield |
|---|---|---|---|
| finished all laps / 20 | 17.0 +- 16.0 (n=2) | 4.5 +- 4.5 (n=2) | 4.5 +- 3.5 (n=2) |
| stuck / 20 | 1.5 +- 0.5 (n=2) | 10.5 +- 3.5 (n=2) | 0.0 +- 0.0 (n=2) |
| clean lap (s) | 33.41 +- 0.96 (n=2) | 34.49 (n=1) | 35.04 +- 0.67 (n=2) |
| collisions / 10 laps | 3.71 +- 2.47 (n=2) | 2.00 +- 1.36 (n=2) | 4.54 +- 2.21 (n=2) |
| passes / race | 1.86 +- 0.66 (n=2) | 1.82 +- 0.68 (n=2) | 1.50 +- 0.40 (n=2) |
| overtake success | 69% +- 9% (n=2) | 78% +- 6% (n=2) | 82% +- 4% (n=2) |
| shield active | 10.4% +- 6.3% (n=2) | 16.0% +- 5.5% (n=2) | 0.0% +- 0.0% (n=2) |
| time > 90% grip | 23.2% +- 7.9% (n=2) | 19.6% +- 5.0% (n=2) | 30.3% +- 2.6% (n=2) |
| time > 15 deg slip | 1.6% +- 1.3% (n=2) | 1.9% +- 1.0% (n=2) | 1.8% +- 0.9% (n=2) |
