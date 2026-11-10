"""Crash-safe evaluation (PROGRESS.md problem 43): races saved in <out>.partial.jsonl are reused on a rerun of the
same command, a cut-off last line is skipped, and a partial file from a different command is moved aside."""
import json

from racing.evaluate import _job_key, _load_partial


def _jobs():
    return [("pid_apf", None, 10_000 + s, r, 1, None, "pid_apf", "saturated_v2", "Singapore", {})
            for r in (False, True) for s in range(2)]


def _write(p, header, races, cut=False):
    with open(p, "w") as f:
        f.write(json.dumps({"header": header}) + "\n")
        for job, race in races:
            f.write(json.dumps({"key": _job_key(job), "race": race}) + "\n")
        if cut:
            f.write('{"key": ["pid_apf", 100')


def test_resume_same_command(tmp_path):
    jobs, p = _jobs(), tmp_path / "x.json.partial.jsonl"
    _write(p, {"a": 1}, [(jobs[3], {"id": 3}), (jobs[0], {"id": 0})], cut=True)
    res = _load_partial(p, {"a": 1}, jobs)
    assert res == [{"id": 0}, None, None, {"id": 3}]


def test_other_command_moved_aside(tmp_path):
    jobs, p = _jobs(), tmp_path / "x.json.partial.jsonl"
    _write(p, {"a": 1}, [(jobs[0], {"id": 0})])
    res = _load_partial(p, {"a": 2}, jobs)
    assert res == [None] * 4
    assert not p.exists() and len(list(tmp_path.glob("x.json.partial.jsonl.mismatch_*"))) == 1
