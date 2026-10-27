"""Synthetic external Core6 admission/recount tests; no model, GPU or HF import."""
from __future__ import annotations

import builtins
import ast
from collections import Counter
import copy
from contextlib import redirect_stdout, contextmanager, nullcontext
import io
import json
from pathlib import Path
import runpy
import re
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import diag_p106b_external_core6 as run


def real_evidence_serialization_smoke(evidence_root, raw_log):
    """Read-only CPU fixture, not a replacement cost report or model rerun.

    Reuse the pinned YAML and exact doc_to_* function bodies on already
    processed raw documents. Do not construct a task/dataset cache or import a
    model library. Cost-only proof lost by v2 closure remains explicitly absent.
    """
    from jinja2 import BaseLoader, Environment, StrictUndefined
    from scripts.p106b_shards import verify

    source_before = run.identity()
    evidence_root, raw_log = Path(evidence_root), Path(raw_log)
    inputs = {}
    def read(path):
        path = Path(path)
        data = path.read_bytes()
        inputs[str(path)] = run.digest(path)
        return data

    canary = json.loads(read(evidence_root / "canary/report.json"))
    if (canary["schema"] != "P106B_EXTERNAL_HF_CORE6_V2"
            or canary["tag"] != "p106b_external_core6_v2_s1337"
            or canary["status"] != "EXTERNAL_CANARY_COMPLETE" or canary["returncode"] != 0
            or canary["numerical_canary"]["passed"] is not True):
        raise AssertionError("actual closed v2 numerical canary required")
    cost = evidence_root / "cost"
    closure = json.loads(read(cost / "report.json"))
    if closure["status"] != "EXTERNAL_REPORT_CLOSURE_ERROR" or closure["original_error"] is not None:
        raise AssertionError("the preserved v2 writer-only failure must remain a failure")
    source = run.ROOT / "data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source"
    loader_path = source / "lm_eval/tasks/_yaml_loader.py"
    read(loader_path)
    loader = runpy.run_path(str(loader_path))

    utils_path = source / "lm_eval/utils.py"
    utils_tree = ast.parse(read(utils_path).decode("utf-8"))
    utilities = {"re": re, "Environment": Environment, "BaseLoader": BaseLoader, "StrictUndefined": StrictUndefined}
    selected = []
    for node in utils_tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"regex_replace", "apply_template"}:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "env" or isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Attribute) and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "env" for target in node.targets):
            selected.append(node)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(utils_path), "exec"), utilities)
    task_path = source / "lm_eval/api/task.py"
    task_tree = ast.parse(read(task_path).decode("utf-8"))
    original_class = next(node for node in task_tree.body if isinstance(node, ast.ClassDef) and node.name == "ConfigurableTask")
    method_names = {"doc_to_text", "doc_to_target", "doc_to_choice"}
    methods = [node for node in original_class.body if isinstance(node, ast.FunctionDef) and node.name in method_names]
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future] + methods, type_ignores=[]))
    namespace = {"ast": ast, "utils": SimpleNamespace(apply_template=utilities["apply_template"])}
    exec(compile(module, str(task_path), "exec"), namespace)
    RawTask = type("RawFixtureTask", (), {name: namespace[name] for name in method_names})

    audits, manifests, all_rows = {}, {}, {}
    for spec in canary["task_specs"]:
        name = spec["task"]
        yaml_path = Path(spec["official_yaml"])
        read(yaml_path)
        if run.digest(yaml_path) != spec["official_yaml_sha256"]:
            raise AssertionError("pinned official YAML changed")
        metadata = loader["load_yaml"](yaml_path, resolve_func=False, recursive=True)
        for key in method_names:
            value = metadata[key]
            if isinstance(value, str) and value.startswith(str(source)):
                helper_path = Path(value.rsplit(".", 1)[0]).with_suffix(".py")
                read(helper_path)
                metadata[key] = runpy.run_path(str(helper_path))[value.rsplit(".", 1)[1]]
        manifest = json.loads(read(cost / (name + "_samples_shards_manifest.json")))
        verify(cost, manifest)
        rows = [json.loads(line) for shard in manifest["shards"]
            for line in read(cost / shard["path"]).splitlines()]
        task = RawTask()
        task.prompt = None
        task.config = task._config = SimpleNamespace(**metadata)
        task.features = list(rows[0]["doc"])
        task.eval_docs = [row["doc"] for row in rows]
        task.multiple_input = type(task.doc_to_text(task.eval_docs[0])) is int
        for row in rows:
            if task.doc_to_target(row["doc"]) != row["target"]:
                raise AssertionError("raw official target differs from exact original task method")
        audit = run.recount_raw(task, cost, manifest, 32)
        if audit != dict(run.official.audit_samples(task, rows, 32),
                choice_likelihoods=sum(len(row["filtered_resps"]) for row in rows)):
            raise AssertionError("independent actual raw recount differs")
        audits[name], manifests[name], all_rows[name] = audit, manifest, rows
    if set(audits) != set(run.official.TASK_COUNTS) or sum(a["rows"] for a in audits.values()) != 192:
        raise AssertionError("all six actual first32 raw tasks are required")

    lengths_manifest = json.loads(read(cost / "token_lengths_shards_manifest.json"))
    verify(cost, lengths_manifest)
    lengths = [json.loads(line) for shard in lengths_manifest["shards"]
        for line in read(cost / shard["path"]).splitlines()]
    choices = sum(a["choice_likelihoods"] for a in audits.values())
    if [row["index"] for row in lengths] != list(range(choices)):
        raise AssertionError("actual length trace does not cover every raw choice")
    log = read(raw_log).decode("utf-8")
    events = [json.loads(line) for line in log.splitlines() if line.startswith('{"event": "EXTERNAL_OFFICIAL_TASK_CLOSED"')]
    if {event["task"] for event in events} != set(audits) or len(events) != 6:
        raise AssertionError("six actual task-closure timings required")

    small_assets = {}
    for name, descriptor in canary["assets"]["files"].items():
        if name == run.REGISTRY[canary["model"]]["weight"]:
            continue  # Do not read a model weight for a JSON-only CPU smoke.
        path = Path(descriptor["resolved_path"])
        read(path)
        if inputs[str(path)] != descriptor["sha256"]:
            raise AssertionError("actual small model/tokenizer asset changed")
        small_assets[name] = descriptor["sha256"]
    loading = copy.deepcopy(canary["model_proof"]["loading_info"])
    for key in ("missing_keys", "unexpected_keys", "mismatched_keys"):
        if loading[key]:
            raise AssertionError("native strict canary has a nonempty loading key set")
        loading[key] = set()
    gaps = ["cost model_proof/fingerprints/exit verification were not retained in the v2 fallback",
        "cost numerical_canary/startup/wall_seconds/full official_results were not retained",
        "native_canary_report and reconstructed loading_info belong to the actual canary, not the cost run",
        "weight SHA is reused from native canary evidence; model weight was not reread"]
    fixture = dict(schema="P106B_REAL_EVIDENCE_JSON_CPU_FIXTURE_V1",
        status="CPU_FIXTURE_ONLY_NOT_AN_EVALUATION_OR_COST_REPORT", quality_claim=False,
        candidate_schema=run.SCHEMA, candidate_tag=run.TAG, native_canary_report=canary,
        preserved_cost_failure=closure, cost_report_unavailable_fields=gaps,
        reconstructed_runtime_loading_info=loading,
        reconstructed_cost_sections=dict(actual_counts={name: audit["rows"] for name, audit in audits.items()},
            sample_manifests=manifests, independent_audits=audits, raw_samples=all_rows,
            lengths_manifest=lengths_manifest, token_lengths=lengths,
            choice_likelihoods=choices, task_evaluation_seconds={event["task"]: event["seconds"] for event in events},
            official_results={"unavailable": gaps[1]}))
    paths, types = [], Counter()
    def inspect(value, path="$"):
        types[type(value).__name__] += 1
        if isinstance(value, dict):
            for key, item in value.items():
                if type(key) is not str:
                    paths.append(path + "[" + repr(key) + "]")
                inspect(item, path + "[" + repr(key) + "]")
        elif isinstance(value, (list, tuple, set, frozenset)):
            for item in value: inspect(item, path + "[]")
    inspect(fixture)
    normalized = run.json_ready(fixture)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    if json.loads(encoded) != normalized or len(encoded) >= run.MAX_BYTES:
        raise AssertionError("complete actual-evidence CPU fixture cannot roundtrip under the report cap")
    for name, audit in audits.items():
        labels = json.loads(encoded)["reconstructed_cost_sections"]["independent_audits"][name]["posthoc_label_counts"]
        if {int(key): value for key, value in labels.items()} != audit["posthoc_label_counts"]:
            raise AssertionError("native integer label counts were not preserved losslessly")
    if any(run.digest(path) != sha for path, sha in inputs.items()) or run.identity() != source_before:
        raise AssertionError("read-only evidence/source changed during CPU fixture smoke")
    if any(name.split(".")[0] in {"torch", "transformers", "tokenizers", "datasets", "lm_eval", "tinylm"} for name in sys.modules):
        raise AssertionError("the read-only fixture imported a model/dataset runtime")
    return dict(status="CPU_REAL_EVIDENCE_SERIALIZATION_SMOKE_COMPLETE", quality_claim=False,
        models=0, gpu_calls=0, files_written=0, rows=192, choice_likelihoods=choices,
        per_task_rows={name: audit["rows"] for name, audit in audits.items()},
        native_integer_key_paths=paths, pre_serialization_types=dict(types),
        deterministic_roundtrip=True, serialized_bytes=len(encoded), evidence_inputs_unchanged=True,
        source_identity=source_before, actual_small_asset_sha256=small_assets,
        v2_canary_source_sha256=canary["source_identity"]["sha256"],
        reconstructed_cost_proof_gaps=gaps, evidence_input_sha256=inputs)


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

    def image_metadata(self, *, special=True):
        name, index = "<image_soft_token>", 262144
        token_metadata = {"added_tokens": [dict(id=index, content=name, special=special)]}
        tokenizer_metadata = dict(added_tokens_decoder={str(index): dict(content=name, special=special)},
            image_token=name, extra_special_tokens={"image_token": name})
        return token_metadata, tokenizer_metadata, {"image_token": name}

    def test_exact_unused_image_special_is_recorded_without_expanding_text_head(self):
        token_metadata, tokenizer_metadata, special_map = self.image_metadata()
        base = {"ordinary": 3}
        full = dict(base, **{"<image_soft_token>": 262144})
        audit = run.audit_tokenizer_vocabulary("gemma270", full, base, 262144,
            token_metadata=token_metadata, tokenizer_metadata=tokenizer_metadata, special_map=special_map)
        self.assertEqual(audit["head_size"], 262144)
        self.assertEqual(audit["out_of_head_added_specials"], [dict(id=262144, content="<image_soft_token>",
            special=True, usable_as_text_input_or_target=False)])
        self.assertEqual(full["<image_soft_token>"], 262144)

    def test_non_special_unregistered_and_base_out_of_head_ids_still_fail(self):
        token_metadata, tokenizer_metadata, special_map = self.image_metadata(special=False)
        for model, full, base, metadata in (
                ("gemma270", {"A": 0, "<image_soft_token>": 262144}, {"A": 0}, (token_metadata, tokenizer_metadata, special_map)),
                ("qwen06", {"A": 0, "<image_soft_token>": 262144}, {"A": 0}, self.image_metadata()),
                ("gemma270", {"A": 0, "other_special": 262144}, {"A": 0}, self.image_metadata()),
                ("gemma270", {"A": 262144}, {"A": 262144}, self.image_metadata())):
            with self.subTest(model=model, full=full), self.assertRaises(run.AdmissionHold):
                run.audit_tokenizer_vocabulary(model, full, base, 262144,
                    token_metadata=metadata[0], tokenizer_metadata=metadata[1], special_map=metadata[2])

    def guarded_scorer(self):
        class Official:
            max_length = 1024
            prefix_token_id, eot_token_id = 1, 2
            def __init__(self):
                self.forward_calls = 0
                self.tokenizer = SimpleNamespace(pad_token_id=0)
            def _encode_pair(self, context, continuation): return [1], [2]
            def tok_encode(self, text, **kwargs): return {"ok": [1, 3], "image": [4], "empty": []}[text]
            def _loglikelihood_tokens(self, requests, *args, **kwargs):
                self.forward_calls += 1
                return [(-1., False)] * len(requests)
        guarded = run.head_guard_type(Official, 4)
        self.assertIs(guarded._encode_pair, Official._encode_pair)
        return guarded()

    def test_encoded_actual_image_context_and_target_are_rejected_before_any_forward(self):
        lm = self.guarded_scorer()
        self.assertEqual(lm.tok_encode("ok"), [1, 3])
        self.assertEqual(lm.tok_encode("empty"), [])
        with self.assertRaises(ValueError): lm.tok_encode("image")
        for context, continuation in (([4], [2]), ([1], [4]), ([], [2]), ([1], []), ([True], [2])):
            with self.subTest(context=context, continuation=continuation), self.assertRaises(ValueError):
                lm._loglikelihood_tokens([(("A", "B"), [1], [2]), (("C", "D"), context, continuation)])
        self.assertEqual(lm.forward_calls, 0)
        self.assertEqual(lm._loglikelihood_tokens([(("A", "B"), [1], [2])]), [(-1., False)])
        self.assertEqual(lm.forward_calls, 1)

    def test_prefix_pad_and_eos_are_checked_before_encoded_forward(self):
        for field in ("prefix", "pad", "eos"):
            with self.subTest(field=field):
                lm = self.guarded_scorer()
                if field == "prefix": lm.prefix_token_id = 4
                elif field == "pad": lm.tokenizer.pad_token_id = 4
                else: lm.eot_token_id = 4
                with self.assertRaises(run.AdmissionHold):
                    lm._loglikelihood_tokens([(("A", "B"), [1], [2])])
                self.assertEqual(lm.forward_calls, 0)

    def test_real_loading_info_set_shape_is_preserved_as_deterministic_json(self):
        loading = dict(missing_keys={"z", "a"}, unexpected_keys=set(),
            mismatched_keys={("weight", (2, 3), (3, 2))}, error_msgs=[])
        normalized = run.json_ready(loading)
        self.assertEqual(normalized["missing_keys"], ["a", "z"])
        self.assertEqual(normalized["unexpected_keys"], [])
        self.assertEqual(normalized["mismatched_keys"], [["weight", [2, 3], [3, 2]]])
        for invalid in (float("nan"), float("inf"), object()):
            with self.assertRaises((TypeError, ValueError)): run.json_ready({"invalid": invalid})

    def test_primitive_json_keys_preserve_label_counts_and_canonical_json_semantics(self):
        value = {"labels": {0: 19, 1: 13}, "primitives": {None: "none", False: "bool", 2: "int", 2.5: "float"}}
        normalized = run.json_ready(value)
        self.assertEqual(normalized, json.loads(json.dumps(value, allow_nan=False)))
        self.assertEqual({int(key): count for key, count in normalized["labels"].items()}, value["labels"])
        self.assertEqual(run.json_ready(normalized), normalized)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.json"
            run.close_report(path, value)
            self.assertEqual(run.read_json(path), normalized)

    def test_canonical_key_collisions_nonfinite_and_nonprimitive_keys_fail_closed(self):
        for keys in ({1: "integer", "1": "string"}, {None: 1, "null": 2},
                {True: 1, "true": 2}, {2.5: 1, "2.5": 2}):
            with self.subTest(keys=keys), self.assertRaisesRegex(ValueError, "canonical report key collision"):
                run.json_ready({"nested": keys})
        for key in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "nonfinite report key"):
                run.json_ready({key: "invalid"})
        for key in ((1, 2), object()):
            with self.assertRaisesRegex(TypeError, "unsupported report key type"):
                run.json_ready({key: "invalid"})
        with self.assertRaisesRegex(TypeError, "nested.*unsupported|unsupported.*nested"):
            run.json_ready({"nested": [object()]})

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
            def get_output_embeddings(self): return self.get_input_embeddings()
            def eval(self): calls.append("eval")
            def to(self, device): calls.append(device); return self
        body = Body()
        class Tokenizer:
            vocab_size = 8
            pad_token_id = 0
            def __len__(self): return 8
            def get_vocab(self): return {"synthetic": 1}
            backend_tokenizer = SimpleNamespace(get_vocab=lambda **kwargs: {"synthetic": 1})
        class HFLM:
            def __init__(self, pretrained, tokenizer, **kwargs):
                self._model, self.tokenizer = pretrained, tokenizer
                self.prefix_token_id, self.eot_token_id, self.device = 1, 2, "cuda"
                self.max_length = 1024
        module = ModuleType("transformers")
        module.AutoModelForCausalLM = SimpleNamespace(from_pretrained=lambda *a, **k: (body,
            dict(missing_keys=set(), unexpected_keys=set(), mismatched_keys=set(), error_msgs=[])))
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
        self.assertEqual(proof["loading_info"], dict(missing_keys=[], unexpected_keys=[], mismatched_keys=[], error_msgs=[]))

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

    def test_execute_failure_with_real_sets_and_secondary_serialization_preserves_primary(self):
        from scripts import prepare_p106b_official_eval as prepare
        from scripts import p106b_official_tasks as tasks
        from scripts import interactive_research_infer as inference
        for inject_unknown in (False, True):
            with self.subTest(inject_unknown=inject_unknown), tempfile.TemporaryDirectory() as tmp:
                prerequisite = dict(loading_info=dict(missing_keys=set(), unexpected_keys=set(), mismatched_keys=set(), error_msgs=[]))
                if inject_unknown: prerequisite["unsupported"] = object()
                primary = run.AdmissionHold("synthetic exact original admission error")
                with patch.object(run, "OUTPUT", Path(tmp)), patch.object(run, "identity", return_value={"sha256": "A"}), \
                        patch.object(run, "validate_execution", return_value={"deadline_epoch": run.LATEST_DEADLINE, "hard_cap_seconds": 300}), \
                        patch.object(run, "phase_wall_limit", return_value=nullcontext()), \
                        patch.object(run, "asset_identity", return_value={}), \
                        patch.object(run, "phase_prerequisites", return_value=prerequisite), \
                        patch.object(prepare, "configure_hf_cache", return_value={}), \
                        patch.object(tasks, "load_tasks", return_value=({}, [], {})), \
                        patch.object(inference, "require_idle_gpu", side_effect=primary), \
                        patch.object(run, "model_runtime") as model:
                    with self.assertRaises(run.AdmissionHold) as caught:
                        run.execute("gemma270", "canary", "A", "2026-10-24T08:40:00+09:00", 300)
                    self.assertIs(caught.exception, primary)
                    model.assert_not_called()
                    report = run.read_json(Path(tmp)/"gemma270/canary/report.json")
                    self.assertEqual(report["status"], "EXTERNAL_PREREQUISITE_HOLD")
                    if inject_unknown:
                        self.assertEqual(report["original_error"]["message"], str(primary))
                        self.assertEqual(report["report_closure_error"]["type"], "TypeError")
                    else:
                        self.assertEqual(report["error"], str(primary))
                        self.assertEqual(report["prerequisites"]["loading_info"]["missing_keys"], [])

    def test_report_closure_failure_without_primary_is_not_a_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.json"
            with self.assertRaises(TypeError): run.close_report(path, {"unsupported": object()})
            report = run.read_json(path)
            self.assertEqual(report["status"], "EXTERNAL_REPORT_CLOSURE_ERROR")
            self.assertEqual(report["returncode"], 9)


if __name__ == "__main__":
    unittest.main()
