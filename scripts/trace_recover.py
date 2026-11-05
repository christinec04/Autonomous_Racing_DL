import sys, numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.evaluate import SHIELD_FOR
from stable_baselines3 import PPO
seed = int(sys.argv[1])
cfg = EnvConfig(n_opp=3, opp_speed=(0.5, 0.75), random_start=True, shield=ShieldConfig(**SHIELD_FOR["ppo_apf_rec"]),
                episode_time=350, seed=seed, tire="saturated_v2", recover=True)
env = RaceEnv(cfg); rng = np.random.default_rng(seed)
opts = dict(s_ego=3.0, opp_gaps=list(np.cumsum(rng.uniform(5.0, 15.0, 3))), opp_speeds=list(rng.uniform(0.5, 0.75, 3)))
obs, _ = env.reset(seed=seed, options=opts); m = PPO.load("runs/ppo_shield_s2/model_stage3.zip", device="cpu")
log = []
while True:
    a, _ = m.predict(obs[None], deterministic=True)
    obs, r, te, tr, info = env.step(a[0]); st = info["state"]
    log.append(f"t={info['t']:6.2f} s={info['progress']%199:6.1f} v={st[3]:+5.2f} lat={info['lat']:+.2f} hdg={np.degrees(info['hdg_err']):+5.0f} "
               f"rec={int(info['recovering'])} rl=({info['a_rl'][0]:+.2f},{info['a_rl'][1]:+5.1f}) fin=({info['a_final'][0]:+.2f},{info['a_final'][1]:+5.1f}) lam={info['lambda']:.2f} fb={int(info['fallback'])} minscan={env.scan.min():.2f}")
    if te or tr: break
print("\n".join(log[-90::3])); print("end wall" if info["wall"] else "end car" if info["car"] else "end trunc")
