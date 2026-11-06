# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)

## nominal

| metric | PPO + shield + escape + stall recovery (final, v2 sim) | PPO + shield + escape (v2 sim) | PPO + original shield (v1 sim) | PPO, no shield (v2 sim) |
|---|---|---|---|---|
| finished all laps / 20 | 13.0 +- 8.5 (n=3) | 8.3 +- 6.1 (n=3) | 6.7 +- 4.5 (n=3) | 3.0 +- 2.4 (n=3) |
| stuck / 20 | 0.3 +- 0.5 (n=3) | 3.0 +- 2.9 (n=3) | 10.0 +- 4.1 (n=3) | 0.3 +- 0.5 (n=3) |
| clean lap (s) | 38.11 +- 3.58 (n=3) | 37.52 +- 2.67 (n=3) | 36.32 +- 4.02 (n=3) | 38.48 +- 6.83 (n=3) |
| collisions / 10 laps | 1.63 +- 2.16 (n=3) | 2.04 +- 2.03 (n=3) | 0.74 +- 0.41 (n=3) | 4.38 +- 2.12 (n=3) |
| passes / race | 2.10 +- 0.76 (n=3) | 1.82 +- 0.88 (n=3) | 1.75 +- 0.73 (n=3) | 1.25 +- 0.78 (n=3) |
| overtake success | 80% +- 9% (n=3) | 81% +- 9% (n=3) | 81% +- 8% (n=3) | 81% +- 13% (n=3) |
| shield active | 9.0% +- 9.5% (n=3) | 8.7% +- 8.2% (n=3) | 11.8% +- 8.8% (n=3) | 0.0% +- 0.0% (n=3) |
| time > 90% grip | 35.5% +- 13.3% (n=3) | 34.4% +- 12.3% (n=3) | 30.3% +- 11.1% (n=3) | 27.3% +- 13.5% (n=3) |
| time > 15 deg slip | 4.9% +- 6.9% (n=3) | 3.0% +- 4.3% (n=3) | 1.4% +- 1.9% (n=3) | 0.7% +- 0.9% (n=3) |

## randomized

| metric | PPO + shield + escape + stall recovery (final, v2 sim) | PPO + shield + escape (v2 sim) | PPO + original shield (v1 sim) | PPO, no shield (v2 sim) |
|---|---|---|---|---|
| finished all laps / 20 | 11.0 +- 5.7 (n=3) | 6.7 +- 5.4 (n=3) | 4.3 +- 3.7 (n=3) | 4.3 +- 2.9 (n=3) |
| stuck / 20 | 0.0 +- 0.0 (n=3) | 1.0 +- 0.8 (n=3) | 11.7 +- 3.3 (n=3) | 0.0 +- 0.0 (n=3) |
| clean lap (s) | 36.99 +- 4.84 (n=3) | 36.08 +- 3.86 (n=3) | 38.36 +- 3.87 (n=2) | 40.09 +- 5.49 (n=3) |
| collisions / 10 laps | 2.04 +- 2.03 (n=3) | 3.14 +- 2.26 (n=3) | 1.48 +- 1.33 (n=3) | 4.27 +- 2.09 (n=3) |
| passes / race | 1.80 +- 0.82 (n=3) | 1.53 +- 0.77 (n=3) | 1.42 +- 0.80 (n=3) | 0.95 +- 0.65 (n=3) |
| overtake success | 71% +- 9% (n=3) | 71% +- 7% (n=3) | 81% +- 6% (n=3) | 59% +- 23% (n=3) |
| shield active | 8.0% +- 7.2% (n=3) | 7.7% +- 6.4% (n=3) | 13.2% +- 6.0% (n=3) | 0.0% +- 0.0% (n=3) |
| time > 90% grip | 28.5% +- 9.2% (n=3) | 27.3% +- 8.2% (n=3) | 23.9% +- 7.4% (n=3) | 22.8% +- 10.9% (n=3) |
| time > 15 deg slip | 2.6% +- 3.6% (n=3) | 1.0% +- 1.3% (n=3) | 1.4% +- 1.1% (n=3) | 1.2% +- 1.0% (n=3) |
