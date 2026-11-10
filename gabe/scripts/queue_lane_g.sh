#!/bin/bash
# Lane G: ResRace-style residual policy *trained* with our final shield (escape) on the v2 simulator (E23).
# Racing the residual policy with the shield added only at race time deadlocks or slides (E8, E21); this tests
# whether training with it fixes that. Waits until fewer than 3 trainings are running (memory).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
ntrain() { powershell -NoProfile -c "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -match 'racing.train' -and \$_.CommandLine -match 'venv' }).Count" | tr -d '\r'; }
while [ "$(ntrain)" -ge 3 ]; do sleep 300; done
run=ppo_residual_shield_s0
$PY -m racing.train --residual --shield cond_fb_grip_esc --tire saturated_v2 --stages 1 2 3 \
  --steps 1500000 1000000 1000000 --n_envs 7 --seed 0 --out runs/$run > runs/$run.log 2>&1
$PY -m racing.evaluate --controllers "ppo_residual_apf_rec@trained" "ppo_residual_apf_esc@trained" "ppo_residual@trained_noshield" \
  --models "ppo_residual_apf_rec@trained=runs/$run/model_stage3.zip" "ppo_residual_apf_esc@trained=runs/$run/model_stage3.zip" \
           "ppo_residual@trained_noshield=runs/$run/model_stage3.zip" \
  --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_residual_shield_s0.json > runs/_eval_residual_shield_s0.log 2>&1
git add runs/$run results/eval_residual_shield_s0.json runs/_eval_residual_shield_s0.log > /dev/null 2>&1
git commit -q -m "Residual policy trained with the shield (E23): trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
push
echo "$(date '+%H:%M') done" >> runs/_lane_g.log
