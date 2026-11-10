#!/bin/bash
# Lane AC (E38 recovery, 2026-11-10): the laptop crashed at about 10:23 on Nov 10 and killed lanes Z, AA and AB.
# Lane Z had finished stage 1 of ppo_residual_widemu_s0/s1 (1.5M steps, saved) and was ~80% through stage 2
# (not saved). Restarting from zero would cost ~10 h, and the report is due Nov 13, so stages 2 and 3 are
# trained from the saved stage-1 model (--init loads the policy, the Adam state and the reward-normalisation
# statistics; the learning rate is the same constant 3e-4). Output goes to NEW folders *_from_stage1 so the
# crashed attempt (stage-1 model + partial stage-2 logs) stays as it was. Difference from an uninterrupted run:
# the random-number state at the start of stage 2 is not the same, and step counters in the new logs restart at 0
# (add 1.5M to compare with an uninterrupted run). Then raced exactly like lane Z (50 races, x0.8, x0.7).
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
LOG=runs/_lane_ac.log
push() { for i in 1 2 3 4 5; do git push -q origin HEAD:main HEAD:gabe-build > /dev/null 2>&1 && return 0; sleep 30; done; }
# 2026-11-10 12:15 update: stopped on user request to free memory. Seed 0 had saved stage 2 and continues with
# stage 3 only (runs/ppo_residual_widemu_s0_from_stage2). Seed 1 stopped at 960k of its 1M stage-2 steps, unsaved,
# so it redoes stages 2-3 from stage 1 in a new folder (runs/ppo_residual_widemu_s1_from_stage1_retry); the stopped
# attempts stay as they are.
train() {  # init_model stages steps seed out
  [ -f runs/$5/model_stage3.zip ] && return
  echo "$(date +%H:%M) $5 train start (stages $2 from $1)" >> $LOG
  $PY -m racing.train --shield cond_fb_grip_esc --residual --tire saturated_v2 --mu_range 0.65 1.15     --init $1 --stages $2 --steps $3 --n_envs 7 --seed $4 --out runs/$5 > runs/$5.log 2>&1
  echo "$(date +%H:%M) $5 train done" >> $LOG
}
race() {  # run
  C=ppo_residual_apf_rec_oxmu@$1; M="$C=runs/$1/model_stage3.zip"
  for t in "eval:--races 50" "stress_mu0.8:--races 20 --mu_scale 0.8" "stress_mu0.7:--races 20 --mu_scale 0.7"; do
    name=${t%%:*}_$1; args=${t#*:}
    [ -f results/$name.json ] && continue
    $PY -m racing.evaluate --controllers $C --models $M --laps 5 --procs 7 --tire saturated_v2 $args \
      --out results/$name.json > runs/_$name.log 2>&1
    echo "$(date +%H:%M) $name done" >> $LOG
  done
  git add runs/$1 runs/$1.log results/*_$1.json runs/_*_$1.log $LOG > /dev/null 2>&1
  git commit -qm "E38: $1 (old shield, x0.65-1.15, resumed from stage 1 after the crash) raced with the combined shield (50 races, x0.8, x0.7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1; push
}
train runs/ppo_residual_widemu_s0_from_stage1/model_stage2.zip "3" "1000000" 0 ppo_residual_widemu_s0_from_stage2 &
sleep 60
train runs/ppo_residual_widemu_s1/model_stage1.zip "2 3" "1000000 1000000" 1 ppo_residual_widemu_s1_from_stage1_retry &
wait
race ppo_residual_widemu_s0_from_stage2
race ppo_residual_widemu_s1_from_stage1_retry
echo "$(date +%H:%M) all done" >> $LOG
