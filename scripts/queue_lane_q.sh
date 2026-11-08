#!/bin/bash
# Lane Q: rerun of lane K's last job (ppo_residual_s2), lost when the laptop shut down on Nov 8 (PROGRESS 38).
# Same recipe as seeds 0-1, trained from scratch, then raced on Singapore and Track2. Push-only git.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_q.log
run=ppo_residual_s2; s=2; ctrl=ppo_residual
echo "$(date +%H:%M) $run train start" >> $LOG
[ -f runs/$run/model_stage3.zip ] || $PY -m racing.train --shield off --residual --stages 1 2 3 \
  --steps 1500000 1000000 1000000 --n_envs 7 --seed $s --out runs/$run > runs/$run.log 2>&1
echo "$(date +%H:%M) $run train done" >> $LOG
for map in Singapore Track2; do
  $PY -m racing.evaluate --map $map --controllers "$ctrl@s$s" --models "$ctrl@s$s=runs/$run/model_stage3.zip" \
    --races 20 --laps 5 --procs 4 --tire saturated_v2 --out results/eval_${run}_$map.json > runs/_eval_${run}_$map.log 2>&1
done
git add runs/$run runs/$run.log results/eval_${run}_*.json runs/_eval_${run}_*.log scripts/queue_lane_q.sh $LOG > /dev/null 2>&1
git commit -q -m "Baseline seed $s ($run): trained and raced on Singapore and Track2

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
for i in 1 2 3 4 5; do git push -q origin gabe-build > /dev/null 2>&1 && break; sleep 30; done
echo "$(date +%H:%M) all done" >> $LOG
