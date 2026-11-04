#!/bin/bash
# Lane A: run sequentially. Each run records its own provenance in runs/<run>/run_info.json.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
S="--stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7"
$PY -m racing.train --shield cond_fb_grip $S --seed 1 --out runs/ppo_shield_s1 > runs/ppo_shield_s1.log 2>&1
$PY -m racing.train --shield additive     $S --seed 0 --out runs/ppo_additive_s0 > runs/ppo_additive_s0.log 2>&1
$PY -m racing.train --shield cond_fb_grip $S --seed 2 --out runs/ppo_shield_s2 > runs/ppo_shield_s2.log 2>&1
