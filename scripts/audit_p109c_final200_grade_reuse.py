"""Reuse verified FINAL200 decisions only for identical answers and prepare blind review."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from scripts.audit_p109c_completed_eval_units import archived, unit_rows
from scripts.audit_p109c_final200_termination import RUBRIC_KEYS


V3 = archived.EVIDENCE / "p109c_integrated_scratch_v3_common_eval_v1_20261124"
V3_REVIEW = archived.ROOT / "handoff/audit/P109C_INTEGRATED_V3_FINAL200_SEMANTIC_20261124.json"
RUBRIC = archived.ROOT / "handoff/audit/nov01_independent/final200_semantic_rubric_v1.md"
GENERALIZATION = archived.EVIDENCE / "p109c_rule_generalization_cpu_20261125/final200"
CASE_FIELDS = ("id", "language", "category", "prompt", "reference", "match_rule", "rubric", "required_repetition")


def generation(record):
    receipt = archived.read(record / "evaluation_input.json")
    return unit_rows(record, "final200", 200, "answers", receipt["mode"])


def fingerprint(generation):
    metadata = generation["metadata"]
    return (generation["answer"], tuple(metadata["generated_ids"]), metadata["finish_reason"],
            tuple(metadata["terminal_ids"]), generation["repeat_tail"])


def flags(decision):
    selected = tuple(decision[key] for key in RUBRIC_KEYS)
    if not all(type(value) is bool for value in selected) or selected[-1] != all(selected[:-1]):
        raise ValueError("semantic usability must be the intersection of the three rubric flags")
    return selected


def reference_grades():
    reference, v3_summary = generation(V3)
    direct = archived.read(V3_REVIEW)
    prior = archived.read(GENERALIZATION / "semantic.json")
    summary_sha = archived.source(GENERALIZATION / "summary.json")["sha256"]
    if (direct["source_sha256"] != v3_summary["answers"]["concat_sha256"]
            or direct["rubric_sha256"] != archived.source(RUBRIC)["sha256"]
            or prior["prior_graded_record_sha256"] != archived.source(V3_REVIEW)["sha256"]
            or prior["prior_original_sha256"] != direct["source_sha256"]
            or prior["frozen_generation_summary_sha256"] != summary_sha):
        raise ValueError("the archived review is bound to different answers or rubric")
    by_case = {row["id"]: row for row in reference}
    if set(by_case) != set(prior["cases"]) or len(by_case) != 200:
        raise ValueError("the historical decisions do not describe the same 200 cases")
    grades = defaultdict(lambda: defaultdict(list))
    for case, row in by_case.items():
        language = row["language"]
        rubric = direct["semantic_true_ids"][language]
        decision = flags({key: case in rubric[key] for key in RUBRIC_KEYS})
        grades[case, fingerprint(row)][decision].append("archived_v3")
    seen, receipts = set(), []
    for path in sorted(GENERALIZATION.glob("[0-9][0-9][0-9][0-9][0-9][0-9].json")):
        chunk = archived.read(path)
        encoded = json.dumps(chunk["rows"], sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        if (chunk["task"] != "final200" or chunk["offset"] != len(seen)
                or chunk["rows_sha256"] != sha256(encoded).hexdigest()):
            raise ValueError("a graded generalization response shard changed")
        receipts.append(archived.source(path))
        for row in chunk["rows"]:
            case = row["id"]
            if case in seen or any(row[key] != by_case[case][key]
                                   for key in ("id", "language", "category", "reference", "match_rule")):
                raise ValueError("the graded response case differs from frozen FINAL200")
            seen.add(case)
            for arm, result in row["generations"].items():
                decision = flags(prior["cases"][case]["arms"][arm])
                grades[case, fingerprint(result)][decision].append(f"rule_{arm}")
    if seen != set(by_case):
        raise ValueError("the older response shards do not cover the full panel")
    return by_case, grades, receipts


def prepare(record):
    reference, grades, receipts = reference_grades()
    rows, summary = generation(record)
    if {row["id"] for row in rows} != set(reference):
        raise ValueError("the candidate does not describe exactly the frozen FINAL200 cases")
    reusable, pending, counts = {}, {"ko": [], "en": []}, Counter()
    for row in rows:
        case, language = row["id"], row["language"]
        if any(row[key] != reference[case][key] for key in CASE_FIELDS):
            raise ValueError(f"the candidate case changed: {case}")
        matches = grades.get((case, fingerprint(row)), {})
        if len(matches) == 1:
            decision, sources = next(iter(matches.items()))
            reusable[case] = dict(flags=dict(zip(RUBRIC_KEYS, decision, strict=True)), sources=sorted(sources))
            counts[f"reused_{language}"] += 1
        else:
            pending[language].append({key: row[key] for key in (*CASE_FIELDS, "answer", "repeat_tail")} |
                                     {"finish_reason": row["metadata"]["finish_reason"],
                                      "generated_tokens": row["metadata"]["generated_tokens"]})
            counts[f"pending_{language}"] += 1
            counts["conflicting_prior_decisions"] += int(len(matches) > 1)
    return dict(status="READY_FOR_BLIND_SEMANTIC_REVIEW", answers_sha256=summary["answers"]["concat_sha256"],
                rubric=archived.source(RUBRIC), counts=dict(counts), reusable=reusable, pending=pending,
                reviewed_sources=[archived.source(V3_REVIEW), archived.source(GENERALIZATION / "semantic.json"), *receipts])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = args.record.resolve(strict=True)
    if record.parent != archived.EVIDENCE:
        parser.error("use a local P109C evidence record")
    result = prepare(record)
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    print(result["status"], result["counts"], flush=True)


if __name__ == "__main__":
    main()
