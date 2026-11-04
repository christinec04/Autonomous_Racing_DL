#!/bin/bash
# Run evaluations one at a time (memory): wait for E15, then the residual race evaluation.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
until [ -f results/shield_confirm.json ]; do sleep 30; done
$PY -m racing.evaluate --controllers ppo_residual --models ppo_residual=runs/ppo_residual_s0/model_stage3.zip \
    --races 20 --laps 5 --procs 4 --out results/eval_residual_s0.json > runs/_eval_residual_s0_stdout.log 2>&1
