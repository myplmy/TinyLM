"""Prepare and resume bounded local teacher windows on the sealed official TRAIN roster."""

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import os
from pathlib import Path
import tempfile
from time import time
from unittest.mock import patch

from scripts import p106b_soda_release_reader as official
from scripts import run_p106b_soda_official_increment as pilot
from scripts.diag_p106b_supported_production8h import supported_wall_limit
from scripts.p106b_soda_production_group import GroupResult, produce_bound_group
from tinylm.train import mtp_sft


ROOT, journal, owner, gemma = pilot.ROOT, pilot.journal, pilot.owner, pilot.gemma
EVIDENCE = ROOT / "test_result" / "evidence"
SCHEMA = "P106B_SODA_RELEASE_INCREMENT_V2"
PINNED = (Path(__file__), Path(official.__file__), Path(pilot.__file__), Path(journal.__file__),
          Path(gemma.__file__), official.ADMISSION, Path(mtp_sft.__file__), ROOT / "scripts/p106b_soda_production_group.py",
          ROOT / "scripts/p106b_soda_candidate_wire.py", ROOT / "scripts/diag_p106b_supported_production8h.py")
encode_record = mtp_sft.encode_record


def pins():
    return {str(path.relative_to(ROOT)): owner.io.digest(path) for path in PINNED}


class SourceInterval:
    def __init__(self, reader, start, limit):
        self.reader, self.begin, self.end = reader, start, start+limit
        if not 0 <= self.begin < self.end <= len(reader.indices):
            raise ValueError("the official TRAIN interval is outside the admitted roster")

    def start(self):
        return dict(self.reader.start(), next_row=self.begin)

    def read_request(self, cursor, *args, **kwargs):
        if cursor == dict(self.start(), next_row=self.end):
            return None
        if not self.begin <= cursor.get("next_row", -1) < self.end:
            raise ValueError("the source cursor is outside the sealed research interval")
        return self.reader.read_request(cursor, *args, **kwargs)


def prepare(record, roster, roster_sha, start, limit, language, seed):
    assets = gemma.assets(full_hash=True)
    admitted = journal.read_json(owner.RECEIPT)["assets"]
    keys = ("model_sha256", "draft_sha256", "runtime_sha256")
    if any(assets[key] != admitted[key] for key in keys):
        raise ValueError("the exact previously measured teacher is required")
    with official.open_train() as parquet:
        reader = official.OfficialReleaseReader(parquet, roster, roster_sha)
        window = SourceInterval(reader, start, limit)
        status = window.read_request(window.start(), language, "qa", seed+start+1)
        if status is None or status.payload is None:
            raise ValueError("the interval should begin at an available source request")
    profile = dict(schema=SCHEMA, roster=str(roster), roster_sha256=roster_sha.upper(), limit=limit,
                   case_sha256=status.request_sha256, code_sha256=pins(),
                   teacher={key: assets[key] for key in keys},
                   asset_stats=[owner.identity(path) for path in (gemma.MODEL, gemma.DRAFT, gemma.SERVER)],
                   settings=dict(first_rank=start, end_rank=start+limit, seed=seed, default_route=[language, "qa"],
                                 overrides={}, teacher_sha256=assets["model_sha256"],
                                 student_corpus_admitted=False))
    record.mkdir(exist_ok=False)
    journal.write_new(record / "profile.json", profile)
    print("SODA_RELEASE_WINDOW_PREPARED", start, limit, language, owner.io.digest(record/"profile.json"), flush=True)


@contextmanager
def gpu_lease():
    fd = os.open(ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner.idle_before_gpu()
        yield
    finally:
        os.close(fd)


def interrupted_attempts(record, cursor, identity):
    previous = sorted(record.glob("receipt_*.json"))
    longest = []
    for index, path in enumerate(previous):
        if path.name != f"receipt_{index:06d}.json":
            raise ValueError("the published teacher window sequence has a gap")
        receipt = journal.read_json(path)
        if receipt["identity_sha256"] != identity or receipt["cursor"]["next_row"] > cursor["next_row"]:
            raise ValueError("a published teacher window does not belong to the verified journal")
        partial = receipt["partial"]
        if receipt["cursor"] != cursor or partial is None:
            continue
        name, manifest = partial["directory"], partial["manifest"]
        lineage = dict(identity_sha256=identity, corpus_admitted=False, cursor=cursor, status="UNCOMMITTED")
        if Path(name).name != name or not name.startswith("interrupted_") or manifest["lineage"] != lineage:
            raise ValueError("the partial teacher window is not bound to the current cursor")
        directory = record / "journal" / name
        pilot.verify(directory, manifest)
        rows = list(owner.fixture.rows(directory, manifest))
        next_cursor = dict(cursor, next_row=cursor["next_row"]+1)
        keys = ("payload", "reply", "source_request_sha256", "source_raw_sha256", "source_next_cursor")
        if (any(row["source_next_cursor"] != next_cursor for row in rows)
                or any(any(a[k] != b[k] for k in keys) for a, b in zip(longest, rows))):
            raise ValueError("the partial teacher responses conflict with the preserved prefix")
        if len(rows) > len(longest):
            longest = rows
    return longest, len(previous)


def publish_receipt(record, index, receipt):
    staging = Path(tempfile.mkdtemp(prefix="pending_receipt_", dir=record))
    file = staging / "receipt.json"
    journal.write_new(file, receipt)
    journal.sync_path(staging)
    os.link(file, record / f"receipt_{index:06d}.json")
    journal.sync_path(record)


class CandidateOverContext(ValueError):
    pass


def bounded_encode_record(row, tokenizer, context=1024):
    try:
        return encode_record(row, tokenizer, context)
    except ValueError as error:
        if error.args != ("SFT row context/token-offset contract",):
            raise
        ids, _, text = mtp_sft.encode_conversation(row, tokenizer, "chatml")
        if len(ids) <= context+1 or len(ids) != len(tokenizer.encode(text).offsets):
            raise
        raise CandidateOverContext(f"student input {len(ids)-1} exceeds context {context}") from error


def bounded_group(reader, cursor, **options):
    try:
        return produce_bound_group(reader, cursor, **options)
    except CandidateOverContext as error:
        attempts = options["raw"].rows
        final = attempts[-1]
        final["candidate_rejection"] = str(error)
        request_shas = tuple(row["source_request_sha256"] for row in attempts)
        return GroupResult(final["source_next_cursor"], final["source_raw_sha256"], "REJECTED", request_shas, None)


def run(record, checksum, stop_by, seconds):
    file = record / "profile.json"
    profile = journal.read_json(file)
    if (owner.io.digest(file).upper() != checksum.upper() or profile["schema"] != SCHEMA
            or profile["code_sha256"] != pins()):
        raise ValueError("the authorized roster, teacher profile or source changed")
    assets = gemma.assets(full_hash=True)
    if (any(assets[key] != expected for key, expected in profile["teacher"].items())
            or profile["asset_stats"] != [owner.identity(path) for path in (gemma.MODEL, gemma.DRAFT, gemma.SERVER)]):
        raise ValueError("the verified teacher assets or server were replaced")
    settings = profile["settings"]
    work = record / "journal"
    tokenizer = owner.fixture.tokenize()
    with official.open_train() as parquet, gpu_lease():
        source = official.OfficialReleaseReader(parquet, Path(profile["roster"]), profile["roster_sha256"])
        reader = SourceInterval(source, settings["first_rank"], profile["limit"])
        with journal.exclusive_writer(work):
            identity = journal.identity(work, reader, settings, tokenizer)
            cursor, _ = journal.verified_prefix(work, reader.start(), identity)
        if cursor["next_row"] == reader.end:
            print("SODA_RELEASE_WINDOW_ALREADY_COMPLETE", reader.end, flush=True)
            return 0
        raw, index = interrupted_attempts(record, cursor, identity)
        stop_marker = record / f"STOP_{index:06d}"
        wall = min(seconds, int(stop_by.timestamp() - time()) - 35)
        if wall < 240:
            raise TimeoutError("the authorized window has insufficient time for teacher startup and return")
        _, free_before = owner.read_memory()
        teacher = gemma.GemmaSession(True)
        stop_at = time()+wall
        try:
            with pilot.stop_signal() as stop, supported_wall_limit(wall), teacher as session:
                transport = pilot.Replay(session, raw)
                call_seconds = int(stop_at-time())-20
                if call_seconds < 1:
                    raise TimeoutError("teacher startup left no time for a stable journal window")
                with (patch.object(journal, "produce_bound_group", bounded_group),
                      patch.object(mtp_sft, "encode_record", bounded_encode_record)):
                    receipt = journal.run_window(work, reader, transport, tokenizer, settings, seconds=call_seconds,
                                                 commit_groups=16, stop=lambda: stop() or stop_marker.exists())
                publish_receipt(record, index, receipt)
                resources = session.memory()
        except BaseException as error:
            process = teacher.session.process if teacher.session is not None else None
            failure = record / f"failure_{time():.6f}.json"
            journal.write_new(failure, dict(status="INTERRUPTED", error_type=type(error).__name__,
                              gpu_return=owner.return_state(process, free_before)))
            raise
        returned = owner.return_state(teacher.session.process, free_before)
        with journal.exclusive_writer(work):
            _, published = journal.verified_prefix(work, reader.start(), identity)
        result = dict(receipt=receipt, profile_sha256=checksum.upper(), resources=resources, gpu_return=returned,
                      teacher_calls=transport.live, raw_reuses=transport.reused, admitted_rows=0,
                      candidate_input_tokens=sum(item["input_tokens"] for item in published),
                      candidate_answer_targets=sum(item["target_tokens"] for item in published))
        journal.write_new(record / f"window_{index:06d}.json", result)
        print("SODA_RELEASE_WINDOW_FINISHED", receipt["status"], receipt["cursor"]["next_row"],
              result["candidate_input_tokens"], returned["returned"], flush=True)
        return 0 if returned["returned"] and returned["owned_process_exit"] == 0 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    seal = modes.add_parser("prepare")
    seal.add_argument("--manifest", required=True, type=Path)
    seal.add_argument("--manifest-sha256", required=True)
    seal.add_argument("--record", required=True, type=Path)
    seal.add_argument("--start", required=True, type=int)
    seal.add_argument("--limit", required=True, type=int)
    seal.add_argument("--language", required=True, choices=("en", "ko"))
    seal.add_argument("--seed", required=True, type=int)
    begin = modes.add_parser("run")
    begin.add_argument("--record", required=True, type=Path)
    begin.add_argument("--profile-sha256", required=True)
    begin.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    begin.add_argument("--seconds", type=int, default=journal.MAX_WINDOW_SECONDS)
    args = parser.parse_args()
    record = args.record.absolute()
    if record.parent != EVIDENCE or record.is_symlink():
        parser.error("an owned SODA evidence directory is required")
    if args.mode == "prepare":
        manifest = args.manifest.absolute()
        if (record.exists() or manifest.parent.parent != EVIDENCE or manifest.name != "report.json"
                or not 0 <= args.seed < 2**31-2_000_000 or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
            parser.error("use CPU-only preparation, the local roster, a fresh output and an explicit seed")
        prepare(record, manifest.parent, args.manifest_sha256, args.start, args.limit, args.language, args.seed)
        return 0
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or args.stop_by.tzinfo is None
            or not 240 <= args.seconds <= journal.MAX_WINDOW_SECONDS):
        parser.error("the assigned single GPU and an explicit bounded window are required")
    return run(record, args.profile_sha256, args.stop_by, args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
