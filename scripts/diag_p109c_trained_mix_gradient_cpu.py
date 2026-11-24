"""Measure one identical mixed update's loss directions on the finished P109C v2 body."""

import argparse
from datetime import datetime
from itertools import combinations_with_replacement
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_course_gradient_components as gradients
from scripts import eval_p109c_mixed_v2 as evaluation
from scripts import run_p109c_scratch_mixed as mixed


COMPONENTS = ("raw", "assistant", "relation", "decimal")
UPDATE = 152


def load_checkpoint(record, digest):
    last = evaluation.original.read_json(record / "input.json")["steps"]
    with patch.object(mixed.native, "STEPS", last):
        export, export_sha = evaluation.completed_v2(record, digest)
    paths = [p for p in (record / "ckpt").glob("*.pt") if not p.name.endswith("_best.pt")]
    if len(paths) != 1:
        raise ValueError("the finished native optimizer checkpoint must be unique")
    native = paths[0]
    model = gradients.load_native_model(native, export, last, head_in_saved_state=True)
    return model, native, export_sha, last


def update_data(bundle, update):
    rows = []
    counts = np.zeros(4, dtype=np.int64)
    contrast = decimal = 0
    for lane, index in bundle.schedule[update]:
        if lane == -1:
            raw = bundle.raw_batch(np.asarray([index]))[0]
            rows.append((raw[:, :-1], raw[:, 1:], None, None, -1, ()))
            counts[0] += mixed.MICRO_TOKENS
        elif lane >= 0:
            x, y, segments = bundle.data[lane][index].transpose(1, 0, 2)
            info = bundle.aux[lane][index]
            gold, events = info["gold"], info["decimal"]
            kinds = mixed.label_kinds(y, segments)
            if gold >= 0:
                kinds[np.arange(mixed.prep.BATCH) != gold] = 0
                contrast += 1
            decimal += len(events)
            counts[1:] += np.bincount(kinds.ravel(), minlength=4)[1:]
            rows.append((x, y, segments, kinds, gold, events))
    if not all(counts) or contrast == 0 or decimal == 0 or len(rows) != mixed.prep.ACCUM:
        raise ValueError("the matched actual update must activate every loss term")
    return rows, counts.tolist(), contrast, decimal


def losses(model, row, counts, relation_count, decimal_count, share):
    tokens, labels, segments, kinds, gold, events = row
    x = torch.tensor(np.array(tokens), dtype=torch.long)
    y = torch.tensor(np.array(labels), dtype=torch.long)
    if segments is None:
        nll, _ = mixed.target_nll(model, model(x, return_hidden=True), y, rows=1024)
        return {"raw": nll.sum() * (1-share)/counts[0]}
    hidden = mixed.masked_hidden(model, x, segments, flash=False)
    positions = torch.as_tensor(np.flatnonzero(labels.ravel() != mixed.prep.IGNORE))
    nll, valid = mixed.prior.course_target_nll(model, hidden, y, rows=2048, positions=positions)
    kind = torch.as_tensor(kinds)
    parts = {"assistant": sum(nll[kind == i].sum()*share*weight/counts[i]
                               for i, weight in enumerate(mixed.KIND_WEIGHTS, 1))}
    if gold >= 0:
        content = valid & y.ne(mixed.prep.END)
        score = -(nll * content).sum(1) / content.sum(1)
        parts["relation"] = mixed.prior.contrast_row(score, gold) * (
            mixed.prior.role_loss.WEIGHTS["ALL_AXES"] / relation_count)
    if events:
        group, column = torch.as_tensor([event[:2] for event in events]).T
        values = [event[2] for event in events]
        loss, count, _, _ = mixed.prior.joint_decimal.objective(
            model.decimal_head, hidden[group, column, None], y[group, column, None], values,
            [[0]] * len(events))
        if count != len(events):
            raise ValueError("the same training event must remain eligible")
        parts["decimal"] = loss * .02 / decimal_count
    return parts


def analyze(model, batch, counts, contrasts, decimals, cutoff):
    trainable = [(name, value) for name, value in model.named_parameters() if value.requires_grad]
    params = tuple(value for _, value in trainable)
    body = [i for i, (name, _) in enumerate(trainable) if not name.startswith("decimal_head.")]
    accumulated = {name: [None] * len(params) for name in COMPONENTS}
    values = dict.fromkeys(COMPONENTS, 0.)
    with sdpa_kernel(SDPBackend.MATH):
        for index, row in enumerate(batch, 1):
            if time.time() >= cutoff:
                raise TimeoutError("the authorized gradient readback ended")
            parts = losses(model, row, counts, contrasts, decimals, .25)
            for i, (name, loss) in enumerate(parts.items(), 1):
                values[name] += float(loss.detach())
                update = torch.autograd.grad(loss, params, allow_unused=True, retain_graph=i < len(parts))
                for j, value in enumerate(update):
                    if value is not None:
                        if accumulated[name][j] is None:
                            accumulated[name][j] = value.detach()
                        else:
                            accumulated[name][j].add_(value)
            if index % 4 == 0:
                print("P109C_MIX_GRADIENT_MICROS", index, flush=True)
    dots = {name: {} for name in COMPONENTS}
    for a, b in combinations_with_replacement(COMPONENTS, 2):
        left, right = ([accumulated[name][i] for i in body] for name in (a, b))
        dots[a][b] = dots[b][a] = gradients.inner(left, right)
    if not all(math.isfinite(value) for row in dots.values() for value in row.values()):
        raise ValueError("each diagnostic gradient inner product must be finite")
    return values, dots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("training", "manifest", "record"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists():
        parser.error("a fresh CPU-only output and the authorized deadline are required")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    began = time.monotonic()
    bundle = mixed.Bundle(args.manifest.absolute(), args.manifest_sha256)
    model, original, export_sha, step = load_checkpoint(args.training.absolute(), bundle.digest)
    stamp = evaluation.original.core6.digest(original)
    data, counts, contrasts, decimals = update_data(bundle, UPDATE)
    values, dots = analyze(model, data, counts, contrasts, decimals, args.stop_by.timestamp())
    if evaluation.original.core6.digest(original) != stamp:
        raise ValueError("the completed native weights changed during readback")
    bundle.unchanged()
    args.record.mkdir(exist_ok=False)
    mixed.native.publish(args.record / "report.json", dict(status="TRAINED_GRADIENT_READBACK_COMPLETE",
        precision="CPU_FP32_MATH", saved_step=step, native_checkpoint_sha256=stamp, export_sha256=export_sha,
        profile_sha256=bundle.digest, update_number=UPDATE+1, target_counts=counts, relation_questions=contrasts,
        decimal_events=decimals, component_loss=values, body_dot_products=dots, optimizer_updates=0,
        body_norm={name: math.sqrt(dots[name][name]) for name in COMPONENTS}, seconds=time.monotonic()-began))


if __name__ == "__main__":
    main()
