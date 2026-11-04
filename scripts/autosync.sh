#!/bin/bash
# Every 20 min: refresh RUNS.md + training curves, commit and push run progress (runs/, RUNS.md, curves only).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
while true; do
  $PY -m scripts.update_registry > /dev/null 2>&1
  $PY -m scripts.plot_training > /dev/null 2>&1
  git add runs RUNS.md results/training_curves.png > /dev/null 2>&1
  if ! git diff --cached --quiet; then
    git commit -q -m "Auto-sync training progress ($(date '+%H:%M'))

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q > /dev/null 2>&1 && echo "$(date '+%H:%M') pushed"
  fi
  # stop once every queued run has finished
  if [ -f runs/ppo_shield_s2/model_stage3.zip ] && [ -f runs/ppo_noshield_s2/model_stage3.zip ]; then echo done; break; fi
  sleep 1200
done
