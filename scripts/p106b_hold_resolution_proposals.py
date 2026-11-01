#!/usr/bin/env python3
"""Run draft context repairs over every unique residual source, with conservation.

This produces proposals and source-linked counterexample packets. It cannot
produce an approved roster or a training cache. All pending bodies remain out
of the admitted set, including every prior individual unresolved judgment.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import heapq
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import p106b_hold_resolution_inventory as inventory
from scripts import p106b_hold_resolution_policy as policy

cache = inventory.cache
BASE = inventory.BASE
SCHEMA = "P106B_RESIDUAL_CONTEXT_DRAFT_PROPOSALS_V1"
CODE = ["scripts/p106b_hold_resolution_proposals.py", "scripts/p106b_hold_resolution_policy.py"]


def pins():
    return {name: inventory.file_sha(ROOT / name) for name in CODE}


def full(base=BASE, output_name="draft_proposals_v1", each=2):
    base = inventory.safe(base)
    inventory.require(output_name.isascii() and output_name.replace("_", "").isalnum(), "safe new version required")
    out = base / output_name
    inventory.require(not out.exists(), "proposal output is immutable; choose a new version")
    source = base / "inventory_v1/complete.json"
    previous = cache.read(source)
    inventory.require(previous["counts"]["documents"] == inventory.EXPECTED, "residual inventory differs")
    inventory.require(inventory.file_sha(inventory.PARENT / "built.json") == previous["pin"]["parent_built_sha256"], "parent changed")
    inventory.require(inventory.file_sha(ROOT / "scripts/p106b_hold_resolution_inventory.py") == previous["pin"]["inventory_source_sha256"], "inventory code changed")
    inventory.verify(base / "inventory_v1/unique", previous["unique_manifest"])
    old_report = cache.read(inventory.PARENT / "built.json")
    manual = {row["input_text_sha256"] for row in cache.read(ROOT / old_report["recovery"]["adoptions"])["rows"] if row["decision"] == "HOLD"}
    lineage = dict(inventory_sha256=inventory.file_sha(source), source_code_sha256=pins(), rules=policy.RULES,
                   status="DRAFT_NOT_CACHE_ADMISSION", training_authorized=False)
    writer = inventory.ShardWriter(out / "unique", "decisions", limit=19_999_999)
    counts = Counter()
    pending_reasons = Counter()
    decisions = {}
    heaps = defaultdict(list)
    covered = set()
    start = last = time.monotonic()
    scope = cache.read(base / "scope.json")
    with ExitStack() as stack:
        reader = inventory.OriginalReader(scope, stack)
        for number, row in enumerate(cache.rows(base / "inventory_v1/unique", previous["unique_manifest"]), 1):
            key = row["original_text_sha256"]
            inventory.require(key not in covered, "unique inventory repeats a source")
            covered.add(key)
            original, complete, valid = reader.text(row)
            value = policy.propose(dict(row, text=original, complete_eos=complete, valid_utf8=valid), key in manual)
            decision = value["decision"]
            inventory.require(decision in ["KEEP", "EDIT", "EXCLUDE", "PENDING"], "unknown draft outcome")
            record = {k: row[k] for k in ["id", "source", "split", "source_ids", "source_ids_sha256", "original_text_sha256", "input_ids", "language_bucket", "occurrences"]}
            record.update(decision=decision, reasons=value["reasons"], changes=value["changes"], rules=policy.RULES,
                          root_approved=False, clean_text_sha256=inventory.sha(value["text"]) if decision in ("KEEP", "EDIT") else None)
            if decision == "EDIT":
                record["text"] = value["text"]
            writer.append(record)
            decisions[key] = (decision, value["reasons"])
            counts.update([decision])
            if decision == "PENDING":
                pending_reasons.update(value["reasons"])
            # Prior individual HOLD bodies (including the known dangerous and
            # damaged source) are not recopied into automated review packets.
            if key not in manual:
                kind = "+".join(sorted({change["reason"] for change in value["changes"]})) or value["reasons"][0]
                size = "short" if len(original) < 700 else "medium" if len(original) < 7000 else "long"
                stratum = "/".join([decision, kind, row["language_bucket"], size])
                heap = heaps[stratum]
                entry = (-int(key, 16), key, row)
                if len(heap) < each:
                    heapq.heappush(heap, entry)
                elif entry[:2] > heap[0][:2]:
                    heapq.heapreplace(heap, entry)
            if time.monotonic() - last >= 20:
                print(json.dumps(dict(phase="full_unique_draft_resolution", unique_done=number,
                    unique_total=previous["unique_original_texts"], counts=dict(counts), seconds=round(time.monotonic() - start, 1))), flush=True)
                last = time.monotonic()
        unique_manifest = writer.close(lineage=lineage)
        occurrence_writer = inventory.ShardWriter(out / "occurrences", "decisions", limit=19_999_999)
        occurrence_counts = Counter()
        source_counts = defaultdict(Counter)
        for row in cache.rows(base / "inventory_v1/occurrences", previous["occurrence_manifest"]):
            decision, reasons = decisions[row["original_text_sha256"]]
            occurrence_writer.append(dict(row, resolution=decision, resolution_reasons=reasons))
            occurrence_counts.update(documents=1, input_ids=row["input_ids"], **{decision: 1})
            occurrence_counts[decision + "_input_ids"] += row["input_ids"]
            source_counts[row["source"]].update([decision])
        inventory.require(occurrence_counts["documents"] == inventory.EXPECTED
                          and occurrence_counts["input_ids"] == previous["counts"]["input_ids"], "actual occurrence conservation differs")
        occurrence_manifest = occurrence_writer.close(lineage=lineage)
        selected = {}
        for stratum, heap in heaps.items():
            for _, key, row in heap:
                selected.setdefault(key, dict(row, strata=[]))["strata"].append(stratum)
        directory = out / "review_packets"
        directory.mkdir()
        packets = []
        for row in sorted(selected.values(), key=lambda r: r["id"]):
            original, complete, valid = reader.text(row)
            value = policy.propose(dict(row, text=original, complete_eos=complete, valid_utf8=valid), False)
            filename = row["id"].replace(":", "_")
            paths = {}
            for label, text in [("original", original), ("candidate", value.get("candidate", value["text"]))]:
                payload = text.encode("utf-8")
                inventory.require(len(payload) < 20_000_000, "ordered packet splitting required")
                path = directory / (filename + "_" + label + ".txt")
                with path.open("xb") as stream:
                    stream.write(payload)
                paths[label] = dict(path=str(path.relative_to(ROOT)), sha256=inventory.file_sha(path))
            packets.append(dict(row, paths=paths, decision=value["decision"], reasons=value["reasons"]))
    inventory.require(pins() == lineage["source_code_sha256"], "draft source code changed during run")
    result = dict(schema=SCHEMA, status="DRAFT_NOT_CACHE_ADMISSION", lineage=lineage,
                  unique_counts=dict(counts), occurrence_counts=dict(occurrence_counts),
                  pending_reasons_unique=dict(pending_reasons), sources={k: dict(v) for k, v in source_counts.items()},
                  unique_manifest=unique_manifest, occurrence_manifest=occurrence_manifest,
                  full_residual_scope_covered=True, unprocessed=occurrence_counts["PENDING"],
                  root_adopted=0, training_authorized=False, seconds=time.monotonic() - start)
    inventory.write_json(directory / "manifest.json", dict(schema=SCHEMA, purpose="PURPOSED_COUNTEREXAMPLES_NOT_COMPLETION", rows=packets))
    inventory.write_json(out / "complete.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ["lineage", "unique_manifest", "occurrence_manifest", "sources"]}), flush=True)
    return result


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false", RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--output-name", default="draft_proposals_v1")
    parser.add_argument("--each", type=int, default=2)
    args = parser.parse_args()
    inventory.require(1 <= args.each <= 5, "packet stratum request out of bounds")
    full(args.base, args.output_name, args.each)


if __name__ == "__main__":
    main()
