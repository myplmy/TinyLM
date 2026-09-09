#!/usr/bin/env python3
"""A06: 한 번 변환한 동일 모델 객체로 cached 품질·생성·상주·속도를 측정한다."""
from __future__ import annotations
import argparse
import dataclasses
import json
import math
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.eval.audit_io import (read_records, sha256_file, digest_json, write_json_new)
from tinylm.eval.heldout import load_cache
from tinylm.eval.bpb_corpus import load_documents, exclude_documents, corpus_digest
from scripts.common_bpb import document_nll
from tinylm.eval.model_adapter import load_local_model
from tinylm.eval.paired_records import mc_metrics
from tinylm.eval.runtime_audit import (RssSampler, ForwardAudit, inventory_summary,
                                      tensor_digest, cached_continuation_nll)
from tinylm.infer.generate import sample


class FixedPromptTokenizer:
    """정본 sample 루프에 검증된 ID prefix를 전달한다. vocab/template을 바꾸지 않는다."""
    def __init__(self, tok, ids):
        self.tok, self.ids = tok, ids
    def encode(self, text):
        return SimpleNamespace(ids=list(self.ids))
    def decode(self, ids):
        return self.tok.decode(ids)
    def token_to_id(self, token):
        return self.tok.token_to_id(token)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--drop-latent", action="store_true")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--lut", action="store_true")
    fmt.add_argument("--int8-store", action="store_true")
    ap.add_argument("--unpack-cache", action="store_true")
    ap.add_argument("--emb-quant", choices=("bf16", "fp16", "int8", "int4", "ternary"))
    ap.add_argument("--emb-chunk", type=int, default=4096)
    ap.add_argument("--lut-out-chunk", type=int, default=256)
    ap.add_argument("--kv-dtype", choices=("fp32", "bf16", "fp16"), default="bf16")
    ap.add_argument("--contexts", nargs="+", type=int, default=[256, 1024])
    ap.add_argument("--max-new", type=int, default=32)
    ap.add_argument("--prompts", required=True, help="긴 대표 prompt의 id/text JSONL")
    ap.add_argument("--check-no-cache", action="store_true")
    ap.add_argument("--last-head", action="store_true", help="A06 추론 전용 마지막 위치 head")
    ap.add_argument("--bpb-text-jsonl", help="미지정이면 SQuAD 원문 사용")
    ap.add_argument("--bpb-squad", default=str(ROOT / "datasets/squad/train-v2.0.json"))
    ap.add_argument("--bpb-max-docs", type=int, default=4000)
    ap.add_argument("--bpb-exclusion-manifest", help="A02의 동일 corpus 전체 scan manifest")
    ap.add_argument("--skip-bpb", action="store_true", help="pilot 전용; 완전한 배포 품질 표를 만들지 않음")
    ap.add_argument("--heldout-version", choices=("2.7", "2.8"), default="2.7")
    ap.add_argument("--quality-n", type=int, default=20, help="0=전수; 기본 20은 pilot만")
    ap.add_argument("--rss-interval", type=float, default=0.01)
    a = ap.parse_args(argv)
    if (a.lut or a.int8_store or a.unpack_cache) and not a.drop_latent:
        ap.error("저장 변환은 --drop-latent와 함께")
    if a.unpack_cache and not a.int8_store:
        ap.error("unpack-cache는 int8-store 필요")
    if not a.skip_bpb and not a.bpb_exclusion_manifest:
        ap.error("최종 측정에는 --bpb-exclusion-manifest 필요. pilot은 --skip-bpb 명시")
    if a.max_new < 2 or a.quality_n < 0 or any(c < a.max_new for c in a.contexts):
        ap.error("max-new>=2, context>=max-new, quality-n>=0")
    out = Path(a.out_dir)
    if out.exists():
        ap.error("새 out-dir 필요")
    import torch
    deployment = {k: getattr(a, k) for k in
                  ("drop_latent", "lut", "int8_store", "unpack_cache",
                   "emb_quant", "emb_chunk", "lut_out_chunk")}
    model, tok, provenance = load_local_model(
        a.tag, checkpoint=a.checkpoint, tokenizer_path=a.tokenizer,
        device=a.device, deployment=deployment)
    cfg = model.cfg
    cfg.kv_dtype = a.kv_dtype
    if max(a.contexts) > cfg.max_seq_len:
        raise ValueError("실제 checkpoint max_seq_len 초과; cfg를 늘려 측정하지 않음")
    prompts = read_records(a.prompts)
    encoded_prompts, ids_seen = [], set()
    for row in prompts:
        ident = str(row.get("id", ""))
        if not ident or ident in ids_seen or not isinstance(row.get("text"), str):
            raise ValueError("고유 prompt id/text 필요")
        ids_seen.add(ident)
        ids = tok.encode(row["text"], add_special_tokens=False).ids
        if len(ids) < max(a.contexts) - a.max_new + 1:
            raise ValueError(f"{ident}: 최대 context의 긴 prefix를 만들 실제 prompt가 부족")
        encoded_prompts.append((ident, ids))
    quality, held_meta = load_cache(ROOT, a.heldout_version)
    if a.quality_n:
        quality = quality[:a.quality_n]
    bpb_docs = []
    if not a.skip_bpb:
        bpb_docs = load_documents(a.bpb_text_jsonl or a.bpb_squad,
                                 squad=not bool(a.bpb_text_jsonl), limit=a.bpb_max_docs)
        exclusion = json.loads(Path(a.bpb_exclusion_manifest).read_text(encoding="utf-8"))
        bpb_docs = exclude_documents(bpb_docs, exclusion)
    tensor_sha, tensor_rows = tensor_digest(model)
    code_paths = sorted((ROOT / "tinylm/model").glob("*.py")) + [
        ROOT / "tinylm/infer/generate.py", Path(__file__),
        ROOT / "tinylm/eval/runtime_audit.py", ROOT / "tinylm/eval/model_adapter.py"]
    artifact = {"checkpoint_sha256": provenance["checkpoint_sha256"],
                "tokenizer_sha256": provenance["tokenizer_sha256"],
                "deployment": deployment, "last_position_head": a.last_head, "cfg": dataclasses.asdict(cfg),
                "tensor_digest_before_measurement": tensor_sha,
                "code_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in code_paths},
                "torch_version": str(torch.__version__), "cpu_threads": torch.get_num_threads(),
                "device": a.device, "visit_schedule": list(model.visit_schedule())}
    artifact_id = digest_json(artifact)
    provenance = dict(provenance, artifact_id=artifact_id, kv_dtype=a.kv_dtype)
    out.mkdir(parents=True, exist_ok=False)
    write_json_new(out / "artifact.json", dict(artifact, artifact_id=artifact_id,
                                             tensor_inventory=tensor_rows,
                                             kind="in_memory_packed_reconstruction_not_native_export_file"))
    resident_initial = inventory_summary(model)
    measurements, memory_rows, cache_matches = [], [], []
    if a.device == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    with RssSampler(a.rss_interval) as rss:
        with ForwardAudit(model, phase="cached_quality") as audit:
            with (out / "quality.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
                for raw in quality:
                    base = {"id": "stage1_heldout:" + str(raw["id"]), "model": a.tag,
                            "task": "deployment_heldout", "dataset_sha256": held_meta["cache_sha256"],
                            "item_sha256": digest_json(raw), "gold": raw["gold"],
                            "scoring_profile": "cached_mean_nll_minus_unconditional.v1",
                            "model_provenance": provenance}
                    conditional, unconditional, error = [], [], None
                    for choice in raw["choices"]:
                        answer = " " + choice.lstrip()
                        c, reason = cached_continuation_nll(model, tok, raw["ctx"], answer,
                                                           device=a.device, seq_max=cfg.max_seq_len, last_head=a.last_head)
                        u, reason_u = cached_continuation_nll(model, tok, "", answer,
                                                             device=a.device, seq_max=cfg.max_seq_len, last_head=a.last_head)
                        if reason or reason_u:
                            error = reason or reason_u
                            break
                        conditional.append(c)
                        unconditional.append(u)
                    if error:
                        rec = dict(base, status="skipped", reason=error)
                    else:
                        costs = [c["nll_mean"] - u["nll_mean"]
                                 for c, u in zip(conditional, unconditional)]
                        rec = dict(base, status="ok", costs=costs,
                                   gold_ce=conditional[raw["gold"]]["nll_mean"],
                                   **mc_metrics(costs, raw["gold"]))
                    stream.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")
                    stream.flush()
        memory_rows.extend(audit.rows)
        bpb_summary = None
        if bpb_docs:
            bpb_sha, nll, byte_count = corpus_digest(bpb_docs), 0.0, 0
            with ForwardAudit(model, phase="uncached_bpb_quality") as bpb_audit:
                with (out / "bpb.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
                    for doc in bpb_docs:
                        score = document_nll(model, tok, doc["text"], device=a.device,
                                             seq=cfg.max_seq_len, stride=min(256, cfg.max_seq_len),
                                             micro_bs=1, ce_chunk=256)
                        score.update(id=doc["id"], model=a.tag, task="common_bpb", status="ok",
                                     model_provenance=provenance, item_sha256=doc["text_sha256"],
                                     dataset_sha256=bpb_sha,
                                     scoring_profile=f"document_all_targets_bpb.v1.seq{cfg.max_seq_len}.stride{min(256, cfg.max_seq_len)}",
                                     bpb=score["nll_sum"] / math.log(2) / score["scored_bytes"])
                        stream.write(json.dumps(score, ensure_ascii=False, allow_nan=False) + "\n")
                        stream.flush()
                        nll += score["nll_sum"]
                        byte_count += score["scored_bytes"]
            memory_rows.extend(bpb_audit.rows)
            bpb_summary = {"bpb": nll / math.log(2) / byte_count, "nll_sum": nll,
                           "bytes": byte_count, "documents": len(bpb_docs), "corpus_sha256": bpb_sha,
                           "exclusion_manifest_sha256": sha256_file(a.bpb_exclusion_manifest),
                           "scope": "같은 packed weight의 전체 target 평가. KV 저장 정밀도는 cached MC에서 별도 검사"}
        for context in a.contexts:
            prompt_len = context - a.max_new + 1
            for ident, ids in encoded_prompts:
                fixed_tok = FixedPromptTokenizer(tok, ids[:prompt_len])
                wall = time.perf_counter()
                with ForwardAudit(model, phase="cached_generate", record_tokens=True) as audit:
                    with torch.inference_mode():
                        text = sample(model, cfg, fixed_tok, "", max_new=a.max_new,
                                      temperature=0, device=a.device, use_cache=True, stop_at_eos=False,
                                      logits_last_only=a.last_head)
                elapsed = time.perf_counter() - wall
                if len(audit.rows) != a.max_new:
                    raise RuntimeError("요청 생성 수와 실제 forward 수 불일치")
                decode = [r["forward_seconds"] for r in audit.rows[1:]]
                measurements.append({"prompt_id": ident, "prompt_tokens": prompt_len,
                                     "prompt_ids_sha256": digest_json(ids[:prompt_len]),
                                     "target_cache_length": context, "generated_ids": audit.tokens,
                                     "output": text, "first_forward_seconds": audit.rows[0]["forward_seconds"],
                                     "median_decode_forward_seconds": statistics.median(decode),
                                     "decode_forward_tokens_per_second": len(decode) / sum(decode),
                                     "whole_run_tokens_per_second_with_audit": a.max_new / elapsed,
                                     "instrumented_wall_seconds": elapsed})
                memory_rows.extend(audit.rows)
                if a.check_no_cache:
                    with ForwardAudit(model, phase="uncached_check", record_tokens=True) as control:
                        with torch.inference_mode():
                            sample(model, cfg, fixed_tok, "", max_new=a.max_new,
                                   temperature=0, device=a.device, use_cache=False, stop_at_eos=False,
                                   logits_last_only=a.last_head)
                    cache_matches.append({"prompt_id": ident, "context": context,
                                          "ids_equal": audit.tokens == control.tokens})
                    # uncached control은 실제 배포 메모리 최고점에서 분리한다.
    deploy_rows = [r for r in memory_rows if r["phase"] == "cached_generate"]
    quality_records = read_records(out / "quality.jsonl")
    scored = [r for r in quality_records if r["status"] == "ok"]
    boundary_peak = max(r["boundary_live_tensor_bytes"] for r in deploy_rows)
    result = {"schema": "tinylm.deployment-audit.v1", "artifact_id": artifact_id,
              "command": vars(a), "resident_initial_bytes": resident_initial["bytes"],
              "observed_boundary_tensor_peak_bytes": boundary_peak,
              "observed_boundary_tensor_peak_MiB": boundary_peak / 2**20,
              "boundary_budget_status": "observed_over_40MiB" if boundary_peak > 40 * 2**20 else "incomplete_workspace_evidence",
              "rss": rss.result, "rss_includes_uncached_control": a.check_no_cache,
              "cuda_allocator_peak_bytes": torch.cuda.max_memory_allocated() if a.device == "cuda" else None,
              "cuda_peak_includes_uncached_control": a.check_no_cache,
              "clean_bpb": bpb_summary,
              "quality": {"asked": len(quality), "scored": len(scored),
                          "correct": sum(r["correct"] for r in scored),
                          "accuracy": sum(r["correct"] for r in scored) / len(scored) if scored else None,
                          "full_registered_version": a.quality_n == 0,
                          "heldout": held_meta},
              "measurements": measurements, "cache_checks": cache_matches,
              "limitations": [
                  "boundary tensor 합에는 forward 내부 임시 workspace 최고점이 빠진다. 40MiB PASS를 발급하지 않음.",
                  "RSS/CUDA 최고점은 engine/allocator/계측 및 선택한 uncached 대조를 포함한다.",
                  "prefill 길이=context-max_new+1, 마지막 cached forward에서 context 길이에 도달한다.",
                  "decode forward 속도는 sampling/Python/계측 비용을 제외. 전체 계측 wall 속도도 별도 제시.",
                  "artifact.json은 동일 in-memory packed 모델의 증거다. C/C++ 실행기 파일 내보내기를 구현한 것은 아님."]}
    write_json_new(out / "forward_memory.json", memory_rows)
    write_json_new(out / "summary.json", result)
    print(json.dumps({"artifact_id": artifact_id, "out": str(out),
                      "quality_scored": len(scored), "memory_status": result["boundary_budget_status"]},
                     ensure_ascii=False))
    return 0 if scored and all(r["ids_equal"] for r in cache_matches) else 2


if __name__ == "__main__":
    raise SystemExit(main())
