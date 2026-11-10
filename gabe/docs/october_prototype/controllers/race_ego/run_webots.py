"""Launch race_ego jobs in headless Webots through the shared guard and lock.

  python run_webots.py "mode=stub run=smoke seconds=60"
  python run_webots.py --cap-gb 4 "mode=train run=wb_friction shield=friction minutes=35" "mode=train run=wb_none shield=none minutes=35"

Each job string becomes RACE_EGO_ARGS for one Webots run. Jobs run one after another and the
lock is released between them so other agents can take Webots. A guard refusal (hot CPU, low RAM)
is retried after a pause, and two jobs in a row killed for temperature stop the runner.
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GUARD = os.path.join(ROOT, "tools", "guard.py")
LOCK = "C:/Users/shore/.racing-webots.lock"
WEBOTS = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Webots", "msys64", "mingw64", "bin", "webots.exe")


def run(job, a):
    args = dict(x.split("=", 1) for x in job.split() if "=" in x)
    out = os.path.join(ROOT, "runs", "rl", args.get("run", "smoke"))
    os.makedirs(out, exist_ok=True)
    timeout = a.timeout or int(float(args.get("minutes", 10)) * 60 + 600)
    cmd = [a.python, GUARD, "--lock", LOCK, "--cap-gb", str(a.cap_gb), "--min-free-gb", str(a.min_free), "--cpu-pct", str(a.cpu_pct),
           "--max-temp-c", str(a.max_temp), "--start-max-c", str(a.start_max), "--log", os.path.join(out, "heartbeat.log"), "--timeout-s", str(timeout), "--",
           WEBOTS, "--batch", "--mode=fast", "--no-rendering", "--minimize", "--stdout", "--stderr",
           os.path.join(ROOT, "worlds", a.world)]
    env = {**os.environ, "RACE_EGO_ARGS": job}
    for attempt in range(a.retries):
        t0 = time.time()
        with open(os.path.join(out, "webots.log"), "a") as log:
            log.write(f"\n=== {time.strftime('%H:%M:%S')} {job}\n")
            log.flush()
            p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            log.write(p.stdout)
        tail = p.stdout.strip().splitlines()[-3:]
        print(f"[run_webots] {job} exit {p.returncode} after {time.time() - t0:.0f} s {tail}", flush=True)
        hot = "KILLED thermal" in p.stdout
        run.hot = run.hot + 1 if hot else 0
        if run.hot >= 2:
            print("[run_webots] guard tripped on temperature twice in a row, stopping", flush=True)
            sys.exit(3)
        if "refusing" not in p.stdout:
            return p.returncode
        time.sleep(a.pause)
    return 1


run.hot = 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jobs", nargs="+")
    p.add_argument("--world", default="race_train.wbt")
    p.add_argument("--cap-gb", type=float, default=3)
    p.add_argument("--timeout", type=int, default=0)
    p.add_argument("--cpu-pct", type=float, default=30)
    p.add_argument("--min-free", type=float, default=1.0)
    p.add_argument("--max-temp", type=float, default=96)
    p.add_argument("--start-max", type=float, default=94)
    p.add_argument("--retries", type=int, default=200)
    p.add_argument("--pause", type=float, default=30)
    p.add_argument("--repeat", type=int, default=1, help="cycle the job list this many times")
    p.add_argument("--gap", type=float, default=20, help="seconds off the lock between jobs")
    p.add_argument("--python", default="python")
    p.add_argument("--wait-for", action="append", default=[], help="hold every launch until these files exist")
    a = p.parse_args()
    for _ in range(a.repeat):
        for job in a.jobs:
            while not all(os.path.exists(f) for f in a.wait_for):
                time.sleep(20)
            run(job, a)
            time.sleep(a.gap)


if __name__ == "__main__":
    sys.exit(main())
