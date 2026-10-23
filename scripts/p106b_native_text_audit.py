#!/usr/bin/env python3
"""Read-only native-cache census and write-once offline text-review import.

Structural signals are search candidates, not quality scores or admission gates.
There is no model, GPU, source overwrite, automatic training, or download path.
The existing conservative cleaner, safe-path guard and shard writer are reused.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
import random
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_source_cleanup import (FENCE, TOKENIZER, TRAIN, clean_text,
                                          safe, sha)
from scripts.p106b_shards import ShardWriter, verify

VERSION = "P106B_NATIVE_TEXT_AUDIT_V1"
BASE = ROOT / "data_cache/p106b_native_text_audit_v1_s1337"
# These are document-format labels, not a list of false facts/forbidden words.
HEADINGS = {"같이 보기", "더보기", "더 보기", "각주", "주석", "참고 문헌", "참고문헌",
            "외부 링크", "외부링크", "see also", "references", "external links",
            "further reading", "table of contents"}
URL = re.compile(r"(?:https?://|www\.)[^\s<>]+", re.I)
HTML = re.compile(r"</?[a-zA-Z][a-zA-Z0-9-]*(?:\s+[^<>]*?)?/?>")
CATEGORY = re.compile(r"^\s*(?:분류|Category)\s*:", re.I)


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 << 20):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if len(payload.encode("utf-8")) >= 20_000_000:
        raise ValueError("one JSON output exceeds 20MB; use row-aligned shards")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)


def normalize_heading(line):
    return " ".join(line.strip().split()).casefold()


def signals(text):
    """Count literal document structure outside protected code; no prose deletion."""
    plain = "".join(FENCE.split(text)[::2])
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    headings = Counter(normalize_heading(line) for line in lines
                       if normalize_heading(line) in HEADINGS)
    counts = Counter({"standalone_heading_lines": sum(headings.values()),
                      "url_occurrences": len(URL.findall(plain)),
                      "html_tag_occurrences": len(HTML.findall(plain)),
                      "explicit_category_lines": sum(bool(CATEGORY.match(x)) for x in lines),
                      "html_comment_openers": plain.count("<!--"),
                      "wiki_markup_openers": plain.count("[[") + plain.count("{{")})
    # Repeated lines can be legitimate lists, quotations or instructions.
    line_counts = Counter(x for x in lines if len(x) >= 6)
    counts["within_doc_repeated_line_extras"] = sum(n - 1 for n in line_counts.values() if n > 1)
    empty = 0
    for index, line in enumerate(lines):
        if normalize_heading(line) in HEADINGS:
            if index == len(lines) - 1 or normalize_heading(lines[index + 1]) in HEADINGS:
                empty += 1
    counts["empty_or_adjacent_heading_lines"] = empty
    return dict(+counts), dict(headings)


def tail_proposal(text):
    """Propose only an empty final heading; never strip a reference section body."""
    lines = text.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    if not nonempty or normalize_heading(lines[nonempty[-1]]) not in HEADINGS:
        return text, []
    end_index = nonempty[-1]
    # A heading inside code is not a page footer.
    offset = sum(map(len, lines[:end_index]))
    for match in FENCE.finditer(text):
        if match.start() <= offset < match.end():
            return text, []
    removed = "".join(lines[end_index:])
    return "".join(lines[:end_index]), [{"text": removed, "reason": "empty_final_heading_candidate"}]


def sample_update(store, seen, row, limit, rng):
    if len(store) < limit:
        store.append(row)
    elif limit:
        index = rng.randrange(seen)
        if index < limit:
            store[index] = row


def census(source, tokenizer, output, *, max_ids=0, seconds=1200, seed=1337,
           sample_count=128, candidate_count=16, chunk_ids=8_000_000):
    """Stream all complete EOS segments up to a declared resource ceiling."""
    import numpy as np
    from tokenizers import Tokenizer
    source, tokenizer, output = safe(source), safe(tokenizer), safe(output)
    if output.exists():
        raise FileExistsError("choose a new write-once census namespace")
    before = (source.stat().st_size, source.stat().st_mtime_ns)
    if before[0] % 2:
        raise ValueError("uint16 source has an incomplete byte")
    total = before[0] // 2
    limit = min(total, max_ids or total)
    if limit < 1 or seconds <= 0 or not 0 <= sample_count <= 512 or not 0 <= candidate_count <= 64:
        raise ValueError("invalid bounded census budget")
    began = time.monotonic()
    source_hash = file_sha(source)
    tok = Tokenizer.from_file(str(tokenizer))
    counts, heading_lines, heading_docs, candidate_seen = Counter(), Counter(), Counter(), Counter()
    background, candidates, unique = [], {}, {}
    rng = random.Random(seed)
    category_rng = random.Random(seed + 1)
    next_start = decoded_end = docs = decoded = skipped_ids = 0
    timed_out = False
    with source.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
        for block_start in range(0, limit, chunk_ids):
            block_end = min(limit, block_start + chunk_ids)
            view = np.frombuffer(mapped, dtype="<u2", count=block_end - block_start, offset=block_start * 2)
            ends = np.flatnonzero(view == 2).tolist()
            del view
            for local_stop in ends:
                if time.monotonic() - began > seconds:
                    timed_out = True
                    break
                stop = block_start + local_stop
                docs += 1
                length = stop - next_start
                if length > 262144:
                    counts["overlong_complete_segments_not_decoded"] += 1
                    skipped_ids += length
                else:
                    ids = np.frombuffer(mapped, dtype="<u2", count=length, offset=next_start * 2).tolist()
                    text = tok.decode(ids, skip_special_tokens=False)
                    info, heads = signals(text)
                    counts.update(info)
                    for key in info:
                        counts[f"documents_with_{key}"] += 1
                    heading_lines.update(heads)
                    heading_docs.update(heads.keys())
                    digest = sha(text)
                    key = bytes.fromhex(digest)
                    if key in unique:
                        counts["decoded_text_exact_duplicate_extras"] += 1
                        counts["decoded_text_exact_duplicate_content_ids"] += length
                    else:
                        unique[key] = 1
                    row = {"eos_segment_index": docs - 1, "cache_segment_ids": [next_start, stop],
                           "content_ids": length, "text": text, "sha256": digest,
                           "signals": info, "source_kind": "UNKNOWN_MIXED_NATIVE_CACHE",
                           "source_url": None, "training_admission": "NOT_DECIDED"}
                    decoded += 1
                    sample_update(background, decoded, row, sample_count, rng)
                    for kind in info:
                        candidate_seen[kind] += 1
                        sample_update(candidates.setdefault(kind, []), candidate_seen[kind],
                                      row, candidate_count, category_rng)
                next_start = decoded_end = stop + 1
            print(json.dumps({"phase": "census", "complete_eos_segments": docs,
                              "ids_consumed": decoded_end, "pool_ids": total,
                              "elapsed_sec": round(time.monotonic() - began, 2)}, ensure_ascii=False), flush=True)
            if timed_out:
                break
    if before != (source.stat().st_size, source.stat().st_mtime_ns):
        raise ValueError("source stat changed; do not treat this as a frozen census")
    output.mkdir(parents=True, exist_ok=False)
    lineage = {"source": str(source.relative_to(ROOT)), "source_sha256": source_hash,
               "tokenizer_sha256": file_sha(tokenizer), "selection_seed": seed,
               "scope": "complete EOS segments of actual training cache; original URLs unresolved"}
    manifests = {}
    for name, rows in (("background", background),
                       ("signal_candidates", [dict(r, candidate_channel=key)
                                              for key, records in sorted(candidates.items()) for r in records])):
        if not rows:
            continue
        writer = ShardWriter(output / "original", name)
        for row in rows:
            writer.append(row)
        manifest = writer.close(lineage=dict(lineage, selection=name))
        verify(output / "original", manifest)
        manifests[name] = {"rows": manifest["rows"], "sha256": manifest["concat_sha256"]}
    if background:
        writer = ShardWriter(output / "automatic_candidates", "format_only")
        for row in background:
            cleaned, changes, warnings = clean_text(row["text"], "unknown")
            final, removals = tail_proposal(cleaned)
            writer.append({"eos_segment_index": row["eos_segment_index"],
                           "original_sha256": row["sha256"], "cleaned_text": final,
                           "conservative_changes": changes, "warnings": warnings,
                           "removed_spans": removals, "training_admission": "REVIEW_PENDING"})
        verify(output / "automatic_candidates", writer.close(lineage=lineage))
    report = {"schema": VERSION, **lineage, "source_ids": total, "requested_id_limit": limit,
              "scanned_through_id_exclusive": decoded_end, "complete_eos_segments": docs,
              "decoded_segments": decoded, "not_decoded_overlong_content_ids": skipped_ids,
              "unprocessed_ids": total - decoded_end, "timed_out": timed_out,
              "full_eos_pool_scanned": not timed_out and limit == total and decoded_end == total,
              "source_stat_unchanged": True, "counts": dict(counts),
              "standalone_heading_lines": dict(heading_lines), "standalone_heading_documents": dict(heading_docs),
              "unique_decoded_text_sha256": len(unique), "samples": manifests,
              "elapsed_sec": time.monotonic() - began,
              "semantic_quality": "NOT_EVALUATED", "repetition_causality": "NOT_RUN",
              "benchmark_decontamination": "NOT_RUN", "full_corpus_cleaned": False,
              "gpu_calls": 0, "model_loads": 0, "original_writes": 0}
    write_json(output / "report.json", report)
    print(json.dumps({"report": str(output / "report.json"), "segments": docs,
                      "full_eos_pool_scanned": report["full_eos_pool_scanned"],
                      "seconds": report["elapsed_sec"]}, ensure_ascii=False), flush=True)
    return report


def validate_deletion(source, row):
    """Accept only exact, unambiguous deletions; never silently repair agent text."""
    original = source["text"]
    if sha(original) != source["sha256"]:
        raise ValueError("sealed source SHA mismatch")
    cleaned = row.get("cleaned_text")
    spans = row.get("removed_spans", [])
    if not isinstance(cleaned, str) or not isinstance(spans, list):
        raise ValueError("text/spans schema invalid")
    if row.get("decision") != "EXTRACT_APPENDIX" and (spans or cleaned != original):
        raise ValueError("KEEP/REVIEW/HOLD must preserve exact original text")
    if row.get("decision") == "EXTRACT_APPENDIX" and not spans:
        raise ValueError("EXTRACT_APPENDIX requires recorded deletions")
    result = original
    for span in spans:
        text = span.get("text")
        if not isinstance(text, str) or not text or result.count(text) != 1:
            raise ValueError("deleted span is absent or ambiguous")
        result = result.replace(text, "", 1)
    if result != cleaned:
        raise ValueError("cleaned text differs beyond declared exact deletions")
    if not cleaned.strip():
        raise ValueError("empty retained body requires HOLD, not automatic deletion")
    return cleaned


def import_reviews(packet, response, output):
    packet, response, output = safe(packet), safe(response), safe(output)
    if output.exists():
        raise FileExistsError("review import is write-once")
    data = json.loads(packet.read_text(encoding="utf-8"))
    rows = json.loads(response.read_text(encoding="utf-8"))
    sources = {r["id"]: r for r in data["documents"]}
    if not isinstance(rows, list) or len(rows) != len(sources) or set(r["id"] for r in rows) != set(sources):
        raise ValueError("missing/duplicate/foreign source IDs")
    output.mkdir(parents=True, exist_ok=False)
    original_writer = ShardWriter(output / "original", "sealed")
    candidate_writer = ShardWriter(output / "reviewed_candidates", "review")
    results = []
    for row in rows:
        source = sources[row["id"]]
        original_writer.append(source)
        try:
            text = validate_deletion(source, row)
            status, error = "EXACT_TEXT_PROVENANCE_VALID", None
        except (ValueError, TypeError, KeyError) as exc:
            text = None
            status, error = "REJECTED_TEXT_PROVENANCE", str(exc)
        candidate_writer.append({"source": source, "agent_response": row, "validated_text": text,
                                 "validation": status, "error": error, "training_admission": "NOT_ADMITTED"})
        results.append({"id": row["id"], "decision": row["decision"], "validation": status, "error": error})
    lineage = {"packet": str(packet.relative_to(ROOT)), "packet_sha256": file_sha(packet),
               "response": str(response.relative_to(ROOT)), "response_sha256": file_sha(response)}
    verify(output / "original", original_writer.close(lineage=lineage))
    verify(output / "reviewed_candidates", candidate_writer.close(lineage=lineage))
    report = {"schema": VERSION, **lineage, "results": results,
              "valid": sum(x["error"] is None for x in results),
              "rejected": sum(x["error"] is not None for x in results),
              "semantic_quality": "NOT_VERIFIED", "training_admission": "NOT_ADMITTED"}
    write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def merge_response(original, revision, output, key):
    """Preserve initial/revised responses and make an explicit merged version."""
    original, revision, output = safe(original), safe(revision), safe(output)
    rows = json.loads(original.read_text(encoding="utf-8"))
    repairs = json.loads(revision.read_text(encoding="utf-8"))
    old = {r[key]: r for r in rows}
    new = {r[key]: r for r in repairs}
    if len(old) != len(rows) or len(new) != len(repairs) or not new.keys() <= old.keys():
        raise ValueError("duplicate/foreign revision ID")
    write_json(output, [new.get(row[key], row) for row in rows])
    write_json(output.with_suffix(".merge_receipt.json"), {
        "original_sha256": file_sha(original), "revision_sha256": file_sha(revision),
        "merged_sha256": file_sha(output), "revised_ids": list(new),
        "original_unchanged": True, "training_admission": "NOT_ADMITTED"})


def plain_content(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, list) or any(x.get("type") != "text" for x in value):
        raise ValueError("non-text source requires separate handling")
    return "".join(x["text"] for x in value)


def prior_authored_roots():
    directory = safe(ROOT / "HF/sft_ready/p106b_luna_augmentation_v1_s1337")
    roots = set()
    for relative in ("authoring.jsonl", "batch_000001/authoring.jsonl"):
        with safe(directory / relative).open(encoding="utf-8") as stream:
            roots.update(json.loads(line)["root_id"] for line in stream if line.strip())
    return roots


def validate_variant_conversation(original_messages, variant):
    messages = variant.get("messages")
    if messages is None:
        if len(original_messages) != 2:
            raise ValueError("multi-turn source collapsed to one question/answer")
        messages = [{"role": "user", "content": variant["question"]},
                    {"role": "assistant", "content": variant["answer"]}]
    if ([m["role"] for m in messages] != [m["role"] for m in original_messages]
            or any(not isinstance(m["content"], str) or not m["content"].strip() for m in messages)):
        raise ValueError("turn count/roles or text content differ")
    return messages


def import_drafts(packet, response, output, *, kind):
    packet, response, output = safe(packet), safe(response), safe(output)
    if output.exists():
        raise FileExistsError("draft import namespace already exists")
    data = json.loads(packet.read_text(encoding="utf-8"))
    rows = json.loads(response.read_text(encoding="utf-8"))
    id_key = "source_index" if kind == "sft" else "id"
    sources = {r[id_key]: r for r in data["sources" if kind == "sft" else "documents"]}
    if len(rows) != len(sources) or set(x[id_key] for x in rows) != set(sources):
        raise ValueError("draft source coverage mismatch")
    admitted, holds, output_rows = 0, [], []
    if kind == "sft":
        prior_roots = prior_authored_roots()
        if len(prior_roots) != data["authored_prior_roots"]:
            raise ValueError("prior authored root count differs from sealed packet")
        canonical = safe(ROOT / "HF/sft_ready/p090_public_v3_train.canonical.jsonl")
        with canonical.open("rb") as stream:
            for index, line in enumerate(stream):
                if index in sources:
                    source = sources[index]
                    if hashlib.sha256(line.rstrip(b"\r\n")).hexdigest().upper() != source["source_line_sha256"].upper():
                        raise ValueError("canonical line SHA differs from sealed SFT packet")
                    if json.loads(line)["messages"] != source["messages"]:
                        raise ValueError("canonical conversation differs from packet")
                if index >= max(sources):
                    break
        for row in rows:
            source = sources[row[id_key]]
            if any(row[k] != source[k] for k in ("source_id", "root_id")):
                raise ValueError("SFT source identity changed")
            if row["root_id"] in prior_roots:
                raise ValueError("previously authored root repeated")
            variants = row["variants"]
            if len(variants) != 3 or {v["kind"] for v in variants} != set(data["required_variants"]):
                raise ValueError("SFT requires exactly three declared variants")
            original_messages = [{"role": m["role"], "content": plain_content(m["content"])} for m in source["messages"]]
            for variant in variants:
                messages = validate_variant_conversation(original_messages, variant)
                output_rows.append({"batch_id": "batch_000002", "source_index": row[id_key],
                                    "source_id": row["source_id"], "root_id": row["root_id"],
                                    "source_line_sha256": source["source_line_sha256"],
                                    "source_split": source["source_split"],
                                    "original_messages": original_messages, "messages": messages,
                                    "variant_kind": variant["kind"],
                                    "language": "en" if variant["kind"] == "en_rephrase" else "ko",
                                    "triage_reason": row["triage_reason"],
                                    "status": "DRAFT_NOT_TRAIN_READY", "semantic_review": "PENDING",
                                    "author_model": "gpt-6-luna", "reasoning_effort": "max",
                                    "training_admission": "NOT_ADMITTED"})
            if row["triage_reason"]:
                holds.append(row[id_key])
    else:
        for row in rows:
            source = sources[row[id_key]]
            if sha(source["text"]) != source["sha256"]:
                raise ValueError("non-SFT sealed text SHA mismatch")
            selected = row["selected_text"]
            if row["decision"] == "TRANSLATION_DRAFT":
                if not isinstance(selected, str) or not selected or selected not in source["text"]:
                    raise ValueError("selected English passage is not an exact source substring")
                if not row["ko_translation"] or not row["ko_rephrase"]:
                    raise ValueError("translation/rephrase absent")
                admitted += 1
            else:
                holds.append(row[id_key])
            output_rows.append({"source": source, "draft": row, "source_url": None,
                                "source_membership": "UNKNOWN_MIXED_NATIVE_CACHE",
                                "training_admission": "PROVENANCE_AND_SEMANTIC_REVIEW_PENDING"})
    output.mkdir(parents=True, exist_ok=False)
    lineage = {"packet_sha256": file_sha(packet), "response_sha256": file_sha(response),
               "kind": kind, "training_admission": "NOT_ADMITTED"}
    writer = ShardWriter(output, "authoring")
    for row in output_rows:
        writer.append(row)
    manifest = writer.close(lineage=lineage)
    verify(output, manifest)
    report = {"schema": VERSION, **lineage, "source_rows": len(sources),
              "draft_rows": len(output_rows), "held_source_ids": holds,
              "translation_passage_drafts": admitted if kind != "sft" else None,
              "all_drafts_semantic_review_pending": True, "turn_structure_verified": kind == "sft"}
    write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def render_review(base, output):
    """Render local readable source/answer text, not a JSON-only review request."""
    base, output = safe(base), safe(output)
    parts = ["# 원문·정제 후보 및 번역 초안 검토 자료\n",
             "이 자료는 후행 검토용이며 자동 학습 채택·정답 판정이 아닙니다. 원문은 별도 보존했습니다.\n",
             "원 URL을 잃은 혼합 캐시여서 개별 영문을 FineWeb-Edu로 확정하지 않습니다.\n"]
    for name in ("preprocess_1", "preprocess_2_revision1", "preprocess_3"):
        directory = base / "imported" / name
        manifest = json.loads((directory / "reviewed_candidates/review_shards_manifest.json").read_text(encoding="utf-8"))
        for spec in manifest["shards"]:
            for line in (directory / "reviewed_candidates" / spec["path"]).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                source, response = row["source"], row["agent_response"]
                parts.extend([f"\n## 원문 {source['id']} — {response['decision']}\n",
                              f"출처 캐시 위치: {source['cache_segment_ids']} / 원문 SHA: {source['sha256']}\n",
                              f"기계 검산: {row['validation']} / {row['error'] or '선언한 삭제 외 본문 변경 없음'}\n",
                              "\n### 원문\n\n", source["text"], "\n\n### 판독 의견\n\n",
                              str(response["quality_notes"]), "\n\n### 분리 후보 구간\n\n"])
                for span in response["removed_spans"]:
                    parts.extend([span["text"], "\n이유: ", str(span["reason"]), "\n\n"])
                if not response["removed_spans"]:
                    parts.append("삭제 제안 없음. 보류/유지는 정답성 보증이 아닙니다.\n")
                parts.extend(["\n### 정제 후보 본문\n\n", row["validated_text"] or "검산 거부 — 원문 유지", "\n"])
    payload = "".join(parts)
    if len(payload.encode("utf-8")) >= 20_000_000:
        raise ValueError("human review exceeds20MB; split by source document")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    print(json.dumps({"human_review": str(output), "bytes": len(payload.encode("utf-8"))}, ensure_ascii=False))


def render_drafts(directory, output):
    directory, output = safe(directory), safe(output)
    manifest = json.loads((directory / "authoring_shards_manifest.json").read_text(encoding="utf-8"))
    verify(directory, manifest)
    parts = ["# 번역·동일의미 증강 초안 원문 대조\n\n",
             "모든 행은 초안이며 실제 학습에 넣지 않았습니다. 원문에 이미 있는 오류는 번역으로 고쳐지지 않습니다.\n",
             "수학 정의 불일치(192), 첫 오답 뒤 사용자가 교정하는 대화의 턴 마스크(198)는 별도 보류입니다.\n"]
    for spec in manifest["shards"]:
        for line in (directory / spec["path"]).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if "messages" in row:
                parts.extend([f"\n## 원천 {row['source_index']} / {row['variant_kind']}\n",
                              f"검토 표시: {row['triage_reason'] or '사실·의미 검토 대기'}\n",
                              "\n### 원문 대화\n\n"])
                for message in row["original_messages"]:
                    label = "질문" if message["role"] == "user" else "답변"
                    parts.extend([f"{label}: ", message["content"], "\n\n"])
                parts.append("\n### 번역 또는 재표현 대화\n\n")
                for message in row["messages"]:
                    label = "질문" if message["role"] == "user" else "답변"
                    parts.extend([f"{label}: ", message["content"], "\n\n"])
            else:
                source, draft = row["source"], row["draft"]
                parts.extend([f"\n## 비SFT 원천 {source['id']} / {draft['decision']}\n",
                              "출처 URL·FineWeb 소속·이용 조건 확정 전 초안입니다.\n\n",
                              "선별 이유: ", draft["quality_reason"], "\n\n### 원문\n\n", source["text"], "\n"])
                if draft["selected_text"]:
                    parts.extend(["\n### 선택한 영어 구간\n\n", draft["selected_text"],
                                  "\n\n### 한국어 번역\n\n", draft["ko_translation"],
                                  "\n\n### 한국어 재표현\n\n", draft["ko_rephrase"], "\n"])
    payload = "".join(parts)
    if len(payload.encode("utf-8")) >= 20_000_000:
        raise ValueError("readable draft text exceeds20MB; split by source")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    print(json.dumps({"human_review": str(output), "bytes": len(payload.encode("utf-8"))}, ensure_ascii=False))


def code_audit(baseline, output):
    baseline, output = safe(baseline), safe(output)
    spec = json.loads(baseline.read_text(encoding="utf-8"))
    changes = [p for p, digest in spec["paths"].items()
               if not (ROOT / p).is_file() or file_sha(ROOT / p) != digest]
    listed = subprocess.check_output(["rg", "--files", "scripts", "tinylm", "-g", "*.py"], cwd=ROOT, text=True).splitlines()
    new = sorted(set(listed) - set(spec["paths"]))
    unexpected = sorted(set(new) - set(spec["allowed_root_new_code"]))
    report = {"schema": VERSION, "existing_files": len(spec["paths"]),
              "existing_changed": changes, "new_files": new, "unexpected_new": unexpected,
              "pass": not changes and not unexpected,
              "isolation": "instruction/allowlist and hash audit; NOT per-agent OS access control"}
    write_json(output, report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    scan = sub.add_parser("census")
    scan.add_argument("--source", type=Path, default=TRAIN)
    scan.add_argument("--tokenizer", type=Path, default=TOKENIZER)
    scan.add_argument("--output", type=Path, required=True)
    scan.add_argument("--max-ids", type=int, default=0)
    scan.add_argument("--seconds", type=float, default=1200)
    review = sub.add_parser("import-reviews")
    review.add_argument("--packet", type=Path, required=True)
    review.add_argument("--response", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    merge = sub.add_parser("merge-response")
    merge.add_argument("--original", type=Path, required=True)
    merge.add_argument("--revision", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--key", choices=("id", "source_index"), required=True)
    draft = sub.add_parser("import-drafts")
    draft.add_argument("--packet", type=Path, required=True)
    draft.add_argument("--response", type=Path, required=True)
    draft.add_argument("--output", type=Path, required=True)
    draft.add_argument("--kind", choices=("sft", "nonsft"), required=True)
    render = sub.add_parser("render-review")
    render.add_argument("--base", type=Path, default=BASE)
    render.add_argument("--output", type=Path, required=True)
    readable = sub.add_parser("render-drafts")
    readable.add_argument("--directory", type=Path, required=True)
    readable.add_argument("--output", type=Path, required=True)
    audit = sub.add_parser("code-audit")
    audit.add_argument("--baseline", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "census":
        if args.max_ids < 0:
            parser.error("max IDs cannot be negative")
        census(args.source, args.tokenizer, args.output, max_ids=args.max_ids, seconds=args.seconds)
    elif args.mode == "import-reviews":
        import_reviews(args.packet, args.response, args.output)
    elif args.mode == "merge-response":
        merge_response(args.original, args.revision, args.output, args.key)
    elif args.mode == "import-drafts":
        import_drafts(args.packet, args.response, args.output, kind=args.kind)
    elif args.mode == "render-review":
        render_review(args.base, args.output)
    elif args.mode == "render-drafts":
        render_drafts(args.directory, args.output)
    else:
        code_audit(args.baseline, args.output)


if __name__ == "__main__":
    main()
