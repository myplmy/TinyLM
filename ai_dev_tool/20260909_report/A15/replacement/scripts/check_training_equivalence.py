#!/usr/bin/env python3
"""A15: 같은 checkpoint/예제에서 forward·mask CE·gradient·fresh optimizer 1 update를 비교한다."""
from __future__ import annotations
import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.chat.supervision import encode_sample, collate_samples, masked_ce_sum, sample_totals
from tinylm.model.checkpoint_io import load_trainable
from tinylm.eval.audit_io import sha256_file, tokenizer_digest, write_json_new


def tensor_difference(a, b, *, atol, rtol):
    import torch
    if a.shape != b.shape:
        return {"shape_equal": False, "allclose": False, "bit_equal": False}
    af, bf = a.detach().double(), b.detach().double()
    if not bool(torch.isfinite(af).all() and torch.isfinite(bf).all()):
        return {"shape_equal": True, "allclose": False, "bit_equal": False, "nonfinite": True}
    diff = (af - bf).abs()
    return {"shape_equal": True, "allclose": bool(torch.allclose(af, bf, atol=atol, rtol=rtol)),
            "bit_equal": a.dtype == b.dtype and bool(torch.equal(
                a.detach().cpu().contiguous().reshape(-1).view(torch.uint8),
                b.detach().cpu().contiguous().reshape(-1).view(torch.uint8))),
            "max_abs": float(diff.max()) if diff.numel() else 0.0,
            "rms_difference": float(diff.square().mean().sqrt()) if diff.numel() else 0.0,
            "a_dtype": str(a.dtype), "b_dtype": str(b.dtype)}


def one_arm(checkpoint, x, y, *, device, seed, variant, candidate, chunk):
    import torch
    import torch.nn.functional as F
    model, cfg, _ = load_trainable(checkpoint, device)
    valid_targets = y[y != -100]
    if (x.shape[-1] > cfg.max_seq_len or int(x.min()) < 0 or int(x.max()) >= cfg.vocab_size
            or valid_targets.numel() == 0 or int(valid_targets.min()) < 0
            or int(valid_targets.max()) >= cfg.vocab_size):
        raise ValueError("batch가 checkpoint context/vocabulary를 초과")
    if variant == "grad-checkpoint":
        cfg.grad_checkpoint = bool(candidate)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    model.clear_quant()
    logits = model(x)
    if candidate and variant == "ce-chunk":
        loss_sum, count = masked_ce_sum(logits, y, chunk=chunk)
        loss = loss_sum / count
    else:
        flat, truth = logits.reshape(-1, logits.size(-1)), y.reshape(-1)
        valid = truth != -100
        loss = F.cross_entropy(flat[valid].float(), truth[valid])
    if not bool(torch.isfinite(loss)):
        raise FloatingPointError("loss nonfinite")
    output = logits.detach().cpu().clone()
    loss.backward()
    gradients = {n: p.grad.detach().cpu().clone() for n, p in model.named_parameters() if p.grad is not None}
    if not gradients:
        raise ValueError("gradient 0개")
    groups = model.param_groups(1e-3)
    if candidate and variant in ("opt-bf16", "opt-fp32c"):
        from tinylm.train.adamw_bf16 import AdamWLowPrec
        optimizer = AdamWLowPrec(groups, betas=(0.9, 0.95), eps=1e-8,
                                 state_dtype=torch.bfloat16 if variant == "opt-bf16" else torch.float32)
    else:
        optimizer = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8, fused=False)
    optimizer.step()
    parameters = {n: p.detach().cpu().clone() for n, p in model.named_parameters()}
    parameter_names = {id(p): n for n, p in model.named_parameters()}
    optimizer_state = {parameter_names[id(p)] + "." + str(key): value.detach().cpu().clone()
                       for p, state in optimizer.state.items() for key, value in state.items()
                       if key in ("exp_avg", "exp_avg_sq") and isinstance(value, torch.Tensor)}
    info = {"loss": float(loss.detach()), "cfg": dataclasses.asdict(cfg),
            "objective": "assistant-only", "autocast": False, "fresh_optimizer": True}
    del logits, loss, optimizer, model
    if str(device).startswith("cuda"):
        torch.cuda.empty_cache()
    return info, output, gradients, parameters, optimizer_state


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--records", required=True, help="작은 train-only canonical JSONL")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--serializer", default="chatml", choices=("chatml", "plain", "minimal", "gemma"))
    ap.add_argument("--seq", type=int, default=128)
    ap.add_argument("--max-records", type=int, default=2)
    ap.add_argument("--variant", choices=("ce-chunk", "grad-checkpoint", "opt-bf16", "opt-fp32c"),
                    default="ce-chunk")
    ap.add_argument("--ce-chunk", type=int, default=17)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--atol", type=float, default=1e-6)
    ap.add_argument("--rtol", type=float, default=1e-5)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if (min(a.seq, a.max_records, a.ce_chunk) < 1 or min(a.atol, a.rtol) < 0
            or not all(math.isfinite(v) for v in (a.atol, a.rtol))):
        ap.error("크기 양수, 허용오차 비음수")
    from tokenizers import Tokenizer
    from tinylm.eval.audit_io import read_records
    rows = read_records(a.records)[:a.max_records]
    if any(r.get("meta", {}).get("split") != "train" for r in rows):
        raise ValueError("등가성 probe는 meta.split=train인 작은 예제로 수행")
    tok = Tokenizer.from_file(a.tokenizer)
    samples = [encode_sample(r, tok, kind=a.serializer, max_length=a.seq+1) for r in rows]
    x, y = collate_samples(samples, device=a.device)
    left = one_arm(a.checkpoint, x, y, device=a.device, seed=a.seed,
                   variant=a.variant, candidate=False, chunk=a.ce_chunk)
    right = one_arm(a.checkpoint, x, y, device=a.device, seed=a.seed,
                    variant=a.variant, candidate=True, chunk=a.ce_chunk)
    def compare_maps(left, right):
        if set(left) != set(right):
            raise ValueError("gradient/parameter 대상 집합 불일치")
        return {n: tensor_difference(left[n], right[n], atol=a.atol, rtol=a.rtol) for n in left}
    forward = tensor_difference(left[1], right[1], atol=a.atol, rtol=a.rtol)
    gradients, parameters = compare_maps(left[2], right[2]), compare_maps(left[3], right[3])
    states = compare_maps(left[4], right[4])
    entries = [forward, *gradients.values(), *parameters.values()]
    # optimizer 상태 dtype 차이는 다음 update부터 품질 차이를 만들 수 있어 별도 보고한다.
    result = {"schema": "tinylm.training-equivalence.v1", "command": vars(a),
              "checkpoint_sha256": sha256_file(a.checkpoint),
              "records_sha256": sha256_file(a.records), "tokenizer_sha256": tokenizer_digest(tok),
              "batch": sample_totals(samples), "control": left[0], "candidate": right[0],
              "forward": forward, "gradients": gradients, "parameters_after_one_update": parameters,
              "bit_equality_scope": "tensor bytes of forward/gradient/parameters/Adam moments; scalar step excluded",
              "optimizer_state": states,
              "optimizer_state_allclose": all(r["allclose"] for r in states.values()),
              "allclose": all(r["allclose"] for r in entries),
              "all_bit_equal": all(r["bit_equal"] for r in entries + list(states.values())),
              "scope": "이 고정 batch와 fresh optimizer 1 update만. 전체 학습 재현성/일반 품질 등가 증명 아님."}
    write_json_new(a.out, result)
    print(json.dumps({"allclose": result["allclose"], "all_bit_equal": result["all_bit_equal"],
                      "out": a.out}, ensure_ascii=False))
    return 0 if result["allclose"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
