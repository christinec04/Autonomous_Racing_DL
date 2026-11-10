#!/bin/bash
# Lane I: the slip penalty (w6 = 1) fixed the sliding seed 1 (1/20 -> 17/20 finished). Is it a better recipe in
# general? Race slip_s1 with the stall recovery, then train seeds 0 and 2 with the same recipe and race them.
# Waits until fewer than 3 trainings run. Push-only git (PROGRESS.md problem 31).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
ntrain() { powershell -NoProfile -c "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -match 'racing.train' -and \$_.CommandLine -match 'venv' }).Count" | tr -d '\r'; }
race() {  # run label
  $PY -m racing.evaluate --controllers "ppo_apf_rec@$2" --models "ppo_apf_rec@$2=runs/$1/model_stage3.zip" \
    --races 20 --laps 5 --procs 3 --tire saturated_v2 --out results/eval_slip_rec_$2.json > runs/_eval_slip_rec_$2.log 2>&1
  git add results/eval_slip_rec_$2.json runs/_eval_slip_rec_$2.log runs/$1 > /dev/null 2>&1
  git commit -q -m "Slip-penalty recipe (E26): $1 raced with stall recovery

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1; push
}
race ppo_shield_v2esc_slip_s1 slip_s1
for s in 0 2; do
  run=ppo_shield_v2esc_slip_s$s
  while [ "$(ntrain)" -ge 3 ]; do sleep 300; done
  [ -f runs/$run/model_stage3.zip ] || $PY -m racing.train --shield cond_fb_grip_esc --tire saturated_v2 --w6 1.0 \
    --stages 1 2 3 --steps 1500000 1000000 1000000 --n_envs 7 --seed $s --out runs/$run > runs/$run.log 2>&1
  race $run slip_s$s
  echo "$(date '+%H:%M') seed $s done" >> runs/_lane_i.log
done
