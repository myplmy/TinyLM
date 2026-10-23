#!/usr/bin/env python3
"""Whole-cache, write-once offline format candidate, never a training gate.

Only NFC/newline normalization and empty terminal format headings are removed.
Uncertain lists, references with content, code and markup are preserved/queued.
Original text is recoverable from immutable source positions and its text SHA.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import mmap
from pathlib import Path
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import (file_sha, safe, sha, signals,
                                           tail_proposal, write_json)
from scripts.p106b_source_cleanup import TOKENIZER, TRAIN
from scripts.p106b_shards import ShardWriter, verify

OUTLINE = {"선수 및 지도자", "선수", "지도자", "통산 기록", "통산기록", "기타", "연기한 배우"}


def transform(text):
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    result, removed = normalized, []
    # Several empty terminal headings can form one suffix. Strip only until
    # the last non-heading content line, never a references section body.
    while True:
        updated, spans = tail_proposal(result)
        if not spans:
            break
        removed.extend(spans)
        result = updated
    info, _ = signals(result)
    labels = [line.strip() for line in result.splitlines() if line.strip() in OUTLINE]
    review = []
    if labels:
        review.append("structured_list_relation_needs_source_reading")
    if info:
        review.append("remaining_structure_is_candidate_not_badness")
    if not result.strip():
        return text, [], ["empty_after_proposal_original_retained"], info
    return result, removed, review, info


def run(source, tokenizer, output, seconds):
    import numpy as np
    from tokenizers import Tokenizer
    source, tokenizer, output = safe(source), safe(tokenizer), safe(output)
    if output.exists():
        raise FileExistsError("new version required; output is write-once")
    before = (source.stat().st_size, source.stat().st_mtime_ns)
    if before[0] % 2:
        raise ValueError("partial uint16 source")
    began = time.monotonic()
    source_sha, tokenizer_sha = file_sha(source), file_sha(tokenizer)
    tok = Tokenizer.from_file(str(tokenizer))
    output.mkdir(parents=True)
    writer = ShardWriter(output / "format_candidate", "documents")
    queue = ShardWriter(output / "review_queue", "positions")
    counts = Counter()
    start = docs = last_end = 0
    total = before[0] // 2
    with source.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        for block in range(0, total, 8_000_000):
            if time.monotonic() - began > seconds:
                break
            length = min(8_000_000, total - block)
            view = np.frombuffer(mm, dtype="<u2", count=length, offset=block * 2)
            ends = np.flatnonzero(view == 2).tolist()
            del view
            for end in ends:
                stop = block + end
                values = np.frombuffer(mm, dtype="<u2", count=stop - start, offset=start * 2).tolist()
                original = tok.decode(values, skip_special_tokens=False)
                text, removals, review, info = transform(original)
                row = dict(eos_segment_index=docs, cache_segment_ids=[start, stop],
                    original_text_sha256=sha(original), candidate_text_sha256=sha(text),
                    text=text, normalization_changed=(original != unicodedata.normalize("NFC", original.replace("\r\n", "\n").replace("\r", "\n"))),
                    removed_empty_terminal_headings=removals,
                    review_reasons=review, training_admission="NOT_ADMITTED", semantic_truth="NOT_REVIEWED")
                writer.append(row)
                counts["changed_documents"] += text != original
                counts["empty_terminal_heading_lines_removed"] += len(removals)
                counts["remaining_" + "structure_documents"] += bool(info)
                if review:
                    counts["pending_review_documents"] += 1
                    queue.append(dict(eos_segment_index=docs, cache_segment_ids=[start, stop],
                        original_text_sha256=row["original_text_sha256"], review_reasons=review))
                docs += 1
                start = last_end = stop + 1
            if (block // 8_000_000) % 8 == 0:
                print(json.dumps(dict(phase="format_candidate", documents=docs, through_id=last_end,
                                     source_ids=total, seconds=round(time.monotonic()-began, 1))), flush=True)
    if before != (source.stat().st_size, source.stat().st_mtime_ns):
        raise ValueError("source stat changed during reading")
    lineage = dict(source=str(source.relative_to(ROOT)), source_sha256=source_sha,
                   tokenizer_sha256=tokenizer_sha, training_admission="NOT_ADMITTED")
    manifests = {"format_candidate": writer.close(lineage=lineage),
                 "review_queue": queue.close(lineage=lineage)}
    for name, manifest in manifests.items():
        verify(output / name, manifest)
    # Hash after reading: size/mtime alone would not detect all source changes.
    if file_sha(source) != source_sha:
        raise ValueError("source SHA changed")
    report = dict(schema="P106B_WHOLE_NATIVE_FORMAT_CANDIDATE_V1", **lineage,
        documents=docs, source_ids=total, through_id_exclusive=last_end,
        remaining_ids=total-last_end, full_eos_pool_transformed=(last_end == total),
        counts=dict(counts), manifests=manifests, elapsed_sec=time.monotonic()-began,
        full_semantic_review=False, full_prose_rewrite=False,
        original_writes=0, gpu_calls=0, model_loads=0,
        quality_claim="FORMAT_DERIVATIVE_ONLY_NOT_TRAIN_READY", benchmark_decontamination="NOT_RUN")
    write_json(output / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "manifests"}, ensure_ascii=False), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=TRAIN)
    p.add_argument("--tokenizer", type=Path, default=TOKENIZER)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=3600)
    a = p.parse_args()
    if not 1 <= a.seconds <= 14400:
        p.error("bounded 1..14400 CPU seconds required")
    run(a.source, a.tokenizer, a.output, a.seconds)


if __name__ == "__main__":
    main()
