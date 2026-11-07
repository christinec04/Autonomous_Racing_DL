#!/bin/bash
# Lane L (E32): is it our shield or any shield? The final recipe (residual policy trained with a shield) but with the
# proposal's additive Eq. 2/3 shield instead of the action-conditioned one, seeds 0 and 1 in parallel, v2 simulator.
# Raced on Singapore (20 races x 5 laps) with that shield. Push-only git (PROGRESS.md problem 31).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
one() {
  s=$1; run=ppo_residual_additive_s$s
  [ -f runs/$run/model_stage3.zip ] || $PY -m racing.train --residual --shield additive --tire saturated_v2 \
    --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --seed $s --out runs/$run > runs/$run.log 2>&1
  $PY -m racing.evaluate --controllers "ppo_residual_additive@s$s" --models "ppo_residual_additive@s$s=runs/$run/model_stage3.zip" \
    --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_$run.json > runs/_eval_$run.log 2>&1
  echo "$(date '+%H:%M') seed $s done" >> runs/_lane_l.log
}
one 0 & one 1 & wait
git add runs/ppo_residual_additive_s0 runs/ppo_residual_additive_s1 runs/ppo_residual_additive_s*.log \
  results/eval_ppo_residual_additive_s*.json runs/_eval_ppo_residual_additive_s*.log runs/_lane_l.log > /dev/null 2>&1
git commit -q -m "Residual policy trained with the additive shield (E32), seeds 0-1: trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
push
echo "$(date '+%H:%M') all done" >> runs/_lane_l.log
