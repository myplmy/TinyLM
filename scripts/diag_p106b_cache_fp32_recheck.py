#!/usr/bin/env python3
"""P106B bounded FP32 recheck of the six observed BF16 cache differences; no training."""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106b_generation_path_audit import (
    SUBJECTS, ARMS, CaptureTokenizer, digest, extracted, OUTPUT as INPUT)
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit

OUTPUT = ROOT / "test_result/evidence/101_P106B_Stage3sWb_fp32_cache_recheck.json"


def pairs_from(report):
    if report.get("status") != "DIAGNOSTIC_COMPLETE" or report.get("case_count") != 128:
        raise ValueError("complete frozen A diagnostic required")
    pairs = [p for p in report["cache_pairs"] if not p["token_ids_identical"]]
    if len(pairs) != 6:
        raise ValueError("this gate is limited to the six already observed pairs")
    return pairs


def check():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("new FP32 output already exists")
    report = json.loads(INPUT.read_text(encoding="utf-8"))
    pairs = pairs_from(report)
    for _name, _arm, path, expected, _step in SUBJECTS:
        if digest(ROOT / path) != expected:
            raise ValueError("frozen checkpoint changed")
    for spec in ARMS.values():
        if digest(ROOT / spec["tokenizer"]) != spec["tok_sha"]:
            raise ValueError("frozen tokenizer changed")
    return report, pairs


class FP32Forward:
    def __init__(self, model):
        self.model = model
    def parameters(self):
        return self.model.parameters()
    def __call__(self, *args, **kwargs):
        import torch
        with torch.autocast("cuda", enabled=False):
            return self.model(*args, **kwargs)


def execute(original, pairs):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip, sample
    torch.set_num_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    began = time.monotonic()
    result = {"schema": "P106B_FP32_CACHE_RECHECK_V1", "status": "RUNNING",
              "input_sha256": digest(INPUT), "source_sha256": digest(Path(__file__)),
              "cases": [], "training_updates": 0, "hard_wall_sec": 300,
              "precision": "FP32 forward, FP32 quantized shadow, TF32 disabled"}
    try:
        idle_before_gpu()
        with wall_limit(300):
            for subject, arm, path, expected, step in SUBJECTS:
                relevant = [p for p in pairs if p["subject"] == subject]
                if not relevant:
                    continue
                state = torch.load(ROOT / path, map_location="cpu", weights_only=True)
                cfg = TMTConfig(**state["cfg"])
                cfg.wq_dtype = "fp32"
                tok = Tokenizer.from_file(str(ROOT / ARMS[arm]["tokenizer"]))
                base = TiedMLPTransformer(cfg).cuda()
                base.load_state_dict(_strip(state["model"]), strict=True)
                del state
                base.requires_grad_(False)
                base.set_anneal(1.0)
                base.eval()
                base.freeze_quant()
                wrapped = FP32Forward(base)
                for pair in relevant:
                    prior = next(r for r in original["records"] if r["subject"] == subject and r["id"] == pair["id"]
                                 and r["prompt_kind"] == pair["prompt_kind"] and r["use_cache"])
                    outcomes = []
                    for cache in (True, False):
                        capture = CaptureTokenizer(tok)
                        start = time.monotonic()
                        decoded, metadata = sample(wrapped, cfg, capture, prior["prompt"],
                            max_new=160, temperature=0, top_k=1, device="cuda", use_cache=cache,
                            logits_last_only=True, return_metadata=True)
                        torch.cuda.synchronize()
                        outcomes.append({**extracted(prior["prompt"], tok, decoded, capture.last_ids),
                                         "use_cache": cache, "generation": metadata,
                                         "wall_sec": time.monotonic() - start})
                    row = {**pair, "fp32_token_ids_identical": outcomes[0]["generated_token_ids"] == outcomes[1]["generated_token_ids"],
                           "outcomes": outcomes}
                    result["cases"].append(row)
                    print("[FP32_CACHE_PAIR] " + json.dumps(row, ensure_ascii=False), flush=True)
                base.clear_quant()
                del base, wrapped, tok, capture
                gc.collect()
                torch.cuda.empty_cache()
        result.update(status="DIAGNOSTIC_COMPLETE", exit_code=0, pair_count=len(result["cases"]),
                      fp32_mismatches=sum(not r["fp32_token_ids_identical"] for r in result["cases"]),
                      limit="FP32 agreement explains these six divergences; not proof of all-cache or broad model correctness")
    except BaseException as exc:
        result.update(status="INCOMPLETE", exit_code=9, failure=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        result["whole_wall_sec"] = time.monotonic() - began
        with OUTPUT.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print("[FP32_CACHE_SUMMARY] " + json.dumps({k:v for k,v in result.items() if k != "cases"}, ensure_ascii=False), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            fixture = {"status":"DIAGNOSTIC_COMPLETE", "case_count":128,
                       "cache_pairs":[{"token_ids_identical":False} for _ in range(6)]}
            assert len(pairs_from(fixture)) == 6
            fixture["cache_pairs"].pop()
            try:
                pairs_from(fixture)
            except ValueError:
                pass
            else:
                raise AssertionError("unbounded/new sample accepted")
            print("[PASS] exact six-pair selection fixture; model/GPU NOT_RUN")
            return 0
        original, pairs = check()
        if args.check_only:
            print(json.dumps({"pairs": pairs, "input_sha256": digest(INPUT),
                              "hard_wall_sec":300, "training_updates":0}, ensure_ascii=False))
            return 0
        return execute(original, pairs)
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
