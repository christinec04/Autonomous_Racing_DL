#!/bin/bash
# E33b: is the low-friction drop the shield's model mismatch? Same stress tests, shield predictor told the true
# friction (oracle). Waits for lanes M and N (memory). Eval only.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_o.log
until grep -q "all done" runs/_lane_n.log 2>/dev/null; do sleep 120; done
CTRL="ppo_apf_rec@s0 ppo_residual_apf_rec@trained ppo_residual_apf_rec@trained_s1 ppo_residual_apf_rec@trained_s2"
MODELS="ppo_apf_rec@s0=runs/ppo_shield_s0/model_stage3.zip \
ppo_residual_apf_rec@trained=runs/ppo_residual_shield_s0/model_stage3.zip \
ppo_residual_apf_rec@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
ppo_residual_apf_rec@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
for mu in 0.8 0.7; do
  out=results/stress_mu${mu}_oracle.json
  [ -f $out ] && continue
  echo "$(date +%H:%M) mu$mu oracle start" >> $LOG
  $PY -m racing.evaluate --controllers $CTRL --models $MODELS --races 20 --laps 5 --procs 6 --tire saturated_v2 \
    --mu_scale $mu --shield_mu --out $out > runs/_stress_mu${mu}_oracle.log 2>&1
  echo "$(date +%H:%M) mu$mu oracle done" >> $LOG
  git add $out && git commit -qm "Stress test friction x$mu with the shield told the true friction (E33b)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin gabe-build >> $LOG 2>&1
done
echo "$(date +%H:%M) all done" >> $LOG
