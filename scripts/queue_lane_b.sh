#!/bin/bash
# Lane B: waits for the residual run, then the unshielded seeds.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
S="--stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7"
until [ -f runs/ppo_residual_s0/model_stage3.zip ]; do sleep 60; done
$PY -m racing.train --shield off $S --seed 1 --out runs/ppo_noshield_s1 > runs/ppo_noshield_s1.log 2>&1
$PY -m racing.train --shield off $S --seed 2 --out runs/ppo_noshield_s2 > runs/ppo_noshield_s2.log 2>&1
