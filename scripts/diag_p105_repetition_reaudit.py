#!/usr/bin/env python3
"""P105 Stage1Wb: read-only candidate repetition audit of the saved 280 answers.

This corrects the old one-token/length>=2 heuristic's blind spot without
rewriting Stage1W output or claiming semantic quality or source causality.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import re
import sys

from diag_p105_wiki_format import records, scoped_file


def line_run(text: str) -> int:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    longest = run = 0
    previous = None
    for line in lines:
        run = run + 1 if line == previous else 1
        previous = line
        longest = max(longest, run)
    return longest


def repeated_ngram(text: str) -> bool:
    tokens = re.findall(r"\S+", text)
    for width in range(1, min(8, len(tokens) // 4) + 1):
        for start in range(len(tokens) - 4 * width + 1):
            phrase = tokens[start:start + width]
            if all(tokens[start + turn * width:start + (turn + 1) * width] == phrase
                   for turn in (1, 2, 3)):
                return True
    return False


def audit(rows, *, require_complete: bool) -> dict:
    buckets = defaultdict(Counter)
    seen = set()
    for index, row in rows:
        if row.get("schema") != "P105_WIKI_PANEL_V1":
            raise ValueError(f"row {index}: wrong panel schema")
        for key in ("model", "case_id", "decode", "stratum", "prompt", "full_output"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ValueError(f"row {index}: missing or non-string {key}")
        identity = (row["model"], row["case_id"], row["decode"])
        if identity in seen:
            raise ValueError(f"row {index}: duplicate model/case/decode")
        seen.add(identity)
        if not row["full_output"].startswith(row["prompt"]):
            raise ValueError(f"row {index}: prompt prefix mismatch")
        continuation = row["full_output"][len(row["prompt"]):]
        longest = line_run(continuation)
        ngram = repeated_ngram(continuation)
        count = buckets[row["model"]]
        count["rows"] += 1
        count["line_loop_ge4"] += longest >= 4
        count["token_ngram_ge4"] += ngram
        count["repeat_candidate"] += longest >= 4 or ngram
        count["empty"] += not bool(continuation.strip())
        count["max_line_run"] = max(count["max_line_run"], longest)
    if require_complete and (len(seen) != 280 or len(buckets) != 7
                             or any(count["rows"] != 40 for count in buckets.values())):
        raise ValueError("expected exactly 7 models x 40 unique answers = 280")
    if not seen:
        raise ValueError("zero answers")
    return {"schema": "P105_REPEAT_REAUDIT_V1", "status": "COMPLETE_280" if require_complete else "FIXTURE",
            "rows": len(seen), "models": len(buckets),
            "by_model": {model: dict(count) for model, count in sorted(buckets.items())},
            "claim": "CANDIDATE_REPETITION_ONLY; manual quality, EOS reason and source causality NOT_RUN"}


def self_test() -> None:
    def fixture_row_p105(case: str, output: str):
        return {"schema": "P105_WIKI_PANEL_V1", "model": "fixture", "case_id": case,
                "decode": "greedy", "stratum": "general", "prompt": "Q:", "full_output": "Q:" + output}

    sample = [(0, fixture_row_p105("A", "\n-\n-\n-\n-\n")),
              (1, fixture_row_p105("B", "가나다 라마 가나다 라마 가나다 라마 가나다 라마")),
              (2, fixture_row_p105("C", "한 문장으로 답합니다.")),
              (3, fixture_row_p105("D", " \n"))]
    result = audit(sample, require_complete=False)["by_model"]["fixture"]
    assert result["repeat_candidate"] == 2 and result["line_loop_ge4"] == 1
    assert result["token_ngram_ge4"] == 2 and result["empty"] == 1
    try:
        audit(sample + [(4, fixture_row_p105("A", "duplicate"))], require_complete=False)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate answer accepted")
    print("[PASS] P105 Stage1Wb bullet-line and phrase-loop fixtures; actual model answers NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--input-jsonl")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        result = audit(records(scoped_file(args.input_jsonl)), require_complete=True)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        print("[PASS] P105 Stage1Wb 280 answer repetition re-audit; quality/source/EOS NOT_RUN")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P105 Stage1Wb: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
