# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield (v1 sim) | PPO, no shield (v2 sim) |
|---|---|---|---|
| finished all laps / 20 | 8.5 +- 7.5 (n=2) | 6.5 +- 5.5 (n=2) | 1.5 +- 1.5 (n=2) |
| stuck / 20 | 1.0 +- 1.0 (n=2) | 10.0 +- 5.0 (n=2) | 0.5 +- 0.5 (n=2) |
| clean lap (s) | 35.80 +- 1.32 (n=2) | 33.51 +- 0.80 (n=2) | 33.69 +- 1.19 (n=2) |
| collisions / 10 laps | 2.67 +- 2.23 (n=2) | 0.85 +- 0.46 (n=2) | 5.29 +- 2.06 (n=2) |
| passes / race | 2.33 +- 0.63 (n=2) | 2.20 +- 0.45 (n=2) | 1.75 +- 0.40 (n=2) |
| overtake success | 77% +- 8% (n=2) | 79% +- 9% (n=2) | 91% +- 1% (n=2) |
| shield active | 11.7% +- 8.5% (n=2) | 15.2% +- 9.0% (n=2) | 0.0% +- 0.0% (n=2) |
| time > 90% grip | 29.4% +- 12.2% (n=2) | 23.5% +- 6.8% (n=2) | 36.5% +- 4.5% (n=2) |
| time > 15 deg slip | 4.6% +- 4.6% (n=2) | 2.0% +- 2.0% (n=2) | 1.0% +- 0.9% (n=2) |

## randomized

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield (v1 sim) | PPO, no shield (v2 sim) |
|---|---|---|---|
| finished all laps / 20 | 7.5 +- 6.5 (n=2) | 4.5 +- 4.5 (n=2) | 2.5 +- 1.5 (n=2) |
| stuck / 20 | 1.0 +- 1.0 (n=2) | 10.5 +- 3.5 (n=2) | 0.0 +- 0.0 (n=2) |
| clean lap (s) | 33.41 +- 0.95 (n=2) | 34.49 (n=1) | 36.39 +- 2.03 (n=2) |
| collisions / 10 laps | 3.47 +- 2.71 (n=2) | 2.00 +- 1.36 (n=2) | 5.31 +- 1.83 (n=2) |
| passes / race | 1.90 +- 0.70 (n=2) | 1.82 +- 0.68 (n=2) | 1.35 +- 0.40 (n=2) |
| overtake success | 68% +- 8% (n=2) | 78% +- 6% (n=2) | 75% +- 5% (n=2) |
| shield active | 10.2% +- 6.5% (n=2) | 16.0% +- 5.5% (n=2) | 0.0% +- 0.0% (n=2) |
| time > 90% grip | 23.5% +- 7.6% (n=2) | 19.6% +- 5.0% (n=2) | 30.3% +- 3.0% (n=2) |
| time > 15 deg slip | 1.4% +- 1.4% (n=2) | 1.9% +- 1.0% (n=2) | 1.8% +- 0.6% (n=2) |
