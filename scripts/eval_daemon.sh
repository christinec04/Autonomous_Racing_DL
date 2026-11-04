#!/bin/bash
# Evaluate each run as soon as it finishes (one evaluation at a time, 4 processes), then refresh tables and push.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
# run -> "controller label" (label = how it appears in results/summary_seeds.md)
declare -A CTRL=(
  [ppo_shield_s1]="ppo_apf@s1" [ppo_shield_s2]="ppo_apf@s2"
  [ppo_noshield_s1]="ppo@s1" [ppo_noshield_s2]="ppo@s2"
  [ppo_additive_s0]="ppo_additive" [ppo_shielddrop_s0]="ppo_apf@drop"
  [ppo_shield_linear_s0]="ppo_apf@linear"
  [ppo_shield_v2esc_s0]="ppo_apf_esc@v2esc" [ppo_shield_w3low_s0]="ppo_apf@w3low" [ppo_shield_preview_s0]="ppo_apf@preview"
  [ppo_shield_v2esc_slip_s1]="ppo_apf_esc@slip_s1"
)
while true; do
  pending=0
  for r in "${!CTRL[@]}"; do
    out=results/eval_${r}.json
    [ -f "$out" ] && continue
    pending=1
    [ -f runs/$r/model_stage3.zip ] || continue
    label=${CTRL[$r]}
    extra=""; tire=saturated
    [ "$r" = ppo_shield_linear_s0 ] && tire=linear
    [ "$r" = ppo_shield_v2esc_s0 ] && tire=saturated_v2
    [ "$r" = ppo_shield_v2esc_slip_s1 ] && tire=saturated_v2
    # the shield-dropout policy is also raced without its shield (did it learn safety itself?)
    [ "$r" = ppo_shielddrop_s0 ] && extra="ppo@drop_noshield" && models_extra="ppo@drop_noshield=runs/$r/model_stage3.zip"
    $PY -m racing.evaluate --controllers "$label" $extra --models "$label=runs/$r/model_stage3.zip" $models_extra \
        --races 20 --laps 5 --procs 4 --tire $tire --out "$out" > runs/_eval_${r}_stdout.log 2>&1
    models_extra=""
    $PY -m scripts.analyze results/eval_baselines.json results/eval_ppo_s0.json results/eval_residual_s0.json \
        results/eval_residual_apf_s0.json $(ls results/eval_ppo_*_s[0-9].json results/eval_ppo_additive_s0.json results/eval_ppo_shielddrop_s0.json results/eval_ppo_shield_linear_s0.json 2>/dev/null | sort -u) \
        --out results/summary_all.md > /dev/null 2>&1
    $PY -m scripts.update_registry > /dev/null 2>&1
    git add results runs RUNS.md > /dev/null 2>&1
    git commit -q -m "Auto-eval: $r raced (20 races x 5 laps, nominal + randomised)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q > /dev/null 2>&1 && echo "$(date '+%H:%M') evaluated $r"
  done
  [ $pending = 0 ] && echo all-done && break
  sleep 300
done
