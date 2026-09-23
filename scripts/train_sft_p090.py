#!/usr/bin/env python3
"""P090 isolated legacy-tokenizer SFT pilot. User-run only; Codex never runs the model."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.data.sft import IGNORE, conversation_split_key, encode_conversation, load_canonical, sft_targets

READY = ROOT / "HF" / "sft_ready"
CKPT = ROOT / "runs" / "ckpt"
LOGS = ROOT / "runs" / "logs"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def scoped_read(path, base, suffix):
    if path.is_symlink():
        raise ValueError(f"symlink refused: {path}")
    real = path.resolve(strict=True)
    if not real.is_relative_to(base.resolve()) or real.suffix != suffix or not real.is_file():
        raise ValueError(f"expected {suffix} file under {base}: {path}")
    return real


def new_output(path, base, suffix):
    if path.suffix != suffix or path.parent.resolve() != base.resolve():
        raise ValueError(f"output must be a {suffix} immediately under {base}")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"output exists: {path}")
    return path


def encode_records(rows, tokenizer, context, vocab):
    result = []
    for index, row in enumerate(rows):
        ids, labels, _ = encode_conversation(row, tokenizer, "chatml")
        if len(ids) < 2 or len(ids) - 1 > context:
            raise ValueError(f"row {index}: context length {len(ids)} invalid")
        if any(token < 0 or token >= vocab for token in ids):
            raise ValueError(f"row {index}: token outside parent vocabulary")
        x, y = sft_targets(ids, labels)
        count = sum(target != IGNORE for target in y)
        if not count:
            raise ValueError(f"row {index}: no assistant targets")
        result.append((x, y, count))
    if not result:
        raise ValueError("SFT split is empty")
    return result


def pad_batch(batch, pad_id):
    import torch
    width = max(len(item[0]) for item in batch)
    x = [item[0] + [pad_id] * (width - len(item[0])) for item in batch]
    y = [item[1] + [IGNORE] * (width - len(item[1])) for item in batch]
    return torch.tensor(x, dtype=torch.long), torch.tensor(y, dtype=torch.long)


def micro_groups(records, order, micro_bs, accum):
    stride = micro_bs * accum
    for start in range(0, len(order), stride):
        selected = order[start:start + stride]
        yield [[records[j] for j in selected[i:i + micro_bs]] for i in range(0, len(selected), micro_bs)]


def check_inputs(args):
    parent = scoped_read(args.parent, CKPT, ".pt")
    tokenizer_file = scoped_read(args.tokenizer, ROOT / "data_cache", ".json")
    train_file = scoped_read(args.train, READY, ".jsonl")
    val_file = scoped_read(args.val, READY, ".jsonl")
    manifest_file = scoped_read(args.manifest, READY, ".json")
    if parent == args.output.resolve() or train_file == val_file:
        raise ValueError("parent/output or train/val collide")
    if "-chat32" in tokenizer_file.name:
        raise ValueError("legacy SFT pilot refuses chat32 without a new pretrained parent")
    if f"_{args.data}_" not in parent.name or tokenizer_file.name != f"tok-{args.data}-32768.json":
        raise ValueError("parent and legacy tokenizer data names do not agree")
    if sha256(parent) != args.parent_sha256.upper() or sha256(tokenizer_file) != args.tokenizer_sha256.upper():
        raise ValueError("parent or tokenizer SHA256 mismatch")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1":
        raise ValueError("public SFT manifest schema mismatch")
    prefix = manifest_file.name.removesuffix("_manifest.json")
    if (train_file.name != prefix + "_train.canonical.jsonl"
            or val_file.name != prefix + "_val.canonical.jsonl"):
        raise ValueError("corpus files do not match the manifest prefix")
    expected_hashes = manifest.get("output_sha256")
    if not isinstance(expected_hashes, dict) or any(
            expected_hashes.get(split) != sha256(path)
            for split, path in (("train", train_file), ("val", val_file))):
        raise ValueError("public SFT corpus SHA256 differs from the manifest")
    if manifest.get("contamination_gate") != "PASS" and not args.pilot_only:
        raise ValueError("contamination gate is not PASS; only --pilot-only is permitted")
    new_output(args.output, CKPT, ".pt")
    new_output(args.log, LOGS, ".json")
    return parent, tokenizer_file, train_file, val_file, manifest


def validate_splits(train_rows, val_rows):
    train_ids = {r["meta"]["source"] + ":" + r["meta"]["source_id"] for r in train_rows}
    val_ids = {r["meta"]["source"] + ":" + r["meta"]["source_id"] for r in val_rows}
    if train_ids & val_ids:
        raise ValueError("train/val source ID overlap")
    train_prompts = {conversation_split_key(row) for row in train_rows}
    val_prompts = {conversation_split_key(row) for row in val_rows}
    if train_prompts & val_prompts:
        raise ValueError("train/val normalized first-prompt overlap")


def make_optimizers(model, args):
    import torch
    groups = model.param_groups(args.lr)
    if args.optimizer == "adamw":
        return torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8), None
    from tinylm.train.muon import Muon, split_params
    matrices, _ = split_params(model)
    if not matrices:
        raise ValueError("Muon has no eligible matrix")
    matrix_ids = {id(p) for p in matrices}
    other_groups = []
    for group in groups:
        rest = [p for p in group["params"] if id(p) not in matrix_ids]
        if rest:
            other_groups.append(dict(group, params=rest))
    adam = torch.optim.AdamW(other_groups, betas=(0.9, 0.95), eps=1e-8)
    muon = Muon(matrices, lr=args.lr * args.muon_lr_mult, scale_mode="rms",
                weight_decay=args.matrix_weight_decay)
    return adam, muon


def chunked_ce_sum(logits, targets, chunk):
    """Assistant-only CE sum with bounded fp32 cast per vocabulary slice."""
    import torch.nn.functional as F
    flat_logits = logits.reshape(-1, logits.shape[-1])
    flat_targets = targets.reshape(-1)
    if chunk < 1 or flat_logits.shape[0] != flat_targets.numel():
        raise ValueError("invalid SFT CE chunk or target shape")
    if not bool((flat_targets != IGNORE).any()):
        raise ValueError("SFT batch has zero assistant targets")
    total = None
    for start in range(0, flat_targets.numel(), chunk):
        part = F.cross_entropy(
            flat_logits[start:start + chunk].float(),
            flat_targets[start:start + chunk],
            ignore_index=IGNORE, reduction="sum",
        )
        total = part if total is None else total + part
    return total


def loss_sum(model, batch, pad_id, device, vocab, chunk):
    import torch
    x, y = pad_batch(batch, pad_id)
    x, y = x.to(device), y.to(device)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        logits = model(x)
        if logits.shape[-1] != vocab:
            raise ValueError("model logits vocab differs from parent checkpoint")
        return chunked_ce_sum(logits, y, chunk)


def evaluate(model, records, args, pad_id, device, vocab):
    import torch
    model.eval()
    total_loss, total_targets = 0.0, 0
    with torch.no_grad():
        for start in range(0, len(records), args.micro_bs):
            batch = records[start:start + args.micro_bs]
            total_loss += float(loss_sum(model, batch, pad_id, device, vocab, args.ce_chunk))
            total_targets += sum(item[2] for item in batch)
    model.train()
    return total_loss / total_targets


def train(args, parent, tokenizer_file, train_file, val_file, manifest):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip

    if not torch.cuda.is_available():
        raise RuntimeError("user-owned CUDA execution is required")
    device = torch.device("cuda")
    torch.manual_seed(args.seed)
    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    pad_id = tokenizer.token_to_id("<pad>")
    if pad_id is None:
        raise ValueError("tokenizer PAD id absent")
    train_rows, val_rows = load_canonical(train_file), load_canonical(val_file)
    validate_splits(train_rows, val_rows)
    parent_state = torch.load(parent, map_location="cpu", weights_only=True)
    cfg = TMTConfig(**parent_state["cfg"])
    if tokenizer.get_vocab_size() != cfg.vocab_size:
        raise ValueError("parent and tokenizer vocab widths differ")
    model = TiedMLPTransformer(cfg).to(device)
    model.load_state_dict(_strip(parent_state["model"]), strict=True)
    model.set_anneal(1.0)
    model.train()
    tr = encode_records(train_rows, tokenizer, cfg.max_seq_len, cfg.vocab_size)
    va = encode_records(val_rows, tokenizer, cfg.max_seq_len, cfg.vocab_size)
    adam, muon = make_optimizers(model, args)
    history, updates = [], 0
    for epoch in range(1, args.epochs + 1):
        order = list(range(len(tr)))
        random.Random(args.seed + epoch).shuffle(order)
        epoch_loss, epoch_targets = 0.0, 0
        for blocks in micro_groups(tr, order, args.micro_bs, args.accum):
            target_count = sum(item[2] for block in blocks for item in block)
            adam.zero_grad(set_to_none=True)
            if muon:
                muon.zero_grad(set_to_none=True)
            for block in blocks:
                part = loss_sum(model, block, pad_id, device, cfg.vocab_size, args.ce_chunk)
                if not torch.isfinite(part):
                    raise RuntimeError(f"non-finite loss at update {updates}")
                (part / target_count).backward()
                epoch_loss += float(part.detach())
            grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not torch.isfinite(grad):
                raise RuntimeError(f"non-finite gradient at update {updates}")
            adam.step()
            if muon:
                muon.step()
            epoch_targets += target_count
            updates += 1
        val_ce = evaluate(model, va, args, pad_id, device, cfg.vocab_size)
        record = {"epoch": epoch, "updates": updates, "train_ce": epoch_loss / epoch_targets,
                  "sft_val_ce": val_ce, "assistant_train_tokens": epoch_targets}
        history.append(record)
        print(f"[SFT] epoch={epoch} updates={updates} train_ce={record['train_ce']:.6f} val_ce={val_ce:.6f}")
    evidence = {
        "schema": "TINYLM_SFT_PILOT_V1", "parent": parent.name,
        "parent_sha256": args.parent_sha256.upper(), "tokenizer_sha256": args.tokenizer_sha256.upper(),
        "train_sha256": sha256(train_file), "val_sha256": sha256(val_file),
        "optimizer": args.optimizer, "lr": args.lr, "epochs": args.epochs,
        "micro_bs": args.micro_bs, "accum": args.accum, "seed": args.seed,
        "ce_chunk": args.ce_chunk, "muon_lr_mult": args.muon_lr_mult,
        "matrix_weight_decay": args.matrix_weight_decay,
        "history": history, "pilot_only": args.pilot_only,
        "contamination_gate": manifest.get("contamination_gate", "NOT_RUN"),
        "base_full_val_forgetting": "NOT_RUN", "generation_capability": "NOT_RUN",
    }
    return {"model": model.state_dict(), "cfg": cfg.__dict__,
            "step": parent_state.get("step", 0), "sft": evidence}


def save_new(args, state):
    import torch
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    temp_model = args.output.with_suffix(".pt.partial")
    temp_log = args.log.with_suffix(".json.partial")
    if temp_model.exists() or temp_log.exists():
        raise FileExistsError("partial output exists; inspect before retry")
    torch.save(state, temp_model)
    report = dict(state["sft"])
    report["status"] = "PILOT_ONLY" if args.pilot_only else "TRAINED_EVAL_PENDING"
    report["checkpoint"] = args.output.name
    temp_log.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    os.link(temp_model, args.output)
    os.link(temp_log, args.log)
    temp_model.unlink()
    temp_log.unlink()
    print(f"[SFT] {report['status']} checkpoint={args.output} log={args.log}")


def self_test():
    from tinylm.data.prepare import SyntheticTokenizer
    tokenizer = SyntheticTokenizer()
    rows = [{"messages": [
        {"role": "user", "content": "기억값은 별빛"},
        {"role": "assistant", "content": "별빛"},
        {"role": "user", "content": "그 값은?"},
        {"role": "assistant", "content": "별빛입니다"},
    ]}]
    records = encode_records(rows, tokenizer, 256, tokenizer.get_vocab_size())
    x, y = pad_batch(records, 0)
    assert x.shape == y.shape and records[0][2] > 0 and y.eq(IGNORE).any()
    assert list(micro_groups(records, [0], 1, 4)) == [[records]]
    import torch
    import torch.nn.functional as F
    logits = torch.randn(1, 5, 17, dtype=torch.float32, requires_grad=True)
    target = torch.tensor([[1, IGNORE, 2, IGNORE, 3]])
    measured = chunked_ce_sum(logits, target, 2)
    reference = F.cross_entropy(logits.reshape(-1, 17), target.reshape(-1),
                                ignore_index=IGNORE, reduction="sum")
    assert torch.allclose(measured, reference, atol=1e-6, rtol=1e-6)
    measured_grad = torch.autograd.grad(measured, logits, retain_graph=True)[0]
    reference_grad = torch.autograd.grad(reference, logits)[0]
    assert torch.allclose(measured_grad, reference_grad, atol=1e-6, rtol=1e-6)
    left = {"meta": {"source": "aya", "source_id": "1"}, "messages": rows[0]["messages"]}
    right = {"meta": {"source": "oasst", "source_id": "2"}, "messages": rows[0]["messages"]}
    try:
        validate_splits([left], [right])
    except ValueError as exc:
        assert "prompt overlap" in str(exc)
    else:
        raise AssertionError("cross-source prompt leak was not rejected")
    print("[PASS] SFT shift/pad/multi-turn/group fixture; model/GPU NOT_RUN")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--execute", action="store_true", help="explicit user-owned training opt-in")
    for name in ("parent", "tokenizer", "train", "val", "manifest", "output", "log"):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--parent-sha256")
    parser.add_argument("--tokenizer-sha256")
    parser.add_argument("--data", default="ko-en")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--micro-bs", type=int, default=2)
    parser.add_argument("--accum", type=int, default=4)
    parser.add_argument("--ce-chunk", type=int, default=1024,
                        help="positions per fp32 CE slice; 1024 bounds temporary allocation")
    parser.add_argument("--lr", type=float)
    parser.add_argument("--optimizer", choices=("adamw", "muon"))
    parser.add_argument("--muon-lr-mult", type=float, default=4.0)
    parser.add_argument("--matrix-weight-decay", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--pilot-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.execute:
        parser.error("no training by default; --execute is required")
    for name in ("parent", "tokenizer", "train", "val", "manifest", "output", "log",
                 "parent_sha256", "tokenizer_sha256", "lr", "optimizer"):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required")
    if (args.epochs not in range(1, 5) or args.micro_bs < 1 or args.accum < 1
            or not math.isfinite(args.lr) or args.lr <= 0
            or not math.isfinite(args.matrix_weight_decay) or args.matrix_weight_decay < 0
            or args.ce_chunk < 1):
        parser.error("invalid epochs, batch, lr or matrix weight decay")
    parent, tokenizer, tr, va, manifest = check_inputs(args)
    print(f"[P090] parent={parent.name} tokenizer={tokenizer.name} contamination={manifest.get('contamination_gate')}")
    state = train(args, parent, tokenizer, tr, va, manifest)
    save_new(args, state)


if __name__ == "__main__":
    main()
