#!/bin/bash
# E33 stress tests (eval only): friction outside the training range (x0.85-1.15) and more/fewer opponents.
# Same 20 race seeds as the main protocol; friction runs have no lidar noise. Commits + pushes per setting.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_m.log
CTRL="pid_apf ppo_apf_rec@s0 ppo_additive ppo_residual_apf_rec@trained ppo_residual_apf_rec@trained_s1 ppo_residual_apf_rec@trained_s2"
MODELS="ppo_apf_rec@s0=runs/ppo_shield_s0/model_stage3.zip ppo_additive=runs/ppo_additive_s0/model_stage3.zip \
ppo_residual_apf_rec@trained=runs/ppo_residual_shield_s0/model_stage3.zip \
ppo_residual_apf_rec@trained_s1=runs/ppo_residual_shield_s1/model_stage3.zip \
ppo_residual_apf_rec@trained_s2=runs/ppo_residual_shield_s2/model_stage3.zip"
run() {  # name, extra args
  out=results/stress_$1.json
  [ -f $out ] && { echo "$(date +%H:%M) $1 exists" >> $LOG; return; }
  echo "$(date +%H:%M) $1 start" >> $LOG
  $PY -m racing.evaluate --controllers $CTRL --models $MODELS --races 20 --laps 5 --procs 5 --tire saturated_v2 \
    $2 --out $out > runs/_stress_$1.log 2>&1
  echo "$(date +%H:%M) $1 done" >> $LOG
  git add $out && git commit -qm "Stress test $1 (E33): 6 controllers x 20 races

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin gabe-build >> $LOG 2>&1
}
run mu0.8 "--mu_scale 0.8"
run mu0.7 "--mu_scale 0.7"
run mu1.2 "--mu_scale 1.2"
run opp5 "--n_opp 5"
run opp1 "--n_opp 1"
run mu0.6 "--mu_scale 0.6"
run mu1.3 "--mu_scale 1.3"
echo "$(date +%H:%M) all done" >> $LOG
