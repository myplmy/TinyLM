"""Compare STE reuse on sustained native G4 updates with sealed authored course rows."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109c_ste_native as diagnostic
from scripts import run_p109c_scratch330 as entry
from tinylm.train import trainer


ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / "test_result/evidence/p109c_authored_curriculum_correction_only_cpu_v1_20261121"
STEPS, BOUNDARY, EVAL_EVERY, EVAL_BATCHES = 24, 8, 8, 8
ORDER = (("a1", False), ("b1", True), ("b2", True), ("a2", False))
STUDY = "p109c_ste_sustained_v1_20261121"
AUTHORIZED_END = datetime.fromisoformat("2026-11-22T13:00:00+09:00")


def sealed_file(path):
    return dict(file=path.name, sha256=entry.file_sha(path).upper())


def pin(spec):
    path = entry.bundle_path(COURSE, spec["file"])
    if entry.file_sha(path).upper() != entry.digest(spec["sha256"]):
        raise ValueError(f"authored input changed: {path.name}")
    return path


def sources():
    path = Path(__file__).resolve()
    return {**diagnostic.model_sources(), str(path.relative_to(ROOT)): entry.file_sha(path).upper()}


def build_bundle(root, deterministic_match):
    source = COURSE / "compiled_manifest.json"
    original = json.loads(source.read_bytes())
    course = original["course"]
    mixed_updates = STEPS - BOUNDARY
    tokenizer = root / "tokenizer.json"
    copyfile(pin(original["tokenizer"]), tokenizer)
    tokenizer_spec = sealed_file(tokenizer)
    if tokenizer_spec["sha256"] != entry.digest(course["tokenizer_sha256"]):
        raise ValueError("the authored course tokenizer differs")

    train_count = 2 * STEPS * entry.MICRO * entry.ACCUM * entry.WIDTH
    val_count = 64 * entry.WIDTH
    cache = root / "synthetic_raw_chat32"
    cache.mkdir()
    rng = np.random.default_rng(104)
    for split, length in (("train", train_count), ("val", val_count)):
        rng.integers(64, entry.VOCAB, size=length, dtype=np.uint16).tofile(cache / f"{split}.bin")
    entry.publish(cache / "meta.json", dict(data="ko-en", vocab=entry.VOCAB, token_dtype="uint16",
        tokenizer_lineage="chat32", tokenizer_sha256=tokenizer_spec["sha256"], train=train_count,
        val=val_count, tokens=train_count + val_count))

    def copy_rows(name, count):
        path = root / (name + ".npy")
        rows = np.load(pin(course[name]), mmap_mode="r", allow_pickle=False)
        if len(rows) < count:
            raise ValueError("the pinned course has insufficient rows")
        np.save(path, rows[:count], allow_pickle=False)
        return sealed_file(path)

    plain_slots, axes_slots = course["plain"]["slots"], course["all_axes"]["slots"]
    plain_count = mixed_updates * len(plain_slots) * entry.MICRO
    axes_count = mixed_updates * len(axes_slots) * entry.MICRO
    bundle = dict(schema=entry.SCHEMA, source_release=entry.RELEASE,
        admission=dict(raw="SYNTHETIC_RAW_FOR_STE_RESOURCE_DIAGNOSTIC", course=original["admission"]["course"]),
        cache=dict(directory=cache.name, sha256={name: entry.file_sha(cache / name) for name in entry.CACHE_FILES}),
        tokenizer=tokenizer_spec, course=dict(tokenizer_sha256=tokenizer_spec["sha256"],
            plain=dict(copy_rows("plain", plain_count), slots=plain_slots),
            all_axes=dict(copy_rows("all_axes", axes_count), slots=axes_slots,
                          gold=course["all_axes"]["gold"][:axes_count // 4]),
            decimal=copy_rows("decimal", plain_count)),
        source_course_manifest_sha256=entry.file_sha(source), sources=sources(),
        deterministic_match=deterministic_match)
    path = root / "bundle.json"
    entry.publish(path, bundle)
    return path, entry.file_sha(path)


def shape():
    return patch.multiple(entry, STEPS=STEPS, BOUNDARY=BOUNDARY, EVAL_EVERY=EVAL_EVERY)


def worker(path, sha256, _resume, record, cutoff):
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("one assigned CUDA device is required")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        spec = json.loads(entry.manifest_bytes(path, sha256))
        if spec["sources"] != sources():
            raise ValueError("the sealed source differs at launch")
        matched = spec["deterministic_match"]
        order = ORDER
        tag_mode = "sustained"
        if matched:
            torch.use_deterministic_algorithms(True)
            torch.backends.cuda.matmul.allow_tf32 = False
            order = ORDER[:2]
            tag_mode = "sustained_det"
        entry.publish(record / "input.json", spec)
        native_args, evaluate = entry.native_args, trainer.evaluate
        reports = {}
        with (shape(), patch.object(entry, "native_args", side_effect=lambda pool, resume:
                                    native_args(pool, resume) + ["--anneal-start", "0"]),
              patch.object(trainer, "evaluate", side_effect=lambda model, loader, _, device, **kwargs:
                           evaluate(model, loader, EVAL_BATCHES, device, **kwargs))):
            bundle = entry.load_bundle(path, sha256)
            receipt = bundle.receipt()
            for label, reuse in order:
                if datetime.now().timestamp() >= cutoff:
                    raise TimeoutError("resource comparison exceeded its approved window")
                tag = f"p109c_{tag_mode}_20261121_{label}_chat32_s1337"
                start = perf_counter()
                with (TemporaryDirectory(prefix=f"p109c_ste_sustained_{label}_") as directory,
                      patch.object(entry, "TAG", tag)):
                    arm = diagnostic.arm(bundle, Path(directory), reuse=reuse)
                    native_log, = (Path(directory) / "logs").glob(f"*_{tag}.json")
                    copyfile(native_log, record / f"{label}_native_log.json")
                arm.update(wall_seconds=perf_counter() - start, tag=tag, reuse=reuse)
                entry.publish(record / f"{label}.json", arm)
                reports[label] = arm
        if spec["sources"] != sources():
            raise ValueError("the sealed source changed during comparison")
        entry.publish(record / "report.json", dict(
            arms=reports, order=list(reports), bundle=receipt,
            steps=STEPS, raw_steps=BOUNDARY, eval_every=EVAL_EVERY, eval_batches=EVAL_BATCHES,
            input_slots_per_arm=STEPS * entry.MICRO * entry.ACCUM * entry.WIDTH,
            synthetic_raw=True, authored_course=True, deterministic_algorithms=torch.are_deterministic_algorithms_enabled()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--record", type=Path)
    parser.add_argument("--deterministic-match", action="store_true")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="p109c_ste_sustained_input_") as directory:
        path, checksum = build_bundle(Path(directory), args.deterministic_match)
        if args.mode == "check":
            with shape():
                print(json.dumps(entry.load_bundle(path, checksum).receipt(), ensure_ascii=False))
            return 0
        study = STUDY if not args.deterministic_match else "p109c_ste_sustained_deterministic_v1_20261121"
        if args.record is None or args.record.resolve() != ROOT / "test_result/evidence" / study:
            parser.error("run requires the fresh evidence path for this comparison")
        now = datetime.now().astimezone()
        stop_by = min(AUTHORIZED_END, now + timedelta(minutes=15))
        if stop_by - now < timedelta(minutes=6 if args.deterministic_match else 10):
            raise ValueError("the authorized window is too short for the planned arms")
        with patch.object(entry, "gpu_worker", worker):
            return entry.supervise(path, checksum, False, args.record.resolve(), stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
