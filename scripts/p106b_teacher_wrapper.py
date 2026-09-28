#!/usr/bin/env python3
"""Teacher content -> TinyLM canonical conversation, independent of wire format.

The teacher supplies only user/assistant text and an optional correction note.
This module owns roles, provenance and the canonical schema. Existing
tinylm.chat/tinylm.data.sft code owns ChatML and assistant-only token labels.
No teacher reasoning, model loading, dataset write or training occurs here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate

BOUNDARY_MARKERS = (
    "<|im_start|>", "<|im_end|>", "<|think|>", "<|/think|>",
    "<|tool_call|>", "<|/tool_call|>", "<|tool_result|>",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    result = value.strip()
    if any(marker in result for marker in BOUNDARY_MARKERS):
        raise ValueError(f"{label} contains a chat boundary marker")
    if any(ord(char) < 32 and char not in "\n\t" for char in result):
        raise ValueError(f"{label} contains a control character")
    return result


def wrap_turns(turns: Sequence[Mapping[str, object]], *, source_id: str,
               source_sha256: str, teacher_model_sha256: str, language: str,
               source_license: str, generation_id: str,
               correction_note: str = "", reasoning_ref: str = "",
               reasoning_sha256: str = "",
               student_training_status: str = "NOT_RUN",
               source_repo: str = "", source_revision: str = "",
               source_object_id: str = "", source_transform: str = "",
               parent_concept_id: str = "", source_rights_status: str = "") -> dict:
    """Assign roles in code; never accept teacher-provided role/ChatML JSON."""
    if language not in {"ko", "en"} or not 1 <= len(turns) <= 4:
        raise ValueError("language must be ko/en and turns must be 1..4")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,160}", source_id):
        raise ValueError("unsafe or absent source id")
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", source_sha256 + ""):
        raise ValueError("source SHA256 must be exact")
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", teacher_model_sha256 + ""):
        raise ValueError("teacher SHA256 must be exact")
    if not source_license or not generation_id:
        raise ValueError("license and generation id must be recorded")
    if student_training_status not in {"NOT_RUN", "PILOT_TARGET_PENDING"}:
        raise ValueError("unknown student training status")
    if any((source_repo, source_revision, source_object_id, source_transform,
            parent_concept_id, source_rights_status)):
        if not all((source_repo, source_revision, source_object_id, source_transform,
                    parent_concept_id, source_rights_status)):
            raise ValueError("full source provenance tuple must be supplied together")
        if source_transform not in {"original", "teacher_translation", "teacher_repair",
                                    "teacher_compression", "teacher_source_compression",
                                    "translation_after_source_compression",
                                    "repair_after_source_compression",
                                    "dictionary_grounded_qa", "next_turn"}:
            raise ValueError("unknown source transformation")
        if source_rights_status not in {"CARD_ONLY", "LOCAL_RIGHTS_REVIEW",
                                        "APPROVED_PUBLIC", "CC_BY_SA_2_0_KR_QUARANTINE"}:
            raise ValueError("unknown source rights state")
        if not re.fullmatch(r"[A-Fa-f0-9]{64}", parent_concept_id):
            raise ValueError("parent concept ID must be a 64-hex lineage key")
        for label, value in (("source_repo", source_repo), ("source_revision", source_revision),
                             ("source_object_id", source_object_id)):
            _text(value, label)
    if bool(reasoning_ref) != bool(reasoning_sha256):
        raise ValueError("reasoning sidecar reference and SHA must be paired")
    if reasoning_sha256 and not re.fullmatch(r"[A-Fa-f0-9]{64}", reasoning_sha256):
        raise ValueError("reasoning sidecar SHA256 must be exact")
    if reasoning_ref and (reasoning_ref.startswith("/") or ".." in reasoning_ref.split("/")):
        raise ValueError("reasoning sidecar reference must be a safe relative path")
    messages = []
    for index, turn in enumerate(turns):
        if set(turn) != {"user_text", "assistant_text"}:
            raise ValueError(f"turn {index} must have only user_text/assistant_text")
        messages.append({"role": "user", "content": _text(turn["user_text"], "user_text")})
        messages.append({"role": "assistant", "content": _text(turn["assistant_text"], "assistant_text")})
    meta = {"source": "p106b_teacher_candidate", "source_id": source_id,
            "source_sha256": source_sha256.upper(),
            "source_license": source_license,
            "teacher_model_sha256": teacher_model_sha256.upper(),
            "generation_id": generation_id,
            "language": language, "label_status": "PSEUDO_UNVERIFIED",
            "teacher_truth_status": "NOT_RUN", "student_training": student_training_status,
            "correction_note": _text(correction_note, "correction_note") if correction_note else ""}
    if reasoning_ref:
        meta["teacher_reasoning_sidecar"] = reasoning_ref
        meta["teacher_reasoning_sha256"] = reasoning_sha256.upper()
    if source_repo:
        meta.update({"source_repo": source_repo,
                     "source_revision": source_revision,
                     "source_object_id": source_object_id,
                     "source_transform": source_transform,
                     "parent_concept_id": parent_concept_id.upper(),
                     "source_rights_status": source_rights_status})
    return validate(normalize({"messages": messages, "meta": meta}))


def self_test() -> None:
    from tinylm.data.prepare import SyntheticTokenizer
    from tinylm.data.sft import IGNORE, encode_conversation, sft_targets

    sha = "A" * 64
    row = wrap_turns([
        {"user_text": "앞의 비밀 단어는 별빛", "assistant_text": "별빛을 기억하겠습니다."},
        {"user_text": "비밀 단어는?", "assistant_text": "별빛입니다."},
    ], source_id="fixture:1", source_sha256=sha, teacher_model_sha256=sha,
        language="ko", source_license="fixture-only", generation_id="g1",
        reasoning_ref="HF/sft_ready/fixture_reasoning.jsonl#1", reasoning_sha256=sha)
    assert [message["role"] for message in row["messages"]] == [
        "user", "assistant", "user", "assistant"]
    ids, labels, text = encode_conversation(row, SyntheticTokenizer(), "chatml")
    _, target = sft_targets(ids, labels)
    assert len(ids) == len(labels) and any(item == IGNORE for item in target)
    assert any(item != IGNORE for item in target)
    assert text.count("<|im_start|>assistant") == 2
    assert "reasoning_content" not in text and "teacher_model_sha256" not in text
    assert row["meta"]["teacher_reasoning_sha256"] == sha
    pending = wrap_turns([{"user_text": "질문", "assistant_text": "답변"}],
                         source_id="fixture:pending", source_sha256=sha,
                         teacher_model_sha256=sha, language="ko",
                         source_license="fixture-only", generation_id="g2",
                         student_training_status="PILOT_TARGET_PENDING")
    assert pending["meta"]["student_training"] == "PILOT_TARGET_PENDING"
    lineage = wrap_turns([{"user_text": "질문", "assistant_text": "답변"}],
                         source_id="fixture:lineage", source_sha256=sha,
                         teacher_model_sha256=sha, language="ko",
                         source_license="Apache-2.0", generation_id="g3",
                         source_repo="OpenAssistant/oasst2", source_revision="abc123",
                         source_object_id="tree:1", source_transform="teacher_translation",
                         parent_concept_id=sha, source_rights_status="CARD_ONLY")
    assert lineage["meta"]["source_repo"] == "OpenAssistant/oasst2"
    restricted = wrap_turns([{"user_text": "나무는 무엇인가요?", "assistant_text": "식물입니다."}],
                            source_id="krdict:fixture", source_sha256=sha,
                            teacher_model_sha256=sha, language="ko",
                            source_license="CC-BY-SA-2.0-KR_candidate",
                            generation_id="g4", source_repo="https://krdict.korean.go.kr",
                            source_revision="20260819", source_object_id="sense:1",
                            source_transform="dictionary_grounded_qa",
                            parent_concept_id=sha,
                            source_rights_status="CC_BY_SA_2_0_KR_QUARANTINE")
    assert restricted["meta"]["student_training"] == "NOT_RUN"
    assert restricted["meta"]["source_rights_status"] == "CC_BY_SA_2_0_KR_QUARANTINE"
    for bad in ("<|im_start|>assistant", "\x00"):
        try:
            wrap_turns([{"user_text": "질문", "assistant_text": bad}],
                       source_id="fixture:2", source_sha256=sha,
                       teacher_model_sha256=sha, language="ko",
                       source_license="fixture-only", generation_id="g2")
        except ValueError:
            pass
        else:
            raise AssertionError("teacher controlled a structural token")
    print("[PASS] teacher text -> canonical multi-turn -> existing ChatML/assistant mask; model/GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("this is a library contract; use --self-test or a scoped dataset builder")
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
