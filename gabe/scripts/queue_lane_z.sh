#!/bin/bash
# Lane Z (E38, control for E37 B): wide friction range x0.65-1.15 but trained with the OLD shield
# (cond_fb_grip_esc, as E29), seeds 0 and 1, raced with the combined shield like E37. Separates the effect of the
# friction range from the effect of training with the new shield. Starts when lane Y's two trainings are done.
# Lane V header follows for reference. Lane V (E37): retrain the final recipe (residual PPO, saturated_v2) with the candidate final shield on during
# training (relaxed opponent check + friction estimate, cond_fb_grip_esc_oxmu).
#   A: usual friction randomisation x0.85-1.15  -> runs/ppo_residual_oxmu_s<seed>
#   B: wider friction randomisation x0.65-1.15  -> runs/ppo_residual_oxmu_widemu_s<seed>
# Two seeds each, two trainings at a time. Each policy is raced with the same shield (ppo_residual_apf_rec_oxmu):
# main protocol 50 races, then x0.8 and x0.7. Compare A with E36 (same shield, policy trained with the old one)
# and B with A. Waits for lanes T and U. New run names and result files only.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_z.log
until [ -f runs/ppo_residual_oxmu_s2/model_stage3.zip ] && [ -f runs/ppo_residual_oxmu_widemu_s2/model_stage3.zip ]; do sleep 120; done
push() { for i in 1 2 3 4 5; do git push -q origin gabe-build > /dev/null 2>&1 && return 0; sleep 30; done; }
train() {  # run seed extra
  [ -f runs/$1/model_stage3.zip ] && return
  [ -d runs/$1 ] && mv runs/$1 runs/$1_attempt_$(date +%Y%m%d%H%M)_incomplete  # keep an interrupted attempt
  echo "$(date +%H:%M) $1 train start" >> $LOG
  $PY -m racing.train --shield cond_fb_grip_esc --residual --tire saturated_v2 $3 --stages 1 2 3 \
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
  git commit -qm "E38: $1 trained with the old shield on x0.65-1.15 and raced with the combined shield (50 races, x0.8, x0.7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1; push
}
train ppo_residual_widemu_s0 0 "--mu_range 0.65 1.15" &
sleep 60
train ppo_residual_widemu_s1 1 "--mu_range 0.65 1.15" &
wait
race ppo_residual_widemu_s0 ppo_residual_widemu_s0
race ppo_residual_widemu_s1 ppo_residual_widemu_s1
echo "$(date +%H:%M) all done" >> $LOG
