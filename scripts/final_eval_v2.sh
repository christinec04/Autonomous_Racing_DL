#!/bin/bash
# Re-race every existing controller on the post-spin-fixed simulator (saturated_v2) so final tables use one
# simulator version. 3 processes (memory). Final-shield runs (eval_escape_v4*) are already on v2.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
$PY -m racing.evaluate --controllers pure_pursuit pid_apf "ppo@s0" "ppo@s1" ppo_residual ppo_additive \
  --models "ppo@s0=runs/ppo_noshield_s0/model_stage3.zip" "ppo@s1=runs/ppo_noshield_s1/model_stage3.zip" \
           ppo_residual=runs/ppo_residual_s0/model_stage3.zip ppo_additive=runs/ppo_additive_s0/model_stage3.zip \
  --races 20 --laps 5 --procs 3 --tire saturated_v2 --out results/final_v2_others.json > runs/_final_v2_others_stdout.log 2>&1
