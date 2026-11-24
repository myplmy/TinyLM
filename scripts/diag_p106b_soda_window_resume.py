"""Exercise incremental SODA publication with stored native replies and OS stops."""

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from time import monotonic, sleep

from scripts import diag_p106b_soda_local_teacher as prior
from scripts import p106b_soda_batch_resume as journal
from scripts.p106b_shards import verify
from scripts.p106b_soda_manifest_source import canonical, digest


ROOT = prior.ROOT
TAG = "p106b_soda_window_resume_v1_20261120"
OUT = prior.OUT.with_name(TAG)
SOURCE = prior.RECOVERY / "report.json"
RUN = OUT / "window"
CRASH = 73
LAST_SOURCE_ROW = 5


class Prefix:
    def __init__(self):
        self.source = prior.fixture.bound.source()

    def start(self):
        return self.source.start()

    def read_request(self, cursor, *args, **kwargs):
        if cursor["next_row"] >= LAST_SOURCE_ROW:
            return None
        return self.source.read_request(cursor, *args, **kwargs)


def recovered():
    report = journal.read_json(SOURCE)
    if report["status"] != "MEASURED" or report["admitted_rows"] != 0 or report["actual_exit"] != 0:
        raise ValueError("Expected the previous successful local teacher witness")
    directory = prior.RECOVERY / "run"
    raw, candidates = (report["manifests"][k] for k in ("raw", "candidate"))
    for manifest in (raw, candidates):
        verify(directory, manifest)
    replies = list(prior.fixture.rows(directory, raw))
    if [(r["source_next_cursor"]["next_row"], r["payload"]["seed"]) for r in replies] != [
        (2, 650002), (5, 650005), (5, 650015), (5, 650025)
    ]:
        raise ValueError("The previous source-bound replies differ")
    settings = dict(teacher_sha256=candidates["lineage"]["model_sha256"],
                    tokenizer_file_sha256=prior.fixture.TOK_SHA, seed=650000,
                    default_route=["en", "qa"], overrides={"4":["ko", "multiturn"]},
                    source_limit=LAST_SOURCE_ROW, prior_reply_file_sha256=digest(SOURCE.read_bytes()),
                    diagnostic="AUTHORED_PREFIX_PREPARATION_ONLY")
    return settings, replies, list(prior.fixture.rows(directory, candidates))


class RecordedTeacher:
    def __init__(self, replies, tokenizer, *, pause=False, delay=False):
        self.replies = {digest(canonical(row["payload"])):row for row in replies}
        self.messages = {digest(canonical(row["payload"]["messages"])):row for row in replies}
        reader = Prefix()
        rejected_row = dict(reader.start(), next_row=3)
        self.invalid_cases = {digest(canonical(reader.read_request(rejected_row, "en", "qa", seed).payload))
                              for seed in (650004, 650005, 650006)}
        self.tokenizer = tokenizer
        self.pause, self.delay = pause, delay
        self.calls = []
        self.signalled = False

    def check(self):
        return None

    def request(self, route, body, *, timeout):
        if self.delay:
            sleep(timeout + .002)
            raise TimeoutError("CPU fixture honored the remaining teacher timeout")
        if route == "/apply-template":
            key = canonical(body["messages"])
            row = self.messages.get(digest(key))
            if self.pause and row and row["payload"]["seed"] == 650015:
                self.signalled = True
                os.kill(os.getpid(), signal.SIGTERM)
            return {"prompt": key.decode("utf-8")}
        if route == "/tokenize":
            row = self.messages.get(digest(body["content"].encode("utf-8")))
            ids = (list(range(row["input_tokens"])) if row else
                   self.tokenizer.encode(body["content"], add_special_tokens=False).ids)
            return {"tokens": ids}
        if route != "/v1/chat/completions":
            raise ValueError("Unexpected teacher route")
        key = digest(canonical(body))
        self.calls.append(body["seed"])
        if key in self.replies:
            return self.replies[key]["reply"]
        if key in self.invalid_cases:
            return {"choices":[{"message":{"content":"malformed authored answer"}, "finish_reason":"stop"}]}
        raise ValueError("The witness asked for an unrecorded teacher response")


def execute(phase):
    settings, replies, _ = recovered()
    tokenizer = prior.fixture.tokenize()
    transport = RecordedTeacher(replies, tokenizer, pause=phase == "pause")
    signal_received = False

    def stop_request(_signal, _frame):
        nonlocal signal_received
        signal_received = True

    def link_before_exit(src, dst, *args, **kwargs):
        if Path(dst).name == "commit_000002.json":
            print("SODA_WINDOW_ABRUPT_EXIT_BEFORE_COMMIT", flush=True)
            os._exit(CRASH)
        return real_link(src, dst, *args, **kwargs)

    previous = signal.signal(signal.SIGTERM, stop_request)
    real_link = os.link
    if phase == "crash":
        os.link = link_before_exit
    try:
        receipt = journal.run_window(RUN, Prefix(), transport, tokenizer, settings, seconds=20,
                                     commit_groups=2, stop=lambda:signal_received)
    finally:
        os.link = real_link
        signal.signal(signal.SIGTERM, previous)
    if phase == "crash":
        raise AssertionError("The publish failure fixture did not fire")
    receipt.update(teacher_completion_seeds=transport.calls, actual_sigterm=signal_received,
                   signal_sent_by_transport=transport.signalled, actual_gpu_calls=0)
    journal.write_new(OUT / f"{phase}.json", receipt)
    print("SODA_WINDOW_PHASE", phase, receipt["status"], receipt["cursor"]["next_row"], transport.calls, flush=True)


def child(phase, expected):
    cmd = [sys.executable, "-B", "-m", "scripts.diag_p106b_soda_window_resume", phase]
    run = subprocess.run(cmd, cwd=ROOT, timeout=30, check=False)
    if run.returncode != expected:
        raise RuntimeError(f"{phase} exit {run.returncode}, expected {expected}")
    return run.returncode


def rejected(call, prefix):
    try:
        call()
    except ValueError as exc:
        if not str(exc).startswith(prefix):
            raise
        return str(exc)
    raise AssertionError("Invalid resume or budget was accepted")


def verify_window(settings, replies, earlier_candidates):
    tok = prior.fixture.tokenize()
    prefix = Prefix()
    exits = {"pause":child("pause", 0)}
    paused = journal.read_json(OUT / "pause.json")
    if (paused["status"], paused["cursor"]["next_row"], paused["actual_sigterm"]) != ("PAUSED", 4, True):
        raise ValueError("SIGTERM did not preserve the completed prefix and pending group")
    first_sha = [digest(path.read_bytes()) for path in sorted(RUN.glob("commit_*.json"))]
    partial = paused["partial"]
    verify(RUN / partial["directory"], partial["manifest"])
    interrupted = list(prior.fixture.rows(RUN / partial["directory"], partial["manifest"]))
    assert len(interrupted) == 1
    exits["crash"] = child("crash", CRASH)
    assert [digest(path.read_bytes()) for path in sorted(RUN.glob("commit_*.json"))] == first_sha
    prefix_ord, old = journal.verified_prefix(RUN, prefix.start(), paused["identity_sha256"])
    assert prefix_ord["next_row"] == 4 and len(old) == 2
    exits["resume"] = child("resume", 0)
    resumed = journal.read_json(OUT / "resume.json")
    assert resumed["resume_cursor"] == paused["cursor"] and resumed["status"] == "SOURCE_EXHAUSTED"
    assert resumed["teacher_completion_seeds"] == [650005, 650015, 650025]
    assert [digest(p.read_bytes()) for p in sorted(RUN.glob("commit_*.json"))[:2]] == first_sha
    cursor, commits = journal.verified_prefix(RUN, prefix.start(), paused["identity_sha256"])
    candidates = [r for c in commits if c["candidate_manifest"]
                  for r in prior.fixture.rows(RUN / c["directory"], c["candidate_manifest"])]
    assert [r["meta"]["student_wire_sha256"] for r in candidates] == [
        r["meta"]["student_wire_sha256"] for r in earlier_candidates
    ]
    final = commits[-1]
    same = next(prior.fixture.rows(RUN / final["directory"], final["raw_manifest"]))
    assert interrupted[0]["source_request_sha256"] == same["source_request_sha256"]
    assert cursor["next_row"] == 5 and len(candidates) == 2
    return exits, paused, resumed, commits


def safety_checks(settings, replies, commits):
    tok = prior.fixture.tokenize()
    prefix = Prefix()
    session = RecordedTeacher(replies, tok)

    def start(root, configuration, seconds=20, active=session):
        return journal.run_window(root, prefix, active, tok, configuration, seconds=seconds,
                                  commit_groups=2, stop=lambda:False)

    with journal.exclusive_writer(RUN):
        locked = child("lock", 0)
    mismatch = rejected(lambda:start(RUN, dict(settings, seed=settings["seed"] + 1)),
                        "Source, teacher, tokenizer")
    ceiling = rejected(lambda:start(OUT / "invalid_duration", settings, seconds=28801),
                       "Teacher-call window")
    fork = OUT / "tampered_copy"
    shutil.copytree(RUN, fork)
    item = commits[0]
    shard = fork / item["directory"] / item["candidate_manifest"]["shards"][0]["path"]
    with shard.open("ab") as file:
        file.write(b"{}\n")
    invalid_shard = rejected(lambda:start(fork, settings), "shard byte")
    delayed = RecordedTeacher(replies, tok, delay=True)
    began = monotonic()
    timer = start(OUT / "timer", settings, seconds=1, active=delayed)
    elapsed = monotonic() - began
    assert timer["status"] == "PAUSED" and timer["cursor"]["next_row"] == 1 and elapsed < 4
    assert not session.calls and not delayed.calls
    return dict(competing_writer_exit=locked, identity_rejection=mismatch, duration_rejection=ceiling,
                shard_rejection=invalid_shard, timer_pause_seconds=elapsed, timer_cursor=timer["cursor"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("test", "pause", "crash", "resume", "lock"))
    phase = parser.parse_args().phase
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("This diagnostic only replays already recorded teacher responses on CPU")
    if phase == "lock":
        try:
            with journal.exclusive_writer(RUN):
                raise AssertionError("A second writer acquired the lock")
        except BlockingIOError:
            print("SODA_WINDOW_COMPETING_WRITER_REJECTED", flush=True)
        return
    if phase != "test":
        execute(phase)
        return
    OUT.mkdir()
    settings, replies, candidates = recovered()
    exits, paused, resumed, commits = verify_window(settings, replies, candidates)
    guards = safety_checks(settings, replies, commits)
    summary = dict(tag=TAG, source_sha256=digest(SOURCE.read_bytes()), child_exits=exits,
                   program_sha256={Path(path).name:digest(Path(path).read_bytes())
                                   for path in (__file__, journal.__file__)},
                   paused=paused, resumed=resumed, commits=len(commits), guards=guards,
                   committed_groups=sum(len(c["groups"]) for c in commits), published_candidates=2,
                   actual_input_tokens=sum(c["input_tokens"] for c in commits),
                   actual_supervised_targets=sum(c["target_tokens"] for c in commits),
                   recorded_teacher_replies=len(replies), new_teacher_calls=0, admitted_rows=0)
    journal.write_new(OUT / "report.json", summary)
    print("SODA_WINDOW_RESULT", summary["committed_groups"], summary["published_candidates"],
          summary["actual_input_tokens"], summary["actual_supervised_targets"], flush=True)


if __name__ == "__main__":
    main()
