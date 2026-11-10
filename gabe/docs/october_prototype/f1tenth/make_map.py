"""Export the 2.1 km circuit as an f1tenth map, full scale, 0.2 m per pixel.

Writes maps/GrandCircuit/GrandCircuit.png and .yaml plus the centerline csv in the gym's format
(x, y, width right, width left) and a raceline csv (s; x; y; psi; kappa; vx; ax).
Free space is every pixel within HALF of the centerline, so the barrier sits where Webots has it.
"""
import os

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

import bridge
from track import HALF, resample

RES = 0.2
PAD = 20.0
NAME = "GrandCircuit"
OUT = os.path.join(bridge.HERE, "maps", NAME)


def main():
    t = bridge.make_track()
    os.makedirs(OUT, exist_ok=True)
    lo = t.center.min(axis=0) - PAD - HALF
    hi = t.center.max(axis=0) + PAD + HALF
    w, h = (np.ceil((hi - lo) / RES)).astype(int)
    dense = resample(t.center, 0.05)
    tree = cKDTree(dense)
    xs = lo[0] + (np.arange(w) + 0.5) * RES
    img = np.zeros((h, w), np.uint8)
    for r in range(h):
        y = lo[1] + (r + 0.5) * RES
        d, _ = tree.query(np.stack([xs, np.full(w, y)], axis=1), distance_upper_bound=HALF + 1)
        img[r] = np.where(d <= HALF, 255, 0)
    # image row 0 is the top, the gym flips it so row 0 becomes y = origin
    Image.fromarray(img[::-1]).save(os.path.join(OUT, NAME + ".png"))
    with open(os.path.join(OUT, NAME + ".yaml"), "w") as fh:
        fh.write(f"image: {NAME}.png\nresolution: {RES}\norigin: [{lo[0]:.3f}, {lo[1]:.3f}, 0.0]\n"
                 "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
    c = t.center
    np.savetxt(os.path.join(OUT, NAME + "_centerline.csv"),
               np.column_stack([c, np.full(t.n, HALF), np.full(t.n, HALF)]), delimiter=",", fmt="%.4f",
               header="x_m,y_m,w_tr_right_m,w_tr_left_m", comments="# ")
    line = t.line
    d = np.roll(line, -1, axis=0) - np.roll(line, 1, axis=0)
    psi = np.arctan2(d[:, 1], d[:, 0])
    s = np.arange(t.n) * t.ds
    ax = np.gradient(t.v ** 2 / 2, t.ds)
    np.savetxt(os.path.join(OUT, NAME + "_raceline.csv"),
               np.column_stack([s, line, psi, t.kappa, t.v, ax]), delimiter=";", fmt="%.5f",
               header="s_m; x_m; y_m; psi_rad; kappa_radpm; vx_mps; ax_mps2", comments="# ")
    lap = float(np.sum(t.ds / t.v))
    print(f"map {w} x {h} px at {RES} m/px, origin {lo.round(2)}, ideal lap without downforce {lap:.1f} s, "
          f"v {t.v.min():.1f}..{t.v.max():.1f} m/s")


if __name__ == "__main__":
    main()
