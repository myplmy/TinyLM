"""Replay the frozen TinyLM evaluator on the reference run's actual documents."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import math
import re
import statistics
import sys
from pathlib import Path

from .artifacts import (digest, fresh_dir, json_write, jsonl_write,
                        read_jsonl, sha256_file)
from .harness_run import model_arguments, make_engine

FROZEN_HASHES = {
    "eval_bench_suite.py": "e612d6ca995a5b3c456cf92d697f1455f6bc91dff4925db3dad5505e35761f8f",
    "eval_korean_bench.py": "b12a83c4aa563eb032cbc54a8dc353479f816510010faa845f204874ba328a89",
}


def frozen_module(name):
    path = Path(__file__).with_name("legacy_sources") / name
    if sha256_file(path) != FROZEN_HASHES[name]:
        raise ValueError(f"Frozen legacy source changed: {path}")
    spec = importlib.util.spec_from_file_location("a16_frozen_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    search_path = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        # Frozen scripts prepend their former repository root; do not shadow dependencies.
        sys.path[:] = search_path
    # The source stays byte-identical. Only its run-time data roots are relocated.
    root = Path(__file__).resolve().parents[3]
    module.ROOT = root
    if name == "eval_bench_suite.py":
        module.BENCH = root / "datasets" / "bench"
    else:
        module.DS = root / "datasets"
        module.YNAT = module.DS / "KLUE/klue_benchmark/ynat-v1.1/ynat-v1.1_dev.json"
        module.NLI = module.DS / "KLUE/klue_benchmark/klue-nli-v1.1/klue-nli-v1.1_dev.json"
        module.KORQUAD = module.DS / "KorQuad/KorQuAD_2.1/KorQuAD_v1.0_dev.json"
    return module


def source_key(task, row):
    """No positional joins and no fuzzy text matches; labels are intentionally excluded."""
    fields = {
        "hellaswag": ("activity_label", "ctx_a", "ctx_b", "endings"),
        "piqa": ("goal", "sol1", "sol2"),
        "winogrande": ("sentence", "option1", "option2"),
        "arc_easy": ("id", "question", "choices"),
        "arc_challenge": ("id", "question", "choices"),
        "boolq": ("passage", "question"),
        "mmlu": ("question", "choices"),
        "mmlu_redux": ("question", "choices"),
        "musr": ("narrative", "question", "choices"),
        "kobest_copa": ("premise", "question", "alternative_1", "alternative_2"),
        "kobest_hellaswag": ("context", "ending_1", "ending_2", "ending_3", "ending_4"),
        "lambada": ("text",), "gsm8k": ("question",), "ifeval": ("prompt",),
    }
    selected = {key: row[key] for key in fields[task]}
    if task == "musr" and isinstance(selected["choices"], str):
        selected["choices"] = ast.literal_eval(selected["choices"])
    return digest({"task": task, "input": selected})


def binary_metric(sample, metric):
    value = sample.get(metric)
    if value is None and isinstance(sample.get("metrics"), dict):
        value = sample["metrics"].get(metric)
    # Some classification tasks log (gold, prediction) for the official F1 reducer.
    # Equality is only paired correctness; the aggregate F1 remains upstream's metric.
    if metric == "f1" and isinstance(value, (list, tuple)) and len(value) == 2:
        return int(value[0] == value[1])
    if value not in (0, 1, False, True):
        raise ValueError(f"{metric} is not a scalar per-document 0/1 metric: {value!r}")
    return int(value)


def paired_summary(rows):
    usable = [r for r in rows if r["legacy_status"] == "scored"
              and r.get("legacy_correct") is not None and r.get("reference_correct") is not None]
    if not usable:
        return {"paired_n": 0, "delta": None, "status": "no_common_binary_metric"}
    ref = [r["reference_correct"] for r in usable]
    old = [r["legacy_correct"] for r in usable]
    b = sum(x == 1 and y == 0 for x, y in zip(ref, old))
    c = sum(x == 0 and y == 1 for x, y in zip(ref, old))
    delta = statistics.fmean(x - y for x, y in zip(ref, old))
    return {"paired_n": len(usable), "reference_accuracy_on_common": statistics.fmean(ref),
            "legacy_accuracy_on_common": statistics.fmean(old),
            "delta_reference_minus_legacy": delta, "reference_only_correct": b,
            "legacy_only_correct": c,
            "mcnemar_z_uncorrected": (b - c) / math.sqrt(b + c) if b + c else 0.0,
            "scope": "same checkpoint; scoring-protocol difference, not architecture significance"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    model_arguments(parser)
    parser.add_argument("--reference-run", required=True, type=Path)
    parser.add_argument("--reference-task", required=True, help="Exact leaf task from samples filename.")
    parser.add_argument("--task", required=True, choices=[
        "hellaswag", "piqa", "winogrande", "arc_easy", "arc_challenge", "boolq",
        "mmlu", "mmlu_redux", "musr", "kobest_copa", "kobest_hellaswag",
        "lambada", "gsm8k", "ifeval"])
    parser.add_argument("--metric", default="acc")
    parser.add_argument("--filter", default="none", help="Logged harness filter name.")
    parser.add_argument("--legacy-seq-max", type=int, default=1024)
    parser.add_argument("--legacy-max-new", type=int, default=96)
    parser.add_argument("--no-pmi", action="store_true")
    parser.add_argument("--id-map", type=Path,
                        help="JSON object: reference doc_id -> zero-based legacy cache row; content verified.")
    parser.add_argument("--scoring-only", action="store_true",
                        help="GSM8K/IFEval: reuse reference text to isolate only the scorer.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.scoring_only and args.task not in {"gsm8k", "ifeval"}:
        parser.error("--scoring-only applies to GSM8K and IFEval.")
    refdir = args.reference_run.resolve(strict=True)
    if not (refdir / "completion.json").exists():
        raise ValueError("Reference run is incomplete.")
    identity = json.loads((refdir / "model.json").read_text(encoding="utf-8"))
    if identity.get("checkpoint_sha256") != sha256_file(args.checkpoint):
        raise ValueError("Reference and legacy must use the same TinyLM checkpoint.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.reference_task):
        raise ValueError("Invalid reference task name.")
    complete = json.loads((refdir / "completion.json").read_text(encoding="utf-8"))
    sample_path = refdir / f"samples_{args.reference_task}.jsonl"
    if complete.get("sample_sha256", {}).get(args.reference_task) != sha256_file(sample_path):
        raise ValueError("Reference samples changed or have no A16 integrity record.")
    raw_samples = read_jsonl(sample_path)
    samples = [s for s in raw_samples if s.get("filter", "none") == args.filter]
    if not samples:
        raise ValueError("Selected reference filter contains no samples.")
    old = frozen_module("eval_bench_suite.py")
    datafile = old.BENCH / f"{args.task}.jsonl"
    raw_rows = read_jsonl(datafile)
    index = {}
    for row_index, row in enumerate(raw_rows):
        key = source_key(args.task, row)
        index.setdefault(key, []).append(row_index)
    explicit = json.loads(args.id_map.read_text(encoding="utf-8")) if args.id_map else {}
    matched, seen = [], set()
    for sample in samples:
        key = source_key(args.task, sample["doc"])
        if key not in index:
            raise ValueError("Reference content not in legacy cache; do not compare by row position.")
        candidates = index[key]
        if str(sample["doc_id"]) in explicit:
            chosen = explicit[str(sample["doc_id"])]
            if type(chosen) is not int or chosen not in candidates:
                raise ValueError("Explicit ID map disagrees with source content.")
        elif len(candidates) == 1:
            chosen = candidates[0]
        else:
            raise ValueError("Ambiguous source content. Supply --id-map; rows are never guessed.")
        if chosen in seen:
            raise ValueError("Duplicate paired legacy row; select one filter/unique source IDs.")
        seen.add(chosen)
        matched.append((key, raw_rows[chosen], sample))
    out = fresh_dir(args.output)
    engine = make_engine(args)
    if engine.identity["tokenizer_sha256"] != identity.get("tokenizer_sha256"):
        raise ValueError("Reference and legacy tokenizer files differ.")
    if engine.identity["tinylm_source"]["sha256"] != identity.get("tinylm_source", {}).get("sha256"):
        raise ValueError("TinyLM implementation changed since the reference evaluation.")
    if args.legacy_seq_max > engine.cfg.max_seq_len:
        raise ValueError("Legacy requested sequence exceeds checkpoint max_seq_len.")
    t = engine.torch
    json_write(out / "invocation.json", {
        "model": engine.identity, "reference_run": str(refdir),
        "reference_task": args.reference_task, "reference_metric": args.metric,
        "reference_filter": args.filter, "legacy_task": args.task,
        "legacy_data_sha256": sha256_file(datafile), "frozen_sources": FROZEN_HASHES,
        "legacy_sequence_limit": args.legacy_seq_max,
        "legacy_max_new": args.legacy_max_new, "legacy_no_pmi": args.no_pmi,
        "legacy_cuda_autocast": "bfloat16" if engine.device.type == "cuda" else "float32",
        "scoring_only": args.scoring_only,
        "id_map_sha256": sha256_file(args.id_map) if args.id_map else None,
    })
    records = []
    try:
        for key, raw, sample in matched:
            item = old.ADAPTERS[args.task](raw)
            record = {"source_key": key, "legacy_gold": item.get("gold"),
                      "reference_target": sample.get("target"),
                      "reference_doc_id": sample.get("doc_id"), "legacy_status": "scored"}
            if old.TASKS[args.task][0] == "mc":
                picks, ok, norm, skipped, ce, margin = old.run_mc(
                    args.task, [item], engine.model, engine.tokenizer, engine.device.type,
                    args.legacy_seq_max, t, t.nn.functional, args.no_pmi)
                record["reference_correct"] = binary_metric(sample, args.metric)
                record["legacy_status"] = "skipped_context_or_target" if skipped else "scored"
                record["legacy_correct"] = ok[0] if ok else None
                record["legacy_token_mean_correct"] = norm[0] if norm else None
                record["legacy_prediction"] = next(iter(picks)) if picks else None
                record["legacy_gold_ce"] = ce[0] if ce else None
                record["legacy_margin"] = margin[0] if margin else None
            elif args.task == "lambada":
                ok, ce, skipped = old.run_cloze(
                    [item], engine.model, engine.tokenizer, engine.device.type,
                    args.legacy_seq_max, t, t.nn.functional)
                record.update(reference_correct=binary_metric(sample, args.metric),
                              legacy_correct=ok[0] if ok else None,
                              legacy_word_nll=ce[0] if ce else None,
                              legacy_status="skipped_context" if skipped else "scored")
            else:
                if args.scoring_only:
                    generation = sample["resps"][0][0]
                    if not isinstance(generation, str):
                        raise ValueError("Expected one raw generated response.")
                else:
                    generation = old.greedy(
                        engine.model, engine.tokenizer, engine.device.type, item["ctx"],
                        args.legacy_max_new, args.legacy_seq_max, t,
                        stop=["\nQuestion:", "\n\n\n"])
                record["legacy_response"] = generation
                if args.task == "gsm8k":
                    nums = re.findall(r"-?\d[\d,]*\.?\d*", generation.replace(",", ""))
                    record.update(
                        legacy_correct=int(bool(nums and nums[-1].rstrip(".") == item["gold"])),
                        reference_correct=binary_metric(sample, args.metric))
                else:
                    checks = [old.ifeval_check(iid, kw, generation) for iid, kw in
                              zip(item["meta"]["ids"],
                                  (item["meta"]["kw"] or [{}]) * len(item["meta"]["ids"]))]
                    record.update(legacy_constraint_passed=sum(v is True for v in checks),
                                  legacy_constraint_evaluated=sum(v is not None for v in checks),
                                  legacy_constraint_unsupported=sum(v is None for v in checks),
                                  legacy_correct=None, reference_correct=None,
                                  reference_metrics={k: v for k, v in sample.items()
                                                     if k.startswith(("prompt_", "inst_"))})
            records.append(record)
        jsonl_write(out / "paired_items.jsonl", records)
        summary = paired_summary(records)
        summary.update(requested=len(samples),
                       legacy_skipped=sum(r["legacy_status"] != "scored" for r in records))
        if args.task == "ifeval":
            passed = sum(r["legacy_constraint_passed"] for r in records)
            evaluated = sum(r["legacy_constraint_evaluated"] for r in records)
            summary["legacy_partial_instruction_accuracy"] = passed / evaluated if evaluated else None
            summary["legacy_constraint_evaluated"] = evaluated
            summary["legacy_constraint_unsupported"] = sum(r["legacy_constraint_unsupported"] for r in records)
            summary["note"] = "Compare to results.json's prompt/inst strict/loose separately; denominators differ."
        json_write(out / "comparison.json", summary)
        json_write(out / "completion.json", {"status": "completed"})
    except BaseException as error:
        jsonl_write(out / "partial_items.jsonl", records)
        json_write(out / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise
