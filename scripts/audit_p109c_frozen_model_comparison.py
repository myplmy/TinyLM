"""Join archived FINAL200 decisions and the common P109C official scorecards."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import fsum, isclose
from pathlib import Path

from scripts import audit_p109c_final200_termination as previous


ROOT, EVIDENCE, panel = previous.ROOT, previous.EVIDENCE, previous.panel
NATIVE_F = EVIDENCE / "p109c_native_final200_cpu_v1_20261121"
NATIVE_Q = EVIDENCE / "p106b_final200_v2_20261101"
V1_CPU = EVIDENCE / "p109c_final200_fp32_cpu_20261122"
V1_COMMON = EVIDENCE / "p109c_completed_eval_v5_20261122"
V2_COMMON = EVIDENCE / "p109c_v2_common_eval_resilient_20261123"
HELLASWAG = EVIDENCE / "p109c_v2_common_eval_hellaswag_cpu_v2_20261123/report.json"
CORE6 = EVIDENCE / "p109c_comparator_core6_recount_cpu_20261121/report.json"
KO = EVIDENCE / "p109c_comparator_ko_choices_cpu_v2_20261121/report.json"
BASELINE = "tinylm_v2"
FIELDS = previous.RUBRIC_KEYS


def digest(data):
    return sha256(data).hexdigest().upper()


def source(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path.read_bytes()))


def read(path):
    return json.loads(path.read_bytes())


def shards(directory, name, expected=None):
    local = directory / name
    manifest = read(local)
    parts = []
    for item in manifest["shards"]:
        if Path(item["path"]).name != item["path"]:
            raise ValueError("the frozen answer shards must belong to the declared directory")
        segment = (directory / item["path"]).read_bytes()
        if (len(segment) != item["bytes"] or len(segment.splitlines()) != item["rows"]
                or digest(segment) != item["sha256"]):
            raise ValueError("one archived response shard changed")
        parts.append(segment)
    joined = b"".join(parts)
    if (len(joined) != manifest["bytes"] or len(joined.splitlines()) != manifest["rows"]
            or digest(joined) != manifest["concat_sha256"] or (expected is not None and manifest != expected)):
        raise ValueError("the joined raw responses differ from the declared report")
    return [json.loads(line) for line in joined.splitlines()], digest(joined)


def split_decisions(all_rows, decisions):
    by_id = {r["id"]: r for r in all_rows}
    normalized = {lang: {key: [] for key in FIELDS} for lang in ("ko", "en")}
    if len(decisions) != len(by_id) or {r["id"] for r in decisions} != set(by_id):
        raise ValueError("one semantic decision per frozen raw answer is required")
    for decision in decisions:
        item = by_id[decision["id"]]
        answer_json = json.dumps(item["answer"], ensure_ascii=False).encode()
        if decision["raw_answer_sha256"].upper() != digest(answer_json):
            raise ValueError("a stored semantic decision refers to a different answer")
        for field in FIELDS:
            if type(decision[field]) is not bool:
                raise ValueError("only completed boolean semantic decisions belong in the comparison")
            if decision[field]:
                normalized[item["language"]][field].append(item["id"])
    return normalized


def native_controls(canonical, rubric):
    manual = read(NATIVE_F / "semantic_readback.json")
    if manual["protocol_input_sha256"] != canonical or manual["rubric_sha256"] != rubric:
        raise ValueError("the original FP32 native comparisons used a different panel or rubric")
    result = {}
    for key in ("native595-f", "new595-broad-f"):
        record = NATIVE_F / key
        verdict = manual["models"][key]
        report = previous.pinned_json(record / "report.json", verdict["response_report_sha256"])
        rows, stamp = shards(record / "answers", "responses_shards_manifest.json", report["answers"])
        if stamp != verdict["answer_concat_sha256"] or report["final_input_sha256"] != canonical:
            raise ValueError("the native FP32 raw answers differ from their reviewed source")
        flags = split_decisions(rows, verdict["decisions"])
        result[key] = (rows, flags, verdict["counts"], dict(report=source(record / "report.json"),
                           answers_sha256=stamp, review=source(NATIVE_F / "semantic_readback.json"),
                           device=report["device"], precision=report["precision"]))
    record = NATIVE_Q / "native595-q"
    summary_path = NATIVE_Q / "readback/native595-q_summary.json"
    summary = read(summary_path)
    proof = summary["proof"]
    report = previous.pinned_json(record / "report.json", proof["report_sha256"])
    rows, stamp = shards(record / "answers", "responses_shards_manifest.json", report["answers"])
    if stamp != proof["response_concat_sha256"] or proof["input_sha256"] != canonical:
        raise ValueError("the quantized Native595 report and reviewed raw answers differ")
    decisions = []
    for item in summary["packets"]:
        packet = previous.pinned_json(ROOT / item["path"], item["sha256"])
        if packet["proof"] != proof or packet["rubric_sha256"] != rubric:
            raise ValueError("the Native595-Q per-task semantic packet changed")
        decisions.extend(packet["rows"])
    result["native595-q"] = (rows, split_decisions(rows, decisions), summary["metrics"],
        dict(report=source(record / "report.json"), answers_sha256=stamp, review=source(summary_path),
             device="cuda", precision="ARCHIVED_FP32_QUANTIZED_NATIVE"))
    return result


def comparator_sources(canonical):
    ext_file = previous.EXTERNAL / "semantic_readback.json"
    self_file = previous.TINYLM / "semantic_readback.json"
    ext, v2 = read(ext_file), read(self_file)
    rubric = ext["rubric_sha256"]
    if (canonical != ext["frozen_final_sha256"] or v2["rubric_sha256"] != rubric
            or digest((ROOT / ext["rubric_file"]).read_bytes()) != rubric):
        raise ValueError("the archived semantic comparisons require the current frozen reference protocol")
    result = native_controls(canonical, rubric)
    for key in previous.MODELS:
        rows, flags, counts, _ = previous.evidence(key, ext, v2)
        if key == BASELINE:
            provenance = dict(answers_sha256=v2["source_sha256"], review=source(self_file),
                              precision=v2["final200_generation_precision"])
        else:
            registered = ext["models"][key]
            provenance = dict(answers_sha256=registered["source_sha256"], review=source(ext_file),
                              report=source(ROOT / registered["generation_receipt"]))
        result[key] = rows, flags, counts, provenance
    base_path = V1_CPU / "precision_readback.json"
    v1, receipt = read(base_path), read(V1_CPU / "report.json")
    rows, stamp = shards(V1_CPU, "responses_shards_manifest.json", receipt["answers"])
    if receipt["final_input_sha256"] != canonical or stamp != v1["cpu_answers_sha256"]:
        raise ValueError("the v1 CPU generation differs from the archived precision readback")
    result["tinylm_v1"] = rows, v1["semantic_true_ids"], v1["cpu_counts"], dict(
        answers_sha256=stamp, report=source(V1_CPU / "report.json"), review=source(base_path),
        device=receipt["device"], precision=receipt["precision"])
    return result, rubric


def summarize(rows, flags, archived, canonical):
    if len(rows) != len(canonical) or any(
            any(row[key] != val for key, val in expected.items()) for row, expected in zip(rows, canonical, strict=True)):
        raise ValueError("the raw questions, references, required form and order must match the frozen panel")
    outcomes, groups = {}, {}
    for lang in ("ko", "en"):
        language_rows = [row for row in rows if row["language"] == lang]
        observed = {row["id"] for row in language_rows}
        sets = None if flags is None else {key: set(flags[lang][key]) for key in FIELDS}
        if sets is not None and (any(len(sets[key]) != len(flags[lang][key]) or not sets[key] <= observed for key in FIELDS)
                or sets["usable"] != sets["stable"] & sets["responsive"] & sets["correct"]):
            raise ValueError("the usage decision must equal stability, responsiveness and correctness")
        for row in language_rows:
            category = f"{lang}/{row['category']}"
            state = {key: None if sets is None else row["id"] in sets[key] for key in FIELDS}
            reference = panel.reference_match(row["answer"], row)
            if reference != row["reference_match"]:
                raise ValueError("the archived automatic comparison does not match its actual raw answer")
            state.update(category=category, reference_match=reference, has_reference=reference is not None,
                         blank=not row["answer"].strip(), finish=row["metadata"]["finish_reason"])
            outcomes[row["id"]] = state
            groups.setdefault(category, []).append(state)
        if sets is not None and any(archived[lang][key] != len(sets[key])
                                    for key in FIELDS if key in archived[lang]):
            raise ValueError("the original semantic tally differs from the linked item decisions")

    def totals(items):
        return dict(rows=len(items), reference_rows=sum(row["has_reference"] for row in items),
                    reference_match=sum(row["reference_match"] is True for row in items), blank=sum(row["blank"] for row in items),
                    finishes=dict(Counter(row["finish"] for row in items)),
                    **{key: None if flags is None else sum(row[key] for row in items) for key in FIELDS})

    return dict(by_category={key: totals(rows) for key, rows in groups.items()},
                by_language={lang: totals([row for row in outcomes.values() if row["category"].startswith(lang + "/")])
                             for lang in ("ko", "en")}, rows=outcomes)


def pair(left, right):
    result = {}
    categories = ("all", "ko", "en", *left["by_category"])
    for group in categories:
        ids = [key for key, row in left["rows"].items()
               if group == "all" or group in (row["category"], row["category"].split("/")[0])]
        attached = {}
        for field in ("reference_match", "usable"):
            domain = [i for i in ids if field != "reference_match" or left["rows"][i]["has_reference"]]
            if domain and all(left["rows"][i][field] is not None and right["rows"][i][field] is not None for i in domain):
                compared = [(left["rows"][i][field], right["rows"][i][field]) for i in domain]
                attached[field] = dict(rows=len(compared), both=sum(a and b for a, b in compared),
                    left_only=sum(a and not b for a, b in compared), right_only=sum(b and not a for a, b in compared),
                    neither=sum(not a and not b for a, b in compared))
        result[group] = attached
    return result


def official():
    original, korean = read(CORE6), read(KO)
    metrics, expected = original["primary_metric"], original["denominators"]
    out = {}
    for key, arm in original["comparators"].items():
        for name, stamp in arm["reports"].items():
            if digest((ROOT / name).read_bytes()) != stamp:
                raise ValueError("a historical official report changed since its recount")
        if not isclose(fsum(arm["per_task"].values()) / len(metrics), arm["macro6"], abs_tol=1e-12):
            raise ValueError("the archived Core6 macro-average differs from its source scores")
        row = korean["models"][key]
        out[key] = dict(core6=arm["macro6"], core6_by_task=arm["per_task"], kobest=row["kobest_macro_f1"],
                        belebele=[round(900 * row[name]) for name in ("belebele_ko", "belebele_en")])
    for name, stamp in korean["source_files"].items():
        if digest((ROOT / name).read_bytes()) != stamp:
            raise ValueError("a stored Korean or Belebele source changed after its recount")
    for key, directory in (("tinylm_v1", V1_COMMON), (BASELINE, V2_COMMON)):
        core, choices = (read(directory / name) for name in ("core6.json", "korean_choices.json"))
        if key == BASELINE:
            extra = read(HELLASWAG)
            if read(directory / "report.json")["model_sha256"] != extra["checkpoint_sha256"]:
                raise ValueError("the separately recovered HellaSwag belongs to another checkpoint")
            core["hellaswag"] = extra["official"]
        if set(core) != set(metrics) or any(core[name]["rows"] != expected[name] for name in core):
            raise ValueError("the P109C official panel denominators differ")
        per_task = {name: core[name]["official"][metric + ",none"] for name, metric in metrics.items()}
        ko = [value for name, value in choices.items() if name.startswith("kobest_")]
        if len(ko) != 5 or sum(q["rows"] for q in ko) != 4561:
            raise ValueError("the frozen KoBEST shape differs")
        out[key] = dict(core6=fsum(per_task.values()) / 6, core6_by_task=per_task,
                        kobest=fsum(row["metrics"]["f1"] for row in ko) / 5,
                        belebele=[round(900 * choices[k]["metrics"]["acc"])
                                  for k in ("belebele_kor_Hang", "belebele_eng_Latn")])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-record", type=Path)
    parser.add_argument("--candidate-name")
    parser.add_argument("--candidate-semantic", type=Path)
    args = parser.parse_args()
    if bool(args.candidate_record) != bool(args.candidate_name) or (args.candidate_semantic and not args.candidate_record):
        parser.error("a candidate directory and name go together")
    frozen = panel.build("final")
    canonical = panel.digest(frozen).upper()
    archives, rubric = comparator_sources(canonical)
    if args.candidate_record:
        record = args.candidate_record.resolve(strict=True)
        if record.parent != EVIDENCE or not args.candidate_name or args.candidate_name in archives:
            parser.error("the candidate needs a new name and its own evidence directory")
        names = [name for name in ("final200_answers_shards_manifest.json", "responses_shards_manifest.json")
                 if (record / name).exists()]
        if len(names) != 1:
            raise ValueError("the candidate must have one completed FINAL200 manifest")
        rows, stamp = shards(record, names[0])
        review = read(args.candidate_semantic) if args.candidate_semantic else None
        if review and (review["source_sha256"] != stamp or review["rubric_sha256"] != rubric):
            raise ValueError("the optional semantic readback refers to different raw responses or rubric")
        proof = dict(answers_sha256=stamp, manifest=source(record / names[0]))
        if review:
            proof["review"] = source(args.candidate_semantic.absolute())
        archives[args.candidate_name] = (rows, review["semantic_true_ids"] if review else None,
                                         review["counts"] if review else {}, proof)
    gathered, sources = {}, {}
    for key, (rows, flags, counts, proof) in archives.items():
        gathered[key] = summarize(rows, flags, counts, frozen)
        sources[key] = proof
    focus = args.candidate_name or BASELINE
    result = dict(status="ARCHIVED_FROZEN_MODEL_COMPARISON_VERIFIED", source=source(Path(__file__).resolve()),
                  final200_sha256=canonical, rubric_sha256=rubric, comparison_target=focus,
                  source_artifacts=sources, official_sources=[source(p) for p in (CORE6, KO, HELLASWAG)],
                  official=official(), final200=gathered,
                  paired={key: pair(gathered[focus], value) for key, value in gathered.items() if key != focus})
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    print(result["status"], len(gathered), len(frozen), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
