# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield (v1 sim) | PPO, no shield (v2 sim) |
|---|---|---|---|
| finished all laps / 20 | 8.3 +- 6.1 (n=3) | 6.7 +- 4.5 (n=3) | 1.5 +- 1.5 (n=2) |
| stuck / 20 | 3.0 +- 2.9 (n=3) | 10.0 +- 4.1 (n=3) | 0.5 +- 0.5 (n=2) |
| clean lap (s) | 37.52 +- 2.67 (n=3) | 36.32 +- 4.02 (n=3) | 33.69 +- 1.19 (n=2) |
| collisions / 10 laps | 2.04 +- 2.03 (n=3) | 0.74 +- 0.41 (n=3) | 5.29 +- 2.06 (n=2) |
| passes / race | 1.82 +- 0.88 (n=3) | 1.75 +- 0.73 (n=3) | 1.75 +- 0.40 (n=2) |
| overtake success | 81% +- 9% (n=3) | 81% +- 8% (n=3) | 91% +- 1% (n=2) |
| shield active | 8.7% +- 8.2% (n=3) | 11.8% +- 8.8% (n=3) | 0.0% +- 0.0% (n=2) |
| time > 90% grip | 34.4% +- 12.3% (n=3) | 30.3% +- 11.1% (n=3) | 36.5% +- 4.5% (n=2) |
| time > 15 deg slip | 3.0% +- 4.3% (n=3) | 1.4% +- 1.9% (n=3) | 1.0% +- 0.9% (n=2) |

## randomized

| metric | PPO + final shield (escape, v2 sim) | PPO + original shield (v1 sim) | PPO, no shield (v2 sim) |
|---|---|---|---|
| finished all laps / 20 | 6.7 +- 5.4 (n=3) | 4.3 +- 3.7 (n=3) | 2.5 +- 1.5 (n=2) |
| stuck / 20 | 1.0 +- 0.8 (n=3) | 11.7 +- 3.3 (n=3) | 0.0 +- 0.0 (n=2) |
| clean lap (s) | 36.08 +- 3.86 (n=3) | 38.36 +- 3.87 (n=2) | 36.39 +- 2.03 (n=2) |
| collisions / 10 laps | 3.14 +- 2.26 (n=3) | 1.48 +- 1.33 (n=3) | 5.31 +- 1.83 (n=2) |
| passes / race | 1.53 +- 0.77 (n=3) | 1.42 +- 0.80 (n=3) | 1.35 +- 0.40 (n=2) |
| overtake success | 71% +- 7% (n=3) | 81% +- 6% (n=3) | 75% +- 5% (n=2) |
| shield active | 7.7% +- 6.4% (n=3) | 13.2% +- 6.0% (n=3) | 0.0% +- 0.0% (n=2) |
| time > 90% grip | 27.3% +- 8.2% (n=3) | 23.9% +- 7.4% (n=3) | 30.3% +- 3.0% (n=2) |
| time > 15 deg slip | 1.0% +- 1.3% (n=3) | 1.4% +- 1.1% (n=3) | 1.8% +- 0.6% (n=2) |
