"""Measure two owned Gemma lifetimes across a real SODA stop and resume."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import time

from scripts import diag_p106b_soda_local_teacher as old
from scripts import p106b_soda_batch_resume as journal
from scripts.p106b_shards import verify


ROOT, gemma = old.ROOT, old.gemma
TAG = "p106b_soda_live_incremental_v1_20261120"
OUT = old.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
BASE = old.RECOVERY / "profile.json"
DATA = OUT / "window"
START_ROW, END_ROW, SEED = 5, 7, 692000
FIRST_MULTITURN = SEED + 7


def authority(reserve=0):
    if time() + reserve >= old.CUTOFF or (OUT / "STOP").exists():
        raise RuntimeError("Current user window ended or requested stop")


class Source:
    def __init__(self):
        self.reader = old.fixture.bound.source()

    def start(self):
        return dict(self.reader.start(), next_row=START_ROW)

    def read_request(self, cursor, *args, **kwargs):
        if cursor["next_row"] < END_ROW:
            return self.reader.read_request(cursor, *args, **kwargs)
        return None


def identity():
    archived = journal.read_json(BASE)
    files = (Path(__file__), Path(journal.__file__), Path(old.__file__), BASE, old.PLAN,
             old.fixture.bound.BOUND, old.fixture.bound.OUT / "bound_receipt.json",
             old.fixture.TOKENIZER, ROOT / "scripts/p106b_soda_production_group.py",
             ROOT / "scripts/p106b_soda_manifest_source.py", ROOT / "scripts/p106b_gemma_teacher.py")
    input_hashes = {path.relative_to(ROOT).as_posix():old.io.digest(path) for path in files}
    if old.identity(gemma.MODEL) != archived["model_identity"]:
        raise ValueError("The previous verified teacher weight file identity changed")
    if any(old.identity(gemma.SERVER.parent / path) != signature
           for path, signature in archived["runtime_identity"].items()):
        raise ValueError("The previous verified teacher runtime changed")
    return dict(pins=input_hashes, model_file_identity=archived["model_identity"],
                model_sha256=archived["model_sha256"], runtime_files=archived["runtime_sha256"])


def seal():
    authority(500)
    proof = identity()
    ready = Source()
    settings = dict(teacher_sha256=proof["model_sha256"], student_tokenizer_file_sha256=old.fixture.TOK_SHA,
                    seed=SEED, default_route=["en", "qa"], overrides={"6":["ko", "multiturn"]},
                    first_row=START_ROW, limit_row=END_ROW, scope="AUTHORED_TWO_LOCAL_SOURCE_ROWS")
    requests = {}
    for row in range(START_ROW, END_ROW):
        lang, task = settings["overrides"].get(str(row), settings["default_route"])
        result = ready.read_request(dict(ready.start(), next_row=row), lang, task, SEED + row + 1)
        if result.payload is None:
            raise ValueError("Both authored rows must be prepared for the live witness")
        requests[str(row)] = result.request_sha256
    old.fixture.tokenize()
    OUT.mkdir()
    journal.write_new(PROFILE, dict(tag=TAG, proof=proof, settings=settings, first_requests=requests, mtp=False))
    print("SODA_LIVE_WINDOW_SEAL", list(requests), flush=True)


def archived_partial():
    prior = journal.read_json(OUT / "pause.json")
    if prior["receipt"]["cursor"]["next_row"] != 6 or not prior["gpu_return"]["returned"]:
        raise ValueError("The actual first process must stop before row 6 is committed and return its GPU")
    partial = prior["receipt"]["partial"]
    directory = DATA / partial["directory"]
    manifest = partial["manifest"]
    verify(directory, manifest)
    records = list(old.fixture.rows(directory, manifest))
    if len(records) != 1 or records[0]["payload"]["seed"] != FIRST_MULTITURN:
        raise ValueError("One exact local turn must be preserved")
    return records[0]


class StopAfterReply:
    def __init__(self, delegate, pause):
        self.delegate, self.pause = delegate, pause

    def check(self):
        authority(10)
        self.delegate.check()

    def request(self, route, body, *, timeout):
        response = self.delegate.request(route, body, timeout=timeout)
        if self.pause and route == "/v1/chat/completions" and body["seed"] == FIRST_MULTITURN:
            os.kill(os.getpid(), signal.SIGTERM)
        return response


@contextmanager
def stop_signal():
    state = [False]

    def stop(_signal, _frame):
        state[0] = True

    stored = signal.signal(signal.SIGTERM, stop)
    try:
        yield lambda:state[0]
    finally:
        signal.signal(signal.SIGTERM, stored)


def phase(name):
    authority(225)
    profile = journal.read_json(PROFILE)
    if identity() != profile["proof"]:
        raise ValueError("An execution source changed since CPU preparation")
    archive = archived_partial() if name == "resume" else None
    old.idle_before_gpu()
    _, free = old.read_memory()
    wrapper = gemma.GemmaSession(False)
    with stop_signal() as received, old.wall_limit(220), wrapper as session:
        delegate = old.TeacherTransport(session, archive)
        transport = StopAfterReply(delegate, name == "pause")
        print("SODA_LIVE_WINDOW_TEACHER_READY", name, session.process.pid, flush=True)
        receipt = journal.run_window(DATA, Source(), transport, old.fixture.tokenize(), profile["settings"],
                                     seconds=160, commit_groups=2, stop=received)
        resources = session.memory()
        signalled = received()
    returned = old.return_state(wrapper.session.process, free)
    journal.write_new(OUT / f"{name}.json", dict(receipt=receipt, actual_sigterm=signalled,
                    live_teacher_calls=delegate.live_calls, archive_replays=delegate.replays,
                    gpu_return=returned, resources=resources))
    print("SODA_LIVE_WINDOW_PHASE", name, receipt["status"], receipt["cursor"]["next_row"],
          delegate.live_calls, delegate.replays, returned["returned"], flush=True)
    if not returned["returned"] or returned["owned_process_exit"] is None:
        raise RuntimeError("The owned teacher did not return the GPU")
    if name == "pause" and (not signalled or receipt["status"] != "PAUSED" or receipt["cursor"]["next_row"] != 6):
        raise ValueError("The live pause did not retain only the completed source prefix")
    if name == "resume" and (delegate.replays != 1 or receipt["status"] != "SOURCE_EXHAUSTED"
                             or receipt["resume_cursor"]["next_row"] != 6 or receipt["cursor"]["next_row"] != END_ROW):
        raise ValueError("The next native worker did not complete from the correct recorded state")


def run():
    authority(500)
    exits = {}
    for name in ("pause", "resume"):
        cmd = [sys.executable, "-B", "-m", "scripts.diag_p106b_soda_live_window_resume", name]
        exits[name] = subprocess.run(cmd, cwd=ROOT, timeout=233, check=False).returncode
        if exits[name]:
            raise RuntimeError(f"The first unsuccessful phase was {name} with exit {exits[name]}")
    paused, resumed = (journal.read_json(OUT / f"{k}.json") for k in ("pause", "resume"))
    row, commits = journal.verified_prefix(DATA, Source().start(), paused["receipt"]["identity_sha256"])
    profile = journal.read_json(PROFILE)
    observed = {str(group["row"]):group["source_request_shas"][0]
                for commit in commits for group in commit["groups"]}
    if observed != profile["first_requests"] or identity() != profile["proof"]:
        raise ValueError("A recorded native request or source identity differs from CPU preparation")
    report = dict(tag=TAG, cursor=row, phase_exits=exits, pause=paused, resume=resumed,
                  candidate_rows=sum((c["candidate_manifest"] or {"rows":0})["rows"] for c in commits),
                  input_tokens=sum(c["input_tokens"] for c in commits), target_tokens=sum(c["target_tokens"] for c in commits),
                  admitted_rows=0, student_updates=0)
    journal.write_new(OUT / "report.json", report)
    print("SODA_LIVE_WINDOW_RESULT", row["next_row"], report["candidate_rows"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("seal", "run", "pause", "resume"))
    action = parser.parse_args().phase
    if os.environ.get("CUDA_VISIBLE_DEVICES") != ("" if action == "seal" else "0"):
        parser.error("Use isolated CPU sealing or the authorized single CUDA device")
    if action == "seal":
        seal()
    elif action == "run":
        run()
    else:
        phase(action)
