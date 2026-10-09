"""CPU matrix fixtures only, not a loaded TinyLM checkpoint or scientific run."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
from tinylm.model.modules import MLP
from tinylm.model.ternary import LoRA
from scripts.p093b_native_repair import (GSQProjection, GSQAdapter, shared_native,
    residual_adapters, weighted_factors, native_weight, parameters_unique, fit,
    measure, patched_group)


def fixtures():
    torch.manual_seed(93013)
    cfg = SimpleNamespace(dim=8, ffn_dim=16, n_layers=4, n_modes=1, mode_rank=0,
        micro_group=4, twn_thr_ratio=.7, ste_clip=2., sparse34=False, mlp_lora_bits=16)
    originals = [MLP(copy.deepcopy(cfg)) for _ in range(4)]
    inputs = [torch.randn(24, 8) for _ in range(4)]
    with torch.no_grad(): targets = [m(x, None).detach() for m, x in zip(originals, inputs)]
    return cfg, originals, inputs, targets


class NativeRepairTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_shared_freezes_and_preserves_originals(self):
        cfg, originals, x, y = fixtures()
        before = [[p.detach().clone() for p in m.parameters()] for m in originals]
        shared = shared_native(originals, cfg)
        self.assertFalse(any(p.requires_grad for p in shared.parameters()))
        for m, values in zip(originals, before):
            self.assertTrue(all(torch.equal(p, v) for p, v in zip(m.parameters(), values)))
        self.assertTrue(torch.isfinite(torch.tensor(measure(shared, x, y)["nrms"])))

    def test_weighted_full_rank_reconstruction(self):
        torch.manual_seed(1)
        e = torch.randn(4, 8); x = torch.randn(24, 8)
        u, d = weighted_factors(e, x, 4)
        self.assertTrue(torch.allclose(u @ d, e, atol=3e-5, rtol=3e-5))

    def test_existing_lora_zero_noop(self):
        cfg, _, x, _ = fixtures(); layer = LoRA(cfg, 8, 16, 2)
        self.assertTrue(torch.equal(layer(x[0]), torch.zeros(24, 16)))
        self.assertEqual(layer.D.dtype, torch.float32)

    def test_residual_ownership_and_finite_adam_gradient(self):
        cfg, originals, x, y = fixtures(); shared = shared_native(originals, cfg)
        adapters = residual_adapters(originals, shared, x, 2, cfg)
        before = [native_weight(getattr(shared, name)) for name in ("gate_proj", "up_proj", "down_proj")]
        result = fit(shared, x, y, adapters=adapters, steps=3)
        self.assertGreater(result["grad_max"], 0)
        self.assertEqual(result["trainable_parameters"], 4*3*2*(8+16))
        for name, weight in zip(("gate_proj", "up_proj", "down_proj"), before):
            self.assertTrue(torch.equal(native_weight(getattr(shared, name)), weight))

    def test_gsq_hard_init_matches_native_and_codes(self):
        cfg, originals, _, _ = fixtures(); weight = native_weight(originals[0].gate_proj)
        q = GSQProjection(weight, 4, cfg).eval()
        self.assertTrue(torch.allclose(q.matrix(), weight, atol=1e-6))
        code, scale = q.code_scale()
        self.assertTrue(set(code.flatten().tolist()).issubset({-1, 0, 1}))
        self.assertTrue(torch.allclose((code*scale).reshape_as(weight), q.matrix()))

    def test_gumbel_has_mask_sign_scale_gradient(self):
        cfg, _, _, _ = fixtures(); q = GSQProjection(torch.ones(4, 8), 4, cfg).train()
        q(torch.randn(12, 8)).square().mean().backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in q.parameters()))

    def test_gsq_factor_native_roundtrip_rank_per_row(self):
        cfg, _, x, _ = fixtures(); a = LoRA(cfg, 8, 16, 2)
        with torch.no_grad(): a.U.normal_(0, .1)
        q = GSQAdapter(a).eval(); native = q.native_export()
        self.assertEqual(native.bits, 2)
        self.assertTrue(torch.allclose(q(x[0]), native(x[0]), atol=2e-6, rtol=2e-5))

    def test_group_zero_rejected_for_native_lora_export(self):
        cfg, _, _, _ = fixtures(); cfg.micro_group = 0
        with self.assertRaises(ValueError): GSQAdapter(LoRA(cfg, 8, 16, 2))

    def test_unique_optimizer_parameters(self):
        cfg, _, _, _ = fixtures(); a = LoRA(cfg, 8, 16, 2)
        self.assertEqual(len(parameters_unique([a, a])), 2)

    def test_patch_restores_slots_after_forward_error(self):
        model = SimpleNamespace(layers=[torch.nn.Module() for _ in range(4)])
        originals = [object() for _ in range(4)]
        for layer, original in zip(model.layers, originals): layer.mlp = [original]; layer.has_lora = False
        with self.assertRaises(RuntimeError):
            with patched_group(model, range(4), "shared", [(torch.nn.Identity(),)*3]*4):
                self.assertTrue(all(l.has_lora for l in model.layers))
                raise RuntimeError("fixture forward failure")
        self.assertTrue(all(l.mlp[0] is o and not l.has_lora for l, o in zip(model.layers, originals)))
        self.assertFalse(any(hasattr(l, "lora_gate") for l in model.layers))

    def test_invalid_geometry_fails_closed(self):
        with self.assertRaises(ValueError): weighted_factors(torch.ones(4, 8), torch.ones(3, 7), 2)
        cfg, _, _, _ = fixtures()
        with self.assertRaises(ValueError): GSQProjection(torch.ones(4, 7), 4, cfg)

    def test_nonfinite_function_error_fails_before_report(self):
        from scripts.p093b_native_repair import normalized_loss
        with self.assertRaises(ValueError): normalized_loss([torch.tensor([float("nan")])], [torch.ones(1)])

    def test_projection_shards_restore_exactly_and_detect_tamper(self):
        from scripts.diag_p093b_native_repair import save_candidate,load_adapters
        cfg,originals,x,y=fixtures(); shared=shared_native(originals,cfg)
        adapters=residual_adapters(originals,shared,x,2,cfg)
        info={"parent_sha256":"A"*64,"source_selected_sha256":"B"*64,"code_sha256":{"fixture":"C"*64}}
        with tempfile.TemporaryDirectory(prefix="p093b_parts_") as tmp:
            folder=Path(tmp); manifest=save_candidate(folder,"fixture",shared,adapters,info)
            self.assertTrue(all(f["bytes"]<=20_000_000 for f in manifest["files"]))
            restored=load_adapters(folder,"fixture",shared,cfg,info)
            for a,b in zip(adapters,restored):
                for aa,bb in zip(a,b): self.assertTrue(torch.equal(aa.D,bb.D) and torch.equal(aa.U,bb.U))
            target=folder/manifest["files"][0]["path"]
            with target.open("ab") as f: f.write(b"fixture corruption")
            with self.assertRaises(ValueError): load_adapters(folder,"fixture",shared,cfg,info)

    def test_native_ce_probe_accepts_tensor_not_tuple(self):
        import numpy as np
        from scripts.diag_p093b_native_repair import ce_probe,viable
        class TensorFixture:
            def __call__(self,t): return torch.zeros(t.shape[0],t.shape[1],8)
        r=ce_probe(TensorFixture(),[np.arange(128)%8],"cpu")
        self.assertAlmostEqual(r["mean_ce"],__import__("math").log(8),places=5)
        self.assertFalse(viable(0,0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
