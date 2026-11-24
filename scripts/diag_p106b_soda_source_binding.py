"""Verify source-bound SODA request preparation across processes."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts import diag_p106b_soda_manifest_resume as legacy
from scripts.p106b_public_refill import english_specs
from scripts.p106b_soda_manifest_source import ManifestSodaSource, canonical, digest, source_spec_sha256


ROOT, io = legacy.io.ROOT, legacy.io
TAG = "p106b_soda_source_binding_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
BOUND = OUT / "source" / legacy.MANIFEST.name
SPEC = english_specs()[4]
OTHER = english_specs()[0]


def rejected(check, phrase):
    try:
        check()
    except ValueError as error:
        if phrase not in str(error):
            raise
    else:
        raise AssertionError(f"expected rejection containing {phrase!r}")


def source():
    manifest = legacy.read(OUT / "bound_receipt.json")
    return ManifestSodaSource(BOUND, manifest["manifest_sha256"], SPEC)


def walk(reader, cursor, limit=None):
    records = []
    while limit is None or len(records) < limit:
        index = cursor["next_row"]
        language = "en" if index % 2 else "ko"
        packet = reader.read_request(cursor, language, "qa", 135000 + index)
        if packet is None:
            break
        payload = packet.payload
        if (payload is None) != (packet.row.prepared is None):
            raise ValueError("HOLD row produced a teacher payload")
        if payload is not None and (
            "AUTHORED_NARRATIVE_NOT_INPUT" in canonical(payload).decode("utf-8")
            or not payload["messages"][0]["content"].startswith("<|think|>SOURCE SCOPE:")
        ):
            raise ValueError("held target or changed task scope in the teacher input")
        records.append(dict(index=packet.row.index, raw_sha256=packet.row.raw_sha256,
                            shard=packet.row.shard, request_sha256=packet.request_sha256,
                            state="HOLD" if payload is None else "PREPARED"))
        cursor = packet.row.next_cursor
    return dict(rows=records, cursor=cursor)


def resume_child():
    reader = source()
    saved = legacy.read(OUT / "first.json")
    result = walk(reader, saved["cursor"])
    io.write(OUT / "resumed.json", result)
    print("SODA_BOUND_RESUMED", len(result["rows"]), result["cursor"]["next_row"], flush=True)


def run():
    original_sha = legacy.read(legacy.OUT / "profile.json")["manifest_sha256"]
    old = ManifestSodaSource(legacy.MANIFEST, original_sha, SPEC)
    wrong = ManifestSodaSource(legacy.MANIFEST, original_sha, OTHER)
    saved = legacy.read(legacy.OUT / "part.json")
    legacy_cursor = saved["committed_cursor"]
    rejected(lambda: old.read_next(legacy_cursor), "cursor is outside")
    rejected(lambda: wrong.bind_legacy_cursor(legacy_cursor, verified_source_spec=SPEC),
             "verified legacy source specification differs")
    recovered = old.bind_legacy_cursor(legacy_cursor, verified_source_spec=SPEC)
    rejected(lambda: wrong.read_next(recovered), "cursor source specification differs")
    rejected(lambda: old.read_request(recovered, "en", "qa", 135004), "manifest-bound source")
    again = old.read_next(recovered)
    if (again.raw_sha256 != saved["observed_uncommitted"]["raw_sha256"] or
            again.prepared.parent_key != saved["observed_uncommitted"]["proposed_parent"]):
        raise ValueError("the actual stored legacy cursor did not recover its next row")

    prior = legacy.read(legacy.MANIFEST)
    pinned = {legacy.MANIFEST: original_sha, legacy.OUT / "part.json": io.digest(legacy.OUT / "part.json")}
    BOUND.parent.mkdir()
    for shard in prior["shards"]:
        before = legacy.MANIFEST.parent / shard["path"]
        raw = before.read_bytes()
        if digest(raw) != shard["sha256"]:
            raise ValueError("original fixture shard changed")
        pinned[before] = shard["sha256"]
        with (BOUND.parent / shard["path"]).open("xb") as stream:
            stream.write(raw)
    bound = dict(prior, lineage=dict(prior["lineage"], source_spec_sha256=source_spec_sha256(SPEC)))
    io.write(BOUND, bound)
    sha = io.digest(BOUND)
    io.write(OUT / "bound_receipt.json", dict(manifest_sha256=sha, source_spec_sha256=source_spec_sha256(SPEC)))
    rejected(lambda: ManifestSodaSource(BOUND, sha, OTHER), "manifest source specification differs")
    reader = source()
    rejected(lambda: reader.read_next(recovered), "cursor is outside")
    control = walk(reader, reader.start())
    start_legacy = dict(manifest_sha256=sha, next_row=0)
    first = walk(reader, start_legacy, 4)
    uncommitted = walk(reader, first["cursor"], 1)
    io.write(OUT / "first.json", first)
    child = subprocess.run([sys.executable, "-B", "-m", "scripts.diag_p106b_soda_source_binding", "resume"],
                           cwd=ROOT, timeout=45, check=True)
    remainder = legacy.read(OUT / "resumed.json")
    if (first["rows"] + remainder["rows"] != control["rows"] or
            uncommitted["rows"] != remainder["rows"][:1] or control["cursor"] != remainder["cursor"]):
        raise ValueError("separate process did not reproduce the source binding and request")
    if any(io.digest(p) != sha for p, sha in pinned.items()):
        raise ValueError("previous input evidence changed")
    rows = control["rows"]
    if [x["index"] for x in rows] != list(range(9)) or len({x["raw_sha256"] for x in rows}) != 9:
        raise ValueError("full row and HOLD coverage differs")
    io.write(OUT / "report.json", dict(tag=TAG, approval="WIP177", rows=rows, legacy_index=again.index,
             legacy_raw_sha256=again.raw_sha256, shard_count=len(prior["shards"]), child_exit=child.returncode,
             rejects=6, actual_teacher_calls=0, original_root_joined=False, corpus_admitted_rows=0,
             exact_uncommitted_request_replay=True, previous_inputs_preserved=True,
             changed_reader_sha256=io.digest(ROOT / "scripts/p106b_soda_manifest_source.py")))
    print("SODA_BOUND_RESULT", len(rows), sum(r["state"] == "PREPARED" for r in rows), 6, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "resume"))
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("the source binding witness runs in isolated CPU")
    (run if parser.parse_args().mode == "run" else resume_child)()
