#!/bin/bash
# Every 20 min: refresh RUNS.md + training curves, commit and push run progress (runs/, RUNS.md, curves only).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
while true; do
  $PY -m scripts.update_registry > /dev/null 2>&1
  $PY -m scripts.plot_training > /dev/null 2>&1
  $PY -m scripts.training_efficiency > /dev/null 2>&1
  git add runs RUNS.md results/training_curves.png results/training_efficiency.md > /dev/null 2>&1
  if ! git diff --cached --quiet; then
    git commit -q -m "Auto-sync training progress ($(date '+%H:%M'))

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q > /dev/null 2>&1 && echo "$(date '+%H:%M') pushed"
  fi
  # stop once every queued run has finished
  done_all=1; for r in ppo_shield_s1 ppo_shield_s2 ppo_noshield_s1 ppo_noshield_s2 ppo_additive_s0 ppo_shielddrop_s0 ppo_shield_linear_s0 ppo_shield_v2esc_s0 ppo_shield_w3low_s0 ppo_shield_preview_s0 ppo_shield_v2esc_slip_s1; do [ -f runs/$r/model_stage3.zip ] || done_all=0; done
  if [ $done_all = 1 ]; then echo done; break; fi
  sleep 1200
done
