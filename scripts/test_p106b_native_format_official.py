#!/usr/bin/env python3
"""새 공식 평가 접점의 격리 CPU 회귀. 실제 모델과 평가 자료는 열지 않는다."""
from __future__ import annotations
import ast
import base64
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_format_official as d


class Budget:
    def __init__(self, seconds=600, deadline_epoch=None, *, started=None, reserve=120):
        self.started = time.monotonic() if started is None else started
        self.end = time.monotonic() + seconds
        self.reserve = reserve
    def remaining(self):
        return self.end - time.monotonic()
    def check(self, stage):
        if self.remaining() <= 0:
            raise TimeoutError(stage)


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(d.canonical(value))
    return dict(path=name, sha256=d.digest(path))


@dataclass
class Cfg:
    n_layers: int = 14
    dim: int = 768
    vocab_size: int = 32768
    max_seq_len: int = 1024
    grad_checkpoint: bool = True
    mtp_aux: bool = False
    tie_mlp: bool = False


def state():
    child = dict(arm="fmt_normuon", corpus="format", optimizer="normuon", source_sha256="D" * 64,
        profile_sha256="E" * 64, pair_complete_sha256="F" * 64, scratch_core_sha256=d.training.CORE,
        final_core_sha256="B" * 64, checkpoint="runs/ckpt/new_fixture.pt", checkpoint_sha256="C" * 64,
        cfg=asdict(Cfg()), updates=2289, totals=dict(targets=300023808, x_tokens=300023808),
        quantization_route=copy.deepcopy(d.ROUTE), status="TRAIN2289_COMPLETE", synthetic=False, original_weights_copied=False)
    return dict(source_identity=dict(sha256="A" * 64, files={}), profile_sha256="1" * 64,
        profile=dict(arm="fmt_normuon", cleanup_reserve_sec=120), train=child,
        train_spec=dict(path="test_result/evidence/train/report.json", sha256="2" * 64), task_specs=[])


def payload(s):
    return dict(model={}, cfg=copy.deepcopy(s["train"]["cfg"]), step=2289,
        tokenizer_sha256=d.training.native.TOKENIZER_SHA, tokenizer_lineage="chat32",
        quantization_route=copy.deepcopy(d.ROUTE), experiment=d.training.checkpoint_experiment(s["train"]))


def route():
    return dict(mode="ternary", metadata=copy.deepcopy(d.ROUTE), tlinear_instances=2,
        owned_tlinear_instances=2, refreshed_tlinear_instances=2,
        forward_methods=["_guarded_forward"], refresh_methods=["_ternary_refresh"])


def oracle():
    lengths = [1, 2, 3, 4, 1, 2, 3, 4]
    def row():
        return dict(gather=[-2., False], full_label=[-2., False], close=True)
    blocks = [dict(lengths=lengths, labels=[[1] * n for n in lengths], rows=[row() for _ in lengths])]
    blocks += [dict(lengths=[n], labels=[[1] * n], rows=[row()]) for n in lengths]
    return dict(status="CANARY_COMPLETE", batch_size=8, requests=[list(c) for c in d.CASES],
        atol=d.ATOL, rtol=d.RTOL, oracle_blocks=blocks,
        batch_vs_separate=[dict(batched=[-2., False], separate=[-2., False], close=True) for _ in lengths], quality_claim=False)


def worker(s, mode="canary"):
    return dict(schema=d.SCHEMA, mode=mode, synthetic=False, source_sha256=s["source_identity"]["sha256"],
        profile_sha256=s["profile_sha256"], arm=s["profile"]["arm"], training_report_sha256=s["train_spec"]["sha256"],
        checkpoint_sha256=s["train"]["checkpoint_sha256"], policy=d.policy(), contract=copy.deepcopy(d.CONTRACT),
        framework_commit=d.assets.COMMIT, data_manifest_sha256=d.assets.MANIFEST_SHA,
        optimizer_updates=0, checkpoint_writes=0, models_loaded=1, canary=oracle(), actual_counts={}, quality_claim=False,
        status={"canary": "CANARY_COMPLETE", "cost": "LIMITED_COST_DIAGNOSTIC", "full": "OFFICIAL_CORE6_FULL_COMPLETE"}[mode],
        model_proof=dict(checkpoint_sha256=s["train"]["checkpoint_sha256"], cfg=s["train"]["cfg"],
            cpu_and_gpu_core_sha256=s["train"]["final_core_sha256"], final_core_sha256=s["train"]["final_core_sha256"],
            contract=copy.deepcopy(d.CONTRACT), updates=2289, targets=300023808, original_training_weights_copied=False,
            scratch_core_sha256=d.training.CORE, state_header_sha256="A" * 64, state_keys=2,
            cpu_key_shape_dtype_layout_alias_verified=True, all_checkpoint_floats_finite=True,
            route=route(), final_route=route()))


def observed(code=0, **changes):
    value = dict(actual_child_exit=code, launch_state="STARTED", forced_cleanup=False, original_error=None,
        cleanup_errors=[], child_group_quiescent=True, stdout_complete=True, subreaper_restored=True)
    value.update(changes)
    return value


class ImportTests(unittest.TestCase):
    def test_import_and_missing_cp_check_are_stdlib_only(self):
        code = """import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','tokenizers','transformers','datasets','lm_eval'}:
   raise AssertionError('모델과 평가 backend import 금지')
sys.meta_path.insert(0,Block())
module=runpy.run_path(sys.argv[1],run_name='fixture_import')
assert module['main'](['--check-only'])==8
assert not any(name.split('.')[0] in {'torch','tokenizers','lm_eval'} for name in sys.modules)
"""
        child = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(Path(d.__file__).resolve())],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertIn('"returncode": 8', child.stdout)

    def test_existing_official_defaults_are_preserved(self):
        self.assertEqual(d.official.MODELS, ("native595-f", "native595-q", "new595-broad-f", "falcon90m"))
        self.assertEqual(d.official.DEADLINE, datetime(2026, 10, 23, 7, 30, tzinfo=timezone.utc).timestamp())
        self.assertEqual(d.policy(), d.official.policy())
        self.assertEqual((d.ATOL, d.RTOL), (1e-5, 1e-4))
        self.assertEqual((d.ITEMS, d.REQUESTS), (19965, 67106))

    def test_worker_bootstrap_uses_own_file_and_no_old_endpoint(self):
        tree = ast.parse(Path(d.__file__).read_text(encoding="utf-8"))
        names = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(n.func, ast.Attribute) and n.func.attr in
            ("research_adapter", "selected_runtime", "routed_runtime", "validate_payload")
            and isinstance(n.func.value, ast.Name) and n.func.value.id in ("official", "training", "native") for n in names))
        main_source = Path(d.__file__).read_text(encoding="utf-8")
        self.assertIn('str(Path(__file__).resolve())', main_source)
        self.assertNotIn("inference_mode(", main_source)


class PayloadTests(unittest.TestCase):
    def test_new_normuon_complete_payload(self):
        s = state()
        d.validate_payload(payload(s), Cfg(), s)
        self.assertEqual(payload(s)["experiment"]["targets"], 300023808)

    def test_step_cfg_tokenizer_lineage_and_route_are_strict(self):
        s = state()
        for key, value in (("step", 2281), ("step", True), ("cfg", {}), ("tokenizer_sha256", "0" * 64),
                ("tokenizer_lineage", "legacy"), ("quantization_route", {}), ("experiment", {})):
            wrong = payload(s); wrong[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                d.validate_payload(wrong, Cfg(), s)


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_official_metadata_", dir="/tmp")
        self.root = Path(self.tmp.name); self.stack = ExitStack(); self.s = state()
        self.stack.enter_context(patch.object(d, "ROOT", self.root))
        self.stack.enter_context(patch.object(d, "source_identity", return_value=self.s["source_identity"]))
        self.train_state = dict(source_identity=dict(sha256="D" * 64))
        self.stack.enter_context(patch.object(d.training, "metadata", return_value=self.train_state))
        self.closed = self.stack.enter_context(patch.object(d.training, "read_closed", side_effect=lambda *args: dict(worker=self.s["train"])))
        checkpoint = self.root / self.s["train"]["checkpoint"]
        checkpoint.parent.mkdir(parents=True); checkpoint.write_bytes(b"CPU CP fixture; model0")
        self.s["train"]["checkpoint_sha256"] = d.digest(checkpoint)
        official_assets = self.root / "data_cache/official_assets"
        manifest = put(self.root, "data_cache/official_assets/manifest.json", dict(files=[]))
        self.stack.enter_context(patch.object(d.assets, "ASSETS", official_assets))
        self.stack.enter_context(patch.object(d.assets, "MANIFEST_SHA", manifest["sha256"]))
        self.stack.enter_context(patch.object(d.assets, "task_specs", return_value=[]))
        self.stack.enter_context(patch.object(d.assets, "verify_assets"))
        self.stack.enter_context(patch.object(d.adapter, "verify_harness_source", return_value=dict(pinned=True)))
        self.profile = dict(schema=d.PROFILE, root_approved=True, source_sha256="A" * 64,
            official_policy=d.policy(), numerical_contract=copy.deepcopy(d.CONTRACT), deadline=d.END.isoformat(),
            cleanup_reserve_sec=120, entry_free_mib=13000, training_profile=dict(path="train_profile.json", sha256="E" * 64),
            training_f4=dict(path="train_f4.json", sha256="F" * 64), training_source_sha256="D" * 64,
            closed_train=self.s["train_spec"], arm=self.s["profile"]["arm"])
        self.args = SimpleNamespace(source_sha256="A" * 64, profile="profile.json", profile_sha256=None)
        self.refresh()
    def tearDown(self): self.stack.close(); self.tmp.cleanup()
    def refresh(self): self.args.profile_sha256 = put(self.root, self.args.profile, self.profile)["sha256"]
    def test_complete_metadata_uses_new_arm_and_train_closure_without_model(self):
        value = d.metadata(self.args, Budget())
        self.assertEqual(value["train"]["optimizer"], "normuon")
        self.assertEqual(self.closed.call_args.args[2:], ("fmt_normuon", "train"))
    def test_missing_actual_cp_is_hold(self):
        self.s["train"]["checkpoint"] = "runs/ckpt/missing.pt"
        with self.assertRaises(d.Hold): d.metadata(self.args, Budget())
    def test_changed_actual_cp_is_error(self):
        (self.root / self.s["train"]["checkpoint"]).write_bytes(b"CPU CP changed")
        with self.assertRaisesRegex(ValueError, "CP SHA"): d.metadata(self.args, Budget())
    def test_partial_updates_targets_or_synthetic_cannot_be_complete(self):
        for key, value in (("updates", 2281), ("updates", True), ("totals", dict(targets=298975232, x_tokens=298975232)),
                ("synthetic", True), ("original_weights_copied", True), ("quantization_route", {})):
            original = copy.deepcopy(self.s["train"])
            self.s["train"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): d.metadata(self.args, Budget())
            self.s["train"] = original
    def test_profile_scope_deadline_tolerance_and_source_are_not_relaxed(self):
        original = copy.deepcopy(self.profile)
        for key, value in (("deadline", "2026-10-27T08:00:00+00:00"), ("cleanup_reserve_sec", 119),
                ("root_approved", False), ("numerical_contract", dict(d.CONTRACT, atol=1e-3)),
                ("source_sha256", "0" * 64), ("training_source_sha256", "0" * 64)):
            self.profile = dict(original, **{key: value}); self.refresh()
            with self.subTest(key=key), self.assertRaises(ValueError): d.metadata(self.args, Budget())


class AliasTests(unittest.TestCase):
    def test_parameter_aliases_are_structural_and_order_independent(self):
        first, second = object(), object()
        model = SimpleNamespace(named_parameters=lambda remove_duplicate: [("head.weight", first), ("x", second), ("emb.weight", first)])
        self.assertEqual(d.aliases(model), [["emb.weight", "head.weight"]])

    def test_original_cpu_state_validator_rejects_keys_shapes_dtype_and_alias_conflicts(self):
        class Tensor:
            def __init__(self, values=(1., 2.), *, shape=(1, 2), dtype="fp32", layout="strided", device="cpu"):
                self.values, self.shape, self.dtype, self.layout = values, shape, dtype, layout
                self.device = SimpleNamespace(type=device)
        shared = Tensor()
        model = SimpleNamespace(state_dict=lambda: {"emb.weight": shared, "head.weight": shared},
            named_parameters=lambda remove_duplicate: [("emb.weight", shared), ("head.weight", shared)])
        torch = SimpleNamespace(Tensor=Tensor, equal=lambda left, right: left.values == right.values)
        supplied = dict(model={"emb.weight": Tensor(), "head.weight": Tensor()})
        d.training.native.validate_cpu_state(model, supplied, torch)
        for kind in ("key", "shape", "dtype", "layout", "device", "alias"):
            values = dict(model={"emb.weight": Tensor(), "head.weight": Tensor()})
            if kind == "key": del values["model"]["head.weight"]
            if kind == "shape": values["model"]["head.weight"].shape = (2, 1)
            if kind == "dtype": values["model"]["head.weight"].dtype = "bf16"
            if kind == "layout": values["model"]["head.weight"].layout = "sparse"
            if kind == "device": values["model"]["head.weight"].device.type = "cuda"
            if kind == "alias": values["model"]["head.weight"].values = (3., 4.)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                d.training.native.validate_cpu_state(model, values, torch)

    def test_live_contract_rejects_anneal_tf32_mtp_dtype_and_stale_cache(self):
        class Linear:
            def __init__(self):
                self.weight = SimpleNamespace(_version=2)
                self._wq = SimpleNamespace(dtype="fp32")
            def _guarded_forward(self): pass
            def _ternary_refresh(self): pass
            forward = _guarded_forward
            refresh_quant = _ternary_refresh
        module = Linear()
        model = SimpleNamespace(training=False, cfg=SimpleNamespace(mtp_aux=False), _quant_frozen=True,
            _anneal=1., parameters=lambda: [SimpleNamespace(dtype="fp32")])
        current = SimpleNamespace(mode="ternary", metadata=copy.deepcopy(d.ROUTE), linears=[module],
            _versions={id(module): 2}, assert_active=lambda: None)
        torch = SimpleNamespace(float32="fp32", isfinite=lambda value: SimpleNamespace(all=lambda: True),
            backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=False)),
                cudnn=SimpleNamespace(allow_tf32=False)))
        runtime = dict(torch=torch, model=model, route=current, quantization_route=copy.deepcopy(d.ROUTE))
        self.assertEqual(d.live_contract(runtime)["refreshed_tlinear_instances"], 1)
        for owner, attribute, value in ((model, "training", True), (model, "_quant_frozen", False),
                (model, "_anneal", 0.), (model.cfg, "mtp_aux", True), (torch.backends.cuda.matmul, "allow_tf32", True),
                (module._wq, "dtype", "bf16")):
            with self.subTest(attribute=attribute), patch.object(owner, attribute, value), self.assertRaises(ValueError):
                d.live_contract(runtime)
        current._versions[id(module)] = 1
        with self.assertRaises(ValueError): d.live_contract(runtime)


class PayloadAdditionalTests(unittest.TestCase):

    def test_no_optimizer_or_partial_checkpoint_keys(self):
        s = state()
        for kind in ("extra", "missing"):
            wrong = payload(s)
            if kind == "extra": wrong["optimizer"] = {}
            else: del wrong["model"]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                d.validate_payload(wrong, Cfg(), s)

    def test_same_numeric_value_cannot_replace_boolean_cfg(self):
        s = state(); wrong = payload(s); wrong["cfg"]["mtp_aux"] = 0
        with self.assertRaises(ValueError): d.validate_payload(wrong, Cfg(), s)

    def test_parent_copy_and_wrong_core_experiment_are_rejected(self):
        s = state()
        for key, value in (("original_training_weights_copied", True), ("core_sha256", "0" * 64),
                ("updates", 2281), ("targets", 298975232)):
            wrong = payload(s); wrong["experiment"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                d.validate_payload(wrong, Cfg(), s)


class CanaryTests(unittest.TestCase):
    def test_original_tolerance_and_eight_rows(self):
        d.validate_canary(oracle())
        wrong = oracle(); wrong["rtol"] = 1e-3
        with self.assertRaises(ValueError): d.validate_canary(wrong)

    def test_recorded_true_does_not_hide_numerical_error(self):
        wrong = oracle(); wrong["oracle_blocks"][0]["rows"][2]["full_label"][0] = -3.
        with self.assertRaises(ValueError): d.validate_canary(wrong)

    def test_batch_and_singleton_drift_or_missing_rows_fail(self):
        for kind in ("drift", "missing", "greedy", "nan", "positive"):
            wrong = oracle()
            if kind == "drift": wrong["batch_vs_separate"][0]["separate"][0] = -3.
            if kind == "missing": wrong["oracle_blocks"].pop()
            if kind == "greedy": wrong["batch_vs_separate"][0]["separate"][1] = True
            if kind == "nan": wrong["batch_vs_separate"][0]["separate"][0] = float("nan")
            if kind == "positive": wrong["batch_vs_separate"][0]["separate"][0] = .1
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.validate_canary(wrong)

    def test_live_canary_calls_eight_batch_and_singletons_then_restores(self):
        class Scorer:
            runtime = dict(cfg=SimpleNamespace(vocab_size=32))
            forward = object()
            def __call__(self, batch): return [(-float(i + 1), False) for i in batch["ids"]]
        class LM:
            def __init__(self): self.core = SimpleNamespace(batch_size=8, score_batch=Scorer())
            def loglikelihood(self, requests, **kwargs):
                result = []
                for start in range(0, len(requests), self.core.batch_size):
                    ids = list(range(start, min(len(requests), start + self.core.batch_size)))
                    result.extend(self.core.score_batch(dict(ids=ids, lengths=[i + 1 for i in ids], labels=[[1] * (i + 1) for i in ids])))
                return result
        module = ModuleType("lm_eval.api.instance")
        module.Instance = lambda **kwargs: SimpleNamespace(**kwargs)
        lm = LM(); original = lm.core.score_batch
        with patch.dict(sys.modules, {"lm_eval.api.instance": module}), patch.object(d.adapter, "direct_label_oracle",
                side_effect=lambda torch, forward, batch, vocab: [(-float(i + 1), False) for i in batch["ids"]]) as direct:
            value = d.canary(lm, object())
        self.assertEqual([len(block["rows"]) for block in value["oracle_blocks"]], [8] + [1] * 8)
        self.assertEqual(direct.call_count, 9)
        self.assertIs(lm.core.score_batch, original)
        self.assertEqual(lm.core.batch_size, 8)

    def test_canary_error_restores_owned_callback(self):
        module = ModuleType("lm_eval.api.instance"); module.Instance = lambda **kwargs: kwargs
        scorer = SimpleNamespace()
        lm = SimpleNamespace(core=SimpleNamespace(batch_size=8, score_batch=scorer),
            loglikelihood=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("원 오류")))
        with patch.dict(sys.modules, {"lm_eval.api.instance": module}), self.assertRaises(OSError):
            d.canary(lm, object())
        self.assertIs(lm.core.score_batch, scorer)
        self.assertEqual(lm.core.batch_size, 8)

    def test_inconsistent_pair_blocks_and_empty_target_masks_fail(self):
        for kind in ("pair", "empty", "pad"):
            wrong = oracle()
            if kind == "pair":
                wrong["batch_vs_separate"][0].update(batched=[-3., False], separate=[-3., False])
            if kind == "empty": wrong["oracle_blocks"][0]["labels"][0] = [-100]
            if kind == "pad": wrong["oracle_blocks"][0]["labels"][0] += [1]
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.validate_canary(wrong)


class RawTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_official_raw_", dir="/tmp")
        self.root = Path(self.tmp.name); self.s = state(); self.budget = Budget()
        self.spec = dict(task="piqa", data_sha256="A" * 64, official_yaml_sha256="B" * 64, dataset_revision="C" * 40)
    def tearDown(self): self.tmp.cleanup()
    def rows(self, count=2):
        rows = []
        for i in range(count):
            doc = dict(label=i % 2, text="원 label 보존")
            rows.append(dict(doc_id=i, doc=doc, filtered_resps=[[-1., False], [-2., False]],
                acc=int(i % 2 == 0), acc_norm=int(i % 2 == 1), native_format_recount=dict(self.spec,
                    doc_sha256=d.sha(doc), choices=["X", "긴 선택지"], gold=i % 2)))
        return rows
    def test_original_labels_character_norm_and_baselines(self):
        result = d.audit_rows(self.rows(), 2, self.spec)
        self.assertEqual((result["correct"], result["correct_norm"], result["random_expected_correct"]), (1, 1, 1.))
        self.assertEqual(result["posthoc_label_counts"], {0: 1, 1: 1})
        self.assertIn("DIAGNOSTIC_ONLY", result["baseline_policy"])

    def test_dropped_reordered_or_incomplete_choices_fail(self):
        for kind in ("dropped", "order", "choice", "label", "greedy", "sha", "doc", "metric"):
            rows = self.rows()
            if kind == "dropped": rows.pop()
            if kind == "order": rows.reverse()
            if kind == "choice": rows[0]["filtered_resps"].pop()
            if kind == "label": rows[0]["native_format_recount"]["gold"] = True
            if kind == "greedy": rows[0]["filtered_resps"][0][1] = 0
            if kind == "sha": rows[0]["native_format_recount"]["data_sha256"] = "0" * 64
            if kind == "doc": rows[0]["doc"]["label"] = 9
            if kind == "metric": rows[0]["acc"] = 0
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.audit_rows(rows, 2, self.spec)

    def test_shards_preserve_utf8_and_reject_same_length_corruption(self):
        writer = d.ShardWriter(self.root, "samples", limit=1000)
        for row in self.rows(4): writer.append(row)
        manifest = writer.close(lineage=dict(synthetic=True))
        self.assertEqual(len(list(d.manifests_rows(self.root, manifest, self.budget))), 4)
        self.assertTrue(all(spec["bytes"] < 20_000_000 for spec in manifest["shards"]))
        path = self.root / manifest["shards"][0]["path"]
        raw = path.read_bytes(); path.write_bytes(raw.replace(b'"doc_id":0', b'"doc_id":9'))
        with self.assertRaises(ValueError): list(d.manifests_rows(self.root, manifest, self.budget))

    def test_full_worker_recounts_items_requests_and_official_scores(self):
        self.s["task_specs"] = [self.spec]
        value = worker(self.s, "full"); rows = self.rows()
        writer = d.ShardWriter(self.root, "piqa_samples", limit=1000)
        for row in rows: writer.append(row)
        samples = writer.close(lineage=dict(synthetic=True))
        writer = d.ShardWriter(self.root, "token_lengths", limit=1000)
        for i in range(4): writer.append(dict(index=i, context_tokens=1, continuation_tokens=1,
            truncated_context_tokens=0, key_sha256="A" * 64))
        lengths = writer.close(lineage=dict(synthetic=True))
        value.update(actual_counts=dict(piqa=2), task_specs=self.s["task_specs"], sample_manifests=dict(piqa=samples),
            independent_audits=dict(piqa=d.audit_rows(rows, 2, self.spec)), lengths_manifest=lengths,
            token_lengths_summary=dict(requests=4, context_truncated_requests=0, context_tokens_removed=0, continuation_tokens=4),
            task_evaluation_seconds=dict(piqa=.1),
            official_results=dict(piqa=dict(results=dict(piqa={"acc,none": .5, "acc_norm,none": .5}))))
        with patch.object(d.official, "TASK_COUNTS", dict(piqa=2)), patch.object(d, "ITEMS", 2), patch.object(d, "REQUESTS", 4):
            d.validate_worker(value, self.s, "full", self.root, self.budget)
            saved = json.loads(d.canonical(value))
            d.validate_worker(saved, self.s, "full", self.root, self.budget)
            wrong = copy.deepcopy(value); wrong["official_results"]["piqa"]["results"]["piqa"]["acc,none"] = 0.
            with self.assertRaises(ValueError): d.validate_worker(wrong, self.s, "full", self.root, self.budget)
            with patch.object(d, "REQUESTS", 5), self.assertRaises(ValueError):
                d.validate_worker(value, self.s, "full", self.root, self.budget)
            wrong = copy.deepcopy(value); del wrong["official_results"]["piqa"]["results"]["piqa"]["acc_norm,none"]
            with self.assertRaises(ValueError): d.validate_worker(wrong, self.s, "full", self.root, self.budget)

    def test_route_metadata_and_refresh_count_must_be_live(self):
        value = worker(self.s)
        d.validate_worker(value, self.s, "canary", self.root, self.budget)
        for key, changed in (("owned_tlinear_instances", 0), ("refreshed_tlinear_instances", 0),
                ("forward_methods", ["forward"]), ("metadata", {})):
            wrong = copy.deepcopy(value); wrong["model_proof"]["final_route"][key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                d.validate_worker(wrong, self.s, "canary", self.root, self.budget)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.s = state(); self.budget = Budget(4000)
        self.value = dict(schema=d.ADMISSION, source_sha256="A" * 64, profile_sha256="1" * 64,
            canary=dict(sha256="C" * 64), cost=dict(sha256="D" * 64, actual_parent_wall_sec=20.))
        self.args = SimpleNamespace(mode="full", admission="admission.json", admission_sha256="A" * 64)
    def test_per_task_forecast_includes_actual_parent_overhead(self):
        timing = {name: 1. for name in d.official.TASK_COUNTS}; timing["hellaswag"] = 2.
        cost = dict(worker=dict(task_evaluation_seconds=timing))
        with patch.object(d, "read_ref", return_value=self.value), patch.object(d, "read_closed", side_effect=[{}, cost]):
            result = d.admission(self.args, self.s, self.budget)
        expected = 1.5 * (sum(d.official.TASK_COUNTS[n] * t / 32 for n, t in timing.items()) + 13.) + 60
        self.assertAlmostEqual(result["work_forecast_seconds"], expected)
        self.assertEqual(result["cleanup_reserve_seconds"], 120)

    def test_missing_canary_is_hold_before_model(self):
        self.args.admission = None
        with self.assertRaises(d.Hold): d.admission(self.args, self.s, self.budget)

    def test_insufficient_whole_window_is_hold(self):
        cost = dict(worker=dict(task_evaluation_seconds={n: 1. for n in d.official.TASK_COUNTS}))
        self.budget.end = time.monotonic() + 200
        with patch.object(d, "read_ref", return_value=self.value), patch.object(d, "read_closed", side_effect=[{}, cost]), self.assertRaises(d.Hold):
            d.admission(self.args, self.s, self.budget)

    def test_profile_source_and_actual_exit_cannot_be_substituted(self):
        self.value["profile_sha256"] = "0" * 64
        with patch.object(d, "read_ref", return_value=self.value), self.assertRaises(ValueError):
            d.admission(self.args, self.s, self.budget)
        with self.assertRaises(ValueError): d.read_closed(dict(actual_supervisor_exit=True), self.s, "canary", self.budget)


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_official_closure_", dir="/tmp")
        self.root = Path(self.tmp.name); self.stack = ExitStack()
        self.stack.enter_context(patch.object(d, "ROOT", self.root))
        self.s = state(); self.budget = Budget()
        self.directory = self.root / "test_result/evidence/closed"
        self.directory.mkdir(parents=True)
        child = worker(self.s)
        ref = put(self.root, "test_result/evidence/closed/worker.json", child)
        writer = d.ShardWriter(self.directory / "stdout", "stdout", limit=1000)
        raw = "실제 자식 출력의 합성 원형".encode()
        writer.append(dict(encoding="BASE64_RAW_STDOUT", bytes=base64.b64encode(raw).decode()))
        manifest = writer.close(lineage={})
        self.report = dict(schema=d.SCHEMA, mode="canary", returncode=0, source_sha256="A" * 64,
            profile_sha256="1" * 64, worker=child, worker_sha256=ref["sha256"],
            whole_parent_seconds=1., supervision=observed(stdout_manifest=manifest,
                stdout_bytes=len(raw), stdout_sha256=d.hashlib.sha256(raw).hexdigest().upper()))
        d.supervisor.append_terminal(self.directory, dict(event="OBSERVATION", returncode=0))
        self.refresh()
    def tearDown(self): self.stack.close(); self.tmp.cleanup()
    def refresh(self):
        self.spec = put(self.root, "test_result/evidence/closed/report.json", self.report)
        self.spec.update(terminal_sha256=d.digest(self.directory / "terminal.jsonl"), actual_supervisor_exit=0, actual_parent_wall_sec=2.)
    def test_real_root_exit_and_closed_stdout_are_required(self):
        result = d.read_closed(self.spec, self.s, "canary", self.budget)
        self.assertEqual(result["supervision"]["actual_child_exit"], 0)
        path = self.directory / "stdout/stdout_000000.jsonl"
        path.write_bytes(path.read_bytes().replace(b'"encoding"', b'"Encoding"'))
        with self.assertRaises(ValueError): d.read_closed(self.spec, self.s, "canary", self.budget)

    def test_later_terminal_veto_is_not_success(self):
        d.supervisor.append_terminal(self.directory, dict(event="TERMINAL_VETO", returncode=9))
        self.spec["terminal_sha256"] = d.digest(self.directory / "terminal.jsonl")
        with self.assertRaises(ValueError): d.read_closed(self.spec, self.s, "canary", self.budget)

    def test_forced_cleanup_residue_or_real_child8_are_not_promoted(self):
        for changed in (dict(forced_cleanup=True), dict(child_group_quiescent=False), dict(actual_child_exit=8),
                dict(cleanup_errors=[dict(type="OSError")]), dict(original_error=dict(type="TimeoutError")), dict(post_errors=[{}])):
            self.report["supervision"] = observed(**changed); self.refresh()
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                d.read_closed(self.spec, self.s, "canary", self.budget)

    def test_no_unobserved_parent_exit_or_shorter_wall(self):
        for field, value in (("actual_supervisor_exit", "ROOT_MUST_COLLECT"), ("actual_supervisor_exit", 9),
                ("actual_parent_wall_sec", .5), ("actual_parent_wall_sec", float("nan"))):
            wrong = dict(self.spec); wrong[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): d.read_closed(wrong, self.s, "canary", self.budget)


class ParentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_official_parent_", dir="/tmp")
        self.root = Path(self.tmp.name); (self.root / "test_result/evidence").mkdir(parents=True)
        self.stack = ExitStack(); self.s = state()
        for owner, name, value in ((d, "ROOT", self.root), (d.supervisor, "Budget", Budget),
                (d, "STARTED", time.monotonic())):
            self.stack.enter_context(patch.object(owner, name, value))
        self.stack.enter_context(patch.object(d, "metadata", return_value=self.s))
        self.stack.enter_context(patch.object(d, "admission", return_value={}))
        self.stack.enter_context(patch.object(d, "immutable"))
        self.stack.enter_context(patch.object(d, "validate_worker"))
        self.output = "test_result/evidence/" + d.PREFIX + "fixture"
        self.args = ["--execute", "--profile", "profile.json", "--profile-sha256", "1" * 64,
            "--source-sha256", "A" * 64, "--output", self.output]
    def tearDown(self): self.stack.close(); self.tmp.cleanup()
    def launch(self, command, output, budget):
        put(self.root, str((output / "worker.json").relative_to(self.root)), worker(self.s))
        self.command = command
        return observed()
    def run_main(self, **kwargs):
        with patch.object(d.training, "supervise", side_effect=self.launch), redirect_stdout(io.StringIO()):
            return d.main(**kwargs) if kwargs else d.main(self.args)
    def test_new_process_argv_reserves_parent_cleanup_and_uses_own_script(self):
        self.assertEqual(self.run_main(), 0)
        self.assertIn(str(Path(d.__file__).resolve()), self.command)
        self.assertIn("--worker", self.command); self.assertNotIn("--execute", self.command)
        inv = json.loads((self.root / self.output / "invocation.json").read_bytes())
        self.assertLess(inv["work_end"], d.STARTED + 600 - 119)

    def test_existing_namespace_is_preserved(self):
        path = self.root / self.output; path.mkdir()
        (path / "old.txt").write_text("원형", encoding="utf-8")
        self.assertEqual(self.run_main(), 9)
        self.assertEqual((path / "old.txt").read_text(encoding="utf-8"), "원형")
        self.assertFalse((path / "terminal.jsonl").exists())

    def test_print_delay_keeps_report0_but_appends_terminal_veto9(self):
        calls = []
        def delayed(*args, **kwargs):
            calls.append(args)
            if len(calls) == 1: raise TimeoutError("출력 지연")
        with patch.object(d, "print", side_effect=delayed, create=True):
            self.assertEqual(self.run_main(), 9)
        terminal = [json.loads(line) for line in (self.root / self.output / "terminal.jsonl").read_text().splitlines()]
        self.assertEqual([row["returncode"] for row in terminal], [0, 9])
        self.assertEqual(terminal[-1]["event"], "TERMINAL_VETO")

    def test_guard_restore_failure_vetoes_after_observation(self):
        @contextmanager
        def broken():
            yield
            raise OSError("신호 복구 실패")
        with patch.object(d.supervisor, "termination_guard", broken):
            self.assertEqual(self.run_main(), 9)
        lines = [json.loads(line) for line in (self.root / self.output / "terminal.jsonl").read_text().splitlines()]
        self.assertEqual([row["event"] for row in lines], ["OBSERVATION", "TERMINAL_VETO"])

    def test_forced_child_exit_is_preserved_and_parent9(self):
        with patch.object(d.training, "supervise", return_value=observed(-9, forced_cleanup=True,
                original_error=dict(type="TimeoutError"))), redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(self.args), 9)
        report = json.loads((self.root / self.output / "report.json").read_bytes())
        self.assertEqual(report["supervision"]["actual_child_exit"], -9)
        self.assertEqual(report["supervision"]["original_error"]["type"], "TimeoutError")
        self.assertEqual(report["returncode"], 9)

    def test_absolute_deadline_cannot_be_extended(self):
        self.args += ["--deadline", "2026-10-26T08:00:01+00:00"]
        self.assertEqual(self.run_main(), 9)
        self.assertFalse((self.root / self.output).exists())

    def test_unowned_worker_is_rejected_before_model(self):
        output = self.root / self.output; output.mkdir()
        inv = dict(parent_pid=-1, parent_starttime=0, source_sha256="A" * 64, profile_sha256="1" * 64,
            mode="canary", work_end=time.monotonic() + 400)
        put(self.root, str((output / "invocation.json").relative_to(self.root)), inv)
        self.args[0] = "--worker"
        self.args += ["--parent-started", str(time.monotonic()), "--work-end", str(inv["work_end"])]
        with patch.object(d, "execute_worker", side_effect=AssertionError("모델 금지")) as model:
            self.assertEqual(self.run_main(), 9)
        model.assert_not_called()


@unittest.skipUnless(sys.platform == "linux", "현재 소유 감독은 Linux 전용이다")
class ActualCPUChildren(unittest.TestCase):
    def run_owned(self, source, *, seconds=5, reserve=.1):
        with tempfile.TemporaryDirectory(prefix="native_official_owned_", dir="/tmp") as temporary:
            root = Path(temporary); output = root / "output"; output.mkdir()
            budget = Budget(seconds, reserve=reserve)
            with patch.object(d.training, "ROOT", root), patch.object(d.training, "path", side_effect=lambda name: root / name):
                result = d.training.supervise([str(Path(sys.executable).resolve()), "-I", "-B", "-c", source], output, budget)
            if "stdout_manifest" in result: d.verify(output / "stdout", result["stdout_manifest"])
            return result

    def test_actual_child0_is_closed(self):
        result = self.run_owned("print('CPU 실제 자식 종료0',flush=True)")
        self.assertEqual(result["actual_child_exit"], 0)
        self.assertTrue(d.training.supervision_ok(result))

    def test_actual_child8_stays8_and_parent_cannot_promote(self):
        result = self.run_owned("raise SystemExit(8)")
        self.assertEqual(result["actual_child_exit"], 8)
        self.assertFalse(d.training.supervision_ok(result))
        self.assertTrue(result["child_group_quiescent"])

    def test_actual_timeout_term_ignore_requires_kill_and_is9(self):
        result = self.run_owned("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); signal.signal(signal.SIGINT,signal.SIG_IGN); print('준비',flush=True); time.sleep(20)", seconds=5, reserve=4.6)
        self.assertTrue(result["forced_cleanup"])
        self.assertLess(result["actual_child_exit"], 0)
        self.assertTrue(result["child_group_quiescent"])
        self.assertFalse(d.training.supervision_ok(result))
        self.assertEqual(result["original_error"]["type"], "TimeoutError")

    def test_actual_leader0_with_live_descendant_is_not_success(self):
        source = """import os,signal,time
child=os.fork()
if child:
 print(child,flush=True)
 time.sleep(.1)
 os._exit(0)
signal.signal(signal.SIGTERM,signal.SIG_IGN)
signal.signal(signal.SIGINT,signal.SIG_IGN)
time.sleep(20)
"""
        result = self.run_owned(source, seconds=6)
        self.assertEqual(result["actual_child_exit"], 0)
        self.assertTrue(result["forced_cleanup"])
        self.assertTrue(result["child_group_quiescent"])
        self.assertFalse(d.training.supervision_ok(result))
        self.assertGreaterEqual(len(result["observed_descendants"]), 2)


if __name__ == "__main__":
    unittest.main()
