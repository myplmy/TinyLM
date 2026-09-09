"""KLUE official metrics on preserved predictions; KorQuAD 1.0 answer generation/scoring."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from .artifacts import (digest, fresh_dir, json_write, jsonl_write, read_jsonl,
                        sha256_file, versions)
from .harness_run import model_arguments, make_engine


def classification_metrics(gold, predictions, labels):
    if not gold or len(gold) != len(predictions):
        raise ValueError("Require one prediction per labeled example.")
    if any(x not in labels for x in gold + predictions):
        raise ValueError("Unknown label; do not silently discard predictions.")
    per_label = {}
    for label in labels:
        tp = sum(a == b == label for a, b in zip(gold, predictions))
        fp = sum(a != label and b == label for a, b in zip(gold, predictions))
        fn = sum(a == label and b != label for a, b in zip(gold, predictions))
        per_label[str(label)] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    return {"accuracy": sum(a == b for a, b in zip(gold, predictions)) / len(gold),
            "macro_f1": sum(per_label.values()) / len(labels), "per_label_f1": per_label,
            "n": len(gold), "scale": "0..1"}


def unique_predictions(records):
    result = {}
    for row in records:
        key = row["guid"]
        if key in result:
            raise ValueError(f"Duplicate prediction guid: {key}")
        result[key] = row["prediction"]
    return result


def qa_rows(dataset):
    rows, seen = [], set()
    if not isinstance(dataset.get("data"), list):
        raise ValueError("Expected KorQuAD v1.0 data/paragraphs/qas, not v2.0.")
    for article in dataset["data"]:
        for paragraph in article["paragraphs"]:
            for qa in paragraph["qas"]:
                if qa["id"] in seen:
                    raise ValueError("Duplicate QA id.")
                seen.add(qa["id"])
                rows.append({"guid": qa["id"], "context": paragraph["context"],
                             "question": qa["question"],
                             "answers": [x["text"] for x in qa["answers"]]})
    if not rows:
        raise ValueError("Empty QA dataset.")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    classify = sub.add_parser("klue")
    model_arguments(classify, required=False)
    classify.add_argument("--task", choices=["ynat", "nli"], required=True)
    classify.add_argument("--dataset", type=Path,
                          help="Override the existing KLUE v1.1 dev file explicitly.")
    classify.add_argument("--predictions", type=Path,
                          help="JSONL {guid, prediction}; scores without loading any model.")
    classify.add_argument("--legacy-seq-max", type=int, default=1024)
    classify.add_argument("--output", type=Path, required=True)
    generate = sub.add_parser("korquad-generate")
    model_arguments(generate)
    generate.add_argument("--dataset", type=Path)
    generate.add_argument("--max-new", type=int, default=64)
    generate.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("korquad-score")
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--scorer", type=Path, required=True,
                       help="Official KorQuAD 1.0 evaluate-v1.0.py, not local evaluate-2.0.py.")
    score.add_argument("--scorer-sha256", required=True,
                       help="Digest of the official file you obtained and reviewed.")
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "korquad-score":
        run = args.run.resolve(strict=True)
        complete = json.loads((run / "completion.json").read_text(encoding="utf-8"))
        meta = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        predictions = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
        dataset = json.loads((run / "dataset.json").read_text(encoding="utf-8"))
        if digest(dataset) != meta["dataset_digest"]:
            raise ValueError("QA source changed after generation.")
        if sha256_file(run / "predictions.json") != complete["predictions_sha256"]:
            raise ValueError("Predictions changed after generation.")
        expected = {row["guid"] for row in qa_rows(dataset)}
        if set(predictions) != expected or any(not isinstance(v, str) for v in predictions.values()):
            raise ValueError("Predictions must cover every QA id exactly once.")
        scorer_hash = sha256_file(args.scorer)
        if args.scorer.name != "evaluate-v1.0.py" or scorer_hash != args.scorer_sha256.lower():
            raise ValueError("Wrong scorer filename/hash. Do not use the KorQuAD 2.0 evaluator.")
        spec = importlib.util.spec_from_file_location("a16_official_korquad_v1", args.scorer)
        official = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(official)
        out = fresh_dir(args.output)
        # The official function owns Korean normalization, all-gold max, EM and character F1.
        scores = official.evaluate(dataset["data"], predictions)
        if not {"exact_match", "f1"}.issubset(scores):
            raise ValueError("Scorer API is not the expected official KorQuAD 1.0 evaluator.")
        json_write(out / "scores.json", scores)
        json_write(out / "manifest.json", {
            "generation_run": str(run), "scorer": str(args.scorer.resolve()),
            "scorer_sha256": scorer_hash, "dataset_digest": meta["dataset_digest"],
            "n": len(expected), "scale": "official 0..100", "split": "local dev",
            "verification": "user-supplied official scorer; hash checks identity, not authorship"})
        json_write(out / "completion.json", {"status": "completed"})
        return

    from .legacy_compare import frozen_module
    old = frozen_module("eval_korean_bench.py")
    if args.command == "klue":
        if bool(args.checkpoint) == bool(args.predictions):
            parser.error("Choose exactly one of --checkpoint and --predictions.")
        dataset_path = args.dataset or (old.YNAT if args.task == "ynat" else old.NLI)
        rows = json.loads(dataset_path.read_text(encoding="utf-8"))
        if not rows or len({r["guid"] for r in rows}) != len(rows):
            raise ValueError("Empty dataset or duplicate guids.")
        labels = old.YNAT_LABELS if args.task == "ynat" else list(old.NLI_LABELS)
        gold_field = "label" if args.task == "ynat" else "gold_label"
        out = fresh_dir(args.output)
        records, engine = [], None
        if args.predictions:
            supplied = unique_predictions(read_jsonl(args.predictions))
            if set(supplied) != {r["guid"] for r in rows}:
                raise ValueError("Prediction guids must match the complete dataset.")
            records = [{"guid": r["guid"], "gold": r[gold_field],
                        "prediction": supplied[r["guid"]]} for r in rows]
        else:
            engine = make_engine(args)
            if args.legacy_seq_max > engine.cfg.max_seq_len:
                raise ValueError("Legacy context limit exceeds checkpoint maximum.")
            if args.task == "ynat":
                old.YNAT = dataset_path
            else:
                old.NLI = dataset_path
            items = old.load_items(args.task, len(rows), args.seed)
            try:
                for prompt, choices, gold, guid, empty in items:
                    values, _ = old.score_continuations(
                        engine.model, engine.tokenizer, engine.device.type, prompt, choices,
                        args.legacy_seq_max, engine.torch, engine.torch.nn.functional)
                    if values is None:
                        raise ValueError(f"{guid}: context overflow; full-dev score would be invalid.")
                    base, _ = old.score_continuations(
                        engine.model, engine.tokenizer, engine.device.type, empty, choices,
                        args.legacy_seq_max, engine.torch, engine.torch.nn.functional)
                    scores = ([a[0] - b[0] for a, b in zip(values, base)]
                              if base is not None else [a[0] for a in values])
                    pick = min(range(len(scores)), key=scores.__getitem__)
                    records.append({"guid": guid, "gold": labels[gold], "prediction": labels[pick]})
            except BaseException as error:
                jsonl_write(out / "partial_predictions.jsonl", records)
                json_write(out / "failure.json", {"type": type(error).__name__, "message": str(error)})
                raise
        metrics = classification_metrics([r["gold"] for r in records],
                                         [r["prediction"] for r in records], labels)
        jsonl_write(out / "predictions.jsonl", records)
        json_write(out / "scores.json", {
            **metrics, "primary_metric": "macro_f1" if args.task == "ynat" else "accuracy",
            "legacy_accuracy_same_predictions": metrics["accuracy"]})
        json_write(out / "manifest.json", {
            "task": args.task, "dataset": str(dataset_path.resolve()),
            "dataset_sha256": sha256_file(dataset_path), "split": "full supplied dev",
            "predictor": "supplied labels" if args.predictions else "frozen TinyLM zero-shot label PMI",
            "model": engine.identity if engine else None, "legacy_seq_max": args.legacy_seq_max,
            "legacy_cuda_autocast": "bfloat16" if engine and engine.device.type == "cuda" else None,
            "metric_equivalence": "NLI accuracy unchanged; YNAT adds official macro F1",
            "leaderboard_equivalence": "not automatic: split, data exposure and training setting must match"})
        json_write(out / "completion.json", {"status": "completed"})
        return

    dataset_path = args.dataset or old.KORQUAD
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = qa_rows(dataset)
    out = fresh_dir(args.output)
    engine = make_engine(args)
    json_write(out / "manifest.json", {
        "task": "KorQuAD-1.0", "dataset_path": str(dataset_path.resolve()),
        "dataset_sha256": sha256_file(dataset_path), "dataset_digest": digest(dataset),
        "model": engine.identity, "n": len(rows), "split": "full supplied dev",
        "prompt": "same Korean context/question/answer prefix as legacy",
        "generation": {"max_new": args.max_new, "temperature": 0, "stop": ["\n"]},
        "answer_postprocessing": "trim surrounding whitespace, no gold-based repair",
        "packages": versions("torch", "tokenizers")})
    json_write(out / "dataset.json", dataset)
    predictions, details = {}, []
    try:
        for row in rows:
            prompt = f"지문: {row['context']}\n질문: {row['question']}\n답:"
            info = engine.generate(prompt, args.max_new, ["\n"])
            predictions[row["guid"]] = info["text"].strip()
            details.append({"guid": row["guid"], **info})
        json_write(out / "predictions.json", predictions)
        jsonl_write(out / "generation.jsonl", details)
        json_write(out / "completion.json", {
            "status": "generated-not-scored", "engine_stats": engine.stats,
            "predictions_sha256": sha256_file(out / "predictions.json")})
    except BaseException as error:
        json_write(out / "partial_predictions.json", predictions)
        json_write(out / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise
