#!/bin/bash
# Lane C: shield dropout experiment, after lane A's last run.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
S="--stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7"
until [ -f runs/ppo_shield_s2/model_stage3.zip ]; do sleep 60; done
$PY -m racing.train --shield cond_fb_grip --shield_prob 1.0 0.5 0.25 $S --seed 0 --out runs/ppo_shielddrop_s0 > runs/ppo_shielddrop_s0.log 2>&1
