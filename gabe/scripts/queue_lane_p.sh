#!/bin/bash
# E34b: two-hypothesis opponent check that relaxes to braking-only when nothing is safe under both (opp_relax),
# final controller seeds 0-2 on 50 race seeds. Waits for lane O (memory). Eval only.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_p.log
until grep -q "all done" runs/_lane_o.log 2>/dev/null; do sleep 120; done
for s in 0 1 2; do
  out=results/eval_opprelax_s$s.json
  [ -f $out ] && continue
  echo "$(date +%H:%M) seed $s start" >> $LOG
  $PY -m racing.evaluate --controllers ppo_residual_apf_rec_ox@trained_s$s \
    --models ppo_residual_apf_rec_ox@trained_s$s=runs/ppo_residual_shield_s$s/model_stage3.zip \
    --races 50 --laps 5 --procs 6 --tire saturated_v2 --out $out > runs/_opprelax_s$s.log 2>&1
  echo "$(date +%H:%M) seed $s done" >> $LOG
  git add $out && git commit -qm "Final controller with the relaxed two-hypothesis opponent check (E34b), seed $s, 50 races

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin gabe-build >> $LOG 2>&1
done
echo "$(date +%H:%M) all done" >> $LOG
