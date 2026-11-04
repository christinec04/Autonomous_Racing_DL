"""The shield's predictor must reproduce the simulator (same model), so its clearance must match reality."""
import numpy as np
import pytest
from racing.sim import make_f110, set_scan_flags, DEFAULT_PARAMS as P
from racing.tires import set_tire_model, set_traction_control
from racing.predict import rollout_clearance
from racing.shield import CIRC_OFF, CIRC_R, WB

PARR = np.array([P[k] for k in ("mu", "C_Sf", "C_Sr", "lf", "lr", "h", "m", "I", "s_min", "s_max",
                                "sv_min", "sv_max", "v_switch", "a_max", "v_min", "v_max")], float)


@pytest.mark.parametrize("tire", ["saturated", "saturated_v2", "linear"])
@pytest.mark.parametrize("cmd", [(0.0, 8.0), (0.15, 6.0), (-0.3, 3.0), (0.25, 0.0)])
def test_predicted_clearance_matches_sim(tire, cmd):
    set_tire_model(tire); set_traction_control(True)
    env = make_f110(1)
    env.reset(options={"poses": np.array([[0.0, 0.0, 0.0]])})
    a = env.unwrapped.sim.agents[0]
    a.state[:] = 0; a.state[0] = 30.0; a.state[3] = 6.0
    a.steer_buffer = np.empty((0,))
    x0 = a.state.copy()
    pt = np.array([[33.0, 1.5]])  # an obstacle point the car passes near
    steps = 100
    # simulator, exact same commands
    clear_sim = 1e9
    for t in range(steps):
        a._scan_now = False; a._rays_now = False
        env.unwrapped.sim.step(np.array([cmd]))
        if t % 2 == 0:
            c, s = np.cos(a.state[4]), np.sin(a.state[4])
            for off in CIRC_OFF:
                d = np.hypot(a.state[0] + off * c - pt[0, 0], a.state[1] + off * s - pt[0, 1]) - CIRC_R
                clear_sim = min(clear_sim, d)
    pred = rollout_clearance(np.array([cmd], float), x0, np.zeros(2), PARR, {"linear": 0, "saturated": 1, "saturated_v2": 2}[tire], True, 0.95, 0.0,
                             pt, np.zeros((60, 2)), 12, np.zeros((0, 5)), 6.0, steps, steps, 0.01, 2,
                             CIRC_OFF, CIRC_R, WB, 10.0)[0]
    assert abs(pred - clear_sim) < 0.02, (pred, clear_sim)
