"""Compare indexed ACTD alignment to the saved strict native metadata only."""

import hashlib
import json
import os
import time
from pathlib import Path

from scripts import diag_p106b_actd_indexed_alignment as prior
from scripts import p106b_actd_cache as original
from scripts import p106b_actd_indexed_alignment as indexed


ROOT = Path(__file__).resolve().parents[1]
SAVED = ROOT / "test_result/evidence/p106b_actd_top128_v1_20261113"
OUT = ROOT / "test_result/evidence/p106b_actd_saved_alignment_cpu_v1_20261118"


def read(path):
    return json.loads(path.read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def positions(text, spans):
    lookup, byte = {0: 0}, 0
    for char, value in enumerate(text, 1):
        byte += len(value.encode("utf-8", errors="strict"))
        lookup[byte] = char
    rows, holds = [], []
    for index, token in enumerate(spans):
        assert token["raw_index"] == index
        if not token["supervised"]:
            continue
        if index == 0:
            holds.append(dict(target_raw_index=index, reason="NO_NATIVE_PREFIX"))
            continue
        end = spans[index-1]["byte_end"]
        if end not in lookup:
            holds.append(dict(target_raw_index=index, reason="PREFIX_INSIDE_UTF8_CHARACTER"))
            continue
        rows.append(dict(prefix_raw_index=index-1, target_raw_index=index, target_id=token["token_id"],
            owner=token["turn_id"], character_end=lookup[end], prefix_byte_end=end,
            target_special_kind=token["special_kind"]))
    return rows, holds


def materialized_records():
    manifest_path = SAVED / "prepared_shards_manifest.json"
    manifest = read(manifest_path)
    records = []
    sequence_hash = hashlib.sha256()
    for desc in manifest["shards"]:
        file = SAVED / desc["path"]
        assert file.parent == SAVED and not file.is_symlink()
        raw = file.read_bytes()
        assert len(raw) == desc["bytes"] and digest(raw) == desc["sha256"]
        sequence_hash.update(raw)
        rows = raw.splitlines()
        assert len(rows) == desc["rows"]
        for line in rows:
            data = json.loads(line)
            text = data["packed"]["text"]
            student, sh = positions(text, data["packed"]["student"]["byte_spans"])
            teacher, th = positions(text, data["teacher"]["byte_spans"])
            assert sh == data["student_boundary_holds"] and th == data["teacher_boundary_holds"]
            records.append(dict(student=student, teacher=teacher, length_hold=data["teacher_oversized"],
                ce=data["ce_targets"], prefix_holds=len(sh), align=data["alignments"], holds=data["alignment_holds"]))
    assert len(records) == manifest["rows"] == 128 and sequence_hash.hexdigest().upper() == manifest["concat_sha256"]
    return records, digest(manifest_path.read_bytes())


def replay(records, implementation):
    total = {policy: dict(accepted=0, alignment_held=0, source_boundary_held=0) for policy in original.POLICIES}
    for record in records:
        for policy in original.POLICIES:
            if record["length_hold"]:
                rows, holds = [], [dict(student_target_raw_index=r["target_raw_index"],
                    reason="TEACHER_FULL_SEQUENCE_OVER1024", policy=policy) for r in record["student"]]
            else:
                rows, holds = implementation.align_positions(record["student"], record["teacher"], policy=policy)
            assert rows == record["align"][policy] and holds == record["holds"][policy]
            assert len(rows) + len(holds) + record["prefix_holds"] == record["ce"]
            total[policy]["accepted"] += len(rows)
            total[policy]["alignment_held"] += len(holds)
            total[policy]["source_boundary_held"] += record["prefix_holds"]
    return total


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not OUT.exists()
    pins = prior.pins()
    assert read(prior.OUT/"report.json")["sources"] == pins
    records, manifest = materialized_records()
    amounts = None
    timing = {"original": [], "indexed": []}
    for label, implementation in (("original", original), ("indexed", indexed),
                                  ("indexed", indexed), ("original", original)):
        started = time.perf_counter()
        result = replay(records, implementation)
        timing[label].append(time.perf_counter() - started)
        if amounts is None:
            amounts = result
        assert result == amounts
    assert pins == prior.pins() and digest((SAVED/"prepared_shards_manifest.json").read_bytes()) == manifest
    evidence = dict(schema="ACTD_SAVED_ALIGNMENT_CPU_V1", records=len(records), prepared_manifest_sha256=manifest,
        ce_targets=sum(r["ce"] for r in records), exact_original_positions_and_holds=amounts,
        alignment_seconds=timing, original_over_indexed=sum(timing["original"])/sum(timing["indexed"]),
        edited_saved_input=False, new_teacher_or_student_loads=0, gpu_calls=0, original_corpus_accesses=0)
    OUT.mkdir(exist_ok=False)
    with (OUT/"report.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2, allow_nan=False)
        print(file=stream)
    print("ACTD_SAVED_ALIGNMENT_CPU", evidence["ce_targets"], amounts, evidence["original_over_indexed"], flush=True)


if __name__ == "__main__":
    main()
