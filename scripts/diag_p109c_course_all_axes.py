"""Check the existing ALL_AXES objective on a single native R2 schedule."""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import signal
from time import monotonic, time
from unittest.mock import patch

import torch
import torch.nn.functional as F

from scripts import diag_p109c_course_full_shape as large
from scripts import diag_p109c_masked_course_resume as base
from scripts import p109_mix_masked_course as mixed
from scripts.run_p109b_scratch_pair_20261120 import CARD_LIMIT_MIB, idle_gpu, publish
from tinylm.model.transformer import TiedMLPTransformer
from tinylm.train import trainer


STEPS, START, BOUNDARY = 3, 1, 2
GPU = base.ROOT / "test_result/evidence/p109c_all_axes_gpu_v3_20261120"
CPU = base.ROOT / "test_result/evidence/p109c_all_axes_cpu_v5_20261120"
QUESTION_ORDER = (1, 0, 3, 2)


def layouts(width, vocab, accum):
    relation_slots = (1, 3, 5, 7)
    plain_slots = (2, 6) if accum == 8 else (11, 15, 19, 23)
    rows = []
    for graph in range(2):
        answers = [tuple(range(35 + index * 5, 37 + index * 6)) + (2,) for index in range(4)]
        for question in QUESTION_ORDER:
            prefix = (5, 7, 9 + graph, 14 + question, 20)
            for answer in answers:
                x = prefix + answer
                y = (mixed.IGNORE,) * (len(prefix) - 1) + answer
                rows.append((x + (0,) * (width - len(x)), y + (mixed.IGNORE,) * (width - len(y))))
    plain = replace(base.examples(width, vocab), start_update=START, micro_slots=plain_slots)
    axes = mixed.AllAxesCourse(mixed.Course(START, relation_slots, tuple(rows), vocab),
                               end_id=2, gold_by_question=QUESTION_ORDER * 2)
    return plain, axes


def algebra():
    generator = torch.Generator().manual_seed(317)
    scores = torch.randn(4, 4, generator=generator, requires_grad=True)
    reference = mixed.role_loss.row_contrast_sum(scores.unsqueeze(0))
    separate = sum(mixed.contrast_row(scores[index], index) for index in range(4))
    ref_grad, = torch.autograd.grad(reference, scores)
    split_grad, = torch.autograd.grad(separate, scores)
    torch.testing.assert_close(separate, reference, atol=1e-7, rtol=1e-7)
    torch.testing.assert_close(split_grad, ref_grad, atol=1e-7, rtol=1e-7)
    return dict(reference=float(reference.detach()), split=float(separate.detach()),
                max_score_gradient_error=float((split_grad - ref_grad).abs().max()))


def model_oracle():
    _, axes = layouts(16, 64, 8)
    rows = axes.layout.rows[:16]
    repeated = rows[:4] * 4
    try:
        replace(axes, layout=replace(axes.layout, rows=repeated), gold_by_question=QUESTION_ORDER)
    except ValueError as error:
        if "distinct question prefixes" not in str(error):
            raise
    else:
        raise AssertionError("identical questions with conflicting gold positions were accepted")

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(317)
        cfg = base.fixture.small_config("m100s12_g4", "tied", 16, True)
        cfg.train_repeat = 2
        model = TiedMLPTransformer(cfg)
    x, y = (torch.tensor(side) for side in zip(*rows))
    nll = F.cross_entropy(model(x).flatten(0, 1), y.flatten(),
                          ignore_index=mixed.IGNORE, reduction="none").reshape_as(y)
    valid = y.ne(mixed.IGNORE)
    content = valid & y.ne(axes.end_id)
    scores = (-(nll * content).sum(1) / content.sum(1)).reshape(4, 4)
    golds = axes.gold_by_question[:4]
    gold_rows = [question * 4 + gold for question, gold in enumerate(golds)]
    reference_ce = (nll[gold_rows].sum(1) / valid[gold_rows].sum(1)).mean()
    indices = torch.tensor(golds).unsqueeze(1)
    negative = indices.ne(torch.arange(4).unsqueeze(0))
    rank = F.softplus(scores - scores.gather(1, indices))[negative].mean()
    weight = mixed.role_loss.WEIGHTS["ALL_AXES"]
    reference_objective = reference_ce + weight * rank

    pieces = [mixed.relation_loss_terms(model, x[group:group + 4], y[group:group + 4], 16, axes.end_id, gold)
              for group, gold in zip(range(0, 16, 4), golds)]
    split_meter = torch.stack([ce + weight * (rank - rank.detach()) for ce, rank in pieces]).mean()
    torch.testing.assert_close(split_meter, reference_ce, atol=1e-6, rtol=1e-6)
    parameters = tuple(model.parameters())
    reference_grad = torch.autograd.grad(reference_objective, parameters, allow_unused=True)
    split_grad = torch.autograd.grad(split_meter, parameters, allow_unused=True)
    max_diff = 0.0
    for actual, expected in zip(split_grad, reference_grad):
        if actual is None or expected is None:
            if actual is not expected:
                raise AssertionError("gradient participation differs")
            continue
        torch.testing.assert_close(actual, expected, atol=2e-6, rtol=1e-4)
        max_diff = max(max_diff, float((actual - expected).abs().max()))
    return dict(repeated_question_rejected=True, reference_ce=float(reference_ce.detach()),
                split_ce_meter=float(split_meter.detach()), max_param_grad_error=max_diff)


def native_args(tag, width, pool, accum, gpu):
    args = base.commands(tag, width, pool)
    for option, value in {
        "--steps": STEPS, "--micro-bs": 4, "--accum": accum, "--eval-every": START,
        "--save-every": START, "--ce-recompute-rows": width,
    }.items():
        args[args.index(option) + 1] = str(value)
    return args + ["--no-ckpt"] if gpu else args


def run(out, width, vocab, pool, accum, gpu):
    out.mkdir(exist_ok=False)
    meta = base.source(out, width, vocab, pool)
    plain, axes = layouts(width, vocab, accum)
    proof = algebra()
    proof.update(model_oracle())
    baseline = idle_gpu() if gpu else None
    if bool(torch.cuda.is_available()) != gpu:
        raise RuntimeError("device selection differs")
    if gpu:
        total, used = baseline
        torch.cuda.set_per_process_memory_fraction((CARD_LIMIT_MIB - used - 512) / total)
        torch.cuda.reset_peak_memory_stats()
    torch.set_num_threads(2 if gpu else 1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    real_evaluate = trainer.evaluate
    tag = "p109c_all_axes_gpu_v3" if gpu else "p109c_all_axes_cpu_v5"
    command = native_args(tag, width, pool, accum, gpu)
    profile = dict(approval="WIP191", input="owned synthetic", device="cuda" if gpu else "cpu",
                   command=command, course=plain.binding(), all_axes=axes.binding(),
                   deterministic_cuda=gpu,
                   native_sources=mixed.routed.source_pins(),
                   source_sha256=large.file_sha(base.ROOT / "scripts/diag_p109c_course_all_axes.py"))
    publish(out / "profile.json", profile)

    def evaluate(model, loader, _count, device, **kwargs):
        return real_evaluate(model, loader, 1, device, **kwargs)

    def native(args, layout):
        return mixed.run_native(plain, args, all_axes=layout)

    def prepare(*args, **kwargs):
        if gpu:
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.allow_tf32 = False
            torch.set_float32_matmul_precision("highest")
        return meta

    def load(path):
        return torch.load(path, map_location="cpu", weights_only=True, mmap=True)

    before = monotonic()
    with (patch.object(trainer, "CKPT", out / "ckpt"), patch.object(trainer, "LOGS", out / "logs"),
          patch.object(trainer, "prepare", prepare), patch.object(trainer, "evaluate", evaluate),
          patch.object(trainer, "build_config", trainer.build_config if gpu else base.fixture.small_config)):
        split = tag + "_split"
        args = native_args(split, width, pool, accum, gpu)
        saver = torch.save
        saved = {}
        boundary = {}

        def save_observed(blob, target):
            saver(blob, target)
            target = Path(target)
            if target.parent != trainer.CKPT or target.suffix != ".pt":
                return
            for run_tag in (tag, split):
                if target.name.endswith(f"_{run_tag}.pt"):
                    saved[run_tag] = target
                    if blob["step"] == BOUNDARY:
                        boundary[run_tag] = base.fixture.state_fingerprint(load(target))
                        if run_tag == split:
                            raise base.fixture.SplitBoundary

        with patch.object(torch, "save", save_observed):
            receipt = native(command, axes)
            try:
                native(args, axes)
            except base.fixture.SplitBoundary:
                pass
            else:
                raise AssertionError("ALL_AXES native boundary was never saved")
        if boundary.get(tag) is None or boundary.get(tag) != boundary.get(split):
            raise AssertionError("ALL_AXES continuous and split controls already differ before resume")
        path = saved[split]
        resume = args + ["--resume"]
        different = replace(axes, layout=replace(axes.layout, rows=axes.layout.rows[16:] + axes.layout.rows[:16]))
        before_sha = large.file_sha(path)
        try:
            native(resume, different)
        except ValueError as error:
            if "context recipe/cache/source/runtime binding differs" not in str(error):
                raise
        else:
            raise AssertionError("a changed relation graph order resumed")
        if before_sha != large.file_sha(path):
            raise AssertionError("rejected relation resume wrote a checkpoint")
        resumed = native(resume, axes)
        final = load(saved[tag])
        restored = load(path)
        if (final["step"] != STEPS or restored["step"] != STEPS
                or base.fixture.state_fingerprint(final) != base.fixture.state_fingerprint(restored)
                or receipt["updates"][BOUNDARY:] != resumed["updates"]):
            raise AssertionError("ALL_AXES continuation and file resume differ")
        proof.update(resume_same=True, resume_boundary=BOUNDARY, changed_relations_rejected=True,
                     boundary_state=boundary[tag], checkpoint_filename=path.name)
    if gpu:
        torch.cuda.synchronize()
        proof.update(allocated_bytes=torch.cuda.max_memory_allocated(), reserved_bytes=torch.cuda.max_memory_reserved(),
                     baseline_card_mib=baseline[1])
    updates = receipt["updates"]
    expected = 4 * (2 + 3 + 4 + 5)
    if (len(updates) != STEPS or any(not value["optimizer_applied"] for value in updates)
            or any(row["draw_tokens"] != 4 * accum * width or row["visits"] != 28 for row in updates)
            or any(row["contrast_questions"] != 4 or row["contrast_candidate_targets"] != expected
                   or row["ordered_contrast_golds"] != list(QUESTION_ORDER)
                   or len(row["contrast_loss"]) != 4 for row in updates[START:])):
        raise AssertionError("ALL_AXES visit or target accounting differs")
    publish(out / "report.json", dict(complete=True, proof=proof, receipt=receipt,
                                      wall_seconds=monotonic() - before,
                                      profile_sha256=large.file_sha(out / "profile.json")))
    print("P109C_ALL_AXES_COMPLETE", profile["device"], expected, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", choices=("cpu", "gpu"))
    gpu = parser.parse_args().device == "gpu"
    budget = 240 if gpu else 120
    if time() + budget >= base.CUTOFF or os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if gpu else ""):
        raise RuntimeError("selected device or approved time unavailable")
    signal.alarm(budget)
    if gpu:
        if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
            raise ValueError("exact replay requires the sealed cuBLAS workspace")
        torch.use_deterministic_algorithms(True)
        receipt = json.loads((CPU / "report.json").read_bytes())
        cpu_profile = json.loads((CPU / "profile.json").read_bytes())
        source = base.ROOT / "scripts/diag_p109c_course_all_axes.py"
        if (not receipt["complete"] or not receipt["proof"]["resume_same"]
                or receipt["profile_sha256"] != large.file_sha(CPU / "profile.json")
                or cpu_profile["source_sha256"] != large.file_sha(source)
                or cpu_profile["course"]["source_sha256"].lower() != large.file_sha(Path(mixed.__file__))
                or cpu_profile["all_axes"]["loss_sha256"].lower() != large.file_sha(Path(mixed.role_loss.__file__))):
            raise ValueError("complete CPU algebra and resume proof is required")
        run(GPU, large.SEQ, 32768, large.POOL, large.ACCUM, True)
    else:
        run(CPU, 16, 64, 4096, 8, False)
    signal.alarm(0)


if __name__ == "__main__":
    main()
