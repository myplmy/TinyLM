#!/usr/bin/env python3
"""P105 read-only wiki-tail exposure/generation counter; no model, download or writes."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ROOT / "datasets" / "TinyDataset"
HEADING = re.compile(r"^\s*(?:={1,6}\s*|#{1,6}\s*)?(같이 보기|참고 문헌|참고문헌|외부 링크|각주)\s*(?:={1,6})?\s*$")
URL = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
STRATA = frozenset({"general", "wiki", "url_request", "provided_context"})


def scoped_file(raw: str) -> Path:
    path = Path(raw)
    if path.is_symlink():
        raise ValueError("symlink input refused")
    real = path.resolve(strict=True)
    if not real.is_file() or not real.is_relative_to(ROOT):
        raise ValueError("input must be a regular file inside the repository")
    if real.is_relative_to(PROTECTED):
        raise ValueError("protected TinyDataset input refused")
    return real


def classify(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    lines = text.splitlines(keepends=True)
    if not lines:
        return {"headings": [], "tail_start": None, "urls": 0}
    offset = 0
    headings = []
    for index, line in enumerate(lines):
        hit = HEADING.fullmatch(line.strip())
        if hit:
            headings.append((index, offset, hit.group(1)))
        offset += len(line)
    tail = next((at for index, at, _ in headings if index / len(lines) >= 0.60), None)
    return {"headings": [kind for _, _, kind in headings],
            "tail_start": tail, "urls": len(URL.findall(text))}


def records(path: Path):
    with path.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"row {index}: object required")
                yield index, value


def source_audit(sources: list[str], tokenizer_path: str | None, max_docs: int) -> dict:
    tok = None
    if tokenizer_path:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(scoped_file(tokenizer_path)))
    report = {}
    for spec in sources:
        if "=" not in spec:
            raise ValueError("--source-jsonl must be LABEL=PATH")
        label, raw = spec.split("=", 1)
        if not label or label in report:
            raise ValueError("source label is empty or repeated")
        path = scoped_file(raw)
        count = Counter()
        candidate_ids = []
        for index, row in records(path):
            if max_docs and count["documents"] >= max_docs:
                break
            body = row.get("text")
            info = classify(body)
            count["documents"] += 1
            count["bytes"] += len(body.encode("utf-8"))
            count["heading_documents"] += bool(info["headings"])
            count["url_documents"] += bool(info["urls"])
            count["url_occurrences"] += info["urls"]
            if tok is not None:
                count["tokens"] += len(tok.encode(body).ids)
            start = info["tail_start"]
            if start is not None:
                count["tail_candidate_documents"] += 1
                tail = body[start:]
                count["tail_candidate_bytes"] += len(tail.encode("utf-8"))
                if tok is not None:
                    count["tail_candidate_tokens"] += len(tok.encode(tail).ids)
                digest = hashlib.sha256(f"{label}:{index}:{body}".encode("utf-8")).hexdigest()
                candidate_ids.append((digest, index))
                candidate_ids.sort()
                del candidate_ids[20:]
        if not count["documents"]:
            raise ValueError(f"{label}: zero documents")
        report[label] = {"counts": dict(count), "sampling": ("first_N" if max_docs else "full_file"),
                         "candidate_row_indices_zero_based": [index for _, index in candidate_ids],
                         "token_fraction": (count["tail_candidate_tokens"] / count["tokens"]
                                            if tok is not None and count["tokens"] else None)}
    return {"schema": "P105_WIKI_SOURCE_AUDIT_V1", "sources": report,
            "token_metric": "MEASURED" if tok is not None else "NOT_RUN",
            "claim": "CANDIDATE_TAIL_NOT_APPROVED_FILTER"}


def generation_audit(path: Path) -> dict:
    buckets: dict[tuple[str, str, str], Counter] = {}
    seen = set()
    model_provenance = {}
    required = ("model", "checkpoint_sha256", "tokenizer_sha256", "stratum",
                "prompt", "full_output", "seed", "temperature", "top_k",
                "stop_at_eos", "url_requested", "heading_requested")
    for index, row in records(path):
        missing = [field for field in required if field not in row]
        if missing:
            raise ValueError(f"row {index}: missing {','.join(missing)}")
        if row["stratum"] not in STRATA or not all(isinstance(row[key], bool)
                                                   for key in ("stop_at_eos", "url_requested", "heading_requested")):
            raise ValueError(f"row {index}: invalid stratum or request flags")
        prompt, full = row["prompt"], row["full_output"]
        if not isinstance(prompt, str) or not isinstance(full, str) or not full.startswith(prompt):
            raise ValueError(f"row {index}: generated text does not contain the exact prompt prefix")
        if not row["checkpoint_sha256"] or not row["tokenizer_sha256"]:
            raise ValueError(f"row {index}: missing model/tokenizer provenance")
        if row.get("schema") == "P105_WIKI_PANEL_V1" and (not row.get("case_id") or not row.get("decode")):
            raise ValueError(f"row {index}: fixed panel case_id/decode missing")
        identity = (str(row["model"]), str(row.get("case_id", index)), str(row.get("decode", "other")))
        if identity in seen:
            raise ValueError(f"row {index}: duplicate model/case/decode")
        seen.add(identity)
        hashes = (row["checkpoint_sha256"], row["tokenizer_sha256"])
        old = model_provenance.setdefault(str(row["model"]), hashes)
        if old != hashes:
            raise ValueError(f"row {index}: model tag has mixed checkpoint/tokenizer SHA")
        out = full[len(prompt):]
        key = (str(row["model"]), str(row["stratum"]), str(row["temperature"]))
        c = buckets.setdefault(key, Counter())
        c["generations"] += 1
        headings = classify(out)["headings"]
        urls = URL.findall(out)
        c["heading_any"] += bool(headings)
        c["url_any"] += bool(urls)
        c["url_occurrences"] += len(urls)
        c["same_url_repeated"] += any(n > 1 for n in Counter(urls).values())
        c["unwanted_heading"] += bool(headings) and not row["heading_requested"]
        c["unwanted_url"] += bool(urls) and not row["url_requested"]
        c["unwanted_url_occurrences"] += 0 if row["url_requested"] else len(urls)
        c["empty_continuation"] += not bool(out.strip())
        c["repeat_heuristic"] += bool(re.search(r"\b([^\s]{2,})\b(?:\s+\1){3,}", out))
    if not buckets:
        raise ValueError("zero generation rows")
    groups = []
    for (model, stratum, temp), counts in sorted(buckets.items()):
        n = counts["generations"]
        groups.append({"model": model, "stratum": stratum, "temperature": temp,
                       **dict(counts), "unwanted_heading_rate": counts["unwanted_heading"] / n,
                       "unwanted_url_rate": counts["unwanted_url"] / n})
    complete = (len(model_provenance) == 7 and len(buckets) == 56 and len(seen) == 280
                and all(counts["generations"] == 5 for counts in buckets.values()))
    return {"schema": "P105_WIKI_GENERATION_AUDIT_V1",
            "status": "COMPLETE_7_MODEL_PANEL" if complete else "PARTIAL_PANEL",
            "models": len(model_provenance), "rows": len(seen), "buckets": groups,
            "claim": "FREQUENCY_ONLY_MANUAL_QUALITY_NOT_RUN"}


def self_test() -> None:
    import io
    from unittest.mock import patch

    body = "본문에서 같이 보기는 설명이다.\n두 번째 본문이다.\n\n== 외부 링크 ==\nhttp://example.invalid\n"
    info = classify(body)
    assert info["headings"] == ["외부 링크"] and info["tail_start"] is not None
    assert classify("같이 보기를 설명한다\n본문\n")["tail_start"] is None
    assert classify("\n")["headings"] == []

    class MemPath:
        def __init__(self, rows):
            self.payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)

        def open(self, encoding):
            assert encoding == "utf-8"
            return io.StringIO(self.payload)

    generation = {"model": "fixture", "checkpoint_sha256": "C", "tokenizer_sha256": "T",
                  "stratum": "general", "prompt": "질문:", "full_output": "질문:== 외부 링크 ==\nhttp://example.invalid",
                  "seed": 7, "temperature": 0, "top_k": 1, "stop_at_eos": True,
                  "url_requested": False, "heading_requested": False}
    checked = generation_audit(MemPath([generation]))["buckets"][0]
    assert checked["generations"] == 1 and checked["unwanted_heading"] == 1
    assert checked["unwanted_url"] == 1
    assert checked["url_occurrences"] == 1
    repeated = dict(generation, full_output=generation["full_output"] + chr(10) + "http://example.invalid")
    repeated_counts = generation_audit(MemPath([repeated]))["buckets"][0]
    assert repeated_counts["same_url_repeated"] == 1 and repeated_counts["url_occurrences"] == 2
    with patch(__name__ + ".scoped_file", return_value=MemPath([{"text": body}])):
        source = source_audit(["wiki=fixture"], None, 0)["sources"]["wiki"]["counts"]
    assert source["documents"] == 1 and source["tail_candidate_documents"] == 1
    print("[FIXTURE] source_docs=1 tail_candidates=1; generation_rows=1, unwanted_heading=1, URL_count=1, repeated_same_URL=1")
    print("[PASS] P105 source/generation JSONL, header/body, tail, URL contract; source/model/GPU NOT_RUN")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--source-jsonl", action="append", default=[], metavar="LABEL=PATH")
    ap.add_argument("--generation-jsonl")
    ap.add_argument("--tokenizer-json", help="optional local tokenizer; without it token metric is NOT_RUN")
    ap.add_argument("--max-docs", type=int, default=0)
    args = ap.parse_args()
    if args.max_docs < 0 or sum(bool(x) for x in (args.self_test, args.source_jsonl, args.generation_jsonl)) != 1:
        ap.error("select exactly one mode; max-docs must be nonnegative")
    try:
        if args.self_test:
            self_test()
            return 0
        if args.source_jsonl:
            result = source_audit(args.source_jsonl, args.tokenizer_json, args.max_docs)
        else:
            result = generation_audit(scoped_file(args.generation_jsonl))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if args.generation_jsonl and result["status"] != "COMPLETE_7_MODEL_PANEL":
            return 8
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P105 audit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
