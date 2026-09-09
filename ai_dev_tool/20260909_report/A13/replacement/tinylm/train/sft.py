"""A05 제한된 SFT 경로: 원본 trainer를 바꾸지 않고 동일 serializer/mask로 학습한다."""
from __future__ import annotations
import argparse
import dataclasses
import json
import math
import random
import time
from pathlib import Path

from ..chat.supervision import (encode_sample, encode_text_sample, collate_samples,
                               masked_ce_sum, sample_totals, CONTRACT)
from ..eval.audit_io import read_records, sha256_file, tokenizer_digest, write_json_new
from ..model.checkpoint_io import load_trainable


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--out-dir", required=True, help="새 실험 디렉터리; 기존 디렉터리 거절")
    ap.add_argument("--format", choices=("chat", "text"), default="chat")
    ap.add_argument("--objective", choices=("assistant", "all"), default="assistant")
    ap.add_argument("--serializer", choices=("chatml", "plain", "minimal", "gemma"), default="chatml")
    ap.add_argument("--no-train-thinking", action="store_true")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--overflow", choices=("error", "truncate"), default="error")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--micro-bs", type=int, default=1)
    ap.add_argument("--accum", type=int, default=1)
    ap.add_argument("--lr", type=float, required=True)
    ap.add_argument("--weight-decay", type=float, default=0.1)
    ap.add_argument("--optimizer", choices=("adamw", "muon"), default="adamw")
    ap.add_argument("--muon-lr-mult", type=float, default=15.0)
    ap.add_argument("--muon-weight-decay", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--ce-chunk", type=int, default=256)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)
    if min(a.seq, a.epochs, a.micro_bs, a.accum, a.ce_chunk) < 1 or a.lr <= 0:
        ap.error("학습 크기/LR는 양수")
    if (not all(math.isfinite(v) for v in (a.lr, a.weight_decay, a.muon_weight_decay,
                                            a.muon_lr_mult, a.grad_clip))
            or min(a.weight_decay, a.muon_weight_decay) < 0
            or min(a.muon_lr_mult, a.grad_clip) <= 0):
        ap.error("LR/WD/grad-clip가 유한하고 유효한 범위여야 함")
    if a.max_steps is not None and a.max_steps < 1:
        ap.error("max-steps는 양수")
    if a.format == "text" and a.objective != "all":
        ap.error("C0 text 학습은 --objective all 명시")
    out = Path(a.out_dir)
    if out.exists():
        ap.error("out-dir가 이미 존재함")
    import torch
    from tokenizers import Tokenizer
    torch.manual_seed(a.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(a.seed)
    tok = Tokenizer.from_file(a.tokenizer)
    records = read_records(a.train)
    seen_ids = set()
    for record in records:
        split = str(record.get("meta", {}).get("split", "train")).lower()
        if split != "train":
            raise ValueError("train 이외 split이 학습 입력에 포함됨")
        ident = record.get("id") or record.get("meta", {}).get("id")
        if ident is not None:
            if str(ident) in seen_ids:
                raise ValueError("중복 train ID")
            seen_ids.add(str(ident))
    if a.format == "chat":
        samples = [encode_sample(r, tok, kind=a.serializer, max_length=a.seq + 1,
                                 train_thinking=not a.no_train_thinking,
                                 overflow=a.overflow, objective=a.objective) for r in records]
    else:
        samples = [encode_text_sample(r, tok, max_length=a.seq + 1, overflow=a.overflow)
                   for r in records]
    model, cfg, parent = load_trainable(a.checkpoint, a.device)
    if int(cfg.vocab_size) != tok.get_vocab_size():
        raise ValueError("checkpoint/tokenizer vocabulary 불일치")
    if a.seq > cfg.max_seq_len:
        raise ValueError("seq가 checkpoint max_seq_len을 초과")
    groups = model.param_groups(a.lr, weight_decay=a.weight_decay)
    muon = None
    if a.optimizer == "muon":
        from .muon import Muon, split_params
        matrices, _ = split_params(model)
        if not matrices:
            raise ValueError("Muon 행렬이 0개")
        ids = {id(p) for p in matrices}
        groups = [dict(g, params=[p for p in g["params"] if id(p) not in ids]) for g in groups]
        groups = [g for g in groups if g["params"]]
        muon = Muon(matrices, lr=a.lr * a.muon_lr_mult, weight_decay=a.muon_weight_decay)
    groups = [g for g in groups if g["params"]]
    optimizer = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8)
    metadata = {"schema": "tinylm.sft-run.v1", "command": vars(a), "mask_contract": CONTRACT,
                "parent_sha256": sha256_file(a.checkpoint),
                "train_sha256": sha256_file(a.train), "tokenizer_sha256": tokenizer_digest(tok),
                "one_epoch": sample_totals(samples), "lr_schedule": "constant",
                "optimizer_groups": [{"lr": g["lr"], "weight_decay": g["weight_decay"],
                                      "parameters": sum(p.numel() for p in g["params"])}
                                     for g in optimizer.param_groups],
                "muon_groups": ([{"lr": g["lr"], "weight_decay": g["weight_decay"],
                                  "parameters": sum(p.numel() for p in g["params"])}
                                 for g in muon.param_groups] if muon else []),
                "note": "new fine-tuning run; original optimizer state is not resumed"}
    out.mkdir(parents=True, exist_ok=False)
    write_json_new(out / "contract.json", metadata)
    rng, updates, total_loss_tokens, total_serialized = random.Random(a.seed), 0, 0, 0
    started = time.perf_counter()
    dev_type = torch.device(a.device).type
    with (out / "updates.jsonl").open("x", encoding="utf-8", newline="\n") as log:
        stop = False
        for epoch in range(a.epochs):
            order = list(range(len(samples)))
            rng.shuffle(order)
            span = a.micro_bs * a.accum
            for start in range(0, len(order), span):
                chosen = [samples[i] for i in order[start:start + span]]
                denominator = sum(s.loss_tokens for s in chosen)
                optimizer.zero_grad(set_to_none=True)
                if muon:
                    muon.zero_grad(set_to_none=True)
                loss_total = 0.0
                for j in range(0, len(chosen), a.micro_bs):
                    batch = chosen[j:j + a.micro_bs]
                    x, y = collate_samples(batch, device=a.device)
                    with torch.autocast(dev_type, dtype=torch.bfloat16, enabled=dev_type == "cuda"):
                        logits = model(x)
                    loss, count = masked_ce_sum(logits, y, chunk=a.ce_chunk)
                    if count != sum(s.loss_tokens for s in batch):
                        raise RuntimeError("계측기/학습 batch의 손실 token 수 불일치")
                    if not bool(torch.isfinite(loss)):
                        raise FloatingPointError("nonfinite loss; update하지 않음")
                    (loss / denominator).backward()
                    loss_total += float(loss.detach())
                    del loss, logits
                    model.clear_quant()
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), a.grad_clip,
                                                           error_if_nonfinite=True)
                optimizer.step()
                if muon:
                    muon.step()
                model.clear_quant()
                updates += 1
                total_loss_tokens += denominator
                total_serialized += sum(len(s.input_ids) for s in chosen)
                row = {"update": updates, "epoch": epoch, "loss": loss_total / denominator,
                       "loss_tokens": denominator, "total_loss_tokens": total_loss_tokens,
                       "total_serialized_tokens": total_serialized, "grad_norm": float(grad_norm),
                       "elapsed_seconds": time.perf_counter() - started}
                log.write(json.dumps(row, allow_nan=False) + "\n")
                log.flush()
                print(json.dumps(row, allow_nan=False), flush=True)
                if a.max_steps is not None and updates >= a.max_steps:
                    stop = True
                    break
            if stop:
                break
    if updates == 0:
        raise RuntimeError("학습 update 0개")
    summary = dict(metadata, updates=updates, total_loss_tokens=total_loss_tokens,
                   total_serialized_tokens=total_serialized,
                   elapsed_seconds=time.perf_counter() - started)
    with (out / "model.pt").open("xb") as f:
        torch.save({"model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                    "cfg": dataclasses.asdict(cfg), "step": updates, "sft_meta": summary}, f)
    write_json_new(out / "summary.json", summary)
    return 0
