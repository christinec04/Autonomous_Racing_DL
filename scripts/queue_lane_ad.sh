#!/bin/bash
# Lane AD (E39, queued 2026-11-10): the classical base controllers have planned their speeds with the TRUE friction
# since Nov 4 (EnvConfig.base_mu, PROGRESS 44) - privileged knowledge a real car does not have. How much of the
# stress-test performance rests on it? Rerun the stress settings with the base planning on the nominal friction
# ("nominal") and on the shield's online friction estimate ("estimate"). Controllers: E29 policies (seeds 0-2),
# E37 B policies (seeds 0-2), all with the combined shield, and PID+APF (no estimate: "estimate" = "nominal" for
# it, so it runs once). 20 race seeds each. Starts after lane AB. Eval only, new result files.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_ad.log
until grep -q "all done" runs/_lane_ab.log 2>/dev/null; do sleep 120; done
V=ppo_residual_apf_rec_oxmu
C="$V@trained $V@trained_s1 $V@trained_s2 $V@widemu_s0 $V@widemu_s1 $V@widemu_s2"
M="$V@trained=runs/ppo_residual_shield_s0/model_stage3.zip $V@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
$V@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip $V@widemu_s0=runs/ppo_residual_oxmu_widemu_s0/model_stage3.zip \
$V@widemu_s1=runs/ppo_residual_oxmu_widemu_s1/model_stage3.zip $V@widemu_s2=runs/ppo_residual_oxmu_widemu_s2/model_stage3.zip"
run() {  # name, controllers, models, extra args, message
  out=results/$1.json
  [ -f $out ] && { echo "$(date +%H:%M) $1 exists, skipped" >> $LOG; return; }
  echo "$(date +%H:%M) $1 start" >> $LOG
  $PY -m racing.evaluate --controllers $2 --models $3 --races 20 --laps 5 --procs 7 --tire saturated_v2 $4 \
    --out $out > runs/_$1.log 2>&1
  echo "$(date +%H:%M) $1 done" >> $LOG
  git add $out runs/_$1.log $LOG && git commit -qm "$5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
}
for mu in 0.7 0.8 0.6; do
  for b in nominal estimate; do
    run stress_mu${mu}_base${b} "$C" "$M" "--mu_scale $mu --base_mu $b" "E39: E29 and E37 B policies at friction x$mu, base controller planning with the $b friction"
  done
  run stress_mu${mu}_pidapf_basenominal "pid_apf" "" "--mu_scale $mu --base_mu nominal" "E39: PID+APF at friction x$mu planning with the nominal friction"
done
echo "$(date +%H:%M) all done" >> $LOG
