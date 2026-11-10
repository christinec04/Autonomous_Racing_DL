"""Replay every car-contact DNF of a controller and classify the contact.

At the contact step: which opponent, its gap along the track (+ = opponent ahead), the ego's closing speed on it,
lateral offsets, and what the shield did in the last second. Classes:
  rear-end   - opponent ahead by > 0.25 m and the ego closes on it
  hit-from-behind - opponent behind by > 0.25 m and it closes on the ego
  side       - overlapping along the track (|gap| <= 0.25 m)
usage: python -m scripts.classify_contacts <label> <model.zip> <results.json> [more results.json ...]
-> prints a table; appends to results/contacts.md
"""
import json, sys
import numpy as np
from stable_baselines3 import PPO
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.evaluate import SHIELD_FOR, RECOVER, residual_scale_for


def replay(label, model_path, seed, randomize, tire="saturated_v2", map_name="Singapore"):
    ctrl = label.split("@")[0]
    cfg = EnvConfig(n_opp=3, opp_speed=(0.5, 0.75), random_start=True, randomize=randomize,
                    shield=ShieldConfig(**SHIELD_FOR[ctrl]), episode_time=350.0, seed=seed, tire=tire,
                    recover=ctrl in RECOVER, residual=ctrl.startswith("ppo_residual"), map_name=map_name,
                    residual_scale=residual_scale_for(model_path))
    env = RaceEnv(cfg)
    rng = np.random.default_rng(seed)
    opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))), opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
    obs, _ = env.reset(seed=seed, options=opts)
    m = PPO.load(model_path, device="cpu")
    hist = []
    while True:
        a, _ = m.predict(obs[None], deterministic=True)
        obs, r, te, tr, info = env.step(a[0])
        hist.append((info["lambda"], info["fallback"]))
        if te or tr:
            break
    if not info["car"]:
        return None
    L = env.cl.length
    sim = env.sim.unwrapped.sim
    j = int(sim.collision_idx[0])  # agent index the ego touched
    st = info["state"]
    gap = (info["opp_prog"][j - 1] - info["progress"] + L / 2) % L - L / 2
    v_ego = st[3] * np.cos(info["hdg_err"])
    v_opp = info["opp_v"][j - 1]
    if gap > 0.25:
        kind = "rear-end"
    elif gap < -0.25:
        kind = "hit-from-behind"
    else:
        kind = "side"
    last = hist[-25:]
    return dict(seed=seed, randomize=randomize, lap=info["progress"] / L, s=info["progress"] % L, kind=kind,
                gap=float(gap), dv=float(v_ego - v_opp), v=float(st[3]), lat_ego=float(info["lat"]),
                lat_opp=float(info["opp_lat"][j - 1]), shield_last_s=float(np.mean([l > 0 for l, _ in last])),
                fallback_last_s=bool(any(f for _, f in last)), t=float(info["t"]))


if __name__ == "__main__":
    label, model = sys.argv[1:3]
    races = [r for f in sys.argv[3:] for r in json.load(open(f))["races"] if r["controller"] == label and r["car"]]
    rows = [x for r in races if (x := replay(label, model, r["seed"], r["randomize"])) is not None]
    out = [f"## {label} ({model})", "",
           "| seed | cond | lap | s (m) | class | gap (m) | ego - opp speed | ego speed | lat ego / opp | shield on, last 1 s | fallback |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        out.append(f"| {x['seed']} | {'rand' if x['randomize'] else 'nom'} | {x['lap']:.2f} | {x['s']:.0f} | {x['kind']} | "
                   f"{x['gap']:+.2f} | {x['dv']:+.2f} | {x['v']:.1f} | {x['lat_ego']:+.2f} / {x['lat_opp']:+.2f} | "
                   f"{x['shield_last_s']:.0%} | {'yes' if x['fallback_last_s'] else 'no'} |")
    kinds = [x["kind"] for x in rows]
    out += ["", f"{len(rows)} contacts replayed ({len(races)} in the results): " +
            ", ".join(f"{k} {kinds.count(k)}" for k in ("rear-end", "hit-from-behind", "side")) +
            f"; shield active in the last second before {sum(x['shield_last_s'] > 0 for x in rows)}; "
            f"in the first lap {sum(x['lap'] < 1 for x in rows)}.", ""]
    print("\n".join(out))
    with open("results/contacts.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
