import numpy as np
from racing.env import RaceEnv, EnvConfig
from racing.shield import ShieldConfig


def _env(mode, n_opp=0):
    env = RaceEnv(EnvConfig(n_opp=n_opp, shield=ShieldConfig(mode=mode)))
    env.reset(seed=0, options={"s_ego": 3.0})
    return env


def test_off_passes_action_through():
    env = _env("off")
    _, _, _, _, info = env.step(np.array([0.1, -0.5]))
    np.testing.assert_allclose(info["a_final"], info["a_rl"])
    assert info["lambda"] == 0.0


def test_conditioned_does_not_intervene_on_safe_action():
    env = _env("conditioned_fallback")
    lams = [env.step(np.array([0.0, -0.9]))[4]["lambda"] for _ in range(20)]  # slow, straight
    assert max(lams) == 0.0


def test_fallback_prevents_full_throttle_wall_hit():
    """Full throttle, wheel straight, into the first chicane: off crashes, fallback shield does not."""
    out = {}
    for mode in ["off", "conditioned_fallback"]:
        env = _env(mode)
        crashed = False
        for _ in range(200):
            _, _, term, trunc, info = env.step(np.array([0.0, 1.0]))
            if term:
                crashed = True; break
        out[mode] = crashed
    assert out["off"] and not out["conditioned_fallback"]


def _stopped_near_wall(escape, gap=0.12, tol=None):
    """Car at rest about 12 cm (as in a real stuck race) from the right wall on the main straight, policy asks to pull away left."""
    kw = {} if tol is None else {"escape_tol": tol}
    env = RaceEnv(EnvConfig(n_opp=0, shield=ShieldConfig(mode="conditioned_fallback", escape=escape, **kw)))
    env.reset(seed=0, options={"s_ego": 10.0})
    a = env.sim.unwrapped.sim.agents[0]
    x, y, h = env.cl.pose_at(10.0, -1.4 + 0.155 + gap)  # half track width - half car width - gap
    a.state[:] = 0; a.state[0], a.state[1], a.state[4] = x, y, h
    env.step(np.array([0.0, -1.0]))  # refresh the scan at the new pose
    moved = 0.0
    for _ in range(50):
        _, _, term, _, info = env.step(np.array([0.5, -0.6]))  # steer left, ~5 m/s
        moved = info["progress"]
        if term:
            break
    return moved, term


def test_escape_fixes_deadlock_next_to_wall():
    for gap in (0.12, 0.08):  # real stuck races stopped ~12 cm from the wall
        moved_old, _ = _stopped_near_wall(escape=False, gap=gap)
        moved_new, crashed = _stopped_near_wall(escape=True, gap=gap)
        assert moved_old < 0.1  # without the fix: deadlock
        assert moved_new > 2.0 and not crashed
