# Build log (incremental results)

Setup: `python -m venv .venv && pip install -r requirements.txt`, then `python -m racing.track_gen`.

## Step 1: track + classical controllers (solo)
- Singapore-inspired street circuit, 199 m lap, 2.8 m wide, 19 corners (`maps/Singapore`).
- F1TENTH Gym v1.0 dynamic single-track model, default vehicle params, dt = 0.01 s. ~4000 sim steps/s per car.
- `python -m scripts.probe_sim`

| controller | speed scale | result | lap time |
|---|---|---|---|
| Pure Pursuit | 0.85 | clean | 35.2 s |
| Pure Pursuit | 1.00 | clean | 30.1 s |
| Pure Pursuit | 1.10 | clean | 27.9 s (max offset 1.18 m of 1.4 m) |
| PID | 0.85 | clean | 34.6 s |
| PID | 1.00 | crash | - |
