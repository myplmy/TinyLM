"""Read source-bound teacher requests by ordinal from sealed official SODA TRAIN."""

from bisect import bisect_right
from contextlib import contextmanager
from hashlib import sha256
from itertools import accumulate
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from scripts import audit_p106b_soda_quote_release as audit
from scripts import p106b_soda_batch_resume as journal
from scripts import p106b_soda_original_lineage as source
from scripts import prepare_p106b_soda_teacher_roster as roster
from scripts.p106b_soda_candidate_wire import PreparedDialogue, teacher_payload
from scripts.p106b_soda_manifest_source import SourceRequest, SourceRow, canonical, digest
from scripts.p106b_teacher_wrapper import BOUNDARY_MARKERS


ADMISSION = roster.ROOT / "handoff" / "audit" / "P106B_SODA_RELEASE_ROSTER_ADMISSION_20261123.json"


def load_roster(path, expected):
    report_path = path / "report.json"
    index_path = path / "train_ordinals.u32le"
    if path.resolve(strict=True) != path or index_path.is_symlink() or report_path.is_symlink():
        raise ValueError("the admitted roster and index must be regular files")
    raw_report = report_path.read_bytes()
    report_sha = digest(raw_report)
    admission = journal.read_json(ADMISSION)
    if (admission["schema"] != "P106B_SODA_TEACHER_ROSTER_ADMISSION_V1"
            or admission["corpus_admitted"] is not False
            or report_path != roster.ROOT / admission["roster_report"]
            or report_sha != admission["roster_sha256"] or report_sha != expected.upper()):
        raise ValueError("the exact independently audited official source roster is required")
    report = json.loads(raw_report)
    if (report["schema"] != roster.SCHEMA or report["status"] != "TRAIN_TEACHER_ROSTER_READY"
            or report["revision"] != source.REVISION or admission["release_revision"] != source.REVISION
            or report["reference_audit_sha256"] != admission["reference_audit_sha256"]
            or report["index_sha256"] != admission["index_sha256"]
            or report["audit"]["accepted"]["rows"] != admission["ready_count"]
            or report["release"]["train"] != list(source.RELEASE["train"])):
        raise ValueError("the admitted roster belongs to another release")
    raw = index_path.read_bytes()
    count = source.RELEASE["train"][0]
    if len(raw) != report["index_bytes"] or digest(raw) != report["index_sha256"] or len(raw) % 4:
        raise ValueError("sealed official source ordinals differ")
    indices = np.frombuffer(raw, dtype="<u4")
    if (len(indices) != report["audit"]["accepted"]["rows"] or not len(indices)
            or indices[-1] >= count or np.any(indices[1:] <= indices[:-1])):
        raise ValueError("official source ordinals are not unique and increasing")
    return report, indices


@contextmanager
def open_train():
    path = roster.OFFICIAL / "train.parquet"
    if path.resolve(strict=True) != path:
        raise ValueError("the pinned local official TRAIN file cannot be linked")
    count, expected = source.RELEASE["train"]
    with path.open("rb") as stream:
        before = source._fingerprint(stream)
        checksum = sha256()
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(chunk)
        if checksum.hexdigest() != expected or source._fingerprint(stream) != before:
            raise ValueError("official TRAIN bytes changed")
        stream.seek(0)
        parquet = pq.ParquetFile(stream)
        try:
            if parquet.metadata.num_rows != count or not set(source.COLUMNS) <= set(parquet.schema_arrow.names):
                raise ValueError("official TRAIN columns or row count changed")
            yield parquet
        finally:
            parquet.close()
            if source._fingerprint(stream) != before:
                raise ValueError("official TRAIN file changed during the window")


def prepare_dialogue(row, ordinal, raw_sha):
    turns = audit.turns(row)
    root = row["original_index"]
    if row["split"] != "train" or type(root) is not int or root < 0 or turns is None:
        raise ValueError("the roster selects an invalid official TRAIN row")
    text = "\n\n".join(f"{name}: {line}" for name, line in turns)
    if (len(text.encode("utf-8")) > 32768 or any(marker in text for marker in BOUNDARY_MARKERS)
            or any(ord(char) < 32 and char not in "\n\t" for char in text)):
        return None
    group = source.hash_json([source.REPO, source.REVISION, root])
    trace = dict(official_train=dict(original_index=root, ordinal=ordinal, group_sha256=group,
                                    row_sha256=raw_sha, split="train", release=source.REVISION),
                 proposed_legacy_split="train", scope="OFFICIAL_FICTIONAL_DIALOGUE_ONLY",
                 original_root_joined=True, corpus_admitted=False)
    meta = dict(source_id=f"soda:{root}", source_repo=source.REPO, source_revision=source.REVISION,
                source_sha256=raw_sha, source_group_id=group, source_family="soda_original",
                source_license=audit.quote.LICENSE, rights_status="CARD_ONLY", language="en",
                original_source_split="train", corpus_admitted=False)
    evidence = dict(messages=[dict(role="user", content=[dict(type="text", text=text)])], meta=meta)
    view = canonical(evidence).decode("utf-8")
    return PreparedDialogue(group, view, view, canonical(trace).decode("utf-8"))


class OfficialReleaseReader:
    """Keep each journal cursor stable across repeated requests and process restarts."""

    def __init__(self, parquet, roster_path, expected):
        report, self.indices = load_roster(roster_path, expected)
        self.parquet = parquet
        self.ends = tuple(accumulate(parquet.metadata.row_group(i).num_rows for i in range(parquet.num_row_groups)))
        self.identity = dict(source_release=source.REVISION, roster_sha256=expected.upper(),
                             source_ordinals_sha256=report["index_sha256"])
        self.cached_group = -1
        self.rows = None

    def start(self):
        return dict(self.identity, next_row=0)

    def read_request(self, cursor, language, task, seed, *, history=()):
        index = cursor.get("next_row")
        if (type(index) is not int or not 0 <= index <= len(self.indices)
                or cursor != dict(self.identity, next_row=index)):
            raise ValueError("official cursor must refer to this exact TRAIN roster")
        if index == len(self.indices):
            return None
        ordinal = int(self.indices[index])
        group = bisect_right(self.ends, ordinal)
        offset = ordinal - (self.ends[group-1] if group else 0)
        if group != self.cached_group:
            self.rows = self.parquet.read_row_group(group, columns=list(source.COLUMNS), use_threads=False)
            self.cached_group = group
        value, = self.rows.slice(offset, 1).to_pylist()
        checksum = source.hash_json(value)
        prepared = prepare_dialogue(value, ordinal, checksum)
        after = dict(self.identity, next_row=index+1)
        row = SourceRow(index, f"train.parquet:row_group_{group}", offset, checksum, after, prepared)
        if prepared is None:
            return SourceRequest(row, None, None)
        payload = teacher_payload(prepared, language, task, seed, history=history)
        binding = dict(next_cursor=after, row_sha256=checksum, payload=payload)
        return SourceRequest(row, journal.digest(canonical(binding)), canonical(payload))
