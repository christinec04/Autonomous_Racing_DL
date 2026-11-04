# Training efficiency (shield removed for every lap measurement)

Solo laps every 50k steps, standing start. 'fast' = under 34 s (best classical solo lap: 35.2 s).

| run | config | steps trained | first clean lap | first fast lap | crashes before first clean lap | crashes during training (episodes) | best lap |
|---|---|---|---|---|---|---|---|
| `ppo_noshield_s0` | off | 3500k | 200k | 850k | 995 | 2318 (5249) | 27.60 |
| `ppo_noshield_s1` | off | 580k | 200k | - | 1080 | 1178 (1620) | 34.28 |
| `ppo_residual_s0` | off residual | 3500k | 50k | 350k | 259 | 995 (4141) | 29.80 |
| `ppo_shield_s0` | cond_fb_grip | 3500k | 200k | 450k | 8 | 234 (4158) | 30.48 |
| `ppo_shield_s1` | cond_fb_grip | 2660k | 200k | 800k | 9 | 177 (3361) | 30.72 |
