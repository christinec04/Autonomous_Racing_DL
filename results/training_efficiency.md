# Training efficiency (shield removed for every lap measurement)

Solo laps every 50k steps, standing start. 'fast' = under 34 s (best classical solo lap: 35.2 s).

| run | config | steps trained | first clean lap | first fast lap | crashes before first clean lap | crashes during training (episodes) | best lap |
|---|---|---|---|---|---|---|---|
| `ppo_additive_s0` | additive | 3500k | 150k | - | 783 | 2333 (5146) | 34.28 |
| `ppo_additive_s1` | additive | 3120k | 150k | - | 703 | 1773 (4316) | 36.84 |
| `ppo_noshield_s0` | off | 3500k | 200k | 850k | 995 | 2318 (5249) | 27.60 |
| `ppo_noshield_s1` | off | 3500k | 200k | 600k | 1080 | 2769 (5517) | 28.60 |
| `ppo_noshield_s2` | off | 3500k | 150k | 550k | 969 | 2295 (5267) | 27.56 |
| `ppo_residual_s0` | off residual | 3500k | 50k | 350k | 259 | 995 (4141) | 29.80 |
| `ppo_residual_shield_s0` | cond_fb_grip_esc residual tyre=saturated_v2 | 3500k | 50k | 200k | 1 | 133 (3568) | 31.40 |
| `ppo_residual_shield_s1` | cond_fb_grip_esc residual tyre=saturated_v2 | 3500k | 50k | 250k | 0 | 81 (3545) | 31.52 |
| `ppo_residual_shield_s2` | cond_fb_grip_esc residual tyre=saturated_v2 | 3500k | 50k | 200k | 0 | 120 (3571) | 31.36 |
| `ppo_residual_wide_s0` | cond_fb_grip_esc residual scale=0.5 tyre=saturated_v2 | 3500k | 50k | 350k | 1 | 65 (3538) | 31.00 |
| `ppo_residual_wide_s1` | cond_fb_grip_esc residual scale=0.5 tyre=saturated_v2 | 3500k | 50k | 350k | 1 | 159 (3611) | 30.12 |
| `ppo_shield_ft2_chicane_s2` | cond_fb_grip_esc tyre=saturated_v2 | 300k | 50k | 50k | 9 | 96 (355) | 31.92 |
| `ppo_shield_ft_chicane_s2` | cond_fb_grip_esc tyre=saturated_v2 | 500k | 50k | 50k | 14 | 94 (547) | 30.36 |
| `ppo_shield_linear_s0` | cond_fb_grip tyre=linear | 3500k | 100k | 100k | 21 | 373 (4593) | 25.00 |
| `ppo_shield_preview_s0` | cond_fb_grip | 3500k | 250k | 400k | 15 | 174 (4103) | 30.00 |
| `ppo_shield_s0` | cond_fb_grip | 3500k | 200k | 450k | 8 | 234 (4158) | 30.48 |
| `ppo_shield_s1` | cond_fb_grip | 3500k | 200k | 800k | 9 | 313 (4572) | 29.12 |
| `ppo_shield_s2` | cond_fb_grip | 3500k | 150k | 600k | 11 | 96 (3965) | 30.28 |
| `ppo_shield_v2esc_s0` | cond_fb_grip_esc tyre=saturated_v2 | 3500k | 150k | 150k | 76 | 497 (3821) | 31.48 |
| `ppo_shield_v2esc_slip_s0` | cond_fb_grip_esc tyre=saturated_v2 | 3500k | 200k | 200k | 107 | 550 (3905) | 30.12 |
| `ppo_shield_v2esc_slip_s1` | cond_fb_grip_esc tyre=saturated_v2 | 3500k | 450k | 1000k | 140 | 339 (3740) | 30.08 |
| `ppo_shield_v2esc_slip_s2` | cond_fb_grip_esc tyre=saturated_v2 | 3500k | 250k | 1100k | 171 | 761 (3888) | 33.32 |
| `ppo_shield_w3low_s0` | cond_fb_grip | 3500k | 450k | 500k | 24 | 405 (4981) | 28.24 |
| `ppo_shielddrop_s0` | cond_fb_grip drop=[1.0, 0.5, 0.25] | 3500k | 150k | 650k | 8 | 561 (4046) | 29.32 |
