#!/usr/bin/env python3
"""Exact P093B native greedy replay and token-time observation. No learning."""
from __future__ import annotations
from contextlib import nullcontext
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p093b_generation_attribution as saved
from scripts import diag_p093b_native_repair as old
from scripts import diag_p093b_calibration_recovery as recovery

TAG = "p093b_live_trace_v1_s1337"
CODE = ("scripts/diag_p093b_live_trace.py", "scripts/p093b_live_trace.py",
        "scripts/test_p093b_live_trace.py", *saved.CODE)


def metadata(args):
    return {"schema": "P093B_LIVE_TRACE_V1", "mode": args.mode, "tag": args.tag,
            "code_sha256": {n: old.digest(ROOT / n) for n in dict.fromkeys(CODE)},
            "source_recovery_report_sha256": saved.REPORT_SHA,
            "max_new": 96, "max_wall_sec": args.max_wall_sec,
            "subjects": ["parent", "shared", "rank64"], "questions_per_subject": 8,
            "planned_native_sequences": 24, "planned_max_primary_token_steps": 2304,
            "sampler": {"temperature": 0, "top_k": 1, "use_cache": True,
                        "logits_last_only": True, "stop_at_eos": True},
            "observer": "module hooks return None; native sample loop is unchanged",
            "shadow": "same actual prefix cache-off forward at every selected token",
            "loop_definition": "three exact token blocks; onset is start of second block",
            "quality": "NOT_REVIEWED", "model_loading": "NOT_RUN",
            "new_generations": 0, "optimizer_updates": 0, "checkpoint_writes": 0}


def directory(tag, mode):
    return old.directory(tag, "live_" + mode)


def verify_factor_pin(source):
    """Pin the manifest and shards to the immutable capacity report."""
    rank = next(row for row in source["ranks"] if row["rank"] == 64)
    manifest_path = saved.BASE / "rank64_manifest.json"
    current = json.loads(manifest_path.read_text(encoding="utf-8"))
    if current != rank["artifact"]:
        raise ValueError("live rank64 manifest differs from frozen source artifact")
    if [row["path"] for row in current["files"]] != [
            "rank64_gate_proj.pt", "rank64_up_proj.pt", "rank64_down_proj.pt"]:
        raise ValueError("three exact projection shards required")
    for record in current["files"]:
        path = saved.BASE / record["path"]
        if not old.regular(path) or path.stat().st_size != record["bytes"] or old.digest(path) != record["sha256"]:
            raise ValueError("frozen factor shard differs: " + record["path"])
    return {"manifest": str(manifest_path.relative_to(ROOT)),
            "sha256": old.digest(manifest_path), "files": current["files"]}


def verify_live_readback(directory, source, code_sha256):
    from scripts.p106b_shards import verify
    if (source.get("status") != "LIVE_TRACE_COMPLETE"
            or source.get("completed_native_sequences") != 24
            or source.get("input", {}).get("code_sha256") != code_sha256
            or source.get("primary_token_steps", 0) <= 0):
        raise ValueError("complete same-code 24-sequence live source required")
    for name in ("trace_manifest", "answer_manifest"):
        verify(directory, source[name])
    if (source["trace_manifest"]["rows"] != source["primary_token_steps"]
            or source["answer_manifest"]["rows"] != 24):
        raise ValueError("native sequence/trace manifest counts differ")
    return {"lossless_shards_verified": True,
            "all_previous_KV_prefixes_unchanged": source["all_previous_KV_prefixes_unchanged"],
            "technical_gate_passed": source["old_text_finish_count_matched"] == 24
                and source["same_prefix_cache_argmax_matched"] == source["primary_token_steps"]
                and source["all_previous_KV_prefixes_unchanged"]}


def execute(args, info, out):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model, sample
    from scripts import p093b_native_repair as native
    from scripts.p093b_live_trace import LiveObserver
    from scripts.p106b_education_followup import ARMS
    from scripts.p106b_gate_runtime import idle_before_gpu
    from scripts.p106b_shards import ShardWriter, verify

    source = saved.source()
    info["factor_pin"] = verify_factor_pin(source)
    spec = ARMS["a"]
    tok_path = ROOT / spec["tokenizer"]
    if old.digest(old.PARENT) != recovery.PARENT_SHA or old.digest(tok_path) != spec["tok_sha"]:
        raise ValueError("pinned parent/tokenizer identity differs")
    idle_before_gpu()
    start = time.perf_counter()
    with torch.no_grad():
        model, cfg, device = load_model("dense", str(old.PARENT), "cuda")
    if (cfg.n_layers != 16 or cfg.tie_mlp or cfg.n_modes != 1
            or model.visit_schedule() != list(range(16))):
        raise ValueError("exact d16 untied single ordered visit geometry required")
    info.update(model_loading="MEASURED", parent_sha256=recovery.PARENT_SHA,
                tokenizer_sha256=spec["tok_sha"], layer_visits=list(range(16)),
                kv_owner_set=sorted(set(model.owner)),
                autocast="native sample CUDA BF16, observer statistics FP32")
    ids = source["input"]["group_layers"]
    originals = [model.layers[index].mlp[0] for index in ids]
    shared = native.shared_native(originals, cfg)
    adapters = old.load_adapters(saved.BASE, "rank64", shared, cfg, source["input"])
    tok = Tokenizer.from_file(str(tok_path))
    trace_writer = ShardWriter(out, "token_trace")
    answer_writer = ShardWriter(out, "actual_answers")
    answers, events, rows_count = [], [], 0
    previous_matches, prefix_preserved, cache_argmax = [], [], []
    try:
        with torch.no_grad():
            for subject in ("parent", "shared", "rank64"):
                rows, manifest_sha = saved.original_answers(subject)
                context = nullcontext() if subject == "parent" else native.patched_group(
                    model, ids, shared, adapters if subject == "rank64" else None)
                with context:
                    for row in rows:
                        prompt = row["prompt"]
                        prompt_ids = tok.encode(prompt).ids
                        if not 2 <= len(prompt_ids) or len(prompt_ids) + 96 > min(256, cfg.max_seq_len):
                            raise ValueError("bounded actual prefix required; no silent crop")
                        torch.manual_seed(2026101030 + [i for i, _ in recovery.PROBES].index(row["id"]))
                        with LiveObserver(model, tok, prompt_ids, subject=subject, ident=row["id"],
                                          emit=trace_writer.append, max_new=96, shadow=True) as observer:
                            decoded, generation = sample(model, cfg, tok, prompt, max_new=96,
                                temperature=0, top_k=1, device=device, use_cache=True,
                                logits_last_only=True, return_metadata=True)
                        if generation["generated_tokens"] != len(observer.generated):
                            raise ValueError("observer/native selection counts differ")
                        if tok.decode(prompt_ids + observer.generated) != decoded:
                            raise ValueError("observer argmax IDs differ from native selected trajectory")
                        prefix = tok.decode(prompt_ids)
                        if not decoded.startswith(prefix):
                            raise ValueError("native prompt extraction differs")
                        answer = decoded[len(prefix):]
                        match = answer == row["answer"] and all(
                            generation.get(k) == row["generation"].get(k)
                            for k in ("finish_reason", "generated_tokens"))
                        previous_matches.append(match)
                        step_rows = observer.rows
                        rows_count += len(step_rows)
                        prefix_preserved.extend(x["kv"]["all_previous_prefixes_unchanged"] for x in step_rows)
                        cache_argmax.extend(x["same_prefix_cache_comparison"]["argmax_match"] for x in step_rows)
                        events.extend(observer.events)
                        windows = []
                        for event in observer.events[:4]:
                            lo, hi = max(1, event["onset_token"] - 3), min(len(step_rows), event["confirmed_at_token"] + 3)
                            windows.append({"event": event, "steps": list(range(lo, hi + 1)),
                                "trace_ref": {"subject": subject, "id": row["id"]},
                                "generated_text_through_confirmation": tok.decode(
                                    observer.generated[:event["confirmed_at_token"]])})
                        record = {"subject": subject, "id": row["id"], "prompt": prompt,
                                  "answer": answer, "decoded": decoded, "generation": generation,
                                  "generated_token_ids": observer.generated,
                                  "old_source_manifest_sha256": manifest_sha,
                                  "old_text_finish_count_match": match,
                                  "token_trace_rows": len(step_rows),
                                  "loop_candidates": observer.events,
                                  "onset_windows": windows,
                                  "semantic_quality": "PENDING_GPT_REVIEW"}
                        answer_writer.append(record)
                        answers.append({k: record[k] for k in (
                            "subject", "id", "old_text_finish_count_match", "token_trace_rows",
                            "generation", "loop_candidates", "onset_windows")})
                        print("[LIVE_ACTUAL_ANSWER] " + json.dumps(record, ensure_ascii=False), flush=True)
    finally:
        info["new_generations"] = len(answers)
        actual_trace_rows = trace_writer._total_rows
        if trace_writer._total_rows:
            traces = trace_writer.close(lineage=info)
            verify(out, traces)
        else:
            traces = None
        if answer_writer._total_rows:
            answer_manifest = answer_writer.close(lineage=info)
            verify(out, answer_manifest)
        else:
            answer_manifest = None
        old.write(out / "partial.json", {"input": info, "completed_native_sequences": len(answers),
            "trace_rows": actual_trace_rows, "completed_sequence_token_steps": rows_count,
            "trace_manifest": traces, "answer_manifest": answer_manifest,
            "answers": answers, "loop_candidates": events, "optimizer_updates": 0,
            "checkpoint_writes": 0})
    complete = len(answers) == 24 and rows_count > 0
    info["new_generations"] = len(answers)
    technical_match = all(previous_matches) and all(prefix_preserved) and all(cache_argmax)
    return {"input": info, "status": "LIVE_TRACE_COMPLETE" if complete else "INCOMPLETE",
            "completed_native_sequences": len(answers), "primary_token_steps": rows_count,
            "same_prefix_uncached_forwards": rows_count, "old_text_finish_count_matched": sum(previous_matches),
            "all_previous_KV_prefixes_unchanged": all(prefix_preserved),
            "same_prefix_cache_argmax_matched": sum(cache_argmax),
            "trace_manifest": traces, "answer_manifest": answer_manifest,
            "answers": answers, "loop_candidates": events,
            "whole_wall_sec": time.perf_counter() - start,
            "new_generations": len(answers), "optimizer_updates": 0, "checkpoint_writes": 0,
            "causality": "temporal observations and identical-prefix cache intervention, not proof any layer causes semantic repetition",
            "precision_scope": "BF16 native cached versus noncached; no bitwise-logit claim",
            "gpu_memory_allocated_peak_bytes": torch.cuda.max_memory_allocated(),
            "gpu_memory_reserved_peak_bytes": torch.cuda.max_memory_reserved()}, 0 if complete and technical_match else 8


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("contract", "trace", "readback"), required=True)
    p.add_argument("--tag", default=TAG)
    p.add_argument("--max-wall-sec", type=int, default=600)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--check-only", action="store_true")
    args = p.parse_args()
    if not 60 <= args.max_wall_sec <= 600:
        p.error("bounded wall60..600 required")
    info = metadata(args)
    out = directory(args.tag, args.mode)
    if args.check_only or not args.execute:
        print("[PREFLIGHT] " + json.dumps(info))
        return 0
    if out.exists():
        print("[HOLD] existing evidence preserved")
        return 8
    out.mkdir(parents=True)
    try:
        if args.mode == "contract":
            tests = subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "unittest",
                "scripts.test_p093b_live_trace", "-v"], cwd=ROOT, timeout=args.max_wall_sec)
            if tests.returncode:
                raise ValueError("CPU live observation regression failed")
            result = {"input": info, "status": "CPU_CONTRACT_PASS", "new_generations": 0}
            rc = 0
        elif args.mode == "readback":
            trace_dir = directory(args.tag, "trace")
            source = json.loads((trace_dir / "report.json").read_text(encoding="utf-8"))
            checks = verify_live_readback(trace_dir, source, info["code_sha256"])
            result = {"input": info, "status": "LIVE_TRACE_READBACK_COMPLETE",
                "source_report_sha256": old.digest(trace_dir / "report.json"),
                "completed_native_sequences": source["completed_native_sequences"],
                "primary_token_steps": source["primary_token_steps"],
                "old_text_finish_count_matched": source["old_text_finish_count_matched"],
                "same_prefix_cache_argmax_matched": source["same_prefix_cache_argmax_matched"],
                "new_generations": 0, "semantic_quality": "PENDING_GPT_REVIEW", "checks": checks}
            rc = 0 if checks["technical_gate_passed"] else 8
        else:
            contract = json.loads((directory(args.tag, "contract") / "report.json").read_text(encoding="utf-8"))
            if contract.get("status") != "CPU_CONTRACT_PASS" or contract["input"]["code_sha256"] != info["code_sha256"]:
                raise FileNotFoundError("fresh same-code CPU live contract required")
            from scripts.p106b_gate_runtime import wall_limit
            with wall_limit(args.max_wall_sec):
                result, rc = execute(args, info, out)
    except BaseException as exc:
        rc = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(
            exc, (FileNotFoundError, FileExistsError, TimeoutError)) else 9
        result = {"input": info, "status": "INTERRUPTED" if rc == 130 else "PARTIAL_OR_PREREQUISITE_HOLD" if rc == 8 else "TOOL_FAILURE",
                  "error_type": type(exc).__name__, "reason": str(exc), "optimizer_updates": 0,
                  "checkpoint_writes": 0, "new_generations": info["new_generations"]}
    old.write(out / "report.json", result)
    print("[EXPERIMENT_FINAL] " + json.dumps({"mode": args.mode, "status": result["status"],
          "exit_code": rc, "model_loading": info["model_loading"],
          "new_model_generation": result.get("new_generations", 0) > 0,
          "new_generations": result.get("new_generations", 0), "optimizer_updates": 0}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
