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
