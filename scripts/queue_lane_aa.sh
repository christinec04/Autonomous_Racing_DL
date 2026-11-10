#!/bin/bash
# Lane AA (E37 follow-up): do the wide-friction policies (E37 B, seeds 0-2) hold up on the unseen track (Track2) and
# with five opponents? The E29 policies (seeds 0-2) are raced with the same combined shield for comparison.
# 20 race seeds x 5 laps, nominal + randomised. Starts after lane Y. Eval only, new result files.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_aa.log
until grep -q "all done" runs/_lane_y.log 2>/dev/null; do sleep 120; done
V=ppo_residual_apf_rec_oxmu
C="$V@trained $V@trained_s1 $V@trained_s2 $V@widemu_s0 $V@widemu_s1 $V@widemu_s2"
M="$V@trained=runs/ppo_residual_shield_s0/model_stage3.zip $V@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
$V@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip $V@widemu_s0=runs/ppo_residual_oxmu_widemu_s0/model_stage3.zip \
$V@widemu_s1=runs/ppo_residual_oxmu_widemu_s1/model_stage3.zip $V@widemu_s2=runs/ppo_residual_oxmu_widemu_s2/model_stage3.zip"
run() {  # name, extra args, message
  out=results/$1.json
  [ -f $out ] && { echo "$(date +%H:%M) $1 exists, skipped" >> $LOG; return; }
  echo "$(date +%H:%M) $1 start" >> $LOG
  $PY -m racing.evaluate --controllers $C --models $M --races 20 --laps 5 --procs 6 --tire saturated_v2 $2 \
    --out $out > runs/_$1.log 2>&1
  echo "$(date +%H:%M) $1 done" >> $LOG
  git add $out runs/_$1.log $LOG && git commit -qm "$3

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
}
run eval_widemu_Track2 "--map Track2" "E37 B vs E29 policies on the unseen track (Track2), combined shield"
run stress_opp5_widemu "--n_opp 5" "E37 B vs E29 policies with five opponents, combined shield"
echo "$(date +%H:%M) all done" >> $LOG
