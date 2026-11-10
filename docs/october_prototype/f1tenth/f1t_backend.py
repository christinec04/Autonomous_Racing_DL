"""f1tenth_gym backend that quacks like sim_backend.SimBackend and env.WebotsBackend.

All cars, ego and opponents, are gym agents on the multi body PAC2002 model. The ego takes
(steer, throttle, brake) from the racelib stack, opponents are driven by racelib Pilot.
Pedals become the gym's acceleration input through the same pedal map pilot.long_accel assumes,
minus drag and rolling loss, since the gym has no aerodynamics. Steering becomes a steering rate
with a fast proportional loop on the rack, capped at the rack speed in vehicle.py.
Positions are reported at the rear axle like Webots, the gym integrates the centre of mass.
"""
import math
import os
import pathlib

import numpy as np

import bridge
import vehicle
from pilot import BRAKE_A, Pilot, coast, motor
from track import HALF

import f1tenth_gym.envs.base_classes as bc
from f1tenth_gym.envs.dynamic_models import init_mb
from f1tenth_gym.envs.f110_env import F110Env
from f1tenth_gym.envs.integrator import RK4Integrator
from stp import STPModel
from f1tenth_gym.envs.track import Track as GymTrack
from f1tenth_gym.envs.track.raceline import Raceline

MAP_YAML = os.path.join(bridge.HERE, "maps", "GrandCircuit", "GrandCircuit.yaml")
LIDAR_RAYS, LIDAR_FOV, LIDAR_RANGE = 180, math.pi, 80.0
K_RACK = 40.0        # 1/s, steering angle loop on top of the gym's rate limited rack

# every gym agent scans with our LiDAR layout, the gym default is 1080 beams over 270 deg
_d = list(bc.RaceCar.__init__.__defaults__)
_d[-2:] = [LIDAR_RAYS, LIDAR_FOV]
bc.RaceCar.__init__.__defaults__ = tuple(_d)


def load_gym_track():
    t = GymTrack.from_track_path(pathlib.Path(MAP_YAML))
    d = pathlib.Path(MAP_YAML).parent
    t.centerline = Raceline.from_centerline_file(d / "GrandCircuit_centerline.csv")
    t.raceline = Raceline.from_raceline_file(d / "GrandCircuit_raceline.csv", skip_rows=1)
    return t


class SafeRK4(RK4Integrator):
    """RK4 that refuses a non finite state. The MB slip equations divide by wheel ground speed, which a
    spinning car can drive to zero, and a NaN pose segfaults the numba ray caster. The car is frozen and flagged."""

    def __init__(self):
        super().__init__()
        self.blown = False

    def integrate(self, f, x, u, dt, params):
        with np.errstate(all="ignore"):
            out = super().integrate(f, x, u, dt, params)
        if np.all(np.isfinite(out)) and abs(out[3]) < 150:
            return out
        self.blown = True
        x = x.copy()
        x[3:] = 0.0
        if len(x) == 29:
            x[11:23] = init_mb(np.array([x[0], x[1], 0.0, 0.0, x[4], 0.0, 0.0]), params)[11:23]
        return x


class Body:
    """Ground truth state with the attribute names of car.Car."""

    def __init__(self):
        self.x = self.y = self.yaw = 0.0
        self.vx = self.vy = self.yaw_rate = self.speed = 0.0
        self.ax = self.ay = 0.0
        self.up_z = 1.0


class F1tBackend:
    def __init__(self, track, n_cars=4, dt=0.004, substeps=8, seed=0, model="stp"):
        """dt is the gym physics step, one control period is substeps of it (32 ms by default like env.py).
        model is st (the gym's linear tyre single track), stp (stp.py, saturating tyres) or mb (gym multi body)."""
        self.track = track
        self.model = model
        self.dt = dt
        self.substeps = substeps
        self.n = n_cars
        self.env = F110Env(config={
            "map": load_gym_track(), "params": vehicle.P, "num_agents": n_cars, "timestep": dt,
            "integrator": "rk4", "model": "mb" if model == "mb" else "st", "control_input": ["accl", "steering_speed"],
            "observation_config": {"type": "kinematic_state"}, "reset_config": {"type": "rl_grid_static"},
            "seed": seed})
        self.sim = self.env.sim
        for a in self.sim.agents:
            a.scan_simulator.max_range = LIDAR_RANGE
            a.integrator = SafeRK4()
            if model == "stp":
                a.model = STPModel(a.model)
        self.ego = Body()
        self.cmd = (0.0, 0.0, 0.0)
        self.active = 0
        self.pilots = []
        self.t = 0.0
        self.collided = np.zeros(n_cars, bool)
        self.opp_cmd = [None] * n_cars

    # state

    def _read(self, k, body=None):
        x = self.sim.agents[k].state
        yaw = (x[4] + math.pi) % (2 * math.pi) - math.pi
        c, s = math.cos(yaw), math.sin(yaw)
        b = body or Body()
        b.x, b.y, b.yaw = x[0] - vehicle.LR * c, x[1] - vehicle.LR * s, yaw
        if self.model == "mb":
            b.vx, b.vy = float(x[3]), float(x[10])
        else:
            b.vx, b.vy = float(x[3] * math.cos(x[6])), float(x[3] * math.sin(x[6]))
        b.yaw_rate = float(x[5])
        b.speed = math.hypot(b.vx, b.vy)
        return b

    def _place(self, k, x, y, yaw, v):
        """Car k with its rear axle at x, y, rolling straight at v."""
        cx, cy = x + vehicle.LR * math.cos(yaw), y + vehicle.LR * math.sin(yaw)
        x0 = np.array([cx, cy, 0.0, v, yaw, 0.0, 0.0])
        self.sim.agents[k].state = init_mb(x0, vehicle.P) if self.model == "mb" else x0
        self.sim.agents[k].steer_buffer = np.empty((0,))

    def reset(self, ego, opps, opp_aggression=1.0):
        """ego is (x, y, yaw, speed), opps a list of (s, lat, pace), at most n_cars minus one."""
        far = np.array([[-60.0 + 30 * k, 0.0, 0.0] for k in range(self.n)])
        self.env.reset(options={"poses": far})
        x, y, yaw, v = ego
        self._place(0, x, y, yaw, v)
        self.active = len(opps)
        self.pilots = []
        for k, (s, lat, pace) in enumerate(opps, start=1):
            ox, oy, oyaw = self.track.pose(s, lat)
            self._place(k, ox, oy, oyaw, pace * self.track.v[self.track.at(s)] * 0.9)
            self.pilots.append(Pilot(self.track, pace, 1.0))
        for k in range(len(opps) + 1, self.n):
            self._place(k, -60.0 + 30 * k, 0.0, 0.0, 0.0)   # parked in the infield
        for key in [key for key in self.track._last if str(key).startswith("f1t")]:
            self.track._last.pop(key)
        self.cmd = (0.0, 0.0, 0.0)
        self.collided[:] = False
        for a in self.sim.agents:
            a.integrator.blown = False
        self.t = 0.0
        self._read(0, self.ego)

    def place_all(self, ego, opps, opp_paces):
        """Explicit starts, ego and opps as (x, y, yaw, speed) with the rear axle at x, y."""
        far = np.array([[-60.0 + 30 * k, 0.0, 0.0] for k in range(self.n)])
        self.env.reset(options={"poses": far})
        self._place(0, *ego)
        self.active = len(opps)
        self.pilots = [Pilot(self.track, pace, 1.0) for pace in opp_paces]
        for k, o in enumerate(opps, start=1):
            self._place(k, *o)
        for k in range(len(opps) + 1, self.n):
            self._place(k, -60.0 + 30 * k, 0.0, 0.0, 0.0)
        for key in [key for key in self.track._last if str(key).startswith("f1t")]:
            self.track._last.pop(key)
        self.cmd = (0.0, 0.0, 0.0)
        self.collided[:] = False
        for a in self.sim.agents:
            a.integrator.blown = False
        self.t = 0.0
        self._read(0, self.ego)

    def command(self, steer, throttle, brake):
        self.cmd = (max(-1.0, min(1.0, steer)), max(0.0, min(1.0, throttle)), max(0.0, min(1.0, brake)))

    def _accel(self, v, throttle, brake):
        return throttle * motor(v) - BRAKE_A * brake - coast(v)

    def _opp_states(self):
        out = []
        for k in range(1, self.active + 1):
            b = self._read(k)
            i, s, lat = self.track.project(b.x, b.y, f"f1t{k}")
            out.append({"x": b.x, "y": b.y, "yaw": b.yaw, "vx": b.vx, "vy": b.vy, "speed": b.speed,
                        "i": i, "s": s, "lat": lat})
        return out

    def step(self):
        """One control period. Opponent pilots act once per period on the same clock as the ego."""
        T = self.substeps * self.dt
        states = self._opp_states()
        e = self.ego
        i, s, lat = self.track.project(e.x, e.y, "f1t0")
        everyone = [{"x": e.x, "y": e.y, "yaw": e.yaw, "speed": e.speed, "s": s, "lat": lat}] + states
        cmds = [self.cmd]
        for k, st in enumerate(states):
            others = [o for j, o in enumerate(everyone) if j != k + 1]
            cmds.append(self.pilots[k].act(st, others, T))
        vx0, vy0 = e.vx, e.vy
        u = np.zeros((self.n, 2))
        for _ in range(self.substeps):
            for k in range(self.active + 1):
                a = self.sim.agents[k].state
                steer, throttle, brake = cmds[k]
                u[k, 0] = max(-vehicle.STEER_RATE, min(vehicle.STEER_RATE, K_RACK * (vehicle.STEER_MAX * steer - a[2])))
                u[k, 1] = self._accel(max(a[3], 0.0), throttle, brake)
            self.sim.step(u)
            self.collided |= self.sim.collisions.astype(bool)
        self.t += T
        self._read(0, e)
        e.ax, e.ay = (e.vx - vx0) / T, (e.vy - vy0) / T
        return True

    def time(self):
        return self.t

    def opponents(self):
        return [{"x": b.x, "y": b.y, "yaw": b.yaw, "speed": b.speed}
                for b in (self._read(k) for k in range(1, self.active + 1))]

    def opp_states(self):
        return self._opp_states()

    def lidar(self):
        return np.minimum(self.sim.agent_scans[0], LIDAR_RANGE)

    def blown(self, k=0):
        return self.sim.agents[k].integrator.blown

    def contact(self):
        """Barrier from the gym's iTTC wall check, cars are checked by env.py and the sweep with the box test."""
        a = self.sim.agents[0]
        if a.integrator.blown:
            return "spin"
        if a.in_collision:
            return "barrier"
        if abs(self.track.project(self.ego.x, self.ego.y, "f1t0")[2]) > HALF + 1.0:
            return "barrier"
        return ""
