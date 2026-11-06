# Design decisions and deviations from the proposal

Each entry: what the proposal said, what we did, why. Problems that forced a decision are numbered as in
[PROGRESS.md](../PROGRESS.md) ("Problems encountered").

| # | proposal | implementation | why |
|---|---|---|---|
| 1 | Singapore-inspired circuit as an occupancy grid | `racing/track_gen.py`: 19 filleted corners, 199 m, 2.8 m wide; long main straight, chicane, back straight, run of 90 deg corners, hairpin | Marina Bay character at 1:10 scale; 2.8 m leaves room to pass |
| 2 | keep default F1TENTH vehicle parameters | kept | comparability with [6]-[9] |
| 3 | dynamic single-track model "with tyre slip" | added a friction-circle cap on each axle (`tire="saturated"`); stock is `tire="linear"` | stock tyres corner at > 2 g (measured 24 m/s^2 at 8 m/s); this is the sliding loophole of Evans et al. the proposal wants to close, and without it "grip utilisation" is meaningless (problem 4) |
| 4 | (none) | traction control on every car | the F1TENTH speed loop accelerates and brakes at 92% of grip, which spins the car under real tyres (problems 5-6). Equal for all controllers, so comparisons stay fair |
| 5 | shield checks LiDAR + opponent poses | shield also uses the known track walls from the map | opponents occlude the lidar; the shield steered into walls it could not see (problem 9) |
| 6 | APF correction weighted by distance (Eq. 3) | kept as the `additive` variant; ours is action-conditioned with an exact-model predictor | grader comment; the simple bicycle model was metres off (problem 10) |
| 7 | shield "does not permit violations" | fallback replaces the action with a braking backup; still not a guarantee | grader comment; the stress test shows remaining car contacts |
| 8 | reach from braking distance with a fixed deceleration | both fixed (6 m/s^2) and grip-aware reach implemented | grader comment (consistency) |
| 9 | PID opponents, "PID+APF" baseline | PID rewritten as curvature feed-forward + PID on cross-track + heading term; APF gains grid-tuned | the textbook PID spun out at the 25 Hz control rate (problem 13); the first APF baseline crashed 20/20 (problem 14). A broken baseline would flatter our method |
| 10 | Pure Pursuit baseline | Pure Pursuit at 0.85 of the grip-limited profile, no avoidance | it is the classical floor; it rear-ends slower cars, as expected |
| 11 | reward Eq. 1 | same terms; episodes are a fixed 40 s instead of "until finished" | with a progress reward, a fixed-length episode rewards covering more distance, i.e. speed |
| 12 | speed or acceleration action | target speed in [1, 16] m/s | simpler to learn; the speed loop and traction control handle the rest |
| 13 | about 60 lidar beams | 60 min-pooled sectors (min, not subsample) | a thin obstacle between subsampled beams would vanish |
| 14 | 3 seeds per learned controller | 3 seeds for ours and the no-shield ablation (`results/seed_summary.md`); seed 0 only for the additive-shield, residual, dropout and timidity variants (residual + our shield, seeds 1-2: running) | compute; runs take about 2 h each on 7 cores |
| 15 | unshielded ablation | shield off in all stages | grader comment (stage 1 had the shield on) |
| 16 | training steps to first clean lap | measured with the shield removed, every 50k steps | grader comment (the shield would otherwise guarantee clean laps) |
| 17 | control rate unspecified | 25 Hz policy, 100 Hz physics | standard for F1TENTH RL; keeps PPO horizons manageable |
| 18 | race 5 laps | DNF on the first collision | the simulator freezes a car after a collision; a DNF is also the honest outcome |
| 19 | (none) | deadlock escape in the shield (`ShieldConfig(escape=True)`) | the shield could stop the car next to a wall or an opponent and never release it (problem 23, E19) |
| 20 | (none) | stall recovery outside the policy (`EnvConfig(recover=True)`): reverse out, then hand back | the policy itself stopped nose-to-wall in the chicane (problems 26-27, E21); seed 0 16/20 -> 19/20 |
| 21 | (none) | final results on the post-spin-fixed tyre model (`tire="saturated_v2"`); every controller re-raced on it | after a spin the stock code kept a wound-up slip angle and the car could not restart (problem 24) |
| 22 | (none) | 20 races for every controller, 50 for the four main ones (E25) | 20 races cannot separate 19/20 from 18/20 |
