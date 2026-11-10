"""Run a command tree under hard memory, CPU and temperature limits.

Usage: python guard2.py --cap-gb 4 --min-free-gb 10 --cpu-pct 25
       --max-temp-c 90 --log heartbeat.log [--timeout-s N] -- cmd ...

The child starts suspended, joins a Windows Job Object whose committed
memory and CPU rate are hard capped (children inherit the job), then
resumes. A watchdog kills the whole job if system available RAM drops
under the floor, the tree's private bytes pass the cap, or the ACPI
thermal zone stays over the ceiling. A heartbeat line is written and
fsynced every few seconds so a hard crash still leaves a trail.
"""

import argparse
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

import psutil
import win32pdh

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

JobObjectExtendedLimitInformation = 9
JobObjectCpuRateControlInformation = 15
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x200
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x1
JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP = 0x4
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
CREATE_SUSPENDED = 0x4


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class BASIC(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class EXTENDED(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", BASIC),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class CPU_RATE(ctypes.Structure):
    _fields_ = [("ControlFlags", wintypes.DWORD), ("CpuRate", wintypes.DWORD)]


k32.CreateJobObjectW.restype = wintypes.HANDLE
k32.OpenProcess.restype = wintypes.HANDLE


class Sensors:
    """Thermal zone and commit charge from performance counters."""

    def __init__(self):
        self.query = win32pdh.OpenQuery()
        self.temp = win32pdh.AddEnglishCounter(
            self.query, r"\Thermal Zone Information(*)\Temperature")
        self.commit = win32pdh.AddEnglishCounter(
            self.query, r"\Memory\Committed Bytes")
        self.limit = win32pdh.AddEnglishCounter(
            self.query, r"\Memory\Commit Limit")
        win32pdh.CollectQueryData(self.query)

    def read(self):
        win32pdh.CollectQueryData(self.query)
        try:
            temps = win32pdh.GetFormattedCounterArray(
                self.temp, win32pdh.PDH_FMT_DOUBLE)
            temp = max(temps.values()) - 273.15
        except Exception:
            temp = float("nan")
        fmt = win32pdh.PDH_FMT_LARGE
        commit = win32pdh.GetFormattedCounterValue(self.commit, fmt)[1]
        limit = win32pdh.GetFormattedCounterValue(self.limit, fmt)[1]
        return temp, commit / 2**30, limit / 2**30


def query(job):
    info = EXTENDED()
    k32.QueryInformationJobObject(
        job, JobObjectExtendedLimitInformation, ctypes.byref(info),
        ctypes.sizeof(info), None)
    return info


def tree_private_gb(root):
    total = 0
    try:
        procs = [root] + root.children(recursive=True)
    except psutil.Error:
        return 0.0
    for p in procs:
        try:
            total += p.memory_info().private
        except psutil.Error:
            pass
    return total / 2**30


def kill_tree(root):
    try:
        procs = root.children(recursive=True) + [root]
    except psutil.Error:
        procs = [root]
    for p in procs:
        try:
            p.kill()
        except psutil.Error:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap-gb", type=float, required=True)
    parser.add_argument("--min-free-gb", type=float, default=10.0)
    parser.add_argument("--cpu-pct", type=float, default=25.0)
    parser.add_argument("--max-temp-c", type=float, default=90.0)
    parser.add_argument("--start-max-c", type=float, default=None,
                        help="refuse to start above this, default max_temp_c minus 10")
    parser.add_argument("--timeout-s", type=float, default=0)
    parser.add_argument("--log", default=None)
    parser.add_argument("--beat-s", type=float, default=5.0)
    parser.add_argument("--lock", default="C:/Users/shore/.flyfly-heavy.lock",
                        help="shared lock so agents never run heavy jobs at once")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    lock = acquire(args.lock)
    try:
        return run(args, cmd)
    finally:
        release(lock)


def acquire(path, stale_s=3600):
    waited = 0
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.time()}".encode())
            os.close(fd)
            return path
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(path)
                if age > stale_s:
                    os.remove(path)
                    continue
            except OSError:
                continue
            if waited % 30 == 0:
                print(f"[guard] waiting for heavy job lock {path}", flush=True)
            time.sleep(2)
            waited += 2


def release(path):
    try:
        os.remove(path)
    except OSError:
        pass


def run(args, cmd):

    sensors = Sensors()
    temp, commit, limit = sensors.read()
    free = psutil.virtual_memory().available / 2**30
    if free - args.cap_gb < args.min_free_gb:
        print(f"[guard] refusing, free {free:.1f} GB minus cap "
              f"{args.cap_gb} GB is under floor {args.min_free_gb} GB",
              flush=True)
        return 3
    start_max = args.max_temp_c - 10 if args.start_max_c is None else args.start_max_c
    if temp > start_max:
        print(f"[guard] refusing, thermal zone already {temp:.0f} C",
              flush=True)
        return 3

    job = k32.CreateJobObjectW(None, None)
    info = EXTENDED()
    info.BasicLimitInformation.LimitFlags = (
        JOB_OBJECT_LIMIT_JOB_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
    info.JobMemoryLimit = int(args.cap_gb * 2**30)
    if not k32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation, ctypes.byref(info),
            ctypes.sizeof(info)):
        print("[guard] memory limit failed", ctypes.get_last_error())
        return 4
    rate = CPU_RATE(
        JOB_OBJECT_CPU_RATE_CONTROL_ENABLE
        | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP,
        int(args.cpu_pct * 100))
    if not k32.SetInformationJobObject(
            job, JobObjectCpuRateControlInformation, ctypes.byref(rate),
            ctypes.sizeof(rate)):
        print("[guard] cpu rate limit failed", ctypes.get_last_error())
        return 4

    proc = subprocess.Popen(
        cmd, creationflags=CREATE_SUSPENDED | BELOW_NORMAL_PRIORITY_CLASS)
    handle = k32.OpenProcess(0x1F0FFF, False, proc.pid)
    if not k32.AssignProcessToJobObject(job, handle):
        proc.kill()
        print("[guard] AssignProcessToJobObject failed",
              ctypes.get_last_error())
        return 4
    ntdll.NtResumeProcess(handle)
    print(f"[guard] pid {proc.pid} cap {args.cap_gb} GB floor "
          f"{args.min_free_gb} GB cpu {args.cpu_pct}% temp ceiling "
          f"{args.max_temp_c} C free at start {free:.1f} GB temp "
          f"{temp:.0f} C", flush=True)

    log = open(args.log, "a", encoding="utf-8") if args.log else None
    root = psutil.Process(proc.pid)
    psutil.cpu_percent(None)
    start = time.time()
    low, tree_peak, temp_peak, hot, reason = free, 0.0, temp, 0, None
    next_beat = next_sense = start
    while proc.poll() is None:
        now = time.time()
        avail = psutil.virtual_memory().available / 2**30
        low = min(low, avail)
        tree = tree_private_gb(root)
        tree_peak = max(tree_peak, tree)
        if now >= next_sense:
            temp, commit, limit = sensors.read()
            temp_peak = max(temp_peak, temp)
            hot = hot + 1 if temp > args.max_temp_c else 0
            next_sense = now + 1.0
        if now >= next_beat and log:
            job_gb = query(job).PeakJobMemoryUsed / 2**30
            log.write(
                f"{time.strftime('%H:%M:%S')} free {avail:.1f} GB commit "
                f"{commit:.1f}/{limit:.0f} GB tree {tree:.2f} GB job peak "
                f"{job_gb:.2f} GB cpu {psutil.cpu_percent(None):.0f}% "
                f"temp {temp:.0f} C\n")
            log.flush()
            os.fsync(log.fileno())
            next_beat = now + args.beat_s
        if avail < args.min_free_gb:
            reason = f"system free RAM {avail:.1f} GB under floor"
        elif tree > args.cap_gb:
            reason = f"process tree private {tree:.2f} GB over cap"
        elif hot >= 3:
            reason = f"thermal zone {temp:.0f} C over ceiling"
        elif args.timeout_s and now - start > args.timeout_s:
            reason = "timeout"
        if reason:
            kill_tree(root)
            k32.TerminateJobObject(job, 99)
            break
        time.sleep(0.2)
    code = proc.wait()
    peak = query(job).PeakJobMemoryUsed / 2**30
    summary = (
        f"[guard] exit {code} peak job {peak:.2f} GB peak tree "
        f"{tree_peak:.2f} GB lowest free {low:.1f} GB peak temp "
        f"{temp_peak:.0f} C elapsed {time.time() - start:.0f}s"
        + (f" KILLED {reason}" if reason else ""))
    print(summary, flush=True)
    if log:
        log.write(summary + "\n")
        log.close()
    k32.CloseHandle(job)
    return code


if __name__ == "__main__":
    sys.exit(main())
