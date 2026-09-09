"""Generate canonical HumanEval completions; run official tests only in a separate stage."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from .artifacts import (digest, finite_json, fresh_dir, json_write, jsonl_write,
                        read_jsonl, sha256_file, source_tree, versions)
from .harness_run import model_arguments, make_engine


def problems_for(suite):
    if suite == "human-eval":
        import human_eval
        from human_eval.data import read_problems
        problems = read_problems()
        root = Path(human_eval.__file__).parent
    else:
        import evalplus
        from evalplus.data import get_human_eval_plus
        problems = get_human_eval_plus()
        root = Path(evalplus.__file__).parent
    if len(problems) != 164:
        raise ValueError(f"Expected HumanEval's 164 task IDs, got {len(problems)}.")
    return problems, source_tree(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    model_arguments(generate)
    generate.add_argument("--suite", choices=["human-eval", "evalplus"], required=True)
    generate.add_argument("--max-new", type=int, default=512)
    generate.add_argument("--samples-per-task", type=int, default=1)
    generate.add_argument("--temperature", type=float, default=0.0)
    generate.add_argument("--top-p", type=float, default=1.0)
    generate.add_argument("--stop", action="append",
                          help="Override stop strings by repeating this flag.")
    generate.add_argument("--legacy-generation", action="store_true",
                          help="Frozen old greedy/stops; actual tests still use the official evaluator.")
    generate.add_argument("--output", type=Path, required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--run", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--workers", type=int, default=2)
    evaluate.add_argument("--timeout", type=float, default=3.0)
    evaluate.add_argument("--execute-generated-code", action="store_true", required=True,
                          help="User-run stage: invokes actual official functional tests.")
    args = parser.parse_args(argv)
    if args.command == "generate":
        if args.samples_per_task < 1 or (args.temperature == 0 and args.samples_per_task != 1):
            raise ValueError("Use one completion for greedy pass@1; duplicate greedy samples add no evidence.")
        if args.legacy_generation and (args.temperature != 0 or args.samples_per_task != 1):
            raise ValueError("Legacy generator was greedy only.")
        if args.legacy_generation and args.stop is not None:
            raise ValueError("Legacy mode uses its frozen stop strings; --stop would be misleading.")
        problems, source = problems_for(args.suite)
        out = fresh_dir(args.output)
        engine = make_engine(args)
        stops = (["\ndef ", "\nclass ", "\n#", "\n\n\n"] if args.legacy_generation else
                 args.stop if args.stop is not None else
                 ["\nclass ", "\ndef ", "\n#", "\nif ", "\nprint("])
        metadata = {"suite": args.suite, "model": engine.identity,
                    "problem_digest": digest(problems), "task_ids": list(problems),
                    "max_new": args.max_new, "stop": stops,
                    "samples_per_task": args.samples_per_task, "temperature": args.temperature,
                    "top_p": args.top_p, "legacy_generation": args.legacy_generation,
                    "prompt": "canonical function prefix (base LM)",
                    "postprocessing": ("legacy: stop string retained, no EOS stop" if args.legacy_generation
                                       else "EOS/declared stops only; no repair/sanitize"),
                    "packages": versions("human-eval", "evalplus", "torch", "tokenizers"),
                    "generated_code_executed": False}
        json_write(out / "manifest.json", metadata)
        json_write(out / "official_source.json", source)
        json_write(out / "problems.json", problems)
        samples, details = [], []
        try:
            for task_id, problem in problems.items():
                for sample_index in range(args.samples_per_task):
                    if args.legacy_generation:
                        from .legacy_compare import frozen_module
                        old = frozen_module("eval_bench_suite.py")
                        text = old.greedy(
                            engine.model, engine.tokenizer, engine.device.type, problem["prompt"],
                            args.max_new, engine.max_length, engine.torch,
                            stop=["\ndef ", "\nclass ", "\n#", "\n\n\n"])
                        info = {"text": text, "finish_reason": "legacy_unknown"}
                    else:
                        info = engine.generate(problem["prompt"], args.max_new, stops,
                                               args.temperature, args.top_p)
                        text = info["text"]
                    try:
                        ast.parse(problem["prompt"] + text)
                        syntax_ok = True
                    except (SyntaxError, ValueError):
                        syntax_ok = False
                    samples.append({"task_id": task_id, "completion": text})
                    details.append({"task_id": task_id, "sample_index": sample_index,
                                    "legacy_syntax_ok_on_this_output": syntax_ok, **info})
            jsonl_write(out / "samples.jsonl", samples)
            jsonl_write(out / "generation.jsonl", details)
            json_write(out / "completion.json", {"status": "generated-not-functionally-scored",
                                                "engine_stats": engine.stats,
                                                "samples_sha256": sha256_file(out / "samples.jsonl")})
        except BaseException as error:
            jsonl_write(out / "partial_samples.jsonl", samples)
            json_write(out / "failure.json", {"type": type(error).__name__, "message": str(error)})
            raise
        return

    # No model is loaded in this stage. Run it in a separate, disposable evaluation environment.
    run = args.run.resolve(strict=True)
    meta = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    done = json.loads((run / "completion.json").read_text(encoding="utf-8"))
    if done["samples_sha256"] != sha256_file(run / "samples.jsonl"):
        raise ValueError("Generated completions changed after generation.")
    samples = read_jsonl(run / "samples.jsonl")
    counts = {task: 0 for task in meta["task_ids"]}
    for sample in samples:
        if sample["task_id"] not in counts:
            raise ValueError("Unknown task ID.")
        counts[sample["task_id"]] += 1
    if set(counts.values()) != {meta["samples_per_task"]}:
        raise ValueError("Missing/duplicate task completions or mixed model runs.")
    problems, current_source = problems_for(meta["suite"])
    if digest(problems) != meta["problem_digest"]:
        raise ValueError("Official problem version changed between generation and scoring.")
    out = fresh_dir(args.output)
    # Official evaluators write beside the input. Give them a fresh copy, preserving the generation run.
    jsonl_write(out / "samples.jsonl", samples)
    json_write(out / "scoring_manifest.json", {
        "generation_run": str(run), "suite": meta["suite"], "official_source": current_source,
        "samples_sha256": sha256_file(out / "samples.jsonl"), "workers": args.workers,
        "timeout": args.timeout if meta["suite"] == "human-eval" else "EvalPlus official defaults",
        "packages": versions("human-eval", "evalplus")})
    if args.workers < 1 or args.timeout <= 0:
        raise ValueError("workers and timeout must be positive.")
    if meta["suite"] == "human-eval":
        from human_eval.evaluation import evaluate_functional_correctness
        jsonl_write(out / "problems.jsonl", problems.values())
        scores = evaluate_functional_correctness(
            str(out / "samples.jsonl"), k=[1], n_workers=args.workers,
            timeout=args.timeout, problem_file=str(out / "problems.jsonl"))
        json_write(out / "scores.json", finite_json(scores))
    else:
        from contextlib import redirect_stdout
        from evalplus.evaluate import evaluate
        # EvalPlus owns tests and pass@k. Preserve its printed aggregates as well as
        # per-problem JSON; supported releases use different result filename separators.
        with (out / "official_stdout.txt").open("x", encoding="utf-8") as capture:
            with redirect_stdout(capture):
                evaluate(dataset="humaneval", samples=str(out / "samples.jsonl"),
                         parallel=args.workers, test_details=True, base_only=False)
        print((out / "official_stdout.txt").read_text(encoding="utf-8"))
        result_files = list(out.glob("*eval_results.json"))
        if len(result_files) != 1:
            raise RuntimeError("Expected exactly one official EvalPlus results artifact.")
        json_write(out / "official_outputs.json", {
            "results": result_files[0].name, "sha256": sha256_file(result_files[0]),
            "aggregate_scores": "official_stdout.txt; computed by EvalPlus"})
    json_write(out / "completion.json", {"status": "official-functional-evaluation-completed"})
