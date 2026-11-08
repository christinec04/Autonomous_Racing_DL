#!/bin/bash
# E34: final controller with the two-hypothesis opponent check (opp_both), seeds 0-2, 50 race seeds. Eval only.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_n.log
until [ -f results/eval_zero_residual.json ]; do sleep 60; done
for s in 0 1 2; do
  out=results/eval_oppboth_s$s.json
  [ -f $out ] && continue
  echo "$(date +%H:%M) seed $s start" >> $LOG
  $PY -m racing.evaluate --controllers ppo_residual_apf_rec_ob@trained_s$s \
    --models ppo_residual_apf_rec_ob@trained_s$s=runs/ppo_residual_shield_s$s/model_stage3.zip \
    --races 50 --laps 5 --procs 6 --tire saturated_v2 --out $out > runs/_oppboth_s$s.log 2>&1
  echo "$(date +%H:%M) seed $s done" >> $LOG
  git add $out && git commit -qm "Final controller with the two-hypothesis opponent check (E34), seed $s, 50 races

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin gabe-build >> $LOG 2>&1
done
echo "$(date +%H:%M) all done" >> $LOG
