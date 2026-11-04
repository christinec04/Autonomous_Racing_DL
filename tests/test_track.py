import numpy as np
from racing.sim import Centerline


def test_centerline_closed_and_length():
    cl = Centerline.load()
    assert 190 < cl.length < 210
    assert np.linalg.norm(cl.xy[0] - cl.xy[-1]) < 0.2  # loop closes


def test_project_roundtrip():
    cl = Centerline.load()
    for s in [5.0, 50.0, 120.0, 190.0]:
        for d in [-0.8, 0.0, 0.6]:
            x, y, _ = cl.pose_at(s, d)
            _, s2, d2, _ = cl.project(x, y)
            assert abs(((s2 - s + cl.length / 2) % cl.length) - cl.length / 2) < 0.15
            assert abs(d2 - d) < 0.05
