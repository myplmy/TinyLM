"""Compare completed P109C evaluation units after either a normal exit or cutoff."""

import argparse
from collections import Counter
import json
from math import fsum, isclose
from pathlib import Path

from scripts.audit_p109c_candidate_official_pairs import CORE_COUNTS, PRIMARY, archived, choice_id, core_id, pairs


GENERATED = {"first_use": 16, "final200": 200}


def binding(record, profile_path):
    profile = archived.read(profile_path)
    receipt = archived.read(record / "evaluation_input.json")
    terminal = archived.read(record / "supervisor.json")
    returned = terminal["card_after_exit"]
    training_record = Path(profile["training_record"]).resolve(strict=True)
    if training_record.parent != archived.EVIDENCE:
        raise ValueError("training must use a local P109C evidence record")
    training = archived.read(training_record / "report.json")
    profile_sha = archived.source(profile_path)["sha256"]
    if (type(terminal["returncode"]) is not int or returned.get("compute_pids") != []
            or returned["sampled_at"] < terminal["ended"]
            or training["status"] != "FULL_SCRATCH_MIXED_COMPLETE"
            or training["tag"] != profile["training_tag"]
            or training["input_manifest_sha256"] != profile["training_manifest_sha256"]
            or receipt["groups"] != profile["groups"] or receipt["mode"] != training["tag"]
            or receipt["model_sha256"] != training["evaluation_sha256"] or receipt["profile_sha256"] != profile_sha):
        raise ValueError("evaluation needs the sealed finished model and an observed device return")
    return profile, receipt, dict(returncode=terminal["returncode"], stop_reason=terminal["stop_reason"],
                                  seconds=terminal["ended"] - terminal["started"])


def unit_rows(record, name, expected, field, model):
    summary = archived.read(record / f"{name}.json")
    manifest = summary[field]
    if (summary["rows"] != expected or manifest["rows"] != expected
            or manifest["lineage"]["model"] != model or manifest["lineage"]["task"] != name):
        raise ValueError(f"the completed {name} denominator or lineage differs")
    rows, _ = archived.shards(record, f"{name}_{field}_shards_manifest.json", manifest)
    return rows, summary


def generation_stats(rows, summary):
    counted = {}
    for language in ("ko", "en"):
        subset = [row for row in rows if row["language"] == language]
        counter = Counter(rows=len(subset))
        for row in subset:
            stop = row["metadata"]["finish_reason"] in ("EOS", "STOP_SEQUENCE")
            match = row["reference_match"]
            counter.update(dict(empty=int(not row["answer"].strip()), stop=int(stop),
                                capped=int(not stop), repeat_tail=int(row["repeat_tail"])))
            if match is not None:
                counter.update(dict(reference_rows=1, reference_match=int(match)))
        if counter != Counter(summary["by_language"][language]):
            raise ValueError("the generation raw answers and reported language counts differ")
        counted[language] = dict(counter)
    return counted


def generation_pair(name, left, right, left_summary, right_summary):
    fields = (("case", "language", "prompt", "expected") if name == "first_use"
              else ("id", "language", "prompt", "category", "match_rule", "reference", "rubric"))
    for field in ("precision", "max_new"):
        if left_summary["answers"]["lineage"][field] != right_summary["answers"]["lineage"][field]:
            raise ValueError(f"the {name} generation precision or budget differs")
    identify = lambda row: tuple(row[key] for key in fields)
    for a, b in zip(left, right, strict=True):
        if identify(a) != identify(b) or (a["reference_match"] is None) != (b["reference_match"] is None):
            raise ValueError(f"the frozen {name} requests or reference denominators differ")
    result = dict(rows=len(left), reference=generation_stats(left, left_summary),
                  candidate=generation_stats(right, right_summary),
                  identical_generated_ids=sum(a["metadata"]["generated_ids"] == b["metadata"]["generated_ids"]
                                              for a, b in zip(left, right, strict=True)),
                  semantic_review="NOT_SCORED_BY_THIS_AUDIT")
    if name == "final200":
        categories = {}
        for a, b in zip(left, right, strict=True):
            label = f"{a['language']}/{a['category']}"
            cell = categories.setdefault(label, Counter())
            cell.update(dict(rows=1, reference_rows=int(a["reference_match"] is not None),
                             reference_only=int(a["reference_match"] is True and b["reference_match"] is False),
                             candidate_only=int(a["reference_match"] is False and b["reference_match"] is True),
                             both_match=int(a["reference_match"] is True and b["reference_match"] is True)))
        result["by_category"] = {name: dict(cell) for name, cell in categories.items()}
    return result


def choice_metrics(rows, summary):
    metrics = summary["metrics"]
    matrix = Counter((row["gold"], row["pred"]) for row in rows)
    classes = sorted({label for cell in matrix for label in cell})
    confusion = [[matrix[gold, pred] for pred in classes] for gold in classes]
    if classes != summary["classes"] or confusion != summary["confusion"]:
        raise ValueError("the choice confusion table differs from the raw decisions")
    if "acc_norm" in metrics:
        correct = sum(row["gold"] == row["pred_norm"] for row in rows)
        if not isclose(correct / len(rows), metrics["acc_norm"], abs_tol=1e-12, rel_tol=0):
            raise ValueError("normalized choice accuracy differs from the raw decisions")
    if "f1" in metrics:
        f1 = []
        for label in classes:
            support = sum(count for (gold, _), count in matrix.items() if gold == label)
            predicted = sum(count for (_, pred), count in matrix.items() if pred == label)
            f1.append(2 * matrix[label, label] / (support + predicted))
        if not isclose(fsum(f1) / len(f1), metrics["f1"], abs_tol=1e-12, rel_tol=0):
            raise ValueError("choice macro-F1 differs from the raw decisions")
    return metrics


def official_pair(name, left, right, left_summary, right_summary):
    if name in PRIMARY:
        metric = PRIMARY[name]
        result = pairs(left, right, core_id, lambda row: row[metric])
        reference = left_summary["official"][metric + ",none"]
        candidate = right_summary["official"][metric + ",none"]
    else:
        metric = "acc"
        result = pairs(left, right, choice_id, lambda row: row["metrics"][metric])
        reference_metrics = choice_metrics(left, left_summary)
        candidate_metrics = choice_metrics(right, right_summary)
        reference, candidate = reference_metrics[metric], candidate_metrics[metric]
        if "f1" in reference_metrics:
            result.update(reference_f1=reference_metrics["f1"], candidate_f1=candidate_metrics["f1"])
    result["reference_only"] = result.pop("v2_only")
    result["reference_hits"] = result.pop("v2_hits")
    result["metric"] = metric
    if not (isclose(result["reference_hits"] / result["rows"], reference, abs_tol=1e-12, rel_tol=0)
            and isclose(result["candidate_hits"] / result["rows"], candidate, abs_tol=1e-12, rel_tol=0)):
        raise ValueError(f"the {name} raw decisions differ from the official score")
    return result


def compare(reference, reference_profile, candidate, candidate_profile):
    base, left, base_terminal = binding(reference, reference_profile)
    current, right, terminal = binding(candidate, candidate_profile)
    metadata = ("schema", "training_manifest_sha256", "groups", "inputs", "sources", "policy")
    if (base_terminal["returncode"] != 0 or base_terminal["stop_reason"] is not None
            or any(base[key] != current[key] for key in metadata) or left["model_sha256"] == right["model_sha256"]):
        raise ValueError("compare a returned reference and a distinct candidate with identical evaluation conditions")
    sizes = dict(GENERATED, **CORE_COUNTS, **{name: item["rows"]
                 for name, item in base["inputs"]["korean_choices"]["requests"].items()})
    completed, missing, evidence = {}, [], {}
    for name, count in sizes.items():
        if not (candidate / f"{name}.json").is_file():
            missing.append(name)
            continue
        kind = "answers" if name in GENERATED else "samples"
        a, a_summary = unit_rows(reference, name, count, kind, left["mode"])
        b, b_summary = unit_rows(candidate, name, count, kind, right["mode"])
        compare_unit = generation_pair if name in GENERATED else official_pair
        completed[name] = compare_unit(name, a, b, a_summary, b_summary)
        evidence[name] = dict(reference=archived.source(reference / f"{name}.json"),
                              candidate=archived.source(candidate / f"{name}.json"))
    core = {name: completed[name] for name in CORE_COUNTS if name in completed}
    kobest = {name: part for name, part in completed.items() if name.startswith("kobest_")}
    aggregates = {}
    if len(core) == len(CORE_COUNTS):
        aggregates["core6"] = {side: fsum(row[f"{side}_hits"] / row["rows"] for row in core.values()) / len(core)
                               for side in ("reference", "candidate")}
    if len(kobest) == 5:
        aggregates["kobest5"] = {side: fsum(row[f"{side}_f1"] for row in kobest.values()) / len(kobest)
                                 for side in ("reference", "candidate")}
    return dict(status="COMPLETED_UNITS_VERIFIED", candidate_terminal=terminal, reference=left, candidate=right,
                completed=completed, missing=missing, aggregates=aggregates, evidence=evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "reference-profile", "candidate", "candidate-profile", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    reference, candidate = (record.resolve(strict=True) for record in (args.reference, args.candidate))
    if reference.parent != archived.EVIDENCE or candidate.parent != archived.EVIDENCE:
        parser.error("use the local P109C evidence records")
    result = compare(reference, args.reference_profile.resolve(strict=True), candidate,
                     args.candidate_profile.resolve(strict=True))
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(dict(result, source=archived.source(Path(__file__).resolve())), ensure_ascii=False, indent=2), file=stream)
    print(result["status"], f"complete={len(result['completed'])}", f"unavailable={len(result['missing'])}", flush=True)


if __name__ == "__main__":
    main()
