"""Dose-matched STE reuse on the actual P109C raw and mixed training path."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

import torch

from scripts import p109_mix_masked_course as mixed
from scripts import run_p109c_scratch330 as entry
from scripts import test_p109c_scratch_bundle as fixture
from scripts.diag_p109_ntp_visit_resume import SplitBoundary, state_fingerprint
from tinylm.train import packed_document_training as packed, trainer


def checkpoint(root):
    return root / "ckpt" / f"{entry.PRESET}_ko-en_330M_{entry.TAG}.pt"


def fingerprint(root):
    state = torch.load(checkpoint(root), weights_only=True, map_location="cpu", mmap=True)
    return state_fingerprint(state)


def arm(bundle, root, *, reuse, resume=False):
    start = 0.0
    clips, durations = [], []
    cursor = mixed.MicroTokensCursor
    prepare_native, finish_native = cursor.prepare, cursor.finish
    clip_native = torch.nn.utils.clip_grad_norm_
    gpu = torch.cuda.is_available()

    def prepare(self):
        nonlocal start
        if gpu:
            torch.cuda.synchronize()
        start = perf_counter()
        return prepare_native(self)

    def finish(self, *, optimizer_applied):
        if gpu:
            torch.cuda.synchronize()
        durations.append(perf_counter() - start)
        return finish_native(self, optimizer_applied=optimizer_applied)

    def clip(parameters, max_norm):
        parameters = list(parameters)
        value = clip_native(parameters, max_norm)
        clips.append(dict(norm=float(value), present=sum(parameter.grad is not None for parameter in parameters)))
        return value

    if gpu:
        torch.cuda.reset_peak_memory_stats()
    with (patch.object(trainer, "CKPT", root / "ckpt"), patch.object(trainer, "LOGS", root / "logs"),
          patch.object(cursor, "prepare", prepare), patch.object(cursor, "finish", finish),
          patch.object(torch.nn.utils, "clip_grad_norm_", clip)):
        result = entry.train_bundle(bundle, resume, reuse_quantization=reuse)
    metadata = dict(weights=fingerprint(root), updates=result["updates"], clip=clips, update_seconds=durations)
    if gpu:
        metadata.update(peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                        peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
    return metadata


def semantic_updates(report):
    return [{key: value for key, value in update.items() if key != "prepared_quantization_tensors"}
            for update in report["updates"]]


def model_sources():
    from scripts import diag_p109b_ste_exact_micro as ste

    return {str(Path(file).relative_to(mixed.routed.ROOT)): entry.file_sha(Path(file)).upper()
            for file in (Path(__file__), entry.__file__, mixed.__file__, ste.__file__, trainer.__file__)}


def cpu(out):
    if torch.cuda.is_available():
        raise RuntimeError("explicit CPU execution is required")
    torch.set_num_threads(1)
    args_native, evaluate_native = entry.native_args, trainer.evaluate
    save_native = packed.save_packed_checkpoint
    out.mkdir(exist_ok=False)
    with (TemporaryDirectory(prefix="p109c_ste_cpu_") as directory,
          patch.multiple(entry, STEPS=fixture.STEPS, BOUNDARY=fixture.BOUNDARY, MICRO=fixture.MICRO,
                         ACCUM=fixture.ACCUM, WIDTH=fixture.WIDTH, VOCAB=fixture.VOCAB, EVAL_EVERY=1),
          patch.object(entry, "native_args", side_effect=lambda pool, resume:
                       args_native(pool, resume) + ["--anneal-start", "0"]),
          patch.object(trainer, "build_config", fixture.small_model),
          patch.object(trainer, "evaluate", side_effect=lambda model, loader, _, device, **kwargs:
                       evaluate_native(model, loader, 2, device, **kwargs))):
        root = Path(directory)
        manifest = root / "bundle.json"
        bundle = entry.load_bundle(manifest, fixture.write_manifest(manifest, fixture.make_bundle(root)))
        baseline = arm(bundle, root / "base", reuse=False)
        use = arm(bundle, root / "reuse", reuse=True)
        split = root / "split"

        def save(path, state):
            save_native(path, state)
            if path == checkpoint(split) and state["step"] == fixture.BOUNDARY + 1:
                raise SplitBoundary()

        with patch.object(packed, "save_packed_checkpoint", save):
            try:
                arm(bundle, split, reuse=True)
            except SplitBoundary:
                pass
            else:
                raise AssertionError("the mixed checkpoint boundary was not captured")
        before = entry.file_sha(checkpoint(split))
        try:
            arm(bundle, split, reuse=False, resume=True)
        except ValueError as error:
            if "binding differs" not in str(error):
                raise
        else:
            raise AssertionError("resume accepted a different quantization path")
        if entry.file_sha(checkpoint(split)) != before:
            raise AssertionError("rejected resume changed the checkpoint")
        resumed = arm(bundle, split, reuse=True, resume=True)

    if (baseline["weights"] != use["weights"] or baseline["clip"] != use["clip"]
            or semantic_updates(baseline) != semantic_updates(use) or use["weights"] != resumed["weights"]
            or use["updates"][fixture.BOUNDARY + 1:] != resumed["updates"]
            or use["clip"][fixture.BOUNDARY + 1:] != resumed["clip"]):
        raise AssertionError("the completed native states or mixed observations differ")
    entry.publish(out / "report.json", dict(synthetic=True, sources=model_sources(), ages="raw2_mixed2",
                  baseline=baseline, reuse=use, resumed=resumed, wrong_mode_rejected=True))


def cuda_worker(path, sha256, _resume, record, _cutoff):
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("one CUDA device is required")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        args_native, evaluate_native = entry.native_args, trainer.evaluate
        arms = {}
        with (patch.multiple(entry, STEPS=fixture.STEPS, BOUNDARY=fixture.BOUNDARY, EVAL_EVERY=fixture.STEPS),
              patch.object(entry, "native_args", side_effect=lambda pool, resume:
                           args_native(pool, resume) + ["--anneal-start", "0"]),
              patch.object(trainer, "evaluate", side_effect=lambda model, loader, _, device, **kwargs:
                           evaluate_native(model, loader, 2, device, **kwargs))):
            bundle = entry.load_bundle(path, sha256)
            for tag, reuse in (("a1", False), ("b1", True), ("b2", True), ("a2", False)):
                with (TemporaryDirectory(prefix=f"p109c_ste_{tag}_") as directory,
                      patch.object(entry, "TAG", f"p109c_ste_{tag}_chat32_s1337")):
                    arms[tag] = arm(bundle, Path(directory), reuse=reuse)
                entry.publish(record / f"{tag}.json", arms[tag])
        entry.publish(record / "report.json", dict(synthetic=True, sources=model_sources(),
            order=list(arms), arms=arms, native_input_slots=4 * 4 * 32 * 1024))


def cuda(out):
    deadline = min(datetime.now().astimezone() + timedelta(minutes=6),
                   datetime.fromisoformat("2026-11-21T13:00:00+09:00"))
    with (TemporaryDirectory(prefix="p109c_ste_input_") as directory,
          patch.multiple(fixture, ACCUM=32, WIDTH=1024, VOCAB=32768), patch.object(entry, "gpu_worker", cuda_worker)):
        path = Path(directory) / "bundle.json"
        sha = fixture.write_manifest(path, fixture.make_bundle(path.parent))
        return entry.supervise(path, sha, False, out, deadline)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("--cpu", "--cuda"):
        raise SystemExit("choose --cpu or --cuda and a fresh evidence directory")
    sys.exit((cpu if sys.argv[1] == "--cpu" else cuda)(Path(sys.argv[2])))
