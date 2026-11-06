"""Mean +- std across training seeds (proposal: 3 seeds per learned controller) -> results/seed_summary.md."""
import json, glob, pathlib
import numpy as np
from racing.evaluate import summarize

GROUPS = {
    "PPO + slip penalty + shield + recovery (E26)": ["ppo_apf_rec@slip_s0", "ppo_apf_rec@slip_s1", "ppo_apf_rec@slip_s2"],
    "residual PPO trained with shield + recovery (E23)": ["ppo_residual_apf_rec@trained", "ppo_residual_apf_rec@trained_s1",
                                                          "ppo_residual_apf_rec@trained_s2"],
    "PPO + shield + escape + stall recovery (final, v2 sim)": ["ppo_apf_rec@s0", "ppo_apf_rec@s1", "ppo_apf_rec@s2"],
    "PPO + shield + escape (v2 sim)": ["ppo_apf_esc@s0", "ppo_apf_esc@s1v4", "ppo_apf_esc@s2"],
    "PPO + original shield (v1 sim)": ["ppo_apf", "ppo_apf@s1", "ppo_apf@s2"],
    "PPO, no shield (v2 sim)": ["ppo@s0", "ppo@s1", "ppo@s2v2"],
}
KEYS = [("finished", "finished all laps / 20", "{:.1f}"), ("stuck", "stuck / 20", "{:.1f}"), ("lap_mean", "clean lap (s)", "{:.2f}"),
        ("collisions_per_10_laps", "collisions / 10 laps", "{:.2f}"), ("passes_per_race", "passes / race", "{:.2f}"),
        ("overtake_success", "overtake success", "{:.0%}"), ("shield_freq", "shield active", "{:.1%}"),
        ("grip_above_90", "time > 90% grip", "{:.1%}"), ("slip_above_15", "time > 15 deg slip", "{:.1%}")]


# Canonical result files only. Older experiment files (e.g. escape v2/v3) reuse labels and must not be pooled.
CANONICAL = ["results/eval_ppo_s0.json", "results/eval_ppo_shield_s1.json", "results/eval_ppo_shield_s2.json",
             "results/final_v2_others.json", "results/final_v2_noshield_s2.json",
             "results/eval_escape_v4.json", "results/eval_escape_v4_s1.json", "results/eval_escape_v4_s2.json",
             "results/eval_recover.json",
             "results/eval_slip_rec_slip_s0.json", "results/eval_slip_rec_slip_s1.json", "results/eval_slip_rec_slip_s2.json",
             "results/eval_residual_shield_s0.json", "results/eval_residual_shield_s1.json",
             "results/eval_residual_shield_s2.json"]


def main(files=None):
    races = []
    for f in files or CANONICAL:
        if pathlib.Path(f).exists():
            races += json.load(open(f)).get("races", [])
    labels = [(r["controller"], r["randomize"], r["seed"]) for r in races]
    assert len(labels) == len(set(labels)), "duplicate races for a label: check the file list"
    out = ["# Across training seeds (mean +- std over seeds; each seed = 20 races x 5 laps)", ""]
    for cond in ("nominal", "randomized"):
        R = [r for r in races if r["randomize"] == (cond == "randomized")]
        S = summarize(R)
        out += [f"## {cond}", "", "| metric | " + " | ".join(GROUPS) + " |", "|---|" + "---|" * len(GROUPS)]
        for k, name, fmt in KEYS:
            cells = []
            for g, labels in GROUPS.items():
                vals = [S[l][k] for l in labels if l in S and S[l][k] is not None]
                n = len(vals)
                cells.append("-" if not n else (fmt.format(np.mean(vals)) + (f" +- {fmt.format(np.std(vals))}" if n > 1 else "") + f" (n={n})"))
            out.append(f"| {name} | " + " | ".join(cells) + " |")
        out.append("")
    pathlib.Path("results/seed_summary.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
