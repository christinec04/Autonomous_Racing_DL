"""Where on the track does the shield intervene? Runs a few races with the shielded policy and maps lambda > 0."""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from racing.render import record
from racing.sim import MAPS_DIR

INK, MUTED, SURF = "#0b0b0b", "#52514e", "#fcfcfb"


def main(model="runs/ppo_shield_s0/model_stage3.zip", out="results/shield_map.png", seeds=(10000, 10001, 10002, 10003)):
    pts, lams, fbs = [], [], []
    for s in seeds:
        env, fr = record("ppo_apf", model, s, 140.0)
        for f in fr:
            pts.append(f["poses"][0, :2]); lams.append(f["lam"])
    pts, lams = np.array(pts), np.array(lams)
    spec = (MAPS_DIR / "Singapore" / "Singapore_map.yaml").read_text().splitlines()
    res = float([l for l in spec if l.startswith("resolution")][0].split(":")[1])
    ox, oy = [float(v) for v in [l for l in spec if l.startswith("origin")][0].split("[")[1].split(",")[:2]]
    img = np.array(Image.open(MAPS_DIR / "Singapore" / "Singapore_map.png"))
    h, w = img.shape
    fig, ax = plt.subplots(figsize=(10, 6.4), facecolor=SURF)
    ax.imshow(np.where(img > 128, 238, 60), cmap="gray", vmin=0, vmax=255, extent=[ox, ox + w * res, oy, oy + h * res])
    on = lams > 0
    ax.scatter(pts[~on, 0], pts[~on, 1], s=1, color="#2a78d6", alpha=0.08, linewidths=0, label="policy in control")
    sc = ax.scatter(pts[on, 0], pts[on, 1], s=10, c=lams[on], cmap="Reds", vmin=0, vmax=1, linewidths=0,
                    label="shield intervening")
    cb = fig.colorbar(sc, ax=ax, shrink=0.6); cb.set_label("lambda (intervention strength)", color=MUTED)
    ax.set_xticks([]); ax.set_yticks([])
    for s_ in ax.spines.values(): s_.set_visible(False)
    ax.set_title(f"Where the shield intervenes: {len(seeds)} races, {on.mean():.1%} of steps", color=INK, loc="left")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.01), ncol=2, frameon=False, fontsize=9, markerscale=4)
    fig.tight_layout(); fig.savefig(out, dpi=130, facecolor=SURF)
    print("wrote", out, f"intervention rate {on.mean():.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
