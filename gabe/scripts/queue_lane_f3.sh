#!/bin/bash
# Lane F3: gentler chicane fine-tuning (E22b). E22 (lr 3e-4, 500k steps) taught the seed-2 policy to slide and made it
# worse (19/20 -> 8/20 finished with recovery). Retry: lr 5e-5 (6x lower), slip penalty w6 = 1, 300k steps.
# Waits until fewer than 3 trainings are running (memory). Push-only git (see PROGRESS.md problem 31).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
ntrain() { powershell -NoProfile -c "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -match 'racing.train' -and \$_.CommandLine -match 'venv' }).Count" | tr -d '\r'; }
while [ "$(ntrain)" -ge 3 ]; do sleep 300; done
run=ppo_shield_ft2_chicane_s2
$PY -m racing.train --init runs/ppo_shield_s2/model_stage3.zip --shield cond_fb_grip_esc --tire saturated_v2 \
  --stages 4 --steps 300000 --lr 5e-5 --w6 1.0 --n_envs 6 --seed 2 --out runs/$run > runs/$run.log 2>&1
$PY -m racing.evaluate --controllers "ppo_apf_esc@ft2_s2" "ppo_apf_rec@ft2_s2" \
  --models "ppo_apf_esc@ft2_s2=runs/$run/model_stage4.zip" "ppo_apf_rec@ft2_s2=runs/$run/model_stage4.zip" \
  --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_ft2_chicane_s2.json > runs/_eval_ft2_chicane_s2.log 2>&1
git add runs/$run results/eval_ft2_chicane_s2.json runs/_eval_ft2_chicane_s2.log > /dev/null 2>&1
git commit -q -m "Gentler chicane fine-tuning (E22b): seed 2 trained and raced

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
push
echo "$(date '+%H:%M') done" >> runs/_lane_f3.log
