"""Publish source-bound SODA production in verified checkpoints on WSL."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
from time import monotonic

from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_soda_manifest_source import canonical, digest
from scripts.p106b_soda_production_group import produce_bound_group


SCHEMA = "P106B_SODA_INCREMENTAL_BATCH_V1"
MAX_WINDOW_SECONDS = 28800


class WindowPause(RuntimeError):
    pass


@contextmanager
def exclusive_writer(root):
    if root.is_symlink():
        raise ValueError("The output root cannot be a link")
    root.mkdir(parents=True, exist_ok=True)
    fd = os.open(root / "writer.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def sync_path(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_json(path):
    if path.is_symlink():
        raise ValueError("A production receipt cannot be symbolic")
    return json.loads(path.read_bytes())


def write_new(path, value):
    with path.open("xb") as output:
        output.write(canonical(value) + b"\n")
        output.flush()
        os.fsync(output.fileno())


def identity(root, reader, settings, tokenizer):
    receipt = dict(schema=SCHEMA, first_cursor=reader.start(), settings=settings,
                   student_tokenizer_sha256=digest(tokenizer.to_str().encode("utf-8")), corpus_admitted=False)
    receipt = json.loads(canonical(receipt))
    path = root / "identity.json"
    if not path.exists():
        stage = Path(tempfile.mkdtemp(prefix="pending_", dir=root))
        write_new(stage / "identity.json", receipt)
        sync_path(stage)
        os.link(stage / "identity.json", path)
        sync_path(root)
    if read_json(path) != receipt:
        raise ValueError("Source, teacher, tokenizer, or task settings differ from the published identity")
    return digest(canonical(receipt))


def input_and_target_counts(row):
    meta = row["meta"]
    inputs, targets = meta["actual_x_tokens"], meta["assistant_targets"]
    if type(inputs) is not int or type(targets) is not int or not 0 < targets <= inputs:
        raise ValueError("Candidate input and supervised counts are invalid")
    if targets != sum(meta["assistant_turn_target_counts"]):
        raise ValueError("Candidate per-turn supervised counts differ")
    return inputs, targets


def counted_rows(directory, manifest):
    if manifest is None:
        return 0, 0
    inputs = targets = 0
    for shard in manifest["shards"]:
        with (directory / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                x, y = input_and_target_counts(json.loads(line))
                inputs += x
                targets += y
    return inputs, targets


def verified_prefix(root, first_cursor, job_sha):
    cursor = first_cursor
    published = []
    for index, path in enumerate(sorted(root.glob("commit_*.json"))):
        if path.name != f"commit_{index:06d}.json":
            raise ValueError("The published commit sequence has a gap")
        receipt = read_json(path)
        if (receipt["schema"] != SCHEMA or receipt["identity_sha256"] != job_sha
                or receipt["begin_cursor"] != cursor or receipt["corpus_admitted"] is not False):
            raise ValueError("The published cursor or immutable job identity differs")
        name = receipt["directory"]
        if Path(name).name != name or not name.startswith("pending_"):
            raise ValueError("The commit must reference an owned staging directory")
        directory = root / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("The committed batch directory is absent or linked")
        raw, candidates = (receipt[name] for name in ("raw_manifest", "candidate_manifest"))
        for manifest in (raw, candidates):
            if manifest is not None:
                if manifest["lineage"] != {"identity_sha256": job_sha, "corpus_admitted": False}:
                    raise ValueError("Published shard lineage differs")
                verify(directory, manifest)
        groups = receipt["groups"]
        for group in groups:
            current = cursor["next_row"]
            if group["row"] != current or group["outcome"] not in ("HOLD", "REJECTED", "PREPARED"):
                raise ValueError("The published states do not form a contiguous source prefix")
            cursor = dict(cursor, next_row=current + 1)
        if (not groups or receipt["end_cursor"] != cursor
                or sum(g["raw_rows"] for g in groups) != (raw["rows"] if raw else 0)
                or sum(g["outcome"] == "PREPARED" for g in groups) != (candidates["rows"] if candidates else 0)
                or (receipt["input_tokens"], receipt["target_tokens"]) != counted_rows(directory, candidates)):
            raise ValueError("The commit rows and token accounting disagree")
        published.append(receipt)
    return cursor, published


class Batch:
    def __init__(self, root, job_sha, cursor):
        self.directory = Path(tempfile.mkdtemp(prefix="pending_", dir=root))
        self.lineage = dict(identity_sha256=job_sha, corpus_admitted=False)
        self.begin = cursor
        self.raw = ShardWriter(self.directory, "raw")
        self.candidates = ShardWriter(self.directory, "candidate")
        self.groups = []
        self.inputs = self.targets = 0

    def add(self, cursor, result, attempts):
        if result.next_cursor != dict(cursor, next_row=cursor["next_row"] + 1):
            raise ValueError("The adapter did not advance by exactly one source row")
        if len(attempts) != len(result.request_shas):
            raise ValueError("Source request and raw attempt counts differ")
        for attempt in attempts:
            self.raw.append(attempt)
        if result.candidate is not None:
            inputs, targets = input_and_target_counts(result.candidate)
            self.candidates.append(result.candidate)
            self.inputs += inputs
            self.targets += targets
        self.groups.append(dict(row=cursor["next_row"], outcome=result.outcome,
                                source_raw_sha256=result.raw_sha256, raw_rows=len(attempts),
                                source_request_shas=list(result.request_shas)))

    def close_shards(self, writer):
        if not writer._total_rows:
            return None
        manifest = writer.close(lineage=self.lineage)
        verify(self.directory, manifest)
        for shard in manifest["shards"]:
            sync_path(self.directory / shard["path"])
        sync_path(writer.manifest_path)
        return manifest

    def publish(self, cursor, index):
        receipt = dict(schema=SCHEMA, **self.lineage, directory=self.directory.name,
                       begin_cursor=self.begin, end_cursor=cursor, groups=self.groups,
                       input_tokens=self.inputs, target_tokens=self.targets,
                       raw_manifest=self.close_shards(self.raw), candidate_manifest=self.close_shards(self.candidates))
        draft = self.directory / "commit.json"
        write_new(draft, receipt)
        sync_path(self.directory)
        root = self.directory.parent
        os.link(draft, root / f"commit_{index:06d}.json")
        sync_path(root)
        return receipt


class Attempts:
    def __init__(self, preceding):
        self.rows = []
        self.preceding = preceding

    @property
    def _total_rows(self):
        return self.preceding + len(self.rows)

    def append(self, value):
        self.rows.append(value)


class BoundedTransport:
    def __init__(self, session, stop, end):
        self.session, self.stop, self.end = session, stop, end

    def check(self):
        if self.stop() or monotonic() >= self.end:
            raise WindowPause("Requested stop or teacher-call window ended")
        self.session.check()

    def request(self, route, body, *, timeout=10):
        self.check()
        remaining = self.end - monotonic()
        if remaining <= 0:
            raise WindowPause("Teacher-call window ended")
        try:
            return self.session.request(route, body, timeout=min(timeout, remaining))
        except TimeoutError as exc:
            if monotonic() >= self.end:
                raise WindowPause("Teacher-call window ended during a request") from exc
            raise


def run_window(root, reader, session, tokenizer, settings, *, seconds, commit_groups, stop):
    """Resume the published prefix. The caller owns authorization and the teacher lifecycle."""
    if type(seconds) is not int or not 1 <= seconds <= MAX_WINDOW_SECONDS:
        raise ValueError("Teacher-call window must be at most eight hours")
    if type(commit_groups) is not int or commit_groups < 1:
        raise ValueError("A positive checkpoint interval is required")
    end = monotonic() + seconds
    with exclusive_writer(root):
        first = reader.start()
        job_sha = identity(root, reader, settings, tokenizer)
        cursor, published = verified_prefix(root, first, job_sha)
        index = len(published)
        new_commits = []
        started = cursor
        batch = None
        pending = None
        partial = None
        transport = BoundedTransport(session, stop, end)
        status = "SOURCE_EXHAUSTED"
        try:
            while True:
                transport.check()
                row = cursor["next_row"]
                route = settings["overrides"].get(str(row), settings["default_route"])
                pending = Attempts(batch.raw._total_rows if batch is not None else 0)
                result = produce_bound_group(
                    reader, cursor, session=transport, raw=pending, tokenizer=tokenizer,
                    teacher_model_sha256=settings["teacher_sha256"], language=route[0], profile=route[1],
                    seed=(settings["seed"] + row) % 2147483647,
                )
                if result is None:
                    break
                if batch is None:
                    batch = Batch(root, job_sha, cursor)
                batch.add(cursor, result, pending.rows)
                cursor = result.next_cursor
                pending = None
                if len(batch.groups) == commit_groups:
                    new_commits.append(batch.publish(cursor, index))
                    index += 1
                    batch = None
        except WindowPause:
            status = "PAUSED"
            if pending is not None and pending.rows:
                directory = Path(tempfile.mkdtemp(prefix="interrupted_", dir=root))
                writer = ShardWriter(directory, "partial")
                for attempt in pending.rows:
                    writer.append(attempt)
                manifest = writer.close(lineage=dict(identity_sha256=job_sha, corpus_admitted=False,
                                                     cursor=cursor, status="UNCOMMITTED"))
                verify(directory, manifest)
                partial = dict(directory=directory.name, manifest=manifest)
        if batch is not None:
            new_commits.append(batch.publish(cursor, index))
        return dict(status=status, resume_cursor=started, cursor=cursor, commits_before=len(published),
                    new_commits=new_commits, partial=partial, identity_sha256=job_sha)
