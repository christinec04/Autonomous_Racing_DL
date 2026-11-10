# October 2026 Webots prototype (archive)

A snapshot of the pre-repo prototype from Oct 15-16, copied on 2026-11-10 from `~/robotics/racing_proposal` so the
background stays with the project. It is a record, not working code for this repo: nothing here is imported or
run by `racing/`, and paths inside the scripts point at the original folder. The story behind it, what it showed
and why the project moved to F1TENTH Gym is in [../background.md](../background.md).

| folder | what |
|---|---|
| `CONTRACT.md` | the plan the October build followed: the two questions from the professor and how each would be answered |
| `worlds/`, `protos/` | Webots worlds (race track, demo, physics probe, trap) and the car/track PROTOs |
| `controllers/` | Webots controllers: ego with the shields (`race_ego`, `ego_shielded_ppo`), PID opponents, probes, supervisors; `racelib/` holds the shared APF and friction-aware shield code |
| `tools/` | world generators, capture and plotting scripts |
| `runs/` | results: physics probe, road-vs-race shield sweep (`shield_test`), offline RL, F1TENTH port |
| `f1tenth/` | the Oct 16 F1TENTH Gym port (full-size car, Pacejka tyres) and its maps |
| `screenshots/` | Webots screenshots of the race world (chase, overhead, close-up, full track) |

Left out to keep the repo small: the Webots log, rendered frame folders (`shots/`, `hamster_*`, `trap_*`), model
checkpoints and anything over 2 MB. They are still in the original folder.
