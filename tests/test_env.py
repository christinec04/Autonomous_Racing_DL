import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig
from racing.evaluate import OvertakeTracker


def test_obs_shape_and_progress_reward():
    env = RaceEnv(EnvConfig(n_opp=3, shield=ShieldConfig(mode="off")))
    obs, _ = env.reset(seed=1)
    assert obs.shape == env.observation_space.shape
    R = 0
    for _ in range(25):
        obs, r, term, trunc, info = env.step(np.array([0.0, -0.6]))
        R += r
    assert info["progress"] > 1.0 and R > 0


def test_action_mapping_roundtrip():
    env = RaceEnv(EnvConfig(n_opp=0))
    for a in [np.array([0.3, -0.2]), np.array([-1.0, 1.0])]:
        np.testing.assert_allclose(env.to_normalized(env.to_physical(a)), a, atol=1e-9)


def test_overtake_tracker_counts_clean_pass():
    ot = OvertakeTracker(1)
    L = 200.0
    t = 0.0
    # behind by 2.5 m, faster, then move 0.5 m sideways, pass and hold for > 2 s
    for k in range(200):
        t = k * 0.04
        gap = -2.5 + k * 0.05
        lat = min(0.6, k * 0.02)
        ot.update(t, 100 + gap, lat, 8.0, [100.0], [0.0], [6.0], False, L)
    assert ot.attempts == 1 and ot.successes == 1
