#!/bin/bash
# Lane J (E30): the final controller with a wider residual (--residual_scale 0.5 instead of 0.3), to see whether
# letting the policy add more to the PID+APF base raises grip use (E29 missed the >= 10% target) without losing
# consistency. Seeds 0 and 1 train in parallel, then each is raced (20 races x 5 laps, with and without the shield).
# Push-only git (PROGRESS.md problem 31).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
one() {
  s=$1; run=ppo_residual_wide_s$s
  [ -f runs/$run/model_stage3.zip ] || $PY -m racing.train --residual --residual_scale 0.5 --shield cond_fb_grip_esc \
    --tire saturated_v2 --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --seed $s --out runs/$run > runs/$run.log 2>&1
  $PY -m racing.evaluate --controllers "ppo_residual_apf_rec@wide_s$s" "ppo_residual@wide_s${s}_noshield" \
    --models "ppo_residual_apf_rec@wide_s$s=runs/$run/model_stage3.zip" "ppo_residual@wide_s${s}_noshield=runs/$run/model_stage3.zip" \
    --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_residual_wide_s$s.json > runs/_eval_residual_wide_s$s.log 2>&1
  echo "$(date '+%H:%M') seed $s done" >> runs/_lane_j.log
}
one 0 & one 1 & wait
git add runs/ppo_residual_wide_s0 runs/ppo_residual_wide_s1 runs/ppo_residual_wide_s*.log results/eval_residual_wide_s*.json \
  runs/_eval_residual_wide_s*.log runs/_lane_j.log > /dev/null 2>&1
git commit -q -m "Wider residual (E30, --residual_scale 0.5) trained with the shield, seeds 0-1: trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
push
echo "$(date '+%H:%M') all done" >> runs/_lane_j.log
