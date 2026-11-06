#!/bin/bash
# Lane H: seeds 1 and 2 of the residual policy trained with our shield (E23 was seed 0 only). One at a time; waits
# until fewer than 3 trainings are running. Push-only git (PROGRESS.md problem 31).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
ntrain() { powershell -NoProfile -c "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -match 'racing.train' -and \$_.CommandLine -match 'venv' }).Count" | tr -d '\r'; }
for s in 1 2; do
  run=ppo_residual_shield_s$s
  while [ "$(ntrain)" -ge 3 ]; do sleep 300; done
  [ -f runs/$run/model_stage3.zip ] || $PY -m racing.train --residual --shield cond_fb_grip_esc --tire saturated_v2 \
    --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --seed $s --out runs/$run > runs/$run.log 2>&1
  $PY -m racing.evaluate --controllers "ppo_residual_apf_rec@trained_s$s" "ppo_residual@trained_s${s}_noshield" \
    --models "ppo_residual_apf_rec@trained_s$s=runs/$run/model_stage3.zip" "ppo_residual@trained_s${s}_noshield=runs/$run/model_stage3.zip" \
    --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_residual_shield_s$s.json > runs/_eval_residual_shield_s$s.log 2>&1
  git add runs/$run results/eval_residual_shield_s$s.json runs/_eval_residual_shield_s$s.log > /dev/null 2>&1
  git commit -q -m "Residual policy trained with the shield (E23), seed $s: trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
  push
  echo "$(date '+%H:%M') seed $s done" >> runs/_lane_h.log
done
