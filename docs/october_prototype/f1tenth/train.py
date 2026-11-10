"""PPO on f1tenth_gym with the unchanged racelib env (obs, action, reward) and race_ego/rl.py (PPO, logging).

  python train.py mode=train run=stp_friction shield=friction model=stp minutes=30 steps=600000 opp_after=300000 threads=2
  python train.py mode=eval run=stp_friction shield=friction model=stp opponents=3 episodes=10 tag=eval_opp3
Results in runs/f1tenth/rl/<run>. Without opponents a one car gym is stepped, with opponents a four car gym,
so the solo phase does not pay for three parked cars.
"""
import os
import sys

import bridge
from env import RaceEnv
from f1t_backend import F1tBackend

sys.path.insert(0, os.path.join(bridge.HERE, "..", "controllers", "race_ego"))
import rl  # noqa: E402


class F1tEnv(RaceEnv):
    def __init__(self, track, model, shield, seed=0, max_steps=2500):
        self.model_kind, self.seed0 = model, seed
        self.solo = F1tBackend(track, n_cars=1, dt=0.008, substeps=4, seed=seed, model=model)
        self.multi = None
        super().__init__(self.solo, track, shield=shield, max_steps=max_steps, seed=seed)

    def set_opponents(self, k):
        super().set_opponents(k)
        if k and self.multi is None:
            self.multi = F1tBackend(self.track, n_cars=4, dt=0.008, substeps=4, seed=self.seed0, model=self.model_kind)
        self.b = self.multi if k else self.solo


def main():
    args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    track = bridge.make_track()
    env = F1tEnv(track, args.get("model", "stp"), args.get("shield", "none"), seed=int(args.get("seed", 0)),
                 max_steps=int(args.get("max_steps", 2500)))
    rl.run(args, env, os.path.abspath(os.path.join(bridge.HERE, "..", "runs", "f1tenth", "rl", args.get("run", "f1t"))))


if __name__ == "__main__":
    main()
