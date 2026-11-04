"""Training efficiency and training-time safety per run -> results/training_efficiency.md.

All lap measurements are with the shield removed (Plan feedback), from eval_log.csv (every 50k steps).
"""
import csv, json, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
FAST = 34.0  # s, faster than the best classical controller's solo lap (35.2 s)


def rows(p):
    with open(p) as f:
        return list(csv.DictReader(f))


def main():
    out = ["# Training efficiency (shield removed for every lap measurement)", "",
           f"Solo laps every 50k steps, standing start. 'fast' = under {FAST:.0f} s (best classical solo lap: 35.2 s).", "",
           "| run | config | steps trained | first clean lap | first fast lap | crashes before first clean lap | crashes during training (episodes) | best lap |",
           "|---|---|---|---|---|---|---|---|"]
    for d in sorted((ROOT / "runs").iterdir()):
        if not (d / "eval_log.csv").exists():
            continue
        a = json.load(open(d / "args.json"))
        ev, tr = rows(d / "eval_log.csv"), rows(d / "train_log.csv")
        clean = [(int(float(r["step"])), float(r["unshielded_lap"])) for r in ev if r["unshielded_clean"] == "True"]
        first = clean[0][0] if clean else None
        fast = next((s for s, t in clean if t < FAST), None)
        crashes = sum(int(r["crashes"]) for r in tr)
        eps = sum(int(r["episodes"]) for r in tr)
        before = sum(int(r["crashes"]) for r in tr if first and float(r["step"]) <= first)
        cfg = f"{a['shield']}{' residual' if a.get('residual') else ''}{' tyre=' + a['tire'] if a['tire'] != 'saturated' else ''}" \
              f"{' drop=' + str(a.get('shield_prob')) if a.get('shield_prob') else ''}"
        k = lambda s: f"{s/1e3:.0f}k" if s else "-"
        out.append(f"| `{d.name}` | {cfg} | {k(int(float(tr[-1]['step'])))} | {k(first)} | {k(fast)} | {before} | "
                   f"{crashes} ({eps}) | {min(t for _, t in clean):.2f} |" if clean else
                   f"| `{d.name}` | {cfg} | {k(int(float(tr[-1]['step'])) if tr else 0)} | - | - | - | {crashes} ({eps}) | - |")
    (ROOT / "results" / "training_efficiency.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
