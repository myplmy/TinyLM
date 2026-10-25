"""합성 원형/종결만 쓰는 CPU 회귀. 실제 평가자료·모델·GPU·취득은 실행하지 않는다."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
from scripts import summarize_p106b_belebele_pairs as m
from scripts.test_p106b_belebele import FixtureTask, FixtureLM
from scripts.p106b_shards import ShardWriter


def write(path, value):
    return m.write_json(Path(path), value)


def synthetic_documents():
    rows = {}
    for language in m.LANGUAGES:
        docs = []
        for index in range(900):
            cluster = index // 2 if index < 824 else 412 + index - 824
            number = index % 2 + 1 if index < 824 else 2
            doc = dict(link=f"https://example.invalid/synthetic-{cluster:04d}", question_number=number,
                flores_passage="합성 지문 " + str(cluster), question="합성 question " + str(index),
                correct_answer_num=str(index % 4 + 1), dialect=language, ds="synthetic-only")
            doc.update({"mc_answer" + str(i): "합성 보기 " + str(i) for i in range(1, 5)})
            docs.append(doc)
        rows[language] = docs if language == m.LANGUAGES[0] else list(reversed(docs))
    return rows


def closed(directory, report, signature):
    directory.mkdir(parents=True)
    sha = write(directory / "report.json", report)
    closure = dict(schema=m.evaluation.CLOSURE_SCHEMA, tag=m.evaluation.TAG,
        model=report["model"], mode=report["mode"], status="CLOSED_WITHIN_OBSERVED_BOUNDS", returncode=0,
        source_sha256=signature["sha256"], report_sha256=sha, admission=report["admission"],
        report_closed_re_read=True, contract=m.evaluation.CLOSURE_CONTRACT,
        root_actual_exit0_required=True, atomicity_claim=False, observed_elapsed_seconds=2.,
        observed_wall_epoch=m.evaluation.base.control.LATEST_DEADLINE - 1000)
    write(directory / "phase_closure.json", closure)
    return sha


class SyntheticFulls:
    """1800/7200와7모델 token manifest 형태를 갖춘 합성 파일만 만든다."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.source = m.source_identity()
        self.signature = self.source["evaluator_source"]
        self.models = ("qwen06", "gemma270")
        self.documents = synthetic_documents()
        self.tasks = {language: FixtureTask(docs) for language, docs in self.documents.items()}
        self.data_audit = m.evaluation.align_languages(self.documents)
        self.assets_directory = self.directory / "assets"
        self.assets_directory.mkdir()
        self.assets = {}
        for language, docs in self.documents.items():
            path = self.assets_directory / (language + ".jsonl")
            body = b"".join(m.canonical(doc) + b"\n" for doc in docs)
            with path.open("xb") as stream:
                stream.write(body)
            self.assets[language] = dict(path=str(path), bytes=len(body), sha256=m.digest(path), synthetic=True)
        self.task_proof = dict(official_definition_sources={}, storage="SYNTHETIC_ONLY", tasks={})
        self.common = set(m.evaluation.key_for(doc) for doc in self.documents[m.LANGUAGES[0]][:-2])
        self.plans = {}
        for language, task in self.tasks.items():
            self.plans[language] = {}
            for index, doc in enumerate(task.eval_docs):
                plans = [m.evaluation.token_plan(FixtureLM(), request)
                    for request in m.evaluation.requests_for(task, doc, index)]
                if m.evaluation.key_for(doc) not in self.common:
                    plans[0]["truncated_context_tokens"] = 1  # 합성 사전 동결 표지; 모델 호출0.
                self.plans[language][index] = plans
        prepare = self.directory / "prepare"
        writer = ShardWriter(prepare, "token_lengths", limit=19_999_999)
        for model in m.MODELS:
            for language, docs in self.documents.items():
                for index, doc in enumerate(docs):
                    writer.append(dict(model=model, language=language, doc_id=index,
                        key=list(m.evaluation.key_for(doc)), plans=self.plans[language][index],
                        untruncated=m.evaluation.key_for(doc) in self.common))
        manifest = writer.close(lineage=dict(models=list(m.MODELS), languages=list(m.LANGUAGES),
            forward_calls=0, quality_claim=False))
        prepared = self.report(None, "prepare")
        prepared.update(model_loads=0, gpu_calls=0, frozen_tokens=dict(models=list(m.MODELS),
            frozen_before_model_output=True, model_instances=0, forward_calls=0, gpu_calls=0,
            token_manifest=manifest, common_keys=[list(key) for key in sorted(self.common)],
            common_rows_per_language=898))
        # writer가 prepare를 이미 만들었다.
        closed(prepare / "temporary_holder", prepared, self.signature)
        for name in ("report.json", "phase_closure.json"):
            (prepare / "temporary_holder" / name).rename(prepare / name)
        prepare_sha = m.digest(prepare / "report.json")
        for model_index, model in enumerate(self.models):
            canary = self.report(model, "canary")
            canary.update(prepare_report_sha256=prepare_sha, numerical_canary_passed=True)
            canary_sha = closed(self.directory / model / "canary", canary, self.signature)
            cost = self.report(model, "cost")
            cost.update(prepare_report_sha256=prepare_sha, canary_report_sha256=canary_sha,
                actual_counts=dict.fromkeys(m.LANGUAGES, 32), actual_rows=64, actual_choice_likelihoods=256,
                raw_independent_recount=True, sample_manifests=dict.fromkeys(m.LANGUAGES, {}),
                independent_audits=dict.fromkeys(m.LANGUAGES, {}))
            cost_path = self.directory / model / "cost/report.json"
            cost_sha = closed(cost_path.parent, cost, self.signature)
            full = self.report(model, "full")
            full.update(prepare_report_sha256=prepare_sha, canary_report_sha256=canary_sha,
                input_pins={str(cost_path): cost_sha}, actual_counts=dict.fromkeys(m.LANGUAGES, 900),
                actual_rows=1800, actual_choice_likelihoods=7200, raw_independent_recount=True,
                auxiliary_common_rows_per_language=898, sample_manifests={}, independent_audits={})
            directory = self.directory / model / "full"
            for language, task in self.tasks.items():
                writer = ShardWriter(directory, language + "_samples", limit=19_999_999)
                for index, doc in enumerate(task.eval_docs):
                    gold = int(doc["correct_answer_num"]) - 1
                    correct = (int(doc["question"].rsplit(" ", 1)[-1]) + model_index) % 3 != 0
                    selected = gold if correct else (gold + 1) % 4
                    responses = [[-1. if i == selected else -5., False] for i in range(4)]
                    _, metrics = m.evaluation.item_metrics(task, doc, responses)
                    writer.append(dict(doc_id=index, language=language, key=list(m.evaluation.key_for(doc)), doc=doc,
                        arguments=[list(request.args) for request in m.evaluation.requests_for(task, doc, index)],
                        responses=responses, metrics=metrics, plans=self.plans[language][index],
                        common_untruncated=m.evaluation.key_for(doc) in self.common))
                manifest = writer.close(lineage=dict(task="belebele_" + language, model=model, mode="full",
                    revision=m.evaluation.REVISION))
                full["sample_manifests"][language] = manifest
                full["independent_audits"][language] = m.evaluation.recount_raw(task, task.eval_docs,
                    language, directory, manifest, 900, self.plans[language], self.common)
            closed(directory / "temporary_holder", full, self.signature)
            for name in ("report.json", "phase_closure.json"):
                (directory / "temporary_holder" / name).rename(directory / name)

    def report(self, model, mode):
        return dict(schema=m.evaluation.SCHEMA, tag=m.evaluation.TAG, source_identity=self.signature,
            model=model, mode=mode, status={"prepare": "BELEBELE_PREPARED", "canary": "BELEBELE_CANARY_COMPLETE",
                "cost": "BELEBELE_COST_COMPLETE", "full": "BELEBELE_FULL_COMPLETE"}[mode],
            returncode=0, policy=m.evaluation.policy(model), sources_unchanged=True, inputs_unchanged=True,
            training=False, optimizer_updates=0, checkpoint_writes=0, body_unchanged=True, owned_cleanup_complete=True,
            model_identity=dict(model=model, synthetic=True), model_proof=dict(synthetic=True), wall_seconds=1.,
            admission=dict(hard_cap_seconds=600, cleanup_reserve_seconds=30,
                deadline_epoch=m.evaluation.base.control.LATEST_DEADLINE),
            data_assets=self.assets, data_audit=self.data_audit, task_contract=self.task_proof)


class ClusterTests(unittest.TestCase):
    def outcomes(self):
        keys = [("a", 1), ("a", 2), ("b", 1)]
        values = {model: {language: dict(zip(keys, (1, 1, 0) if index == 0 else (0, 0, 1)))
            for language in m.LANGUAGES} for index, model in enumerate(("left", "right"))}
        return values, keys, {keys[0], keys[2]}

    def test_question_weighted_not_cluster_macro_matches_direct_replication(self):
        weights = np.asarray([[1, 1], [2, 0], [0, 2]], dtype=np.int64)
        result = m.sample_means(np, weights, np.asarray([2, 1]), np.asarray([[2], [0]]))[:, 0]
        expected = [sum([1, 1] * int(row[0]) + [0] * int(row[1])) / (2 * row[0] + row[1]) for row in weights]
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(result[0], 2 / 3)
        self.assertNotEqual(result[0], .5)

    def test_shared_cluster_draws_all_models_languages_subsets_match_direct_expansion(self):
        values, keys, common = self.outcomes()
        actual = m.cluster_intervals(values, keys, common, draws=200, seed=7, chunk=13)
        rng = np.random.default_rng(7)
        weights = rng.multinomial(2, [.5, .5], size=200)
        raw = {"main900": [], "common_untruncated898": []}
        for weight in weights:
            selected = [key for i, link in enumerate(("a", "b")) for _ in range(int(weight[i])) for key in keys if key[0] == link]
            raw["main900"].append(sum(values["left"][m.LANGUAGES[0]][key] for key in selected) / len(selected))
            aux = [key for key in selected if key in common]
            raw["common_untruncated898"].append(sum(values["left"][m.LANGUAGES[0]][key] for key in aux) / len(aux))
        for name in m.SUBSETS:
            row = actual["subsets"][name]
            for language in m.LANGUAGES:
                np.testing.assert_array_equal(row["scores"]["left"][language]["ci95"], np.quantile(raw[name], [.025, .975]))
                delta = 1 - 2 * np.asarray(raw[name])
                np.testing.assert_array_equal(row["pairs"]["left__right"]["languages"][language]["ci95"], np.quantile(delta, [.025, .975]))
        self.assertEqual(actual["shared_draws_sha256"], hashlib.sha256(weights.astype("<i8").tobytes()).hexdigest().upper())

    def test_chunking_preserves_draw_sequence_and_intervals(self):
        values, keys, common = self.outcomes()
        a = m.cluster_intervals(values, keys, common, draws=300, chunk=1)
        b = m.cluster_intervals(values, keys, common, draws=300, chunk=512)
        self.assertEqual(a["subsets"], b["subsets"])
        self.assertEqual(a["shared_draws_sha256"], b["shared_draws_sha256"])

    def test_empty_selected_question_denominator_is_error_not_resampled(self):
        with self.assertRaises(ValueError):
            m.sample_means(np, np.asarray([[2, 0]]), np.asarray([0, 1]), np.asarray([[0], [1]]))

    def test_bad_correspondence_nonbinary_nan_and_empty_common_are_rejected(self):
        values, keys, common = self.outcomes()
        for kind in ("missing", "extra", "nan", "infinity", "nonbinary", "empty"):
            altered = copy.deepcopy(values)
            row = altered["left"][m.LANGUAGES[0]]
            if kind == "missing":
                row.pop(keys[0])
            elif kind == "extra":
                row[("c", 1)] = 1
            elif kind != "empty":
                row[keys[0]] = {"nan": float("nan"), "infinity": float("inf"), "nonbinary": .5}[kind]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                m.cluster_intervals(altered, keys, set() if kind == "empty" else common, draws=10)

    def test_baselines_are_separate_random_majority_and_always_A(self):
        row = m.baseline([0, 1, 1, 1])
        self.assertEqual(row["uniform_random"], dict(expected_accuracy=.25, sampled=False))
        self.assertEqual(row["majority_label"]["label"], "B")
        self.assertEqual(row["majority_label"]["accuracy"], .75)
        self.assertEqual(row["always_A"]["accuracy"], .25)

    def test_100000_draws_900_questions_488_clusters_7models_bounded_shape(self):
        docs = synthetic_documents()[m.LANGUAGES[0]]
        keys = [m.evaluation.key_for(doc) for doc in docs]
        values = {model: {language: {key: (index + model_index) % 2 for index, key in enumerate(keys)}
            for language in m.LANGUAGES} for model_index, model in enumerate(m.MODELS)}
        started = time.perf_counter()
        with m.shared.cpu_wall_limit(120):
            row = m.cluster_intervals(values, keys, set(keys[:-2]))
        self.assertEqual(row["resamples"], 100000)
        self.assertEqual(row["seed"], 20261024)
        self.assertEqual(row["max_weight_shape"], [512, 488])
        self.assertEqual(row["sample_array_bytes"], 2 * 100000 * 14 * 8)
        self.assertEqual(row["subsets"]["main900"]["scores"][m.MODELS[0]][m.LANGUAGES[0]]["accuracy"], .5)
        self.assertLess(time.perf_counter() - started, 120)
        print("[SYNTHETIC_CLUSTER] draws=100000 keys=900 links=488 common=898 models=7 sample_bytes=22400000 seconds="
              + f"{time.perf_counter() - started:.6f}")


class FullReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="p106b_belebele_pairs_synthetic_")
        cls.fixture = SyntheticFulls(Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def collect(self, models=None):
        f = self.fixture
        with patch.object(m.evaluation, "DATA", f.assets_directory), \
                patch.object(m.evaluation, "read_assets", return_value=(f.documents, f.assets, f.data_audit)) as read, \
                patch.object(m.evaluation, "load_tasks", return_value=(f.tasks, f.task_proof)):
            result = m.collect(f.models if models is None else models, expected_source=f.source["sha256"], evidence_root=f.directory)
            read.assert_called_once_with(allow_download=False)
            return result

    def test_synthetic_full1800_7200_raw_recount_and_source_unchanged(self):
        result, check = self.collect()
        self.assertTrue(check())
        self.assertEqual(result["exact_pairing"]["rows"], 900)
        self.assertEqual(result["exact_pairing"]["links"], 488)
        self.assertEqual(result["exact_pairing"]["common_untruncated_rows"], 898)
        self.assertFalse(result["raw_modified"])
        self.assertFalse(result["model_weight_bodies_read"])
        for audits in result["independent_audits"].values():
            self.assertEqual(sum(row["rows"] for row in audits.values()), 1800)
            self.assertEqual(sum(row["choice_likelihoods"] for row in audits.values()), 7200)
        print("[SYNTHETIC_FULL_RECOUNT] models=2 rows_per_model=1800 choices_per_model=7200 raw_unchanged=True")

    def test_missing_or_unselected_model_never_opens_assets_or_task(self):
        f = self.fixture
        with patch.object(m.evaluation, "read_assets") as assets, patch.object(m.evaluation, "load_tasks") as tasks:
            with self.assertRaises(m.IncompleteFull):
                m.collect(["falcon90m"], expected_source=f.source["sha256"], evidence_root=f.directory)
            assets.assert_not_called()
            tasks.assert_not_called()
        for models in ([], ["qwen06", "qwen06"], ["not_registered"]):
            with self.assertRaises(ValueError):
                m.collect(models, expected_source=f.source["sha256"], evidence_root=f.directory)

    def test_source_replacement_and_wrong_pin_rejected_before_raw(self):
        f = self.fixture
        with patch.object(m.evaluation, "identity", return_value=dict(sha256="0" * 64)):
            with self.assertRaises(ValueError):
                m.source_identity()
        with self.assertRaises(ValueError):
            m.collect(f.models, expected_source="0" * 64, evidence_root=f.directory)

    def test_late_source_replacement_is_caught_by_returned_final_check(self):
        _, check = self.collect(models=["qwen06"])
        with patch.object(m, "source_identity", return_value=dict(sha256="0" * 64)):
            with self.assertRaises(ValueError):
                check()

    def test_prepare_and_full_closure_report_mutation_or_veto_rejected(self):
        f = self.fixture
        original = f.directory / f.models[0] / "full"
        for mode in ("missing", "closure", "report", "veto", "nan"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                directory = Path(name)
                report, closure = m.read_json(original / "report.json"), m.read_json(original / "phase_closure.json")
                if mode == "report":
                    report["status"] = "HOLD"
                if mode == "closure":
                    closure["report_sha256"] = "0" * 64
                write(directory / "report.json", report)
                if mode != "missing":
                    write(directory / "phase_closure.json", closure)
                if mode == "veto":
                    write(directory / "phase_veto.json", dict(status="VETO"))
                if mode == "nan":
                    (directory / "phase_closure.json").write_text('{"nan":NaN}', encoding="utf-8")
                with self.assertRaises(ValueError):
                    m.Evidence(f.signature).closed(directory / "report.json", f.models[0], "full")

    def test_partial_counts_wrong_policy_or_cleanup_cannot_be_full(self):
        f = self.fixture
        report = m.read_json(f.directory / f.models[0] / "full/report.json")
        for key, value in (("actual_rows", 1799), ("actual_choice_likelihoods", 7199), ("returncode", 8),
                ("mode", "cost"), ("raw_independent_recount", False), ("owned_cleanup_complete", False),
                ("body_unchanged", False), ("partial_artifacts", {"left": True})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.admit_report(dict(report, **{key: value}), f.models[0], "full")

    def test_input_replacement_strict_20mb_and_invalid_raw_nan(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "fixture.json"
            write(path, dict(value=1))
            inputs = m.shared.Inputs()
            inputs.add(path)
            path.write_text('{"value":2}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                inputs.unchanged()
            for raw in ('{"x":NaN}', '{"x":1e309}'):
                path.write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    m.Evidence(self.fixture.signature).json(path)
            with path.open("wb") as stream:
                stream.truncate(20_000_000)
            with self.assertRaises(ValueError):
                m.read_json(path)
            with self.assertRaises(ValueError):
                m.write_json(Path(name) / "too_large.json", "x" * 20_000_000)

    def test_partial_or_hash_valid_semantically_wrong_raw_is_rejected(self):
        f, language, model = self.fixture, m.LANGUAGES[0], self.fixture.models[0]
        directory = f.directory / model / "full"
        report = m.read_json(directory / "report.json")
        original = []
        for spec in report["sample_manifests"][language]["shards"]:
            original.extend(m.evaluation.decode(line) for line in (directory / spec["path"]).read_text(encoding="utf-8").splitlines())
        for kind in ("partial", "key", "document", "plan", "request", "nan", "metric"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                rows = copy.deepcopy(original)
                if kind == "partial":
                    rows.pop()
                elif kind == "key":
                    rows[0]["key"][0] += "-wrong"
                elif kind == "document":
                    rows[0]["doc"]["question"] += "-wrong"
                elif kind == "plan":
                    rows[0]["plans"][0]["target_start"] += 1
                elif kind == "request":
                    rows[0]["arguments"][0][1] = "A"  # 원 선행공백 삭제도 거부한다.
                elif kind == "nan":
                    rows[0]["responses"][0][0] = float("nan")
                else:
                    rows[0]["metrics"]["acc"] = 1 - rows[0]["metrics"]["acc"]
                writer = ShardWriter(Path(name), "synthetic", limit=19_999_999)
                for row in rows:
                    writer.append(row)
                manifest = writer.close(lineage=dict(synthetic=True))
                with self.assertRaises(ValueError):
                    m.evaluation.recount_raw(f.tasks[language], f.documents[language], language, Path(name),
                        manifest, 900, f.plans[language], f.common)

    def test_manifest_size_is_rejected_before_hash_and_linked_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            writer = ShardWriter(directory, "synthetic", limit=19999999)
            writer.append(dict(synthetic=True))
            manifest = writer.close(lineage=dict(synthetic=True))
            path = directory / manifest["shards"][0]["path"]
            with path.open("ab") as stream:
                stream.write(b"changed")
            evidence = m.Evidence(self.fixture.signature)
            with patch.object(evidence.inputs, "add", wraps=evidence.inputs.add) as add:
                with self.assertRaises(ValueError):
                    evidence.manifest(directory, manifest, "synthetic", dict(synthetic=True), 1)
                self.assertEqual(add.call_count, 1)  # 작은 manifest만 읽었고 큰 raw는 해시하지 않았다.
            link = directory / "linked.json"
            link.symlink_to(directory / "synthetic_shards_manifest.json")
            with self.assertRaises(ValueError):
                m.read_json(link)


class BoundaryTests(unittest.TestCase):
    def synthetic_report(self):
        return dict(schema=m.SCHEMA, tag=m.TAG, status="SYNTHETIC_ONLY", returncode=0,
                    selected_models=["qwen06"], source_identity=dict(sha256="a" * 64))

    def test_exclusive_output_readback_and_raw_not_copied(self):
        with tempfile.TemporaryDirectory() as name, patch.object(m, "collect", return_value=(self.synthetic_report(), lambda: True)):
            target = Path(name) / "fresh"
            report, _ = m.bounded_run(["qwen06"], "a" * 64, target=target)
            receipt = m.read_json(target / "outputs.json")
            self.assertEqual(receipt["report_sha256"], m.digest(target / "report.json"))
            self.assertEqual(receipt["raw_examples_copied"], 0)
            before = (target / "report.json").read_bytes()
            with self.assertRaises(FileExistsError):
                m.bounded_run(["qwen06"], "a" * 64, target=target)
            self.assertEqual((target / "report.json").read_bytes(), before)
            self.assertFalse((target / "veto.json").exists())
            self.assertFalse(report["atomic_process_exit_guarantee"])

    def test_delayed_report_or_receipt_write_read_is_vetoed_without_overwrite(self):
        for operation in ("report_write", "report_read", "receipt_write", "receipt_read"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as name:
                now = [0.]
                real_write, real_read = m.write_json, m.read_json
                def write_delay(path, value):
                    result = real_write(path, value)
                    if operation == ("report_write" if path.name == "report.json" else "receipt_write"):
                        now[0] = 120.1
                    return result
                def read_delay(path):
                    result = real_read(path)
                    if operation == ("report_read" if path.name == "report.json" else "receipt_read"):
                        now[0] = 120.1
                    return result
                target = Path(name) / "new"
                with patch.object(m, "collect", return_value=(self.synthetic_report(), lambda: True)), \
                        patch.object(m, "write_json", side_effect=write_delay), patch.object(m, "read_json", side_effect=read_delay):
                    with self.assertRaises(TimeoutError):
                        m.bounded_run(["qwen06"], "a" * 64, target=target, clock=lambda: now[0])
                self.assertTrue((target / "report.json").exists())
                self.assertTrue((target / "veto.json").exists())

    def test_120_second_cap_and_active_alarm_are_not_overridden(self):
        for cap in (0, 121, 1.5):
            with self.assertRaises(ValueError):
                with m.shared.cpu_wall_limit(cap):
                    self.fail("invalid cap must not enter")
        with m.shared.cpu_wall_limit(120):
            with self.assertRaises(ValueError):
                with m.shared.cpu_wall_limit(120):
                    self.fail("existing alarm must remain owned")
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)

    def test_check_only_is_source_only_and_cli_requires_explicit_models(self):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(m, "collect") as collect:
            self.assertEqual(m.main(["--check-only"]), 0)
            collect.assert_not_called()
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["raw_reads"], 0)
        self.assertEqual(receipt["models_loaded"], 0)
        with redirect_stderr(io.StringIO()):
            for args in (["--read-only"], ["--read-only", "--models", "qwen06"],
                         ["--execute", "--models", "qwen06", "--source-sha256", "a"]):
                with self.assertRaises(SystemExit):
                    m.main(args)

    def test_cli_missing_full_is_hold8_not_zero_score_and_existing_output_is_error9(self):
        with patch.object(m, "bounded_run", side_effect=m.IncompleteFull("synthetic full not run")), \
                redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
            self.assertEqual(m.main(["--read-only", "--models", "qwen06", "--source-sha256", "a"]), 8)
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(json.loads(error.getvalue())["status"], "INCOMPLETE_FULL_HOLD")
        with patch.object(m, "output_path", side_effect=FileExistsError("preserve prior output")), \
                redirect_stderr(io.StringIO()) as error:
            self.assertEqual(m.main(["--execute", "--models", "qwen06", "--source-sha256", "a", "--output-stamp", "old"]), 9)
            self.assertEqual(json.loads(error.getvalue())["status"], "CPU_RECOUNT_ERROR")


if __name__ == "__main__":
    unittest.main()
