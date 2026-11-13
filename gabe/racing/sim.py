"""Thin layer over F1TENTH Gym with our tracks, the vehicle parameters and the track geometry."""
from __future__ import annotations

import pathlib

import gymnasium as gym
import numpy as np

import f1tenth_gym.envs.track.track as _track_mod
from f1tenth_gym.envs import base_classes as _bc
from f1tenth_gym.envs.collision_models import get_vertices as _get_vertices
from f1tenth_gym.envs.laser_models import ray_cast as _ray_cast

MAPS_DIR = pathlib.Path(__file__).resolve().parents[1] / "maps"

DEFAULT_PARAMS = {
    "mu": 1.0489, "C_Sf": 4.718, "C_Sr": 5.4562, "lf": 0.15875, "lr": 0.17145,
    "h": 0.074, "m": 3.74, "I": 0.04712, "s_min": -0.4189, "s_max": 0.4189,
    "sv_min": -3.2, "sv_max": 3.2, "v_switch": 7.319, "a_max": 9.51,
    "v_min": -5.0, "v_max": 20.0, "width": 0.31, "length": 0.58,
}
G = 9.81


def _find_track_dir(name: str) -> pathlib.Path:
    d = MAPS_DIR / name
    if not d.exists():
        raise FileNotFoundError(f"map {name} not found in {MAPS_DIR}, run python -m racing.track_gen")
    return d


# load tracks from maps/ instead of downloading them
_track_mod.find_track_dir = _find_track_dir


class Centerline:
    """Closed centerline with projection onto arc length s, lateral offset d and heading."""

    def __init__(self, xy: np.ndarray):
        self.xy = xy
        d = np.diff(np.vstack([xy, xy[:1]]), axis=0)
        self.seg_len = np.linalg.norm(d, axis=1)
        self.s = np.concatenate([[0], np.cumsum(self.seg_len)[:-1]])
        self.length = float(self.seg_len.sum())
        self.heading = np.arctan2(d[:, 1], d[:, 0])
        dh = np.diff(np.concatenate([self.heading, self.heading[:1]]))
        dh = (dh + np.pi) % (2 * np.pi) - np.pi
        self.curvature = dh / self.seg_len

    @classmethod
    def load(cls, name: str = "Singapore") -> "Centerline":
        a = np.loadtxt(MAPS_DIR / name / f"{name}_centerline.csv", delimiter=",")
        return cls(a[:, :2])

    def project(self, x: float, y: float, hint: int | None = None, window: int = 80):
        """Returns (index, s, lateral offset with left positive, heading).

        With a hint, only points near that index are searched.
        """
        n = len(self.xy)
        if hint is None:
            idx = np.arange(n)
        else:
            idx = (hint + np.arange(-window, window + 1)) % n
        p = self.xy[idx]
        i = idx[np.argmin((p[:, 0] - x) ** 2 + (p[:, 1] - y) ** 2)]
        h = self.heading[i]
        dx, dy = x - self.xy[i, 0], y - self.xy[i, 1]
        along = dx * np.cos(h) + dy * np.sin(h)
        lat = -dx * np.sin(h) + dy * np.cos(h)
        return int(i), (self.s[i] + along) % self.length, float(lat), float(h)

    def pose_at(self, s: float, d: float = 0.0) -> np.ndarray:
        s = s % self.length
        i = int(np.searchsorted(self.s, s, side="right") - 1)
        h = self.heading[i]
        x = self.xy[i, 0] + (s - self.s[i]) * np.cos(h) - d * np.sin(h)
        y = self.xy[i, 1] + (s - self.s[i]) * np.sin(h) + d * np.cos(h)
        return np.array([x, y, h])


def make_f110(num_agents: int, timestep: float = 0.01, seed: int = 0, map_name: str = "Singapore"):
    return gym.make(
        "f1tenth_gym:f1tenth-v0",
        config={
            "map": map_name, "num_agents": num_agents, "timestep": timestep,
            "integrator": "rk4", "model": "st",
            "control_input": ["speed", "steering_angle"],
            "observation_config": {"type": "original"},
            "params": dict(DEFAULT_PARAMS), "seed": seed, "reset_config": {"type": "cl_grid_static"},
        },
    )


# Speed patches for F1TENTH Gym that do not change the results.
# 1. A car computes its lidar scan only when flagged. The ego scans on every physics step, because wall
#    collisions are detected from the scan, and the opponents scan once per control step.
# 2. Other cars are ray-cast into a scan only when flagged, and cars behind the lidar or out of range are
#    skipped. The stock code loops over the whole scan for a car behind.
_orig_update_pose = _bc.RaceCar.update_pose


def _update_pose(self, raw_steer, vel):
    if getattr(self, "_scan_now", True):
        return _orig_update_pose(self, raw_steer, vel)
    # the stock update without the scan
    if self.steer_buffer.shape[0] < self.steer_buffer_size:
        steer = 0.0
        self.steer_buffer = np.append(raw_steer, self.steer_buffer)
    else:
        steer = self.steer_buffer[-1]
        self.steer_buffer = self.steer_buffer[:-1]
        self.steer_buffer = np.append(raw_steer, self.steer_buffer)
    accl, sv = self.action_type.act(action=(vel, steer), state=self.state, params=self.params)
    self.state = self.integrator.integrate(f=self.model.f_dynamics, x=self.state,
                                           u=np.array([sv, accl]), dt=self.time_step, params=self.params)
    self.state[4] %= 2 * np.pi
    return None


def _update_scan(self, agent_scans, agent_index):
    if not getattr(self, "_scan_now", True):
        return
    scan = agent_scans[agent_index]
    self.check_ttc(scan)
    if not getattr(self, "_rays_now", True):
        return
    pose = np.append(self.state[0:2], self.state[4])
    for op in self.opp_poses:
        dx, dy = op[0] - pose[0], op[1] - pose[1]
        dist = np.hypot(dx, dy)
        if dist > 30.0:
            continue
        rel = (np.arctan2(dy, dx) - pose[2] + np.pi) % (2 * np.pi) - np.pi
        if dist > 0.8 and abs(rel) > 2.35 + 0.6 / dist:
            continue  # fully behind the 270 deg field of view
        verts = _get_vertices(op, self.params["length"], self.params["width"])
        scan = _ray_cast(pose, scan, self.scan_angles, verts)
    agent_scans[agent_index] = scan


def _sim_step(self, control_inputs):
    for i, agent in enumerate(self.agents):
        cur = agent.update_pose(control_inputs[i, 0], control_inputs[i, 1])
        if cur is not None:
            self.agent_scans[i, :] = cur
        self.agent_poses[i, :] = np.append(agent.state[0:2], agent.state[4])
        self.agent_steerings[i] = agent.state[2]
    self.check_collision()
    for i, agent in enumerate(self.agents):
        agent.update_opp_poses(np.concatenate((self.agent_poses[0:i, :], self.agent_poses[i + 1:, :]), axis=0))
        agent.update_scan(self.agent_scans, i)
        if agent.in_collision:
            self.collisions[i] = 1.0


_bc.RaceCar.update_pose = _update_pose
_bc.RaceCar.update_scan = _update_scan
_bc.Simulator.step = _sim_step


def set_scan_flags(env, last_substep: bool):
    """The ego scans every substep and ray-casts cars on the last one. Opponents do both on the last one."""
    for i, a in enumerate(env.unwrapped.sim.agents):
        a._scan_now = (i == 0) or last_substep
        a._rays_now = (i == 0) and last_substep
