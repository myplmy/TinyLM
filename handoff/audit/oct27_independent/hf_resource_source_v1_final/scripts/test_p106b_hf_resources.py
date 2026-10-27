#!/usr/bin/env python3
"""CPU contracts only; no original model/asset/benchmark is opened."""
from pathlib import Path
from contextlib import contextmanager
import copy
import io
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tinylm  # noqa: F401 -- same process-local cache policy as the actual driver.
import torch
from transformers import GPT2Config, GPT2LMHeadModel
from transformers.cache_utils import Cache, DynamicLayer, LinearAttentionLayer
from scripts import diag_p106b_hf_resources as target


class Budget:
    def check(self):
        pass


class Tokenizer:
    eos_token_id = 3
    bos_token_id = 2
    pad_token_id = 0

    def decode(self, values, **_):
        return " ".join(str(x) for x in values)


class ResourceTests(unittest.TestCase):
    def test_prompt_is_not_first_generated_token(self):
        observer = target.Observer(None, "cpu", Budget())
        observer.started = 10.
        with patch.object(target.time, "perf_counter", side_effect=(10.1, 10.2)):
            observer.put(torch.tensor([[1, 2, 3]]))
            observer.put(torch.tensor([4]))
            observer.put(torch.tensor([5]))
        self.assertEqual(observer.prompt_ids, [1, 2, 3])
        self.assertEqual(observer.ids, [4, 5])
        self.assertAlmostEqual(observer.times[0], .1)

    def test_missing_prompt_and_multi_token_put_are_rejected(self):
        observer = target.Observer(None, "cpu", Budget())
        with self.assertRaises(ValueError):
            observer.end()
        observer.started = 0.
        observer.put(torch.tensor([[1]]))
        with self.assertRaises(ValueError):
            observer.put(torch.tensor([2, 3]))

    def test_actual_attention_cache_alias_storage(self):
        values = torch.arange(48, dtype=torch.float32).reshape(1, 2, 6, 4)
        layer = DynamicLayer()
        layer.update(values, values.view_as(values))
        cache = Cache([layer])
        # The real layer's initial update concatenates/copies K and V.
        audit = target.cache_audit(cache)
        self.assertEqual(audit["unique_storage_bytes"], 2*values.untyped_storage().nbytes())
        self.assertEqual(audit["unique_storages"], 2)
        # Exercise actual tensor aliases, rather than assuming update kept one.
        layer.values = layer.keys.view_as(layer.keys)
        audit = target.cache_audit(cache)
        self.assertEqual(audit["unique_storage_bytes"], layer.keys.untyped_storage().nbytes())
        self.assertEqual(audit["unique_storages"], 1)

    def test_actual_recurrent_and_conv_cache_are_counted(self):
        layer = LinearAttentionLayer()
        layer.lazy_initialization(conv_states=torch.zeros(1, 4, 3),
            recurrent_states=torch.zeros(1, 2, 4, 3), conv_kernel_size=3)
        expected = sum(t.untyped_storage().nbytes()
            for t in (layer.conv_states[0], layer.recurrent_states[0]))
        audit = target.cache_audit(Cache([layer]))
        self.assertEqual(audit["unique_storage_bytes"], expected)
        self.assertEqual(audit["unique_storages"], 2)

    def test_empty_or_unknown_cache_does_not_become_zero_pass(self):
        for value in (None, Cache([]), SimpleNamespace(keys=torch.zeros(2))):
            with self.assertRaises((ValueError, TypeError)):
                target.cache_audit(value)

    def test_nested_alias_and_cycle_terminate(self):
        value = torch.ones(8)
        cache = dict(keys=value, values=value[2:])
        cache["cycle"] = cache
        self.assertEqual(target.cache_audit(cache)["unique_storage_bytes"], value.untyped_storage().nbytes())

    def test_generation_config_eos_and_forced_length_are_separate(self):
        model = SimpleNamespace(generation_config=SimpleNamespace(eos_token_id=[3, 4]))
        forced, eos = target.config_for(model, Tokenizer(), 32, False)
        natural, _ = target.config_for(model, Tokenizer(), 64, True)
        self.assertIsNone(forced.eos_token_id)
        self.assertEqual(eos, [3, 4])
        self.assertEqual(natural.eos_token_id, [3, 4])
        self.assertTrue(natural.use_cache and natural.disable_compile)
        self.assertFalse(natural.do_sample)
        self.assertEqual(natural.num_beams, 1)

    def test_actual_tiny_hf_generate_observer_matches_unobserved(self):
        torch.manual_seed(9)
        model = GPT2LMHeadModel(GPT2Config(vocab_size=32, n_layer=1, n_head=2,
            n_embd=16, n_positions=32, bos_token_id=2, eos_token_id=3,
            pad_token_id=0, attn_implementation="eager")).float().eval()
        before = {k: v.clone() for k, v in model.state_dict().items()}
        values = target.pair(model, Tokenizer(), [4, 5, 6], "cpu", 4, False, Budget(), True)
        self.assertTrue(values["actual_token_ids_and_stop_equal"])
        self.assertEqual(values["observed"]["generated_tokens"], 4)
        self.assertGreater(values["observed"]["first_token_ms"], 0)
        self.assertGreater(values["observed"]["returned_cache"]["unique_storage_bytes"], 0)
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in model.state_dict().items()))
        self.assertFalse(model._forward_hooks)

    def test_actual_forced_eos_token_does_not_end_fixed_length(self):
        model = GPT2LMHeadModel(GPT2Config(vocab_size=16, n_layer=1, n_head=2,
            n_embd=8, n_positions=32, bos_token_id=2, eos_token_id=0,
            pad_token_id=0, attn_implementation="eager")).float().eval()
        with torch.no_grad():
            model.lm_head.weight.zero_()
        forced = target.pair(model, Tokenizer(), [4, 5], "cpu", 8, False, Budget(), True)
        natural = target.pair(model, Tokenizer(), [4, 5], "cpu", 8, True, Budget(), False)
        self.assertEqual(forced["unobserved"]["generated_ids"], [0]*8)
        self.assertEqual(forced["observed"]["finish_reason"], "MAX_NEW_EOS_DISABLED")
        self.assertEqual(natural["unobserved"]["generated_ids"], [0])
        self.assertEqual(natural["observed"]["finish_reason"], "EOS")

    @staticmethod
    def closed_fixture():
        spec = dict(id="gemma270", assets={"weight": "SHA"}, core_sha256="CORE", model_source_sha256="CODE")
        closed = dict(model="gemma270", returncode=0, status="OFFICIAL_CORE6_FULL_COMPLETE",
            assets={"weight": "SHA"}, model_proof=dict(initial_core_sha256="CORE", final_core_sha256="CORE",
                body_unchanged=True, source_assets_unchanged=True, model_source_sha256="CODE"))
        return spec, closed

    def test_closed_model_id_is_not_inferred_from_shared_class(self):
        spec, closed = self.closed_fixture()
        target.closed_evidence("gemma270", spec, closed)
        swapped = copy.deepcopy(closed)
        swapped["model"] = "gemma1b"
        with self.assertRaisesRegex(ValueError, "model ID"):
            target.closed_evidence("gemma270", spec, swapped)

    def test_closed_core_and_assets_must_match_entire_lineage(self):
        spec, closed = self.closed_fixture()
        bad = copy.deepcopy(closed)
        bad["model_proof"]["final_core_sha256"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "core differs"):
            target.closed_evidence("gemma270", spec, bad)
        bad = copy.deepcopy(closed)
        bad["assets"]["weight"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "assets/body"):
            target.closed_evidence("gemma270", spec, bad)

    def test_generation_exception_removes_forward_hook(self):
        model = torch.nn.Linear(2, 2)
        model.generation_config = SimpleNamespace(eos_token_id=3)
        model.generate = lambda **_: (_ for _ in ()).throw(RuntimeError("deliberate fixture failure"))
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            target.generate(model, Tokenizer(), [1], "cpu", 3, False, Budget(), True)
        self.assertFalse(model._forward_hooks)

    def test_observation_mismatch_is_error(self):
        with patch.object(target, "generate", side_effect=(
            dict(generated_ids=[1], finish_reason="MAX_NEW"),
            dict(generated_ids=[2], finish_reason="MAX_NEW"))):
            with self.assertRaisesRegex(ValueError, "observation changed"):
                target.pair(None, None, [0], "cpu", 1, False, Budget(), True)

    def test_cpu_watch_cleanup_does_not_replace_generation_error(self):
        failures = []
        watch = SimpleNamespace(start=lambda: None,
            stop=lambda: (_ for _ in ()).throw(OSError("watch cleanup failed")))
        with patch("scripts.bench_infer._CpuWatch", return_value=watch), \
                patch.object(target, "generate", side_effect=ValueError("generation failed")):
            with self.assertRaisesRegex(ValueError, "generation failed"):
                target.pair(None, None, [0], "cpu", 1, False, Budget(), True, failures)
        self.assertEqual(failures[0]["original_generation_error"]["type"], "ValueError")
        self.assertEqual(failures[0]["cpu_watch_exit_error"]["type"], "OSError")

    def test_loader_cleanup_failure_keeps_primary_body_error(self):
        @contextmanager
        def context(*_):
            try:
                yield SimpleNamespace(), {}
            finally:
                raise OSError("loader cleanup failed")
        proof = {}
        with patch.object(target.official, "model_runtime", context):
            with self.assertRaisesRegex(OSError, "loader cleanup failed"):
                with target.runtime("falcon90m", None, {}, proof):
                    raise ValueError("first body error")
        self.assertEqual(proof["primary_body_error"], dict(type="ValueError", message="first body error"))
        self.assertEqual(proof["loader_exit_error"]["type"], "OSError")

    def test_report_write_failure_is_separate_and_nonzero(self):
        report = dict(status="HF_RESOURCE_LANE_ERROR", error=dict(type="ValueError", message="primary"))
        with patch.object(target.common, "write_new", side_effect=OSError("report write failed")), \
                patch("sys.stdout", new=io.StringIO()):
            self.assertFalse(target.persist_report(ROOT/"unused", report))
        self.assertEqual(report["returncode"], 9)
        self.assertEqual(report["error"]["message"], "primary")
        self.assertEqual(report["report_persist_error"]["type"], "OSError")

    def test_check_only_does_not_enter_runtime(self):
        args = ["--profile", "unused", "--profile-sha256", "X", "--source-sha256", "Y",
            "--model", "gemma270", "--device", "cuda", "--check-only"]
        with patch.object(target, "metadata", return_value=({}, {}, ROOT/"unused", {"sha256": "Y"})), \
                patch.object(target, "execute") as execute, patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(target.main(args), 0)
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
