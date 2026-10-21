#!/usr/bin/env python3
"""Small immutable metadata snapshots; never copy raw corpora or weights to Git."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SOURCES = (
    "data_cache/ko-en_1200000000/meta.json",
    "data_cache/ko-en_601000000_chat32/meta.json",
    "data_cache/p106b_native_expansion_v1_s1337/meta.json",
    "data_cache/p106b_native_cleanup_v1_s1337/report.json",
    "HF/sft_ready/p101a_sft_mtp_cleanbilingual_v3_s1337/corpus/report.json",
    "HF/sft_ready/p101a_sft_mtp_verified_direct_v3_s1337/corpus/report.json",
    "HF/sft_ready/p101a_sft_mtp_verified_trace_v3_s1337/corpus/report.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/manifest.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/job_manifest.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/batch_000001/manifest.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/batch_000001/revision_manifest.json",
    "HF/sft_ready/p106b_supported_production8h_v1_s1337_pilot/batch_000000/report.json",
    "HF/sft_ready/p106b_supported_production8h_v2_s1337_pilot/batch_000000/report.json",
    "HF/sft_ready/p106b_supported_production8h_v3_s1337_pilot/batch_000000/report.json",
)


def collect():
    from scripts.p106b_source_cleanup import safe
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = safe(ROOT / "test_result/evidence" / ("p106b_oct21_preparation_" + stamp))
    destination.mkdir(parents=True, exist_ok=False)
    entries = []
    for index, relative in enumerate(SOURCES):
        path = safe(ROOT / relative)
        if not path.is_file():
            entries.append(dict(source=relative, status="ABSENT_AT_SNAPSHOT_NOT_A_FAILURE")); continue
        before = path.stat(); raw = path.read_bytes()
        if len(raw) >= 2_000_000: raise ValueError("small metadata only; no raw/weight copying")
        json.loads(raw.decode("utf-8"))
        if (before.st_size, before.st_mtime_ns) != (path.stat().st_size, path.stat().st_mtime_ns):
            raise ValueError("metadata changed during read")
        name = f"{index:02d}_metadata.json"
        with (destination / name).open("xb") as stream: stream.write(raw)
        entries.append(dict(source=relative, snapshot=name, bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest().upper(), status="COPIED_METADATA_ONLY"))
    report = dict(schema="P106B_PREPARATION_METADATA_SNAPSHOT_V1", created_at=stamp,
        entries=entries, models_loaded=0, gpu_calls=0, raw_dataset_copied=False,
        semantic_quality="NOT_ESTABLISHED_BY_METADATA_SNAPSHOT",
        original_writes=0, snapshot_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper())
    body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    with (destination / "report.json").open("x", encoding="utf-8") as stream: stream.write(body)
    print(json.dumps(dict(snapshot=str(destination.relative_to(ROOT)),
        copied=sum(e["status"] == "COPIED_METADATA_ONLY" for e in entries),
        absent=[e["source"] for e in entries if e["status"] != "COPIED_METADATA_ONLY"],
        models_loaded=0, original_writes=0), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true"); group.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps(dict(source_count=len(SOURCES), source_reads=0, model_loading=False)))
    else: collect()


if __name__ == "__main__": main()
