# Build log (incremental results)

Branch `gabe-build`. Setup: `python -m venv .venv && pip install -r requirements.txt`, then `python -m racing.track_gen`.

Layout: `racing/` (track, sim wrapper, tyres, controllers, shield, predictor, env), `scripts/` (experiments), `results/` (raw outputs).

## Step 1: track + classical controllers (solo)
- Singapore-inspired street circuit, 199 m lap, 2.8 m wide, 19 corners (`maps/Singapore`), `python -m racing.track_gen`.
- F1TENTH Gym v1.0 dynamic single-track model, default vehicle params, physics dt 0.01 s, control at 25 Hz.
- `python -m scripts.probe_sim <saturated|linear> <tcs|notcs>`

Stock F1TENTH tyres (first run):

| controller | speed scale | result | lap time |
|---|---|---|---|
| Pure Pursuit | 0.85 | clean | 35.2 s |
| Pure Pursuit | 1.00 | clean | 30.1 s |
| Pure Pursuit | 1.10 | clean | 27.9 s |
| PID | 0.85 | clean | 34.6 s |
| PID | 1.00 | crash | - |

Friction-circle tyres + traction control (what we use now, see problems 4-5):

| controller | speed scale | result | lap time |
|---|---|---|---|
| Pure Pursuit | 0.85 | clean | 35.2 s |
| Pure Pursuit | 0.95+ | slides out, crash | - |
| PID | 0.85 | clean | 34.0 s |
| PID | 0.95+ | spins, crash | - |

## Step 2: race env + APF shield, tested without any learning
`racing/env.py` (ego + 3 opponents, obs/action/reward from the proposal), `racing/shield.py`, `racing/predict.py`.

Shield variants (each one targets a grader comment):
- `additive_*`: proposal Eq. 2/3, `a = clip(a_rl + w(d) a_apf)`, w from distance and speed only.
- `cond_*`: action-conditioned (comment 3). Roll out the policy's action for one control step, then a backup manoeuvre
  (brake to a stop, hold the lane). Intervene only if that rollout hits something or loses control; then pick the smallest
  blend weight lambda towards the APF correction that is predicted safe.
- `cond_fb_*`: same, but if no blend is safe, replace the action with the backup manoeuvre (or the safest braking manoeuvre).
- `*_fixed` vs `*_grip`: braking used for the reach/backup is a fixed assumed 6 m/s^2 vs what the friction circle leaves
  after cornering (comment 2).

Stress test, `python -m scripts.shield_stress 8 <tyres>`: scripted bad drivers, no RL. `pp_fast_solo` = Pure Pursuit at
1.1x the grip-limited speed profile, `pp_traffic` = Pure Pursuit at 0.85x that ignores the 3 slower cars, `random_traffic`
= random actions held for 0.4 s. Cell = crash % (8 runs x 30 s) / mean distance / % of steps the shield is active.

**friction-circle tyres**

| shield | pp_fast_solo | pp_traffic | random_traffic |
|---|---|---|---|
| off | 100% / 55 m / 0% | 100% / 31 m / 0% | 100% / 5 m / 0% |
| additive_fixed | 100% / 55 m / 89% | 100% / 55 m / 88% | 100% / 6 m / 53% |
| additive_grip | 100% / 32 m / 81% | 100% / 32 m / 80% | 100% / 4 m / 51% |
| cond_grip | 0% / 54 m / 84% | 38% / 42 m / 66% | 38% / 4 m / 76% |
| cond_fb_fixed | 0% / 185 m / 44% | 12% / 142 m / 36% | 0% / 13 m / 92% |
| cond_fb_grip | 0% / 35 m / 90% | 38% / 112 m / 38% | 12% / 13 m / 91% |

**stock linear tyres**

| shield | pp_fast_solo | pp_traffic | random_traffic |
|---|---|---|---|
| off | 100% / 82 m / 0% | 100% / 31 m / 0% | 100% / 4 m / 0% |
| additive_fixed | 0% / 205 m / 98% | 100% / 74 m / 91% | 100% / 4 m / 48% |
| additive_grip | 100% / 40 m / 80% | 88% / 44 m / 74% | 100% / 3 m / 46% |
| cond_grip | 100% / 45 m / 22% | 88% / 58 m / 26% | 75% / 6 m / 54% |
| cond_fb_fixed | 0% / 203 m / 24% | 25% / 132 m / 35% | 0% / 19 m / 89% |
| cond_fb_grip | 0% / 210 m / 18% | 38% / 111 m / 31% | 0% / 24 m / 87% |

What this says about the feedback:
- Comment 1 (additive APF cannot guarantee no violations): confirmed. The proposal's additive shield crashed in 15 of 18
  cells-worth of runs, usually while active on ~50-90% of steps. Even the best variant still has contacts in traffic
  (opponent behaviour is predicted, not known). "Does not permit violations" has to become "reduces violations".
- Comment 3 (w(d) ignores the action): the action-conditioned trigger is what made the difference. On stock tyres the
  fallback shield is active on only 18-24% of steps for the fast driver and still prevents every crash, while the additive
  shield is active on 98%.
- Comment 2 (grip vs fixed decel): no clear winner yet. The fixed 6 m/s^2 assumption is more conservative, which helps
  safety in traffic; grip-aware lets the car drive further on stock tyres. Revisit with the RL agent.

## Step 3: baselines in races + PPO training
Race protocol (`racing/evaluate.py`): 3 opponents (PID / Pure Pursuit, 0.5-0.75 of the speed profile, gap keeping),
5 laps, DNF on first collision, 20 shared seeds, nominal and randomised (friction 0.85-1.15x, lidar noise).

Metric targets (Introduction feedback; our proposed values, defined in `TARGETS`):

| metric | target |
|---|---|
| clean-lap time vs PID+APF | <= 0.95x (>= 5% faster) |
| collisions per 10 laps | <= 0.5 |
| overtake success | >= 70% |
| shield active on race day | <= 10% of steps |
| time above 90% of mu*g | >= 10% (uses the grip) |
| time above 15 deg body slip | <= 1% (no sliding exploit) |

Classical baselines, 20 races x 5 laps (`results/eval_baselines.log`):

| controller | finished | clean lap | collisions/10 laps | overtakes | APF active | grip>90% | slip>15 |
|---|---|---|---|---|---|---|---|
| Pure Pursuit (nominal) | 0/20 | - | 61 (all rear-ends) | 0 | - | 12% | 0% |
| PID+APF (nominal) | 9/20 | 43.9 s (best 36.0) | 1.75 | 25/38 | 93% | 2.5% | 0.6% |
| PID+APF (randomised) | 12/20 | 44.0 s (best 35.5) | 1.18 | 28/40 | 93% | 2.3% | 0.8% |

PID+APF is "safe-ish but slow": the APF is on almost all the time and slows the car (Koren & Borenstein).

PPO training (`racing/train.py`, SB3 PPO, 7 envs, 1.5M + 1M + 1M steps over the 3 stages). Two runs so far,
seed 0: shield = action-conditioned fallback (grip reach) in every stage, and shield off in every stage
(this is how the unshielded ablation is defined, Plan feedback). Curves: `results/training_curves.png`.

Training efficiency, measured fairly (Plan feedback): every 50k steps the policy drives one solo lap *with the shield
removed*. First clean unshielded lap: both runs at 200k steps, so the shield did not speed up learning to lap. It did
speed up learning to lap *fast*: 34.9 s by 350k (shield) vs 38.3 s (no shield); by the end of stage 1 both reach ~32.5 s.

Crashes during training: stage 1 solo, ~0-5% of episodes with the shield vs 5-55% without. Stage 2 traffic, 7-18%
with the shield vs 20-54% without.

## Step 4: race day, seed 0 (full tables: `results/summary.md`)
Nominal, 20 races x 5 laps:

| controller | finished | clean lap | collisions/10 laps | passes/race | overtake success | shield active |
|---|---|---|---|---|---|---|
| **PPO + shield (ours)** | **17/20** | **34.3 s** | **0.38** | **2.65** | **88%** | 6% |
| PPO, no shield | 2/20 | 36.8 s | 5.53 | 1.05 | 72% | - |
| shield-trained PPO, shield removed | 5/20 | 34.9 s | 4.72 | 1.00 | 62% | - |
| unshielded PPO + shield at race time | 20/20 | 36.7 s | 0.00 | 1.25 | 81% | 16% |
| PID + APF | 9/20 | 43.9 s | 1.75 | 1.25 | 66% | 93% |
| Pure Pursuit | 0/20 | - | 61 | 0 | - | - |

- Ours meets all 6 targets on nominal races; under randomised friction/noise it misses two narrowly
  (0.63 collisions/10 laps vs <= 0.5; shield active 10.5% vs <= 10%).
- vs unshielded PPO and vs PID+APF: fewer collisions, more passes, more laps completed (Mann-Whitney p < 0.01);
  vs PID+APF also 22% faster laps (p = 2e-5).
- Training *with* the shield produced a much more aggressive overtaker (2.65 vs 1.25 passes/race when the shield is
  only bolted on at race time) but it leans on the shield: removed, it crashes in 15/20 races. The intervention
  penalty lowered shield use (60% of steps at the start of training -> 6% on race day) but did not make the policy
  safe on its own.
- The unshielded policy has the fastest single laps (best 28.2 s) but crashes in 18/20 races, mostly walls at the limit.
- Only one seed per configuration so far; seeds 1-2 next.

Videos (not in the repo): `~/Downloads/racing_videos/`, rendered with `python -m scripts.make_videos batchN`.

## Problems encountered
1. **F1TENTH map download.** Gym tries to download `Spielberg` on startup. Fixed by pointing its track loader at our `maps/`.
2. **Built-in lap counter is wrong** for our start position (it reported 60 s laps). We count laps from centerline progress.
3. **Simulator too slow (~35 control steps/s with 4 cars).** Upstream ray-casts every car into every LiDAR on every 10 ms
   step, and for a car *behind* the LiDAR its index range wraps and it loops the full 1080 beams. Patched
   (`racing/sim.py`): skip cars behind/out of range, only ray-cast cars into the ego scan on the step the policy sees,
   opponents scan once per control step. ~10x faster (~400 steps/s per env, no shield).
4. **Stock F1TENTH tyres have no grip limit.** Measured ~24 m/s^2 lateral at 8 m/s vs mu*g = 10.3. This is the
   Evans et al. loophole the proposal says it closes, and it makes "grip utilisation" meaningless. Added a
   friction-circle cap per axle (`racing/tires.py`, identical to stock below the limit). Kept stock tyres as an option.
   Consequence: default F1TENTH params saturate the rear axle first, so at the limit the car oversteers and spins.
5. **Speed loop brakes/accelerates at 9.5 m/s^2 (~92% of grip)**, so any steering on top spins the car with real tyres.
   Added traction control/ABS on every car (equal for all controllers): longitudinal accel clamped to the friction circle.
6. **TCS fooled during a spin.** It estimates lateral load as v*yaw_rate, which explodes in a spin, so it blocked braking
   and the car slid at constant speed (the single-track model also has no sliding drag). Above 15 deg body slip TCS now
   allows full braking.
7. **Shield saw opponents as walls.** LiDAR returns on the car ahead were treated as static, so the shield braked for a
   phantom stopped car. Opponent returns are now removed and opponents are predicted as moving obstacles.
8. **Opponents assumed constant speed** but they brake for traffic, so the shield reacted too late. Prediction now assumes
   opponents may brake at 6 m/s^2 (worst case).
9. **LiDAR occlusion.** With a car ahead, walls behind it are invisible, and the shield steered into a wall it could not
   see. The shield now adds the known track walls from the map.
10. **Kinematic-bicycle prediction did not match the sim** (no slip, no tyre limit, no steering lag); calibration showed
    end-pose errors of metres (`scripts/calib_pred.py`). Replaced with an exact-model predictor (`racing/predict.py`, numba):
    same ODE, RK4, steering servo + 2-step delay, speed loop, TCS.
11. **Safety check was not recursively feasible.** The backup manoeuvre assumed by the check was not among the fallback
    actions, so "safe now" did not imply "safe next step". The backup itself is now the first fallback candidate.
12. **Spins counted as safe** if the spinning car did not touch a wall within the horizon. Predicted body slip > 20 deg
    now counts as a violation.
13. **PID unstable at the 25 Hz control rate** (it was tuned at 100 Hz in step 1): it spun out at ~5 m/s on corner
    entry; none of 81 gain settings worked. Rewritten as curvature feed-forward + PID on cross-track error + heading
    error at the nearest point (`scripts/tune_pid.py`): laps cleanly at 35.3 s. Opponents use the same controller.
14. **First PID+APF baseline crashed in 20/20 races** (APF gains too aggressive, car sliding 22% of the time). Grid-tuned
    the APF gains (`scripts/tune_apf.py`) so the course baseline is fair.
15. **Grip metric read > 100% of mu*g** because it used v*yaw_rate as lateral acceleration, which is wrong while sliding.
    Now computed from the change of the velocity vector.
16. **Trail braking spins the car** under the friction-circle tyres: braking moves load off the rear axle, the rear
    saturates first. Traction control works on the whole-car friction circle, not per axle, so it does not prevent this;
    controllers have to brake before turning in.
17. **Evaluation merged two controllers into one row**: results were labelled by base controller ("ppo"), so the
    shield-trained-shield-removed variant would have been pooled with the ablation. Caught before results; results now
    carry their own label.
18. **First video in Downloads would not play**: an interrupted render left an mp4 without its index ("moov atom not
    found"). Videos now render to a temp file, are checked with ffprobe, then moved into place.
