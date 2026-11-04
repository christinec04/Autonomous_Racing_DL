#!/bin/bash
# Lane E: is the shielded agent's timidity (top speed ~8.4 m/s) caused by the intervention penalty or short preview?
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
S="--stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7"
until [ -f runs/ppo_noshield_s2/model_stage3.zip ]; do sleep 60; done
$PY -m racing.train --shield cond_fb_grip --w3 0.02 $S --seed 0 --out runs/ppo_shield_w3low_s0 > runs/ppo_shield_w3low_s0.log 2>&1
$PY -m racing.train --shield cond_fb_grip --curvature_preview $S --seed 0 --out runs/ppo_shield_preview_s0 > runs/ppo_shield_preview_s0.log 2>&1
$PY -m racing.train --shield cond_fb_grip_esc --tire saturated_v2 --w6 1.0 $S --seed 1 --out runs/ppo_shield_v2esc_slip_s1 > runs/ppo_shield_v2esc_slip_s1.log 2>&1
