# Training efficiency (shield removed for every lap measurement)

Solo laps every 50k steps, standing start. 'fast' = under 34 s (best classical solo lap: 35.2 s).

| run | config | steps trained | first clean lap | first fast lap | crashes before first clean lap | crashes during training (episodes) | best lap |
|---|---|---|---|---|---|---|---|
| `ppo_additive_s0` | additive | 3500k | 150k | - | 783 | 2333 (5146) | 34.28 |
| `ppo_noshield_s0` | off | 3500k | 200k | 850k | 995 | 2318 (5249) | 27.60 |
| `ppo_noshield_s1` | off | 3500k | 200k | 600k | 1080 | 2769 (5517) | 28.60 |
| `ppo_noshield_s2` | off | 3500k | 150k | 550k | 969 | 2295 (5267) | 27.56 |
| `ppo_residual_s0` | off residual | 3500k | 50k | 350k | 259 | 995 (4141) | 29.80 |
| `ppo_shield_preview_s0` | cond_fb_grip | 1560k | 250k | 400k | 15 | 41 (1796) | 30.84 |
| `ppo_shield_s0` | cond_fb_grip | 3500k | 200k | 450k | 8 | 234 (4158) | 30.48 |
| `ppo_shield_s1` | cond_fb_grip | 3500k | 200k | 800k | 9 | 313 (4572) | 29.12 |
| `ppo_shield_s2` | cond_fb_grip | 3500k | 150k | 600k | 11 | 96 (3965) | 30.28 |
| `ppo_shield_v2esc_s0` | cond_fb_grip_esc tyre=saturated_v2 | 3500k | 150k | 150k | 76 | 497 (3821) | 31.48 |
| `ppo_shield_w3low_s0` | cond_fb_grip | 3500k | 450k | 500k | 24 | 405 (4981) | 28.24 |
| `ppo_shielddrop_s0` | cond_fb_grip drop=[1.0, 0.5, 0.25] | 80k | - | - | - | 5 (185) | - |
