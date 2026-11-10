#!/bin/bash
# Lane V (E37): retrain the final recipe (residual PPO, saturated_v2) with the candidate final shield on during
# training (relaxed opponent check + friction estimate, cond_fb_grip_esc_oxmu).
#   A: usual friction randomisation x0.85-1.15  -> runs/ppo_residual_oxmu_s<seed>
#   B: wider friction randomisation x0.65-1.15  -> runs/ppo_residual_oxmu_widemu_s<seed>
# Two seeds each, two trainings at a time. Each policy is raced with the same shield (ppo_residual_apf_rec_oxmu):
# main protocol 50 races, then x0.8 and x0.7. Compare A with E36 (same shield, policy trained with the old one)
# and B with A. Waits for lanes T and U. New run names and result files only.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_v.log
until grep -q "all done" runs/_lane_t.log 2>/dev/null && grep -q "all done" runs/_lane_u.log 2>/dev/null; do sleep 120; done
push() { for i in 1 2 3 4 5; do git push -q origin gabe-build > /dev/null 2>&1 && return 0; sleep 30; done; }
train() {  # run seed extra
  [ -f runs/$1/model_stage3.zip ] && return
  [ -d runs/$1 ] && mv runs/$1 runs/$1_attempt_$(date +%Y%m%d%H%M)_incomplete  # keep an interrupted attempt
  echo "$(date +%H:%M) $1 train start" >> $LOG
  $PY -m racing.train --shield cond_fb_grip_esc_oxmu --residual --tire saturated_v2 $3 --stages 1 2 3 \
    --steps 1500000 1000000 1000000 --n_envs 7 --seed $2 --out runs/$1 > runs/$1.log 2>&1
  echo "$(date +%H:%M) $1 train done" >> $LOG
}
race() {  # run label
  C=ppo_residual_apf_rec_oxmu@$2; M="$C=runs/$1/model_stage3.zip"
  for t in "eval:--races 50" "stress_mu0.8:--races 20 --mu_scale 0.8" "stress_mu0.7:--races 20 --mu_scale 0.7"; do
    name=${t%%:*}_$1; args=${t#*:}
    [ -f results/$name.json ] && continue
    $PY -m racing.evaluate --controllers $C --models $M --laps 5 --procs 7 --tire saturated_v2 $args \
      --out results/$name.json > runs/_$name.log 2>&1
    echo "$(date +%H:%M) $name done" >> $LOG
  done
  git add runs/$1 runs/$1.log results/*_$1.json runs/_*_$1.log $LOG > /dev/null 2>&1
  git commit -qm "E37: $1 trained with the candidate final shield and raced (50 races, x0.8, x0.7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1; push
}
for pair in "ppo_residual_oxmu:" "ppo_residual_oxmu_widemu:--mu_range 0.65 1.15"; do
  base=${pair%%:*}; extra=${pair#*:}
  train ${base}_s0 0 "$extra" &
  sleep 60
  train ${base}_s1 1 "$extra" &
  wait
  race ${base}_s0 ${base}_s0
  race ${base}_s1 ${base}_s1
done
echo "$(date +%H:%M) all done" >> $LOG
