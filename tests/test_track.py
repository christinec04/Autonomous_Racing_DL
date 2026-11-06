import numpy as np
from PIL import Image

from racing.env import EnvConfig, RaceEnv
from racing.sim import MAPS_DIR, Centerline


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


def test_track2_loads_closed_and_width():
    """Track2 (unseen generalisation track): loads, closes, 2.8 m wide, and the env can run on it."""
    cl = Centerline.load("Track2")
    assert 150 < cl.length < 250
    assert np.linalg.norm(cl.xy[0] - cl.xy[-1]) < 0.2
    a = np.loadtxt(MAPS_DIR / "Track2" / "Track2_centerline.csv", delimiter=",")
    assert np.allclose(a[:, 2] + a[:, 3], 2.8)
    # free-space width in the occupancy map, measured across a straight (centreline point s = 20 m, heading +x)
    spec = (MAPS_DIR / "Track2" / "Track2_map.yaml").read_text()
    ox, oy = [float(v) for v in spec.split("origin: [")[1].split(",")[:2]]
    img = np.array(Image.open(MAPS_DIR / "Track2" / "Track2_map.png"))
    x, y, _ = cl.pose_at(20.0)
    col = int((x - ox) / 0.05)
    rows_free = np.nonzero(img[:, col] > 128)[0]
    ys = oy + (img.shape[0] - 1 - rows_free) * 0.05
    near = ys[np.abs(ys - y) < 3.0]
    assert abs((near.max() - near.min() + 0.05) - 2.8) < 0.15
    env = RaceEnv(EnvConfig(n_opp=1, map_name="Track2", episode_time=1.0))
    obs, _ = env.reset(seed=0)
    assert env.cl.length == cl.length and np.isfinite(obs).all()
