# Background: the project before this repo

This page covers what happened before the first commit on 2026-11-04: the course, the proposal deck and report,
the professor's follow-up questions, the October Webots prototype and simulator survey, the mockups, and how the
project ended up in F1TENTH Gym. Everything from Nov 4 onward is documented elsewhere:
[README](../README.md), [PROGRESS.md](../PROGRESS.md), [timeline.md](timeline.md),
[design-decisions.md](design-decisions.md), [feedback.md](feedback.md) and [experiments.md](experiments.md).

Sources are named inline. Times are local (EDT/EST) unless marked UTC. "Session" means a Claude Code session
transcript under `~/.claude/projects/`, identified by the first 8 characters of its id. Items that the sources do
not settle are marked **uncertain**.

**Note:** none of the October code is used by this repo. The original sits outside it at `~/robotics/racing_proposal` (a snapshot of its code, results and screenshots is archived in [october_prototype/](october_prototype/README.md)), and
this repo was written from scratch on Nov 4 (see [Path to this repo](#path-from-the-prototype-to-this-repo)).

## Contents

1. [Course and assignment context](#course-and-assignment-context)
2. [How the idea started](#how-the-idea-started-oct-10)
3. [The proposal deck](#the-proposal-deck-oct-1112)
4. [The professor's two follow-up asks](#the-professors-two-follow-up-asks-oct-15)
5. [Simulator survey](#simulator-survey)
6. [The October Webots prototype](#the-october-webots-prototype-oct-1516)
7. [Racing vs. self-driving: the friction-limit argument](#racing-vs-self-driving-the-friction-limit-argument)
8. [The October F1TENTH Gym port](#the-october-f1tenth-gym-port-oct-16)
9. [The proposal report](#the-proposal-report-oct-16)
10. [Proposal grading](#proposal-grading)
11. [Mockups and presentation visuals](#mockups-and-presentation-visuals)
12. [Path from the prototype to this repo](#path-from-the-prototype-to-this-repo)
13. [Open questions](#open-questions-and-things-not-found)

## Course and assignment context

| Item | What the sources say | Source |
|---|---|---|
| Course | CSCI-B 590, Indiana University Bloomington, Fall 2026, section listed as `FA26-BL-CSCI-B590-15290`. A personal note calls it the graduate Intro to Robotics course. The course's earlier programming assignment (PA1) used Webots with the e-puck robot. | Canvas page text pasted into session `6b01ea71` (2026-10-10); user memory notes |
| Team | Christine Chen, Chinmay Deshpande, Gabriel Shores (all MSCS, Luddy School) | deck slide 2; proposal report header |
| Proposal slides | Canvas assignment "Project Proposal Slides". The deck was exported Oct 11-12. | `6b01ea71`; file dates of `Robotics Presentation with Theme*.pdf` and `Robotics Presentation.pptx` |
| Proposal report | IEEE-format, 3 pages. The report gives the proposal date as October 12. The final PDF is dated Oct 16 22:48. | `ProjectProposalReport.pdf` |
| Proposal grade | 90/100, with a rubric of six criteria | rubric text pasted into session `2eda1f2e` (2026-11-04); [feedback.md](feedback.md) |
| Mid-term report | 3-4 pages, IEEE format, due 2026-11-13. Required sections: Introduction, System Architecture, Implemented Approach, Preliminary Results, Plan. | assignment brief given 2026-11-10 (user memory note); `report/midterm.tex` |
| Final demo and presentation | December 7, 2026 | proposal report, Section III-E |

`Downloads/Final Project Proposal.pdf` is unrelated: it is a finance-course proposal on lattice models. Likewise
`Downloads/CSCI-B590Presentation.pdf` is from a different B590 offering (a spring 2026 distributed-systems
project), not this course.

## How the idea started (Oct 10)

Session `6b01ea71` (2026-10-10) shows the first written idea. The pasted draft was titled *"Escaping Local Minima:
A Hybrid APF and Deep Reinforcement Learning Local Navigator"*. In that version a differential-drive robot
(TurtleBot3 or e-puck) in Webots drives by APF. When it gets stuck in a U-shaped trap (low speed, far from the
goal), a PPO agent takes over to escape and then hands control back. It was benchmarked against Bug-2.

The same paste then contained a reworked version, *"APF-Shielded Deep Reinforcement Learning for High-Speed
Autonomous Racing"*. Here the RL agent drives full-time and the APF acts as a safety shield that overrides
unsafe actions. That version already had:

- 4-5 Ackermann cars on a Singapore-styled F1 track in Webots
- PID "dummy" opponents
- elliptical opponent fields, longer front and back
- a reward of speed + sector progress + pass bonus, with a penalty for shield triggers
- a 10-week plan

The racing version is the one the team carried forward. The sources do not record who wrote either draft or why
the team switched (**uncertain**).

## The proposal deck (Oct 11-12)

Source: `Downloads/Robotics Presentation with Theme (1).pdf` (12 slides, Oct 12). The `.pptx` is the editable
copy.

- **Pitch:** "A race car in Webots that learns to race other cars with reinforcement learning, while the
  potential field method from class stops it from crashing."
- **Motivation:** "Pure RL is wasteful" (most early training is spent crashing). "Pure APF is timid" (safe but
  slow, and it can't plan a pass).
- **Objective:** race 4 autonomous cars on an F1 Singapore track in Webots. If the RL car requests a move that
  breaks the APF safety threshold, for example a risky divebomb into a corner, the shield overrides steering and
  braking.
- **Literature:** PID + APF (Khatib), Pure Pursuit and Stanley, GT Sophy, ResRace, Evans et al. 2023 and TraD-RL.
  The deck's takeaway: "a safety layer speeds up RL training a lot. The open question is keeping the car from
  turning timid."
- **Plan:** Wk 1 track + vehicles; Wk 2-3 three Pure Pursuit opponents and moving elliptical fields; Wk 4-5
  connect Webots to Stable-Baselines3 and train solo with the shield on; Wk 6-7 overtakes; Wk 8 race day.
- **Metrics:** lap time, collision rate, APF intervention frequency and overtake success rate. No target values
  were given.
- **Equipment:** Webots, 4 Ackermann cars, 2D LiDAR, GPS and IMU, Python 3.10+, SB3/PyTorch and Gymnasium.

The deck planned to use **Webots**. The switch to F1TENTH Gym came after the professor's questions (below).

## The professor's two follow-up asks (Oct 15)

After the proposal presentation, the professor asked for two things. The wording below is the team's paraphrase,
as given to session `c53285f1` on 2026-10-15 at 18:57:

> 1. Check if racing simulation is possible on Webots and to look into other sim platforms if not.
> 2. We need to find a problem to discuss that directly distinguishes this project as a high speed racing
>    project and not a regular self driving project.

| Ask | Answer that came out of Oct 15-16 | Where it ended up |
|---|---|---|
| 1. Can Webots do racing? | Webots can run a car at race speed, but its friction model is wrong in a way that matters for this project. The friction pyramid is aligned with the world's x/y axes, so a car can get up to about 1.35-1.4x the set grip depending on its heading. Webots also has no tyre slip curve and no aerodynamics, and it is slow with 4 cars plus LiDAR. The survey found no published racing-RL work that uses Webots. The recommendation was to train in a fast single-track model (the F1TENTH Gym family) and keep Webots only for visuals. | The proposal report switched to F1TENTH Gym and added a "Why F1TENTH Gym" paragraph (Section III-G). |
| 2. What makes this racing rather than self-driving? | The friction circle. A race car runs at the tyre limit on purpose, so a shield that adds steering and braking on top of the policy asks for grip that does not exist, and it can cause the crash it was meant to prevent. A fixed-radius APF also triggers too late, because braking distance grows with v². | The report's introduction ("in racing the car runs at the limit of tire friction"), the grip-dependent reach in Section II, and the grip-utilization and slip-angle metrics. In this repo: the friction-circle tyre model, grip-aware reach and the friction estimate (see [below](#how-it-carried-into-this-repo)). |

The reasoning behind both answers was written down in `~/robotics/racing_proposal/CONTRACT.md` (Oct 15 20:27).

## Simulator survey

On Oct 15, a research subagent in session `c53285f1` surveyed the simulators. Its full output file
(`AppData/Local/Temp/claude/C--Users-shore/c53285f1-.../tasks/*.output`) no longer exists. The table below is
put together from the parts quoted in the parent transcript, the deck and the proposal report. Rows marked
"listed only" were in the survey brief, but their verdict text was not kept (**uncertain**).

| Platform | What the sources say | Verdict |
|---|---|---|
| **Webots** (R2025a, ODE fork) | Every contact uses `dContactApprox1`, which forces ODE's friction pyramid instead of a cone. `forceDependentSlip` is a linear slip law with no Pacejka peak. `Car.proto` has no drag or downforce, and the stock BMW X5 tops out at 50 m/s. The survey found no published racing or high-speed RL paper using Webots. | Keep only for demos and visual checks. Confirmed by measurement (next section). |
| **F1TENTH Gym** (`f1tenth_gym`) | 2D, headless and fast. Dynamic single-track model with tyre slip. Ray-cast LiDAR, multi-agent with collision detection. The standard platform for the APF+RL work the proposal compares against (ResRace, RaceMOP). Stock tyres are linear, so there is no friction circle. | Chosen. Main reasons in the report: tyre slip, speed and comparability. |
| **Gym-Khana** | An F1TENTH-family gym with a Pacejka ("STP") tyre model. It was tried on Oct 16 (`f1t_src/khana_pip`, empty). The Oct 16 port wrote its own STP model instead. | Not used. |
| **CARLA** | Named in the report as "also considered" | Not chosen |
| TORCS, Assetto Corsa gym, AWSIM, BeamNG, Learn-to-Race, racecar_gym, tmrl | listed only | Not chosen; reasons not kept |

F1TENTH Gym branches checked out on Oct 16 (`~/robotics/f1t_src`, all from `github.com/f1tenth/f1tenth_gym`):

| Folder | Branch | Last commit |
|---|---|---|
| `gym_main` | `main` | 2025-06-09 |
| `gym_v1` | `v1.0.0` | 2024-09-17 |
| `gym_dyn` | `dev-dynamics` (multi-body PAC2002 model) | 2025-11-24 |
| `br_zirui` | `zirui` | 2025-09-16 |
| `br_dev-zirui-merge` | `dev-zirui-merge` | 2025-07-22 |
| `br_dev-features` | `dev-features` | 2026-08-21 |
| `br_dev-jax` | `dev-jax` | 2026-09-04 |

The October port ran on `gym_dyn`. This repo pins `f1tenth_gym @ v1.0.0` ([architecture.md](architecture.md)).

## The October Webots prototype (Oct 15-16)

**Where:** `~/robotics/racing_proposal` (not in this repo).
**Built by:** session `c53285f1`, Oct 15 18:57 to Oct 16 about 12:54. A lead agent split the work across
subagents for the world and physics probe, the shields and opponents, RL, the simulator survey and, later, an
F1TENTH port. `CONTRACT.md` records each agent's interfaces and which files it owned.

### What was built

| Part | Files | Notes |
|---|---|---|
| Track library | `controllers/racelib/track.py`, `track.json` | A 2.1 km street circuit modelled on the deck's Singapore-style layout. It has a minimum-curvature racing line and a friction-limited speed profile from 10 to 66 m/s, for an ideal lap of about 81 s. |
| Race car | `protos/RaceCar.proto`, `racelib/car.py` | **Full-size car, not F1TENTH scale:** 860 kg, 450 kW, slick tyres, mu 1.6. Aero drag and downforce were added through Supervisor forces, because Webots has none. |
| Worlds | `worlds/race.wbt` (visual), `race_train.wbt` (no buildings), `race_demo.wbt`, `probe.wbt`, `shield_test*.wbt`, `street_circuit.wbt` | Ego car plus `OPP_1..3`. Ego LiDAR: 180 beams over 180°, 80 m range. 8 ms physics step. |
| Opponents and pilot | `controllers/opponent_pid`, `racelib/pilot.py` | Pure Pursuit plus a speed profile, at pace 0.80, 0.86 and 0.92 |
| Shields | `racelib/shield.py` | `none`, `geometric` (the course-style APF: fixed radius, adds steering and braking) and `friction` (horizon from stopping distance, speed cap from a braking envelope, correction kept inside the friction circle) |
| RL | `controllers/race_ego`, `racelib/env.py` | A Gymnasium env inside Webots, plus an offline Python car model for faster debugging, and PPO from SB3 |
| Older proposal scenes | `controllers/hybrid_apf_drl`, `hamster_*`, `trap_supervisor`, `worlds/apf_trap.wbt`, `hamster_trap.wbt` | From Oct 10, for the earlier trap-escape idea (see Mockups) |

### Problems found while building

These are all from the `c53285f1` transcript.

- **Laptop temperature:** the machine's thermal sensor read a flat about 95 °C even at idle, so the run guard
  refused or killed every Webots launch. The temperature limits were removed on the user's instruction, and the
  memory and CPU caps were kept.
- **Car models would not load:** `RaceCar.proto` pointed at `webots://` vehicle protos that are not installed
  locally. It was switched to GitHub R2025a URLs.
- **Engine speed cap:** the car topped out at 22.9 m/s because of Webots' default 4500 rpm engine limit. It was
  raised to 18000 rpm, and every earlier number was discarded.
- **Weak brakes:** with `brakeCoefficient` 400, full braking gave only about 6.5 m/s² on top of coasting. It was
  raised to 2000, after which braking matched the model (24.8 vs 25.8 m/s² at 55 m/s).
- **Slow launch:** acceleration below 41 m/s was limited to about 5.5 m/s². The cause is the Driver library's
  wheel-acceleration torque limiter (50 rad/s²), which no proto setting can change.
- **Geometric shield deadlock:** at a standstill the geometric shield kept braking forever. The repo hit a similar
  deadlock with its own shield on Nov 4 (escape fix, [timeline.md](timeline.md)).
- **Machine stall:** the machine stalled or slept for 45 minutes overnight (57 of 63 GB committed). Later runs
  were refused for low free RAM. The session ended abruptly about 12:54 on Oct 16, while the system was low on
  memory. The last records show background loops being stopped for low memory.

### Physics probe (question 1 evidence)

Source: `runs/probe/*.json` and `*.png`, and the world agent's report in `c53285f1`. The car used
`brakeCoefficient` 2000 and 18000 rpm.

| Test | Result |
|---|---|
| 0-100 / 0-200 km/h | 5.98 s / 10.85 s |
| Top speed | Hard plateau at 71 m/s, but only with the added aero. The cause was never found, and it does not bind on a 66 m/s track. |
| Braking 60 to 0 m/s | 3.0 s over 83 m |
| Max lateral g | 2.4 g at 56 m/s with downforce (0.91 of model); 1.9 g without |
| Barrier tunnelling at 30/50/70 m/s | None at 8 or 16 ms. Impacts were almost elastic (70 m/s in, about 66 m/s out). |
| **Friction shape** | **A box aligned with the world x/y axes**, not with the wheels. Locked-wheel deceleration / (mu g) was 0.96 along world x and 0.95 along world y, but 1.35 with the car at 30-45°. Skidpad lateral g swung between about 1.6 and 2.7 once per revolution. Asymmetric `coulombFriction` made it worse (1.13-2.45x). There is no fix within Webots. |
| Combined slip | Reproduced: full braking mid-corner spins the car (body slip 19.5° at 30 m/s, 32.8° at 49 m/s). Half braking stays under 9°. |
| Real-time factor, 4 cars + LiDAR, 30% CPU cap | 1.84x at 8 ms, 6.5x at 16 ms. The sweep world ran at about 2.9x. |

### Road-vs-race shield sweep (question 2 evidence)

Source: `runs/shield_test/sweep/summary.json` and `results.csv` (finished Oct 16 09:39).

Setup:

- **Road:** ego pace 0.45, aggression 1.0 and 1.3
- **Race:** ego pace 0.95 with divebomb passes, aggression 1.0, 1.15 and 1.3
- 4 start positions per setting, scripted pilot (no RL), 60 runs in total

Crashes per 4 runs:

| Regime | Aggression | No shield | Geometric APF | Friction-aware |
|---|---|---|---|---|
| road | 1.0 | 0 | 0 | 0 |
| road | 1.3 | 0 | 0 | 0 |
| race | 1.0 | 2 (car contact) | 3 (car) | 4 (car) |
| race | 1.15 | 4 (3 wall, 1 car) | 4 (2 wall, 1 spin, 1 car) | **1** (wall) |
| race | 1.3 | 4 (wall) | 4 (wall) | **3** (2 car, 1 wall) |
| **race total** | | 10/12 | 11/12 | **8/12** |

Other numbers:

- **Road:** mean lap 90 s at aggression 1.0 and 74 s at 1.3. All three shields were almost identical. The
  geometric shield was active on 1-3.5% of steps.
- **Grip commanded (p95), race:** 1.7-4.1 times the available grip with no shield or the geometric shield. With
  the friction-aware shield it was 1.7-2.6, before its projection.
- **Shield activity, race:** 17-44% of steps for the friction-aware shield and 3.5-8% for the geometric shield.

How to read this:

- At road speeds the shields are indistinguishable. At race speeds the geometric shield is no better than no
  shield, because nearly every race run ends at a wall.
- The friction-aware shield removed most of the wall crashes at aggression 1.15 and above. Even so, it still
  crashed in 8 of 12 race runs, mostly by contact with other cars.
- The transcript called the full result "more mixed than the early runs suggested". The early smoke runs (2 runs
  per setting) had shown the friction shield finishing where the others crashed.
- The race-pace car contacts at aggression 1.0 were traced to the scripted pilot's passing logic, not to the
  shields. That logic was patched before the full sweep, but contacts still happened.
- Sample size is 4 per cell, so none of these differences were tested statistically.

### RL training in October

**Offline Python car model**, PPO, 500k steps each, seed 0. Sources: `runs/rl/sim_*/state.json` and
`eval_opp*_summary.json`.

| | No shield | Geometric | Friction-aware |
|---|---|---|---|
| Training episodes (each ends in a crash or timeout) | 1,348 | 726 | 464 |
| Crashes during training (from transcript) | 1,344 of 1,348 | n/a | 320 of 464 |
| Eval solo: laps / crashes per km | 0 / 1.87 | 0 / 6.0 | 0 / 0.99 |
| Eval with 3 opponents: laps / crashes per km | 0 / 6.0 | 0 / 6.9 | **2 / 0.84** (best lap 94.1 s) |

The friction shield cut training crashes by about 4x and was the only setup that finished a lap. Its laps
(94-97 s) were still slower than the scripted pilot (93 s) and far from the ideal of 81 s.

**PPO inside Webots** (`runs/rl/wb_friction`): 126,671 steps and 182 episodes in one 25-minute chunk, at about
90-100 steps/s, or about 3x real time. An earlier chunk ran on the weak-brake car and was discarded
(`wb_old_brake400_friction`). The planned no-shield Webots run (`wb_none`) has no `state.json` and was apparently
never completed (**uncertain**).

The transcript estimated that a 1M-step run would take most of a day per configuration in Webots with 4 cars,
compared with about 1,600 steps/s in the offline model. That was the throughput argument against training in
Webots.

### Visual demo and replay page

- On Oct 16 a viewable Webots demo (`worlds/race_demo.wbt`) looped no shield, then geometric, then friction-aware
  at aggression 1.3 from the run-up to Turn 1, with a custom chase camera. The first two hit the Turn 1 barrier
  and the friction-aware car lapped in about 93 s.
- An interactive replay page of the 60 sweep runs, with a Webots-grip heading panel, was published as a private
  claude.ai artifact. The link is in the `c53285f1` transcript.
- No write-up was sent to the professor from this session. It ended before the planned report was written.

## Racing vs. self-driving: the friction-limit argument

The argument, as stated in `CONTRACT.md` and the transcript:

1. A normal self-driving car uses about 0.3 g, so a safety override always has spare grip.
2. A race car runs at the grip limit on purpose. A geometric APF shield adds steering and braking on top of the
   policy, so it asks for more grip than exists and can cause the crash it was meant to stop.
3. A fixed APF radius triggers too late. Stopping from 66 m/s takes about 150 m (full-size car), while the
   LiDAR saw 80 m.
4. A friction-aware shield instead sizes its horizon by stopping distance, caps speed with a braking envelope,
   and keeps its correction inside the friction circle.

### How it carried into the proposal report

- **Introduction:** "in racing the car runs at the limit of tire friction".
- **Literature:** Koren and Borenstein's 0.8 m/s APF robot; Ge and Cui's fixed braking limit; Evans et al.'s
  agents sliding above 15° slip on linear tyres.
- **Section II:** the shield's reach "depends on the grip left over after cornering". The grader noted that this
  was inconsistent with Section III-C, which used a fixed deceleration ([feedback.md](feedback.md)).
- **Metrics:** "Grip utilization" (g-g diagram, share of time above 90% of mu g) and slip-angle checks.

### How it carried into this repo

The Nov 4 build is 1:10 scale F1TENTH, not the October full-size car. It re-derived the same idea:

- **Tyre model:** stock F1TENTH tyres corner at more than 2 g. A friction-circle cap per axle
  (`tire="saturated"`, later `saturated_v2`) and traction control were added.
  [design-decisions.md](design-decisions.md) rows 3, 4 and 21; [architecture.md](architecture.md).
- **Shield reach:** fixed (6 m/s²) and grip-aware reach were both implemented
  ([design-decisions.md](design-decisions.md) row 8). The shield checks the policy's own action with an
  exact-model rollout ([feedback.md](feedback.md)).
- **Grip metrics:** g-g use (E12) and stock-tyre exploitation (E27) in [experiments.md](experiments.md).
- **Friction estimate:** the shield estimates the friction online (E35, E35b), combined with the relaxed opponent
  check in E36 and E36b/E35c, and the policy was retrained with it in E37 ([experiments.md](experiments.md)).

## The October F1TENTH Gym port (Oct 16)

At 09:32 on Oct 16 the user asked to "try that other program the f1tenth thing too". A subagent ported the
October stack to F1TENTH Gym in `~/robotics/racing_proposal/f1tenth/`:

- `bridge.py` reuses `racelib` unchanged.
- `vehicle.py` keeps the **full-size** 860 kg / 450 kW / mu 1.6 car. The gym's stock road-car parameters spun
  under braking.
- `stp.py` is a single-track model with saturating Pacejka tyres and a friction circle per axle, because the
  released ST model has linear tyres.
- `make_map.py` exports the 2.1 km circuit as `maps/GrandCircuit` at 0.2 m/pixel.
- `sweep.py` and `train.py` use the same protocol as Webots, on `gym_dyn`.

Partial results, from `runs/f1tenth/`:

| Sweep | Runs | Outcome |
|---|---|---|
| `sweep_stp` (Pacejka, friction circle) | 60 | Road: 24/24 clean. Race: every run with every shield crashed, mostly by spinning (friction-aware 11 spins + 1 car contact, geometric 12 spins, none 8 spins + 4 wall). |
| `sweep_st` (gym linear tyres) | 26 (incomplete, killed on timeout) | All finished runs were clean, including no shield at aggression 1.3. This is consistent with linear tyres never running out of grip. |
| PPO training (`train.out`) | none | Never started: it was stuck waiting for the lock and refused for low RAM. |

There is also a calibration file, `runs/f1tenth/calib*.json`. This port was cut off when the session ended. Its
findings were never summarised in a transcript, so the reading above is from the result files only. The
all-spin outcome on `stp` suggests the shield and pilot settings were not tuned for that model. A tuned sweep
(`sweep_tuned.out`) failed to start (**uncertain**).

## The proposal report (Oct 16)

The written proposal was drafted the evening of Oct 16, after the Webots and F1TENTH work above. File versions in
`~/Downloads`:

| File | Time (Oct 16) | Notes |
|---|---|---|
| `Robotics_Proposal_Report.pdf` | 19:10 | First draft, still in the IEEE template with its placeholder text. Already says F1TENTH Gym. |
| `Robotics_Proposal_Report.docx` | 21:51 | Adds the "Why F1TENTH Gym" paragraph |
| `Robotics_Proposal_Report (1).pdf` / `(1).docx` | 21:15 / 22:26 | Intermediate versions |
| `Robotics_Proposal_Report (2)-(4).docx` | 22:33-22:45 | Identical size, so near-final |
| `ProjectProposalReport.pdf` | 22:48 | Final. About 97% word-identical to the graded copy; the differences are line-break hyphenation only. |
| `annotated-Robotics_Proposal_Report_Chen_Deshpande_Shores.docx.pdf` | downloaded Nov 4 11:24 | The graded copy, exported from Google Docs. It contains no PDF annotations; the grader's comments came separately as rubric text. |

Content of the final report:

- **Problem:** race an ego car against three PID-controlled opponents on a Singapore-inspired circuit in F1TENTH
  Gym. PPO drives, and an APF shield intervenes only when a crash is imminent.
- **Pipeline:** policy, then the APF shield (an environment wrapper that can be switched off), then the
  simulator. The shield reports whether and how strongly it intervened.
- **Observation:** about 60 LiDAR beams (downsampled from 1080 over 270°); speed, yaw rate and steering;
  centerline offset and heading error; the nearest 1-2 opponents. **Actions:** steering and speed (or
  acceleration).
- **Reward (Eq. 1):** `R_t = w1 v_par + w2 Δs + w5 1_pass - w3 λ_t - w4 1_collision`, where `λ_t` is the
  intervention strength, from 0 to 1.
- **Shield:**
  - LiDAR repulsion plus elliptical fields stretched along each opponent's heading.
  - Speed-dependent reach `d0` = minimum distance + braking distance at an assumed deceleration.
  - Additive blend `a_final = clip(a_rl + w(d) a_apf)` (Eq. 2), with `w(d) = clip((d0 - d_obs)/(d0 - d_crit), 0, 1)`
    (Eq. 3), smoothed over a few steps.
- **Curriculum:** (1) solo laps with the shield on, (2) slow opponents, (3) varied speeds and starts. Friction and
  sensor noise randomised; several seeds.
- **Evaluation:**
  - Pure Pursuit, PID+APF, unshielded PPO and PPO+APF.
  - 20 four-car races of 5 laps each, shared seeds, 3 training seeds, nominal and randomised conditions.
  - Mann-Whitney U tests.
  - Metrics: lap time, collisions per 10 laps, overtake success (with an exact attempt definition), intervention
    frequency, training steps to first clean lap, and grip utilization with a slip-angle check.
- **Equipment:** simulation only, with default F1TENTH vehicle parameters; team laptops, with IU research
  computing as a fallback.
- **Why F1TENTH Gym:** tyre slip, headless speed for millions of PPO steps, and it is the platform used by
  ResRace and RaceMOP. CARLA and Webots were "also considered".
- **Team roles:** not stated. The grader asked for them.
- **Acknowledgement:** LLM assistance (Claude, ChatGPT) with prose and with checking the math and physics.

Changes from the deck:

- the simulator (Webots to F1TENTH Gym)
- the opponents (Pure Pursuit to PID or Pure Pursuit)
- the sensors (GPS/IMU replaced by simulator state)
- two new metrics: training steps to first clean lap and grip utilization
- the statistical protocol

Note that the October prototype used a full-size car on a 2.1 km circuit, while the report specifies the 1:10
F1TENTH car with default parameters.

## Proposal grading

The proposal scored 90/100:

| Criterion | Score |
|---|---|
| Introduction | 16/20 |
| Literature | 20/20 |
| Content | 16/20 |
| Approach | 10/10 |
| Plan | 8/10 |
| Format | 10/10 |

The comments cover:

- metric targets
- the difference from ResRace/RaceMOP
- the additive shield's lack of a guarantee
- fixed deceleration vs. grip-dependent reach
- `w(d)` not depending on the action
- team roles, a risk plan, and the training-efficiency metric

Each comment is mapped to code and evidence in [feedback.md](feedback.md), so it is not repeated here. The rubric
text reached this repo through the first message of session `2eda1f2e` on Nov 4.

## Mockups and presentation visuals

| What | Where | Made | Notes |
|---|---|---|---|
| 6 concept renders, 1920x1080, dark theme | `~/Downloads/apf-shield-racing-mockups/01_simulator_scene.png` ... `06_control_loop.png` | Oct 10 08:28, session `6b01ea71` | Drawn illustrations, **not** simulator output. The numbers in them (187 km/h, U = 0.83, rewards) are invented, and the track is a made-up 21-corner, 2.1 km Marina Bay-style circuit. The user rejected them because they were not Webots. |
| Webots racing screenshots and clips | `~/robotics/racing_proposal/hires/` and `shots/` (`01_webots_chase_shield` ... `06_webots_full_track_top`) | Oct 10 about 08:47 | Real Webots R2025a renders: a street circuit (`worlds/street_circuit.wbt`) with BMW X5 cars, Road protos with barriers and a SICK LiDAR |
| Trap-escape scenes (first idea) | `trap_hires/`, `trap_shots/` (TurtleBot3) and `hamster_hires/`, `hamster_shots/` (the course's Hamster robot, Robomation) | Oct 10 08:50-08:55 | The TurtleBot3 meshes initially failed to download |
| Final deck images | `Robotics Presentation.pptx` | Oct 11-12 | Light-theme diagrams: an oval track with opponents and an APF repulsion zone (slide 3), and a corner comparing PID+APF / RL alone / ours (slide 8), plus template art. They do not appear to be any of the Oct 10 mockups or Webots screenshots. Who made them is not recorded (**uncertain**). |
| Oct 16 Webots demo and replay page | `worlds/race_demo.wbt`; private claude.ai artifact | Oct 16 | See the Webots prototype section |

## Path from the prototype to this repo

1. **Oct 10-12:** the deck planned Webots.
2. **Oct 15:** the professor asked whether Webots can do racing.
3. **Oct 15-16:** the survey and the probe showed that Webots' friction is world-axis-aligned and cannot be fixed,
   that it has no aero and no tyre curve, and that it runs slowly with 4 cars. The survey recommended training in
   the F1TENTH Gym family.
4. **Oct 16, morning:** a port to F1TENTH Gym was started and got as far as two shield sweeps.
5. **Oct 16, evening:** the proposal report was written with F1TENTH Gym as the simulator and gave three reasons:
   tyre slip, headless speed, and comparability with ResRace and RaceMOP. The decision itself is not recorded in
   any transcript. It may have been made by the team outside Claude Code (**uncertain**).
6. **Oct 17 - Nov 3:** no project work was found. All 13 transcripts in this period that mention the project do
   so only through a memory index. The repo's [timeline.md](timeline.md) starts on Nov 4.
7. **Nov 4, 11:18:** Christine Chen created `christinec04/Autonomous_Racing_DL` (initial commit `f54092d`).
8. **Nov 4, 11:23:** Gabriel Shores started session `2eda1f2e`. It cloned the repo into `~/gabe`, read the graded
   proposal and rubric, and began building with the instruction to address the feedback incrementally.
   - First commits: Step 1 (track, F1TENTH wrapper, Pure Pursuit and PID) at 11:36, and Step 2a at 11:42
     ([presquash_history.md](presquash_history.md)).
   - It built a new 199 m, 1:10-scale Singapore-inspired map and used F1TENTH Gym v1.0.

The repo was written from scratch. It does not import or mention the October `racelib`, Webots or the full-size
car; a grep of the repo for `racing_proposal`, `racelib` and `Webots` finds nothing before this page. The ideas
that carried over are the friction-circle tyres, the grip-aware shield and a shield that checks the policy's
action.

## Open questions and things not found

- **Course title:** "Intro to Robotics" comes only from a personal memory note, not from a course document.
- **The professor:** the professor's name and the exact date and wording of the two follow-up asks were not
  found. The quoted wording is the team's paraphrase from Oct 15.
- **Presentation date:** the date of the in-class presentation is not recorded. The deck was exported Oct 11-12
  and the report calls Oct 12 the proposal date.
- **Who decided on F1TENTH Gym, and where:** no transcript records the decision. The report drafts appear at
  19:10 on Oct 16.
- **Full simulator survey:** the subagent's output file no longer exists. Verdicts for TORCS, Assetto Corsa gym,
  AWSIM, BeamNG, Learn-to-Race, racecar_gym and tmrl are not available.
- **Results sent to the professor:** whether any October results or the replay page went to the professor is
  unknown. No write-up was produced in `c53285f1`.
- **Webots no-shield training:** whether the `wb_none` run ever completed is unknown.
- **Gym-Khana:** whether it was ever installed is unknown (its folder is empty).
- **Final deck images:** who made them is not recorded.
- **Team roles:** never stated in the proposal; see [feedback.md](feedback.md) for how the repo answers this.
