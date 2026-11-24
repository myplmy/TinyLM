"""Recount the archived comparators on the exact KoBEST and Belebele rows."""

import argparse
import json
import math
from pathlib import Path
from statistics import mean

from scripts import eval_p109c_completed as evaluation
from scripts import run_p109c_scratch330 as training
from scripts.p106b_shards import verify as verify_shards


ARCHIVE = evaluation.ROOT / "test_result/evidence"
CORE_PANEL = ARCHIVE / "p109c_comparator_assets_cpu_v1_20261121/report.json"
DEFAULT_BELEBELE = "p106b_belebele_v2_s1337/{model}/full/report.json"
BELEBELE = {
    "qwen3508": "p106b_qwen35_extra_official_v2_20261113/belebele/belebele/report.json",
    "bonsai2b": "p106b_bonsai_native_mc_v1_20261118/actual/report.json",
}
KOBEST = {
    "native595-f": "p109c_native595f_kobest_cpu_v2_20261121/report.json",
    "native595-q": "p106b_kobest_exact_followups_v2_20261118/actual/native595-q/report.json",
    "new595-broad-f": "p108_frozen_edit_official_v2_20261113/original/report.json",
    "falcon90m": "p108b_layer_transfer_v2_s1337/external_kobest_v1/report.json",
    "gemma270": "p108b_layer_transfer_v3_s1337/external_gemma_kobest_v2/report.json",
    "qwen3508": "p106b_kobest_gemma_qwen_remaining_v1_20261118/qwen3508/actual/qwen3508/report.json",
    "bonsai2b": "p106b_bonsai_native_kobest_v2_20261118/actual/report.json",
}
QWEN_WIC = "p106b_qwen_hf_kobest_wic_remaining_v1_20261118/actual/qwen3508/report.json"


def archived_task(model, name):
    if name.startswith("kobest_"):
        relative = QWEN_WIC if name == "kobest_wic" and model == "qwen3508" else KOBEST[model]
    else:
        relative = BELEBELE.get(model, DEFAULT_BELEBELE.format(model=model))
    path = ARCHIVE / relative
    report = evaluation.read_json(path)
    if "official_results" in report:
        result = report["official_results"][name]["results"][name]
        metrics = {key: result[key + ",none"] for key in ("acc", "acc_norm", "f1") if key + ",none" in result}
        samples = report["sample_manifests"][name]
    elif "task_result" in report:
        result = report["task_result"]
        samples = result["manifest"]
        metrics = result["metrics"]
    elif "tasks" in report:
        result = report["tasks"][name]
        samples = result.get("samples") or result.get("sample_manifest") or result["manifest"]
        metrics = result["metrics"]
    else:
        language = name.removeprefix("belebele_")
        samples = report["sample_manifests"][language]
        metrics = report["independent_audits"][language]["metrics"]
    return path, samples, metrics, report.get("status")


def recount_task(task, items, path, manifest):
    from scripts.diag_p106b_bonsai_native_mc import aggregate, item_score

    verify_shards(path.parent, manifest)
    raw_rows = []
    for part in manifest["shards"]:
        with (path.parent / part["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                raw_rows.append(json.loads(line))
    audited = []
    for row, expected in zip(raw_rows, items, strict=True):
        if any(row[key] != expected[key] for key in ("doc_id", "doc", "arguments")):
            raise ValueError(f"the original document, choice request or row ID differs: {path} {expected['doc_id']}")
        scores = row.get("responses", row.get("filtered_resps"))
        winner, normalized, metrics = item_score(task, expected, scores)
        audited.append(dict(gold=expected["gold"], pred=winner, pred_norm=normalized, metrics=metrics))
    return aggregate(task, audited)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    profile = json.loads(training.manifest_bytes(args.profile.absolute(), args.profile_sha256))
    stages, proofs = evaluation.load_inputs(("korean_choices",))
    if json.loads(json.dumps(proofs)) != {"korean_choices": profile["inputs"]["korean_choices"]}:
        raise ValueError("the comparator row hashes differ from the admitted P109C evaluation input")
    tasks, items = stages["korean_choices"]
    panel = evaluation.read_json(CORE_PANEL)["panel"]
    scores, references = {}, {}
    for model in panel:
        results = {}
        for name, task in tasks.items():
            if (model == "native595-f" and name.startswith("kobest_")
                    and not (ARCHIVE / KOBEST[model]).is_file()):
                continue
            path, stored, metrics, status = archived_task(model, name)
            if model == "native595-f" and name.startswith("kobest_"):
                original = evaluation.read_json(path)
                if (not original["complete"] or original["device"] != "CPU"
                        or original["checkpoint_sha256"] != panel[model]["weights"]["sha256"]):
                    raise ValueError("the new CPU comparator differs in model identity or completion")
            result = recount_task(task, items[name], path, stored)
            if set(metrics) != set(result["metrics"]) or any(
                    not math.isclose(score, result["metrics"][key], rel_tol=1e-12, abs_tol=1e-12)
                    for key, score in metrics.items()):
                raise ValueError(f"archive metric differs from raw likelihood recount: {model} {name}")
            results[name] = dict(rows=len(items[name]), source=str(path.relative_to(evaluation.ROOT)),
                                 raw_sha256=stored["concat_sha256"], status=status, **result)
            references[str(path.relative_to(evaluation.ROOT))] = evaluation.core6.digest(path)
        kobest = [row["metrics"]["f1"] for name, row in results.items() if name.startswith("kobest_")]
        scores[model] = dict(tasks=results, kobest_rows=sum(row["rows"] for name, row in results.items()
                                                          if name.startswith("kobest_")),
            kobest_macro_f1=mean(kobest) if len(kobest) == 5 else None,
            belebele_ko=results["belebele_kor_Hang"]["metrics"]["acc"],
            belebele_en=results["belebele_eng_Latn"]["metrics"]["acc"])
        print("P109C_COMPARATOR_CHOICES", model, scores[model]["kobest_macro_f1"],
              scores[model]["belebele_ko"], scores[model]["belebele_en"], flush=True)
    args.record.mkdir(exist_ok=False)
    training.publish(args.record / "report.json", dict(source_files=references, raw_matches=proofs["korean_choices"]["requests"],
        scope="SAME_OFFICIAL_ROWS_AND_METRICS_MODEL_PRECISION_AND_HISTORY_DIFFER", models=scores,
        current_p109c_eval_profile_sha256=training.digest(args.profile_sha256),
        model_runs=0, comparator_native595_f_device="CPU"))


if __name__ == "__main__":
    main()
