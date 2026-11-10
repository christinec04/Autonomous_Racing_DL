"""The car for f1tenth_gym and the racelib constants that have to match it.

Base is the gym's full size parameter set (CommonRoad vehicle 1, a Ford Escort). As shipped it is a
road car, CoG 0.56 m high, 63 % of the weight and 76 % of the braking on the front axle. With race tyres
(mu 1.6) it spins under any braking the pilot asks for, the rear axle unloads to a third of its static
load. So the chassis numbers are replaced by the ones of protos/RaceCar.proto and sim_backend.py
  860 kg, Iz 1100, wheelbase 3.0 m with the CoG in the middle, CoG 0.30 m high, 1.8 x 4.4 m body
  peak tyre friction 1.6 in both directions, rear wheel drive, 65 % front brake bias
  450 kW through the gym's power limit a_max v_switch / v, steering lock 0.45 rad, rack 2 rad/s
The gym has no aerodynamics. Drag is folded into the acceleration command by the backend,
downforce is not possible without editing the vendored dynamics, so the planner's grip is MU g at every speed.
"""
from f1tenth_gym.envs.f110_env import F110Env

MU = 1.6
P_MAX = 450e3
STEER_MAX = 0.45
STEER_RATE = 2.0
A_MAX = 25.0        # gym symmetric accel bound, high enough that the brakes can lock the wheels


def params():
    p = F110Env.fullscale_vehicle_params()
    m = 860.0
    p.update({
        "m": m, "I": 1100.0, "lf": 1.5, "lr": 1.5, "h": 0.30, "width": 1.8, "length": 4.4,
        "mu": MU, "tire_p_dx1": MU, "tire_p_dy1": MU,
        "s_min": -STEER_MAX, "s_max": STEER_MAX, "sv_min": -STEER_RATE, "sv_max": STEER_RATE,
        "a_max": A_MAX, "v_switch": P_MAX / (m * A_MAX), "v_min": 0.0, "v_max": 85.0,
        "T_se": 0.0, "T_sb": 0.65,
    })
    return p


P = params()
MASS = P["m"]
WHEELBASE = P["lf"] + P["lr"]
LR = P["lr"]
