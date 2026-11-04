# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield | PPO, no shield |
|---|---|---|---|
| finished all laps / 20 | 8.5 +- 7.5 (n=2) | 6.5 +- 5.5 (n=2) | 3.0 +- 1.6 (n=3) |
| stuck / 20 | 1.0 +- 1.0 (n=2) | 10.0 +- 5.0 (n=2) | 0.3 +- 0.5 (n=3) |
| clean lap (s) | 35.80 +- 1.32 (n=2) | 33.51 +- 0.80 (n=2) | 40.16 +- 5.74 (n=3) |
| collisions / 10 laps | 2.67 +- 2.23 (n=2) | 0.85 +- 0.46 (n=2) | 3.88 +- 1.18 (n=3) |
| passes / race | 2.33 +- 0.63 (n=2) | 2.20 +- 0.45 (n=2) | 1.20 +- 0.80 (n=3) |
| overtake success | 77% +- 8% (n=2) | 79% +- 9% (n=2) | 74% +- 6% (n=3) |
| shield active | 11.7% +- 8.5% (n=2) | 15.2% +- 9.0% (n=2) | 0.0% +- 0.0% (n=3) |
| time > 90% grip | 29.4% +- 12.2% (n=2) | 23.5% +- 6.8% (n=2) | 27.1% +- 13.1% (n=3) |
| time > 15 deg slip | 4.6% +- 4.6% (n=2) | 2.0% +- 2.0% (n=2) | 0.6% +- 0.7% (n=3) |

## randomized

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield | PPO, no shield |
|---|---|---|---|
| finished all laps / 20 | 7.5 +- 6.5 (n=2) | 4.5 +- 4.5 (n=2) | 5.0 +- 2.9 (n=3) |
| stuck / 20 | 1.0 +- 1.0 (n=2) | 10.5 +- 3.5 (n=2) | 0.0 +- 0.0 (n=3) |
| clean lap (s) | 33.41 +- 0.95 (n=2) | 34.49 (n=1) | 39.50 +- 6.33 (n=3) |
| collisions / 10 laps | 3.47 +- 2.71 (n=2) | 2.00 +- 1.36 (n=2) | 3.93 +- 2.00 (n=3) |
| passes / race | 1.90 +- 0.70 (n=2) | 1.82 +- 0.68 (n=2) | 1.12 +- 0.63 (n=3) |
| overtake success | 68% +- 8% (n=2) | 78% +- 6% (n=2) | 76% +- 9% (n=3) |
| shield active | 10.2% +- 6.5% (n=2) | 16.0% +- 5.5% (n=2) | 0.0% +- 0.0% (n=3) |
| time > 90% grip | 23.5% +- 7.6% (n=2) | 19.6% +- 5.0% (n=2) | 23.0% +- 10.5% (n=3) |
| time > 15 deg slip | 1.4% +- 1.4% (n=2) | 1.9% +- 1.0% (n=2) | 1.3% +- 1.0% (n=3) |
