"""Rebuild RUNS.md: index of every training run and result file, with provenance and key numbers.

Run after any training/evaluation: python -m scripts.update_registry
"""
import csv, json, pathlib, time
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGE_END = {1: 1_500_000, 2: 2_500_000, 3: 3_500_000}

PURPOSE = {
    "ppo_shield_s0": "Ours: PPO + action-conditioned APF shield with fallback (grip reach), all stages",
    "ppo_noshield_s0": "Ablation: PPO, shield off in every stage",
    "ppo_residual_s0": "ResRace/RaceMOP-style: PPO residual on top of PID+APF (APF shapes every command)",
    "ppo_shield_s1": "Ours, seed 1",
    "ppo_shield_s2": "Ours, seed 2",
    "ppo_noshield_s1": "Ablation (no shield), seed 1",
    "ppo_noshield_s2": "Ablation (no shield), seed 2",
    "ppo_shielddrop_s0": "Shield dropout: shield on in 100% / 50% / 25% of episodes in stages 1/2/3 (does the policy learn safety itself?)",
    "ppo_shield_linear_s0": "Ours on stock linear tyres: does PPO exploit unlimited grip (slip > 15 deg, > 100% mu g)?",
    "ppo_shield_w3low_s0": "Timidity test: ours with intervention penalty w3 = 0.02 (default 0.1)",
    "ppo_shield_preview_s0": "Timidity test: ours with 10 centerline curvatures (1-20 m ahead) in the observation",
    "ppo_shield_v2esc_s0": "Ours, improved: shield with deadlock escape, trained on the post-spin-fixed simulator",
    "ppo_shield_v2esc_slip_s1": "Final shield + slip penalty (w6 = 1), seed 1 (the seed that learned to slide)",
    "ppo_additive_s0": "Proposal's original shield: PPO + additive Eq. 2/3 APF (fixed reach)",
    "ppo_shield_ft_chicane_s2": "E22: seed-2 shielded policy fine-tuned 500k steps, half the episodes starting before the chicane",
    "ppo_shield_ft2_chicane_s2": "E22b: gentler chicane fine-tuning of seed 2 (lr 5e-5, slip penalty w6 = 1, 300k steps)",
    "ppo_residual_shield_s0": "E23: ResRace-style residual policy trained with the final shield (escape, v2 sim)",
    "ppo_residual_shield_s1": "E23, seed 1",
    "ppo_residual_shield_s2": "E23, seed 2",
}
RESULTS = {
    "eval_recover.json": "E21: final shield + stall recovery, seeds 0-2 (20 races x 5 laps, nominal + randomised)",
    "eval_residual_rec.json": "E21: residual policy + final shield + stall recovery",
    "final_summary.md": "Final comparison on the v2 simulator: tables, targets, Mann-Whitney tests (scripts/final_tables.sh)",
    "seed_summary.md": "Mean +- std across training seeds (scripts/seed_summary.py)",
    "failure_map.png": "Where on the lap races end, per controller (scripts/plot_failures.py)",
    "eval_ft_chicane_s2.json": "E22: chicane fine-tuned seed-2 policy, with and without stall recovery",
    "eval_ft2_chicane_s2.json": "E22b: gentler chicane fine-tuning, seed 2",
    "eval_residual_shield_s0.json": "E23: residual policy trained with the shield",
    "eval_residual_shield_s1.json": "E23 seed 1", "eval_residual_shield_s2.json": "E23 seed 2",
    "headtohead50.md": "E25: 50-race head-to-head with confidence intervals (scripts/headtohead.py)",
    "shield_stress_saturated.json": "Step 2 shield stress test (scripted bad drivers), friction-circle tyres",
    "shield_stress_linear.json": "Step 2 shield stress test, stock linear tyres",
    "eval_baselines.json": "Step 3 race evaluation: Pure Pursuit, PID+APF (20 races x 5 laps, nominal + randomised)",
    "eval_baselines.log": "Printed summary of eval_baselines.json",
    "tune_apf.json": "Grid search of APF gains for the PID+APF baseline",
    "eval_ppo_s0.json": "Step 4 race evaluation of seed-0 PPO models (with/without shield, cross-combinations)",
    "summary.md": "Merged race results, metric targets, Mann-Whitney U tests (scripts/analyze.py)",
    "gg_diagrams.png": "g-g diagrams per controller (scripts/plot_gg.py)",
    "shield_map.png": "Where on track the shield intervenes, 4 races (scripts/plot_shield_map.py)",
    "shield_sensitivity.json": "E14: shield settings at race time with the seed-0 shield-trained policy",
    "shield_sensitivity.md": "E14 table",
    "shield_confirm.json": "E15: best shield settings on the full protocol",
    "shield_confirm_summary.md": "E15 tables + Mann-Whitney tests",
    "eval_residual_s0.json": "E8: race evaluation of the residual (ResRace-style) policy",
    "eval_residual_apf_s0.json": "E8: residual policy with our shield added at race time",
    "training_efficiency.md": "E16: steps to first clean / fast unshielded lap, crashes during training (per run)",
    "final_v2_others.json": "Every non-final controller re-raced on the saturated_v2 simulator",
    "final_summary.md": "FINAL comparison, all controllers on saturated_v2 (scripts/final_tables.sh)",
    "eval_escape_v4.json": "E19: final shield (escape v4) seed 0, original shield on v2, residual + escape shield",
    "eval_escape_v4_s1.json": "Final shield, seed 1",
    "eval_escape_v2.json": "E19: escape v2 (failed: ratchet)",
    "eval_escape_v3.json": "E19: escape v3",
    "eval_ppo_additive_s0.json": "E9: PPO trained + raced with the additive Eq. 2/3 shield (v1 simulator)",
    "eval_ppo_shield_s1.json": "Original shield, seed 1 (v1 simulator)",
    "eval_ppo_noshield_s1.json": "No shield, seed 1 (v1 simulator)",
    "seed_summary.md": "Mean +- std across training seeds",
    "telemetry_speed.png": "E17: speed trace on a solo flying lap",
    "telemetry_sectors.md": "E17: sector times",
    "tradeoff.png": "Safety vs speed, every controller (scripts/plot_tradeoff.py)",
    "training_curves.png": "Training curves for all runs (crash rate, shield activity, unshielded solo lap)",
}


def rows(p):
    with open(p) as f:
        return list(csv.DictReader(f))


def run_row(d):
    a = json.load(open(d / "args.json"))
    info = json.load(open(d / "run_info.json")) if (d / "run_info.json").exists() else {}
    tr = rows(d / "train_log.csv") if (d / "train_log.csv").exists() else []
    ev = rows(d / "eval_log.csv") if (d / "eval_log.csv").exists() else []
    steps = int(float(tr[-1]["step"])) if tr else 0
    done = [s for s in (1, 2, 3) if (d / f"model_stage{s}.zip").exists()]
    status = "finished" if len(done) == len(a["stages"]) else ("running" if steps else "starting")
    crash = []
    for s in a["stages"]:
        # fine-tuning stages (e.g. 4, --init) count their own steps from 0
        lo, hi = (STAGE_END.get(s - 1, 0), STAGE_END[s]) if s in STAGE_END else (0, float("inf"))
        c = [float(r["crash_rate"]) for r in tr if lo < float(r["step"]) <= hi]
        crash.append(f"{100*np.mean(c):.0f}%" if c else "-")
    first = next((int(float(r["step"])) for r in ev if r["unshielded_clean"] == "True"), None)
    laps = [float(r["unshielded_lap"]) for r in ev if r["unshielded_clean"] == "True"]
    lam = [float(r["lam_freq"]) for r in tr[-5:]] if tr else []
    return dict(
        run=d.name, purpose=info.get("purpose", PURPOSE.get(d.name, "")),
        config=f"shield={a['shield']}{' residual' if a.get('residual') else ''} seed={a['seed']} tyre={a['tire']}",
        commit=info.get("git_commit", "?") + (" +dirty" if info.get("git_dirty") else ""),
        status=status, steps=f"{steps/1e6:.2f}M", crash=" / ".join(crash),
        first_clean=f"{first/1e3:.0f}k" if first else "-",
        best_lap=f"{min(laps):.2f}" if laps else "-", last_lap=f"{laps[-1]:.2f}" if laps else "-",
        lam=f"{100*np.mean(lam):.0f}%" if lam else "-", models=", ".join(f"stage{s}" for s in done) or "-",
        notes=info.get("notes", ""), command=info.get("command", ""),
    )


def main():
    runs = sorted(d for d in (ROOT / "runs").iterdir() if d.is_dir() and (d / "args.json").exists())
    R = [run_row(d) for d in runs]
    out = ["# Run registry", "",
           f"Auto-generated by `python -m scripts.update_registry` ({time.strftime('%Y-%m-%d %H:%M')}). "
           "Each run directory `runs/<run>/` holds `args.json`, `run_info.json` (git commit, command, status), "
           "`train_log.csv` (every ~20k steps), `eval_log.csv` (solo laps with/without shield every 50k steps), "
           "`model_stage*.zip` + `vecnorm_stage*.pkl` (checkpoint after each curriculum stage). TensorBoard logs "
           "(`runs/*/tb`) stay local.", "",
           "## Training runs", "",
           "| run | purpose | config | commit | status | steps | train crash rate (stage 1/2/3) | first clean lap, shield removed | best / last solo lap, shield removed (s) | shield active (last 100k) | checkpoints |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in R:
        out.append(f"| `{r['run']}` | {r['purpose']} | {r['config']} | `{r['commit']}` | {r['status']} | {r['steps']} | "
                   f"{r['crash']} | {r['first_clean']} | {r['best_lap']} / {r['last_lap']} | {r['lam']} | {r['models']} |")
    out += ["", "### Commands and notes", ""]
    for r in R:
        out.append(f"- `{r['run']}`: `{r['command']}`" + (f"  \n  Note: {r['notes']}" if r["notes"] else ""))
    out += ["", "## Result files (`results/`)", "", "| file | what |", "|---|---|"]
    for f in sorted((ROOT / "results").iterdir()):
        out.append(f"| `{f.name}` | {RESULTS.get(f.name, '')} |")
    (ROOT / "RUNS.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[:8 + len(R)]))


if __name__ == "__main__":
    main()
