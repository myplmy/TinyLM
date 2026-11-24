"""Regression for sealed chat32 inputs, an auxiliary head, and native file resume."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta
import importlib
import io
import json
import os
from pathlib import Path
import signal
import sys
from tempfile import TemporaryDirectory
from threading import Event, Thread
import time
import unittest
from unittest.mock import patch

import numpy as np
import torch
from tokenizers import Tokenizer, models

from scripts import run_p109c_scratch330 as entry
from scripts.diag_p109_ntp_visit_resume import SplitBoundary, state_fingerprint
from scripts.p109_mix_masked_course import DecimalG4
from tinylm import paths
from tinylm.chat.tokens import SLOT_NAMES
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train import packed_document_training as packed, trainer


STEPS, BOUNDARY, MICRO, ACCUM, WIDTH, VOCAB = 4, 2, 4, 6, 16, 64


def seal(path):
    return entry.file_sha(path).upper()


def make_bundle(root):
    specials = ("<pad>", "<bos>", "<eos>", *SLOT_NAMES)
    words = (*specials, "5", "2+3", *(f"w{index}" for index in range(VOCAB - len(specials) - 2)))
    tokenizer = Tokenizer(models.WordLevel(vocab={word: index for index, word in enumerate(words)}, unk_token="w0"))
    tokenizer.add_special_tokens(list(specials))
    token_path = root / "tokenizer.json"
    tokenizer.save(str(token_path))
    tok_sha = seal(token_path)
    end = tokenizer.token_to_id("<|im_end|>")

    cache = root / "fixture_chat32"
    cache.mkdir()
    rng = np.random.default_rng(104)
    train_count = 2 * STEPS * MICRO * ACCUM * WIDTH
    val_count = max(256, 4 * WIDTH)
    for split, count in (("train", train_count), ("val", val_count)):
        rng.integers(4, VOCAB, size=count, dtype=np.uint16).tofile(cache / f"{split}.bin")
    (cache / "meta.json").write_text(json.dumps(dict(data="ko-en", vocab=VOCAB, token_dtype="uint16",
        tokenizer_lineage="chat32", tokenizer_sha256=tok_sha, train=train_count, val=val_count,
        tokens=train_count + val_count)), encoding="utf-8")

    def row(question, answer):
        x = [question, *([48] * 4), answer, end, *([0] * (WIDTH - 7))]
        y = [-100] * WIDTH
        y[4:6] = [answer, end]
        return x, y

    def write_array(name, values):
        file = root / name
        np.save(file, np.array(values, dtype="<i4"), allow_pickle=False)
        return dict(file=name, sha256=seal(file))

    plain = write_array("plain.npy", [row(tokenizer.token_to_id("2+3"), tokenizer.token_to_id("5"))
                                    for _ in range((STEPS - BOUNDARY) * MICRO)])
    plain["slots"] = [1]
    relation = write_array("relation.npy", [row(50 + question, 54 + answer)
                       for _ in range(STEPS - BOUNDARY) for question in range(4) for answer in range(4)])
    relation.update(slots=[2, 3, 4, 5], gold=[0, 1, 2, 3] * (STEPS - BOUNDARY))
    decimal = write_array("decimal.npy", [(4, 2, 3)] * ((STEPS - BOUNDARY) * MICRO))
    return dict(schema=entry.SCHEMA, source_release=entry.RELEASE,
                admission=dict(raw="SYNTHETIC_FIXTURE_ONLY", course="SYNTHETIC_FIXTURE_ONLY"),
                cache=dict(directory=cache.name, sha256={name: seal(cache / name) for name in entry.CACHE_FILES}),
                tokenizer=dict(file=token_path.name, sha256=tok_sha),
                course=dict(tokenizer_sha256=tok_sha, plain=plain, all_axes=relation, decimal=decimal))


def small_model(_preset, _arch, seq, ckpt):
    return TMTConfig(vocab_size=VOCAB, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=seq,
                     n_q_heads=4, n_kv_heads=2, n_prelude=2, n_middle=12, n_coda=2,
                     tie_mlp=True, mlp_group=4, cla_group=2, micro_group=8, grad_checkpoint=ckpt)


def write_manifest(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return seal(path)


def idle_test_worker(_path, _sha256, _resume, _record, _cutoff):
    time.sleep(30)


def cuda_shape(out):
    """One full-size raw update and one mixed update, using authored fixtures."""
    if datetime.now().astimezone() >= datetime.fromisoformat("2026-11-21T12:56:00+09:00"):
        raise RuntimeError("the WIP 191 GPU window has insufficient time")
    _, baseline = entry.idle_gpu()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("one CUDA device is required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    out.mkdir(exist_ok=False)
    stop = Event()
    samples = []
    errors = []

    def abort(_signal, _frame):
        raise RuntimeError(errors[0] if errors else "CUDA fixture exceeded 90 seconds")

    def sample_card():
        while not stop.is_set():
            try:
                _, used, util = entry.gpu_status()
                samples.append((time.time(), used, util))
                if used > entry.CARD_LIMIT_MIB:
                    raise RuntimeError("card exceeded the preflight ceiling")
            except Exception as error:
                errors.append(str(error))
                os.kill(os.getpid(), signal.SIGALRM)
                return
            stop.wait(1)

    previous = signal.signal(signal.SIGALRM, abort)
    signal.alarm(90)
    sampler = Thread(target=sample_card, daemon=True)
    sampler.start()
    real_args = entry.native_args
    try:
        with (TemporaryDirectory(prefix="p109c_cuda_") as directory,
              patch.multiple(sys.modules[__name__], STEPS=2, BOUNDARY=1, ACCUM=32, WIDTH=1024, VOCAB=32768),
              patch.multiple(entry, STEPS=2, BOUNDARY=1, EVAL_EVERY=2, TAG="p109c_bundle_cuda2_chat32_s1337"),
              patch.object(entry, "native_args", side_effect=lambda pool, resume:
                           real_args(pool, resume) + ["--anneal-start", "0"])):
            root = Path(directory)
            (root / "cache").mkdir()
            path = root / "cache" / "input.json"
            sha = write_manifest(path, make_bundle(path.parent))
            bundle = entry.load_bundle(path, sha)
            # Normal validation samples from a cache longer than one full context.
            with (patch.object(trainer, "CKPT", root / "ckpt"), patch.object(trainer, "LOGS", out / "logs")):
                start = time.perf_counter()
                receipt = entry.train_bundle(bundle, resume=False)
                elapsed = time.perf_counter() - start
                checkpoint = trainer.CKPT / f"{entry.PRESET}_ko-en_330M_{entry.TAG}.pt"
                entry.export_for_evaluation(checkpoint, root / "evaluation.pt")
                updates = receipt["updates"]
                if ([row["ce_recompute_rows"] for row in updates] != [1024, 2048]
                        or updates[1]["decimal_events"] != 4 or updates[1]["contrast_questions"] != 4):
                    raise AssertionError("the production-sized boundary lost a course operation")
            from scripts import p109_mix_masked_course as mixed

            report = dict(status="CUDA_SHAPE_VERIFIED", synthetic=True, native_seconds=elapsed,
                          baseline_card_mib=baseline, peak_card_mib=max(row[1] for row in samples),
                          max_alloc_mib=torch.cuda.max_memory_allocated() / 2**20,
                          max_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                          sources={str(file): seal(file) for file in (Path(__file__), Path(entry.__file__),
                                   Path(mixed.__file__), Path(trainer.__file__))},
                          main=receipt, evaluation_sha256=seal(root / "evaluation.pt"))
            entry.publish(out / "report.json", report)
    finally:
        stop.set()
        sampler.join(timeout=9)
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        entry.publish(out / "card_samples.json", dict(samples=samples, errors=errors))


class SealedRunTest(unittest.TestCase):
    def test_launcher_dispatches_ste_mode(self):
        args = ["run_p109c_scratch330", "run", "--manifest", "/tmp/manifest.json",
                "--manifest-sha256", "0" * 64, "--record", "/tmp/receipt",
                "--stop-by", "2026-11-21T13:00:00+09:00", "--ste-per-micro"]
        with patch.object(sys, "argv", args), patch.object(entry, "supervise", return_value=0) as launch:
            self.assertEqual(entry.main(), 0)
        self.assertTrue(launch.call_args.kwargs["reuse_quantization"])

    def test_supervisor_stops_its_child_at_card_limit(self):
        with TemporaryDirectory(prefix="p109c_supervisor_") as directory:
            root = Path(directory)
            manifest = root / "input.json"
            sha = write_manifest(manifest, {})
            record = root / "evidence"
            deadline = datetime.now().astimezone() + timedelta(minutes=2)
            with (patch.object(paths, "RUNS", root / "runs"), patch.object(entry, "idle_gpu"),
                  patch.object(entry, "gpu_worker", idle_test_worker),
                  patch.object(entry, "gpu_status", side_effect=[(16376, entry.CARD_LIMIT_MIB + 1, 50), (16376, 1118, 0)]),
                  patch.object(entry.subprocess, "check_output", return_value="")):
                self.assertEqual(entry.supervise(manifest, sha, False, record, deadline), 1)
            result = json.loads((record / "supervisor.json").read_bytes())
            self.assertEqual(result["stop_reason"], "CARD_MEMORY_LIMIT")
            self.assertIsInstance(result["pid"], int)
            self.assertEqual(result["returncode"], -signal.SIGTERM)
            self.assertGreaterEqual(result["card_after_exit"]["sampled_at"], result["ended"])
            self.assertEqual(result["card_after_exit"]["free_mib"], 15258)
            self.assertEqual(result["card_after_exit"]["compute_pids"], [])

    def test_resume_cache_cannot_be_created_or_backfilled(self):
        prepare = importlib.import_module("tinylm.data.prepare")
        verify = prepare.verify_chat_tokenizer
        with TemporaryDirectory(prefix="p109c_prepare_") as directory:
            root = Path(directory) / "cache"
            with patch.object(prepare, "DATA_CACHE", root):
                with self.assertRaises(FileNotFoundError):
                    prepare.prepare("ko-en", 100, exact=True, chat32=True, existing_only=True)
                self.assertFalse(root.exists())
                root.mkdir()
                manifest = make_bundle(root)
                cache = root / manifest["cache"]["directory"]
                meta = json.loads((cache / "meta.json").read_bytes())
                real_cache = root / f"ko-en_{meta['tokens']}_chat32"
                cache.rename(real_cache)
                (root / "tokenizer.json").rename(prepare.chat_tokenizer_path("ko-en"))
                with (patch.object(prepare, "verify_chat_tokenizer", side_effect=lambda tok: verify(tok, VOCAB)),
                      patch.object(prepare, "_ensure_bpt", side_effect=AssertionError("resume tried to backfill"))):
                    result = prepare.prepare("ko-en", meta["tokens"], exact=True, chat32=True, existing_only=True)
                self.assertEqual(result["dir"], str(real_cache))
                self.assertEqual(seal(real_cache / "meta.json"), manifest["cache"]["sha256"]["meta.json"])

    def test_native_resume_uses_identical_course_and_training_state(self):
        self.assertEqual(os.environ.get("CUDA_VISIBLE_DEVICES"), "")
        torch.set_num_threads(1)
        real_evaluate = trainer.evaluate
        real_save = packed.save_packed_checkpoint
        real_args = entry.native_args

        def evaluate(model, loader, _steps, device, **kwargs):
            return real_evaluate(model, loader, 2, device, **kwargs)

        with (TemporaryDirectory(prefix="p109c_bundle_") as directory,
              patch.multiple(entry, STEPS=STEPS, BOUNDARY=BOUNDARY, MICRO=MICRO, ACCUM=ACCUM,
                             WIDTH=WIDTH, VOCAB=VOCAB, EVAL_EVERY=1),
              patch.object(entry, "native_args", side_effect=lambda pool, resume:
                           real_args(pool, resume) + ["--anneal-start", "0"]),
              patch.object(trainer, "build_config", small_model),
              patch.object(trainer, "evaluate", evaluate),
              patch.object(trainer, "prepare", side_effect=AssertionError("fallback prepare was called"))):
            root = Path(directory)
            manifest = make_bundle(root)
            path = root / "input.json"
            sha = write_manifest(path, manifest)
            with self.assertRaisesRegex(ValueError, "admitted SHA-256"):
                entry.load_bundle(path, "0" * 64)
            bundle = entry.load_bundle(path, sha)
            other = root / "other.json"
            manifest["course"]["tokenizer_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "one tokenizer identity"):
                entry.load_bundle(other, write_manifest(other, manifest))
            manifest["course"]["tokenizer_sha256"] = bundle.meta["tokenizer_sha256"]
            manifest["admission"]["course"] = "CHANGED_FIXTURE_ADMISSION"
            changed = entry.load_bundle(other, write_manifest(other, manifest))
            self.assertEqual(bundle.receipt()["course_slots"], 2 * 5 * MICRO * WIDTH)

            def train(side, resume=False, source=bundle):
                with (patch.object(trainer, "CKPT", root / side / "ckpt"),
                      patch.object(trainer, "LOGS", root / side / "logs"), redirect_stdout(io.StringIO())):
                    return entry.train_bundle(source, resume)

            def checkpoint(side):
                return root / side / "ckpt" / f"{entry.PRESET}_ko-en_330M_{entry.TAG}.pt"

            full = train("full")
            boundary_path = checkpoint("split")

            def stop(path, state):
                real_save(path, state)
                if path == boundary_path and state["step"] == BOUNDARY + 1:
                    raise SplitBoundary()

            with patch.object(packed, "save_packed_checkpoint", stop), self.assertRaises(SplitBoundary):
                train("split")
            before = seal(boundary_path)
            with self.assertRaisesRegex(ValueError, "binding differs"):
                train("split", resume=True, source=changed)
            self.assertEqual(before, seal(boundary_path))
            resumed = train("split", resume=True)
            self.assertEqual(resumed["updates"], full["updates"][BOUNDARY + 1:])
            self.assertEqual([row["ce_recompute_rows"] for row in full["updates"]], [1024, 1024, 2048, 2048])
            self.assertEqual([row["decimal_events"] for row in full["updates"][BOUNDARY:]], [4, 4])
            self.assertEqual([row["contrast_questions"] for row in full["updates"][BOUNDARY:]], [4, 4])
            left, right = (torch.load(checkpoint(side), weights_only=True, map_location="cpu") for side in ("full", "split"))
            self.assertEqual(state_fingerprint(left), state_fingerprint(right))
            self.assertTrue(torch.count_nonzero(right["model"]["decimal_head.weight"]))

            export = root / "evaluation.pt"
            entry.export_for_evaluation(checkpoint("split"), export)
            evaluation = torch.load(export, weights_only=True)
            base = TiedMLPTransformer(TMTConfig(**evaluation["cfg"])).eval()
            with_head = DecimalG4(TMTConfig(**right["cfg"])).eval()
            base.load_state_dict(evaluation["model"], strict=True)
            with_head.load_state_dict(right["model"], strict=True)
            inputs = torch.arange(WIDTH).unsqueeze(0)
            with torch.inference_mode():
                self.assertTrue(torch.equal(base(inputs), with_head(inputs)))
            self.assertFalse(torch.cuda.is_initialized())


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cuda-shape":
        cuda_shape(Path(sys.argv[2]))
    else:
        unittest.main()
