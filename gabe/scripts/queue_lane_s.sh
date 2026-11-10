#!/bin/bash
# Lane S (E35): the shield estimates the friction online (ShieldConfig.mu_est) instead of assuming nominal.
# Final controller, 3 training seeds: friction x0.8 and x0.7 (compare with E33 nominal model / true friction), then
# the main protocol (20 races, nominal + randomised) to check it costs nothing in normal conditions.
# Waits for lane P (CPU). Eval only.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_s.log
until grep -q "all done" runs/_lane_p.log 2>/dev/null; do sleep 120; done
CTRL="ppo_residual_apf_rec_mu@trained ppo_residual_apf_rec_mu@trained_s1 ppo_residual_apf_rec_mu@trained_s2"
MODELS="ppo_residual_apf_rec_mu@trained=runs/ppo_residual_shield_s0/model_stage3.zip \
ppo_residual_apf_rec_mu@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
ppo_residual_apf_rec_mu@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
run() {  # name, extra args
  out=results/$1.json
  [ -f $out ] && return
  echo "$(date +%H:%M) $1 start" >> $LOG
  $PY -m racing.evaluate --controllers $CTRL --models $MODELS --races 20 --laps 5 --procs 5 --tire saturated_v2 \
    $2 --out $out > runs/_$1.log 2>&1
  echo "$(date +%H:%M) $1 done" >> $LOG
  git add $out && git commit -qm "Shield with online friction estimate (E35): $1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin gabe-build >> $LOG 2>&1
}
run stress_mu0.8_muest "--mu_scale 0.8"
run stress_mu0.7_muest "--mu_scale 0.7"
run eval_muest ""
echo "$(date +%H:%M) all done" >> $LOG
