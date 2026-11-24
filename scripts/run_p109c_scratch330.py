"""Check or run P109C on an explicitly admitted, sealed cache and course bundle."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

from scripts.run_p109b_scratch_pair_20261120 import file_sha, gpu_status, idle_gpu, publish


TAG = "p109c_scratch330_v1_chat32_s1337"
RELEASE = "20261120_정제데이터셋v1.1"
SCHEMA = "P109C_PRESET_V1_INPUT"
STEPS, BOUNDARY, MICRO, ACCUM, WIDTH = 2518, 2060, 4, 32, 1024
EVAL_EVERY = 515
VOCAB = 32768
CARD_LIMIT_MIB = 12390
PRESET = "m100s12_g4"
CACHE_FILES = ("meta.json", "train.bin", "val.bin")


def file_stamp(path):
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def bundle_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("all inputs must be inside the admitted bundle")
    path = root / relative
    if path.resolve(strict=True) != path:
        raise ValueError(f"the admitted input may not be linked: {path}")
    return path


def digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ValueError("a SHA-256 digest is required")
    return value.upper()


def manifest_bytes(path, sha256):
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError("an unlinked admission manifest file is required")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != digest(sha256):
        raise ValueError("manifest differs from the admitted SHA-256")
    return raw


@dataclass
class Bundle:
    manifest_sha256: str
    meta: dict
    cache_identity: dict
    stamps: dict
    plain: object
    all_axes: object
    decimal: object

    def unchanged(self):
        if any(path.resolve(strict=True) != path or file_stamp(path) != expected
               for path, expected in self.stamps.items()):
            raise ValueError("a sealed P109C input changed")

    def prepare(self, name, count, *, exact, doc_filter, doc_min_chars, hf_tok, chat32, existing_only=False):
        if (name != "ko-en" or count != self.meta["tokens"] or not exact or not chat32
                or doc_filter or hf_tok):
            raise ValueError("P109C accepts the admitted exact ko-en chat32 cache only")
        self.unchanged()
        return dict(self.meta)

    def receipt(self):
        total = STEPS * MICRO * ACCUM * WIDTH
        course = (len(self.plain.rows) + len(self.all_axes.layout.rows)) * WIDTH
        return dict(manifest_sha256=self.manifest_sha256, cache=self.cache_identity,
                    tokenizer_sha256=self.meta["tokenizer_sha256"], train_pool=self.meta["train"],
                    updates=STEPS, mixed_from_update=BOUNDARY, input_slots=total,
                    ordinary_slots=total - course, course_slots=course,
                    decimal_rows=len(self.decimal.by_row),
                    plain=self.plain.binding(), all_axes=self.all_axes.binding(), decimal=self.decimal.binding())


def load_bundle(path, sha256):
    from scripts.p109_mix_masked_course import AllAxesCourse, Course, DecimalLabels, MappedRows
    from tinylm.data.prepare import verify_chat_tokenizer
    from tinylm.train.context_training_state import cache_identity
    from tokenizers import Tokenizer

    stamps = {path: file_stamp(path)}
    manifest = json.loads(manifest_bytes(path, sha256))
    admission = manifest["admission"]
    if (manifest["schema"] != SCHEMA or manifest["source_release"] != RELEASE
            or any(not isinstance(admission[scope], str) or not admission[scope].strip()
                   for scope in ("raw", "course"))):
        raise ValueError("exact v1.1 cache and train-only curriculum admission records are required")

    def pin(item):
        pinned = bundle_path(path.parent, item["file"])
        stamps[pinned] = file_stamp(pinned)
        expected = digest(item["sha256"])
        if not pinned.is_file() or file_sha(pinned).upper() != expected:
            raise ValueError(f"sealed input digest differs: {pinned.name}")
        return pinned, expected

    spec = manifest["cache"]
    cache = bundle_path(path.parent, spec["directory"])
    if not cache.is_dir() or not cache.name.endswith("_chat32"):
        raise ValueError("the cache directory must be the admitted *_chat32 directory")
    for name in CACHE_FILES:
        target = bundle_path(cache, name)
        stamps[target] = file_stamp(target)
    actual = cache_identity(cache)
    if any(actual["files"][name]["sha256"] != digest(spec["sha256"][name]) for name in CACHE_FILES):
        raise ValueError("sealed cache bytes differ")
    meta = json.loads((cache / "meta.json").read_bytes())
    tokenizer_file, token_sha = pin(manifest["tokenizer"])
    course = manifest["course"]
    if (meta["data"] != "ko-en" or meta["vocab"] != VOCAB or meta["token_dtype"] != "uint16"
            or meta["tokenizer_lineage"] != "chat32" or meta["tokenizer_sha256"] != token_sha
            or digest(course["tokenizer_sha256"]) != token_sha
            or (type(meta["train"]), type(meta["val"]), type(meta["tokens"])) != (int, int, int)
            or meta["train"] < 2 * STEPS * MICRO * ACCUM * WIDTH or meta["val"] <= WIDTH + 1
            or meta["tokens"] != meta["train"] + meta["val"]
            or any(actual["files"][split + ".bin"]["bytes"] != 2 * meta[split] for split in ("train", "val"))):
        raise ValueError("P109C needs one tokenizer identity and a full-sized exact train/val cache")
    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    end_id = verify_chat_tokenizer(tokenizer, VOCAB)["<|im_end|>"]

    def layout(item):
        file, expected = pin(item)
        rows = MappedRows(file, expected)
        slots = tuple(item["slots"])
        if rows.width != WIDTH or len(rows) != (STEPS - BOUNDARY) * len(slots) * MICRO:
            raise ValueError("the ordered rows must cover each declared microbatch exactly once")
        return Course(BOUNDARY, slots, rows, VOCAB)

    plain = layout(course["plain"])
    relation = layout(course["all_axes"])
    slots = plain.micro_slots + relation.micro_slots
    if len(set(slots)) != len(slots) or len(slots) >= ACCUM or max(slots) >= ACCUM:
        raise ValueError("disjoint course slots and at least one ordinary slot are required")
    all_axes = AllAxesCourse(relation, end_id, tuple(course["all_axes"]["gold"]))
    labels_file, labels_sha = pin(course["decimal"])
    decimal = DecimalLabels.load(labels_file, labels_sha, plain, tokenizer, end_id)
    bundle = Bundle(digest(sha256), dict(meta, dir=str(cache)), actual, stamps, plain, all_axes, decimal)
    bundle.unchanged()
    return bundle


def native_args(pool, resume):
    # Match the CLI's decimal token convention without rounding an integer pool size.
    from tinylm.cli import _tok

    whole, fraction = divmod(pool, 1_000_000)
    count = f"{whole}.{fraction:06d}M"
    if _tok(count) != pool:
        count = f"{whole + (fraction + 0.5) / 1_000_000:.7f}M"
    if _tok(count) != pool:
        raise ValueError("the pool size cannot be represented exactly by the native CLI")
    args = ["train", "--preset", PRESET, "--arch", "tied", "--data", "ko-en", "--tokens", "330M",
            "--pool-tokens", count, "--chat32-tokenizer", "--exact-cache", "--seed", "1337",
            "--steps", str(STEPS), "--micro-bs", str(MICRO), "--accum", str(ACCUM), "--seq", str(WIDTH),
            "--context-curriculum", f"{STEPS}:{WIDTH}", "--optimizer", "muon", "--muon-scale", "rms",
            "--muon-lr-mult", "4", "--lr", "1e-3", "--sched", "wsd", "--anneal-end", "0.60",
            "--decay-frac", "0.2", "--train-repeat", "2", "--ce-recompute-rows", "1024", "--no-ckpt",
            "--eval-every", str(EVAL_EVERY), "--save-every", str(EVAL_EVERY), "--tag", TAG]
    if resume:
        args.append("--resume")
    return args


def train_bundle(bundle, resume, *, reuse_quantization=False):
    from scripts import p109_mix_masked_course as mixed
    from tinylm.train import context_training_state, trainer

    bind_native = context_training_state.make_binding

    def bind_bundle(plan, recipe, cache, device):
        bundle.unchanged()
        if cache != bundle.cache_identity:
            raise ValueError("native cache identity differs from the admitted bundle")
        return bind_native(plan, dict(recipe, p109c_input_manifest=bundle.manifest_sha256,
                                     p109c_launch_sha256=file_sha(Path(__file__)).upper()), cache, device)

    commands = native_args(bundle.meta["tokens"], resume)
    with (patch.object(trainer, "prepare", bundle.prepare),
          patch.object(context_training_state, "make_binding", bind_bundle)):
        receipt = mixed.run_native(bundle.plain, commands, all_axes=bundle.all_axes,
                                   mixed_ce_recompute_rows=2048, exact_course_rows=True, decimal=bundle.decimal,
                                   reuse_quantization=reuse_quantization)
    bundle.unchanged()
    updates = receipt["updates"]
    if any(not row["optimizer_applied"] for row in updates):
        raise RuntimeError("P109C reached its final step with skipped optimizer updates")
    if not resume and (len(updates) != STEPS or sum(row["decimal_events"] for row in updates[BOUNDARY:])
                      != len(bundle.decimal.by_row)):
        raise RuntimeError("P109C update or decimal counts do not match the admitted schedule")
    return receipt


def gpu_worker(path, sha256, resume, record, cutoff, *, reuse_quantization=False):
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        try:
            gpu_train(path, sha256, resume, record, cutoff, reuse_quantization=reuse_quantization)
        except BaseException:
            traceback.print_exc()
            raise


def gpu_train(path, sha256, resume, record, cutoff, *, reuse_quantization=False):
    import torch
    from tinylm.train import trainer

    bundle = load_bundle(path, sha256)
    publish(record / "input.json", dict(bundle.receipt(), ste_per_micro=reuse_quantization))
    if time.time() >= cutoff or not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("one assigned CUDA device and time before the cutoff are required")
    receipt = train_bundle(bundle, resume, reuse_quantization=reuse_quantization)
    checkpoint = trainer.CKPT / f"{PRESET}_ko-en_330M_{TAG}.pt"
    output = record / "evaluation.pt"
    export_for_evaluation(checkpoint, output)
    receipt.update(peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                   peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                   evaluation_sha256=file_sha(output).upper())
    publish(record / "training.json", receipt)


def export_for_evaluation(checkpoint, output):
    import torch
    from tinylm.train import trainer
    from tinylm.train.packed_document_training import save_packed_checkpoint

    state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
    head = {key for key in state["model"] if key.startswith("decimal_head.")}
    export = {key: state[key] for key in ("step", "cfg", "tokenizer_sha256")}
    export["model"] = {key: value for key, value in state["model"].items() if key not in head}
    cursor = state[trainer.CONTEXT_STATE_KEY]["cursor"]["cursor"]
    if (state["step"] != STEPS or cursor["optimizer_updates"] != STEPS
            or head != {"decimal_head.weight", "decimal_head.bias"}):
        raise RuntimeError("the completed training state lacks the expected updates or auxiliary head")
    save_packed_checkpoint(output, export)


def observe_card_return():
    try:
        total, used, utilization = gpu_status()
        processes = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            text=True, timeout=3,
        )
        pids = [int(row) for row in processes.splitlines() if row.strip()]
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return dict(sampled_at=time.time(), error=repr(error))
    return dict(sampled_at=time.time(), free_mib=total - used, utilization=utilization, compute_pids=pids)


def supervise(path, sha256, resume, record, stop_by, *, reuse_quantization=False):
    from tinylm import paths

    cutoff = stop_by.timestamp() - 35
    if stop_by.tzinfo is None or cutoff <= time.time():
        raise ValueError("run needs a future authorized deadline with an explicit UTC offset")
    manifest_bytes(path, sha256)
    paths.RUNS.mkdir(parents=True, exist_ok=True)
    lock = os.open(paths.RUNS, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        idle_gpu()
        record.mkdir(exist_ok=False)
        options = {"reuse_quantization": True} if reuse_quantization else {}
        child = multiprocessing.get_context("spawn").Process(target=gpu_worker,
                                     args=(path, sha256, resume, record, cutoff), kwargs=options)
        started = time.time()
        peak = 0
        reason = None

        def interrupted(value, frame):
            raise KeyboardInterrupt(signal.Signals(value).name)

        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            child.start()
            with (record / "gpu.csv").open("x", encoding="utf-8", buffering=1) as telemetry:
                telemetry.write("unix_seconds,pid,card_used_mib,gpu_util_percent\n")
                while child.is_alive():
                    instant = time.time()
                    if instant >= cutoff:
                        reason = "AUTHORIZED_CUTOFF"
                        break
                    _, used, utilization = gpu_status()
                    peak = max(peak, used)
                    telemetry.write(f"{instant:.3f},{child.pid},{used},{utilization}\n")
                    if used > CARD_LIMIT_MIB:
                        reason = "CARD_MEMORY_LIMIT"
                        break
                    child.join(timeout=2)
        except BaseException as error:
            reason = repr(error)
            raise
        finally:
            try:
                if child.pid is not None:
                    if child.is_alive():
                        child.terminate()
                        child.join(timeout=8)
                        if child.is_alive():
                            child.kill()
                    child.join()
                ended = time.time()
                returned = observe_card_return() if child.pid is not None else None
                publish(record / "supervisor.json", dict(pid=child.pid, started=started, ended=ended,
                            returncode=child.exitcode, peak_card_mib=peak, stop_reason=reason,
                            card_after_exit=returned))
            finally:
                signal.signal(signal.SIGTERM, previous)
    finally:
        os.close(lock)
    return 0 if child.exitcode == 0 and reason is None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--ste-per-micro", action="store_true", help="use the P109C per-micro STE candidate")
    args = parser.parse_args()
    path = args.manifest.absolute()
    if args.mode == "check":
        bundle = load_bundle(path, args.manifest_sha256)
        print(json.dumps(dict(bundle.receipt(), ste_per_micro=args.ste_per_micro), indent=2))
        return 0
    if args.record is None or args.stop_by is None:
        parser.error("run requires --record and --stop-by")
    return supervise(path, args.manifest_sha256, args.resume, args.record.absolute(), args.stop_by,
                     reuse_quantization=args.ste_per_micro)


if __name__ == "__main__":
    sys.exit(main())
