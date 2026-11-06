"""Step 2 experiment: stress-test shield variants with scripted 'bad' policies.

No learning involved: this isolates what the shield itself can and cannot guarantee
(feedback point 1: an additive, clipped APF cannot guarantee zero violations).
"""
import json, sys, time, itertools, numpy as np
from multiprocessing import Pool
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.controllers import PurePursuit

VARIANTS = {
    "off": dict(mode="off"),
    "additive_fixed": dict(mode="additive", reach="fixed"),       # proposal Eq. 2/3
    "additive_grip": dict(mode="additive", reach="grip"),
    "cond_grip": dict(mode="conditioned", reach="grip"),
    "cond_fb_fixed": dict(mode="conditioned_fallback", reach="fixed"),
    "cond_fb_grip": dict(mode="conditioned_fallback", reach="grip"),
}
POLICIES = {
    "pp_fast_solo": dict(n_opp=0, scale=1.1),   # too fast for the corners
    "pp_traffic": dict(n_opp=3, scale=0.85),     # ignores slower cars ahead
    "random_traffic": dict(n_opp=3, scale=None), # uniformly random actions
}

def run(args):
    var, pol, seed = args
    pc = POLICIES[pol]
    env = RaceEnv(EnvConfig(n_opp=pc["n_opp"], tire=TIRE, shield=ShieldConfig(**VARIANTS[var]), episode_time=30.0, seed=seed))
    env.reset(seed=seed)
    rng = np.random.default_rng(seed)
    pp = PurePursuit(env.cl, speed_scale=pc["scale"] or 1.0)
    lams, fbs, slips = [], 0, []
    t0 = time.time(); k = 0
    while True:
        e = env._states()[0]
        if pc["scale"] is None:
            a = rng.uniform(-1, 1, 2) if k % 10 == 0 else a  # hold random action for 0.4 s
        else:
            a = env.to_normalized(pp.act(e[0], e[1], e[4], e[3]))
        _, r, term, trunc, info = env.step(a); k += 1
        lams.append(info["lambda"]); fbs += info["fallback"]; slips.append(abs(e[6]))
        if term or trunc: break
    return dict(variant=var, policy=pol, seed=seed, crash=bool(term), wall=info["wall"], car=info["car"],
                dist=info["progress"], time=info["t"], lam_freq=float(np.mean(np.array(lams) > 0)),
                lam_mean=float(np.mean(lams)), fallback=fbs, max_slip_deg=float(np.degrees(max(slips))),
                steps_per_s=k / (time.time() - t0))

TIRE = sys.argv[2] if len(sys.argv) > 2 else "saturated"
if __name__ == "__main__":
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print("tire:", TIRE)
    jobs = list(itertools.product(VARIANTS, POLICIES, range(n_seeds)))
    with Pool(15) as p:
        res = p.map(run, jobs, chunksize=1)
    json.dump(res, open(f"results/shield_stress_{TIRE}.json", "w"), indent=1)
    print(f"{'policy':15s} {'variant':15s} crash%  wall car  dist_m  lam>0  fallback/ep  max_slip")
    for pol in POLICIES:
        for var in VARIANTS:
            R = [r for r in res if r["variant"] == var and r["policy"] == pol]
            print(f"{pol:15s} {var:15s} {100*np.mean([r['crash'] for r in R]):5.0f}  {sum(r['wall'] for r in R):4d} {sum(r['car'] for r in R):3d} "
                  f"{np.mean([r['dist'] for r in R]):7.1f}  {np.mean([r['lam_freq'] for r in R]):.2f}  {np.mean([r['fallback'] for r in R]):8.1f}  "
                  f"{np.mean([r['max_slip_deg'] for r in R]):6.1f}")
