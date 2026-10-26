#!/usr/bin/env python3
"""새 쌍 통계의 합성 CPU 회귀. 실제 새 결과·CP·모델·GPU는 읽지 않는다."""
from __future__ import annotations
import ast
from contextlib import ExitStack, contextmanager, redirect_stdout
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import summarize_p106b_native_format_pair as d


class Budget:
    def __init__(self, *args, **kwargs):
        self.started = time.monotonic(); self.end = self.started + 600; self.reserve = 1
    def remaining(self): return self.end - time.monotonic()
    def check(self, stage):
        if self.remaining() <= 0: raise TimeoutError(stage)


def put(root, name, value):
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(d.canonical(value))
    return dict(path=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())


def observed():
    return dict(actual_child_exit=0, launch_state="STARTED", forced_cleanup=False, original_error=None,
        cleanup_errors=[], child_group_quiescent=True, stdout_complete=True, subreaper_restored=True)


class Fixture:
    """합성 종결 metadata만 쓴다. CP 경로에는 어떤 파일도 만들지 않는다."""
    def __init__(self, root):
        self.root, self.stack = root, ExitStack()
        self.real = d.shared_api()
        self.api = SimpleNamespace(Inputs=self.real.Inputs, read_json=self.real.read_json, decode=self.real.decode,
            report_path=lambda name, base: Path(base) / ("peer_" + name + ".json"), admit_report=Mock())
        self.signature = dict(sha256="A" * 64, files={}, frozen={})
        self.stack.enter_context(patch.object(d, "shared_api", return_value=self.api))
        self.stack.enter_context(patch.object(d, "source_identity", return_value=self.signature))
        self.train_source, self.eval_source = d.training.source_identity(), d.official.source_identity()
        self.train_profile = dict(schema=d.training.PROFILE, recipe=copy.deepcopy(d.training.RECIPE),
            normuon=dict(beta2=.95, eps=1e-10, implementation="TINYLM_ADAPTED_POST_NS_ROW_EMA"),
            arms=[dict(id="format_muon", corpus="format", optimizer="muon", required=True),
                dict(id="format_normuon", corpus="format", optimizer="normuon", required=True)],
            pair_complete=dict(path="pair/complete.json", sha256="F" * 64))
        self.train_profile_ref = put(root, "train_profile.json", self.train_profile)
        self.f4_ref = put(root, "f4.json", dict(schema="P106B_NATIVE_FORMAT_F4_V1", root_approved=True,
            source_sha256=d.TRAINING_SHA, profile_sha256=self.train_profile_ref["sha256"], allowed_modes=["train"]))
        self.profiles, self.train_workers, self.workers, self.reports, self.root_specs = {}, {}, {}, {}, {}
        self.config = dict(schema=d.INPUTS_SCHEMA, root_approved=True, statistics_source_sha256="A" * 64,
            official_source_sha256=d.OFFICIAL_SHA, training_source_sha256=d.TRAINING_SHA,
            dialogue_source_sha256=d.DIALOGUE_SHA, new_models={})
        for index, model in enumerate(d.NEW_MODELS):
            train = dict(schema=d.training.SCHEMA, status="TRAIN2289_COMPLETE", mode="train", arm=model, corpus="format",
                optimizer="muon" if index == 0 else "normuon", synthetic=False, updates=2289,
                totals=dict(targets=300023808, x_tokens=300023808), scratch_core_sha256=d.training.CORE,
                original_weights_copied=False, source_sha256=d.TRAINING_SHA, profile_sha256=self.train_profile_ref["sha256"],
                pair_complete_sha256="F" * 64, quantization_route=copy.deepcopy(d.official.ROUTE),
                cfg=dict(mtp_aux=False, vocab_size=32768), offsets=dict(seed=1337, offsets_bytes_sha256="1" * 64),
                training_completed_epoch=d.training.TRAIN_END.timestamp() - 100,
                checkpoint="runs/ckpt/" + model + "_fixture.pt", checkpoint_sha256=("B" if index == 0 else "C") * 64,
                final_core_sha256=("D" if index == 0 else "E") * 64)
            train_spec, train_report = self.parent(model + "_train", model, train, d.training.SCHEMA, "train", d.TRAINING_SHA,
                self.train_profile_ref["sha256"], self.train_source, f4_sha256=self.f4_ref["sha256"], pair_complete_sha256="F" * 64)
            profile = dict(schema=d.official.PROFILE, root_approved=True, arm=model, source_sha256=d.OFFICIAL_SHA,
                training_source_sha256=d.TRAINING_SHA, official_policy=d.official.policy(), numerical_contract=d.official.CONTRACT,
                deadline=d.official.END.isoformat(), training_profile=self.train_profile_ref, training_f4=self.f4_ref,
                closed_train=train_spec, cleanup_reserve_sec=120, entry_free_mib=14000)
            profile_ref = put(root, model + "_profile.json", profile)
            worker = dict(schema=d.official.SCHEMA, status="OFFICIAL_CORE6_FULL_COMPLETE", mode="full", arm=model,
                actual_counts=copy.deepcopy(d.COUNTS), token_lengths_summary=dict(requests=d.REQUESTS),
                source_sha256=d.OFFICIAL_SHA, profile_sha256=profile_ref["sha256"], training_report_sha256=train_spec["sha256"],
                checkpoint_sha256=train["checkpoint_sha256"], framework_commit=d.official.assets.COMMIT,
                data_manifest_sha256=d.official.assets.MANIFEST_SHA, task_specs=[], fixture_only=True)
            root_spec, report = self.parent(model + "_full", model, worker, d.official.SCHEMA, "full", d.OFFICIAL_SHA,
                profile_ref["sha256"], self.eval_source, authority_end=d.official.END.isoformat())
            root_ref = put(root, model + "_root_closed_ref.json", root_spec)
            self.config["new_models"][model] = dict(profile=profile_ref, full_root_ref=root_ref)
            self.profiles[model], self.train_workers[model], self.workers[model] = profile, train, worker
            self.reports[model], self.root_specs[model] = report, root_spec
        for peer in d.PEERS:
            put(root, "peer_" + peer + ".json", dict(model=peer, fixture_only=True))
        self.refresh()
    def close(self): self.stack.close()
    def refresh(self): self.ref = put(self.root, "inputs.json", self.config)
    def parent(self, folder, model, worker, schema, mode, source, profile_sha, code, **extra):
        directory = "test_result/evidence/fixture_" + folder
        worker_ref = put(self.root, directory + "/worker.json", worker)
        put(self.root, directory + "/source.json", code)
        terminal = self.root / directory / "terminal.jsonl"
        terminal.write_bytes(d.canonical(dict(event="OBSERVATION", returncode=0)) + bytes([10]))
        report = dict(schema=schema, mode=mode, arm=model, source_sha256=source, profile_sha256=profile_sha,
            returncode=0, supervision=observed(), whole_parent_seconds=10., worker=worker, worker_sha256=worker_ref["sha256"], **extra)
        ref = put(self.root, directory + "/report.json", report)
        spec = dict(ref, terminal_sha256=hashlib.sha256(terminal.read_bytes()).hexdigest().upper(),
            actual_supervisor_exit=0, actual_parent_wall_sec=11.)
        return spec, report
    def prepare(self): return d.prepare(self.ref, "A" * 64, Budget(), root=self.root)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_pair_stats_metadata_", dir="/tmp")
        self.root = Path(self.tmp.name); self.f = Fixture(self.root)
    def tearDown(self): self.f.close(); self.tmp.cleanup()
    def test_two_real_schema_metadata_and_no_cp_path_access(self):
        with patch.object(d.official, "metadata", side_effect=AssertionError("CP 해시 금지")),\
                patch.object(d.training, "read_closed", side_effect=AssertionError("CP 해시 금지")):
            value = self.f.prepare()
        self.assertEqual(set(value["models"]), set((*d.NEW_MODELS, *d.PEERS)))
        self.assertEqual(self.f.api.admit_report.call_count, 2)
        self.assertFalse(any("runs/ckpt" in path or path.endswith(".pt") for path in value["evidence"].inputs.files))
    def test_second_full_absent_stops_before_any_new_report_values(self):
        path = self.root / self.f.config["new_models"]["format_normuon"]["full_root_ref"]["path"]
        path.unlink()
        with patch.object(d, "new_metadata", side_effect=AssertionError("두 full 이전 수치 읽기 금지")) as reader:
            with self.assertRaises(d.Hold): self.f.prepare()
        reader.assert_not_called()
    def test_nonzero_or_boolean_actual_exit_is_hold(self):
        for code in (8, 9, True, "ROOT_MUST_COLLECT"):
            spec = dict(self.f.root_specs["format_normuon"], actual_supervisor_exit=code)
            self.f.config["new_models"]["format_normuon"]["full_root_ref"] = put(self.root, "bad_root_ref.json", spec)
            self.f.refresh()
            with self.subTest(code=code), self.assertRaises(d.Hold): self.f.prepare()
    def test_unknown_model_or_old_model_alias_is_rejected(self):
        self.f.config["new_models"]["native595-q"] = self.f.config["new_models"].pop("format_muon")
        self.f.refresh()
        with self.assertRaises(ValueError): self.f.prepare()
    def test_profile_sha_or_frozen_source_change_is_not_relaxed(self):
        self.f.config["new_models"]["format_muon"]["profile"]["sha256"] = "0" * 64
        self.f.refresh()
        with self.assertRaises(ValueError): self.f.prepare()
    def test_legacy3269_official_denominator_is_rejected(self):
        model = "format_muon"; worker = copy.deepcopy(self.f.workers[model]); worker["actual_counts"]["boolq"] = 3269
        spec, report = self.f.parent(model + "_wrong_full", model, worker, d.official.SCHEMA, "full", d.OFFICIAL_SHA,
            self.f.config["new_models"][model]["profile"]["sha256"], self.f.eval_source, authority_end=d.official.END.isoformat())
        self.f.config["new_models"][model]["full_root_ref"] = put(self.root, "wrong_full_root_ref.json", spec)
        self.f.refresh()
        with self.assertRaisesRegex(ValueError, "19965/67106"): self.f.prepare()
    def test_partial_parent_or_forced_cleanup_is_not_complete(self):
        for kind in ("nonzero", "forced", "child8"):
            report = copy.deepcopy(self.f.reports["format_muon"])
            if kind == "nonzero": report["returncode"] = 9
            if kind == "forced": report["supervision"]["forced_cleanup"] = True
            if kind == "child8": report["supervision"]["actual_child_exit"] = 8
            original = self.f.root_specs["format_muon"]
            ref = put(self.root, original["path"], report)
            spec = dict(original, **ref)
            self.f.config["new_models"]["format_muon"]["full_root_ref"] = put(self.root, "changed_root_ref.json", spec)
            self.f.refresh()
            with self.subTest(kind=kind), self.assertRaises((d.Hold, ValueError)): self.f.prepare()
    def test_late_terminal_veto_is_preserved_and_rejected(self):
        spec = self.f.root_specs["format_muon"]
        terminal = (self.root / spec["path"]).parent / "terminal.jsonl"
        with terminal.open("ab") as stream:
            stream.write(d.canonical(dict(event="TERMINAL_VETO", returncode=9)) + bytes([10]))
        spec = dict(spec, terminal_sha256=hashlib.sha256(terminal.read_bytes()).hexdigest().upper())
        self.f.config["new_models"]["format_muon"]["full_root_ref"] = put(self.root, "veto_root_ref.json", spec)
        self.f.refresh()
        with self.assertRaisesRegex(ValueError, "후행"): self.f.prepare()
    def test_checkpoint_and_protected_paths_are_rejected_before_io(self):
        for name in ("runs/ckpt/anything", "data_cache/train.bin", "weights.gguf", "data.pt",
                ".claude/x.json", "datasets/TinyDataset/x.json", ".agents/x.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                d.Evidence(self.f.api, root=self.root).json(self.root / name)
    def test_source_receipt_uses_original_new_canonical_hash(self):
        data = {"scripts/x.py": "A" * 64}; expected = d.sha(data)
        d.code_receipt(dict(files=data, sha256=expected), expected)
        with self.assertRaises(ValueError): d.code_receipt(dict(files=data, sha256="0" * 64), expected)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_pair_stats_shards_", dir="/tmp")
        self.root = Path(self.tmp.name); self.shared = d.shared_api(); self.e = d.Evidence(self.shared, root=self.root)
    def tearDown(self): self.tmp.cleanup()
    def manifest(self):
        writer = d.official.ShardWriter(self.root, "piqa_samples", limit=1000)
        writer.append(dict(fixture=True, doc_id=0))
        lineage = dict(schema=d.official.SCHEMA, checkpoint_sha256="A" * 64, task="piqa", mode="full")
        return writer.close(lineage=lineage), lineage
    def test_original_disk_manifest_lineage_and_sha(self):
        manifest, lineage = self.manifest()
        self.e.manifest(self.root, "piqa_samples", manifest, lineage, rows=1, bodies=True)
        self.assertIn(str(self.root / "piqa_samples_000000.jsonl"), self.e.inputs.files)
    def test_old_model_lineage_cannot_replace_new_cp_lineage(self):
        manifest, lineage = self.manifest()
        with self.assertRaises(ValueError):
            self.e.manifest(self.root, "piqa_samples", manifest, dict(model="native595-q", task="piqa", mode="full"))
    def test_changed_raw_same_length_is_not_ignored(self):
        manifest, lineage = self.manifest()
        raw = self.root / manifest["shards"][0]["path"]
        raw.write_bytes(raw.read_bytes().replace(b'"doc_id":0', b'"doc_id":1'))
        with self.assertRaises(ValueError): self.e.manifest(self.root, "piqa_samples", manifest, lineage, bodies=True)
    def test_new_raw_equal20mb_is_not_admitted(self):
        manifest, lineage = self.manifest(); manifest["limit_bytes"] = 20_000_000
        with self.assertRaises(ValueError): self.e.manifest(self.root, "piqa_samples", manifest, lineage)


def correspondence():
    return {name: {key + "_ordered_sha256": d.sha(dict(task=name, field=key))
        for key in ("docs", "arguments", "gold_choices", "cases")} for name in d.PRIMARY}


def small_models():
    bits = dict(format_muon=[1, 0], format_normuon=[1, 1], **{"native595-q": [0, 0], "falcon90m": [1, 0]})
    return {model: dict(model=model, rows=12, choice_likelihoods=24, correspondence=correspondence(),
        values={name: list(values) for name in d.PRIMARY}) for model, values in bits.items()}


def fake_paired(left, right, *, draws, seed):
    assert (draws, seed) == (100000, 20261024)
    rows = {}
    for name in d.PRIMARY:
        a, b = left[name], right[name]
        rows[name] = dict(n=len(a), primary_metric=d.PRIMARY[name], left=sum(a)/len(a), right=sum(b)/len(b),
            right_minus_left=(sum(b)-sum(a))/len(a), ci95=[-.5, 1.],
            discordant_right_worse=sum(x == 1 and y == 0 for x, y in zip(a, b)),
            discordant_right_better=sum(x == 0 and y == 1 for x, y in zip(a, b)),
            same_correctness=sum(x == y for x, y in zip(a, b)))
    return dict(per_task=rows, mean6=dict(right_minus_left=sum(r["right_minus_left"] for r in rows.values())/6,
        ci95=[-.5, 1.]), resamples=draws, seed=seed, multiple_comparisons_corrected=False)


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        for key, value in (("COUNTS", {name: 2 for name in d.PRIMARY}), ("ITEMS", 12), ("REQUESTS", 24)):
            self.stack.enter_context(patch.object(d, key, value))
    def tearDown(self): self.stack.close()
    def test_all_five_pairs_thirty_exact_tests_and_positive_normuon_sign(self):
        paired, exact = Mock(side_effect=fake_paired), Mock(wraps=d.mcnemar_exact_p)
        result = d.comparisons(small_models(), paired=paired, exact=exact)
        self.assertEqual((paired.call_count, exact.call_count), (5, 30))
        primary = result["pairs"]["format_muon__format_normuon"]
        self.assertEqual(primary["pointwise95"]["mean6"]["right_minus_left"], .5)
        self.assertEqual(result["holm_family"]["size"], 30)
        self.assertEqual(result["holm_family"]["families"], 1)
        self.assertFalse(result["intervals"]["multiplicity_adjusted"])
        self.assertFalse(result["intervals"]["training_seed_uncertainty"])
        self.assertEqual([r["id"] for r in result["exact_tests"]], d.family_ids())
    def test_intersection_or_wrong_binary_values_fail_before_statistics(self):
        for kind in ("3269", "missing", "binary", "sha", "emptysha", "rows"):
            models = small_models()
            if kind == "3269": models["format_normuon"]["values"]["boolq"].pop()
            if kind == "missing": del models["format_normuon"]["values"]["piqa"]
            if kind == "binary": models["format_normuon"]["values"]["piqa"][0] = 2
            if kind == "sha": models["format_normuon"]["correspondence"]["piqa"]["docs_ordered_sha256"] = "0" * 64
            if kind == "emptysha":
                for model in models.values(): model["correspondence"] = {}
            if kind == "rows": models["format_normuon"]["rows"] -= 1
            paired = Mock(side_effect=AssertionError("불완전 입장 뒤 계산 금지"))
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.comparisons(models, paired=paired)
            paired.assert_not_called()
    def test_existing_exact_function_handles_zero_and_small_discordance(self):
        self.assertEqual(d.mcnemar_exact_p(0, 0), 1.)
        self.assertAlmostEqual(d.mcnemar_exact_p(5, 0), .0625, places=12)
        self.assertAlmostEqual(d.mcnemar_exact_p(0, 5), .0625, places=12)
    def family_rows(self, values): return [dict(id=key, raw_p=p) for key, p in zip(d.family_ids(), values)]
    def test_holm_uses_one30_family_and_monotone_stepdown(self):
        result = d.holm(self.family_rows([.0001, .001, .002, .01] + [1.] * 26))
        for row, expected in zip(result[:4], (.003, .029, .056, .27)):
            self.assertAlmostEqual(row["holm_adjusted_p"], expected)
        self.assertEqual([row["holm_rank"] for row in result], list(range(1, 31)))
        self.assertTrue(all(result[i]["holm_adjusted_p"] <= result[i+1]["holm_adjusted_p"] for i in range(29)))
    def test_holm_ties_caps_and_unity_are_deterministic(self):
        result = d.holm(self.family_rows([.01, .01] + [1.] * 28))
        self.assertEqual(result[0]["holm_adjusted_p"], result[1]["holm_adjusted_p"])
        self.assertAlmostEqual(result[0]["holm_adjusted_p"], .3)
        self.assertTrue(all(0 <= row["holm_adjusted_p"] <= 1 for row in result))
        self.assertEqual(d.holm(self.family_rows([1.] * 30))[-1]["holm_adjusted_p"], 1.)
    def test_holm_missing_duplicate_reordered_or_nonfinite_family_is_rejected(self):
        for kind in ("missing", "duplicate", "order", "nan", "inf", "negative", "aboveone", "boolean"):
            tests = self.family_rows([.1] * 30)
            if kind == "missing": tests.pop()
            if kind == "duplicate": tests[1]["id"] = tests[0]["id"]
            if kind == "order": tests.reverse()
            if kind == "nan": tests[0]["raw_p"] = math.nan
            if kind == "inf": tests[0]["raw_p"] = math.inf
            if kind == "negative": tests[0]["raw_p"] = -.1
            if kind == "aboveone": tests[0]["raw_p"] = 1.1
            if kind == "boolean": tests[0]["raw_p"] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.holm(tests)


class RecountTests(unittest.TestCase):
    def test_new_extra_field_keeps_original_case_recount_and_wino_gold(self):
        shared = d.shared_api()
        class Task:
            multiple_input = True
            task_docs = [dict(choices=["X", "a long choice"], gold=0, suffix="same suffix"),
                dict(choices=["X", "a long choice"], gold=1, suffix="same suffix")]
            doc_to_choice = staticmethod(lambda doc: doc["choices"])
            doc_to_text = staticmethod(lambda doc: doc["gold"])
            doc_to_target = staticmethod(lambda doc: doc["suffix"])
            def process_results(self, doc, responses):
                return dict(acc=d.official.official.independent_row(doc["choices"], doc["gold"], [r[0] for r in responses])["acc"])
        def requests(task, doc, i):
            args = [SimpleNamespace(args=("fixed context", choice)) for choice in doc["choices"]]
            return "fixed context", doc["choices"], args
        task = Task(); contracts = shared.CaseContracts(task, 2, requests); rows = []
        for i, original in enumerate(contracts.rows):
            filtered = [[-1., False], [-2., False]]
            rows.append(dict(doc_id=i, filter="none", doc=original["doc"], arguments=original["arguments"],
                target=original["target"], **original["hashes"], filtered_resps=filtered,
                resps=[[value] for value in filtered], metrics=["acc"], acc=int(i == 0),
                native_format_recount=dict(doc_sha256=d.sha(original["doc"]))))
        before = copy.deepcopy(rows)
        value = shared.recount_task("winogrande", task, rows, expected=2, request_builder=requests, contracts=contracts)
        self.assertEqual(value["values"], [1, 0])
        self.assertEqual(len(value["correspondence"]), 4)
        self.assertEqual(rows, before)
        rows[1]["target"] = "different suffix"
        with self.assertRaises(ValueError): shared.recount_task("winogrande", task, rows, expected=2, request_builder=requests, contracts=contracts)


class PipelineTests(unittest.TestCase):
    """평가·데이터 loader를 막고 원 CPU 재계수만 작은 합성 문항으로 잇는다."""
    def test_closure_recount_statistics_and_summary_without_raw_arrays(self):
        shared = d.shared_api()
        from scripts.p106b_official_tasks import task_requests
        class Task:
            def __init__(self, name):
                self.config = SimpleNamespace(task=name, repeats=1)
                self.multiple_input = name == "winogrande"
                self.task_docs = [dict(question="RAW_QUESTION_MUST_NOT_EXPORT", choices=["X", "a long choice"], gold=i,
                    suffix="RAW_SUFFIX_MUST_NOT_EXPORT") for i in range(2)]
            def doc_to_choice(self, doc): return doc["choices"]
            def doc_to_text(self, doc): return doc["gold"] if self.multiple_input else doc["question"]
            def doc_to_target(self, doc): return doc["suffix"] if self.multiple_input else doc["gold"]
            def fewshot_context(self, doc, **kwargs):
                assert kwargs["num_fewshot"] == 0 and kwargs["apply_chat_template"] is False
                return "fixed context"
            def construct_requests(self, *, doc, ctx, **kwargs):
                return [SimpleNamespace(request_type="loglikelihood", args=(ctx, choice)) for choice in doc["choices"]]
            def process_results(self, doc, responses):
                value = d.official.official.independent_row(doc["choices"], doc["gold"], [r[0] for r in responses])
                metrics = ("acc",) if self.config.task in ("piqa", "winogrande", "boolq") else ("acc", "acc_norm")
                return {key: value[key] for key in metrics}
        with tempfile.TemporaryDirectory(prefix="native_pair_stats_pipeline_", dir="/tmp") as temporary, ExitStack() as stack:
            root = Path(temporary); counts = {name: 2 for name in d.PRIMARY}; events = []
            for name, value in (("COUNTS", counts), ("ITEMS", 12), ("REQUESTS", 24)):
                stack.enter_context(patch.object(d, name, value))
            tasks = {name: Task(name) for name in d.PRIMARY}
            contracts = {name: shared.CaseContracts(tasks[name], 2, task_requests) for name in d.PRIMARY}
            api = SimpleNamespace(Inputs=shared.Inputs, read_json=shared.read_json, decode=shared.decode,
                CaseContracts=shared.CaseContracts, recount_task=shared.recount_task, verify_audit=shared.verify_audit,
                paired_intervals=Mock(side_effect=fake_paired))
            api.load_readonly_tasks = Mock(side_effect=lambda inputs: (events.append("tasks") or tasks,
                dict(task_source_sha256={"fixture.py": "A" * 64})))
            evidence = d.Evidence(api, root=root); bundles = {}
            for model in d.NEW_MODELS:
                directory = root / model; directory.mkdir()
                checkpoint_sha = ("A" if model == "format_muon" else "B") * 64
                worker = dict(checkpoint_sha256=checkpoint_sha, sample_manifests={}, independent_audits={}, official_results={})
                for name, task in tasks.items():
                    rows = []
                    for i, contract in enumerate(contracts[name].rows):
                        scores = [-1., -2.] if model == "format_muon" else ([-.01, -10.] if i == 0 else [-10., -.01])
                        filtered = [[value, False] for value in scores]
                        metrics = task.process_results(contract["doc"], filtered)
                        rows.append(dict(doc_id=i, filter="none", doc=contract["doc"], arguments=contract["arguments"],
                            target=contract["target"], **contract["hashes"], resps=[[r] for r in filtered], filtered_resps=filtered,
                            metrics=list(metrics), **metrics, native_format_recount=dict(doc_sha256=d.sha(contract["doc"]))))
                    counted = shared.recount_task(name, task, rows, expected=2, request_builder=task_requests, contracts=contracts[name])
                    raw = d.official.ShardWriter(directory, name + "_samples", limit=19999)
                    for row in rows: raw.append(row)
                    worker["sample_manifests"][name] = raw.close(lineage=dict(schema=d.official.SCHEMA,
                        checkpoint_sha256=checkpoint_sha, task=name, mode="full"))
                    worker["independent_audits"][name] = counted["audit"]
                    worker["official_results"][name] = dict(results={name: {key + ",none": sum(row[key] for row in rows)/2 for key in metrics}})
                raw = d.official.ShardWriter(directory, "token_lengths", limit=1000)
                for i in range(24): raw.append(dict(index=i))
                worker["lengths_manifest"] = raw.close(lineage=dict(schema=d.official.SCHEMA, mode="full", checkpoint_sha256=checkpoint_sha))
                raw = d.official.ShardWriter(directory / "stdout", "stdout", limit=1000)
                raw.append(dict(fixture=True))
                stdout = raw.close(lineage=dict(schema=d.training.SCHEMA))
                report = dict(worker=worker, supervision=dict(stdout_manifest=stdout))
                bundles[model] = dict(model=model, worker=worker, report=report, directory=directory,
                    root_spec=dict(path="fixture/report.json", sha256="A" * 64), root_ref=dict(path="fixture/root.json", sha256="A" * 64),
                    profile_ref=dict(path="fixture/profile.json", sha256="A" * 64),
                    state=dict(train_spec=dict(path="fixture/train.json", sha256="A" * 64),
                        train=dict(checkpoint="runs/ckpt/never_created.pt", final_core_sha256="B" * 64)))
            corr = {name: shared.recount_task(name, tasks[name],
                list(d.official.manifests_rows(bundles["format_muon"]["directory"], bundles["format_muon"]["worker"]["sample_manifests"][name], Budget())),
                expected=2, request_builder=task_requests, contracts=contracts[name])["correspondence"] for name in d.PRIMARY}
            for peer in d.PEERS:
                ref = put(root, peer + ".json", dict(fixture=True))
                evidence.inputs.add(root / ref["path"], ref["sha256"])
                bundles[peer] = dict(model=peer, path=root / ref["path"], report=dict(fixture=True))
            def recount_peer(name, *args):
                bits = [0, 0] if name == "native595-q" else [1, 0]
                return dict(model=name, rows=12, choice_likelihoods=24, correspondence=corr,
                    values={task: bits for task in d.PRIMARY}, per_task={task: dict(primary_score=sum(bits)/2) for task in d.PRIMARY},
                    mean6=sum(bits)/2, model_proof=dict(secret="PRIVATE_PROOF_MUST_NOT_EXPORT"))
            api.recount_model = Mock(side_effect=recount_peer)
            signature = dict(sha256="A" * 64)
            prepared = dict(source=signature, evidence=evidence, models=bundles)
            def close(spec, state, mode, budget):
                model = next(name for name in d.NEW_MODELS if bundles[name]["state"] is state)
                events.append("close_" + model)
                return bundles[model]["report"]
            stack.enter_context(patch.object(d, "shared_api", return_value=api))
            stack.enter_context(patch.object(d, "source_identity", return_value=signature))
            reader = stack.enter_context(patch.object(d, "read_official_closed", side_effect=close))
            summary = d.collect(prepared, Budget())
            self.assertEqual(events[:3], ["close_format_muon", "close_format_normuon", "tasks"])
            self.assertEqual((reader.call_count, api.recount_model.call_count, api.paired_intervals.call_count), (2, 2, 5))
            self.assertEqual(len(summary["exact_tests"]), 30)
            self.assertEqual(summary["models"]["format_normuon"]["mean6"], 1.)
            self.assertEqual(summary["pairs"]["format_muon__format_normuon"]["pointwise95"]["mean6"]["right_minus_left"], .5)
            output = d.canonical(summary).decode("utf-8")
            for forbidden in ('"values"', '"doc"', '"arguments"', "RAW_QUESTION_MUST_NOT_EXPORT", "PRIVATE_PROOF_MUST_NOT_EXPORT"):
                self.assertNotIn(forbidden, output)
            self.assertFalse(summary["model_weight_bodies_read"])


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="native_pair_stats_output_", dir="/tmp")
        self.root = Path(self.tmp.name); (self.root / "test_result/evidence").mkdir(parents=True)
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(d, "ROOT", self.root))
        self.stack.enter_context(patch.object(d.supervisor, "Budget", Budget))
        self.prepared = dict(source=dict(sha256="A" * 64), config_ref=dict(path="input.json", sha256="B" * 64))
        self.stack.enter_context(patch.object(d, "prepare", return_value=self.prepared))
        self.stack.enter_context(patch.object(d, "final_check"))
        self.output = "test_result/evidence/" + d.PREFIX + "fixture"
        self.args = ["--execute", "--inputs", "fixture.json", "--inputs-sha256", "A" * 64,
            "--source-sha256", "A" * 64, "--output", self.output]
    def tearDown(self): self.stack.close(); self.tmp.cleanup()
    def run_main(self, summary):
        with patch.object(d, "collect", return_value=summary), redirect_stdout(io.StringIO()): return d.main(self.args)
    def test_summary_is_pending_until_actual_exit_and_terminal0(self):
        self.assertEqual(self.run_main(dict(pairs={}, exact_tests=[])), 0)
        path = self.root / self.output
        report = json.loads((path / "report.json").read_bytes())
        self.assertEqual((report["returncode"], report["candidate_returncode"]), (9, 0))
        self.assertEqual(report["actual_parent_exit"], "ROOT_MUST_COLLECT")
        self.assertEqual(json.loads((path / "terminal.jsonl").read_text()), dict(event="OBSERVATION", returncode=0))
        self.assertLess((path / "report.json").stat().st_size, 20_000_000)
    def test_existing_namespace_is_preserved(self):
        path = self.root / self.output; path.mkdir(); (path / "old.txt").write_text("원형", encoding="utf-8")
        self.assertEqual(self.run_main({}), 9)
        self.assertEqual((path / "old.txt").read_text(encoding="utf-8"), "원형")
        self.assertFalse((path / "terminal.jsonl").exists())
    def test_error_after_publication_appends_veto_instead_of_success(self):
        calls = []
        def printing(*args, **kwargs):
            calls.append(args)
            if len(calls) == 1: raise TimeoutError("출력 지연")
        with patch.object(d, "print", side_effect=printing, create=True): self.assertEqual(self.run_main({}), 9)
        lines = [json.loads(line) for line in (self.root / self.output / "terminal.jsonl").read_text().splitlines()]
        self.assertEqual(lines[-1]["event"], "TERMINAL_VETO")
        self.assertEqual(lines[-1]["returncode"], 9)
    def test_twenty_mb_summary_is_rejected(self):
        self.assertEqual(self.run_main(dict(fixture="x" * 20_000_000)), 9)
        self.assertFalse((self.root / self.output / "report.json").exists())


class ImportTests(unittest.TestCase):
    def test_no_cp_runtime_or_live_data_calls_in_source(self):
        tree = ast.parse(Path(d.__file__).read_text(encoding="utf-8"))
        forbidden = {"load", "load_runtime", "metadata", "load_routed_state", "selected_runtime", "routed_runtime"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, forbidden)
        self.assertIs(d.read_official_closed, d.official.read_closed)
    def test_source_only_and_missing_inputs_have_no_torch_or_model(self):
        source = """import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','tokenizers','transformers','datasets','lm_eval'}:
   raise AssertionError('모델과 raw 실행 금지')
sys.meta_path.insert(0,Block())
module=runpy.run_path(sys.argv[1],run_name='fixture_import')
assert module['main'](['--check-only'])==8
assert module['main'](['--source-only'])==0
assert 'torch' not in sys.modules
"""
        result = subprocess.run([sys.executable, "-I", "-B", "-c", source, str(Path(d.__file__).resolve())],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(data[0]["returncode"], 8)
        self.assertEqual(data[-1]["raw_reads"], 0)
    def test_old_primary_counts_and_registries_are_unchanged(self):
        shared = d.shared_api()
        self.assertEqual(d.PRIMARY, shared.PRIMARY)
        self.assertEqual(d.COUNTS, shared.COUNTS)
        self.assertEqual((sum(d.COUNTS.values()), d.COUNTS["boolq"]), (19965, 3270))
        self.assertNotIn("format_muon", shared.MODELS)
        self.assertNotIn("format_normuon", d.official.official.MODELS)
    def test_new_source_has_no_forbidden_language_characters(self):
        for name in d.OWN:
            value = (ROOT / name).read_text(encoding="utf-8")
            self.assertFalse(any(0x3040 <= ord(c) <= 0x30ff or 0x3400 <= ord(c) <= 0x9fff
                or 0xf900 <= ord(c) <= 0xfaff for c in value))


if __name__ == "__main__":
    unittest.main()
