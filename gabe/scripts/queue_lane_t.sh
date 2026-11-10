#!/bin/bash
# Lane T: E33 opponent-count stress tests rerun after the overtake-counter fix (PROGRESS 40), then E35b (smoother
# friction estimate, mu2) at x0.7 and on the main protocol. Eval only. New output files, nothing overwritten.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_t.log
S6="pid_apf ppo_apf_rec@s0 ppo_additive ppo_residual_apf_rec@trained ppo_residual_apf_rec@trained_s1 ppo_residual_apf_rec@trained_s2"
M6="ppo_apf_rec@s0=runs/ppo_shield_s0/model_stage3.zip ppo_additive=runs/ppo_additive_s0/model_stage3.zip \
ppo_residual_apf_rec@trained=runs/ppo_residual_shield_s0/model_stage3.zip \
ppo_residual_apf_rec@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
ppo_residual_apf_rec@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
V=ppo_residual_apf_rec_mu2
S3="$V@trained $V@trained_s1 $V@trained_s2"
M3="$V@trained=runs/ppo_residual_shield_s0/model_stage3.zip $V@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
$V@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
run() {  # name, controllers, models, extra args, message
  out=results/$1.json
  [ -f $out ] && { echo "$(date +%H:%M) $1 exists, skipped" >> $LOG; return; }
  echo "$(date +%H:%M) $1 start" >> $LOG
  $PY -m racing.evaluate --controllers $2 --models $3 --races 20 --laps 5 --procs 7 --tire saturated_v2 $4 \
    --out $out > runs/_$1.log 2>&1
  echo "$(date +%H:%M) $1 done" >> $LOG
  git add $out runs/_$1.log && git commit -qm "$5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && { git push -q origin gabe-build || { sleep 20; git push -q origin gabe-build; }; } >> $LOG 2>&1
}
run stress_opp1_v2 "$S6" "$M6" "--n_opp 1" "Stress test 1 opponent (E33), after the overtake-counter fix"
run stress_opp5_v2 "$S6" "$M6" "--n_opp 5" "Stress test 5 opponents rerun with passes counted on all cars (E33)"
run stress_mu0.7_mu2 "$S3" "$M3" "--mu_scale 0.7" "Smoother friction estimate (E35b) at x0.7"
run eval_mu2 "$S3" "$M3" "" "Smoother friction estimate (E35b), main protocol"
echo "$(date +%H:%M) all done" >> $LOG
