"""Focused CPU regressions for recomputed CE and its native resume contract."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
from tempfile import mkdtemp
import unittest
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F

from tinylm import cli
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train import trainer
from tinylm.train.recomputed_ce import target_nll


def tiny_config():
    return TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                     emb_rank=8, n_prelude=1, n_middle=4, n_coda=1, tie_mlp=True,
                     mlp_group=2, micro_group=8, max_seq_len=16)


class RecomputedCE(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_available():
            raise RuntimeError("run these tests with CUDA_VISIBLE_DEVICES empty")

    def test_masked_nll_and_tied_gradients(self):
        torch.manual_seed(31)
        model = TiedMLPTransformer(tiny_config())
        y = torch.tensor([[-100, -100, 5, 8], [4, -100, 1, 20]])
        weight = torch.tensor([[0., 0., 1., -.5], [2., 0., .25, 3.]])
        for amp in (False, True):
            with self.subTest(bf16=amp):
                hidden = torch.randn(2, 4, 32, requires_grad=True)
                with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
                    logits = model._head_logits(hidden).flatten(0, 1)
                    ref = F.nll_loss(F.log_softmax(logits, dim=1, dtype=logits.dtype).float(),
                                     y.flatten(), reduction="none").reshape_as(y)
                    got, valid = target_nll(model, hidden, y, rows=2)
                self.assertTrue(torch.equal(valid, y.ne(-100)))
                self.assertTrue(bool(got[~valid].eq(0).all()))
                torch.testing.assert_close(got, ref)
                params = (hidden, model.emb.weight, model.emb_up.weight)
                lhs = torch.autograd.grad((ref * weight).sum(), params)
                rhs = torch.autograd.grad((got * weight).sum(), params)
                for a, b in zip(lhs, rhs, strict=True):
                    torch.testing.assert_close(a, b)

    def test_all_ignored_preserves_native_mean_and_zero_gradients(self):
        model = TiedMLPTransformer(tiny_config())
        hidden = torch.randn(2, 3, 32, requires_grad=True)
        y = torch.full((2, 3), -100)
        nll, mask = target_nll(model, hidden, y, rows=2)
        ce = nll.sum() / mask.sum()
        plain = F.cross_entropy(model._head_logits(hidden).flatten(0, 1), y.flatten())
        self.assertTrue(bool(ce.isnan() and plain.isnan()))
        operands = (hidden, model.emb.weight, model.emb_up.weight)
        for gradient in torch.autograd.grad(ce, operands):
            self.assertTrue(bool(gradient.eq(0).all()))

    def test_incompatible_options_fail_before_loading_inputs(self):
        common = dict(preset="m100s12_g4", arch="tied", data="synthetic",
                      n_tokens=1536, steps=4, micro_bs=2, seq=16, accum=2,
                      lr=.001, eval_every=1, tag="recomputed_guard")
        conflicts = ({"kd": True}, {"ce_chunk": 4}, {"loss_first": True},
                     {"ce_vocab_tile": 8}, {"compile_": True})
        with patch.object(trainer, "prepare", side_effect=AssertionError("input should not open")):
            for extra in conflicts:
                with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, "--ce-recompute-rows"):
                    trainer.train(**common, ce_recompute_rows=4, **extra)
            with self.assertRaisesRegex(ValueError, "nonnegative integer"):
                trainer.train(**common, ce_recompute_rows=-1)
        with (patch.object(sys, "argv", ["tinylm", "eval", "--ce-recompute-rows", "4"]),
              redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result):
            cli.main()
        self.assertEqual(result.exception.code, 2)

    def test_cli_storage_and_exact_context_resume(self):
        root = Path(mkdtemp(prefix="tinylm-recompute-ce-", dir="/tmp"))
        cache = root / "cache"
        cache.mkdir()
        rng = np.random.default_rng(32)
        meta = dict(data="synthetic", dir=str(cache), tokens=1536, vocab=35,
                    token_dtype="uint16", train=1024, val=512)
        (cache / "meta.json").write_text(json.dumps(meta))
        for split in ("train", "val"):
            rng.integers(0, 35, meta[split], dtype=np.uint16).tofile(cache / f"{split}.bin")
        ckpt, logs = root / "ckpt", root / "logs"
        prefix = "m100s12_g4_synthetic_1536"
        original_save, original_evaluate = torch.save, trainer.evaluate

        def run(tag, rows=None, resume=False):
            argv = ["tinylm", "train", "--preset", "m100s12_g4", "--arch", "tied", "--data", "synthetic",
                    "--tokens", "0.001536M", "--pool-tokens", "0.001536M", "--exact-cache",
                    "--steps", "4", "--seq", "16", "--micro-bs", "2", "--accum", "2",
                    "--eval-every", "1", "--save-every", "1", "--context-curriculum", "4:16",
                    "--sched", "wsd", "--anneal-start", "0", "--tag", tag]
            if rows is not None:
                argv += ["--ce-recompute-rows", str(rows)]
            if resume:
                argv.append("--resume")
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                cli.main()

        def evaluate(model, loader, _count, device, **kwargs):
            return original_evaluate(model, loader, 2, device, **kwargs)

        def checkpoint(tag):
            return ckpt / f"{prefix}_{tag}.pt"

        class Boundary(Exception):
            pass

        def save_at_boundary(blob, path):
            original_save(blob, path)
            if path == checkpoint("split") and blob["step"] == 2:
                raise Boundary

        with (patch.object(trainer, "CKPT", ckpt), patch.object(trainer, "LOGS", logs),
              patch.object(trainer, "prepare", return_value=meta),
              patch.object(trainer, "build_config", side_effect=lambda *args, **kwargs: tiny_config()),
              patch.object(trainer, "evaluate", evaluate)):
            run("default")
            plain = torch.load(checkpoint("default"), weights_only=True)
            self.assertNotIn("ce_recompute_rows", plain)
            default_run = json.loads((logs / f"{prefix}_default.json").read_text())
            self.assertNotIn("ce_recompute_rows", default_run)

            run("continuous", 4)
            with patch.object(torch, "save", save_at_boundary), self.assertRaises(Boundary):
                run("split", 4)
            mid = torch.load(checkpoint("split"), weights_only=True)
            self.assertEqual((mid["step"], mid["ce_recompute_rows"]), (2, 4))
            source_pins = mid[trainer.CONTEXT_STATE_KEY]["binding"]["sources"]
            self.assertIn("recomputed_ce.py", source_pins)
            for stem, rows in (("split", None), ("split", 8), ("default", 4)):
                with self.assertRaisesRegex(ValueError, "checkpoint recompute rows"):
                    run(stem, rows, resume=True)
            with self.assertRaises(FileExistsError):
                run("split", 4)
            run("split", 4, resume=True)

        full = torch.load(checkpoint("continuous"), weights_only=True)
        resumed = torch.load(checkpoint("split"), weights_only=True)
        self.assertEqual((full["step"], resumed["step"]), (4, 4))
        torch.testing.assert_close(full["model"], resumed["model"], rtol=0, atol=0)
        for key in ("opt", "opt_muon"):
            self.assertEqual(full[key]["param_groups"], resumed[key]["param_groups"])
            torch.testing.assert_close(full[key]["state"], resumed[key]["state"], rtol=0, atol=0)
        joined = json.loads((logs / f"{prefix}_split.json").read_text())
        self.assertEqual((joined["ce_recompute_rows"], joined["context_resume_start_step"]), (4, 2))
        self.assertFalse(torch.cuda.is_initialized())
        print("Recomputed CE CPU checkpoints:", root)


if __name__ == "__main__":
    unittest.main()
