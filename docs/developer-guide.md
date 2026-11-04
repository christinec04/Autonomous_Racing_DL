# Developer guide

How to extend the code without breaking the experiments.

## Conventions

- Physical actions are `(steering angle [rad], target speed [m/s])`. The policy works in normalised `[-1, 1]^2`;
  `RaceEnv.to_physical` / `to_normalized` convert.
- F1TENTH state vector (single track): `x, y, steering angle, speed, yaw, yaw rate, body slip angle`
  (`env._states()` returns it for every car, ego first).
- Lateral offset `d` is positive to the left of the centerline; `progress` is unwrapped arc length in metres.
- Everything that changes behaviour goes in a dataclass config (`EnvConfig`, `ShieldConfig`) with a default equal to
  the current behaviour, so older runs stay reproducible.

## Add a classical controller

1. Implement `act(x, y, yaw, v) -> (steer, speed)` in `racing/controllers.py` (see `PurePursuit`).
2. Register it in `racing/evaluate.py`: a branch in `make_controller` and an entry in `SHIELD_FOR`
   (which shield, if any, it races with).
3. `python -m racing.evaluate --controllers <name> --races 20 --out results/eval_<name>.json`.

## Add a shield variant

1. Add the mode to `ShieldConfig.mode` handling in `APFShield.__call__` (`racing/shield.py`). Return
   `(a_final, lambda, info)`; `lambda` in [0, 1] feeds the reward and the metrics, `info["fallback"]` is logged.
2. If it needs predictions, use `predict_clearance(cands, x7, steer_buf, scan, opps_world)`. It is exact for the ego
   (same model as the simulator); keep it that way. If you change the tyre model, traction control or the speed
   loop, change `racing/predict.py` too and run `pytest tests/test_predictor.py`.
3. Stress-test it before training: add it to `VARIANTS` in `scripts/shield_stress.py`.
4. Train: add a key to `SHIELDS` in `racing/train.py`.

## Add a track

`racing/track_gen.py` builds a track from a list of corner vertices with fillet radii. Copy it, change `VERTICES`
and the output name, check `min_clearance_m` > track width + 1 m (otherwise sections merge), then pass the map name
to `make_f110`. The centerline CSV drives progress, lap counting, opponents and the shield's map walls.

## Running experiments

- Long runs: add a line to a queue script (`scripts/queue_lane_*.sh`) or start
  `python -m racing.train ... --out runs/<name>` yourself. Each run writes `run_info.json` with the git commit; commit
  code before starting so the run is reproducible.
- `scripts/autosync.sh` refreshes `RUNS.md` and the training curves and pushes every 20 min while runs are going.
- After a run: `python -m racing.evaluate ...`, then `python -m scripts.analyze <all eval json files>`.
- Videos: `python -m racing.render --controller <name> --model <zip> --out <file.mp4>`.

## Pitfalls we hit (details in PROGRESS.md)

- Changing `racing/*.py` while a training run is going: SubprocVecEnv workers re-import the code when each curriculum
  stage starts. Behaviour-changing edits must be opt-in (new config flag, old default).
- Never edit a queue or loop script (`scripts/queue_*.sh`, `autosync.sh`, `eval_daemon.sh`) while it is running:
  bash reads scripts incrementally and dies or misbehaves. Stop it, edit, restart, or start a new script.
- The F1TENTH lap counter and `done` flag are unreliable on this map; use `info["progress"]`.
- Controllers tuned at 100 Hz can be unstable at the 25 Hz control rate.
- Do not judge a shield by intervention count alone; check collisions in the stress test and on race day.
- Evaluation labels: give every variant its own controller label, otherwise results get pooled.
- Memory: each training run with 7 envs uses about 2.5 GB; evaluation pools about 0.3 GB per process.
