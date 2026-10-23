#!/usr/bin/env python3
"""Reversible offline appendix proposals over the frozen full format candidate.

Two distinct terminal heading types, minimum body and suffix position/fraction
are proposal guards, not semantic-quality thresholds or training admission.
Lists in the article body are never inferred or rewritten by this script.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import HEADINGS, normalize_heading, safe, sha, file_sha, write_json
from scripts.p106b_source_cleanup import FENCE
from scripts.p106b_shards import ShardWriter, verify

POLICY = dict(min_body_chars=300, min_first_heading_fraction=.5, max_appendix_fraction=.4,
              minimum_distinct_headings=2, duplicate_heading_types_refused=True,
              code_fences_preserved=True, training_admission="NOT_ADMITTED")


def proposal(text):
    spans = [(m.start(), m.end()) for m in FENCE.finditer(text)]
    position, hits = 0, []
    for line in text.splitlines(keepends=True):
        name = normalize_heading(line)
        if name in HEADINGS and name != "table of contents" and not any(a <= position < b for a, b in spans):
            hits.append((position, name))
        position += len(line)
    if len(hits) < POLICY["minimum_distinct_headings"]:
        return None
    names = [name for _, name in hits]
    if len(names) != len(set(names)):
        return None
    offset = hits[0][0]
    body, appendix = text[:offset], text[offset:]
    if (len(body.strip()) < POLICY["min_body_chars"] or offset < len(text) * POLICY["min_first_heading_fraction"]
            or len(appendix) > len(text) * POLICY["max_appendix_fraction"]):
        return None
    if not appendix.strip() or not body.strip():
        return None
    return dict(body=body, appendix=appendix, char_offset=offset, headings=names,
                source_text_sha256=sha(text), body_sha256=sha(body), appendix_sha256=sha(appendix))


def run(directory, output, seconds):
    directory, output = safe(directory), safe(output)
    if output.exists():
        raise FileExistsError("write-once appendix overlay version exists")
    report_path = directory / "report.json"
    before = file_sha(report_path)
    source = json.loads(report_path.read_text(encoding="utf-8"))
    if source.get("full_eos_pool_transformed") is not True or source.get("original_writes") != 0:
        raise ValueError("complete immutable full format candidate required")
    manifest = source["manifests"]["format_candidate"]
    verify(directory / "format_candidate", manifest)
    output.mkdir(parents=True)
    writer = ShardWriter(output, "appendix_overlay")
    began = time.monotonic()
    counts = Counter()
    sample, rng = [], random.Random(2202026)
    timed_out = False
    for shard in manifest["shards"]:
        with (directory / "format_candidate" / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                if time.monotonic() - began > seconds:
                    timed_out = True
                    break
                row = json.loads(line)
                if sha(row["text"]) != row["candidate_text_sha256"]:
                    raise ValueError("format source text changed")
                change = proposal(row["text"])
                counts["documents_examined"] += 1
                if not change:
                    continue
                counts["appendix_proposals"] += 1
                counts["appendix_characters"] += len(change["appendix"])
                counts.update("heading_" + name for name in change["headings"])
                writer.append(dict(eos_segment_index=row["eos_segment_index"],
                    cache_segment_ids=row["cache_segment_ids"], original_text_sha256=row["original_text_sha256"],
                    **change, training_admission="NOT_ADMITTED", semantic_review="PENDING",
                    decision="STRUCTURE_BASED_APPENDIX_CANDIDATE_NOT_GOLD"))
                item = dict(id=row["eos_segment_index"], text=row["text"], sha256=sha(row["text"]),
                    cache_segment_ids=row["cache_segment_ids"], proposed_body=change["body"],
                    proposed_appendix=change["appendix"], proposed_char_offset=change["char_offset"])
                n = counts["appendix_proposals"]
                if len(sample) < 32:
                    sample.append(item)
                else:
                    chosen = rng.randrange(n)
                    if chosen < 32:
                        sample[chosen] = item
            if timed_out:
                break
        if counts["documents_examined"] % 100000 < shard["rows"]:
            print(json.dumps(dict(phase="appendix_overlay", counts=dict(counts),
                                 seconds=round(time.monotonic()-began, 1)), ensure_ascii=False), flush=True)
    lineage = dict(source_format_report=str(report_path.relative_to(ROOT)), source_format_report_sha256=before,
        original_cache_sha256=source["source_sha256"], policy=POLICY, training_admission="NOT_ADMITTED")
    result_manifest = writer.close(lineage=lineage)
    verify(output, result_manifest)
    if file_sha(report_path) != before:
        raise ValueError("source report changed")
    report = dict(schema="P106B_NATIVE_APPENDIX_OVERLAY_V1", **lineage, counts=dict(counts),
        full_input_examined=counts["documents_examined"] == source["documents"], timed_out=timed_out,
        full_semantic_review=False, actual_training=False, original_writes=0,
        elapsed_sec=time.monotonic()-began, manifest=result_manifest)
    write_json(output / "review_packet.json", dict(documents=sample, source_scope="uniform reservoir among eligible appendix proposals, not all documents", **lineage))
    write_json(output / "report.json", report)
    print(json.dumps({k:v for k,v in report.items() if k != "manifest"}, ensure_ascii=False), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=1800)
    a = p.parse_args()
    if not 1 <= a.seconds <= 7200:
        p.error("bounded CPU seconds required")
    run(a.directory, a.output, a.seconds)


if __name__ == "__main__":
    main()
