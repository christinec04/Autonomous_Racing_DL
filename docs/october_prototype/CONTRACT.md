# Build contract for the parallel agents

Project root `C:\Users\shore\robotics\racing_proposal`. Python is `C:\Users\shore\robotics\.venv\Scripts\python.exe`
(numpy, matplotlib, torch CPU, stable-baselines3, gymnasium). Webots R2025a at
`%LOCALAPPDATA%\Programs\Webots`, its controller Python preference already points at that venv.

The professor asked two things.
1. Is high speed racing simulation possible in Webots, or do we need another platform? Answer with measurements.
2. Name one problem that makes this a high speed racing project and not regular self driving.
   Our answer is the friction circle. A race car drives at the tyre grip limit on purpose, so there is no spare
   grip for a safety override. A geometric APF shield (fixed radius, adds steering and braking on top of the
   policy) asks for more grip than exists and causes the crash it was meant to prevent, and its fixed radius
   triggers too late because braking distance grows with v squared (66 m/s needs about 150 m, the LiDAR sees 80 m).
   The friction aware shield sizes its horizon by stopping distance, caps speed with the map based braking envelope,
   and allocates its correction inside the friction circle. At road speeds both shields behave the same, at race
   speeds only the friction aware one works. That contrast is the experiment.

## Existing shared code (do not change signatures without telling the lead)
- `controllers/racelib/track.py` constants `G MU RHO CLA CDA MASS P_MAX WHEELBASE V_TOP HALF`, `grip(v)`,
  `drive_accel(v)`, class `Track` (`center line nrm tan kappa v ds n length`, `project(x, y, key)` returns
  `(i, s, lat)` with lat positive to the left, `pose(s, lat)` returns `(x, y, yaw)`, `ahead(i, metres)`).
  `track.json` is the cache, rebuild with `python track.py`.
- `controllers/racelib/car.py` class `Car` (Driver plus supervisor ground truth, `read()`, `aero()`,
  `command(steer, throttle, brake)` steer in [-1, 1] positive left, `step()`, `place(x, y, yaw)`), `out_dir(...)`
  makes `runs/...`. Controller args `key=value` land in `car.args`.
- `protos/RaceCar.proto` 860 kg, 450 kW, slick tyres `contactMaterial "slick"`, supervisor TRUE.
  Webots has no aero, `Car.step()` adds drag and downforce.
- Every controller adds `../racelib` to `sys.path`.

## Files each agent owns
- world agent: `tools/make_race_world.py`, `worlds/probe.wbt`, `worlds/race.wbt`, `worlds/race_train.wbt`,
  `controllers/race_probe/`, `protos/RaceCar.proto` fixes, `runs/probe/`, `tools/plot_probe.py`.
- shield agent: `controllers/racelib/shield.py`, `controllers/racelib/pilot.py`, `controllers/opponent_pid/`,
  `controllers/shield_test/`, `runs/shield_test/`, `tools/plot_shield.py`.
- rl agent: `controllers/race_ego/`, `controllers/racelib/env.py`, `runs/rl/`, `tools/plot_rl.py`.

## World layout (world agent produces, others rely on it)
- `race.wbt` and `race_train.wbt`: the track Road with barriers, `WorldInfo` contactProperties giving
  "slick" coulombFriction = `MU`, basicTimeStep 8. Cars are `DEF EGO RaceCar` plus `DEF OPP_1..OPP_3 RaceCar`.
  EGO controller `race_ego`, opponents `opponent_pid` with controllerArgs `pace=0.80|0.86|0.92`.
  EGO carries `Lidar { name "lidar" fieldOfView 3.14159 horizontalResolution 180 numberOfLayers 1 maxRange 80 }`
  in sensorsSlotFront. `race_train.wbt` has no buildings or lights. `race.wbt` is the pretty one.
  The generator takes `--ego-controller` and `--ego-args` so `shield_test` can reuse the same world
  (written to `worlds/shield_test.wbt`).
- The ego supervisor may move any car with `getFromDef("OPP_k")` translation, rotation and resetPhysics.

## Shield interface (shield agent produces, rl agent consumes)
```python
from shield import make_shield            # kind in {"none", "geometric", "friction"}
sh = make_shield(kind, track)
steer, throttle, brake, info = sh.filter(state, opponents, steer, throttle, brake)
# state: dict x y yaw vx vy speed i s lat   (i, s, lat from track.project)
# opponents: list of dicts x y yaw speed s lat
# info: dict intervened(bool) reason(str) grip_used(float, fraction of friction circle) u(float potential)
```
`pilot.py` holds `Pilot(track, pace, aggression)` returning `(steer, throttle, brake)` from the same state dict,
a pure pursuit plus speed profile tracker used by opponents and as the scripted stand in policy.

## Running Webots (one instance at a time, RAM is tight, about 5 GB free)
Always go through the guard with the shared lock so agents queue instead of stacking:
```
python C:/Users/shore/robotics/racing_proposal/tools/guard.py --lock C:/Users/shore/.racing-webots.lock --cap-gb 3 --min-free-gb 1.5 --cpu-pct 30 --max-temp-c 200 --start-max-c 200 --log <runs dir>/heartbeat.log --timeout-s <N> -- "%LOCALAPPDATA%/Programs/Webots/msys64/mingw64/bin/webots.exe" --batch --mode=fast --no-rendering --minimize --stdout --stderr <world>
```
(base `python` 3.11 has psutil and pywin32 for the guard). Controllers end the run with `simulationQuit`.
Never run two Webots at once, never launch the Webots GUI, never touch other desktop apps.

## Style
Match the existing files. Short docstrings, no em dashes, colons or semicolons as prose punctuation in comments.
