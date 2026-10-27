"""CPU contract tests for physical storage and transparent token observation."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import torch

from scripts import diag_p106b_resource_matrix as diag


class ResourceContract(unittest.TestCase):
    def test_true_first_token_and_decode_denominator(self):
        value = diag.summarize_times([11., 11.5, 12.], 10., 12.5, 3)
        self.assertEqual(value["first_token_ms"], 1000.)
        self.assertEqual(value["decode_tokens_per_second"], 2.)
        self.assertEqual(value["end_to_end_tokens_per_second"], 1.2)

    def test_zero_missing_backwards_and_nan_token_times_fail(self):
        for points, count in [([], 0), ([11.], 2), ([12., 11.], 2), ([float("nan")], 1)]:
            with self.assertRaises(ValueError):
                diag.summarize_times(points, 10., 13., count)

    def test_single_natural_eos_has_no_invented_decode_rate(self):
        self.assertIsNone(diag.summarize_times([11.], 10., 12., 1)["decode_tokens_per_second"])

    def test_physical_storage_deduplicates_alias_and_view(self):
        a = torch.arange(24.)
        observed = diag.storage_audit([("parameter", a), ("cache", a.view(4, 6)), ("slice", a[:1])])
        self.assertEqual(observed["unique_storage_bytes"], 96)
        self.assertEqual(observed["unique_storages"], 1)
        self.assertEqual(observed["tensor_references"], 3)

    def test_model_unregistered_cache_and_shared_parameter_count(self):
        model = torch.nn.Linear(2, 3, bias=False)
        model.alias = model.weight
        model._wq = model.weight.detach().view_as(model.weight)
        model._independent = torch.zeros(5)
        self.assertEqual(diag.model_storage(model)["unique_storage_bytes"], 24 + 20)

    def test_empty_view_still_holds_nonempty_backing_storage(self):
        original = torch.zeros(12)
        view = original[:0]
        self.assertEqual(diag.storage_audit([("empty_view", view)])["unique_storage_bytes"], 48)
        self.assertEqual(diag.storage_audit([("empty", torch.zeros(0))])["unique_storage_bytes"], 0)

    def test_nested_cache_cycle_does_not_recurse_or_double_count(self):
        t = torch.zeros(7)
        value = dict(t=t)
        value["cycle"] = value
        value["again"] = [t]
        self.assertEqual(len(list(diag.nested_tensors(value))), 1)

    def test_fixed_capture_keeps_exact_special_ids(self):
        tok = SimpleNamespace(decode=lambda ids, skip_special_tokens: str(ids), token_to_id=lambda s: 2)
        capture = diag.FixedCapture(tok, [3, 10, 4])
        self.assertEqual(capture.encode("ignored").ids, [3, 10, 4])
        self.assertEqual(capture.decode([3, 10, 4, 2]), "[3, 10, 4, 2]")
        self.assertEqual(capture.decoded_ids, [3, 10, 4, 2])

    def test_expired_authority_is_not_old_4gb_limit(self):
        budget = diag.Budget(10, datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaises(TimeoutError):
            budget.check()

    def test_never_overwrite_and_nonfinite_json_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "report.json"
            diag.write_new(p, dict(done=True))
            with self.assertRaises(ValueError):
                diag.write_new(p, dict(done=False))
            with self.assertRaises(ValueError):
                diag.write_new(Path(directory) / "bad.json", dict(x=float("nan")))

    def test_protected_and_escape_paths_refused(self):
        for p in ["datasets/TinyDataset/x", "../elsewhere", "/tmp/x", ".codex/a"]:
            with self.assertRaises(ValueError):
                diag.safe(p)

    def test_pick_observer_preserves_sampler_outputs_and_restores(self):
        module = __import__("importlib").import_module("tinylm.infer.generate")
        cfg = SimpleNamespace(max_seq_len=16)
        tok = SimpleNamespace(decode=lambda ids, skip_special_tokens=False: str(ids), token_to_id=lambda s: 2)
        class Toy(torch.nn.Module):
            def forward(self, x, **kw):
                logits = torch.zeros(1, x.shape[1], 5)
                logits[..., 1] = 2
                past = {0: (torch.zeros(1, 1, 4, 1), torch.zeros(1, 1, 4, 1))}
                return logits, past
        original = module._pick
        record = diag.one_generation(Toy(), cfg, tok, [3], "cpu", 3,
            natural=False, chatml=False, budget=diag.Budget(10))
        self.assertEqual(record["generated_ids"], [1, 1, 1])
        self.assertEqual(record["forward_calls"], 3)
        self.assertEqual(record["max_returned_kv_storage_bytes"], 32)
        plain = diag.unobserved_generation(Toy(), cfg, tok, [3], "cpu", 3)
        self.assertEqual(record["generated_ids"], plain["generated_ids"])
        self.assertIs(module._pick, original)

    def test_pick_observer_restored_on_model_failure(self):
        module = __import__("importlib").import_module("tinylm.infer.generate")
        tok = SimpleNamespace(token_to_id=lambda s: 2)
        original = module._pick
        class Broken(torch.nn.Module):
            def forward(self, *args, **kw):
                raise RuntimeError("original failure")
        with self.assertRaisesRegex(RuntimeError, "original failure"):
            diag.one_generation(Broken(), SimpleNamespace(max_seq_len=16), tok, [3], "cpu", 3,
                natural=False, chatml=False, budget=diag.Budget(10))
        self.assertIs(module._pick, original)

    def test_workspace_clear_removes_only_library_cache_and_records_before(self):
        class CUDA:
            allocated, reserved = 8519680, 20971520
            def synchronize(self): pass
            def empty_cache(self):
                if not self.allocated: self.reserved = 0
            def memory_allocated(self): return self.allocated
            def memory_reserved(self): return self.reserved
        cuda = CUDA()
        def clear(): cuda.allocated = 0
        value = diag.close_cuda(SimpleNamespace(cuda=cuda, _C=SimpleNamespace(_cuda_clearCublasWorkspaces=clear)))
        self.assertEqual(value["before_workspace_clear"]["allocated_bytes"], 8519680)
        self.assertTrue(value["workspace_clear_called"])
        self.assertEqual((value["allocated_bytes"], value["reserved_bytes"]), (0, 0))

    def test_live_allocation_is_not_hidden_by_workspace_clear(self):
        cuda = SimpleNamespace(synchronize=lambda: None, empty_cache=lambda: None,
            memory_allocated=lambda: 1234, memory_reserved=lambda: 4096)
        value = diag.close_cuda(SimpleNamespace(cuda=cuda, _C=SimpleNamespace(_cuda_clearCublasWorkspaces=lambda: None)))
        self.assertEqual(value["allocated_bytes"], 1234)

    def test_workspace_clear_error_preserves_earlier_memory_receipt(self):
        cuda = SimpleNamespace(synchronize=lambda: None, empty_cache=lambda: None,
            memory_allocated=lambda: 8519680, memory_reserved=lambda: 20971520)
        def fail(): raise RuntimeError("workspace failed")
        receipt = {}
        with self.assertRaisesRegex(RuntimeError, "workspace failed"):
            diag.close_cuda(SimpleNamespace(cuda=cuda, _C=SimpleNamespace(_cuda_clearCublasWorkspaces=fail)), receipt)
        self.assertEqual(receipt["before_workspace_clear"]["allocated_bytes"], 8519680)
        self.assertEqual(receipt["error"]["message"], "workspace failed")
        self.assertEqual(receipt["allocated_bytes"], 8519680)

    def test_plain_timing_excludes_cpu_watcher_shutdown(self):
        tok = SimpleNamespace(decode=lambda ids, skip_special_tokens=False: str(ids), token_to_id=lambda s: 2)
        clock = dict(stopped=False, calls=0)
        class Watch:
            ps = True
            def start(self): pass
            def stop(self):
                clock["stopped"] = True
                return 0., 0., 0.
        class Model(torch.nn.Module):
            def forward(self, x, **kw):
                return torch.zeros(1, x.shape[1], 5), {0: (torch.zeros(1, 1, 2, 1), torch.zeros(1, 1, 2, 1))}
        def tick():
            clock["calls"] += 1
            return 10. if clock["calls"] == 1 else (1000. if clock["stopped"] else 11.)
        with patch("scripts.bench_infer._CpuWatch", Watch), patch.object(diag.time, "perf_counter", tick):
            result = diag.unobserved_generation(Model(), SimpleNamespace(max_seq_len=16), tok, [3], "cpu", 3)
        self.assertEqual(result["seconds"], 1.)

    def test_natural_eos_and_eot_observer_keep_original_stop(self):
        tok = SimpleNamespace(decode=lambda ids, skip_special_tokens=False: str(ids), token_to_id=lambda s: 2)
        class Stop(torch.nn.Module):
            def __init__(self, token):
                super().__init__()
                self.token = token
            def forward(self, x, **kw):
                z = torch.zeros(1, x.shape[1], 5)
                z[..., self.token] = 5
                return z, {0: (torch.zeros(1, 1, 2, 1), torch.zeros(1, 1, 2, 1))}
        for token, reason in ((2, "EOS"), (4, "STOP_SEQUENCE")):
            row = diag.one_generation(Stop(token), SimpleNamespace(max_seq_len=16), tok, [3], "cpu", 3,
                natural=True, chatml=True, budget=diag.Budget(10))
            self.assertEqual(row["generated_ids"], [token])
            self.assertEqual(row["metadata"]["finish_reason"], reason)

    def test_pick_timeout_restores_observer_even_after_gpu_style_allocation(self):
        module = __import__("importlib").import_module("tinylm.infer.generate")
        tok = SimpleNamespace(token_to_id=lambda s: 2)
        original = module._pick
        class Model(torch.nn.Module):
            def forward(self, x, **kw):
                z = torch.zeros(1, x.shape[1], 5)
                return z, {0: (torch.zeros(1, 1, 2, 1), torch.zeros(1, 1, 2, 1))}
        budget = SimpleNamespace(check=lambda: (_ for _ in ()).throw(TimeoutError("after pick")))
        with self.assertRaisesRegex(TimeoutError, "after pick"):
            diag.one_generation(Model(), SimpleNamespace(max_seq_len=16), tok, [3], "cpu", 3,
                natural=False, chatml=False, budget=budget)
        self.assertIs(module._pick, original)


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
