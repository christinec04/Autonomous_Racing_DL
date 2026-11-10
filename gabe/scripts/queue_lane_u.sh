#!/bin/bash
# Lane U (E36): candidate final shield, relaxed two-hypothesis opponent check + online friction estimate (oxmu),
# final controller 3 seeds: 50 races main protocol, then x0.8 and x0.7. Eval only, new files.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_u.log
S6="pid_apf ppo_apf_rec@s0 ppo_additive ppo_residual_apf_rec@trained ppo_residual_apf_rec@trained_s1 ppo_residual_apf_rec@trained_s2"
M6="ppo_apf_rec@s0=runs/ppo_shield_s0/model_stage3.zip ppo_additive=runs/ppo_additive_s0/model_stage3.zip \
ppo_residual_apf_rec@trained=runs/ppo_residual_shield_s0/model_stage3.zip \
ppo_residual_apf_rec@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
ppo_residual_apf_rec@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
V=ppo_residual_apf_rec_oxmu
S3="$V@trained $V@trained_s1 $V@trained_s2"
M3="$V@trained=runs/ppo_residual_shield_s0/model_stage3.zip $V@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
$V@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
run() {  # name, controllers, models, extra args, message
  out=results/$1.json
  [ -f $out ] && { echo "$(date +%H:%M) $1 exists, skipped" >> $LOG; return; }
  echo "$(date +%H:%M) $1 start" >> $LOG
  $PY -m racing.evaluate --controllers $2 --models $3 --races ${RACES:-20} --laps 5 --procs 6 --tire saturated_v2 $4 \
    --out $out > runs/_$1.log 2>&1
  echo "$(date +%H:%M) $1 done" >> $LOG
  git add $out runs/_$1.log && git commit -qm "$5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && { git push -q origin gabe-build || { sleep 20; git push -q origin gabe-build; }; } >> $LOG 2>&1
}
RACES=50 run eval_oxmu "$S3" "$M3" "" "Candidate final shield (E36): relaxed opponent check + friction estimate, 50 races"
run stress_mu0.8_oxmu "$S3" "$M3" "--mu_scale 0.8" "Candidate final shield (E36) at x0.8"
run stress_mu0.7_oxmu "$S3" "$M3" "--mu_scale 0.7" "Candidate final shield (E36) at x0.7"
echo "$(date +%H:%M) all done" >> $LOG
