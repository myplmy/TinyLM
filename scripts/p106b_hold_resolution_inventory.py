#!/usr/bin/env python3
"""Source-linked CPU inventory of the last verified cache's residual HOLD.

This module does not admit, edit or exclude any text. It reuses the frozen
byte decoder and shard writer, records every occurrence, and makes full-source
review packets for subsequent text-only authoring. Originals remain immutable.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import heapq
import json
import mmap
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import p106b_corpus_cache as cache
from scripts import p106b_corpus_cleanup as corpus
from scripts import p106b_hold_recovery as recovery
from scripts.p106b_native_text_audit import file_sha, write_json
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_source_cleanup import safe, sha

BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
PARENT_BASE = recovery.BASE
PARENT = PARENT_BASE / "cache_v5"
SCHEMA = "P106B_RESIDUAL_HOLD_INVENTORY_V1"
EXPECTED = 460_695


def require(ok, message):
    if not ok:
        raise ValueError(message)


class OriginalReader:
    """Read only the exact token intervals named by the verified HOLD ledger."""

    def __init__(self, scope, stack):
        self.scope = scope
        token_spec = scope["tokenizer"]
        require(file_sha(ROOT / token_spec["path"]) == token_spec["sha256"], "tokenizer changed")
        self.codec = cache.native.ByteCodec(cache.read(ROOT / token_spec["path"]))
        self.banks = {}
        for spec in scope["inputs"]:
            path = ROOT / spec["path"]
            require(file_sha(path) == spec["sha256"], "original source changed")
            stream = stack.enter_context(path.open("rb"))
            self.banks[spec["name"]] = stack.enter_context(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))

    def text(self, row):
        lo, hi = row["source_ids"]
        raw = self.banks[row["source"]][lo * 2:hi * 2]
        require(hashlib.sha256(raw).hexdigest().upper() == row["source_ids_sha256"], "interval bytes differ")
        values = array("H")
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        complete = bool(values and values[-1] == 2)
        text, decoded_bytes = self.codec.text(values[:-1] if complete else values)
        require(text.encode("utf-8") == decoded_bytes, "decoded UTF-8 bytes differ")
        require(sha(text) == row["original_text_sha256"], "decoded original body differs")
        return text, complete, True


def inventory(base=BASE, each=3):
    base = safe(base)
    require(not (base / "inventory_v1").exists(), "write-once inventory; choose a new version")
    parent = cache.read(PARENT / "built.json")
    proof = cache.read(PARENT / "recovery_verified.json")
    require(proof["status"] == "CPU_FULL_RECOVERY_CACHE_VERIFIED", "verified parent required")
    require(proof["built_sha256"] == file_sha(PARENT / "built.json"), "parent verification linkage differs")
    require(parent["counts"]["HOLD"] == EXPECTED, "residual scope changed")
    for name, digest in parent["source_code_sha256"].items():
        require(file_sha(ROOT / name) == digest, "frozen parent code changed")
    verify(PARENT / "hold", parent["manifests"]["hold"])
    scope = cache.read(PARENT_BASE / "scope.json")
    base.mkdir(parents=True, exist_ok=True)
    scope_path = base / "scope.json"
    if not scope_path.exists():
        with scope_path.open("xb") as stream:
            stream.write((PARENT_BASE / "scope.json").read_bytes())
    require(file_sha(scope_path) == parent["lineage"]["scope_sha256"], "scope changed")
    out = base / "inventory_v1"
    pin = dict(parent_built_sha256=file_sha(PARENT / "built.json"),
               parent_verified_sha256=file_sha(PARENT / "recovery_verified.json"),
               parent_hold_manifest=parent["manifests"]["hold"], scope_sha256=file_sha(scope_path),
               inventory_source_sha256=file_sha(Path(__file__)))
    writer = ShardWriter(out / "occurrences", "positions", limit=19_999_999)
    unique = {}
    counts = Counter()
    reasons = Counter()
    all_reasons = Counter()
    sources = Counter()
    start = last = time.monotonic()
    for row in cache.rows(PARENT / "hold", parent["manifests"]["hold"]):
        require(row["decision"] == "HOLD", "non-HOLD entered residual scope")
        key = row["original_text_sha256"]
        if key not in unique:
            unique[key] = dict(row, occurrences=0)
        unique[key]["occurrences"] += 1
        writer.append(dict(row, resolution="NOT_REVIEWED"))
        counts.update(documents=1, input_ids=row["input_ids"])
        reasons.update(row["reasons"][:1])
        all_reasons.update(row["reasons"])
        sources.update([row["source"]])
    require(counts["documents"] == EXPECTED and counts["input_ids"] == parent["counts"]["HOLD_input_ids"], "residual conservation differs")
    occurrences = writer.close(lineage=pin)
    unique_writer = ShardWriter(out / "unique", "texts", limit=19_999_999)
    language = Counter()
    weighted_language = Counter()
    unique_reasons = Counter()
    heaps = defaultdict(list)
    # Explicit prior individual HOLDs are routed separately, never silently
    # released by a broad pattern or reopened as an unrestricted review packet.
    prior_manual = {r["input_text_sha256"]: r for r in cache.read(ROOT / parent["recovery"]["adoptions"])["rows"]}
    with ExitStack() as stack:
        reader = OriginalReader(scope, stack)
        for number, (key, row) in enumerate(unique.items(), 1):
            text, complete, valid = reader.text(row)
            bucket = corpus.language_bucket(text)
            language.update([bucket])
            weighted_language[bucket] += row["occurrences"]
            unique_reasons.update(row["reasons"][:1])
            record = dict(row, language_bucket=bucket, characters=len(text), complete_eos=complete,
                          valid_utf8=valid, resolution="NOT_REVIEWED")
            unique_writer.append(record)
            manual = prior_manual.get(key)
            if manual and manual["decision"] == "HOLD":
                continue
            reason = row["reasons"][0]
            size = "short" if len(text) < 700 else "medium" if len(text) < 7000 else "long"
            stratum = reason + "/" + bucket + "/" + size
            entry = (-int(key, 16), key, record)
            heap = heaps[stratum]
            if len(heap) < each:
                heapq.heappush(heap, entry)
            elif entry[:2] > heap[0][:2]:
                heapq.heapreplace(heap, entry)
            if time.monotonic() - last >= 20:
                print(json.dumps(dict(phase="residual_unique_source_read", unique_done=number,
                                     unique_total=len(unique), seconds=round(time.monotonic() - start, 1))), flush=True)
                last = time.monotonic()
        manifest_unique = unique_writer.close(lineage=pin)
        selected = {}
        for stratum, heap in heaps.items():
            for _, key, row in heap:
                selected.setdefault(key, dict(row, strata=[]))["strata"].append(stratum)
        packets = out / "review_packets"
        packets.mkdir()
        catalog = []
        for number, row in enumerate(sorted(selected.values(), key=lambda r: (r["reasons"][0], r["id"]))):
            text, _, _ = reader.text(row)
            path = packets / (row["id"].replace(":", "_") + ".txt")
            payload = text.encode("utf-8")
            require(len(payload) < 20_000_000, "review packet requires ordered splitting")
            with path.open("xb") as stream:
                stream.write(payload)
            catalog.append(dict(row, path=str(path.relative_to(ROOT)), sha256=file_sha(path),
                                role=recovery.ROLE_NAMES[number % 5]))
    require(file_sha(Path(__file__)) == pin["inventory_source_sha256"], "inventory source changed during run")
    result = dict(schema=SCHEMA, pin=pin, counts=dict(counts), unique_original_texts=len(unique),
                  first_reasons=dict(reasons), all_reasons=dict(all_reasons), unique_first_reasons=dict(unique_reasons),
                  sources=dict(sources), unique_language=dict(language), occurrence_language=dict(weighted_language),
                  occurrence_manifest=occurrences, unique_manifest=manifest_unique,
                  manual_hold_unique=sum(1 for key in unique if prior_manual.get(key, {}).get("decision") == "HOLD"),
                  full_residual_coverage=True, resolved=0, unprocessed=EXPECTED, training_authorized=False,
                  seconds=time.monotonic() - start)
    write_json(packets / "manifest.json", dict(schema=SCHEMA, purpose="CONTEXT_REVIEW_NOT_PREVALENCE_OR_COMPLETION", rows=catalog))
    write_json(out / "complete.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ["pin", "occurrence_manifest", "unique_manifest"]}), flush=True)
    return result


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false", RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--each", type=int, default=3)
    args = parser.parse_args()
    require(1 <= args.each <= 10, "review stratum size out of bounds")
    inventory(args.base, args.each)


if __name__ == "__main__":
    main()
