"""CPU synthetic observation fixtures; no checkpoint/tokenizer/cache/GPU loads."""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock
import unittest
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p093b_live_trace as trace
from tinylm.infer.generate import sample


class TokenizerFixture:
    def encode(self, _):
        return SimpleNamespace(ids=[1, 3])

    def token_to_id(self, _):
        return 4

    def decode(self, ids):
        return " ".join(str(int(x)) for x in ids)


class LayerFixture(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln2 = nn.Identity()
        self.mlp = [nn.Identity()]

    def forward(self, x):
        after = x + .1
        return self.mlp[0](self.ln2(after)) + .2


class ModelFixture(nn.Module):
    def __init__(self, corrupt_shadow=False):
        super().__init__()
        self.emb = nn.Embedding(6, 4)
        self.layers = nn.ModuleList([LayerFixture(), LayerFixture()])
        self.cfg = SimpleNamespace(max_seq_len=32)
        self.owner = [0, 1]
        self.corrupt_shadow = corrupt_shadow

    def forward(self, tokens, past_kv=None, use_cache=False, logits_last_only=False):
        x = self.emb(tokens)
        for layer in self.layers:
            x = layer(x)
        logits = x.new_zeros(1, tokens.shape[1], 6)
        logits[:, :, 2] = 10.
        if self.corrupt_shadow and not use_cache:
            logits[:, :, 3] = 20.
        if logits_last_only:
            logits = logits[:, -1:]
        if not use_cache:
            return logits
        kv = {}
        for owner in self.owner:
            k = x[:, None].clone()
            v = (x[:, None] + .5).clone()
            if past_kv:
                old_k, old_v = past_kv[owner]
                k, v = torch.cat([old_k, k], 2), torch.cat([old_v, v], 2)
            kv[owner] = k, v
        return logits, kv


class LiveTraceTests(unittest.TestCase):
    def test_exact_periodic_onset_is_not_confirmation_time(self):
        event = trace.loop_candidate([1, 2, 1, 2, 1, 2])
        self.assertEqual(event["period"], 2)
        self.assertEqual(event["first_block_token"], 1)
        self.assertEqual(event["onset_token"], 3)
        self.assertEqual(event["confirmed_at_token"], 6)
        self.assertIn("legitimate", event["decision"])

    def test_two_blocks_do_not_claim_confirmed_loop(self):
        self.assertIsNone(trace.loop_candidate([1, 2, 1, 2]))

    def test_single_token_onset_and_empty_input(self):
        self.assertIsNone(trace.loop_candidate([]))
        self.assertEqual(trace.loop_candidate([3, 3, 3])["onset_token"], 2)

    def test_logits_mass_uses_unique_ids_and_eos_is_separate(self):
        r = trace.logits_stats(torch.tensor([0., 1., 4., -1., 2.]), [2, 2], [1, 2], 4, str)
        p = torch.softmax(torch.tensor([0., 1., 4., -1., 2.]), 0)
        self.assertEqual(r["argmax_id"], 2)
        self.assertAlmostEqual(r["mass_on_prior_generated_token_types"], float(p[2]))
        self.assertAlmostEqual(r["eos_probability"], float(p[4]))
        self.assertIn("entropy_nats", r)

    def test_nonfinite_logits_fail_closed(self):
        with self.assertRaises(ValueError):
            trace.logits_stats(torch.tensor([float("nan"), 1.]), [], [], -1, str)

    def test_pair_change_zero_vectors_are_explicit(self):
        r = trace.pair_change(torch.zeros(4), torch.zeros(4))
        self.assertIsNone(r["cosine"])
        self.assertEqual(r["rms"], 0.)

    def test_kv_append_and_prefix_corruption_are_distinguished(self):
        old = torch.randn(1, 1, 2, 4)
        nxt = torch.cat([old, torch.ones(1, 1, 1, 4)], 2)
        r = trace.kv_stats({0: (nxt, nxt)}, {0: (old.clone(), old.clone())}, 3)
        self.assertTrue(r["all_previous_prefixes_unchanged"])
        self.assertIsNotNone(r["owners"][0]["last_vs_previous_token"]["k"]["cosine"])
        broken = nxt.clone()
        broken[:, :, 0] += 1.
        r = trace.kv_stats({0: (broken, nxt)}, {0: (old.clone(), old.clone())}, 3)
        self.assertFalse(r["all_previous_prefixes_unchanged"])
        self.assertGreater(r["owners"][0]["prefix_difference"]["k"]["max_abs"], 0)

    def test_kv_wrong_length_is_error_not_empty_pass(self):
        with self.assertRaises(ValueError):
            trace.kv_stats({0: (torch.ones(1, 1, 2, 4), torch.ones(1, 1, 2, 4))}, {}, 3)

    def test_native_output_ids_weights_and_hooks_are_preserved(self):
        torch.manual_seed(1)
        model = ModelFixture().eval()
        tok = TokenizerFixture()
        before = {k: v.clone() for k, v in model.state_dict().items()}
        plain, expected = sample(model, model.cfg, tok, "fixture", max_new=6, temperature=0,
            top_k=1, device="cpu", logits_last_only=True, return_metadata=True)
        emitted = []
        with trace.LiveObserver(model, tok, [1, 3], subject="fixture", ident="fixture",
                               emit=emitted.append, max_new=6) as observer:
            actual, meta = sample(model, model.cfg, tok, "fixture", max_new=6, temperature=0,
                top_k=1, device="cpu", logits_last_only=True, return_metadata=True)
        self.assertEqual(actual, plain)
        self.assertEqual(meta, expected)
        self.assertEqual(observer.generated, [2] * 6)
        self.assertEqual(len(emitted), 6)
        self.assertEqual(emitted[0]["prefix_token_count"], 2)
        self.assertEqual(emitted[-1]["prefix_token_count"], 7)
        self.assertTrue(all(r["same_prefix_cache_comparison"]["argmax_match"] for r in emitted))
        self.assertTrue(all(r["kv"]["all_previous_prefixes_unchanged"] for r in emitted))
        self.assertEqual(len(emitted[0]["layers"]), 2)
        self.assertTrue(all(torch.equal(before[k], v) for k, v in model.state_dict().items()))
        self.assertEqual(len(model._forward_hooks), 0)
        self.assertEqual(len(model._forward_pre_hooks), 0)
        self.assertTrue(all(not layer._forward_hooks and not layer.ln2._forward_pre_hooks for layer in model.layers))

    def test_shadow_mismatch_does_not_change_actual_native_selection(self):
        model = ModelFixture(corrupt_shadow=True).eval()
        tok = TokenizerFixture()
        with trace.LiveObserver(model, tok, [1, 3], subject="fixture", ident="fixture",
                               emit=lambda _: None, max_new=3) as observer:
            _, meta = sample(model, model.cfg, tok, "fixture", max_new=3, temperature=0,
                top_k=1, device="cpu", logits_last_only=True, return_metadata=True)
        self.assertEqual(observer.generated, [2] * 3)
        self.assertEqual(meta["generated_tokens"], 3)
        self.assertFalse(observer.rows[0]["same_prefix_cache_comparison"]["argmax_match"])

    def test_hook_cleanup_when_emit_fails(self):
        model = ModelFixture().eval()
        tok = TokenizerFixture()
        with self.assertRaises(RuntimeError):
            with trace.LiveObserver(model, tok, [1, 3], subject="fixture", ident="fixture",
                emit=lambda _: (_ for _ in ()).throw(RuntimeError("fixture")), max_new=3):
                sample(model, model.cfg, tok, "fixture", max_new=3, temperature=0,
                       top_k=1, device="cpu", logits_last_only=True)
        self.assertFalse(model._forward_hooks)
        self.assertFalse(model._forward_pre_hooks)
        self.assertTrue(all(not layer._forward_hooks for layer in model.layers))

    def test_checkonly_does_not_open_real_source_or_model(self):
        from scripts import diag_p093b_live_trace as driver
        with mock.patch.object(driver.saved, "source", side_effect=AssertionError("source IO")), \
             mock.patch.object(driver, "execute", side_effect=AssertionError("model")), \
             mock.patch("sys.argv", ["fixture", "--mode", "trace", "--check-only"]), \
             mock.patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(driver.main(), 0)

    def test_factor_pin_is_bound_to_frozen_source_not_only_local_manifest(self):
        from scripts import diag_p093b_live_trace as driver
        with TemporaryDirectory(prefix="p093b-live-pin-") as temp:
            root = Path(temp)
            files = []
            import hashlib
            for stem in ("gate_proj", "up_proj", "down_proj"):
                p = root / ("rank64_" + stem + ".pt")
                p.write_bytes(b"synthetic non-model fixture")
                files.append({"path": p.name, "bytes": p.stat().st_size,
                              "sha256": hashlib.sha256(p.read_bytes()).hexdigest().upper()})
            manifest = {"input": {}, "files": files}
            (root / "rank64_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            source = {"ranks": [{"rank": 64, "artifact": manifest}]}
            with mock.patch.object(driver.saved, "BASE", root), mock.patch.object(driver, "ROOT", root):
                self.assertEqual(len(driver.verify_factor_pin(source)["files"]), 3)
                mutated = {"input": {}, "files": files[:2]}
                (root / "rank64_manifest.json").write_text(json.dumps(mutated), encoding="utf-8")
                with self.assertRaises(ValueError):
                    driver.verify_factor_pin(source)

    def test_readback_requires_same_code_and_nonempty_complete_real_manifest(self):
        from scripts import diag_p093b_live_trace as driver
        from scripts.p106b_shards import ShardWriter
        with TemporaryDirectory(prefix="p093b-live-readback-") as temp:
            root = Path(temp)
            trace_writer = ShardWriter(root, "token_trace")
            answer_writer = ShardWriter(root, "actual_answers")
            for i in range(24):
                trace_writer.append({"fixture": i})
                answer_writer.append({"fixture": i})
            source = {"status": "LIVE_TRACE_COMPLETE", "completed_native_sequences": 24,
                "input": {"code_sha256": {"fixture": "a"}}, "primary_token_steps": 24,
                "trace_manifest": trace_writer.close(lineage={}),
                "answer_manifest": answer_writer.close(lineage={}),
                "all_previous_KV_prefixes_unchanged": True, "old_text_finish_count_matched": 24,
                "same_prefix_cache_argmax_matched": 24}
            self.assertTrue(driver.verify_live_readback(root, source, {"fixture": "a"})["technical_gate_passed"])
            with self.assertRaises(ValueError):
                driver.verify_live_readback(root, source, {"fixture": "b"})
            with (root / "token_trace_000000.jsonl").open("ab") as stream:
                stream.write(b"tampered fixture\n")
            with self.assertRaises(ValueError):
                driver.verify_live_readback(root, source, {"fixture": "a"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
