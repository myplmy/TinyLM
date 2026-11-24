"""Measure native primary and auxiliary gradient contributions on actual course rows."""

import argparse
from datetime import datetime
import math
import os
from pathlib import Path
from time import perf_counter, time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import eval_p109c_completed as completed
from scripts import p109_mix_masked_course as sequence
from scripts import run_p109c_scratch330 as entry
from tinylm.config import TMTConfig


def trimmed_batch(layout, first):
    records = tuple(layout.rows[index] for index in range(first, first + entry.MICRO))
    x, labels = (torch.tensor(values, dtype=torch.long) for values in zip(*records, strict=True))
    width = int(labels.ne(sequence.IGNORE).nonzero().amax(dim=0)[1]) + 1
    return x[:, :width].contiguous(), labels[:, :width].contiguous()


def losses(model, bundle, offset, kind):
    if kind == "decimal":
        first = offset * entry.MICRO
        x, y = trimmed_batch(bundle.plain, first)
        hidden = model(x, return_hidden=True)
        nll, valid = sequence.course_target_nll(model, hidden, y, rows=2048)
        labels, windows = [], []
        for index in range(first, first + entry.MICRO):
            case = bundle.decimal.by_row.get(index)
            labels.append(case[0] if case is not None else None)
            windows.append([case[1]] if case is not None else [])
        decimal, count, _, _ = sequence.joint_decimal.objective(model.decimal_head, hidden, y, labels, windows)
        if count != 1:
            raise ValueError("one admitted decimal event is required per measured update")
        return nll.sum() / (entry.ACCUM * valid.sum()), decimal / count, x.shape[1]
    query = offset * len(bundle.all_axes.layout.micro_slots)
    x, y = trimmed_batch(bundle.all_axes.layout, query * entry.MICRO)
    gold = bundle.all_axes.gold_by_question[query]
    primary, ranking = sequence.relation_loss_terms(model, x, y, 2048, bundle.all_axes.end_id, gold)
    weight = sequence.role_loss.WEIGHTS["ALL_AXES"] / len(bundle.all_axes.layout.micro_slots)
    return primary / entry.ACCUM, ranking * weight, x.shape[1]


def inner(xs, ys):
    return sum(float(torch.dot(x.flatten(), y.flatten()))
               for x, y in zip(xs, ys, strict=True) if x is not None and y is not None)


def measure(model, bundle, offset, kind):
    base, auxiliary, width = losses(model, bundle, offset, kind)
    parameters = [(name, value) for name, value in model.named_parameters() if value.requires_grad]
    values = tuple(value for _, value in parameters)
    base_grad = torch.autograd.grad(base, values, allow_unused=True, retain_graph=True)
    aux_grad = torch.autograd.grad(auxiliary, values, allow_unused=True)
    results = {}
    for role in ("body", "decimal_head"):
        indices = [i for i, (name, _) in enumerate(parameters)
                   if name.startswith("decimal_head.") == (role == "decimal_head")]
        previous, added = ([grad[i] for i in indices] for grad in (base_grad, aux_grad))
        left = math.sqrt(inner(previous, previous))
        right = math.sqrt(inner(added, added))
        dot = inner(previous, added)
        if not all(math.isfinite(v) for v in (left, right, dot)):
            raise ValueError("nonfinite course gradient comparison")
        results[role] = dict(primary_norm=left, auxiliary_norm=right, dot=dot,
                             cosine=dot / (left * right) if left and right else None)
    return dict(kind=kind, actual_update=entry.BOUNDARY + offset, effective_width=width,
                primary_batch_term=float(base.detach()), auxiliary_term=float(auxiliary.detach()), groups=results)


def load_native_model(path, inference_path, expected_step, *, head_in_saved_state):
    saved = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if saved["step"] != expected_step:
        raise ValueError("the checkpoint step differs")
    cfg = TMTConfig(**saved["cfg"])
    model = sequence.DecimalG4(cfg).train()
    missing, unexpected = model.load_state_dict(saved["model"], strict=head_in_saved_state)
    expected_missing = [] if head_in_saved_state else ["decimal_head.weight", "decimal_head.bias"]
    if list(missing) != expected_missing or unexpected:
        raise ValueError("the native body or auxiliary head differs")
    if head_in_saved_state:
        inference = torch.load(inference_path, map_location="cpu", weights_only=True, mmap=True)
        body = {name: value for name, value in saved["model"].items() if not name.startswith("decimal_head.")}
        if set(body) != set(inference["model"]) or any(not torch.equal(v, inference["model"][k]) for k, v in body.items()):
            raise ValueError("the native checkpoint does not match the completed inference export")
    model.training_route = tuple(model.visit_schedule())
    if len(model.training_route) != 28 or cfg.grad_checkpoint:
        raise ValueError("the native 28-visit training configuration differs")
    model.set_anneal(1.)
    return model


def evaluate(args):
    if time() >= args.stop_by.timestamp():
        raise TimeoutError("the CPU gradient diagnostic deadline has passed")
    profile_path = completed.regular_file(args.profile.absolute())
    profile = completed.read_json(profile_path)
    if (completed.core6.digest(profile_path) != args.profile_sha256.upper()
            or completed.source_pins() != profile["sources"]):
        raise ValueError("the official evaluation profile differs")
    record = Path(profile["training_record"])
    inference, inference_sha = completed.completed_checkpoint(record, profile["training_manifest_sha256"])
    midpoint = completed.regular_file(record / "evaluation_steps" / "aoa_step_2060.pt")
    midpoint_receipt = completed.read_json(midpoint.with_suffix(".json"))
    if completed.core6.digest(midpoint) != midpoint_receipt["sha256"] or midpoint_receipt["step"] != entry.BOUNDARY:
        raise ValueError("the before-course checkpoint receipt differs")
    bundle = entry.load_bundle(args.bundle.absolute(), profile["training_manifest_sha256"])
    final_stage = args.stage == "complete"
    if final_stage:
        native = completed.regular_file(args.native_checkpoint.absolute())
        path, step = native, entry.STEPS
    else:
        path, step = midpoint, entry.BOUNDARY
    sources = (Path(__file__), Path(sequence.__file__), Path(sequence.joint_decimal.__file__),
               Path(sequence.role_loss.__file__), inference, path)
    pins = {str(item): completed.core6.digest(item) for item in sources}
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    started = perf_counter()
    results = []
    with sdpa_kernel(SDPBackend.MATH):
        model = load_native_model(path, inference, step, head_in_saved_state=final_stage)
        for offset in (0, 1):
            for kind in ("decimal", "relation"):
                if time() >= args.stop_by.timestamp():
                    raise TimeoutError("the CPU gradient diagnostic reached its cutoff")
                row = measure(model, bundle, offset, kind)
                results.append(row)
                print("P109C_COURSE_GRADIENT_ROW", step, row, flush=True)
    if (completed.source_pins() != profile["sources"]
            or any(completed.core6.digest(Path(path)) != sha for path, sha in pins.items())):
        raise ValueError("a sealed gradient input changed")
    bundle.unchanged()
    entry.publish(args.output, dict(status="COMPLETE", precision="CPU_FP32_MATH", step=step, samples=results,
                                    model_sha256=pins[str(path)], evaluation_sha256=inference_sha,
                                    sources=pins, seconds=perf_counter()-started))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--stage", choices=("before_course", "complete"), required=True)
    parser.add_argument("--native-checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.output.exists():
        parser.error("CPU-only device, a fresh output and an explicit cutoff timezone are required")
    if args.stage == "complete" and args.native_checkpoint is None:
        parser.error("the complete stage needs the exact full native checkpoint")
    evaluate(args)


if __name__ == "__main__":
    main()
