#!/usr/bin/env python3
"""P100 Stage0bW: conservative, read-only triage of saved 36 raw answers.

This is not a benchmark score. Exact leading-answer and JSON checks are
diagnostic signals; all failures still require human reading of the raw answer.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import re
import sys

from diag_p105_wiki_format import records, scoped_file
from eval_p100_capability_panel import CASES

EXPECTED = {case_id: (ability, prompt, rubric) for case_id, ability, prompt, rubric in CASES}
DIRECT = {
    "KO_FACT": "서울", "EN_FACT": "Seoul",
    "KO_CONTEXT": "417", "EN_CONTEXT": "417",
    "KO_MULTI": "달빛-47", "EN_MULTI": "moon-47",
    "KO_NEGATION": "배",
}


def leading_answer(text: str, expected: str) -> bool:
    first = text.lstrip().splitlines()[0].strip() if text.strip() else ""
    first = re.sub(r"^(?:Answer|답)\s*:\s*", "", first, flags=re.IGNORECASE)
    return bool(re.match(r"^" + re.escape(expected) + r"(?:$|[\s.!?,;:。])",
                         first, flags=re.IGNORECASE))


def classify(case_id: str, continuation: str) -> str:
    if case_id == "KO_FORMAT":
        try:
            value = json.loads(continuation.strip())
        except (json.JSONDecodeError, TypeError):
            return "FORMAT_NOT_EXACT"
        return ("STRICT_SIGNAL" if isinstance(value, dict)
                and value == {"city": "서울", "country": "대한민국"}
                else "FORMAT_NOT_EXACT")
    if case_id in DIRECT:
        return ("STRICT_SIGNAL" if leading_answer(continuation, DIRECT[case_id])
                else "NOT_DIRECT")
    return "MANUAL_REQUIRED"


def audit(rows, *, require_complete: bool) -> dict:
    seen = set()
    buckets = defaultdict(Counter)
    provenance = {}
    for index, row in rows:
        model, case_id, form = row.get("model"), row.get("case_id"), row.get("form")
        if not all(isinstance(value, str) and value for value in (model, case_id, form)):
            raise ValueError(f"row {index}: missing model/case/form")
        if case_id not in EXPECTED or form not in ("base", "qa"):
            raise ValueError(f"row {index}: unknown case or form")
        identity = (model, case_id, form)
        if identity in seen:
            raise ValueError(f"row {index}: duplicate model/case/form")
        seen.add(identity)
        ability, prompt, rubric = EXPECTED[case_id]
        expected_prompt = prompt if form == "base" else "Question: " + prompt + " Answer:"
        if (row.get("prompt") != expected_prompt or row.get("rubric") != rubric
                or row.get("ability") != ability):
            raise ValueError(f"row {index}: prompt/rubric/ability drift")
        full = row.get("full_output")
        if not isinstance(full, str) or not full.startswith(expected_prompt):
            raise ValueError(f"row {index}: output does not preserve exact prompt")
        hashes = (row.get("checkpoint_sha256"), row.get("tokenizer_sha256"))
        if not all(isinstance(value, str) and value for value in hashes):
            raise ValueError(f"row {index}: missing provenance")
        if provenance.setdefault(model, hashes) != hashes:
            raise ValueError(f"row {index}: mixed model/tokenizer provenance")
        signal = classify(case_id, full[len(expected_prompt):])
        bucket = buckets[model]
        bucket["rows"] += 1
        bucket[signal] += 1
        bucket[f"{ability}_{form}_{signal}"] += 1
    if not seen:
        raise ValueError("zero answers")
    if require_complete and (len(seen) != 36 or len(buckets) != 2
                             or any(bucket["rows"] != 18 for bucket in buckets.values())):
        raise ValueError("expected exactly 2 models x 9 cases x 2 forms = 36")
    return {"schema": "P100_SAVED_ANSWER_TRIAGE_V1",
            "status": "COMPLETE_36" if require_complete else "FIXTURE",
            "rows": len(seen), "models": len(buckets),
            "by_model": {key: dict(value) for key, value in sorted(buckets.items())},
            "claim": "STRICT_LEADING_ANSWER_OR_JSON_SIGNAL_ONLY; knowledge, reasoning and SFT causality NOT_SCORED"}


def self_test() -> None:
    rows = []
    for model in ("control", "fineweb"):
        for case_id, ability, prompt, rubric in CASES:
            for form in ("base", "qa"):
                shown = prompt if form == "base" else "Question: " + prompt + " Answer:"
                answer = ('{"city":"서울","country":"대한민국"}' if case_id == "KO_FORMAT"
                          else DIRECT.get(case_id, "검수 필요"))
                rows.append((len(rows), {"model": model, "case_id": case_id, "form": form,
                                         "ability": ability, "rubric": rubric, "prompt": shown,
                                         "full_output": shown + answer,
                                         "checkpoint_sha256": model, "tokenizer_sha256": "tok"}))
    result = audit(rows, require_complete=True)
    assert result["rows"] == 36 and all(bucket["STRICT_SIGNAL"] == 16
                                        for bucket in result["by_model"].values())
    for bad in (rows + [rows[0]], [(0, {**rows[0][1], "full_output": "wrong"})]):
        try:
            audit(bad, require_complete=False)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid saved answer accepted")
    print("[PASS] P100 36-row completeness, direct/JSON signals and invalid fixtures; model NOT_RUN")


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
        print("[PASS] P100 saved-answer triage complete; strict signals are not accuracy")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P100 answer triage: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
