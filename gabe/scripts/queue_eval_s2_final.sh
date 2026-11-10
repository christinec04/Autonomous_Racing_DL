#!/bin/bash
# After seed 2 finishes and the daemon has raced it (original shield), race it with the final shield on v2.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
until [ -f results/eval_ppo_shield_s2.json ] && [ -f results/final_v2_others.json ]; do sleep 60; done
$PY -m racing.evaluate --controllers "ppo_apf_esc@s2" --models "ppo_apf_esc@s2=runs/ppo_shield_s2/model_stage3.zip" \
  --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_escape_v4_s2.json > runs/_eval_escape_v4_s2_stdout.log 2>&1
$PY -m scripts.seed_summary > /dev/null 2>&1
bash scripts/final_tables.sh > /dev/null 2>&1
git add results && git commit -q -m "Auto: seed 2 with the final shield; seed summary and final tables refreshed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q
