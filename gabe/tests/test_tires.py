"""The friction-circle tyre model must equal stock F1TENTH below the grip limit and cap force above it."""
import numpy as np
from f1tenth_gym.envs.dynamic_models import vehicle_dynamics_st as stock
from racing.tires import vehicle_dynamics_st_sat as sat
from racing.sim import DEFAULT_PARAMS as P

ARGS = [P[k] for k in ("mu", "C_Sf", "C_Sr", "lf", "lr", "h", "m", "I", "s_min", "s_max",
                       "sv_min", "sv_max", "v_switch", "a_max", "v_min", "v_max")]


def test_identical_below_limit():
    rng = np.random.default_rng(0)
    for _ in range(200):
        x = np.array([0, 0, rng.uniform(-0.03, 0.03), rng.uniform(2, 10), 0, rng.uniform(-0.3, 0.3), rng.uniform(-0.02, 0.02)])
        u = np.array([rng.uniform(-1, 1), rng.uniform(-2, 2)])
        np.testing.assert_allclose(sat(x, u, *ARGS), stock(x, u, *ARGS), rtol=1e-6, atol=1e-8)


def test_caps_lateral_force_above_limit():
    # big steer at speed: stock model gives yaw acceleration far beyond what friction allows
    x = np.array([0, 0, 0.4, 10.0, 0, 0, 0])
    u = np.array([0.0, 0.0])
    assert abs(sat(x, u, *ARGS)[5]) < abs(stock(x, u, *ARGS)[5])
    # lateral acceleration implied by the saturated model stays within mu*g
    f = sat(x, u, *ARGS)
    a_lat = x[3] * (f[6] + x[5])  # v * (beta_dot + yaw_rate)
    assert abs(a_lat) <= P["mu"] * 9.81 * 1.001
