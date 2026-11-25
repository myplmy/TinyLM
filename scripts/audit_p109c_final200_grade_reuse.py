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


def add_review(path, reference, grades):
    review = archived.read(path)
    rows, summary = generation(path.parent)
    per_case = review["per_case"]
    if (review["status"] != "SEMANTIC_REVIEW_COMPLETED"
            or review["rubric"] != archived.source(RUBRIC)
            or review["answers_sha256"] != summary["answers"]["concat_sha256"]
            or set(per_case) != set(reference) or {row["id"] for row in rows} != set(reference)):
        raise ValueError("the extra reviewed source is not bound to the same rubric and 200 cases")
    for row in rows:
        case = row["id"]
        if any(row[key] != reference[case][key] for key in CASE_FIELDS):
            raise ValueError(f"the extra reviewed source has a changed case: {case}")
        item = per_case[case]
        if (item["language"] != row["language"] or item["category"] != row["category"]
                or item["answer_sha256"] != sha256(row["answer"].encode()).hexdigest().upper()):
            raise ValueError(f"the extra reviewed case has changed metadata: {case}")
        decision = flags(item["flags"])
        grades[case, fingerprint(row)][decision].append(path.parent.name)
    return archived.source(path)


def prepare(record, extra_reviews=()):
    reference, grades, receipts = reference_grades()
    extra = [add_review(path, reference, grades) for path in extra_reviews]
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
                extra_review_sources=extra,
                reviewed_sources=[archived.source(V3_REVIEW), archived.source(GENERALIZATION / "semantic.json"), *receipts, *extra])


def finalize(record, prepared, grade_files):
    rows, summary = generation(record)
    if (prepared["status"] != "READY_FOR_BLIND_SEMANTIC_REVIEW"
            or prepared["answers_sha256"] != summary["answers"]["concat_sha256"]
            or prepared["rubric"] != archived.source(RUBRIC)):
        raise ValueError("the blind review request does not describe these raw answers and rubric")
    extra = [(archived.ROOT / item["path"]).resolve(strict=True) for item in prepared["extra_review_sources"]]
    if any(path.parent.parent != archived.EVIDENCE for path in extra) or prepared != prepare(record, extra):
        raise ValueError("the blind request or reused grade sources differ from their readback")
    prior = archived.read(V3_REVIEW)["semantic_true_ids"]
    by_id = {row["id"]: row for row in rows}
    pending = {row["id"]: row for group in prepared["pending"].values() for row in group}
    reused = prepared["reusable"]
    if set(by_id) != set(reused) | set(pending) or set(reused) & set(pending):
        raise ValueError("blind review and reused cases must partition the full panel")
    for case, pending_row in pending.items():
        source = by_id[case]
        if (any(pending_row[key] != source[key] for key in (*CASE_FIELDS, "answer", "repeat_tail"))
                or any(pending_row[key] != source["metadata"][key] for key in ("finish_reason", "generated_tokens"))):
            raise ValueError(f"the blind review request differs from the actual answer: {case}")
    graded, grade_sources = {}, {}
    for path in grade_files:
        decisions = archived.read(path)
        if path.name in grade_sources or set(decisions) - set(pending) or set(decisions) & set(graded):
            raise ValueError("graded files must be disjoint subsets of the pending cases")
        for case, item in decisions.items():
            decision = dict(zip(RUBRIC_KEYS, flags(item), strict=True))
            if not isinstance(item.get("note"), str):
                raise ValueError(f"a readable note is required for blind adjudication: {case}")
            graded[case] = (decision, path.name, item["note"])
        grade_sources[path.name] = dict(sha256=sha256(path.read_bytes()).hexdigest().upper(), rows=len(decisions))
    if set(pending) != set(graded) or len(by_id) != 200:
        raise ValueError("blind adjudication did not cover all unresolved cases")
    per_case, counts, categories, pair = {}, defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for case, row in by_id.items():
        language, category = row["language"], row["category"]
        if case in reused:
            decision = dict(zip(RUBRIC_KEYS, flags(reused[case]["flags"]), strict=True))
            sources, note = reused[case]["sources"], ""
        else:
            decision, source, note = graded[case]
            sources = [source]
        if decision["stable"] and (not row["answer"].strip() or row["metadata"]["finish_reason"] not in ("STOP_SEQUENCE", "EOS")):
            raise ValueError(f"the review marked a blank or unterminated answer stable: {case}")
        current = dict(total=1, **{key: int(value) for key, value in decision.items()})
        counts[language].update(current)
        categories[f"{language}/{category}"].update(current)
        before, after = case in prior[language]["usable"], decision["usable"]
        outcome = {(True, True): "both", (True, False): "lost", (False, True): "gained", (False, False): "neither"}
        pair[language][outcome[before, after]] += 1
        per_case[case] = dict(language=language, category=category, flags=decision, origin=sources, note=note,
                              answer_sha256=sha256(row["answer"].encode()).hexdigest().upper())
    return dict(status="SEMANTIC_REVIEW_COMPLETED", answers_sha256=prepared["answers_sha256"], rubric=prepared["rubric"],
                reviewed_sources=grade_sources, evidence_for_reuse=prepared["reviewed_sources"],
                counts={key: dict(value) for key, value in counts.items()},
                by_category={key: dict(value) for key, value in categories.items()},
                paired_usable_vs_archived_v3={key: dict(value) for key, value in pair.items()}, per_case=per_case)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-review", action="append", type=Path, default=[])
    parser.add_argument("--blind-request", type=Path)
    parser.add_argument("--grades", action="append", type=Path, default=[])
    args = parser.parse_args()
    record = args.record.resolve(strict=True)
    if record.parent != archived.EVIDENCE:
        parser.error("use a local P109C evidence record")
    extra = [path.resolve(strict=True) for path in args.extra_review]
    if any(path.parent.parent != archived.EVIDENCE for path in extra):
        parser.error("extra reviews must accompany their original completed P109C generation")
    if args.blind_request is not None:
        if extra:
            parser.error("reused sources are determined when the blind request is prepared")
        result = finalize(record, archived.read(args.blind_request), args.grades)
    else:
        if args.grades:
            parser.error("grades require a matching blind request")
        result = prepare(record, extra)
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    print(result["status"], result["counts"], flush=True)


if __name__ == "__main__":
    main()
