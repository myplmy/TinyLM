#!/usr/bin/env python3
"""P090 public SFT source fetch and canonical conversion. Never trains a model.

Downloads are opt-in and pinned under HF/sft_sources; converted data stays in
HF/sft_ready. No protected TinyDataset path is read. A separate contamination,
license-sample, and model gate is required before training.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["TINYLM_HF"] = str(ROOT / "HF")
import tinylm  # HF cache redirect before huggingface_hub
from tinylm.data.sft import conversation_split_key
HF_DIR = ROOT / "HF"
SOURCE_DIR = HF_DIR / "sft_sources"
READY_DIR = HF_DIR / "sft_ready"
SOURCES = {
    "aya": {
        "repo": "CohereLabs/aya_dataset",
        "revision": "f9ea04583f02a8f86404ff6c58bf75fe637df8a2",
        "data": "data/train-00000-of-00001.parquet",
        "license": "Apache-2.0",
        "extras": ("README.md",),
    },
    "oasst": {
        "repo": "OpenAssistant/oasst1",
        "revision": "fdf72ae0827c1cda404aff25b6603abec9e3399b",
        "data": "2023-04-12_oasst_ready.trees.jsonl.gz",
        "license": "Apache-2.0",
        "extras": ("README.md", "LICENSE"),
    },
}


def _canonical(messages, source, source_id, language):
    from tinylm.chat.canonical import normalize, validate
    row = normalize({"messages": messages, "meta": {
        "source": source,
        "source_id": source_id,
        "source_revision": SOURCES[source]["revision"],
        "source_license": SOURCES[source]["license"],
        "language": language,
    }})
    return validate(row)


def aya_to_canonical(row):
    """Original human annotations only; re-annotations can duplicate prompts."""
    language = {"eng": "en", "kor": "ko"}.get(row.get("language_code"))
    question, answer = row.get("inputs"), row.get("targets")
    if language is None or row.get("annotation_type") != "original-annotations":
        return None
    if not isinstance(question, str) or not isinstance(answer, str):
        return None
    question, answer = question.strip(), answer.strip()
    if not question or not answer:
        return None
    key = hashlib.sha256((language + chr(0) + question + chr(0) + answer).encode("utf-8")).hexdigest()
    return _canonical(
        [{"role": "user", "content": question},
         {"role": "assistant", "content": answer}],
        "aya", key, language,
    )


def oasst_tree_to_canonical(tree):
    """One deterministic best-rank path per ready tree; no cross-branch packing."""
    if tree.get("tree_state") != "ready_for_export":
        return None
    node = tree.get("prompt")
    if not isinstance(node, dict):
        return None
    language = {"en": "en", "ko": "ko"}.get(node.get("lang"))
    if language is None:
        return None
    messages = []
    while isinstance(node, dict):
        if node.get("deleted") or node.get("review_result") is False:
            return None
        role = {"prompter": "user", "assistant": "assistant"}.get(node.get("role"))
        value = node.get("text")
        if role is None or not isinstance(value, str) or not value.strip():
            return None
        if node.get("lang") != language or (messages and messages[-1]["role"] == role):
            return None
        messages.append({"role": role, "content": value.strip()})
        replies = [r for r in node.get("replies", []) if isinstance(r, dict)
                   and not r.get("deleted") and r.get("review_result") is not False]
        if not replies:
            break
        node = min(
            replies,
            key=lambda r: (r.get("rank") is None,
                           r.get("rank") if r.get("rank") is not None else 999,
                           str(r.get("message_id", ""))),
        )
    if len(messages) < 2 or messages[-1]["role"] != "assistant":
        return None
    source_id = str(tree.get("message_tree_id") or tree["prompt"].get("message_id") or "")
    if not source_id:
        return None
    return _canonical(messages, "oasst", source_id, language)


def _iter_aya(path):
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(path)
    cols = ("inputs", "targets", "language_code", "annotation_type")
    for batch in parquet.iter_batches(batch_size=512, columns=cols):
        for row in batch.to_pylist():
            yield aya_to_canonical(row)


def _iter_oasst(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield oasst_tree_to_canonical(json.loads(line))


def _fingerprint(row):
    text = chr(10).join(
        str(message["content"]) for message in row["messages"]
    )
    normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def select_rows(rows, max_ko, max_en, max_chars):
    """Order-independent subset by stable source id, with exact-content dedup."""
    candidates = {"ko": [], "en": []}
    for row in rows:
        if row is None:
            continue
        language = row["meta"]["language"]
        if language not in candidates:
            continue
        length = sum(len(message["content"][0]["text"]) for message in row["messages"])
        if length > max_chars:
            continue
        candidates[language].append(row)
    selected, seen = [], set()
    selected_count = {"ko": 0, "en": 0}
    for language, limit in (("ko", max_ko), ("en", max_en)):
        for row in sorted(candidates[language], key=lambda r: (
            r["meta"]["source_id"], r["meta"]["source"]
        )):
            fingerprint = _fingerprint(row)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            selected.append(row)
            selected_count[language] += 1
            if selected_count[language] >= limit:
                break
    return selected


def fetch_sources(kinds):
    from huggingface_hub import hf_hub_download
    for kind in kinds:
        source = SOURCES[kind]
        dest = SOURCE_DIR / kind
        dest.mkdir(parents=True, exist_ok=True)
        for filename in (source["data"], *source["extras"]):
            path = hf_hub_download(
                repo_id=source["repo"], repo_type="dataset",
                revision=source["revision"], filename=filename, local_dir=dest,
            )
            print(f"[FETCH] {kind} {filename} -> {path}")


def convert_sources(kinds, max_ko, max_en, max_chars, prefix, max_tokens=0, tokenizer_data=None):
    if not prefix or Path(prefix).name != prefix or "." in prefix:
        raise ValueError("prefix must be a single name without an extension")
    READY_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "train": READY_DIR / f"{prefix}_train.canonical.jsonl",
        "val": READY_DIR / f"{prefix}_val.canonical.jsonl",
        "manifest": READY_DIR / f"{prefix}_manifest.json",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("output exists; use a new prefix, never overwrite a corpus")
    rows = []
    for kind in kinds:
        path = SOURCE_DIR / kind / SOURCES[kind]["data"]
        if not path.is_file():
            raise FileNotFoundError(f"pinned source missing: {path}")
        rows.extend(_iter_aya(path) if kind == "aya" else _iter_oasst(path))
    selected = select_rows(rows, max_ko, max_en, max_chars)
    token_filter = {"status": "NOT_RUN"}
    if max_tokens:
        if not tokenizer_data:
            raise ValueError("--max-tokens requires --tokenizer-data")
        from tinylm.data import load_tokenizer, tokenizer_path
        from tinylm.data.sft import encode_conversation
        tok = load_tokenizer(tokenizer_data)
        kept, excluded = [], {"ko": 0, "en": 0}
        for row in selected:
            ids, _, _ = encode_conversation(row, tok)
            if len(ids) - 1 > max_tokens:
                excluded[row["meta"]["language"]] += 1
            else:
                kept.append(row)
        selected = kept
        token_filter = {
            "status": "APPLIED", "max_tokens": max_tokens, "tokenizer_data": tokenizer_data,
            "tokenizer_sha256": hashlib.sha256(
                tokenizer_path(tokenizer_data).read_bytes()
            ).hexdigest().upper(),
            "excluded": excluded,
        }
    if not selected or not any(row["meta"]["language"] == "ko" for row in selected):
        raise ValueError("no Korean examples; dataset is not ready")
    counts = {"train": {"ko": 0, "en": 0}, "val": {"ko": 0, "en": 0}}
    partition = {"train": [], "val": []}
    for row in selected:
        language = row["meta"]["language"]
        # tree 단위만으로는 다른 tree의 같은 질문이 train/val에 누출된다.
        # 출처와 무관한 정규화 첫 질문을 전역 group key로 쓴다.
        key = conversation_split_key(row)
        split = "val" if int.from_bytes(key[:4], "big") % 20 == 0 else "train"
        partition[split].append(row)
        counts[split][language] += 1
    if any(counts[split][language] == 0 for split in counts for language in ("ko", "en")):
        raise ValueError(f"train/val needs both ko and en; counts={counts}")
    for split in ("train", "val"):
        with paths[split].open("x", encoding="utf-8") as handle:
            for row in partition[split]:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + chr(10))
    output_sha256 = {
        split: hashlib.sha256(paths[split].read_bytes()).hexdigest().upper()
        for split in ("train", "val")
    }
    manifest = {
        "schema": "TINYLM_PUBLIC_SFT_V1",
        "sources": {kind: SOURCES[kind] for kind in kinds},
        "counts": counts,
        "output_sha256": output_sha256,
        "token_filter": token_filter,
        "selection": {"max_ko": max_ko, "max_en": max_en, "max_chars": max_chars,
                      "branch_policy": "oasst one best-rank path per tree",
                      "split_policy": "global normalized first-prompt group across sources and trees"},
        "contamination_gate": "NOT_RUN",
        "tokenizer_mask_gate": "NOT_RUN",
        "training_gate": "NOT_RUN",
    }
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PREPARED_NOT_TRAIN_READY] counts={counts} files={paths}")
    return manifest


def self_test():
    a = aya_to_canonical({
        "language_code": "kor", "annotation_type": "original-annotations",
        "inputs": "첫 질문", "targets": "첫 답",
    })
    tree = {"tree_state": "ready_for_export", "message_tree_id": "tree-1",
            "prompt": {"role": "prompter", "lang": "en", "text": "first",
                       "replies": [{"role": "assistant", "lang": "en", "text": "answer",
                                    "rank": 0, "replies": [{
                                        "role": "prompter", "lang": "en", "text": "follow up",
                                        "replies": [{"role": "assistant", "lang": "en",
                                                     "text": "second answer", "replies": []}]}]}]}}
    o = oasst_tree_to_canonical(tree)
    assert a and o and len(o["messages"]) == 4
    o_same_prompt = dict(o, messages=[dict(o["messages"][0], content=a["messages"][0]["content"])] + o["messages"][1:])
    assert conversation_split_key(a) == conversation_split_key(o_same_prompt)
    system_first = {"messages": [{"role": "system", "content": "공통 규칙"}, *a["messages"]]}
    assert conversation_split_key(system_first) == conversation_split_key(a)
    assert len(select_rows([a, a, o], 2, 2, 4096)) == 2
    print("[PASS] public SFT canonical conversion synthetic fixture; download NOT_RUN")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--convert", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--sources", choices=("aya", "oasst", "both"), default="both")
    parser.add_argument("--max-ko", type=int, default=3000)
    parser.add_argument("--max-en", type=int, default=3000)
    parser.add_argument("--max-chars", type=int, default=4096)
    parser.add_argument("--prefix", default="p090_public_v1")
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--tokenizer-data")
    args = parser.parse_args()
    kinds = tuple(SOURCES) if args.sources == "both" else (args.sources,)
    if args.self_test:
        self_test()
        return
    if not (args.fetch or args.convert):
        parser.error("choose --fetch and/or --convert; neither runs implicitly")
    if min(args.max_ko, args.max_en, args.max_chars) < 1 or args.max_tokens < 0:
        parser.error("limits must be non-negative and quota/character limits positive")
    if args.fetch:
        fetch_sources(kinds)
    if args.convert:
        convert_sources(kinds, args.max_ko, args.max_en, args.max_chars, args.prefix, args.max_tokens, args.tokenizer_data)


if __name__ == "__main__":
    main()
