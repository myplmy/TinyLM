"""CPU-only original-scale deployment and fresh-process loading contracts."""
from copy import deepcopy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from scripts import p014e_packed_g128 as packed
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.model.ternary import TLinear


def toy(tied=True):
    cfg = TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                    emb_rank=8, n_prelude=1, n_middle=2, n_coda=1, mlp_group=2,
                    cla_group=2, micro_group=8, max_seq_len=32,
                    quantize_embedding=False, grad_checkpoint=False, tie_mlp=tied)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(20261027)
        model = TiedMLPTransformer(cfg).eval()
    with torch.no_grad():
        model.freeze_quant()
    return model


def payload():
    return packed.export_payload(toy(), provenance=dict(purpose="CPU_TOY_ONLY"), tile_rows=8)


class PackedContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise AssertionError("CPU contract entered with CUDA initialized")

    def tearDown(self):
        self.assertFalse(torch.cuda.is_initialized())

    def test_noninteger_and_nonfinite_trits_rejected_before_codec(self):
        for value in (0.5, -0.5, float("nan"), float("inf"), 2.0):
            with self.assertRaises(ValueError):
                packed.strict_pack(torch.tensor([value]))

    def test_g128_padding_scale_and_tiny_nonzero_roundtrip(self):
        trits = (torch.arange(2 * 256).reshape(2, 2, 128) % 3 - 1).float()
        scales = torch.tensor([[1e-14, 0.7], [0.02, 0.0]])
        weight = (trits * scales.unsqueeze(-1)).reshape(2, 256)
        record = packed.pack_weight(weight, 128, 1)
        self.assertEqual(record["codes"].shape, (2, 2, 26))
        self.assertTrue(torch.equal(record["scales"], scales))
        module = packed.PackedGroupLinear(record, 1).eval()
        self.assertTrue(torch.equal(module.unpack_rows(0, 2), weight))
        self.assertEqual(sum(t.numel() * t.element_size() for t in module.buffers()), 120)
        self.assertEqual(list(module.parameters()), [])

    def test_nonternary_source_is_not_requantized(self):
        with self.assertRaises(ValueError):
            packed.pack_weight(torch.tensor([[0.2, 0.3, 0.0, -0.3]]), 4)

    def test_reserved_byte_padding_zero_scale_and_nan_refused(self):
        base = packed.pack_weight(torch.ones(1, 8), 8)
        for kind in ("reserved", "padding", "zero", "nan"):
            value = deepcopy(base)
            if kind == "reserved":
                value["codes"][0, 0, 0] = 243
            elif kind == "padding":
                raw = torch.zeros(1, 1, 10, dtype=torch.int8)
                raw[..., -1] = 1
                value["codes"] = packed.strict_pack(raw)[0]
            elif kind == "zero":
                value["scales"].zero_()
            else:
                value["scales"].fill_(float("nan"))
            with self.assertRaises(ValueError):
                packed.validate_record(value)

    def test_linear_allclose_without_full_weight_parameter_or_cache(self):
        weight = ((torch.arange(11 * 16).reshape(11, 16) % 3) - 1).float() * 0.07
        module = packed.PackedGroupLinear(packed.pack_weight(weight, 8), 3).eval()
        x = torch.randn(2, 5, 16)
        with torch.no_grad():
            torch.testing.assert_close(module(x), torch.nn.functional.linear(x, weight), rtol=2e-6, atol=2e-6)
        self.assertFalse(hasattr(module, "weight"))
        self.assertFalse(hasattr(module, "_wq"))
        self.assertEqual(set(dict(module.named_buffers())), {"packed_codes", "group_scales"})

    def test_grad_training_mode_delta_and_activation_dtype_refused(self):
        module = packed.PackedGroupLinear(packed.pack_weight(torch.ones(2, 8), 8))
        with self.assertRaises(RuntimeError):
            module.train()
        with self.assertRaises(ValueError):
            module(torch.zeros(1, 8))
        with torch.no_grad():
            for x, mode in ((torch.zeros(1, 8, dtype=torch.float64), None),
                            (torch.zeros(1, 8), torch.ones(1))):
                with self.assertRaises(ValueError):
                    module(x, mode)

    def test_full_toy_prefill_and_cache_match_product(self):
        source = toy()
        before = {k: v.clone() for k, v in source.state_dict().items()}
        exported = packed.export_payload(source, provenance=dict(purpose="CPU_TOY_ONLY"), tile_rows=8)
        deployed = packed.load_payload(exported)
        ids = torch.tensor([[3, 10, 4, 11, 12]])
        with torch.no_grad():
            a, b = source(ids), deployed(ids)
            torch.testing.assert_close(a, b, rtol=2e-5, atol=2e-6)
            pa, pb = None, None
            for token in ids[0]:
                la, pa = source(token.reshape(1, 1), past_kv=pa, use_cache=True)
                lb, pb = deployed(token.reshape(1, 1), past_kv=pb, use_cache=True)
                torch.testing.assert_close(la, lb, rtol=2e-5, atol=2e-6)
                self.assertEqual(la.argmax(-1).tolist(), lb.argmax(-1).tolist())
                self.assertEqual(set(pa), set(pb))
                for key in pa:
                    for xa, xb in zip(pa[key], pb[key]):
                        torch.testing.assert_close(xa, xb, rtol=2e-5, atol=2e-6)
        self.assertTrue(all(torch.equal(v, source.state_dict()[k]) for k, v in before.items()))

    def test_shared_mlp_aliases_and_nonpersistent_buffers_restored(self):
        deployed = packed.load_payload(payload())
        self.assertIs(deployed.layers[1].mlp[0], deployed.layers[2].mlp[0])
        self.assertIs(deployed.layers[1].mlp[0], deployed.mid_mlps[0])
        self.assertIs(deployed.layers[1].mlp[0].gate_proj, deployed.mid_mlps[0].gate_proj)
        self.assertFalse(any(t.is_meta for t in (*deployed.parameters(), *deployed.buffers())))
        self.assertFalse(any(isinstance(m, TLinear) for m in deployed.modules()))
        self.assertEqual(deployed._tlinear_cache, [])
        self.assertEqual(deployed._armed_tlinears, [])
        self.assertEqual(deployed.rope_cos.device.type, "cpu")
        self.assertEqual(deployed._anneal.item(), 1.0)
        with self.assertRaises(RuntimeError):
            deployed.clear_quant()

    def test_missing_or_split_aliases_and_rest_fields_refused(self):
        original = payload()
        variants = []
        value = deepcopy(original)
        value["matrices"][0]["paths"].pop()
        variants.append(value)
        value = deepcopy(original)
        value["rest"].pop()
        variants.append(value)
        value = deepcopy(original)
        value["rest"][0]["paths"].append("invalid.weight")
        variants.append(value)
        for value in variants:
            with self.assertRaises(ValueError):
                packed.load_payload(value)

    def test_loader_preserves_cpu_rng_and_uses_meta_skeleton(self):
        value = payload()
        rng = torch.get_rng_state().clone()
        deployed = packed.load_payload(value)
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        self.assertTrue(deployed._packed_g128_inference)
        self.assertFalse(any(p.requires_grad for p in deployed.parameters()))

    def test_export_rest_is_independent_snapshot_preserving_declared_aliases(self):
        source = toy()
        data = packed.export_payload(source, provenance=dict(purpose="CPU_TOY_ONLY"), tile_rows=8)
        deployed = packed.load_payload(data)
        original = deployed.emb.weight.clone()
        with torch.no_grad():
            source.emb.weight.add_(1)
            source.rope_cos.zero_()
        self.assertTrue(torch.equal(original, deployed.emb.weight))
        self.assertFalse(torch.equal(source.rope_cos, deployed.rope_cos))

    def test_packed_embedding_matches_existing_quantizer_and_chunked_head(self):
        source = toy()
        data = packed.export_payload(source, provenance=dict(purpose="CPU_TOY_ONLY"), tile_rows=8,
                                     embedding_format="ternary5_existing_twn", head_rows=16)
        deployed = packed.load_payload(data)
        source.quantize_embedding("ternary")
        source.cfg.emb_chunk = 16
        self.assertFalse(any("emb.weight" in row["paths"] for row in data["rest"]))
        self.assertEqual(deployed.emb.weight.numel(), 0)
        ids = torch.tensor([[3, 10, 4, 11, 12]])
        with torch.no_grad():
            torch.testing.assert_close(source(ids), deployed(ids), rtol=2e-5, atol=2e-6)
            selected = ids.reshape(-1)
            self.assertTrue(torch.equal(source._emb_rows(selected), deployed._emb_rows(selected)))
            for begin in range(0, 67, 16):
                selected = slice(begin, min(begin + 16, 67))
                self.assertTrue(torch.equal(source._emb_rows(selected), deployed._emb_rows(selected)))
            with self.assertRaises(ValueError):
                deployed._emb_rows(None)
            with self.assertRaises(ValueError):
                deployed._emb_rows(slice(0, 67))
            with self.assertRaises(RuntimeError):
                deployed._emb_w()

    def test_ternary_embedding_and_fp32_variant_cannot_be_silently_mixed(self):
        data = packed.export_payload(toy(), provenance=dict(purpose="CPU_TOY_ONLY"), tile_rows=8,
                                     embedding_format="ternary5_existing_twn", head_rows=16)
        data["embedding_format"] = "fp32_unchanged"
        with self.assertRaises(ValueError):
            packed.load_payload(data)

    def test_metadata_cannot_hide_master_weights_and_is_independent(self):
        source = toy()
        with self.assertRaises(ValueError):
            packed.export_payload(source, provenance=dict(state=source.state_dict()))
        with self.assertRaises(ValueError):
            packed.export_payload(source, provenance=dict(bad=float("nan")))
        provenance = dict(case=dict(name="original"))
        data = packed.export_payload(source, provenance=provenance)
        provenance["case"]["name"] = "changed"
        self.assertEqual(data["provenance"]["case"]["name"], "original")
        data["unneeded_master"] = source.state_dict()
        with self.assertRaises(ValueError):
            packed.load_payload(data)

    def test_loader_rejects_unsupported_cfg_before_forward(self):
        original = payload()
        for key, value in (("x2_active_tiles", [0]), ("wq_dtype", "bf16"),
                           ("quant_anneal", 0.5), ("micro_group", 16)):
            data = deepcopy(original)
            data["cfg"][key] = value
            if key == "x2_active_tiles":
                data["cfg"]["x2_tile_size"] = 16
            with self.assertRaises(ValueError):
                packed.load_payload(data)

    def test_existing_embedding_reference_restores_source_even_on_error(self):
        from scripts import diag_p014e_packed_deploy as driver
        source = toy()
        before = {key: value.clone() for key, value in source.state_dict().items()}
        chunk = source.cfg.emb_chunk
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with driver.reference_embedding(source, "ternary5_existing_twn", 16):
                self.assertEqual(source.emb.weight.numel(), 0)
                self.assertEqual(source.embedding_quantized(), "ternary")
                raise RuntimeError("deliberate")
        self.assertEqual(source.cfg.emb_chunk, chunk)
        self.assertIsNone(source.embedding_quantized())
        self.assertTrue(all(torch.equal(value, source.state_dict()[key]) for key, value in before.items()))

    def test_driver_cost_hold_keeps_partial_and_does_not_shrink_full_suite(self):
        from scripts import diag_p014e_packed_deploy as driver
        from scripts.diag_p106b_resource_matrix import Budget
        tok = SimpleNamespace(encode=lambda _: SimpleNamespace(ids=list(range(1024))))
        base = dict(workloads=[dict(id=str(i), text="x", prompt_tokens=128 if i < 2 else 512)
                               for i in range(4)])
        progress = {}
        with patch.object(driver.resource, "unobserved_generation", return_value=dict(seconds=1000.0)) as probe:
            result, tensors = driver.measured_suite(None, None, tok, base, {}, "cpu", Budget(10), progress=progress)
        self.assertIs(result, progress)
        self.assertEqual(result["status"], "BUDGET_HOLD_NOT_FULL_SUITE")
        self.assertEqual(probe.call_count, 2)
        self.assertEqual(result["records"], [])
        self.assertEqual(tensors, [])

    def test_export_uses_existing_frozen_model_api_and_releases_toy(self):
        from scripts import diag_p014e_packed_deploy as driver
        from scripts.diag_p106b_resource_matrix import Budget
        @contextmanager
        def fake_context(spec, tokenizer, device, budget, proof):
            self.assertEqual(device, "cpu")
            proof["toy_api_contract"] = True
            yield toy(), None, None, None
        with tempfile.TemporaryDirectory(prefix="p014e_export_api_", dir=ROOT / "tmp") as directory:
            report = {}
            with patch.object(driver.resource, "frozen_model", side_effect=fake_context) as loader, \
                    patch.object(driver, "deploy_dir", return_value=Path(directory) / "new"), \
                    patch.object(driver, "VARIANTS", ("fp32_unchanged",)):
                driver.export(dict(tokenizer={}), dict(checkpoint={}, core_sha256="CPU_TOY"), {}, Budget(30), report)
            self.assertEqual(loader.call_count, 1)
            self.assertTrue(report["source_model_released"])
            self.assertTrue(report["source_proof"]["toy_api_contract"])
            self.assertEqual(len(report["payloads"]), 1)

    def test_cuda_cleanup_requires_both_physical_counters_zero(self):
        from scripts import diag_p014e_packed_deploy as driver
        driver.assert_cuda_clean(dict(allocated_bytes=0, reserved_bytes=0))
        for proof in ({}, dict(allocated_bytes=1, reserved_bytes=0),
                      dict(allocated_bytes=0, reserved_bytes=1)):
            with self.assertRaises(ValueError):
                driver.assert_cuda_clean(proof)

    def test_separate_reference_preserves_real_weight_route_guard(self):
        from scripts import diag_p014e_packed_deploy as driver
        from scripts.p106b_weight_route import weight_route
        source = toy(tied=False)
        with weight_route(source, "ternary") as route:
            source.freeze_quant()
            reference = driver.verified_reference_copy(source)
            with driver.reference_embedding(reference, "ternary5_existing_twn", 16), torch.no_grad():
                self.assertEqual(reference(torch.tensor([[3, 10, 4]])).shape, (1, 3, 67))
                self.assertEqual(source(torch.tensor([[3, 10, 4]])).shape, (1, 3, 67))
                route.assert_active()
                self.assertIsNone(source.embedding_quantized())
        self.assertIsNone(reference.embedding_quantized())

    def test_driver_identity_binds_reused_product_codec(self):
        from scripts import diag_p014e_packed_deploy as driver
        self.assertIn("tinylm/model/lut.py", driver.identity()["files"])

    def test_new_file_weights_only_fresh_process_without_source_checkpoint(self):
        with tempfile.TemporaryDirectory(prefix="p014e_toy_") as directory:
            path = Path(directory) / "toy.pt"
            data = payload()
            size = packed.save_new(data, path)
            self.assertGreater(size, packed.payload_storage(data)["unique_storage_bytes"])
            with self.assertRaises(ValueError):
                packed.save_new(data, path)
            code = ("import json,sys,torch; from scripts.p014e_packed_g128 import load_file; "
                    "torch.set_num_threads(1); m=load_file(sys.argv[1]); "
                    "torch.set_grad_enabled(False); y=m(torch.tensor([[3,10,4]])); "
                    "print(json.dumps(dict(shape=list(y.shape),cuda=torch.cuda.is_initialized(),"
                    "meta=any(t.is_meta for t in m.buffers()))))")
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"}
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", code, str(path)],
                                    cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), dict(shape=[1, 3, 67], cuda=False, meta=False))


if __name__ == "__main__":
    unittest.main()
