#!/bin/bash
# Final comparison, everything on the saturated_v2 simulator.
cd "$(dirname "$0")/.."
PY=../.venv/Scripts/python
FILES="results/final_v2_others.json results/eval_escape_v4.json"
[ -f results/eval_escape_v4_s1.json ] && FILES="$FILES results/eval_escape_v4_s1.json"
[ -f results/eval_escape_v4_s2.json ] && FILES="$FILES results/eval_escape_v4_s2.json"
[ -f results/eval_recover.json ] && FILES="$FILES results/eval_recover.json"
OURS=ppo_apf_esc@s0; [ -f results/eval_recover.json ] && OURS=ppo_apf_rec@s0
$PY -m scripts.analyze $FILES --ours "$OURS" --out results/final_summary.md
