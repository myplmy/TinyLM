"""Measure how the training-only decimal head changes clipping on the same fixture."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import math
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import torch

from scripts import p109_mix_masked_course as mixed
from scripts import run_p109c_scratch330 as entry
from scripts import test_p109c_scratch_bundle as fixture
from tinylm.train import trainer


@dataclass
class Observation:
    body_before: float
    head_before: float
    body_after: float
    head_after: float
    body_delta: float | None = None
    head_delta: float | None = None


def norm(tensors):
    norms = [torch.linalg.vector_norm(tensor.detach(), dtype=torch.float64) for tensor in tensors]
    return float(torch.linalg.vector_norm(torch.stack(norms))) if norms else 0.0


def run_variant(mode, bundle, root):
    clip_native = torch.nn.utils.clip_grad_norm_
    init_native = mixed.DecimalG4.__init__
    finish_native = mixed.MicroTokensCursor.finish
    object_native = mixed.joint_decimal.objective
    measurements = []
    groups = before = None

    def init_model(model, cfg):
        nonlocal groups
        init_native(model, cfg)
        body, head = [], []
        for name, parameter in model.named_parameters():
            (head if name.startswith("decimal_head.") else body).append(parameter)
        groups = body, head

    def gradients(parameters):
        return norm(p.grad for p in parameters if p.grad is not None)

    def clip_gradients(parameters, max_norm):
        nonlocal before
        body, head = groups
        before = [[p.detach().clone() for p in group] for group in groups]
        body_before, head_before = gradients(body), gradients(head)
        if mode == "split":
            total = torch.hypot(clip_native(body, max_norm), clip_native(head, max_norm))
        else:
            total = clip_native(parameters, max_norm)
        measurements.append(Observation(body_before, head_before, gradients(body), gradients(head)))
        return total

    def finish(cursor, *, optimizer_applied):
        observation = measurements[-1]
        if not optimizer_applied:
            raise AssertionError("the fixture skipped an optimizer update")
        observation.body_delta, observation.head_delta = (
            norm(p.detach() - original for p, original in zip(group, prior))
            for group, prior in zip(groups, before))
        return finish_native(cursor, optimizer_applied=optimizer_applied)

    def objective(*args, **kwargs):
        loss, count, correct, events = object_native(*args, **kwargs)
        return (loss * 0 if mode == "off" else loss), count, correct, events

    with (patch.object(trainer, "CKPT", root / "ckpt"), patch.object(trainer, "LOGS", root / "logs"),
          patch.object(mixed.DecimalG4, "__init__", init_model),
          patch.object(mixed.MicroTokensCursor, "finish", finish),
          patch.object(mixed.joint_decimal, "objective", objective),
          patch.object(torch.nn.utils, "clip_grad_norm_", clip_gradients)):
        receipt = entry.train_bundle(bundle, resume=False)
    return [dict(asdict(row), update=result["index"]) for row, result in zip(measurements, receipt["updates"])]


def main(out):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("the diagnostic needs an explicitly CPU-only environment")
    torch.set_num_threads(1)
    real_args = entry.native_args
    evaluate = trainer.evaluate
    out.mkdir(exist_ok=False)
    with (TemporaryDirectory(prefix="p109c_clipping_") as directory,
          patch.multiple(entry, STEPS=fixture.STEPS, BOUNDARY=fixture.BOUNDARY, MICRO=fixture.MICRO,
                         ACCUM=fixture.ACCUM, WIDTH=fixture.WIDTH, VOCAB=fixture.VOCAB, EVAL_EVERY=fixture.STEPS),
          patch.object(entry, "native_args", side_effect=lambda pool, resume:
                       real_args(pool, resume) + ["--anneal-start", "0"]),
          patch.object(trainer, "build_config", fixture.small_model),
          patch.object(trainer, "evaluate", side_effect=lambda model, loader, _, device, **kwargs:
                       evaluate(model, loader, 2, device, **kwargs))):
        root = Path(directory)
        path = root / "input.json"
        sha = fixture.write_manifest(path, fixture.make_bundle(root))
        bundle = entry.load_bundle(path, sha)
        modes = ("global", "split", "off")
        arms = {mode: run_variant(mode, bundle, root / mode) for mode in modes}
    boundary = fixture.BOUNDARY
    a, b, c = (arms[mode][boundary] for mode in modes)
    if not (arms["global"][:boundary] == arms["off"][:boundary]
            and math.isclose(a["body_before"], b["body_before"], abs_tol=1e-8)
            and math.isclose(a["body_before"], c["body_before"], abs_tol=1e-8)
            and a["head_before"] == b["head_before"] and c["head_before"] == c["head_delta"] == 0
            and math.isclose(b["body_after"], c["body_after"], rel_tol=1e-6)
            and a["body_after"] < b["body_after"] and not torch.cuda.is_initialized()):
        raise AssertionError("the first mixed update does not isolate the auxiliary head")
    entry.publish(out / "report.json", dict(synthetic=True, input_slots=fixture.STEPS * fixture.MICRO * fixture.ACCUM * fixture.WIDTH,
                  first_mix=boundary, arms=arms, sources=source_pins()))
    print("P109C_DECIMAL_CLIP", {mode: arms[mode][boundary] for mode in modes})


def source_pins():
    sources = (Path(__file__), Path(entry.__file__), Path(mixed.__file__), Path(fixture.__file__), Path(trainer.__file__))
    return {str(path): fixture.seal(path) for path in sources}


def cuda_worker(path, sha256, _resume, record, _cutoff):
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log), TemporaryDirectory(prefix="p109c_clip_cuda_run_") as directory):
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("the clipping diagnostic needs one CUDA device")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        boundary = fixture.BOUNDARY
        real_args = entry.native_args
        evaluate = trainer.evaluate
        with (patch.multiple(entry, STEPS=fixture.STEPS, BOUNDARY=boundary, EVAL_EVERY=fixture.STEPS),
              patch.object(entry, "native_args", side_effect=lambda pool, resume:
                           real_args(pool, resume) + ["--anneal-start", "0"]),
              patch.object(trainer, "evaluate", side_effect=lambda model, loader, _, device, **kwargs:
                           evaluate(model, loader, 2, device, **kwargs))):
            bundle = entry.load_bundle(path, sha256)
            arms = {}
            for mode in ("global", "split"):
                with patch.object(entry, "TAG", f"p109c_decimal_clip_gpu_chat32_{mode}_s1337"):
                    arms[mode] = run_variant(mode, bundle, Path(directory) / mode)
        entry.publish(record / "report.json", dict(device="cuda", synthetic=True, arms=arms,
                      first_mix=boundary, input_slots=fixture.STEPS * 4 * 32 * 1024, sources=source_pins(),
                      peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                      peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20))


def cuda_main(out):
    window_end = datetime.fromisoformat("2026-11-21T13:00:00+09:00")
    now = datetime.now().astimezone()
    if now + timedelta(minutes=4) >= window_end:
        raise RuntimeError("insufficient remaining time for the CUDA clipping diagnostic")
    with (TemporaryDirectory(prefix="p109c_clip_cuda_inputs_") as directory,
          patch.multiple(fixture, ACCUM=32, WIDTH=1024, VOCAB=32768),
          patch.object(entry, "gpu_worker", cuda_worker)):
        path = Path(directory) / "input.json"
        sha = fixture.write_manifest(path, fixture.make_bundle(path.parent))
        return entry.supervise(path, sha, False, out, now + timedelta(minutes=4))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cuda":
        sys.exit(cuda_main(Path(sys.argv[2])))
    main(Path(sys.argv[1]))
