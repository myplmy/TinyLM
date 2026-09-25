#!/usr/bin/env python3
"""P105 Stage1Wc: audit actual termination reasons in a new write-once panel."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import sys

from diag_p105_wiki_format import records, scoped_file
from diag_p105_repetition_reaudit import line_run, repeated_ngram
from eval_p105_wiki_panel import CASES, DECODES

REASONS = frozenset({"EOS", "MAX_NEW", "EOS_UNAVAILABLE"})


def audit(rows, *, require_complete: bool) -> dict:
    by_model = defaultdict(Counter)
    by_stratum = defaultdict(Counter)
    seen = set()
    provenance = {}
    for index, row in rows:
        if row.get("schema") != "P105_WIKI_PANEL_V1" or row.get("termination_schema") != "P105_TERMINATION_V1":
            raise ValueError(f"row {index}: measured P105 panel schema required")
        required = ("model", "case_id", "decode", "stratum", "prompt", "full_output",
                    "checkpoint_sha256", "tokenizer_sha256")
        if any(not isinstance(row.get(key), str) or not row[key] for key in required):
            raise ValueError(f"row {index}: missing identity, provenance or text")
        if require_complete:
            expected = {case: (group, prompt) for case, group, prompt, _, _ in CASES}
            if (row["case_id"] not in expected
                    or row["decode"] not in {decode for decode, _, _ in DECODES}
                    or (row["stratum"], row["prompt"]) != expected[row["case_id"]]):
                raise ValueError(f"row {index}: fixed panel case/prompt/decode drift")
        identity = (row["model"], row["case_id"], row["decode"])
        if identity in seen:
            raise ValueError(f"row {index}: duplicate model/case/decode")
        seen.add(identity)
        if not row["full_output"].startswith(row["prompt"]):
            raise ValueError(f"row {index}: prompt prefix mismatch")
        hashes = (row["checkpoint_sha256"], row["tokenizer_sha256"])
        if provenance.setdefault(row["model"], hashes) != hashes:
            raise ValueError(f"row {index}: mixed model/tokenizer provenance")
        reason = row.get("finish_reason")
        count, cap = row.get("generated_tokens"), row.get("max_new")
        if reason not in REASONS or type(count) is not int or type(cap) is not int or not 1 <= count <= cap:
            raise ValueError(f"row {index}: invalid reason or generated-token count")
        if require_complete and cap != 80:
            raise ValueError(f"row {index}: expected 80-token generation cap")
        if row.get("stop_at_eos") is not True or row.get("stop_at_eos_requested") is not True:
            raise ValueError(f"row {index}: EOS stop was not requested")
        available = row.get("eos_token_available")
        effective = row.get("stop_at_eos_effective")
        if type(available) is not bool or type(effective) is not bool or effective != available:
            raise ValueError(f"row {index}: inconsistent EOS availability")
        if reason == "EOS" and not available:
            raise ValueError(f"row {index}: EOS without token")
        if reason == "MAX_NEW" and (not available or count != cap):
            raise ValueError(f"row {index}: false max-new report")
        if reason == "EOS_UNAVAILABLE" and (available or count != cap):
            raise ValueError(f"row {index}: false missing-EOS report")
        out = row["full_output"][len(row["prompt"]):]
        repeated = line_run(out) >= 4 or repeated_ngram(out)
        for bucket in (by_model[row["model"]], by_stratum[row["stratum"]]):
            bucket["rows"] += 1
            bucket["generated_tokens"] += count
            bucket[reason] += 1
            bucket["repeat_candidate"] += repeated
            bucket["repeat_at_max_new"] += repeated and reason == "MAX_NEW"
            bucket["empty_continuation"] += not bool(out.strip())
    if not seen:
        raise ValueError("zero answers")
    if require_complete and (len(seen) != 280 or len(by_model) != 7
                             or any(bucket["rows"] != 40 for bucket in by_model.values())):
        raise ValueError("expected exactly 7 models x 40 unique answers = 280")
    return {"schema": "P105_TERMINATION_AUDIT_V1",
            "status": "COMPLETE_280" if require_complete else "FIXTURE",
            "rows": len(seen), "models": len(by_model),
            "by_model": {key: dict(value) for key, value in sorted(by_model.items())},
            "by_stratum": {key: dict(value) for key, value in sorted(by_stratum.items())},
            "claim": "ACTUAL_STOP_REASON_AND_REPEAT_ASSOCIATION_ONLY; source and semantic causality NOT_RUN"}


def self_test() -> None:
    def termination_fixture_record(case: str, reason: str, count: int, available: bool) -> dict:
        return {"schema": "P105_WIKI_PANEL_V1", "termination_schema": "P105_TERMINATION_V1",
                "model": "fixture", "case_id": case, "decode": "greedy", "stratum": "general",
                "prompt": "Q:", "full_output": "Q:서울", "checkpoint_sha256": "C",
                "tokenizer_sha256": "T", "finish_reason": reason, "generated_tokens": count,
                "max_new": 80, "stop_at_eos": True, "stop_at_eos_requested": True,
                "eos_token_available": available, "stop_at_eos_effective": available}
    sample = [(0, termination_fixture_record("A", "EOS", 1, True)), (1, termination_fixture_record("B", "MAX_NEW", 80, True)),
              (2, termination_fixture_record("C", "EOS_UNAVAILABLE", 80, False))]
    assert audit(sample, require_complete=False)["rows"] == 3
    for bad in (sample + [(3, termination_fixture_record("A", "EOS", 1, True))],
                [(0, termination_fixture_record("D", "EOS", 1, False))],
                [(0, termination_fixture_record("E", "MAX_NEW", 1, True))]):
        try:
            audit(bad, require_complete=False)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid termination record accepted")
    print("[PASS] P105 termination schema, EOS/max/missing and duplicate fixtures; model NOT_RUN")


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
        print("[PASS] P105 measured EOS/max-new panel; quality and source causality NOT_RUN")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P105 termination audit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
