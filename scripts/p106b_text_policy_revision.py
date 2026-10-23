#!/usr/bin/env python3
"""Write-once text revisions of sealed review packets; no model/training.

Only declared source spans and unambiguous message targets may change.
Human-authored overrides are input data, not universal semantic filters.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import file_sha, safe, sha, write_json
from scripts.p106b_shards import ShardWriter, verify

BASE = ROOT / "data_cache/p106b_native_text_audit_v2_policy"
KINDS = {"ko_translation", "ko_rephrase", "en_rephrase"}


def apply_spans(original, changes):
    text = original
    for change in changes:
        span = change["source_span"]
        if not span or text.count(span) != 1:
            raise ValueError("source span absent or ambiguous")
        if change["action"] not in ("REMOVE", "MOVE_TO_PROSE"):
            raise ValueError("unknown source transform")
        if change["action"] == "REMOVE" and change["replacement"].strip():
            raise ValueError("REMOVE must not add content")
        text = text.replace(span, change["replacement"], 1)
    return text


def merge_messages(original, patch):
    """A partial role patch never replaces the entire conversation."""
    if [x["role"] for x in patch] == [x["role"] for x in original]:
        result, partial = copy.deepcopy(patch), False
    else:
        if not patch or len({x["role"] for x in patch}) != len(patch):
            raise ValueError("duplicate/empty partial message targets")
        result, partial = copy.deepcopy(original), True
        for change in patch:
            targets = [i for i, x in enumerate(original) if x["role"] == change["role"]]
            if len(targets) != 1:
                raise ValueError("partial role target absent or ambiguous")
            result[targets[0]] = copy.deepcopy(change)
    if ([x["role"] for x in result] != [x["role"] for x in original]
            or any(not isinstance(x["content"], str) or not x["content"].strip() for x in result)):
        raise ValueError("conversation roles/turns/text changed")
    return result, partial


def apply_override(raw, override):
    row = copy.deepcopy(raw)
    notes = override.get("notes", [])
    if "decision" in override:
        row["decision"] = override["decision"]
    if row["decision"] == "HOLD":
        row["changes"] = []
    for op in override.get("changes", []):
        target = row["changes"][op["index"]]
        if target["replacement"] != op["expected_replacement"]:
            raise ValueError("stale manual text override")
        for key in ("action", "replacement", "reason"):
            if key in op:
                target[key] = op[key]
    return row, notes


def main(base=BASE):
    base = safe(base)
    override_path = base / "root_policy_overrides.json"
    spec = json.loads(override_path.read_text(encoding="utf-8"))
    for name, digest in spec["input_sha256"].items():
        if file_sha(safe(base / name)) != digest:
            raise ValueError("manual review input SHA changed")
    if (base / "correction_report.json").exists():
        raise FileExistsError("revision already exists; choose a new version")
    packet = json.loads((base / "published21_packet.json").read_text(encoding="utf-8"))
    sources = {x["source"]["id"]: x["source"] for x in packet["documents"]}
    responses = json.loads((base / "published21_prose_review.json").read_text(encoding="utf-8"))
    if len(responses) != len(sources) or {x["id"] for x in responses} != set(sources):
        raise ValueError("page review coverage differs")
    pages, page_audit = [], []
    for raw in responses:
        source = sources[raw["id"]]
        original = source["text"]
        if sha(original) != source["sha256"]:
            raise ValueError("page source SHA differs")
        agent_expected = apply_spans(original, raw["changes"])
        whitespace_only = (agent_expected != raw["proposed_text"]
                           and agent_expected.split() == raw["proposed_text"].split())
        if agent_expected != raw["proposed_text"] and not whitespace_only:
            raise ValueError("undeclared non-whitespace edit in agent prose")
        row, notes = apply_override(raw, spec["page_overrides"].get(str(raw["id"]), {}))
        text = apply_spans(original, row["changes"])
        if row["decision"] != "REWRITE" and text != original:
            raise ValueError("held source must remain unchanged")
        pages.append({"id": row["id"], "source": source, "agent_decision": raw["decision"],
                      "root_decision": row["decision"], "text": text, "changes": row["changes"],
                      "root_notes": notes, "review_notes": row["review_notes"],
                      "source_time_context": "historical source; CURRENT not verified today",
                      "training_admission": "NOT_ADMITTED", "semantic_truth": "NOT_REVIEWED"})
        page_audit.append({"id": row["id"], "decision": row["decision"],
                           "declared_changes": len(row["changes"]),
                           "agent_undeclared_whitespace_ignored": whitespace_only})
    packet = json.loads((base / "sft_all180_packet.json").read_text(encoding="utf-8"))
    groups = {x["root_id"]: x for x in packet["sources"]}
    reviews = json.loads((base / "sft_all180_term_review.json").read_text(encoding="utf-8"))
    if len(reviews) != len(groups) or {x["root_id"] for x in reviews} != set(groups):
        raise ValueError("SFT review coverage differs")
    drafts, changed, partials = [], [], 0
    for review in reviews:
        source = groups[review["root_id"]]
        if source["source_index"] != review["source_index"]:
            raise ValueError("source identity changed")
        variants = {x["variant_kind"]: x for x in source["variants"]}
        patches = {x["variant_kind"]: x for x in review["patches"]}
        if (set(variants) != KINDS or len(source["variants"]) != 3
                or set(review["reviewed_variant_kinds"]) != KINDS
                or len(patches) != len(review["patches"]) or not set(patches) <= KINDS):
            raise ValueError("variant coverage/patch identity differs")
        for kind, old in variants.items():
            messages = copy.deepcopy(old["messages"])
            if kind in patches:
                messages, partial = merge_messages(messages, patches[kind]["messages"])
                partials += partial
                changed.append([source["source_index"], kind])
            if len(messages) != len(source["original_messages"]):
                raise ValueError("source conversation turn loss")
            drafts.append({"root_id": source["root_id"], "source_index": source["source_index"],
                           "variant_kind": kind, "original_messages": source["original_messages"],
                           "original_variant_messages": old["messages"], "messages": messages,
                           "revision_of": {k: old[k] for k in ("original_authoring_file", "original_row_index", "original_line_sha256")},
                           "term_review_decision": review["decision"], "issues": review["issues"],
                           "term_reference_pending": review["term_reference_pending"], "has_patch": kind in patches,
                           "status": "REVISED_DRAFT_NOT_TRAIN_READY", "semantic_review": "PENDING",
                           "training_admission": "NOT_ADMITTED"})
    lineage = {"manual_overrides_sha256": file_sha(override_path), "originals_preserved": True,
               "training_admission": "NOT_ADMITTED"}
    for folder, records in (("revised_pages", pages), ("revised_sft", drafts)):
        writer = ShardWriter(base / folder, "candidate")
        for row in records:
            writer.append(row)
        manifest = writer.close(lineage=dict(lineage, scope=folder))
        verify(base / folder, manifest)
    report = {"schema": "P106B_TEXT_POLICY_CORRECTION_V2", "page_sources_reviewed": len(pages),
              "page_rewrite_candidates": sum(x["root_decision"] == "REWRITE" for x in pages),
              "page_held": sum(x["root_decision"] == "HOLD" for x in pages), "page_exact_span_results": page_audit,
              "sft_source_roots_reviewed": len(groups), "sft_variants_reviewed": len(drafts),
              "sft_patch_candidate_roots": sum(x["decision"] == "PATCH_CANDIDATE" for x in reviews),
              "sft_variants_changed": len(changed), "sft_held_roots": [x["source_index"] for x in reviews if x["decision"] == "HOLD_REVIEW"],
              "partial_role_patches_applied_without_turn_loss": partials, "new_roots_authored": 0,
              "standard_term_183_verified": False, "full_corpus_preprocessing_complete": False,
              "original_writes": 0, "local_model_loads": 0, "training_runs": 0}
    write_json(base / "correction_report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "page_exact_span_results"}, ensure_ascii=False))


def render_reviews(base=BASE):
    """Readable text views of every published page and current SFT variant."""
    base = safe(base)
    loaded = {}
    for name in ("revised_pages", "revised_sft"):
        directory = base / name
        manifest = json.loads((directory / "candidate_shards_manifest.json").read_text(encoding="utf-8"))
        verify(directory, manifest)
        loaded[name] = [json.loads(line) for shard in manifest["shards"]
                        for line in (directory / shard["path"]).read_text(encoding="utf-8").splitlines()]
    parts = ["# 위키·웹 목록 문장화 후보 v2\n\n",
             "공개21건의 수리본이며 전체 코퍼스 정제 완료가 아닙니다. 원문 보존·학습 미채택입니다. 원문의 ‘현재’는 원자료 시점이며 오늘의 사실로 검증한 것이 아닙니다.\n\n"]
    for row in loaded["revised_pages"]:
        parts.extend([f"## 원문 {row['id']} — {row['root_decision']}\n\n",
                      "### 원문\n\n", row["source"]["text"],
                      "\n\n### 새 본문 후보 또는 보류 원형\n\n", row["text"],
                      "\n\n### 분리·문장화 근거\n\n"])
        for change in row["changes"]:
            parts.extend([change["reason"], "\n\n원문 구간:\n", change["source_span"],
                          "\n\n옮긴 문장:\n", change["replacement"] or "(본문에서 분리·원형 보존)", "\n\n"])
        parts.extend(["총괄 의견: ", " / ".join(row["root_notes"]) or row["review_notes"], "\n\n"])
    page_text = "".join(parts)
    parts = ["# SFT60원천·180변형 용어 보존 대조 v2\n\n",
             "기존180초안의 새 버전이며 새180개 추가 생산이 아닙니다. 학습 미채택이고 모든 사실·학술 용어 표준성을 검증한 것이 아닙니다. ‘광회전’의 표준성은 별도 확인 대기입니다.\n\n"]
    for row in loaded["revised_sft"]:
        parts.extend([f"## 원천 {row['source_index']} / {row['variant_kind']} — {'수정 후보' if row['has_patch'] else '기존 표현 유지'}\n\n",
                      "검토 상태: ", row["term_review_decision"], "\n\n"])
        for title, messages in (("원문 대화", row["original_messages"]),
                                ("수정 전 변형", row["original_variant_messages"]),
                                ("수정 후 후보", row["messages"])):
            parts.extend([f"### {title}\n\n"])
            for message in messages:
                content = message["content"]
                if not isinstance(content, str):
                    content = "".join(x["text"] for x in content)
                parts.extend(["질문: " if message["role"] == "user" else "답변: ", content, "\n\n"])
        for issue in row["issues"]:
            if issue["variant_kind"] == row["variant_kind"]:
                parts.extend(["검토 의견: ", issue["reason"], "\n\n"])
        if row["term_reference_pending"]:
            parts.extend(["용어 기준 확인 대기: ", str(row["term_reference_pending"]), "\n\n"])
    rendered = (("20261022_위키웹_목록문장화_정제후보_v2.md", page_text),
                ("20261022_SFT180변형_학술용어보존_대조_v2.md", "".join(parts)))
    for name, text in rendered:
        if len(text.encode("utf-8")) >= 20_000_000:
            raise ValueError("readable view exceeds20MB; split by source")
        output = safe(ROOT / "review_request" / name)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(text)
        print(json.dumps({"readable_review": str(output), "bytes": output.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
