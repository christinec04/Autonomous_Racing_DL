#!/bin/bash
# Lane F: chicane fine-tuning (E22). Waits for the stall-recovery evaluation to finish (memory), then fine-tunes the
# seed-2 and seed-1 shielded policies with hotspot starts and races each with the final shield and with recovery.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
until [ -f results/eval_recover.json ]; do sleep 60; done
for s in 2 1; do
  run=ppo_shield_ft_chicane_s$s
  if [ ! -f runs/$run/model_stage4.zip ]; then
    $PY -m racing.train --init runs/ppo_shield_s$s/model_stage3.zip --shield cond_fb_grip_esc --tire saturated_v2 \
      --stages 4 --steps 500000 --n_envs 6 --seed $s --out runs/$run > runs/$run.log 2>&1
  fi
  $PY -m racing.evaluate --controllers "ppo_apf_esc@ft_s$s" "ppo_apf_rec@ft_s$s" \
    --models "ppo_apf_esc@ft_s$s=runs/$run/model_stage4.zip" "ppo_apf_rec@ft_s$s=runs/$run/model_stage4.zip" \
    --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_ft_chicane_s$s.json > runs/_eval_ft_chicane_s$s.log 2>&1
  git add runs/$run results/eval_ft_chicane_s$s.json runs/_eval_ft_chicane_s$s.log > /dev/null 2>&1
  git commit -q -m "Chicane fine-tuning (E22): seed $s trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
  git pull -q --rebase --autostash > /dev/null 2>&1; git push -q > /dev/null 2>&1
  echo "$(date '+%H:%M') seed $s done" >> runs/_lane_f.log
done
