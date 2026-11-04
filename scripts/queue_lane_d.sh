#!/bin/bash
# Lane D: does PPO exploit the stock linear tyres (Evans et al. loophole)? Runs after lane C.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
S="--stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7"
until [ -f runs/ppo_shielddrop_s0/model_stage3.zip ]; do sleep 60; done
$PY -m racing.train --shield cond_fb_grip --tire linear $S --seed 0 --out runs/ppo_shield_linear_s0 > runs/ppo_shield_linear_s0.log 2>&1
