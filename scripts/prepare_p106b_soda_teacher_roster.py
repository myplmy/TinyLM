"""Seal eligible row addresses in the admitted official SODA release."""

import argparse
from array import array
from datetime import datetime
import json
import os
from pathlib import Path
import time

import numpy as np

from scripts import audit_p106b_soda_quote_release as release
from scripts import p106b_soda_batch_resume as journal
from scripts import p106b_soda_original_lineage as source


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data_cache" / "p106b_soda_original_fdc848a_20261120"
AUDIT = ROOT / "handoff" / "audit" / "P106B_SODA_DIRECT_QUOTE_FULL_RELEASE_20261123.json"
SCHEMA = "P106B_SODA_TEACHER_ROSTER_V1"


def compile_roster(record, deadline):
    previous = journal.read_json(AUDIT)
    if (previous["status"] != "FULL_EXACT_RELEASE_AUDIT" or previous["revision"] != source.REVISION
            or previous["official_files"] != json.loads(json.dumps(source.RELEASE))):
        raise ValueError("the audited official release is required")
    ordinals = array("I")
    started = time.monotonic()
    measured = release.audit(OFFICIAL, deadline.timestamp(), on_accepted=ordinals.append)
    for field in ("scanned", "accepted", "rejected", "existing_join_sha256",
                  "accepted_ordered_groups_sha256", "tokenizer_sha256"):
        if json.loads(json.dumps(measured[field])) != previous[field]:
            raise ValueError(f"the ordered stream differs from its audited release at {field}")
    indices = np.asarray(ordinals, dtype="<u4")
    if (len(indices) != previous["accepted"]["rows"] or np.any(indices[1:] <= indices[:-1])
            or not len(indices) or indices[-1] >= source.RELEASE["train"][0]):
        raise ValueError("source ordinals must form one unique ordered TRAIN program")
    raw = indices.tobytes()
    record.mkdir(exist_ok=False)
    data = record / "train_ordinals.u32le"
    with data.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    report = dict(schema=SCHEMA, status="TRAIN_TEACHER_ROSTER_READY",
                  reference_audit_sha256=journal.digest(AUDIT.read_bytes()), release=source.RELEASE,
                  revision=source.REVISION, audit=measured, index_sha256=journal.digest(raw),
                  index_bytes=len(raw), first_ordinal=int(indices[0]), last_ordinal=int(indices[-1]),
                  teacher_calls=0, admitted_rows=0, seconds=time.monotonic()-started)
    journal.write_new(record / "report.json", report)
    journal.sync_path(record)
    print("SODA_TEACHER_ROSTER_READY", len(indices), report["index_sha256"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    record = args.record.absolute()
    if (record.parent != ROOT / "test_result" / "evidence" or record.is_symlink() or record.exists()
            or args.stop_by.tzinfo is None or time.time() >= args.stop_by.timestamp()):
        parser.error("a fresh evidence directory and an explicit future cutoff are required")
    compile_roster(record, args.stop_by)


if __name__ == "__main__":
    main()
