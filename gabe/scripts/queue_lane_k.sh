#!/bin/bash
# Lane K: seeds 1 and 2 of the learned baselines that only had seed 0 (PPO + additive Eq. 2/3 shield, ResRace-style
# residual PPO without a shield), same recipe as seed 0, so every learned controller has 3 training seeds for the
# final evaluation. Each is raced on Singapore and Track2 (20 races x 5 laps, v2 simulator). Waits until fewer than
# 3 trainings are running. Push-only git (PROGRESS.md problem 31).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
push() { for i in 1 2 3 4 5; do git push -q > /dev/null 2>&1 && return 0; sleep 30; done; return 1; }
ntrain() { powershell -NoProfile -c "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -match 'racing.train' -and \$_.CommandLine -match 'venv' }).Count" | tr -d '\r'; }
for job in "additive 1" "residual 1" "additive 2" "residual 2"; do
  set -- $job; kind=$1; s=$2
  if [ $kind = additive ]; then run=ppo_additive_s$s; flags="--shield additive"; ctrl=ppo_additive
  else run=ppo_residual_s$s; flags="--shield off --residual"; ctrl=ppo_residual; fi
  while [ "$(ntrain)" -ge 3 ]; do sleep 300; done
  [ -f runs/$run/model_stage3.zip ] || $PY -m racing.train $flags --stages 1 2 3 --steps 1500000 1000000 1000000 \
    --n_envs 7 --seed $s --out runs/$run > runs/$run.log 2>&1
  for map in Singapore Track2; do
    $PY -m racing.evaluate --map $map --controllers "$ctrl@s$s" --models "$ctrl@s$s=runs/$run/model_stage3.zip" \
      --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_${run}_$map.json > runs/_eval_${run}_$map.log 2>&1
  done
  git add runs/$run runs/$run.log results/eval_${run}_*.json runs/_eval_${run}_*.log > /dev/null 2>&1
  git commit -q -m "Baseline seed $s ($run): trained and raced on Singapore and Track2

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
  push
  echo "$(date '+%H:%M') $run done" >> runs/_lane_k.log
done
