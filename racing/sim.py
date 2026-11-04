"""Thin layer over F1TENTH Gym: our map, vehicle params, track geometry."""
from __future__ import annotations

import pathlib

import gymnasium as gym
import numpy as np

import f1tenth_gym.envs.track.track as _track_mod

MAPS_DIR = pathlib.Path(__file__).resolve().parents[1] / "maps"


def _find_track_dir(name: str) -> pathlib.Path:
    d = MAPS_DIR / name
    if not d.exists():
        raise FileNotFoundError(f"map {name} not found in {MAPS_DIR}; run python -m racing.track_gen")
    return d


# Point F1TENTH Gym at our local maps instead of downloading.
_track_mod.find_track_dir = _find_track_dir

DEFAULT_PARAMS = {
    "mu": 1.0489, "C_Sf": 4.718, "C_Sr": 5.4562, "lf": 0.15875, "lr": 0.17145,
    "h": 0.074, "m": 3.74, "I": 0.04712, "s_min": -0.4189, "s_max": 0.4189,
    "sv_min": -3.2, "sv_max": 3.2, "v_switch": 7.319, "a_max": 9.51,
    "v_min": -5.0, "v_max": 20.0, "width": 0.31, "length": 0.58,
}
G = 9.81


class Centerline:
    """Closed centerline with arc-length projection (Frenet s, d, heading)."""

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
        """Return (index, s, signed lateral offset d [left +], heading)."""
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


def make_f110(num_agents: int, params: dict | None = None, timestep: float = 0.01, seed: int = 0):
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    return gym.make(
        "f1tenth_gym:f1tenth-v0",
        config={
            "map": "Singapore", "num_agents": num_agents, "timestep": timestep,
            "integrator": "rk4", "model": "st",
            "control_input": ["speed", "steering_angle"],
            "observation_config": {"type": "original"},
            "params": p, "seed": seed, "reset_config": {"type": "cl_grid_static"},
        },
    )
