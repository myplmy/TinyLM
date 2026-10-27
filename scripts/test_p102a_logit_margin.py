"""Numerical and resource-boundary tests; no checkpoints or GPU calls."""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from scripts import diag_p102a_logit_margin as diag


class MarginContract(unittest.TestCase):
    def test_checkpoint_tuple_json_array_cfg_contract(self):
        checkpoint = dict(mtp_horizons=(2, 3, 4), mtp_aux=False, dim=768)
        wire = dict(dim=768, mtp_aux=False, mtp_horizons=[2, 3, 4])
        self.assertTrue(diag.same_cfg(checkpoint, wire))
        self.assertFalse(diag.same_cfg(checkpoint, dict(wire, dim=512)))
        self.assertFalse(diag.same_cfg(checkpoint, dict(wire, mtp_aux=0)))

    def test_target_exclusion_uses_whole_nontarget_mass(self):
        z = torch.tensor([[4., 0., 0.], [0., 4., 0.]])
        margin, loss, gradient = diag.reference_rows(z, torch.tensor([0, 1]))
        expected = 4 - math.log(2)
        self.assertTrue(torch.allclose(margin, torch.full((2,), expected, dtype=torch.float64)))
        self.assertTrue(torch.all(loss > 0))
        self.assertTrue(torch.all(gradient < 0))

    def test_fp32_high_margin_real_ce_sum_loses_target_gradient(self):
        z = torch.tensor([[18. + math.log(2), 0., 0.]])
        observed = diag.observe_ce(z, torch.tensor([0]))
        self.assertEqual(observed["zero_target_gradient_with_nonzero_reference"], 1)
        self.assertEqual(observed["zero_forward_loss_with_nonzero_reference"], 1)
        self.assertGreater(observed["forward_abs_error_max"], 0)
        self.assertFalse(z.requires_grad)

    def test_nonargmax_target_is_not_false_collapse(self):
        observed = diag.observe_ce(torch.tensor([[18., 0., 0.]]), torch.tensor([1]))
        self.assertEqual(observed["zero_target_gradient_with_nonzero_reference"], 0)
        self.assertLess(observed["margin"][0], -17)

    def test_permutation_of_vocabulary_preserves_margin(self):
        z = torch.tensor([[2., -2., 1.], [0., 4., -3.]])
        y = torch.tensor([2, 0])
        a = diag.reference_rows(z, y)
        b = diag.reference_rows(z[:, [2, 0, 1]], torch.tensor([0, 1]))
        for x, v in zip(a, b):
            self.assertTrue(torch.equal(x, v))

    def test_invalid_and_zero_targets_are_rejected(self):
        for z, y in [(torch.tensor([[float("nan"), 0.]]), torch.tensor([0])),
                     (torch.ones(1, 3), torch.tensor([3])),
                     (torch.ones(1, 1), torch.tensor([0]))]:
            with self.assertRaises(ValueError):
                diag.reference_rows(z, y)
        with self.assertRaises(ValueError):
            diag.summarize([])

    def test_update_coverage_fixed_first_last_unique(self):
        selected = diag.choose_updates(16, 2289)
        self.assertEqual((selected[0], selected[-1]), (0, 2288))
        self.assertEqual(len(set(selected)), 16)
        with self.assertRaises(ValueError):
            diag.choose_updates(1, 2289)

    def test_biased_probes_are_unique_low_middle_high(self):
        chosen = diag.choose_probes(list(range(1024)))
        self.assertEqual(len(set(chosen)), 16)
        self.assertEqual(chosen[:4], list(range(4)))
        self.assertEqual(chosen[-8:], list(range(1016, 1024)))

    def test_global_cap_context_reserve_and_exact_boundary(self):
        cap = 4_000_000_000
        diag.admit_point(dict(used_mib=3000), cap, 512)
        for used, reserve in [(3400, 512), (3815, 0), (4096, 0)]:
            with self.assertRaises(diag.ResourceHold):
                diag.admit_point(dict(used_mib=used), cap, reserve)

    def test_nvml_failure_holds_and_does_not_retry_gpu(self):
        with patch.object(diag.subprocess, "run") as run:
            run.return_value.returncode = 255
            run.return_value.stderr = "blocked"
            with self.assertRaises(diag.ResourceHold):
                diag.memory_point()
            self.assertEqual(run.call_count, 1)

    def test_paths_protected_and_symlink_guard(self):
        for name in ["../elsewhere", "datasets/TinyDataset/a", "/tmp/x", ".codex/x"]:
            with self.assertRaises(ValueError):
                diag.safe(name)
        self.assertEqual(diag.safe("scripts/diag_p102a_logit_margin.py").parent, diag.ROOT / "scripts")

    def test_evidence_never_overwrites_and_requires_json_finite(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "report.json"
            diag.write_new(p, dict(done=True))
            with self.assertRaises(ValueError):
                diag.write_new(p, dict(done=False))
            with self.assertRaises(ValueError):
                diag.write_new(Path(directory) / "invalid.json", dict(v=float("nan")))

    def test_cpu_gradient_does_not_mutate_supplied_tensor(self):
        z = torch.randn(32, 47)
        old = z.clone()
        observed = diag.observe_ce(z, torch.arange(32))
        self.assertTrue(torch.equal(z, old))
        self.assertIsNone(z.grad)
        self.assertEqual(diag.summarize([observed])["targets"], 32)

    def test_fp64_reference_does_not_alias_and_scatter_into_input(self):
        z = torch.tensor([[1., 3., 2.]], dtype=torch.float64)
        original = z.clone()
        diag.reference_rows(z, torch.tensor([1]))
        self.assertTrue(torch.equal(z, original))

    def test_oracle_underflow_is_not_silently_called_no_collapse(self):
        row = diag.observe_ce(torch.tensor([[1200., 0.]]), torch.tensor([0]))
        self.assertEqual(row["fp64_reference_underflow_positions"], 1)
        self.assertEqual(diag.summarize([row])["fp64_reference_underflow_positions"], 1)


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
