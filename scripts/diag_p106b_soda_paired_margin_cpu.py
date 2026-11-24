"""Teach quote switches with matched histories and paired answer margins."""

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_soda_attention_evidence_cpu as prior


SEED, MARGIN_WEIGHT = 62297, .50
OLD_BASELINE = prior.original.ROOT / "test_result/evidence/p106b_soda_attention_evidence_cpu_v2_20261123/baseline.json"


def prepare(directory, tokenizer, check):
    historical, _ = prior.quote.read(prior.quote.SOURCE_MAP)
    reserved = {prior.source.hash_json([prior.source.REPO, prior.source.REVISION, row["original_index"]])
                for row in historical["rows"] if "original_index" in row}
    reserved.update(row["root"] for row in json.loads(prior.OLD_EVAL.read_text())["rows"])
    reserved.update(row["source"] for row in json.loads(OLD_BASELINE.read_text())["provided_results"])
    held_roots, held_texts, _ = prior.release.released_groups(directory, check)
    examples = prior.item_examples

    def paired(tokenizer, group, turns, pair, gap, split):
        items = examples(tokenizer, group, turns, pair, gap, "valid")
        if split == "valid":
            yield from items
            return
        swap = bool(int(group[:6], 16) % 2)
        chosen = [item for item in items if item.swap == swap and item.history in ("repeat", "switch")]
        yield from sorted(chosen, key=lambda row: (row.target if row.history == "repeat" else 1-row.target, row.history))

    with patch.object(prior, "item_examples", paired), patch.object(prior, "SEED", SEED):
        train, train_roots, train_texts = prior.choose_rows(
            directory, "train", tokenizer, check, reserved, held_roots, held_texts)
        valid, valid_roots, valid_texts = prior.choose_rows(
            directory, "valid", tokenizer, check, reserved, train_roots, train_texts)
    marker = "<|im_start|>user\n"
    if train_roots & valid_roots or train_texts & valid_texts:
        raise ValueError("the new source split has a shared original or normalized dialogue")
    for repeat, switch in zip(train[::2], train[1::2], strict=True):
        if (repeat.source != switch.source or repeat.history != "repeat" or switch.history != "switch"
                or repeat.prompt.rsplit(marker, 1)[0] != switch.prompt.rsplit(marker, 1)[0]
                or repeat.labels[0] == switch.labels[0]):
            raise ValueError("a paired training row changed more than its final quotation and correct answer")
    return train, valid


def fit(model, attention, rows, order, check, weight):
    torch.manual_seed(SEED)
    adapter = prior.prior_adapter.Residual(model.cfg.dim)
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=.002, weight_decay=.01)
    receipts = []

    def shifted(_module, args, output):
        return output + adapter.up(adapter.down(args[0]))

    with attention.q_proj.register_forward_hook(shifted):
        for step, indexes in enumerate(order, 1):
            check()
            items = [rows[i] for i in indexes]
            longest = max(len(row.prefix)+1 for row in items)
            x = torch.zeros((len(items), longest), dtype=torch.long)
            ends = torch.tensor([len(row.prefix)-1 for row in items])
            lane = torch.arange(len(items))
            for target, item in zip(x, items, strict=True):
                values = torch.tensor([*item.prefix, item.labels[0]])
                target[:len(values)] = values
            labels = torch.tensor([item.labels for item in items])
            optimizer.zero_grad(set_to_none=True)
            hidden = model(x, return_hidden=True)
            logits = model._head_logits(hidden[lane[:, None], ends[:, None] + torch.arange(2)])
            ce = F.cross_entropy(logits.flatten(0, 1), labels.flatten())
            gold = labels[:, 0]
            foil = gold.reshape(-1, 2).flip(1).flatten()
            margin = logits[lane, 0, gold] - logits[lane, 0, foil]
            # A constant bias toward the identical earlier answer cancels in each pair.
            paired = F.softplus(1. - margin.reshape(-1, 2).sum(dim=1)).mean()
            loss = ce + weight * paired
            if not torch.isfinite(loss):
                raise ValueError("the paired and token losses must stay finite")
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            receipts.append(dict(ce=float(ce.detach()), paired=float(paired.detach()), gradient=float(norm)))
            if step == 1 or step % 16 == 0:
                print("SODA_PAIRED_TRAIN", weight, step, receipts[-1], flush=True)
    return adapter.eval(), receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("original-dir", "training", "record"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--training-manifest-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    digest = prior.original.core6.digest
    paths = (Path(__file__), Path(prior.__file__), prior.OLD_EVAL, OLD_BASELINE)
    pins = {str(path): digest(path) for path in paths}
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists()
            or pins[str(paths[0])] != prior.native.digest(args.source_sha256)):
        parser.error("the CPU-only source, fresh output and authorized deadline are required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)

    def check():
        if time.time() >= args.stop_by.timestamp():
            raise TimeoutError("the paired SODA experiment has reached its approved cutoff")

    tokenizer = prior.original.load_tokenizer()
    train, valid = prepare(args.original_dir, tokenizer, check)
    rng = np.random.default_rng(SEED)
    order = np.arange(len(train)).reshape(-1, 4)[rng.permutation(len(train)//4)]
    end = prior.original.read_json(args.training / "input.json")["steps"]
    with patch.object(prior.native, "STEPS", end):
        weights, sha = prior.evaluation.completed_v2(args.training.absolute(), args.training_manifest_sha256)
    with torch.no_grad():
        model = prior.original.load_model(weights, end, "cpu").requires_grad_(False)
    attention = model.layers[prior.ATTENTION_LAYER].attn_mod
    if model.visit_schedule().count(prior.ATTENTION_LAYER) != 1:
        raise ValueError("the fixed query projection must be visited once")
    args.record.mkdir(exist_ok=False)
    results = {}
    with sdpa_kernel(SDPBackend.MATH):
        for name, weight in (("paired_next_token", 0.), ("paired_margin", MARGIN_WEIGHT)):
            adapter, updates = fit(model, attention, train, order, check, weight)
            report = prior.score(model, attention, adapter, tokenizer, valid, check)
            results[name] = report["totals"]
            prior.native.publish(args.record / f"{name}.json", dict(report, updates=updates))
    if digest(weights) != sha or pins != {str(path): digest(path) for path in paths}:
        raise ValueError("a sealed source or the original model changed")
    prior.native.publish(args.record / "report.json", dict(status="SODA_PAIRED_MARGIN_CONTRAST_COMPLETE",
        input_pins=pins, model_sha256=sha, source_release=prior.source.REVISION, training_rows=len(train),
        valid_rows=len(valid), training_roots=len({row.source for row in train}),
        valid_roots=len({row.source for row in valid}), histories=dict(Counter(row.history for row in train)),
        optimizer_updates_per_arm=len(order), margin_weight=MARGIN_WEIGHT, results=results,
        teacher_calls=0, model_writes=0))
    print(results, flush=True)


if __name__ == "__main__":
    main()
