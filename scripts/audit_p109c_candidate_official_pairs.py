"""Pair a completed P109C candidate's official decisions with the frozen v2 cohort."""

import argparse
from math import fsum, isclose
from pathlib import Path

from scripts import audit_p109c_frozen_model_comparison as archived


PRIMARY = archived.read(archived.CORE6)["primary_metric"]
CORE_COUNTS = archived.read(archived.CORE6)["denominators"]


def pairs(a, b, identify, score):
    if len(a) != len(b) or not a:
        raise ValueError("matching nonempty official denominators are required")
    base = {identify(row): row for row in a}
    current = {identify(row): row for row in b}
    if set(base) != set(current) or len(base) != len(a) or len(current) != len(b):
        raise ValueError("the evaluated documents, prompts or gold answers differ")
    left = [score(base[case]) for case in base]
    right = [score(current[case]) for case in base]
    if any(value not in (0, 1) for value in (*left, *right)):
        raise ValueError("the paired task must use binary correctness decisions")
    return dict(rows=len(left), both=sum(x == y == 1 for x, y in zip(left, right, strict=True)),
                candidate_only=sum(y > x for x, y in zip(left, right, strict=True)),
                v2_only=sum(x > y for x, y in zip(left, right, strict=True)),
                neither=sum(x == y == 0 for x, y in zip(left, right, strict=True)),
                v2_hits=sum(left), candidate_hits=sum(right))


def collect(record, complement):
    proof_file = record / "report.json"
    proof, returned = (archived.read(path) for path in (proof_file, record / "supervisor.json"))
    if (proof["status"] != "COMPLETE" or returned["returncode"] != 0 or returned["stop_reason"]
            or returned["card_after_exit"].get("compute_pids") != []):
        raise ValueError("the official evaluation needs the successful device return and completed report")
    model = proof["model_sha256"]
    core = {name: (record, item) for name, item in archived.read(record / "core6.json").items()}
    if complement:
        extra = archived.read(complement / "report.json")
        if (extra["status"] != "COMPLETE" or extra["checkpoint_sha256"] != model or "hellaswag" in core
                or extra["task"] != "hellaswag" or extra["rows"] != CORE_COUNTS["hellaswag"]):
            raise ValueError("HellaSwag completion belongs to a different model or duplicates a complete task")
        core["hellaswag"] = complement, extra["official"]
    if set(core) != set(PRIMARY):
        raise ValueError("all six official tasks are required")
    kchoices = archived.read(record / "korean_choices.json")
    return proof, core, kchoices


def artifact_rows(directory, stage, summary):
    rows, stamp = archived.shards(directory, stage + "_samples_shards_manifest.json")
    if len(rows) != summary["rows"] or stamp != summary["samples"]["concat_sha256"]:
        raise ValueError("the original summary and submitted raw decisions differ")
    return rows


def core_id(row):
    return row["doc_id"], row["doc_hash"], row["prompt_hash"], row["target_hash"]


def choice_id(row):
    return row["doc_id"], archived.panel.digest(row["doc"]), archived.panel.digest(row["arguments"]), row["gold"]


def serve(record, complement):
    known, control_core, control_choices = collect(archived.V2_COMMON, archived.HELLASWAG.parent)
    tested, candidate_core, candidate_choices = collect(record, complement)
    scores, parts = {}, {}
    for name, measure in PRIMARY.items():
        a, b = control_core[name], candidate_core[name]
        left, right = artifact_rows(a[0], name, a[1]), artifact_rows(b[0], name, b[1])
        result = pairs(left, right, core_id, lambda row: row[measure])
        if (result["rows"] != CORE_COUNTS[name] or not all(isclose(result[k] / result["rows"],
                contract["official"][measure + ",none"], abs_tol=1e-12)
                for k, contract in (("v2_hits", a[1]), ("candidate_hits", b[1])))):
            raise ValueError("raw exact outcomes failed to reproduce the published official score")
        parts[name] = result
        scores[name] = result["candidate_hits"] / result["rows"]

    if set(control_choices) != set(candidate_choices):
        raise ValueError("the same KoBEST and Belebele tasks are required")
    local = {}
    for name, control in control_choices.items():
        candidate = candidate_choices[name]
        left, right = artifact_rows(archived.V2_COMMON, name, control), artifact_rows(record, name, candidate)
        result = pairs(left, right, choice_id, lambda row: row["metrics"]["acc"])
        if any(not isclose(result[k] / result["rows"], value["metrics"]["acc"], abs_tol=1e-12)
               for k, value in (("v2_hits", control), ("candidate_hits", candidate))):
            raise ValueError("raw Korean and Belebele decisions did not recover the official accuracy")
        if "f1" in control["metrics"]:
            result.update(v2_f1=control["metrics"]["f1"], candidate_f1=candidate["metrics"]["f1"])
        local[name] = result
    f1 = [row["candidate_f1"] for name, row in local.items() if name.startswith("kobest_")]
    if len(f1) != 5 or sum(row["rows"] for name, row in local.items() if name.startswith("kobest_")) != 4561:
        raise ValueError("the official KoBEST mixture changed")
    official = archived.official()
    evidence = [record / name for name in ("report.json", "supervisor.json", "core6.json", "korean_choices.json")]
    if complement:
        evidence.append(complement / "report.json")
    return dict(status="FROZEN_P109C_OFFICIAL_ITEM_PAIRS_VERIFIED", model_sha256=tested["model_sha256"],
                v2_model_sha256=known["model_sha256"], sources=[archived.source(path) for path in evidence],
                cohort=official, candidate=dict(core6=fsum(scores.values()) / 6, core6_by_task=scores,
                kobest=fsum(f1) / 5, belebele=[local[name]["candidate_hits"]
                for name in ("belebele_kor_Hang", "belebele_eng_Latn")]), core6_pairs=parts, choice_pairs=local)


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--hellaswag-complement", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = args.record.resolve(strict=True)
    complement = args.hellaswag_complement.resolve(strict=True) if args.hellaswag_complement else None
    if record.parent != archived.EVIDENCE or (complement and complement.parent != archived.EVIDENCE):
        parser.error("completed P109C evidence directories are required")
    result = serve(record, complement)
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(dict(result, source=archived.source(Path(__file__).resolve())), ensure_ascii=False, indent=2), file=stream)
    print(result["status"], result["candidate"], flush=True)


if __name__ == "__main__":
    main()
