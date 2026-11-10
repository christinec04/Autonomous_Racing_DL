"""Plot runs/probe/summary.csv into g-g, skidpad, accel and brake figures."""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "controllers", "racelib"))
from track import G, MU, drive_accel, grip  # noqa: E402

RUN = os.path.join(HERE, "..", "runs", "probe")


def load(name):
    path = os.path.join(RUN, name + ".csv")
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            d = out.setdefault(r["test"], {})
            for k, v in r.items():
                if k != "test" and v != "":
                    d.setdefault(k, []).append(float(v))
    return {t: {k: np.array(v) for k, v in d.items()} for t, d in out.items()}


def smooth(a, n=13):
    return np.convolve(a, np.ones(n) / n, "same") if len(a) > n else a


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(RUN, name), dpi=130)
    plt.close(fig)
    print("wrote", name)


def gg(d, summ):
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    tags = [("accel", "tab:green"), ("brake60", "tab:red"), ("brake70", "tab:pink"),
            ("skid_r100", "tab:blue"), ("skid_r25", "tab:cyan")]
    tags += [(t, "tab:purple") for t in d if t.startswith("combined")]
    for tag, col in tags:
        if tag not in d:
            continue
        r = d[tag]
        lat = r["ay_ss"] if "ay_ss" in r else smooth(r["ay"])
        lat = smooth(r["ay"], 25)
        ax.scatter(lat / G, smooth(r["ax"], 25) / G, s=2, color=col, alpha=0.4,
                   label="combined, steer then brake" if tag == "combined_b5" else None if tag.startswith("combined") else tag)
    for k, s in summ.items():
        if k.startswith("combined"):
            ax.plot(abs(s["ay"]) / G, s["ax"] / G, "o", color="k", ms=4)
    th = np.linspace(0, 2 * np.pi, 200)
    for v, ls in ((0, "-"), (30, "--"), (50, ":")):
        g = grip(v) / G
        ax.plot(g * np.cos(th), g * np.sin(th), "k", ls=ls, lw=1, label=f"model circle at {v} m/s")
    g = MU
    ax.plot([g, g, -g, -g, g], [g, -g, -g, g, g], color="0.6", lw=0.8, ls="--", label="pyramid (box) at 0 m/s")
    ax.set_xlabel("lateral acceleration (g)")
    ax.set_ylabel("longitudinal acceleration (g)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title("g-g diagram, Webots RaceCar on mu 1.6")
    save(fig, "gg.png")


def pyramid(summ):
    """Locked wheel slides against world direction, and corner then brake peaks against the car frame angle."""
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axs[0]
    for name, block, mark in (("mu 1.6", summ, "s"), ("mu 1.0", summ.get("variant_mu10", {}), "^"),
                              ("asym friction", summ.get("variant_asym", {}), "o")):
        pts = [(s["world_dir_deg"], s["decel_over_mu_g"], k) for k, s in block.items() if k.startswith("slide_")]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], mark, ms=7, alpha=0.8, label=name)
            for x, y, k in pts:
                ax.annotate(k[6:], (x, y), fontsize=6, xytext=(4, 2), textcoords="offset points")
    ax.axhline(1, color="k", label="circle, mu N in every direction")
    ax.axhline(2 ** 0.5, color="k", ls="--", label="box corner, sqrt 2 mu N")
    ax.set_xlabel("world direction of the sliding velocity (deg)")
    ax.set_ylabel("deceleration / mu g")
    ax.set_title("locked wheel slide, y = car yaw, b = slide angle to the car")
    ax.set_ylim(0.6, 2.6)
    ax.legend(fontsize=7, loc="lower right")
    ax = axs[1]
    th = np.linspace(0, 90, 200)
    ax.plot(th, np.ones_like(th), "k-", label="friction circle")
    ax.plot(th, 1 / np.maximum(np.cos(np.radians(th)), np.sin(np.radians(th))), "k--", label="friction box")
    c = [(s["angle_deg"], s["ratio_to_circle"], k) for k, s in summ.items() if k.startswith("combined")]
    for x, y, k in c:
        ax.plot(x, y, "o", color="tab:purple")
        ax.annotate(k[9:], (x, y), fontsize=6, xytext=(4, 2), textcoords="offset points")
    ax.set_xlabel("acceleration direction in car frame (deg, 0 lateral, 90 braking)")
    ax.set_ylabel("peak total acceleration / grip(v)")
    ax.set_title("corner at the limit then brake (b = brake level)")
    ax.set_ylim(0.6, 1.6)
    ax.legend(fontsize=7, loc="lower right")
    for a in axs:
        a.grid(alpha=0.3)
    save(fig, "friction_shape.png")


def skidpad(d):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    v = np.linspace(0, 70, 100)
    axs[0].plot(v, grip(v) / G, "k-", label="model grip(v) with downforce")
    axs[0].axhline(MU, color="k", ls="--", label="model mu g, no downforce")
    for tag, col in (("skid_r100", "tab:blue"), ("skid_r50", "tab:cyan"), ("skid_r25", "tab:green"),
                     ("skid_r100_noaero", "tab:red"), ("skid_r50_noaero", "tab:orange"), ("skid_r25_noaero", "tab:pink"),
                     ("skid_r25_mu10", "tab:brown"), ("skid_r25_fds", "tab:olive"), ("skid_r25_fds5", "tab:gray")):
        if tag in d:
            r = d[tag]
            ay = np.abs(smooth(r["ay"], 125)) / G
            if not tag.endswith(("mu10", "fds", "fds5")):
                axs[0].plot(r["vx"], ay, color=col, lw=1, label=tag)
            if tag.startswith("skid_r25") or tag == "skid_r50":
                axs[1].plot(ay, np.abs(smooth(r["beta_deg"], 25)), color=col, lw=1, label=tag)
    axs[0].set_xlabel("speed (m/s)")
    axs[0].set_ylabel("steady lateral acceleration v r (g)")
    axs[0].set_title("skidpad, rising speed at fixed steer")
    axs[1].set_xlabel("lateral acceleration (g)")
    axs[1].set_ylabel("rear axle slip angle (deg)")
    axs[1].set_title("slip angle versus lateral g")
    axs[1].set_ylim(0, 13)
    for a in axs:
        a.grid(alpha=0.3)
        a.legend(fontsize=7)
    save(fig, "skidpad.png")


def accel_brake(d):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    if "accel" in d:
        r = d["accel"]
        axs[0].plot(r["t"], r["vx"], label="speed")
        ax2 = axs[0].twinx()
        ax2.plot(r["t"], smooth(r["ax"], 25) / G, color="tab:green", lw=0.8, label="ax")
        ax2.plot(r["t"], [drive_accel(v) / G for v in r["vx"]], "k--", lw=0.8, label="model drive_accel")
        ax2.set_ylabel("ax (g)")
        ax2.legend(fontsize=7, loc="center right")
        axs[0].axhline(27.78, color="0.6", lw=0.6)
    axs[0].set_xlabel("time (s)")
    axs[0].set_ylabel("speed (m/s)")
    axs[0].set_title("full throttle from rest")
    v = np.linspace(0, 85, 100)
    axs[1].plot(v, grip(v) / G, "k-", label="model grip(v)")
    for tag, col in (("brake60", "tab:red"), ("brake70", "tab:pink")):
        if tag in d:
            r = d[tag]
            axs[1].plot(r["vx"][12:], -smooth(r["ax"], 25)[12:] / G, color=col, lw=1, label=tag)
    axs[1].set_xlabel("speed (m/s)")
    axs[1].set_ylabel("deceleration (g)")
    axs[1].set_title("full braking")
    for a in axs:
        a.grid(alpha=0.3)
    axs[1].legend(fontsize=7)
    save(fig, "accel_brake.png")


def main():
    d = load("summary")
    with open(os.path.join(RUN, "summary.json")) as fh:
        summ = json.load(fh)
    extra = os.path.join(RUN, "summary_extra.json")
    if os.path.exists(extra):
        with open(extra) as fh:
            summ.update({k: v for k, v in json.load(fh).items() if k.startswith("variant_")})
    gg(d, summ)
    pyramid(summ)
    skidpad(d)
    accel_brake(d)


if __name__ == "__main__":
    main()
