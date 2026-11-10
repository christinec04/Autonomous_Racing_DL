#!/bin/bash
# Lane F2 (replaces lane F, which used `git pull --rebase --autostash`: on Windows that fails on log files held open
# by running trainings and leaves the repo mid-rebase). Every background job commits to this same clone, so the
# remote cannot get ahead; a plain push with retries is enough.
# Chicane fine-tuning (E22): seed 2 (already training when this lane started), then seed 1; race each with the final
# shield and with stall recovery.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
for s in 2 1; do
  run=ppo_shield_ft_chicane_s$s
  if [ $s = 2 ]; then
    until [ -f runs/$run/model_stage4.zip ]; do sleep 60; done
  elif [ ! -f runs/$run/model_stage4.zip ]; then
    $PY -m racing.train --init runs/ppo_shield_s$s/model_stage3.zip --shield cond_fb_grip_esc --tire saturated_v2 \
      --stages 4 --steps 500000 --n_envs 6 --seed $s --out runs/$run > runs/$run.log 2>&1
  fi
  $PY -m racing.evaluate --controllers "ppo_apf_esc@ft_s$s" "ppo_apf_rec@ft_s$s" \
    --models "ppo_apf_esc@ft_s$s=runs/$run/model_stage4.zip" "ppo_apf_rec@ft_s$s=runs/$run/model_stage4.zip" \
    --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_ft_chicane_s$s.json > runs/_eval_ft_chicane_s$s.log 2>&1
  git add runs/$run results/eval_ft_chicane_s$s.json runs/_eval_ft_chicane_s$s.log > /dev/null 2>&1
  git commit -q -m "Chicane fine-tuning (E22): seed $s trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
  push
  echo "$(date '+%H:%M') seed $s done" >> runs/_lane_f.log
done
