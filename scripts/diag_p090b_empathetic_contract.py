#!/usr/bin/env python3
"""Read-only public Korean multi-turn structural gate; no model or output files."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "HF" / "sft_sources" / "p090_empathetic_ko_9847cd2" / "Empathetic_data.jsonl"
SOURCE_SHA256 = "BC2B24FBEE11782071A9F84FBCEE615721F729ED31A01103E6755F80F9BC80C8"
TOKENIZER = ROOT / "data_cache" / "tok-ko-en-32768.json"
TOKENIZER_SHA256 = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"


def restore(row: dict, index: int) -> dict:
    """Restore only unambiguous multi_2/3 rows into canonical roles."""
    from tinylm.chat.canonical import normalize, validate
    if not isinstance(row, dict) or row.get("type") not in ("multi_2", "multi_3"):
        raise ValueError("unsupported_type")
    instruction, answer = row.get("instruction"), row.get("output")
    if not isinstance(instruction, str) or not isinstance(answer, str) or not answer.strip():
        raise ValueError("missing_text")
    if re.search("(?m)^(질문|답변):", answer):
        raise ValueError("ambiguous_final_answer")
    turns = 2 if row["type"] == "multi_2" else 3
    markers = list(re.finditer("(?m)^(질문|답변):", instruction))
    expected = ["질문", "답변"] * (turns - 1) + ["질문"]
    if not markers or markers[0].start() != 0 or [m.group(1) for m in markers] != expected:
        raise ValueError("marker_sequence")
    values = [instruction[m.end():markers[i + 1].start() if i + 1 < len(markers)
                          else len(instruction)].strip()
              for i, m in enumerate(markers)]
    if any(not value for value in values):
        raise ValueError("empty_turn")
    messages = [{"role": "user" if marker == "질문" else "assistant", "content": value}
                for marker, value in zip(expected, values)]
    messages.append({"role": "assistant", "content": answer.strip()})
    source_id = hashlib.sha256((SOURCE_SHA256 + ":" + str(index)).encode()).hexdigest()
    return validate(normalize({"messages": messages, "meta": {
        "source": "empathetic_ko", "source_id": source_id,
        "source_revision": "9847cd2c7d7634c9523d36cd9c1d377ea354eac9",
        "source_license": "Apache-2.0", "license_evidence": "card_only",
        "language": "ko", "raw_type": row["type"],
        "raw_source": str(row.get("source", "")), "raw_row_index_zero_based": index,
    }}))


def audit() -> dict:
    from tokenizers import Tokenizer
    from tinylm.data.sft import IGNORE, encode_conversation, sft_targets
    if SOURCE.is_symlink() or not SOURCE.is_file():
        raise ValueError("pinned public source missing or linked")
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() != SOURCE_SHA256:
        raise ValueError("pinned public source SHA differs")
    if TOKENIZER.is_symlink() or not TOKENIZER.is_file():
        raise ValueError("pinned legacy tokenizer missing or linked")
    if hashlib.sha256(TOKENIZER.read_bytes()).hexdigest().upper() != TOKENIZER_SHA256:
        raise ValueError("pinned legacy tokenizer SHA differs")
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    totals: Counter[str] = Counter()
    accepted: Counter[str] = Counter()
    eligible: Counter[str] = Counter()
    too_long: Counter[str] = Counter()
    empty_mask: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    rejected_indices: dict[str, list[int]] = {}
    first_prompts: Counter[str] = Counter()
    ranked: dict[str, list[tuple[str, int]]] = {"multi_2": [], "multi_3": []}
    url_rows = at_sign_rows = target_tokens = serialized_tokens = 0
    with SOURCE.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            kind = str(row.get("type"))
            totals[kind] += 1
            if kind not in ranked:
                continue
            try:
                conv = restore(row, index)
            except ValueError as exc:
                reason = str(exc)
                rejected[reason] += 1
                rejected_indices.setdefault(reason, [])
                if len(rejected_indices[reason]) < 20:
                    rejected_indices[reason].append(index)
                continue
            accepted[kind] += 1
            texts = [block["text"] for message in conv["messages"]
                     for block in message["content"] if block["type"] == "text"]
            first_key = " ".join(unicodedata.normalize("NFKC", texts[0]).casefold().split())
            first_prompts[first_key] += 1
            joined = " ".join(texts)
            url_rows += int("http://" in joined or "https://" in joined)
            at_sign_rows += int("@" in joined)
            ids, labels, _ = encode_conversation(conv, tokenizer, "chatml")
            _, targets = sft_targets(ids, labels)
            if len(ids) - 1 > 1024:
                too_long[kind] += 1
                continue
            count = sum(value != IGNORE for value in targets)
            if count < 1:
                empty_mask[kind] += 1
                continue
            eligible[kind] += 1
            target_tokens += count
            serialized_tokens += len(targets)
            rank = hashlib.sha256(f"{SOURCE_SHA256}:{index}".encode()).hexdigest()
            ranked[kind].append((rank, index))
    expected = {"single": 8094, "multi_2": 3812, "multi_3": 14756}
    if dict(totals) != expected:
        raise ValueError("pinned source type counts differ from prior audit")
    samples = {kind: [index for _, index in sorted(rows)[:50]]
               for kind, rows in ranked.items()}
    structural = "PASS" if not rejected else "PARTIAL"
    mask_gate = "PASS" if not empty_mask and all(eligible[k] >= 50 for k in ranked) else "PARTIAL"
    return {"schema": "P090B_EMPATHETIC_KO_AUDIT_V1",
            "source_sha256": SOURCE_SHA256, "tokenizer_sha256": TOKENIZER_SHA256,
            "raw_type_counts": dict(totals), "accepted_multi": dict(accepted),
            "eligible_multi": dict(eligible), "too_long_rows": dict(too_long),
            "empty_mask_rows": dict(empty_mask), "rejected_reasons": dict(rejected),
            "rejected_row_indices": rejected_indices,
            "first_prompt_duplicate_rows": sum(n - 1 for n in first_prompts.values() if n > 1),
            "url_rows": url_rows, "at_sign_rows": at_sign_rows,
            "supervised_target_tokens": target_tokens, "serialized_tokens": serialized_tokens,
            "supervised_ratio": target_tokens / serialized_tokens if serialized_tokens else 0.0,
            "human_review_row_indices": samples, "structural_gate": structural,
            "legacy_tokenizer_mask_gate": mask_gate,
            "human_quality_gate": "NOT_RUN", "contamination_gate": "NOT_RUN",
            "license_gate": "CARD_ONLY", "train_ready": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        good = {"type": "multi_2",
                "instruction": chr(10).join(("질문: 첫째", "답변: 둘째", "질문: 셋째")),
                "output": "넷째"}
        conv = restore(good, 0)
        if [msg["role"] for msg in conv["messages"]] != [
                "user", "assistant", "user", "assistant"]:
            raise RuntimeError("role restoration fixture differs")
        for bad in (dict(good, instruction="앞말" + chr(10) + good["instruction"]),
                    dict(good, instruction=chr(10).join(("질문: 첫째", "질문: 셋째"))),
                    dict(good, output="질문: 다른 문답"), dict(good, output="")):
            try:
                restore(bad, 0)
            except ValueError:
                pass
            else:
                raise RuntimeError("ambiguous multi-turn row was accepted")
        print("[PASS] P090B strict parser fixture; corpus/model NOT_RUN")
        return 0
    report = audit()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("[HOLD] structural candidates only; human quality/PII/license/contamination NOT_RUN")
    return 0 if report["accepted_multi"].get("multi_2", 0) >= 50 and report["accepted_multi"].get("multi_3", 0) >= 50 else 1


if __name__ == "__main__":
    raise SystemExit(main())
