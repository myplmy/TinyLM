#!/usr/bin/env python3
"""P090B public SFT aggregate preflight; no raw text, model, GPU or writes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
READY = ROOT / "HF" / "sft_ready"
TOKENIZERS = ROOT / "data_cache"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            sha.update(block)
    return sha.hexdigest().upper()


def scoped(path: Path, directory: Path, suffix: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"symlink refused: {path}")
    real = path.resolve(strict=True)
    if real.parent != directory.resolve() or not real.is_file() or not real.name.endswith(suffix):
        raise ValueError(f"expected {suffix} directly under {directory}")
    return real


def split_counts(train_rows: list[dict], val_rows: list[dict]) -> dict:
    from tinylm.data.sft import conversation_split_key
    def ids(rows):
        return {(r["meta"]["source"], r["meta"]["source_id"]) for r in rows}
    tr_ids, va_ids = ids(train_rows), ids(val_rows)
    tr_prompts = {conversation_split_key(r) for r in train_rows}
    va_prompts = {conversation_split_key(r) for r in val_rows}
    return {"source_id_overlap": len(tr_ids & va_ids),
            "first_prompt_overlap": len(tr_prompts & va_prompts),
            "train_unique_source_ids": len(tr_ids),
            "val_unique_source_ids": len(va_ids)}



def panel_exact_overlap(rows: list[dict]) -> dict:
    """Count exact P100 fixed-panel prompts in user turns; never print text."""
    from collections import Counter
    from eval_p100_capability_panel import CASES

    def norm(value: str) -> str:
        return " ".join(value.casefold().split())

    prompts: dict[str, set[str]] = {}
    for case_id, _ability, prompt, _rubric in CASES:
        for form in (prompt, "Question: " + prompt + " Answer:"):
            prompts.setdefault(norm(form), set()).add(case_id)
    hits: Counter[str] = Counter()
    for row in rows:
        for message in row.get("messages", ()):
            if message.get("role") != "user":
                continue
            content = message.get("content", ())
            texts = ([content] if isinstance(content, str) else
                     [block.get("text", "") for block in content
                      if isinstance(block, dict) and block.get("type") == "text"])
            for value in texts:
                for case_id in prompts.get(norm(value), ()):
                    hits[case_id] += 1
    return {"matched_user_messages": sum(hits.values()),
            "case_ids": dict(sorted(hits.items()))}


def full_mask_counts(rows: list[dict], tok) -> dict:
    """Count assistant body and stop-token coverage without printing any text."""
    from tinylm.chat.serialize import SPECS
    from tinylm.data.sft import covered_text, mask_detail
    end_token = SPECS["chatml"]["end"]
    missing_body = missing_end = 0
    for row in rows:
        detail = mask_detail(row, tok, "chatml")
        covered = covered_text(detail["text"], detail["offsets"], detail["keep"])
        wants = [block.get("text", "") for message in row["messages"]
                 if message["role"] == "assistant"
                 for block in message["content"] if block.get("type") == "text"]
        missing_body += int(any(text and text not in covered for text in wants))
        missing_end += int(bool(wants) and end_token not in covered)
    return {"checked": len(rows), "missing_assistant_body": missing_body,
            "missing_end_token": missing_end}


def source_quality_screen(train_rows: list[dict], val_rows: list[dict], manifest: dict) -> dict:
    """Aggregate metadata/PII/length triage only; never print conversation text."""
    import re
    from collections import Counter

    def content(message):
        value = message.get("content", "")
        if isinstance(value, str):
            return value
        return "".join(block.get("text", "") for block in value
                       if isinstance(block, dict) and block.get("type") == "text")

    counts = Counter()
    answers = Counter()
    candidates = []
    mismatched = unknown = missing_assistant = multi_turn = url_rows = email_rows = 0
    assistant_lengths = []
    sources = manifest.get("sources", {})
    for split, rows in (("train", train_rows), ("val", val_rows)):
        for index, row in enumerate(rows):
            meta = row.get("meta", {})
            source, lang = meta.get("source"), meta.get("language")
            counts[(split, lang)] += 1
            spec = sources.get(source)
            if spec is None:
                unknown += 1
            elif (meta.get("source_license") != spec.get("license")
                  or meta.get("source_revision") != spec.get("revision")):
                mismatched += 1
            messages = row.get("messages", ())
            user_count = sum(m.get("role") == "user" for m in messages)
            assistant = [content(m) for m in messages if m.get("role") == "assistant"]
            multi_turn += int(user_count >= 2 and len(assistant) >= 2)
            missing_assistant += int(not assistant or any(not text.strip() for text in assistant))
            assistant_lengths.extend(len(text) for text in assistant)
            answers.update(" ".join(text.casefold().split()) for text in assistant if text.strip())
            joined = " ".join(content(m) for m in messages)
            url_rows += int(bool(re.search(r"https?://", joined, re.I)))
            email_rows += int(bool(re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", joined)))
            if source is not None and lang in ("ko", "en"):
                rank = hashlib.sha256(f"{source}:{meta.get('source_id')}".encode()).hexdigest()
                candidates.append((rank, split, source, lang, index))
    expected = {(split, lang): int(count)
                for split, group in manifest.get("counts", {}).items()
                for lang, count in group.items()}
    actual = dict(counts)
    count_mismatch = actual != expected
    chosen = {}
    for item in sorted(candidates):
        _, split, source, lang, index = item
        bucket = f"{source}/{lang}"
        chosen.setdefault(bucket, [])
        if len(chosen[bucket]) < 5:
            chosen[bucket].append({"split": split, "row_index_zero_based": index})
    total = sum(counts.values())
    structural_fail = unknown + mismatched + missing_assistant + int(count_mismatch)
    return {"source_metadata_gate": "PASS" if structural_fail == 0 else "FAIL",
            "source_language_counts": {f"{split}/{lang}": count
                                       for (split, lang), count in sorted(counts.items())},
            "ko_row_share": (sum(n for (_, lang), n in counts.items() if lang == "ko") / total
                             if total else 0.0),
            "multi_turn_rows": multi_turn,
            "assistant_chars_min": min(assistant_lengths, default=0),
            "assistant_chars_max": max(assistant_lengths, default=0),
            "max_exact_answer_repeat": max(answers.values(), default=0),
            "url_rows": url_rows, "email_rows": email_rows,
            "unknown_source_rows": unknown, "license_or_revision_mismatch_rows": mismatched,
            "missing_assistant_rows": missing_assistant,
            "manifest_count_mismatch": count_mismatch,
            "human_review_indices": chosen,
            "human_quality_gate": "NOT_RUN"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--tokenizer", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        a = {"meta": {"source": "a", "source_id": "1"},
             "messages": [{"role": "user", "content": "same"}]}
        b = {"meta": {"source": "b", "source_id": "2"},
             "messages": [{"role": "user", "content": "same"}]}
        assert split_counts([a], [b])["first_prompt_overlap"] == 1
        from tinylm.data.prepare import SyntheticTokenizer
        conversation = {"messages": [
            {"role": "user", "content": [{"type": "text", "text": "질문"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "답변"}]}]}
        checked = full_mask_counts([conversation], SyntheticTokenizer())
        assert checked["missing_assistant_body"] == 0 and checked["missing_end_token"] == 0
        from eval_p100_capability_panel import CASES
        panel_row = {"messages": [{"role": "user",
                                   "content": [{"type": "text", "text": CASES[0][2]}]}]}
        if panel_exact_overlap([panel_row])["case_ids"] != {CASES[0][0]: 1}:
            raise AssertionError("fixed-panel exact prompt was missed")
        print("[PASS] public SFT split/assistant/end/P100 exact-panel/source-metadata fixture; corpus/model/GPU NOT_RUN")
        qa_row = {"meta": {"source": "a", "source_id": "1", "language": "ko",
                           "source_license": "Apache-2.0", "source_revision": "r1"},
                  "messages": [{"role": "user", "content": "질문"},
                               {"role": "assistant", "content": "답변"}]}
        qa_manifest = {"sources": {"a": {"license": "Apache-2.0", "revision": "r1"}},
                       "counts": {"train": {"ko": 1}}}
        if source_quality_screen([qa_row], [], qa_manifest)["source_metadata_gate"] != "PASS":
            raise AssertionError("public source metadata fixture differs")
        if source_quality_screen([dict(qa_row, meta=dict(qa_row["meta"],
                source_license="wrong"))], [], qa_manifest)["source_metadata_gate"] != "FAIL":
            raise AssertionError("license provenance mismatch was accepted")
        return 0
    if not args.manifest or not args.tokenizer:
        ap.error("--manifest and --tokenizer are required")
    manifest_path = scoped(args.manifest, READY, "_manifest.json")
    tokenizer_path = scoped(args.tokenizer, TOKENIZERS, ".json")
    prefix = manifest_path.name.removesuffix("_manifest.json")
    train_file = scoped(READY / f"{prefix}_train.canonical.jsonl", READY, ".jsonl")
    val_file = scoped(READY / f"{prefix}_val.canonical.jsonl", READY, ".jsonl")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1":
        raise ValueError("unsupported public SFT manifest schema")
    for split, path in (("train", train_file), ("val", val_file)):
        if manifest.get("output_sha256", {}).get(split) != digest(path):
            raise ValueError(f"{split} canonical SHA256 mismatch")
    token_sha = digest(tokenizer_path)
    if manifest.get("token_filter", {}).get("tokenizer_sha256") != token_sha:
        raise ValueError("tokenizer lineage SHA256 mismatch")
    licenses = {value.get("license") for value in manifest.get("sources", {}).values()}
    if not licenses or None in licenses:
        raise ValueError("public SFT source license metadata is missing")
    from tokenizers import Tokenizer
    from tinylm.data.sft import load_canonical, mask_stats
    tok = Tokenizer.from_file(str(tokenizer_path))
    tr, va = load_canonical(train_file), load_canonical(val_file)
    counts = split_counts(tr, va)
    train_mask = mask_stats(tr, tok)
    val_mask = mask_stats(va, tok)
    full_mask = full_mask_counts(tr + va, tok)
    panel = panel_exact_overlap(tr + va)
    source_screen = source_quality_screen(tr, va, manifest)
    mask_pass = (0.02 <= train_mask["ratio"] <= 0.90
                 and 0.02 <= val_mask["ratio"] <= 0.90
                 and train_mask["empty_mask"] == 0
                 and val_mask["empty_mask"] == 0)
    report = {"schema": "P090B_PUBLIC_SFT_PREFLIGHT_V1",
              "corpus_train_sha256": manifest["output_sha256"]["train"],
              "corpus_val_sha256": manifest["output_sha256"]["val"],
              "tokenizer_sha256": token_sha,
              "train_rows": len(tr), "val_rows": len(va),
              "train_supervised_ratio": train_mask["ratio"],
              "val_supervised_ratio": val_mask["ratio"],
              "train_empty_mask": train_mask["empty_mask"],
              "val_empty_mask": val_mask["empty_mask"],
              "licenses": sorted(licenses),
              "split": counts,
              "panel_exact_overlap": panel,
              "panel_exact_gate": "PASS" if panel["matched_user_messages"] == 0 else "FAIL",
              "contamination_gate": manifest.get("contamination_gate", "NOT_RUN"),
              "manifest_tokenizer_mask_gate": manifest.get("tokenizer_mask_gate", "NOT_RUN"),
              "aggregate_mask_gate": "PASS" if mask_pass else "FAIL",
              "full_mask": full_mask,
              "full_mask_gate": ("PASS" if not full_mask["missing_assistant_body"]
                                and not full_mask["missing_end_token"] else "FAIL"),
              "source_quality_gate": manifest.get("source_quality_gate", "NOT_RUN"),
              "source_auto_screen": source_screen,
              "source_metadata_gate": source_screen["source_metadata_gate"],
              "train_ready": False}
    report["train_ready"] = (report["contamination_gate"] == "PASS"
                             and report["manifest_tokenizer_mask_gate"] == "PASS"
                             and report["aggregate_mask_gate"] == "PASS"
                             and report["full_mask_gate"] == "PASS"
                             and report["source_quality_gate"] == "PASS"
                             and not counts["source_id_overlap"]
                             and report["source_metadata_gate"] == "PASS"
                             and not counts["first_prompt_overlap"]
                             and not panel["matched_user_messages"])
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if (not mask_pass or report["full_mask_gate"] != "PASS"
            or counts["source_id_overlap"] or counts["first_prompt_overlap"]
            or panel["matched_user_messages"] or source_screen["source_metadata_gate"] != "PASS"):
        print("[FAIL] public SFT split, mask or P100 exact prompt overlap", file=sys.stderr)
        return 1
    if not report["train_ready"]:
        print("[HOLD] pilot-only: contamination or other TRAIN_READY evidence is missing")
    else:
        print("[PASS] full no-text mask preflight; manual source quality remains a separate gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
