#!/usr/bin/env python3
"""Root-owned, write-once text packets and strict Luna draft imports.

Workers read sealed text only. They never run or edit this analysis code.
Batch size is transport, never a claim that the whole corpus was processed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import (file_sha, plain_content, safe, sha,
    validate_variant_conversation, write_json)
from scripts.p106b_text_policy_revision import apply_spans
from scripts.p106b_shards import ShardWriter, verify

BASE = ROOT / "data_cache/p106b_text_work_20261022"
CANONICAL = ROOT / "HF/sft_ready/p090_public_v3_train.canonical.jsonl"
KINDS = ("ko_translation", "ko_rephrase", "en_rephrase")
LINE_EDIT_CONTRACT = "LF_LINE_RANGE_AND_BOUNDARY_ACK_V1"


def lf_lines(text):
    """Match numbered LF text views without interpreting bare CR as a line."""
    parts = text.split("\n")
    return [line + "\n" for line in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def apply_positioned_edits(original, changes):
    """Resolve exact declared line ranges; never search/guess a nearby span."""
    lines = lf_lines(original)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    resolved = []
    for change_index, change in enumerate(changes):
        pair = change.get("source_lines")
        if (not isinstance(pair, list) or len(pair) != 2
                or any(type(n) is not int for n in pair) or not 1 <= pair[0] <= pair[1] <= len(lines)
                or "source_span" in change):
            raise ValueError("exact 1-based inclusive LF line range required")
        first, last = lines[pair[0]-1].strip(), lines[pair[1]-1].strip()
        begin_raw, end_raw = change.get("source_start"), change.get("source_end")
        if not isinstance(begin_raw, str) or not isinstance(end_raw, str):
            raise ValueError("literal boundary acknowledgment strings required")
        # The contract compares trimmed line boundaries. Only trim the two
        # acknowledgments; source coordinates/bytes/replacement stay exact.
        begin, end = begin_raw.strip(), end_raw.strip()
        if (len(begin) > 160 or len(end) > 160
                or bool(begin) != bool(first) or bool(end) != bool(last)
                or not first.startswith(begin) or not last.endswith(end)):
            detail = dict(change_index=change_index, source_lines=pair,
                start_ack_matches=bool(begin) == bool(first) and first.startswith(begin),
                end_ack_matches=bool(end) == bool(last) and last.endswith(end),
                expected_start=first[:160], expected_end=last[-160:],
                supplied_start=begin[:160], supplied_end=end[-160:])
            raise ValueError("declared line boundary text differs; no fuzzy alignment; " +
                             json.dumps(detail, ensure_ascii=False, sort_keys=True))
        action, replacement = change.get("action"), change.get("replacement")
        if action not in ("REMOVE", "MOVE_TO_PROSE") or not isinstance(replacement, str):
            raise ValueError("known action and literal replacement required")
        if action == "REMOVE" and replacement.strip():
            raise ValueError("REMOVE must not add content")
        a, z = offsets[pair[0]-1], offsets[pair[1]]
        resolved.append(dict(start=a, end=z, replacement=replacement, source_lines=pair,
            offset_unit="UNICODE_CODEPOINT_END_EXCLUSIVE", line_range_unit="ONE_BASED_INCLUSIVE_LF",
            source_span_sha256=sha(original[a:z]), action=action,
            boundary_ack_whitespace_normalized=begin_raw != begin or end_raw != end,
            normalized_boundary_ack=dict(source_start=begin, source_end=end)))
    ordered = sorted(resolved, key=lambda row: row["start"])
    if any(a["end"] > z["start"] for a, z in zip(ordered, ordered[1:])):
        raise ValueError("source line ranges overlap")
    result = original
    for row in reversed(ordered):
        result = result[:row["start"]] + row["replacement"] + result[row["end"]:]
    return result, [{k:v for k,v in row.items() if k != "replacement"} for row in ordered]


def valid_array_prefix(text):
    """Return only complete strict JSON objects before the first syntax error.

    This is an explicit recovery aid, never the ordinary import parser.
    Broken trailing records are not repaired, guessed or treated as read.
    """
    index = len(text) - len(text.lstrip())
    if index >= len(text) or text[index] != "[":
        raise ValueError("explicit JSON array prefix required")
    index += 1
    decoder, rows = json.JSONDecoder(), []
    while True:
        while index < len(text) and text[index].isspace(): index += 1
        if index >= len(text) or text[index] == "]":
            return rows, index
        try:
            row, stop = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            return rows, index
        if not isinstance(row, dict):
            raise ValueError("only complete object records may be recovered")
        rows.append(row)
        index = stop
        while index < len(text) and text[index].isspace(): index += 1
        if index >= len(text) or text[index] == "]":
            return rows, index
        if text[index] != ",":
            return rows, index
        index += 1


def explicit_trailing_comma_repair(text):
    """Root opt-in for local author JSON; ordinary imports stay strict.

    Only commas outside quoted strings immediately before closing ]/} may be
    removed. No word, string escape, missing record or other syntax is guessed.
    """
    try:
        json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        raise ValueError("valid JSON needs ordinary import, not syntax repair")
    inside = escaped = False
    output, removed = [], []
    for index, char in enumerate(text):
        if inside:
            output.append(char)
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == '"': inside = False
            continue
        if char == '"': inside = True
        if char == ",":
            following = index + 1
            while following < len(text) and text[following] in " \t\r\n": following += 1
            if following < len(text) and text[following] in "]}":
                removed.append(index)
                continue
        output.append(char)
    if inside or not removed:
        raise ValueError("not a complete local JSON with trailing-comma-only repair")
    repaired = "".join(output)
    return json.loads(repaired), removed


def recover_responses(packet_path, original, directory, output):
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    raw = original.read_text(encoding="utf-8")
    try:
        json.loads(raw)
    except json.JSONDecodeError:
        pass
    else:
        raise ValueError("valid response needs ordinary import, not recovery")
    prefix, stopped = valid_array_prefix(raw)
    expected = [r["id"] for r in packet["documents"]]
    rows = {r["id"]: r for r in prefix}
    if len(rows) != len(prefix) or not set(rows) <= set(expected):
        raise ValueError("duplicate or foreign complete prefix records")
    missing = [ident for ident in expected if ident not in rows]
    expected_files = {str(ident) + ".json" for ident in missing}
    if {p.name for p in directory.iterdir()} != expected_files:
        raise ValueError("new text objects must exactly cover missing records")
    replacement_sha = {}
    for ident in missing:
        path = safe(directory / (str(ident) + ".json"))
        row = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(row, dict) or row.get("id") != ident:
            raise ValueError("replacement file ID differs")
        rows[ident] = row
        replacement_sha[path.name] = file_sha(path)
    write_json(output, [rows[ident] for ident in expected])
    receipt = dict(schema="EXPLICIT_JSON_PREFIX_RECOVERY_V1", original_sha256=file_sha(original),
        packet_sha256=file_sha(packet_path), strict_complete_prefix_records=len(prefix),
        stopped_at_character=stopped, newly_authored_record_ids=missing,
        replacement_sha256=replacement_sha, full_source_rows=len(expected),
        content_edits_to_prefix=0, output_sha256=file_sha(output),
        ordinary_source_span_validation="STILL_REQUIRED", training_admission="NOT_ADMITTED")
    write_json(output.with_suffix(".recovery_receipt.json"), receipt)
    return receipt


def source_rows():
    with CANONICAL.open("rb") as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            yield index, line, row


def issued_sft_sources(canonical_sha):
    """Dispatch history is not completion; never silently reissue held work."""
    issued = set()
    for path in sorted((BASE / "packets").glob("sft_*.json")):
        packet = json.loads(safe(path).read_text(encoding="utf-8"))
        if packet.get("canonical_sha256") != canonical_sha or not isinstance(packet.get("sources"), list):
            raise ValueError("issued SFT packet has different canonical lineage")
        for source in packet["sources"]:
            ident = source.get("source_index")
            if type(ident) is not int or ident < 0:
                raise ValueError("issued source index must be a nonnegative integer")
            issued.add(ident)
    return issued


def sft_packet(output, start, count):
    # The sealed inventory excludes the already authored 60 roots. Issued,
    # incomplete and triaged work stay reserved, not automatically retried.
    jobs = ROOT / "data_cache/p106b_native_text_audit_v2_policy/jobs/sft_canonical_en_jobs_v2_000000.jsonl"
    canonical_sha = file_sha(CANONICAL)
    issued = issued_sft_sources(canonical_sha)
    with jobs.open(encoding="utf-8") as stream:
        wanted = {r["source_index"] for line in stream
                  if (r := json.loads(line))["state"] == "NOT_AUTHORED"
                  and r["source_index"] >= start and r["source_index"] not in issued}
    selected = []
    for index, line, row in source_rows():
        if index not in wanted:
            continue
        selected.append(dict(source_index=index, source_id=row["meta"]["source_id"],
            root_id=sha("p090_public_v3:" + str(index)), source_split="train",
            source_line_sha256=hashlib.sha256(line.rstrip(b"\r\n")).hexdigest().upper(),
            messages=row["messages"], meta=row["meta"]))
        if len(selected) == count:
            break
    if not selected:
        raise ValueError("no new source selected")
    if file_sha(CANONICAL) != canonical_sha:
        raise ValueError("canonical changed while dispatching sources")
    packet = dict(schema="P106B_LUNA_SFT_TEXT_PACKET_V3", sources=selected,
        required_variants=KINDS, canonical_sha256=canonical_sha,
        corpus_scope="2821 metadata-English rows; source language still needs reading",
        previously_authored_roots=60, total_remaining_before_today=2761,
        issued_sources_excluded=len(issued),
        reissue_policy="Issued includes pending/held/incomplete work, not authored completion; explicit recovery required.",
        next_source_index=selected[-1]["source_index"] + 1,
        training_admission="NOT_ADMITTED", code_edit_permission=False)
    write_json(output, packet)
    return dict(packet=str(output), sources=len(selected), next_source_index=packet["next_source_index"])


def native_packet(output, start, count, language):
    original = ROOT / "data_cache/p106b_native_text_audit_v1_s1337/census_full/original"
    existing = json.loads((ROOT / "data_cache/p106b_native_text_audit_v2_policy/published21_packet.json").read_text())
    seen = {r["source"]["sha256"] for r in existing["documents"]}
    documents = []
    # Reservoir is already frozen by the full census, not a new full census.
    for name in ("background_000000.jsonl", "signal_candidates_000000.jsonl"):
        for line in (original / name).open(encoding="utf-8"):
            row = json.loads(line)
            index = row["eos_segment_index"]
            if index < start or row["sha256"] in seen:
                continue
            text = row["text"]
            korean = sum("가" <= c <= "힣" for c in text)
            if (language == "ko") != (korean >= 20):
                continue
            seen.add(row["sha256"])
            documents.append(dict(row, id=index))
    documents.sort(key=lambda r: r["eos_segment_index"])
    documents = documents[:count]
    if not documents:
        raise ValueError("selected reservoir text exhausted; do not call whole corpus complete")
    write_json(output, dict(schema="P106B_NATIVE_REVIEW_TEXT_PACKET_V2", documents=documents,
        source_scope="frozen 256-row reservoir from full census, not whole corpus cleaning",
        source_cache_sha256="6DB291329CB1562E127A2D753F879C8ED8D3AB46789A3EF2B4BC3C4258846138",
        language_selection=language, training_admission="NOT_ADMITTED", code_edit_permission=False))
    return dict(packet=str(output), sources=len(documents), next_source_index=documents[-1]["id"] + 1)


def native_full_packet(directory, output, start, count, language):
    """Continue beyond the small reservoir using exact original cache spans.

    KO prioritizes the user's body-list headings; EN uses the existing review
    queue. Neither selection label is a badness or semantic correctness gate.
    """
    from scripts.p106b_shards import verify
    from tokenizers import Tokenizer
    import numpy as np
    report_path = directory / "report.json"
    report_sha = file_sha(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("full_eos_pool_transformed") is not True or report.get("original_writes") != 0:
        raise ValueError("complete immutable format version required")
    source = safe(ROOT / report["source"])
    tokenizer = safe(ROOT / "data_cache/tok-ko-en-32768-chat32.json")
    if file_sha(source) != report["source_sha256"] or file_sha(tokenizer) != report["tokenizer_sha256"]:
        raise ValueError("original cache/tokenizer identity differs")
    tok = Tokenizer.from_file(str(tokenizer))
    seen = set()
    for path in (BASE / "packets").glob("native_*.json"):
        packet = json.loads(path.read_text(encoding="utf-8"))
        seen.update(r["sha256"] for r in packet.get("documents", []))
    published = json.loads((ROOT / "data_cache/p106b_native_text_audit_v2_policy/published21_packet.json").read_text())
    seen.update(r["source"]["sha256"] for r in published["documents"])
    manifest = report["manifests"]["review_queue"]
    verify(directory / "review_queue", manifest)
    documents = []
    examined = 0
    with source.open("rb") as raw:
        for shard in manifest["shards"]:
            with (directory / "review_queue" / shard["path"]).open(encoding="utf-8") as positions:
                for line in positions:
                    position = json.loads(line)
                    ident = position["eos_segment_index"]
                    if ident < start or position["original_text_sha256"] in seen:
                        continue
                    if language == "ko" and "structured_list_relation_needs_source_reading" not in position["review_reasons"]:
                        continue
                    a, z = position["cache_segment_ids"]
                    raw.seek(a * 2)
                    buffer = raw.read((z-a) * 2)
                    if len(buffer) != (z-a) * 2:
                        raise ValueError("original cache span shortened")
                    text = tok.decode(np.frombuffer(buffer, dtype="<u2").tolist(), skip_special_tokens=False)
                    if sha(text) != position["original_text_sha256"]:
                        raise ValueError("original text/source position differs")
                    examined += 1
                    if (language == "ko") != (sum("가" <= c <= "힣" for c in text) >= 20):
                        continue
                    seen.add(sha(text))
                    documents.append(dict(id=ident, eos_segment_index=ident, text=text, sha256=sha(text),
                        cache_segment_ids=[a,z], review_reasons=position["review_reasons"], line_count=len(lf_lines(text))))
                    if len(documents) == count:
                        break
            if len(documents) == count:
                break
    if not documents:
        raise ValueError("selected full-review scope exhausted; not whole semantic cleaning complete")
    if file_sha(report_path) != report_sha or file_sha(source) != report["source_sha256"]:
        raise ValueError("candidate manifest or original cache changed during selection")
    write_json(output, dict(schema="P106B_NATIVE_REVIEW_TEXT_PACKET_V5", documents=documents,
        source_scope="sequential full review queue; KO body-list priority / EN structure candidates; not a uniform quality estimate",
        source_cache_sha256=report["source_sha256"], full_format_report_sha256=report_sha,
        language_selection=language, examined_eligible_positions=examined,
        next_source_index=documents[-1]["id"]+1, edit_contract=LINE_EDIT_CONTRACT,
        training_admission="NOT_ADMITTED", code_edit_permission=False))
    return dict(packet=str(output), sources=len(documents), next_source_index=documents[-1]["id"]+1)


def import_packet(packet_path, response_path, output, kind):
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if output.exists():
        raise FileExistsError("write-once output exists")
    key = "source_index" if kind == "sft" else "id"
    sources = {r[key]: r for r in packet["sources" if kind == "sft" else "documents"]}
    if response_path.is_dir():
        expected_files = {str(ident) + ".json" for ident in sources}
        if {p.name for p in response_path.iterdir()} != expected_files:
            raise ValueError("response objects must exactly cover the packet")
        response, files = [], {}
        for ident in sources:
            path = safe(response_path / (str(ident) + ".json"))
            row = json.loads(path.read_text(encoding="utf-8"))
            if row.get(key) != ident:
                raise ValueError("response file name and source identity differ")
            response.append(row)
            files[path.name] = file_sha(path)
        response_identity = dict(response_sha256=sha(json.dumps(files, sort_keys=True)),
            response_identity_kind="SORTED_FILENAME_TO_FILE_SHA256_BUNDLE", response_files=files)
    else:
        response = json.loads(response_path.read_text(encoding="utf-8"))
        response_identity = dict(response_sha256=file_sha(response_path), response_identity_kind="FILE_BYTES")
    if (not isinstance(response, list)
            or any(not isinstance(r, dict) or type(r.get(key)) is not int for r in response)
            or len(response) != len(sources)
            or {r[key] for r in response} != set(sources)):
        raise ValueError("missing, duplicate or foreign source IDs")
    if kind == "sft" and file_sha(CANONICAL) != packet["canonical_sha256"]:
        raise ValueError("canonical input changed")
    originals = {i: (line, row) for i, line, row in source_rows() if i in sources} if kind == "sft" else {}
    rows, held, triage_only = [], [], []
    unchanged_variants, distinct_changed = 0, set()
    for r in response:
        source = sources[r[key]]
        if kind == "sft":
            line, canonical = originals[r[key]]
            if (hashlib.sha256(line.rstrip(b"\r\n")).hexdigest().upper() != source["source_line_sha256"]
                    or canonical["messages"] != source["messages"]
                    or ("meta" in source and source["meta"] != canonical.get("meta", {}))
                    or any(k in r and r[k] != source[k] for k in ("source_id", "root_id"))):
                raise ValueError("source identity or conversation changed")
            source_meta = canonical.get("meta", {})
            allowed = source_meta.get("supervised_assistant_turns")
            assistant_count = sum(m["role"] == "assistant" for m in canonical["messages"])
            if allowed is not None and (not isinstance(allowed, list) or not allowed
                    or any(type(i) is not int or not 1 <= i <= assistant_count for i in allowed)
                    or len(set(allowed)) != len(allowed)):
                raise ValueError("invalid explicit source assistant supervision allowlist")
            variants, reason = r.get("variants"), r.get("triage_reason")
            if not isinstance(variants, list) or not isinstance(reason, str):
                raise ValueError("variants array and literal triage_reason required")
            original = [dict(role=m["role"], content=plain_content(m["content"])) for m in source["messages"]]
            if not variants:
                if not reason.strip():
                    raise ValueError("triage-only source needs an explicit nonempty reason")
                held.append(r[key])
                triage_only.append(dict(source_index=r[key], source_id=source["source_id"],
                    root_id=source["root_id"], original_messages=original,
                    source_line_sha256=source["source_line_sha256"], source_metadata=dict(source_meta),
                    triage_reason=reason, authored_variant_count=0,
                    classification="NOT_AUTHORED_TRIAGE_ONLY", semantic_review="PENDING",
                    training_admission="NOT_ADMITTED"))
                continue
            if (len(variants) != 3 or any(not isinstance(v, dict) for v in variants)
                    or {v.get("kind") for v in variants} != set(KINDS)):
                raise ValueError("three complete variants required")
            for variant in variants:
                messages = validate_variant_conversation(original, variant)
                unchanged = messages == original
                unchanged_variants += int(unchanged)
                if not unchanged:
                    distinct_changed.add((r[key], json.dumps(messages, ensure_ascii=False, sort_keys=True)))
                rows.append(dict(source_index=r[key], source_id=source["source_id"], root_id=source["root_id"],
                    original_messages=original, messages=messages, variant_kind=variant["kind"],
                    source_line_sha256=source["source_line_sha256"], source_split="train",
                    requested_language="en" if variant["kind"] == "en_rephrase" else "ko",
                    language="UNVERIFIED", content_language_review="PENDING",
                    identical_to_original_conversation=unchanged,
                    source_metadata=dict(source_meta),
                    meta=dict(source_meta, language="UNVERIFIED",
                        requested_language="en" if variant["kind"] == "en_rephrase" else "ko",
                        content_language_review="PENDING", training_admission="NOT_ADMITTED"),
                    supervision_contract="INHERITED_EXPLICIT_ALLOWLIST" if allowed is not None else "TURN_MASK_REVIEW_REQUIRED",
                    supervision_scope="Conversation preservation does not certify every assistant turn as a correct target.",
                    triage_reason=r["triage_reason"], training_admission="NOT_ADMITTED",
                    semantic_review="PENDING", author_model="gpt-6-luna", reasoning_effort="max"))
            if r["triage_reason"]:
                held.append(r[key])
        else:
            if sha(source["text"]) != source["sha256"]:
                raise ValueError("native source SHA changed")
            if "source_sha256" in r and r["source_sha256"] != source["sha256"]:
                raise ValueError("worker source acknowledgment differs from this ID's sealed original")
            if r["decision"] not in ("KEEP", "REWRITE", "HOLD"):
                raise ValueError("unknown text review decision")
            if packet.get("edit_contract") == LINE_EDIT_CONTRACT:
                text, resolved = apply_positioned_edits(source["text"], r["changes"])
                r = dict(r, root_resolved_source_ranges=resolved)
            else:
                text = apply_spans(source["text"], r["changes"])
            if "proposed_text" in r and text != r["proposed_text"]:
                raise ValueError("undeclared edit outside exact source spans")
            if r["decision"] != "REWRITE" and text != source["text"]:
                raise ValueError("KEEP/HOLD must preserve original")
            if r["decision"] == "HOLD":
                held.append(r[key])
            r = dict(r, proposed_text=text, reconstructed_from_exact_spans=True)
            rows.append(dict(source=source, draft=r, training_admission="NOT_ADMITTED",
                             semantic_truth="UNVERIFIED"))
    output.mkdir(parents=True)
    lineage = dict(packet_sha256=file_sha(packet_path), **response_identity,
                   training_admission="NOT_ADMITTED", kind=kind)
    if rows:
        writer = ShardWriter(output, "authoring" if kind == "sft" else "review")
        for row in rows:
            writer.append(row)
        manifest = writer.close(lineage=lineage)
        verify(output, manifest)
    if triage_only:
        triage_writer = ShardWriter(output, "triage")
        for row in triage_only:
            triage_writer.append(row)
        triage_manifest = triage_writer.close(lineage=lineage)
        verify(output, triage_manifest)
    report = dict(schema="P106B_TEXT_WORK_IMPORT_V5", source_rows=len(sources), output_rows=len(rows),
        held_source_ids=held, source_and_turns_preserved=True, semantic_review="PENDING", **lineage)
    report.update(code_sha256={str(path.relative_to(ROOT)): file_sha(path) for path in (
        Path(__file__), ROOT / "scripts/p106b_native_text_audit.py", ROOT / "scripts/p106b_text_policy_revision.py", ROOT / "scripts/p106b_shards.py")},
        source_identity_policy="Source metadata belongs to sealed packet; supplied IDs must match exactly, omitted copied hashes are resolved by source index.")
    if kind == "sft":
        report.update(unchanged_variant_rows=unchanged_variants,
            changed_variant_rows=len(rows) - unchanged_variants,
            distinct_changed_source_conversations=len(distinct_changed),
            authored_source_rows=len(rows) // 3,
            triage_only_source_rows=len(triage_only),
            triage_only_source_ids=[r["source_index"] for r in triage_only],
            triage_manifest="triage_shards_manifest.json" if triage_only else None,
            language_quota_eligible=False,
            language_scope="Requested language is not a verified property; unchanged/held drafts are not new translations.")
    write_json(output / "report.json", report)
    return report


def visible_review_text(text):
    """Escape only the human view; original source/draft bytes stay in shards."""
    counts = {}
    parts = []
    for char in text:
        code = ord(char)
        if code <= 8 or code in (11, 12) or 14 <= code <= 31:
            label = f"U+{code:04X}"
            counts[label] = counts.get(label, 0) + 1
            parts.append("[" + label + "]")
        else:
            parts.append(char)
    if not counts:
        return text, counts
    note = ("표시 안내: 원문·후보의 인쇄 불가 제어문자는 [U+0002] 같은 표기로 보입니다. "
            "이는 출력 전용 표현이며 실제 원문·후보의 shard 바이트와 SHA는 변경하지 않습니다.\n\n")
    return note + "".join(parts), counts


def render_review(directory, output):
    stem = next((name for name in ("authoring", "review", "triage")
                 if (directory / (name + "_shards_manifest.json")).exists()), None)
    if stem is None:
        raise FileNotFoundError("no complete authoring/review/triage manifest")
    manifest = json.loads((directory / (stem + "_shards_manifest.json")).read_text(encoding="utf-8"))
    verify(directory, manifest)
    parts = ["# 원문과 정제·번역 후보 검토\n\n",
             "모든 후보는 미채택·의미 검토 대기입니다. 보류는 불량 확정이 아니며, 구조 검산은 정답성 보증이 아닙니다.\n\n"]
    seen = set()
    def messages(rows):
        for row in rows:
            label = {"user": "질문", "assistant": "답변", "system": "대화 조건"}.get(row["role"], row["role"])
            parts.extend([label + ":\n", row["content"], "\n\n"])
    for shard in (manifest["shards"] if stem != "triage" else []):
        for line in (directory / shard["path"]).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if stem == "authoring":
                ident = row["source_index"]
                if ident not in seen:
                    seen.add(ident)
                    parts.extend([f"\n## 원천 {ident}\n\n검토 사유: ", row["triage_reason"] or "의미 검토 대기",
                                  "\n\n### 원문 대화\n\n"])
                    messages(row["original_messages"])
                label = {"ko_translation": "한국어 번역", "ko_rephrase": "한국어 문장 재구성", "en_rephrase": "영어 문장 재구성"}[row["variant_kind"]]
                parts.append("\n### " + label + "\n\n")
                messages(row["messages"])
            elif stem == "review":
                source, draft = row["source"], row["draft"]
                note = next((draft.get(key) for key in ("review_notes", "reason")
                             if isinstance(draft.get(key), str) and draft[key].strip()),
                            "상위 검토 사유 미기재 — 원문과 변경별 근거를 확인해 주세요.")
                parts.extend([f"\n## 원문 구간 {source['id']} / {draft['decision']}\n\n",
                              note, "\n\n### 원문\n\n", source["text"],
                              "\n\n### 정제 후보\n\n", draft["proposed_text"], "\n\n"])
                for change in draft["changes"]:
                    reason = change.get("reason")
                    if not isinstance(reason, str) or not reason.strip():
                        reason = "변경별 사유 미기재 — 위 검토 사유를 확인해 주세요."
                    parts.extend(["변경 근거: ", reason, "\n\n"])
    triage_path = directory / "triage_shards_manifest.json"
    if triage_path.exists():
        triage_manifest = json.loads(triage_path.read_text(encoding="utf-8"))
        verify(directory, triage_manifest)
        for shard in triage_manifest["shards"]:
            for line in (directory / shard["path"]).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                parts.extend([f"\n## 원천 {row['source_index']} / 작성하지 않고 보류\n\n",
                    "새 변형: 0개. 보류 사유: ", row["triage_reason"], "\n\n### 원문 대화\n\n"])
                messages(row["original_messages"])
    text, display_controls = visible_review_text("".join(parts))
    if len(text.encode("utf-8")) >= 20_000_000:
        raise ValueError("review text exceeds20MB; split by source groups")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(text)
    return dict(output=str(output), bytes=len(text.encode("utf-8")), training_admission="NOT_ADMITTED",
                display_control_counts=display_controls, source_and_candidate_bytes_modified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("sft-packet", "native-packet", "import", "render-input", "render-review", "recover-responses"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--count", type=int, default=16)
    p.add_argument("--language", choices=("ko", "en"), default="ko")
    p.add_argument("--packet", type=Path)
    p.add_argument("--response", type=Path)
    p.add_argument("--kind", choices=("sft", "native"))
    p.add_argument("--directory", type=Path)
    p.add_argument("--original", type=Path)
    a = p.parse_args()
    if not 1 <= a.count <= 128:
        p.error("packet transport size must be 1..128, not total work quota")
    output = safe(a.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if a.mode == "sft-packet":
        result = sft_packet(output, a.start, a.count)
    elif a.mode == "native-packet":
        result = (native_full_packet(safe(a.directory), output, a.start, a.count, a.language)
                  if a.directory else native_packet(output, a.start, a.count, a.language))
    elif a.mode == "recover-responses":
        if not a.packet or not a.original or not a.directory:
            p.error("recovery requires exact packet/original/directory")
        result = recover_responses(safe(a.packet), safe(a.original), safe(a.directory), output)
    elif a.mode == "render-review":
        if not a.directory:
            p.error("render-review requires exact imported --directory")
        result = render_review(safe(a.directory), output)
    elif a.mode == "render-input":
        if not a.packet:
            p.error("render-input requires exact --packet")
        data = json.loads(safe(a.packet).read_text(encoding="utf-8"))
        output.mkdir(exist_ok=False)
        for row in data["documents"]:
            text = row["text"]
            if len(text.encode("utf-8")) >= 20_000_000:
                raise ValueError("individual source text needs smaller text spans")
            with (output / (str(row["id"]) + ".txt")).open("x", encoding="utf-8") as stream:
                stream.write(text)
            if data.get("edit_contract") == LINE_EDIT_CONTRACT:
                with (output / (str(row["id"]) + ".lines.txt")).open("x", encoding="utf-8") as stream:
                    stream.write("".join(f"{i}\t{line}" for i, line in enumerate(lf_lines(text),1)))
        result = dict(output=str(output), documents=len(data["documents"]),
                      packet_sha256=file_sha(safe(a.packet)), original_text_preserved=True)
        write_json(output / "manifest.json", result)
    else:
        if not a.packet or not a.response or not a.kind:
            p.error("import requires packet/response/kind")
        result = import_packet(safe(a.packet), safe(a.response), output, a.kind)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
