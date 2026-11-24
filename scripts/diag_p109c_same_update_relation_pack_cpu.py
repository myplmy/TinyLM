"""Compare full G4 relation losses before and after packing within one update."""

import argparse
from datetime import datetime
import math
import os
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_trained_mix_gradient_cpu as readback
from scripts import run_p109c_scratch_mixed as mixed


def pack(rows):
    shape = (mixed.prep.BATCH, mixed.prep.WIDTH)
    inputs = np.zeros(shape, dtype=np.int16)
    labels = np.full(shape, mixed.prep.IGNORE, dtype=np.int16)
    packed_segments = np.zeros(shape, dtype=np.int16)
    offsets = np.zeros(shape[0], dtype=int)
    for group, (x, y, s, _, _, _) in enumerate(rows, 1):
        for lane in range(shape[0]):
            length = int(np.count_nonzero(s[lane]))
            start, stop = offsets[lane], offsets[lane] + length
            if stop > shape[1] or length <= 0 or len(np.unique(s[lane, :length])) != 1:
                raise ValueError("all four members must fit independently inside the packed rows")
            inputs[lane, start:stop] = x[lane, :length]
            labels[lane, start:stop] = y[lane, :length]
            packed_segments[lane, start:stop] = group
            offsets[lane] = stop
    width = int(offsets.max())
    return inputs[:, :width], labels[:, :width], packed_segments[:, :width]


def measure(model, batches, counts, cutoff, *, device="cpu", flash=False):
    parameters = tuple(parameter for name, parameter in model.named_parameters()
                       if parameter.requires_grad and not name.startswith("decimal_head."))
    summed = [None] * len(parameters)
    scores, loss_sum = [], 0.
    cuda = torch.device(device).type == "cuda"
    if cuda:
        torch.cuda.synchronize()
    started = time.monotonic()
    group_count = sum(len(groups) for _, _, _, groups in batches)
    for x, y, segments, groups in batches:
        if time.time() >= cutoff:
            raise TimeoutError("the authorized relation packing readback ended")
        # Model positions retain their order inside each independent segment.
        x, target = (torch.tensor(values.astype(np.int64), device=device) for values in (x, y))
        present = torch.as_tensor(np.flatnonzero(y.ravel() != mixed.prep.IGNORE), device=device)
        kinds = torch.as_tensor(mixed.label_kinds(y, segments), device=device)
        segment = torch.tensor(segments, device=device)
        with torch.autocast("cuda", enabled=cuda, dtype=torch.bfloat16):
            hidden = mixed.masked_hidden(model, x, segments, flash=flash)
            ce, valid = mixed.prior.course_target_nll(model, hidden, target, 2048, present)
            objective = 0.
            for group, gold in enumerate(groups, 1):
                members = segment == group
                content = members & valid & target.ne(mixed.prep.END)
                choice = -(ce * content).sum(1) / content.sum(1)
                contribution = sum(ce[gold][members[gold] & (kinds[gold] == role)].sum() * (.25 * weight / counts[role])
                                   for role, weight in enumerate(mixed.KIND_WEIGHTS, 1))
                objective = objective + contribution + mixed.prior.contrast_row(choice, gold) * (
                    mixed.prior.role_loss.WEIGHTS["ALL_AXES"] / group_count)
                scores.append(choice.detach().tolist())
        loss_sum += float(objective.detach())
        values = torch.autograd.grad(objective, parameters, allow_unused=True)
        for i, new in enumerate(values):
            if new is not None:
                summed[i] = new.detach() if summed[i] is None else summed[i].add_(new)
    if cuda:
        torch.cuda.synchronize()
    return dict(scores=scores, loss=loss_sum, seconds=time.monotonic()-started), summed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("training", "manifest", "record"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists():
        parser.error("a fresh CPU-only output and the authorized deadline are required")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    bundle = mixed.Bundle(args.manifest.absolute(), args.manifest_sha256)
    model, saved, export_sha, step = readback.load_checkpoint(args.training.absolute(), bundle.digest)
    checksum = readback.evaluation.original.core6.digest(saved)
    rows, counts, n, _ = readback.update_data(bundle, readback.UPDATE)
    relations = [row for row in rows if row[4] >= 0]
    if len(relations) != n:
        raise ValueError("some actual relation questions are missing")
    dedicated = [(row[0], row[1], row[2], [row[4]]) for row in relations]
    packed = [(*pack(relations), [row[4] for row in relations])]
    cutoff = args.stop_by.timestamp()
    with sdpa_kernel(SDPBackend.MATH):
        before, before_grad = measure(model, dedicated, counts, cutoff)
        after, after_grad = measure(model, packed, counts, cutoff)
    if any((a is None) != (b is None) for a, b in zip(before_grad, after_grad, strict=True)):
        raise ValueError("the packed route activates different parameters")
    delta = [a-b if a is not None else None for a, b in zip(before_grad, after_grad, strict=True)]
    dot = readback.gradients.inner
    score_delta = np.asarray(before["scores"]) - np.asarray(after["scores"])
    result = dict(status="SAME_UPDATE_RELATION_GRADIENTS_MEASURED", precision="CPU_FP32_MATH",
                  checkpoint_sha256=checksum, export_sha256=export_sha, step=step, source_update=readback.UPDATE+1,
                  profile_sha256=bundle.digest, groups=n, optimizer_updates=0,
                  baseline=before, packed=after, gradient_relative_l2=math.sqrt(dot(delta, delta)/dot(before_grad, before_grad)),
                  max_choice_logp_delta=float(np.max(np.abs(score_delta))),
                  baseline_slots=sum(x.size for x, _, _, _ in dedicated), packed_slots=packed[0][0].size)
    bundle.unchanged()
    if readback.evaluation.original.core6.digest(saved) != checksum:
        raise ValueError("the original completed weights did not remain identical")
    args.record.mkdir(exist_ok=False)
    mixed.native.publish(args.record / "report.json", result)
    print(result, flush=True)


if __name__=="__main__":
    main()
