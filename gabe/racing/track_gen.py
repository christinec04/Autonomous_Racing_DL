"""Builds the race tracks, the Singapore-inspired street circuit and Track2.

Marina Bay is a tight street circuit with many 90 degree corners, a chicane after the main straight,
one long back straight and a slow hairpin. Our track keeps that character, scaled for a 1/10 car.
Track2 is a second track with long straights, a fast sweeper and a tight hairpin, used only to test
how well a policy generalises.

Each track is written to maps/<name>/ as an occupancy grid for F1TENTH Gym (<name>_map.png and
<name>_map.yaml) and a centerline (<name>_centerline.csv with x, y, w_left, w_right).

  python -m racing.track_gen            builds all tracks
  python -m racing.track_gen Track2     builds one track
"""
from __future__ import annotations

import pathlib

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

TRACK_WIDTH = 2.8      # m, wide enough for two cars side by side
RESOLUTION = 0.05      # m / pixel
CORNER_RADIUS = 3.0    # m, default fillet radius
MARGIN = 3.0           # m around the track

# corner points, counter-clockwise, as (x, y, corner radius or None for the default)
VERTICES = [
    (0.0, 0.0, None),    # start / finish straight (pit straight)
    (34.0, 0.0, 2.2),    # T1  left  (chicane entry)
    (37.0, 3.0, 2.0),    # T2  right
    (41.0, 3.0, 2.2),    # T3  left
    (46.0, 1.0, 3.5),    # T4/T5 sweep
    (54.0, 1.0, 4.0),
    (58.0, 6.0, 5.0),    # T5  long left onto back straight
    (58.0, 30.0, 2.5),   # T7  90 left (end of back straight)
    (46.0, 30.0, 2.5),   # T8  90 right
    (46.0, 36.0, 2.5),   # T9  90 left
    (34.0, 36.0, 2.5),   # T10 90 left (Singapore Sling area)
    (34.0, 24.0, 2.5),   # T11 90 right
    (24.0, 24.0, 2.5),   # T12 90 right
    (24.0, 34.0, 1.6),   # T13 hairpin (left, tight)
    (18.0, 34.0, 1.6),
    (18.0, 16.0, 3.0),   # T14 left
    (6.0, 10.0, 3.0),    # T16 bay section
    (-4.0, 10.0, 2.5),   # T17/18 left
    (-6.0, 4.0, 3.0),    # T19 left onto main straight
]

# Track2, counter-clockwise, with a 55 m main straight, a fast left sweeper, 90 deg corners, a tight hairpin
# and a 30 m back straight
VERTICES_TRACK2 = [
    (0.0, 0.0, None),    # start / finish straight
    (60.0, 0.0, 10.0),   # T1 fast sweeper, first half (left)
    (70.0, 10.0, 10.0),  # T2 fast sweeper, second half (left)
    (70.0, 30.0, 3.0),   # T3 90 left
    (56.0, 30.0, 3.0),   # T4 90 left
    (56.0, 18.0, 2.5),   # T5 hairpin (right, tight)
    (50.0, 18.0, 2.5),   # T6 hairpin exit (right)
    (50.0, 40.0, 3.5),   # T7 90 left onto the back straight
    (18.0, 40.0, 6.0),   # T8 medium left
    (4.0, 30.0, 5.0),    # T9 left kink
    (-10.0, 3.0, 4.0),   # T10 left onto the main straight
]

TRACKS = {"Singapore": VERTICES, "Track2": VERTICES_TRACK2}


def _fillet_polyline(verts: list[tuple[float, float, float | None]], ds: float = 0.1) -> np.ndarray:
    pts = np.array([[v[0], v[1]] for v in verts])
    radii = [v[2] if v[2] is not None else CORNER_RADIUS for v in verts]
    n = len(pts)
    out = []
    for i in range(n):
        p_prev, p, p_next = pts[i - 1], pts[i], pts[(i + 1) % n]
        a = p_prev - p
        b = p_next - p
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        ua, ub = a / la, b / lb
        theta = np.arccos(np.clip(np.dot(ua, ub), -1, 1))  # angle inside the corner
        r = radii[i]
        t = r / np.tan(theta / 2)  # distance from the corner point to where the arc starts
        t = min(t, 0.45 * la, 0.45 * lb)
        r = t * np.tan(theta / 2)
        start = p + ua * t
        end = p + ub * t
        bis = ua + ub
        bis /= np.linalg.norm(bis)
        center = p + bis * (r / np.sin(theta / 2))
        a0 = np.arctan2(*(start - center)[::-1])
        a1 = np.arctan2(*(end - center)[::-1])
        da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
        m = max(2, int(abs(da) * r / ds))
        angs = a0 + da * np.linspace(0, 1, m)
        out.append(np.stack([center[0] + r * np.cos(angs), center[1] + r * np.sin(angs)], 1))
    # join arcs with straight segments, then resample uniformly
    poly = np.concatenate(out + [out[0][:1]])
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    s_new = np.arange(0, s[-1], ds)
    return np.stack([np.interp(s_new, s, poly[:, 0]), np.interp(s_new, s, poly[:, 1])], 1)


def build(out_dir: pathlib.Path, name: str = "Singapore", vertices: list | None = None) -> dict:
    vertices = VERTICES if vertices is None else vertices
    center = _fillet_polyline(vertices)
    xmin, ymin = center.min(0) - TRACK_WIDTH / 2 - MARGIN
    xmax, ymax = center.max(0) + TRACK_WIDTH / 2 + MARGIN
    w = int(np.ceil((xmax - xmin) / RESOLUTION))
    h = int(np.ceil((ymax - ymin) / RESOLUTION))

    # draw the centerline, then mark everything within half the track width of it as free
    mask = np.ones((h, w), dtype=bool)
    dense = _fillet_polyline(vertices, ds=RESOLUTION / 2)
    cols = ((dense[:, 0] - xmin) / RESOLUTION).astype(int)
    rows = ((dense[:, 1] - ymin) / RESOLUTION).astype(int)
    mask[rows, cols] = False
    dist = distance_transform_edt(mask) * RESOLUTION
    free = dist <= TRACK_WIDTH / 2
    img = np.where(free, 255, 0).astype(np.uint8)
    # image row 0 is the top of the map, so flip vertically
    img = img[::-1]

    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(out_dir / f"{name}_map.png")
    # write LF line endings on every OS (the committed maps were generated with LF)
    (out_dir / f"{name}_map.yaml").write_bytes((
        f"image: {name}_map.png\n"
        f"resolution: {RESOLUTION}\n"
        f"origin: [{xmin:.4f}, {ymin:.4f}, 0.0]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n"
    ).encode())
    wl = np.full(len(center), TRACK_WIDTH / 2)
    with open(out_dir / f"{name}_centerline.csv", "wb") as f:
        np.savetxt(f, np.column_stack([center, wl, wl]), delimiter=",", fmt="%.4f",
                   header="x_m, y_m, w_tr_left_m, w_tr_right_m")

    # check that distant parts of the track do not touch
    seg_len = 0.1
    idx = np.arange(len(center))
    d = np.linalg.norm(center[:, None] - center[None], axis=-1)
    gap = np.abs(idx[:, None] - idx[None])
    gap = np.minimum(gap, len(center) - gap) * seg_len
    min_clear = d[gap > 3 * TRACK_WIDTH].min()
    return {"length_m": len(center) * seg_len, "min_clearance_m": float(min_clear),
            "image_px": (w, h)}


if __name__ == "__main__":
    import sys
    root = pathlib.Path(__file__).resolve().parents[1]
    for name in sys.argv[1:] or list(TRACKS):
        print(name, build(root / "maps" / name, name, TRACKS[name]))
