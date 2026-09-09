"""Reference task execution through the pinned EleutherAI evaluator."""
from __future__ import annotations

import argparse
import importlib.metadata
import sys
from pathlib import Path

from .artifacts import (finite_json, fresh_dir, json_write, jsonl_write,
                        sha256_file, source_tree, versions)

HARNESS_VERSION = "0.4.13"
PROFILES = {
    "core": ["hellaswag", "piqa", "winogrande", "arc_easy", "arc_challenge", "boolq"],
    "knowledge": ["mmlu", "mmlu_redux"],
    "korean": ["kobest_copa", "kobest_hellaswag"],
    "lambada": ["lambada_openai"],
    "gsm8k": ["gsm8k"],
    "ifeval": ["ifeval"],
    # Documented Open LLM Leaderboard v2 MC protocol, not the MuSR paper's CoT.
    "musr": ["leaderboard_musr"],
}


def model_arguments(parser, required=True):
    parser.add_argument("--checkpoint", type=Path, required=required)
    parser.add_argument("--data", default="ko-en")
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda", "cuda:0"], default="cpu")
    parser.add_argument("--dtype", choices=["float32", "bfloat16"], default="float32")
    parser.add_argument("--max-length", type=int)
    parser.add_argument("--overflow", choices=["error", "left"], default="error")
    parser.add_argument("--seed", type=int, default=99)


def make_engine(args):
    from .engine import TinyLMEngine
    return TinyLMEngine(args.checkpoint, args.data, args.device, args.dtype,
                        args.max_length, args.overflow, args.tokenizer, args.seed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    model_arguments(parser, required=False)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--profile", choices=sorted(PROFILES))
    selection.add_argument("--tasks", nargs="+", help="Exact upstream task/group names.")
    parser.add_argument("--shots", type=int, default=None,
                        help="Omit for task defaults; zero is an explicit override.")
    parser.add_argument("--limit", type=int, help="Pilot only; per LEAF task, not per group.")
    parser.add_argument("--max-gen-toks", type=int, default=256,
                        help="Adapter fallback; explicit upstream limits win.")
    parser.add_argument("--generation-budget", type=int,
                        help="Explicit task limit override, recorded as a protocol change.")
    parser.add_argument("--kv-cache", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hf-model", type=Path, help="External LOCAL HF model directory.")
    args = parser.parse_args(argv)
    if bool(args.checkpoint) == bool(args.hf_model):
        parser.error("Choose exactly one of --checkpoint and --hf-model.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive; omit for full split.")
    if args.shots is not None and args.shots < 0:
        parser.error("--shots must be nonnegative.")
    installed = importlib.metadata.version("lm_eval")
    if installed != HARNESS_VERSION:
        raise RuntimeError(f"Requires lm_eval=={HARNESS_VERSION}; installed={installed}.")
    import lm_eval
    from lm_eval import evaluator
    tasks = PROFILES[args.profile] if args.profile else args.tasks
    if any(t in {"all", "arc_easy_full", "stage1_heldout", "humaneval", "bfcl_v3"}
           or "*" in t for t in tasks):
        raise ValueError("Use exact reference tasks; code/BFCL have separate runners.")
    out = fresh_dir(args.output)
    source = source_tree(Path(lm_eval.__file__).parent)
    json_write(out / "harness_source.json", source)
    invocation = {"argv": sys.argv if argv is None else argv, "tasks": tasks,
                  "shots_override": args.shots, "limit_per_leaf": args.limit,
                  "generation_budget_override": args.generation_budget,
                  "raw_prompts": True, "use_kv_cache": args.kv_cache,
                  "packages": versions("lm_eval", "torch", "tokenizers", "transformers",
                                       "datasets", "evaluate"),
                  "protocol": "reference-full-split" if args.limit is None else "reference-pilot"}
    json_write(out / "invocation.json", invocation)
    engine = None
    try:
        if args.hf_model is not None:
            from lm_eval.models.huggingface import HFLM
            hf_path = args.hf_model.resolve(strict=True)
            model = HFLM(pretrained=str(hf_path), tokenizer=str(hf_path),
                         device=args.device, dtype=args.dtype, batch_size=1,
                         max_length=args.max_length, trust_remote_code=False)
            identity = {"local_hf_model": str(hf_path),
                        "files": {p.relative_to(hf_path).as_posix(): sha256_file(p)
                                  for p in sorted(hf_path.rglob("*"))
                                  if p.is_file() and p.suffix in {
                                      ".json", ".model", ".safetensors", ".bin"}},
                        "adapter": "upstream HFLM", "overflow": "upstream left truncation",
                        "apply_chat_template": False}
        else:
            from .lm_adapter import TinyLMHarness
            engine = make_engine(args)
            model = TinyLMHarness(engine, args.max_gen_toks, args.kv_cache)
            identity = engine.identity
        json_write(out / "model.json", identity)
        generation = None if args.generation_budget is None else {
            "max_gen_toks": args.generation_budget, "do_sample": False, "temperature": 0.0}
        result = evaluator.simple_evaluate(
            model=model, tasks=tasks, num_fewshot=args.shots, batch_size=1,
            limit=args.limit, log_samples=True, cache_requests=False, use_cache=None,
            apply_chat_template=False, gen_kwargs=generation,
            random_seed=args.seed, numpy_random_seed=args.seed,
            torch_random_seed=args.seed, fewshot_random_seed=args.seed,
            confirm_run_unsafe_code=False,
        )
        if not result or not result.get("results") or not result.get("samples"):
            raise RuntimeError("No scored samples returned; not a successful benchmark.")
        samples = result.pop("samples")
        for task_name, config in result.get("configs", {}).items():
            if "mmlu_redux" in task_name and "redux" not in str(config.get("dataset_path", "")).lower():
                raise RuntimeError("Redux task points at a non-Redux dataset; upstream configuration mismatch.")
        json_write(out / "results.json", finite_json(result))
        for task, rows in samples.items():
            if not task.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"Unsafe task filename: {task}")
            if not rows:
                raise RuntimeError(f"No samples for {task}")
            jsonl_write(out / f"samples_{task}.jsonl", finite_json(rows))
        json_write(out / "completion.json", {
            "status": "completed", "samples": {k: len(v) for k, v in samples.items()},
            "sample_sha256": {k: sha256_file(out / f"samples_{k}.jsonl") for k in samples},
            "engine_stats": engine.stats if engine else None,
            "comparison_requires": ["same task/scorer version", "same data/split",
                                    "same shots/template/filter", "matching generation/context policy"],
        })
    except BaseException as error:
        json_write(out / "failure.json", {"status": "incomplete", "type": type(error).__name__,
                                        "message": str(error),
                                        "engine_stats": engine.stats if engine else None})
        raise
