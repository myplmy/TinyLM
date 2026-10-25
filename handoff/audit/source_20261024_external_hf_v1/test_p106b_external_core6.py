"""Synthetic external Core6 admission/recount tests; no model, GPU or HF import."""
from __future__ import annotations

import builtins
import ast
from contextlib import redirect_stdout, contextmanager, nullcontext
import io
import json
from pathlib import Path
import runpy
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import diag_p106b_external_core6 as run


class ExternalContracts(unittest.TestCase):
    def test_scoped_hf_redirect_and_explicit_external_metadata_names(self):
        from scripts.check_hf_redirect import scan
        source = Path(run.__file__).read_text(encoding="utf-8")
        uses, imports_tinylm, error = scan(Path(run.__file__))
        self.assertIsNone(error)
        self.assertIn("transformers", uses)
        self.assertTrue(imports_tinylm)
        self.assertIn("sys.path.insert", source)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                self.assertNotIn(node.value.id, {"cfg", "config"})
        runtime = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "model_runtime")
        runtime_source = ast.get_source_segment(source, runtime)
        self.assertLess(runtime_source.index("import tinylm"), runtime_source.index("configure_hf_cache()"))
        self.assertLess(runtime_source.index("configure_hf_cache()"), runtime_source.index("from transformers import"))

    def test_source_import_and_check_only_never_import_heavy_libraries(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "tokenizers", "datasets", "lm_eval", "tinylm"}:
                raise AssertionError("unexpected heavy import: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            module = runpy.run_path(str(Path(run.__file__)), run_name="pure_external_import")
            self.assertEqual(module["TAG"], run.TAG)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(run.main(["--check-only"]), 0)
            value = json.loads(output.getvalue())
            self.assertEqual((value["status"], value["models"]), ("SOURCE_ONLY", 0))

    def test_holds_nested_qwen_before_any_model_or_assets(self):
        with self.assertRaisesRegex(run.AdmissionHold, "qwen3508 HOLD"):
            run.validate_execution("qwen3508", "canary", "2026-10-24T08:40:00+09:00", 300, now=0)

    def test_deadline_offset_bounds_and_whole_phase_fit(self):
        deadline = "2026-10-24T08:40:00+09:00"
        stop = run.LATEST_DEADLINE
        self.assertEqual(run.validate_execution("qwen06", "canary", deadline, 300, now=stop-301)["hard_cap_seconds"], 300)
        for mode, value, dt, now in (("canary", 299, deadline, 0), ("cost", 599, deadline, 0),
                ("full", 7201, deadline, 0), ("cost", 600, deadline, stop-599),
                ("canary", 300, "2026-10-24T08:41:00+09:00", 0),
                ("canary", 300, "2026-10-24T08:40:00", 0)):
            with self.subTest(mode=mode, value=value, dt=dt), self.assertRaises(run.AdmissionHold):
                run.validate_execution("qwen06", mode, dt, value, now=now)

    def test_forecast_enforces_model_and_deadline_budgets(self):
        admission = dict(hard_cap_seconds=100, deadline_epoch=200)
        run.admit_forecast(dict(forecast_seconds=99), admission, now=100)
        for forecast, now in ((101, 0), (99, 102)):
            with self.assertRaises(run.AdmissionHold):
                run.admit_forecast(dict(forecast_seconds=forecast), admission, now=now)

    def test_score_oracles_reject_length_nonfinite_greedy_and_positive(self):
        self.assertTrue(run.compare_scores([(-1., True)], [(-1.000001, True)])[0]["close"])
        for other in ([], [(float("nan"), True)], [(1., True)], [(-1., 1)], [(-1., False)], [(-2., True)]):
            with self.subTest(other=other), self.assertRaises(ValueError):
                run.compare_scores([(-1., True)], other)

    def test_actual_batch_property_is_used_and_restored_on_second_call_failure(self):
        class LM:
            batch_size_per_gpu = 7
            seen = []
            @property
            def batch_size(self): return self.batch_size_per_gpu
            def loglikelihood(self, requests, **kwargs):
                self.seen.append(self.batch_size)
                if self.batch_size == 2: raise RuntimeError("synthetic second batch error")
                return [(-1., True)]
        lm = LM()
        with self.assertRaises(RuntimeError): run.canary_batches(lm, ["synthetic"])
        self.assertEqual((lm.seen, lm.batch_size), ([1, 2], 7))

    def fixture_assets(self, root):
        directory = root / "HF/model"
        directory.mkdir(parents=True)
        for name, value in (("config.json", {"model_type": "qwen3"}), ("tokenizer.json", {}), ("tokenizer_config.json", {})):
            run.write_json(directory/name, value)
        (directory/"model.safetensors").write_bytes(b"synthetic-not-a-model")
        spec = dict(path="HF/model", model_type="qwen3", revision="fixture", weight="model.safetensors",
            weight_sha256=run.digest(directory/"model.safetensors"))
        return directory, spec

    def test_asset_identity_pins_weight_and_metadata_without_outside_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, spec = self.fixture_assets(root)
            with patch.object(run, "ROOT", root), patch.dict(run.REGISTRY, {"qwen06": spec}):
                assets = run.asset_identity("qwen06")
                self.assertEqual(set(assets["files"]), {"model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json"})
                (directory/"model.safetensors").write_bytes(b"changed")
                with self.assertRaisesRegex(run.AdmissionHold, "weight SHA"):
                    run.asset_identity("qwen06")

    def test_asset_symlink_must_resolve_inside_hf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, spec = self.fixture_assets(root)
            outside = root/"outside.json"
            run.write_json(outside, {})
            (directory/"added_tokens.json").symlink_to(outside)
            with patch.object(run, "ROOT", root), patch.dict(run.REGISTRY, {"qwen06": spec}):
                with self.assertRaisesRegex(run.AdmissionHold, "approved HF"):
                    run.asset_identity("qwen06")

    def test_write_once_size_limit_and_bounded_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.json"
            run.write_json(path, dict(a=1))
            self.assertEqual(run.read_json(path), dict(a=1))
            with self.assertRaises(FileExistsError): run.write_json(path, dict(a=2))
            with patch.object(run, "MAX_BYTES", 10), self.assertRaises(ValueError):
                run.write_json(Path(tmp)/"too_large.json", dict(a="x"*50))

    def test_source_and_existing_partial_stop_before_model(self):
        with patch.object(run, "identity", return_value={"sha256": "A"}), self.assertRaises(run.AdmissionHold):
            run.execute("qwen06", "canary", "B", "2026-10-24T08:40:00+09:00", 300)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/"qwen06/canary"
            target.mkdir(parents=True)
            with patch.object(run, "OUTPUT", Path(tmp)), patch.object(run, "identity", return_value={"sha256": "A"}), \
                    patch.object(run, "validate_execution", return_value={}), self.assertRaises(FileExistsError):
                run.execute("qwen06", "canary", "A", "2026-10-24T08:40:00+09:00", 300)

    def test_matching_cost_and_canary_needed_and_forecast_is_task_weighted(self):
        signature, assets = {"sha256": "A"}, {"synthetic": True}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for phase in ("canary", "cost"):
                (root/"qwen06"/phase).mkdir(parents=True)
            canary_path = root/"qwen06/canary/report.json"
            common = dict(schema=run.SCHEMA, tag=run.TAG, model="qwen06", source_identity=signature, policy=run.policy(), assets=assets, returncode=0)
            run.write_json(canary_path, dict(common, mode="canary", status="EXTERNAL_CANARY_COMPLETE", numerical_canary={"passed": True}))
            timing = {name: (2. if name == "hellaswag" else 1.) for name in run.official.TASK_COUNTS}
            cost = dict(common, mode="cost", status="EXTERNAL_LIMITED_COST_DIAGNOSTIC", actual_counts=run.official.expected_counts("cost"),
                raw_independent_recount=True, prerequisites={"canary_report_sha256": run.digest(canary_path)},
                task_evaluation_seconds=timing, pre_evaluation_seconds=10.)
            run.write_json(root/"qwen06/cost/report.json", cost)
            with patch.object(run, "OUTPUT", root):
                result = run.phase_prerequisites("qwen06", "full", signature, assets)
                self.assertAlmostEqual(result["forecast_seconds"], 1.3*sum(run.official.TASK_COUNTS[n]*v/32 for n,v in timing.items())+70)
                with self.assertRaises(run.AdmissionHold):
                    run.phase_prerequisites("qwen06", "full", signature, {"synthetic": False})

    def test_disk_raw_recount_rejects_missing_or_reordered_docs(self):
        from scripts.p106b_shards import ShardWriter
        class Task:
            multiple_input = False
            eval_docs = [{"choices": ["A", "BB"], "gold": 0}, {"choices": ["A", "BB"], "gold": 1}]
            def doc_to_choice(self, doc): return doc["choices"]
            def doc_to_target(self, doc): return doc["gold"]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            writer = ShardWriter(target, "raw")
            for index in (1, 0):
                writer.append(dict(doc_id=index, filtered_resps=[[-1., False], [-2., False]]))
            manifest = writer.close(lineage={"synthetic": True})
            with self.assertRaisesRegex(ValueError, "denominator/order"):
                run.recount_raw(Task(), target, manifest, 2)

    def test_model_runtime_cleans_gpu_and_verifies_body_on_scoring_error(self):
        calls = []
        class Body:
            config = SimpleNamespace(model_type="qwen3", use_cache=False, _attn_implementation="eager", vocab_size=8)
            def parameters(self): return iter([SimpleNamespace(dtype="FP32", numel=lambda: 8)])
            def get_input_embeddings(self): return SimpleNamespace(weight=SimpleNamespace(shape=(8, 2)))
            def eval(self): calls.append("eval")
            def to(self, device): calls.append(device); return self
        body = Body()
        class Tokenizer:
            vocab_size = 8
            pad_token_id = 0
            def __len__(self): return 8
            def get_vocab(self): return {"synthetic": 1}
        class HFLM:
            def __init__(self, pretrained, tokenizer, **kwargs):
                self._model, self.tokenizer = pretrained, tokenizer
                self.prefix_token_id, self.eot_token_id, self.device = 1, 2, "cuda"
        module = ModuleType("transformers")
        module.AutoModelForCausalLM = SimpleNamespace(from_pretrained=lambda *a, **k: (body, {}))
        module.AutoTokenizer = SimpleNamespace(from_pretrained=lambda *a, **k: Tokenizer())
        hf = ModuleType("lm_eval.models.huggingface"); hf.HFLM = HFLM
        torch = SimpleNamespace(float32="FP32", cuda=SimpleNamespace(empty_cache=lambda: calls.append("empty_cache")))
        from scripts import prepare_p106b_official_eval as prepare
        from scripts import interactive_research_infer as inference
        with patch.dict("sys.modules", {"transformers": module, "lm_eval.models.huggingface": hf}), \
                patch.object(prepare, "configure_hf_cache", return_value={}), \
                patch.object(run, "hflm_source_identity", return_value={"synthetic": True}), \
                patch.object(inference, "state_fingerprint", return_value="SAME"), \
                patch.object(run, "asset_identity", return_value={"assets": True}):
            with self.assertRaisesRegex(RuntimeError, "synthetic scoring"):
                with run.model_runtime("qwen06", torch, {"assets": True}) as (lm, proof):
                    raise RuntimeError("synthetic scoring")
        self.assertEqual(calls, ["eval", "cuda", "cpu", "empty_cache"])
        self.assertTrue(proof["body_unchanged"])
        self.assertTrue(proof["source_assets_unchanged"])

    def test_idle_guard_failure_preserves_report_without_model_or_torch(self):
        from scripts import prepare_p106b_official_eval as prepare
        from scripts import p106b_official_tasks as tasks
        from scripts import interactive_research_infer as inference
        signature = {"sha256": "A"}
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=signature), \
                patch.object(run, "validate_execution", return_value={"deadline_epoch": run.LATEST_DEADLINE, "hard_cap_seconds": 300}), \
                patch.object(run, "phase_wall_limit", return_value=nullcontext()), \
                patch.object(run, "asset_identity", return_value={}), \
                patch.object(run, "phase_prerequisites", return_value={}), \
                patch.object(prepare, "configure_hf_cache", return_value={}), \
                patch.object(tasks, "load_tasks", return_value=({}, [], {})), \
                patch.object(inference, "require_idle_gpu", side_effect=RuntimeError("synthetic GPU occupied")), \
                patch.object(run, "model_runtime") as model:
            with self.assertRaisesRegex(RuntimeError, "GPU occupied"):
                run.execute("qwen06", "canary", "A", "2026-10-24T08:40:00+09:00", 300)
            model.assert_not_called()
            report = run.read_json(Path(tmp)/"qwen06/canary/report.json")
            self.assertEqual(report["status"], "EXTERNAL_EVALUATION_ERROR")
            self.assertTrue(report["sources_unchanged"])
            self.assertFalse(report["quality_claim"])


if __name__ == "__main__":
    unittest.main()
