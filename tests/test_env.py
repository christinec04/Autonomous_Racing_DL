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


def test_summary_separates_finished_stuck_crashed():
    from racing.evaluate import summarize
    base = dict(controller="x", seed=0, randomize=False, laps_target=5, overtake_attempts=0, overtake_successes=0,
                shield_freq=0.0, lam_mean=0.0, grip_above_90=0.0, grip_above_100=0.0, slip_above_15=0.0, gg=[[], []])
    races = [
        dict(base, laps_done=5.0, lap_times=[35.0] * 5, wall=False, car=False, dnf=False),   # finished
        dict(base, laps_done=0.6, lap_times=[], wall=False, car=False, dnf=False),           # stuck
        dict(base, laps_done=2.3, lap_times=[35.0, 34.0], wall=True, car=False, dnf=True),   # crashed
    ]
    s = summarize(races)["x"]
    assert (s["finished"], s["stuck"], s["wall"]) == (1, 1, 1)


def test_stall_recovery_reverses_out_of_a_nose_to_wall_stop():
    # a "policy" that crawls and always steers left: drives into the left wall at minimum speed
    sh = ShieldConfig(mode="conditioned_fallback", reach="grip", escape=True, allow_reverse=True)
    env = RaceEnv(EnvConfig(n_opp=0, shield=sh, recover=True, tire="saturated_v2", episode_time=20.0))
    env.reset(seed=0)
    vs, crashed, info = [], False, {}
    for _ in range(500):
        _, _, term, trunc, info = env.step(np.array([1.0, -1.0]))
        vs.append(info["state"][3])
        crashed |= term
        if term or trunc:
            break
    assert not crashed
    assert info["n_recover"] >= 1
    assert min(vs) < -0.1  # it actually reversed
