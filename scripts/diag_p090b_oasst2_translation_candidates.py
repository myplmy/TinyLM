#!/usr/bin/env python3
"""Read-only OASST2 English multi-turn translation pilot selector.

No text is printed or exported. Source rights, human quality, translation, and
Korean train readiness remain separate user-owned gates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "HF" / "sft_sources" / "p090_oasst2_179dd21" / "2023-11-05_oasst2_ready.trees.jsonl.gz"
SOURCE_SHA256 = "7A886A16CCFC1173C4F00A6897523E3C95B2785A86EE44A18A98F4F2807EE29B"
V3_TRAIN = ROOT / "HF" / "sft_ready" / "p090_public_v3_train.canonical.jsonl"
V3_VAL = ROOT / "HF" / "sft_ready" / "p090_public_v3_val.canonical.jsonl"
V3_SHA = (
    "96A3507344FEFCA5072887AB4664DBB9BEDBD37BCD0D01A564220C1008D4F836",
    "A14026E62ED5E2E3466E1843DAD5696DE0E622CE8E249B5BF4B4DB2064B68225",
)
TOKENIZER = ROOT / "data_cache" / "tok-ko-en-32768.json"
TOKENIZER_SHA = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("pinned public input missing or linked")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            sha.update(block)
    return sha.hexdigest().upper()


def _valid(node: dict, expected_role: str, parent_id=None) -> bool:
    return (isinstance(node, dict) and node.get("role") == expected_role
            and node.get("lang") == "en" and node.get("review_result") is True
            and isinstance(node.get("review_count"), int) and node["review_count"] >= 1
            and not node.get("deleted") and node.get("synthetic") is False
            and isinstance(node.get("text"), str) and bool(node["text"].strip())
            and isinstance(node.get("message_id"), str)
            and (parent_id is None or node.get("parent_id") == parent_id))


def select(tree: dict) -> dict | None:
    """One reviewed, non-synthetic best-rank English path per complete tree."""
    from tinylm.chat.canonical import normalize, validate
    if not isinstance(tree, dict) or tree.get("tree_state") != "ready_for_export":
        return None
    node = tree.get("prompt")
    if not _valid(node, "prompter"):
        return None
    messages = []
    while node is not None:
        expected = "prompter" if not messages or messages[-1]["role"] == "assistant" else "assistant"
        if not _valid(node, expected):
            return None
        messages.append({"role": "user" if expected == "prompter" else "assistant",
                         "content": node["text"].strip()})
        next_role = "assistant" if expected == "prompter" else "prompter"
        replies = [child for child in (node.get("replies") or ())
                   if _valid(child, next_role, node["message_id"])]
        node = min(replies, key=lambda child: (child.get("rank") is None,
                   child["rank"] if isinstance(child.get("rank"), int) else 999,
                   child["message_id"])) if replies else None
    if len(messages) < 4 or messages[-1]["role"] != "assistant":
        return None
    source_id = str(tree.get("message_tree_id") or tree["prompt"]["message_id"])
    return validate(normalize({"messages": messages, "meta": {
        "source": "oasst2_en", "source_id": source_id,
        "source_revision": "179dd21fc55192153d94adb0e0ce8f69e222bf75",
        "source_license": "Apache-2.0", "license_evidence": "card_only",
        "language": "en", "translation_status": "NOT_RUN",
    }}))


def audit() -> dict:
    from tokenizers import Tokenizer
    from tinylm.data.sft import IGNORE, conversation_split_key, encode_conversation, load_canonical, sft_targets
    for path, expected in ((SOURCE, SOURCE_SHA256), (V3_TRAIN, V3_SHA[0]),
                           (V3_VAL, V3_SHA[1]), (TOKENIZER, TOKENIZER_SHA)):
        if _digest(path) != expected:
            raise ValueError("pinned OASST2 comparison input SHA differs")
    old_keys = {conversation_split_key(row)
                for path in (V3_TRAIN, V3_VAL) for row in load_canonical(path)}
    tok = Tokenizer.from_file(str(TOKENIZER))
    counts: Counter[str] = Counter()
    seen: set[bytes] = set()
    ranked: list[tuple[str, int]] = []
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            tree = json.loads(line)
            conv = select(tree)
            if conv is None:
                continue
            counts["reviewed_multiturn"] += 1
            key = conversation_split_key(conv)
            if key in old_keys:
                counts["overlap_v3_first_prompt"] += 1
                continue
            if key in seen:
                counts["duplicate_oasst2_first_prompt"] += 1
                continue
            ids, labels, _ = encode_conversation(conv, tok, "chatml")
            if len(ids) - 1 > 1024:
                counts["legacy_over_1024"] += 1
                continue
            _, targets = sft_targets(ids, labels)
            if not any(value != IGNORE for value in targets):
                counts["empty_assistant_mask"] += 1
                continue
            counts["eligible_english_trees"] += 1
            rank = hashlib.sha256((SOURCE_SHA256 + ":" + conv["meta"]["source_id"]).encode()).hexdigest()
            ranked.append((rank, index))
            seen.add(key)
    selected = [index for _, index in sorted(ranked)[:200]]
    return {"schema": "P090B_OASST2_TRANSLATION_CANDIDATES_V1",
            "source_sha256": SOURCE_SHA256, "tokenizer_sha256": TOKENIZER_SHA,
            "counts": dict(counts), "pilot_tree_indices": selected,
            "human_review_tree_indices": selected[:50],
            "candidate_gate": "PASS" if len(selected) == 200 else "FAIL",
            "translation_gate": "NOT_RUN", "human_quality_gate": "NOT_RUN",
            "license_gate": "CARD_ONLY", "train_ready": False}


def self_test() -> None:
    def node(identifier, parent, role, text, replies=()):
        return {"message_id": identifier, "parent_id": parent, "role": role,
                "lang": "en", "review_result": True, "review_count": 2,
                "deleted": False, "synthetic": False, "text": text,
                "rank": 0, "replies": list(replies)}
    a4 = node("a4", "u3", "assistant", "last")
    u3 = node("u3", "a2", "prompter", "follow", (a4,))
    a2 = node("a2", "u1", "assistant", "answer", (u3,))
    tree = {"tree_state": "ready_for_export", "message_tree_id": "t1",
            "prompt": node("u1", None, "prompter", "question", (a2,))}
    conv = select(tree)
    if conv is None or [m["role"] for m in conv["messages"]] != [
            "user", "assistant", "user", "assistant"]:
        raise RuntimeError("reviewed English tree restoration differs")
    a2["review_result"] = False
    if select(tree) is not None:
        raise RuntimeError("unreviewed English branch was accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("[PASS] P090B OASST2 reviewed branch fixture; corpus/model/translation NOT_RUN")
        return 0
    report = audit()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("[HOLD] candidate IDs only; human QA, translation, rights and contamination NOT_RUN")
    return 0 if report["candidate_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
