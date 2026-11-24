"""CPU synthetic optimizer contracts; no native model, forward or dataset."""
from __future__ import annotations

import contextlib
import copy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import torch
from tinylm.training_defaults import EXPERIMENTAL_MATRIX_OPTIMIZERS as METHODS
from tinylm.train.experimental_optimizers import (
    build_experimental_optimizers as build, checkpoint_manifest,
    validate_options, validate_optimizer_checkpoint, CHECKPOINT_KEY,
)


class SyntheticParameters(torch.nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(20261117)
        self.embedding = torch.nn.Embedding(7, 3)
        self.lm_head = torch.nn.Linear(3, 7, bias=False)
        self.lm_head.weight = self.embedding.weight
        self.emb_up = torch.nn.Parameter(torch.randn(3, 4))
        self.body = torch.nn.Linear(4, 3, bias=False)
        self.body_alias = self.body
        self.second = torch.nn.Parameter(torch.randn(2, 4))
        self.gsq_logits = torch.nn.Parameter(torch.randn(2, 3))
        self.mtp_up2 = torch.nn.Parameter(torch.randn(3, 4))
        self.scale_table = torch.nn.Parameter(torch.randn(2, 3))
        self.qk_gain_logit = torch.nn.Parameter(torch.randn(3))
        self.lrm = torch.nn.Parameter(torch.randn(()))
        self.norm = torch.nn.LayerNorm(4)

    def get_output_embeddings(self):
        return self.lm_head

    def param_groups(self, lr):
        parameters = dict(self.named_parameters())
        special = {"qk_gain_logit", "lrm"}
        return [dict(params=[self.body.weight], lr=lr / 2, weight_decay=.1, marker="tied"),
                dict(params=[p for n, p in parameters.items()
                             if n not in special and n != "body.weight"],
                     lr=lr, weight_decay=.07, marker="base"),
                dict(params=[self.lrm], lr=lr, weight_decay=.01, marker="lrm"),
                dict(params=[self.qk_gain_logit], lr=lr * .1, weight_decay=0., marker="qkg")]


def route(model, method, **options):
    return build(model, method, lr=.001, matrix_lr_mult=2., **options)


def gradients(model, phase):
    for index, p in enumerate(model.parameters()):
        p.grad = ((torch.arange(p.numel()).reshape(p.shape).float() + 1 + index + phase)
                  / (p.numel() + 7))


def step(model, optimizers, phase):
    gradients(model, phase)
    optimizers.validate_before_step()
    optimizers.adamw.step()
    optimizers.matrix.step()
    optimizers.adamw.zero_grad(set_to_none=True)
    optimizers.matrix.zero_grad(set_to_none=True)


def state_bytes(optimizer):
    return sum(t.numel() * t.element_size() for state in optimizer.state.values()
               for t in state.values() if isinstance(t, torch.Tensor))


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise ValueError("CPU contracts must not initialize CUDA")

    def same_parameters(self, first, second):
        for (name, a), (other, b) in zip(first.named_parameters(), second.named_parameters()):
            self.assertEqual(name, other)
            self.assertTrue(torch.equal(a.detach().reshape(-1).view(torch.uint8),
                                        b.detach().reshape(-1).view(torch.uint8)), name)

    def test_common_roles_alias_head_and_special_group_metadata(self):
        manifests = []
        for method in METHODS:
            model = SyntheticParameters()
            result = route(model, method)
            selected = {id(p) for p in result.matrices}
            self.assertEqual(selected, {id(model.body.weight), id(model.second)})
            all_parameters = [p for g in result.adamw.param_groups for p in g["params"]]
            self.assertEqual(len(all_parameters), len({id(p) for p in all_parameters}))
            self.assertFalse(selected & {id(p) for p in all_parameters})
            self.assertEqual(selected | {id(p) for p in all_parameters},
                             {id(p) for p in model.parameters()})
            self.assertEqual([g["marker"] for g in result.adamw.param_groups],
                             ["tied", "base", "lrm", "qkg"])
            self.assertEqual(result.adamw.param_groups[2]["weight_decay"], .01)
            self.assertEqual(result.adamw.param_groups[3]["lr"], .0001)
            self.assertEqual(result.adamw.param_groups[0]["params"], [])
            manifests.append(result.manifest["parameters"])
        self.assertTrue(all(m == manifests[0] for m in manifests))

    def test_explicit_LR_and_precision_validation(self):
        for method in METHODS:
            for value in (None, 0., -1., float("nan"), float("inf"), True):
                with self.subTest(method=method, value=value):
                    with self.assertRaises(ValueError):
                        validate_options(method, value)
            with self.assertRaises(ValueError):
                validate_options(method, 2., opt_dtype="bf16")
            if method.startswith("adamuon_"):
                with self.assertRaises(ValueError):
                    validate_options(method, 2., muon_scale="jordan")
            if method == "normuon_author_fp32":
                with self.assertRaisesRegex(ValueError, "owns its shape scale"):
                    validate_options(method, 2., muon_scale="jordan")

    def test_all_methods_update_finitely_and_retain_actual_state_precision(self):
        for method in METHODS:
            with self.subTest(method=method):
                model = SyntheticParameters()
                before = [p.detach().clone() for p in model.parameters()]
                result = route(model, method)
                step(model, result, 0)
                self.assertTrue(all(torch.isfinite(p).all() for p in model.parameters()))
                self.assertTrue(all(not torch.equal(a, b) for a, b in zip(before, model.parameters())))
                elements = sum(p.numel() for p in result.matrices)
                expected = {"muon_matched": 4 * elements,
                            "normuon_tinylm": 4 * elements + 4 * sum(p.shape[0] for p in result.matrices),
                            "normuon_author_fp32": 4 * elements + 4 * sum(p.shape[0] for p in result.matrices),
                            "adamuon_fp32v": 8 * elements,
                            "adamuon_author_bf16": 6 * elements}[method]
                self.assertEqual(state_bytes(result.matrix), expected)
                if method == "adamuon_author_bf16":
                    self.assertTrue(all(s["v_buffer"].dtype == torch.bfloat16
                                        for s in result.matrix.state.values()))
                    self.assertEqual(result.matrix.scratch_bytes, 2 * (12 + 8))

    def test_all_methods_exact_serialized_resume_including_AdamW_and_BF16_V(self):
        for method in METHODS:
            with self.subTest(method=method):
                first = SyntheticParameters()
                a = route(first, method)
                for phase in range(2):
                    step(first, a, phase)
                payload = dict(model=first.state_dict(), opt=a.adamw.state_dict(),
                               opt_muon=a.matrix.state_dict(), **{CHECKPOINT_KEY: checkpoint_manifest(a)})
                stream = io.BytesIO()
                torch.save(payload, stream)
                stream.seek(0)
                saved = torch.load(stream, map_location="cpu", weights_only=True)
                second = SyntheticParameters()
                b = route(second, method)
                validate_optimizer_checkpoint(saved, b.manifest, route=b)
                first_state_dtype = [x.dtype for s in saved["opt_muon"]["state"].values()
                                     for x in s.values() if isinstance(x, torch.Tensor)]
                second.load_state_dict(saved["model"])
                b.adamw.load_state_dict(saved["opt"])
                b.matrix.load_state_dict(saved["opt_muon"])
                self.assertEqual(first_state_dtype, [x.dtype for s in saved["opt_muon"]["state"].values()
                                                     for x in s.values() if isinstance(x, torch.Tensor)])
                for phase in range(2, 4):
                    step(first, a, phase)
                    step(second, b, phase)
                    self.same_parameters(first, second)
                self.assertEqual(state_bytes(a.matrix), state_bytes(b.matrix))

    def test_wrong_method_role_LR_WD_and_missing_states_rejected_before_load(self):
        model = SyntheticParameters()
        result = route(model, "adamuon_author_bf16")
        base = dict(opt={}, opt_muon={}, **{CHECKPOINT_KEY: checkpoint_manifest(result)})
        original = copy.deepcopy(model)
        for field, value in (("method", "muon_matched"), ("matrix_lr_mult", 4.),
                             ("matrix_weight_decay", .1), ("parameters", [])):
            bad = copy.deepcopy(base)
            bad[CHECKPOINT_KEY][field] = value
            with self.assertRaises(ValueError):
                validate_optimizer_checkpoint(bad, result.manifest)
            self.same_parameters(model, original)
        for key in (CHECKPOINT_KEY, "opt", "opt_muon"):
            bad = copy.deepcopy(base)
            del bad[key]
            with self.assertRaises(ValueError):
                validate_optimizer_checkpoint(bad, result.manifest)
        with self.assertRaises(ValueError):
            validate_optimizer_checkpoint(base, None)
        validate_optimizer_checkpoint({}, None)

    def test_author_None_preflight_prevents_AdamW_or_matrix_writes(self):
        model = SyntheticParameters()
        result = route(model, "adamuon_author_bf16")
        step(model, result, 0)
        before = copy.deepcopy(model)
        adamw_before = copy.deepcopy(result.adamw.state_dict())
        matrix_before = copy.deepcopy(result.matrix.state_dict())
        gradients(model, 1)
        model.body.weight.grad = None
        with self.assertRaisesRegex(ValueError, "None"):
            result.validate_before_step()
        self.same_parameters(model, before)
        adamw_after = result.adamw.state_dict()
        self.assertEqual(adamw_before["param_groups"], adamw_after["param_groups"])
        for key, state in adamw_before["state"].items():
            for field, value in state.items():
                self.assertTrue(torch.equal(value.reshape(-1).view(torch.uint8),
                                            adamw_after["state"][key][field].reshape(-1).view(torch.uint8)))
        for key, state in matrix_before["state"].items():
            for field, value in state.items():
                if isinstance(value, torch.Tensor):
                    self.assertTrue(torch.equal(value, result.matrix.state_dict()["state"][key][field]))

    def test_matrix_WD_override_does_not_modify_special_or_head_groups(self):
        model = SyntheticParameters()
        result = route(model, "muon_matched", matrix_weight_decay=.02)
        self.assertEqual(result.matrix.param_groups[0]["weight_decay"], .02)
        self.assertEqual([g["weight_decay"] for g in result.adamw.param_groups], [.1, .07, .01, 0.])

    def test_incomplete_duplicate_or_non_FP32_matrix_configuration_rejected(self):
        for mode in ("duplicate", "missing"):
            model = SyntheticParameters()
            groups = model.param_groups(.001)
            if mode == "duplicate":
                groups[1]["params"].append(model.body.weight)
            else:
                groups[0]["params"] = []
            with patch.object(model, "param_groups", return_value=groups):
                with self.assertRaises(ValueError):
                    route(model, "muon_matched")
        model = SyntheticParameters()
        model.body.weight.data = model.body.weight.detach().to(torch.bfloat16)
        with self.assertRaises(ValueError):
            route(model, "muon_matched")

    def test_CLI_choices_and_early_trainer_rejection_require_no_dataset_or_model(self):
        from tinylm import cli
        with patch.object(sys, "argv", ["tinylm", "train", "--help"]):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), self.assertRaises(SystemExit) as cm:
                cli.main()
            self.assertEqual(cm.exception.code, 0)
        for method in METHODS:
            self.assertIn(method, buffer.getvalue())
        self.assertIn("--matrix-lr-mult", buffer.getvalue())
        from tinylm.train.trainer import train
        arguments = dict(preset="unused", arch="dense", data="never-read", n_tokens=0,
                         steps=0, micro_bs=1, seq=1, accum=1, lr=.001, eval_every=1)
        for method in METHODS:
            with self.assertRaisesRegex(ValueError, "matrix-lr-mult"):
                train(**arguments, optimizer=method)
            with self.assertRaisesRegex(ValueError, "legacy only"):
                train(**arguments, optimizer=method, matrix_lr_mult=2., muon_lr_mult=7.)
        with self.assertRaisesRegex(ValueError, "explicit experimental"):
            train(**arguments, optimizer="muon", matrix_lr_mult=2.)

    def test_exported_checkpoint_manifest_is_independent_of_future_changes(self):
        result = route(SyntheticParameters(), "adamuon_author_bf16")
        exported = checkpoint_manifest(result)
        exported["parameters"][0]["name"] = "changed"
        self.assertNotEqual(exported, result.manifest)

    def test_Nor_author_manifest_and_None_tail_keep_matched_auxiliary_AdamW(self):
        model = SyntheticParameters()
        result = route(model, "normuon_author_fp32")
        self.assertEqual(result.manifest["matrix_scale"], "AUTHOR_JORDAN;LEGACY_MUON_SCALE_NOT_APPLIED")
        self.assertTrue(result.manifest["matrix_gradient_mutation"])
        self.assertIn("NONE_CONTINUES", result.manifest["state_rule"])
        self.assertIn("NOT_AUTHOR_AUX_ADAM_EPS_1E-10", result.manifest["auxiliary_reference"])
        self.assertTrue(all(group["eps"] == 1e-8 for group in result.adamw.param_groups))
        step(model, result, 0)
        before = model.body.weight.detach().clone()
        gradients(model, 1)
        model.body.weight.grad = None
        result.validate_before_step()
        result.adamw.step(); result.matrix.step()
        self.assertIsNotNone(model.body.weight.grad)
        self.assertFalse(torch.equal(before, model.body.weight))
        self.assertEqual(result.matrix.state_dict()["author_contract"]["completed_steps"], 2)

    def test_Nor_author_nonfinite_preflight_preserves_AdamW_matrix_and_weights(self):
        from scripts.test_normuon_author import tensors_same
        model = SyntheticParameters()
        result = route(model, "normuon_author_fp32")
        step(model, result, 0)
        before = copy.deepcopy(model)
        old_adamw, old_matrix = copy.deepcopy(result.adamw.state_dict()), copy.deepcopy(result.matrix.state_dict())
        gradients(model, 1)
        model.body.weight.grad[0, 0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite differs"):
            result.validate_before_step()
        self.same_parameters(model, before)
        self.assertTrue(tensors_same(old_adamw, result.adamw.state_dict()))
        self.assertTrue(tensors_same(old_matrix, result.matrix.state_dict()))

    def test_Nor_author_matrix_checkpoint_precheck_is_pure_and_rejects_missing_state(self):
        from scripts.test_normuon_author import tensors_same
        first = SyntheticParameters()
        a = route(first, "normuon_author_fp32")
        step(first, a, 0)
        saved = dict(model=copy.deepcopy(first.state_dict()), opt=copy.deepcopy(a.adamw.state_dict()),
            opt_muon=copy.deepcopy(a.matrix.state_dict()), **{CHECKPOINT_KEY: checkpoint_manifest(a)})
        untouched = copy.deepcopy(saved)
        second = SyntheticParameters()
        b = route(second, "normuon_author_fp32")
        before = copy.deepcopy(second)
        validate_optimizer_checkpoint(saved, b.manifest, route=b)
        self.assertTrue(tensors_same(saved, untouched))
        self.assertFalse(b.matrix.state); self.assertFalse(b.adamw.state)
        bad = []
        item = copy.deepcopy(saved); item["opt_muon"]["state"].clear(); bad.append(item)
        item = copy.deepcopy(saved); item["opt_muon"]["author_contract"]["completed_steps"] = True; bad.append(item)
        item = copy.deepcopy(saved)
        value = next(iter(item["opt_muon"]["state"].values()))
        value["second_momentum_buffer"] = value["second_momentum_buffer"].bfloat16()
        bad.append(item)
        for item in bad:
            with self.assertRaises(ValueError):
                validate_optimizer_checkpoint(item, b.manifest, route=b)
            self.same_parameters(second, before)
            self.assertFalse(b.matrix.state); self.assertFalse(b.adamw.state)
        with self.assertRaisesRegex(ValueError, "constructed matched route"):
            validate_optimizer_checkpoint(saved, b.manifest)


if __name__ == "__main__":
    unittest.main()
