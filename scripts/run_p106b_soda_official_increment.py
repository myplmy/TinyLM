"""Run a bounded, resumable local teacher window on newly selected official SODA sources."""

import argparse
from datetime import datetime
import fcntl
import os
from pathlib import Path
import time

from scripts import diag_p106b_soda_exact_teacher as exact
from scripts import p106b_soda_batch_resume as journal
from scripts import wait_p109_cuda_return as gpu_return
from scripts.diag_p106b_soda_live_window_resume import stop_signal
from scripts.p106b_shards import verify


ROOT, gemma, owner = exact.ROOT, exact.gemma, exact.previous
FIRST, LAST, SEED = 2, 10, 823216
MAX_CARD_MIB = 12390


class OfficialReader:
    def __init__(self):
        self.reader = exact.open_source()

    def start(self):
        return dict(self.reader.start(), next_row=FIRST)

    def read_request(self, cursor, *args, **kwargs):
        if cursor["next_row"] >= LAST:
            return None
        return self.reader.read_request(cursor, *args, **kwargs)


def seal(reader):
    provenance = owner.fixture.load(exact.SOURCE / "report.json")
    assets = gemma.assets(full_hash=True)
    previous = owner.fixture.load(owner.RECEIPT)["assets"]
    if any(assets[key] != previous[key] for key in ("model_sha256", "draft_sha256", "runtime_sha256")):
        raise ValueError("the current local teacher files differ from the established teacher")
    if provenance["mapped_rows"] != 248 or len(provenance["original_group_binding"]) != 248:
        raise ValueError("the official TRAIN source roster was not established")
    settings = dict(first_row=FIRST, limit_row=LAST, teacher_sha256=assets["model_sha256"],
                    draft_sha256=assets["draft_sha256"], seed=SEED, default_route=["en", "qa"],
                    overrides={str(i): ["ko", "qa"] for i in range(FIRST, LAST) if i % 2})
    rows = []
    if set(range(FIRST, LAST)).intersection(row for row, _, _ in exact.CASES):
        raise ValueError("an earlier exact teacher pilot already used a selected source")
    for i in range(FIRST, LAST):
        lang, task = settings["overrides"].get(str(i), settings["default_route"])
        cursor = dict(reader.start(), next_row=i)
        request = reader.read_request(cursor, lang, task, SEED + i + 1)
        established = provenance["original_group_binding"][i]
        if request.payload is None or request.row.index != i or not established:
            raise ValueError("the new official source could not be prepared")
        rows.append(dict(row=i, request_sha256=request.request_sha256, raw_sha256=request.row.raw_sha256,
                         official_binding=established, language=lang, task=task))
    return dict(settings=settings, rows=rows, sources={str(path.relative_to(ROOT)): owner.io.digest(path)
        for path in (Path(__file__), exact.MANIFEST, exact.SOURCE / "report.json", Path(journal.__file__),
                     Path(exact.__file__), Path(gemma.__file__))}, runtime_sha256=assets["runtime_sha256"],
        teacher_file_identity=owner.identity(gemma.MODEL), draft_file_identity=owner.identity(gemma.DRAFT))


class Replay:
    def __init__(self, session, attempts):
        self.session, self.attempts = session, list(attempts)
        self.reused, self.live = 0, 0

    def check(self):
        self.session.check()
        if self.session.samples and self.session.samples[-1]["used"] > MAX_CARD_MIB:
            raise RuntimeError("the approved teacher card budget was exceeded")

    def request(self, route, payload, *, timeout=10):
        self.check()
        if route == "/v1/chat/completions":
            if self.attempts:
                old = self.attempts.pop(0)
                if payload != old["payload"]:
                    raise ValueError("an interrupted raw response is for a different request")
                self.reused += 1
                return old["reply"]
            self.live += 1
        return self.session.request(route, payload, timeout=timeout)


def partial_from_last_window(record, state):
    logs = sorted(record.glob("window_*.json"))
    if not logs:
        return [], 0
    prior = journal.read_json(logs[-1])
    if state["identity_sha256"] != prior["receipt"]["identity_sha256"]:
        raise ValueError("the interrupted window belongs to another sealed production")
    partial = prior["receipt"]["partial"]
    out = []
    if partial:
        directory = record / "journal" / partial["directory"]
        verify(directory, partial["manifest"])
        out = list(owner.fixture.rows(directory, partial["manifest"]))
        if any(row["source_next_cursor"]["next_row"] != state["cursor"]["next_row"]+1 for row in out):
            raise ValueError("a partial response no longer belongs to the first unfinished group")
    return out, len(logs)


def wait_for_evaluation(record, expected, deadline):
    remaining = deadline.timestamp() - 285
    while time.time() < remaining:
        terminal_path = record / "supervisor.json"
        if terminal_path.is_file():
            terminal = journal.read_json(terminal_path)
            finished = journal.read_json(record / "report.json") if terminal["returncode"] == 0 else {}
            if (finished.get("status") != "COMPLETE" or finished.get("profile_sha256") != expected
                    or (record / "evaluation_input.json").is_symlink()):
                raise ValueError("the queued teacher needs the exact successfully completed comparison")
            gpu_return.wait_for_return(terminal_path, terminal["pid"], deadline)
            return True
        time.sleep(2.)
    print("SODA_OFFICIAL_QUEUE_NO_REMAINING_WINDOW", flush=True)
    return False


def run(record, deadline, reader):
    now = time.time()
    remaining = int(deadline.timestamp() - now) - 45
    if remaining < 240:
        print("SODA_OFFICIAL_WINDOW_HOLD_TIME", remaining, flush=True)
        return 0
    profile = journal.read_json(record / "profile.json")
    if seal(reader) != profile:
        raise ValueError("the CPU-prepared source or local runtime changed")
    tokenizer = owner.fixture.tokenize()
    work = record / "journal"
    work.mkdir(exist_ok=True)
    with journal.exclusive_writer(work):
        sha = journal.identity(work, reader, profile["settings"], tokenizer)
        cursor, _ = journal.verified_prefix(work, reader.start(), sha)
    if cursor["next_row"] >= LAST:
        print("SODA_OFFICIAL_WINDOW_ALREADY_CLOSED", cursor["next_row"], flush=True)
        return 0
    attempts, index = partial_from_last_window(record, dict(identity_sha256=sha, cursor=cursor))
    remaining = int(deadline.timestamp() - time.time()) - 45
    if remaining < 240:
        print("SODA_OFFICIAL_WINDOW_HOLD_TIME", remaining, flush=True)
        return 0
    lock = os.open(ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner.idle_before_gpu()
        _, free = owner.read_memory()
        wrapped = gemma.GemmaSession(True)
        try:
            with stop_signal() as stopped, owner.wall_limit(min(remaining, 400)), wrapped as session:
                transport = Replay(session, attempts)
                seconds = min(300, int(deadline.timestamp() - time.time()) - 55)
                if seconds < 1:
                    raise TimeoutError("the teacher did not leave time for a resumable window")
                receipt = journal.run_window(work, reader, transport, tokenizer, profile["settings"], seconds=seconds,
                                             commit_groups=2, stop=lambda: stopped() or (record / "STOP").exists())
                resources = session.memory()
        except Exception as error:
            process = wrapped.session.process if wrapped.session is not None else None
            journal.write_new(record / f"failure_{index:03d}.json", dict(status="TEACHER_WINDOW_INTERRUPTED",
                error=f"{type(error).__name__}: {error}", gpu_return=owner.return_state(process, free)))
            raise
        returned = owner.return_state(wrapped.session.process, free)
        with journal.exclusive_writer(work):
            cursor, commits = journal.verified_prefix(work, reader.start(), receipt["identity_sha256"])
        result = dict(status=receipt["status"], receipt=receipt, cursor=cursor, new_teacher_calls=transport.live,
                      replayed_replies=transport.reused, candidate_rows=sum((item["candidate_manifest"] or {"rows":0})["rows"]
                        for item in commits), candidate_input_tokens=sum(item["input_tokens"] for item in commits),
                      candidate_answer_targets=sum(item["target_tokens"] for item in commits),
                      train_admitted_rows=0, resources=resources, gpu_return=returned)
        journal.write_new(record / f"window_{index:03d}.json", result)
        print({k: result[k] for k in ("status", "new_teacher_calls", "replayed_replies", "candidate_input_tokens", "gpu_return")},
              flush=True)
        return 0 if returned["returned"] and returned["owned_process_exit"] == 0 else 1
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", "run"))
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--profile-sha256")
    args = parser.parse_args()
    record = args.record.absolute()
    if record.is_symlink() or record.parent != ROOT / "test_result/evidence":
        parser.error("a dedicated local evidence directory is required")
    reader = OfficialReader()
    if args.mode == "seal":
        if record.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
            parser.error("use CPU-only preparation and a new destination")
        profile = seal(reader)
        record.mkdir()
        journal.write_new(record / "profile.json", profile)
        print("SODA_OFFICIAL_WINDOW_SEALED", len(profile["rows"]), flush=True)
        return 0
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or args.stop_by is None or args.stop_by.tzinfo is None:
        parser.error("use the authorized single GPU and an explicit cutoff")
    if bool(args.after) != bool(args.profile_sha256):
        parser.error("provide both a predecessor evaluation and its exact profile checksum")
    if args.after:
        predecessor = args.after.absolute()
        if predecessor.parent != record.parent:
            parser.error("the predecessor must be one owned local evaluation record")
        if not wait_for_evaluation(predecessor, args.profile_sha256.upper(), args.stop_by):
            return 0
    return run(record, args.stop_by, reader)


if __name__ == "__main__":
    raise SystemExit(main())
