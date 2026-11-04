#!/bin/bash
# Unshielded seed 2 on the v2 simulator, after the seed-2 final-shield evaluation (one evaluation at a time).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
until [ -f results/eval_escape_v4_s2.json ]; do sleep 60; done
$PY -m racing.evaluate --controllers "ppo@s2v2" --models "ppo@s2v2=runs/ppo_noshield_s2/model_stage3.zip" \
  --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/final_v2_noshield_s2.json > runs/_final_v2_noshield_s2_stdout.log 2>&1
$PY -m scripts.seed_summary > /dev/null 2>&1
git add results && git commit -q -m "Auto: unshielded seed 2 on v2; seed summary refreshed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q
