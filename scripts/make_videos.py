"""Pick good seeds (no crash, most passes in the clip) and render short clips to ~/Downloads/racing_videos."""
import sys, pathlib
import numpy as np
from racing.render import record, render
OUT = pathlib.Path.home() / "Downloads" / "racing_videos"

def best_seed(ctrl, model, seconds, seeds=range(10000, 10012), tire="saturated"):
    best = None
    for s in seeds:
        env, fr = record(ctrl, model, s, seconds, tire=tire)
        passes = sum(f["passes"] for f in fr)
        score = (not fr[-1]["crash"], passes, fr[-1]["prog"])
        if best is None or score > best[0]:
            best = (score, s, env, fr)
    return best

def clip(ctrl, model, title, name, seconds=20, solo=False, tire="saturated"):
    if solo:
        env, fr = record(ctrl, model, 0, seconds, solo=True); s = 0; score = (not fr[-1]["crash"], 0, fr[-1]["prog"])
    else:
        score, s, env, fr = best_seed(ctrl, model, seconds, tire=tire)
    p = render(env, fr, OUT / name, f"{title}  (seed {s})")
    print(f"{name}: seed={s} crash={fr[-1]['crash']} passes={score[1]} dist={fr[-1]['prog']:.0f} m shield_steps={np.mean([f['lam']>0 for f in fr]):.0%}")

if __name__ == "__main__":
    which = sys.argv[1]
    if which == "batch1":
        clip("ppo", "runs/ppo_noshield_s0/model_stage3.zip", "PPO, no shield (ablation): race", "01_ppo_noshield_race.mp4")
        clip("ppo", "runs/ppo_noshield_s0/model_stage3.zip", "PPO, no shield: solo hot lap", "02_ppo_noshield_solo_lap.mp4", seconds=34, solo=True)
        clip("pid_apf", None, "PID+APF baseline: race", "03_pid_apf_race.mp4")
    elif which == "batch2":
        clip("ppo_apf", "runs/ppo_shield_s0/model_stage3.zip", "PPO + APF shield (ours): race (red = shield intervening)", "04_ppo_shield_race.mp4")
        clip("ppo_apf", "runs/ppo_shield_s0/model_stage3.zip", "PPO + APF shield: solo hot lap", "05_ppo_shield_solo_lap.mp4", seconds=34, solo=True)
    elif which == "batch4":
        clip("ppo_residual_apf", "runs/ppo_residual_s0/model_stage3.zip", "Residual PPO + our shield: race (red = shield intervening)", "07_ppo_residual_shield_race.mp4")
    elif which == "batch5":
        clip("ppo_apf_esc", "runs/ppo_shield_s0/model_stage3.zip", "PPO + final shield (deadlock escape): race (red = shield)", "08_ppo_final_shield_race.mp4", tire="saturated_v2")
    elif which == "batch7":
        # stall recovery in the chicane: seed 2 policy, race seed 10006 (stuck without recovery), from 14 s
        env, fr = record("ppo_apf_rec", "runs/ppo_shield_s2/model_stage3.zip", 10006, 34, tire="saturated_v2")
        fr = [f for f in fr if f["t"] >= 14.0]
        render(env, fr, OUT / "10_stall_recovery_chicane.mp4", "Seed-2 policy stalls nose-to-wall in the chicane; stall recovery reverses out")
        print("recoveries:", sum(1 for a, b in zip(fr, fr[1:]) if b["rec"] and not a["rec"]), "crash:", fr[-1]["crash"])
    elif which == "batch6":
        clip("ppo_additive", "runs/ppo_additive_s0/model_stage3.zip", "PPO trained with the additive Eq. 2/3 shield: safe but timid", "09_ppo_additive_shield_race.mp4", tire="saturated_v2")
    elif which == "batch3":
        clip("ppo_residual", "runs/ppo_residual_s0/model_stage3.zip", "Residual PPO on PID+APF (ResRace-style): race", "06_ppo_residual_race.mp4")
