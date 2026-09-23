#!/usr/bin/env python3
"""P090 Aya Collection Korean provenance audit; no model or training imports.

Network and large parquet reads require an explicit queue-idle acknowledgement.
Outputs stay under HF/sft_ready and are audit-only, never an SFT train corpus.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tinylm  # noqa: F401  - set HF_HOME/HF_HUB_CACHE before huggingface_hub import
HF = ROOT / "HF"
SOURCE = HF / "sft_sources" / "aya_collection_ko"
READY = HF / "sft_ready"
REPO = "CohereLabs/aya_collection_language_split"
REVISION = "a3af2fde4b4cb5b2775830b11244a1a20b5f004f"
SHARDS = {
    "korean/train-00000-of-00002.parquet": 513477364,
    "korean/train-00001-of-00002.parquet": 460197761,
}
COLUMNS = ("id", "inputs", "targets", "dataset_name", "sub_dataset_name",
           "task_type", "template_id", "language", "split")


def assert_scoped_dirs() -> None:
    for path in (HF, HF / "sft_sources", SOURCE, READY):
        if path.is_symlink():
            raise ValueError(f"HF source/output directory is a symlink: {path}")
    if not HF.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("HF directory escaped repository root")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def local_shards() -> list[Path]:
    assert_scoped_dirs()
    base = SOURCE.resolve()
    files = []
    for name, expected_size in SHARDS.items():
        path = SOURCE / name
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"pinned shard absent or symlink: {path}")
        if not path.resolve().is_relative_to(base):
            raise ValueError(f"source escaped HF/sft_sources: {path}")
        if path.stat().st_size != expected_size:
            raise ValueError(f"pinned shard size mismatch: {path}")
        files.append(path)
    return files


def fetch() -> None:
    """Download only the two pinned Korean train shards after queue is idle."""
    assert_scoped_dirs()
    os.environ["HF_HOME"] = str(HF)
    os.environ["HF_DATASETS_CACHE"] = str(HF / "datasets")
    from huggingface_hub import hf_hub_download

    SOURCE.mkdir(parents=True, exist_ok=True)
    for name in SHARDS:
        result = hf_hub_download(
            repo_id=REPO, repo_type="dataset", revision=REVISION,
            filename=name, local_dir=SOURCE,
        )
        print(f"[FETCH] {name} -> {result}")
    local_shards()


def classify(row: dict) -> tuple[str, str]:
    """Return (status, source); no raw text is sent to stdout."""
    if row.get("language") != "kor" or row.get("split") != "train":
        return "wrong_language_or_split", ""
    question, answer = row.get("inputs"), row.get("targets")
    if not isinstance(question, str) or not isinstance(answer, str):
        return "non_string", ""
    if not question.strip() or not answer.strip():
        return "empty_pair", ""
    source = row.get("dataset_name")
    if not isinstance(source, str) or not source.strip():
        return "missing_source", ""
    if not isinstance(row.get("id"), int):
        return "missing_id", ""
    return "candidate", source.strip()


def audit_rows(rows, *, review_per_source: int = 20):
    """Bounded samples; all counts are descriptive, not quality approvals."""
    if not 1 <= review_per_source <= 50:
        raise ValueError("review_per_source must be 1..50")
    outcomes = Counter()
    provenance = Counter()
    samples = defaultdict(list)
    for index, row in enumerate(rows):
        status, source = classify(row)
        outcomes[status] += 1
        if status != "candidate":
            continue
        tuple_key = (source, str(row.get("sub_dataset_name") or ""),
                     str(row.get("task_type") or ""),
                     str(row.get("template_id") or ""))
        provenance[tuple_key] += 1
        # Stable hash-min sample, O(number of sources * requested sample size).
        rank = int.from_bytes(hashlib.sha256(
            f"{source}:{row['id']}".encode("utf-8")
        ).digest()[:8], "big")
        sample = {
            "source": source, "source_id": str(row["id"]),
            "task_type": row.get("task_type"), "template_id": row.get("template_id"),
            "inputs": row["inputs"], "targets": row["targets"],
        }
        heap = samples[source]
        item = (-rank, str(row["id"]), index, sample)
        if len(heap) < review_per_source:
            heapq.heappush(heap, item)
        elif -rank > heap[0][0]:
            heapq.heapreplace(heap, item)
    flattened = []
    for source in sorted(samples):
        flattened.extend(item[3] for item in sorted(samples[source], reverse=True))
    return {
        "rows_by_status": dict(sorted(outcomes.items())),
        "source_groups": [
            {"dataset_name": key[0], "sub_dataset_name": key[1],
             "task_type": key[2], "template_id": key[3], "rows": n}
            for key, n in sorted(provenance.items())
        ],
        "review_samples": flattened,
    }


def iter_local_rows(paths):
    import pyarrow.parquet as pq
    for path in paths:
        parquet = pq.ParquetFile(path)
        missing = set(COLUMNS) - set(parquet.schema.names)
        if missing:
            raise ValueError(f"required parquet columns missing: {sorted(missing)}")
        for batch in parquet.iter_batches(batch_size=1024, columns=COLUMNS):
            yield from batch.to_pylist()


def audit(tag: str, review_per_source: int) -> None:
    assert_scoped_dirs()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,79}", tag):
        raise ValueError("tag must be a 3..80 character safe basename")
    paths = local_shards()
    READY.mkdir(parents=True, exist_ok=True)
    manifest = READY / f"{tag}_manifest.json"
    review = READY / f"{tag}_review.jsonl"
    if manifest.exists() or review.exists() or manifest.is_symlink() or review.is_symlink():
        raise FileExistsError("audit outputs already exist; choose a new tag")
    result = audit_rows(iter_local_rows(paths), review_per_source=review_per_source)
    if result["rows_by_status"].get("candidate", 0) == 0:
        raise ValueError("no Korean train candidates; refusing empty audit")
    samples = result.pop("review_samples")
    result.update({
        "schema": "TINYLM_AYA_COLLECTION_KO_AUDIT_V1",
        "status": "PROVENANCE_AUDIT_ONLY",
        "repo": REPO, "revision": REVISION,
        "repo_card_license": "Apache-2.0",
        "source_level_rights": "NOT_REVIEWED",
        "human_quality": "NOT_RUN",
        "contamination": "NOT_RUN",
        "deduplication": "NOT_RUN",
        "multiturn": "NO_PROOF_SINGLE_PROMPT_COMPLETION",
        "source_files": [
            {"path": name, "size": SHARDS[name], "sha256": sha256(SOURCE / name)}
            for name in SHARDS
        ],
        "review_sample_count": len(samples),
    })
    # No overwrite: interrupted files remain visible and require a new tag.
    with review.open("x", encoding="utf-8") as output:
        for row in samples:
            output.write(json.dumps(row, ensure_ascii=False) + chr(10))
    with manifest.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write(chr(10))
    print(json.dumps({
        "status": result["status"], "rows_by_status": result["rows_by_status"],
        "source_groups": len(result["source_groups"]),
        "review_sample_count": len(samples),
        "manifest": str(manifest), "review": str(review),
    }, ensure_ascii=False))


def self_test() -> None:
    rows = [
        {"id": 1, "inputs": "질문", "targets": "답", "dataset_name": "human",
         "sub_dataset_name": "-", "task_type": "qa", "template_id": 0,
         "language": "kor", "split": "train"},
        {"id": 2, "inputs": "", "targets": "답", "dataset_name": "human",
         "language": "kor", "split": "train"},
        {"id": 3, "inputs": "Q", "targets": "A", "dataset_name": "human",
         "language": "eng", "split": "train"},
    ]
    rows.insert(1, dict(rows[0], inputs="다른 질문"))  # repeated source ID is allowed in audit
    result = audit_rows(rows)
    assert result["rows_by_status"] == {
        "candidate": 2, "empty_pair": 1, "wrong_language_or_split": 1
    }
    assert len(result["review_samples"]) == 2
    assert result["source_groups"][0]["rows"] == 2
    print("[PASS] Aya Korean provenance audit synthetic contract; no source download/read")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--self-test", action="store_true")
    action.add_argument("--fetch", action="store_true")
    action.add_argument("--audit", action="store_true")
    parser.add_argument("--queue-idle-confirmed", action="store_true")
    parser.add_argument("--tag", default="p090_aya_collection_ko_audit_v1")
    parser.add_argument("--review-per-source", type=int, default=20)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.queue_idle_confirmed:
        parser.error("source I/O requires --queue-idle-confirmed after queue completion")
    if args.fetch:
        fetch()
    else:
        audit(args.tag, args.review_per_source)


if __name__ == "__main__":
    main()
