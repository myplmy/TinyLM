"""공식 LAMBADA default 제어기의 순수 CPU 회귀. 실자산·모델·GPU는 열지 않는다."""
from __future__ import annotations

import ast
from contextlib import redirect_stderr
import io
import json
import math
from pathlib import Path
import tempfile
import tarfile
from types import SimpleNamespace
import unittest

from scripts import diag_p106b_lambada_default as m
from scripts.p106b_shards import ShardWriter, verify


class FixtureTask:
    def __init__(self, texts=("A short context lastword", "One  two", "Standalone")):
        self.eval_docs = [dict(text=text) for text in texts]
        self.config = SimpleNamespace(repeats=1)

    def doc_to_text(self, doc):
        return " ".join(doc["text"].split(" ")[:-1])

    def doc_to_target(self, doc):
        return " " + doc["text"].split(" ")[-1]

    def fewshot_context(self, doc, **kwargs):
        if kwargs != dict(num_fewshot=0, apply_chat_template=False,
                          fewshot_as_multiturn=False, system_instruction=None):
            raise AssertionError("공식 0shot/chatOFF 경계가 변경됐다")
        return self.doc_to_text(doc)

    def construct_requests(self, doc, ctx, metadata, apply_chat_template):
        if ctx != self.doc_to_text(doc) or apply_chat_template or metadata[0] != m.TASK:
            raise AssertionError("공식 요청 조건이 변경됐다")
        return SimpleNamespace(request_type="loglikelihood", args=(ctx, self.doc_to_target(doc)))

    def process_results(self, doc, results):
        (ll, greedy), = results
        return dict(perplexity=ll, acc=int(greedy))

    def aggregation(self):
        return dict(acc=lambda values: sum(values) / len(values),
                    perplexity=lambda values: math.exp(-sum(values) / len(values)))


class FixtureLM:
    prefix_token_id = 1
    core = SimpleNamespace(vocab_size=32)

    def tok_encode(self, text, add_special_tokens=False):
        if add_special_tokens:
            raise AssertionError("추가 BOS를 삽입하지 않는다")
        return [ord(char) % 25 + 2 for char in text]

    def _encode_pair(self, context, continuation):
        return self.tok_encode(context), self.tok_encode(continuation)

    def loglikelihood(self, requests, disable_tqdm=True):
        return [(-float(len(request.args[1])), index % 2 == 0) for index, request in enumerate(requests)]


class PrefixFixtureLM(FixtureLM):
    def tok_encode(self, text, add_special_tokens=False):
        return [self.prefix_token_id, 3, 4]


class BadAggregationTask(FixtureTask):
    def aggregation(self):
        return dict(acc=lambda values: 1., perplexity=lambda values: 1.)


class WrongMetricTask(FixtureTask):
    def process_results(self, doc, results):
        return dict(perplexity=0., acc=1)


class MissingResponseLM(FixtureLM):
    def loglikelihood(self, requests, disable_tqdm=True):
        return []


class LambadaTests(unittest.TestCase):
    def metadata(self):
        return dict(bytes=m.DATA_BYTES, sha256=m.DATA_SHA.lower(), rows=5153, columns=["text"])

    def task_yaml(self):
        return dict(task="lambada_openai", dataset_path="EleutherAI/lambada_openai", dataset_name="default",
            output_type="loglikelihood", test_split="test", doc_to_text=m.PROMPT, doc_to_target=m.TARGET,
            metric_list=[dict(metric="perplexity", aggregation="perplexity", higher_is_better=False),
                         dict(metric="acc", aggregation="mean", higher_is_better=True)])

    def cost(self):
        return dict(schema=m.SCHEMA, tag=m.TAG, task=m.TASK, mode="cost", model="falcon90m", returncode=0,
            status="LAMBADA_COST_COMPLETE", source_identity={"fixture": True}, policy=m.policy("falcon90m"),
            sources_unchanged=True, inputs_unchanged=True, raw_independent_recount=True, actual_rows=32,
            canary_report_sha256="fixture-canary", evaluation_seconds=10., wall_seconds=20.)

    def admission(self):
        return m.control.window(m.control.DEADLINE_ISO, 7200, "full", now=m.control.LATEST_DEADLINE - 10000)

    def record(self, task, index=0, response=(-3., False)):
        doc = task.eval_docs[index]
        request = m.request_for(task, doc, index)
        return m.record_for(task, doc, index, request, response, m.token_plan(FixtureLM(), request))

    def write(self, directory, rows):
        writer = ShardWriter(directory, "samples", limit=600)
        for row in rows:
            writer.append(row)
        return writer.close(lineage=dict(fixture=True))

    def test_default_alias_uses_exact_provider_revision_bytes_and_lfs_sha(self):
        proof = m.alias_contract(self.metadata())
        self.assertTrue(proof["byte_identical_alias"])
        self.assertEqual(proof["official_config"], "default")
        self.assertEqual(proof["remote_lfs_sha256"], m.DATA_SHA)
        self.assertIn(m.REVISION, proof["remote_api_url"])
        self.assertEqual(proof["remote_path"], "default/test/default.parquet")
        self.assertFalse(proof["remote_request_in_this_driver"])
        self.assertEqual(proof["rows"], m.ROWS)

    def test_alias_never_promotes_equal_row_count_to_byte_identity(self):
        for key, value in (("sha256", "A" * 64), ("bytes", m.DATA_BYTES + 1), ("rows", 5152),
                           ("columns", ["text", "label"])):
            data = self.metadata(); data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.alias_contract(data)

    def test_pinned_task_preserves_prompt_target_and_both_official_metrics(self):
        task_yaml = self.task_yaml()
        kept = m.validate_config(task_yaml)
        self.assertEqual(kept["doc_to_target"], "{{' '+text.split(' ')[-1]}}")
        task_yaml["metric_list"][0]["aggregation"] = "mean"
        self.assertEqual(kept["metric_list"][0]["aggregation"], "perplexity")

    def test_mt_en_and_rewritten_target_or_metric_are_rejected(self):
        for key, value in (("task", "lambada_openai_mt_en"), ("dataset_name", "en"),
                           ("test_split", "validation"), ("doc_to_target", "{{text}}"),
                           ("metric_list", [])):
            task_yaml = self.task_yaml(); task_yaml[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_config(task_yaml)

    def definition_fixture(self, directory):
        source, runtime = directory / "source", directory / "runtime"
        source.mkdir(); runtime.mkdir()
        archive_path = directory / "official.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for index, name in enumerate(("task.py", "metrics.py", "loader.py")):
                body = f"# 합성 공식 정의 fixture {index}\n".encode()
                for folder in (source, runtime):
                    with (folder / name).open("xb") as stream:
                        stream.write(body)
                item = tarfile.TarInfo("lm-evaluation-harness-fixture/" + name)
                item.size = len(body)
                archive.addfile(item, io.BytesIO(body))
        return source, runtime, archive_path, m.control.original.digest(archive_path)

    def test_task_definitions_must_match_archive_preserved_source_and_runtime(self):
        with tempfile.TemporaryDirectory() as name:
            source, runtime, archive, sha = self.definition_fixture(Path(name))
            result = m.verify_definition_sources(source, runtime, archive, sha, "fixture", ("task.py", "metrics.py", "loader.py"))
            self.assertEqual(len(result), 3)
            self.assertEqual(result["task.py"]["sha256"], m.control.original.digest(source / "task.py"))
            with (runtime / "task.py").open("ab") as stream:
                stream.write(b"# changed\n")
            with self.assertRaises(ValueError):
                m.verify_definition_sources(source, runtime, archive, sha, "fixture", ("task.py",))

    def test_definition_source_archive_sha_path_escape_and_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            source, runtime, archive, sha = self.definition_fixture(Path(name))
            for digest, names in (("A" * 64, ("task.py",)), (sha, ("../task.py",))):
                with self.assertRaises(ValueError):
                    m.verify_definition_sources(source, runtime, archive, digest, "fixture", names)
            linked = Path(name) / "linked"; linked.symlink_to(runtime, target_is_directory=True)
            with self.assertRaises(ValueError):
                m.verify_definition_sources(source, linked, archive, sha, "fixture", ("task.py",))

    def test_official_last_space_boundary_and_empty_context_are_preserved(self):
        task = FixtureTask()
        self.assertEqual(m.request_for(task, task.eval_docs[1], 1).args, ("One ", " two"))
        self.assertEqual(m.request_for(task, task.eval_docs[2], 2).args, ("", " Standalone"))
        self.assertGreater(m.token_plan(FixtureLM(), m.request_for(task, task.eval_docs[0], 0))["continuation_tokens"], 1)

    def test_empty_context_uses_one_prefix_without_duplicating_native_prefix(self):
        request = SimpleNamespace(args=("", " target"))
        normal = m.token_plan(FixtureLM(), request)
        prefixed = m.token_plan(PrefixFixtureLM(), request)
        self.assertEqual(normal["original_context_tokens"], 1)
        self.assertEqual(prefixed["original_context_tokens"], 1)
        self.assertEqual(prefixed["continuation_tokens"], 2)

    def test_left_truncation_never_removes_target_subwords(self):
        request = SimpleNamespace(args=("x" * 1500, " target"))
        plan = m.token_plan(FixtureLM(), request)
        self.assertEqual(plan["continuation_tokens"], len(" target"))
        self.assertEqual(plan["input_tokens"], 1024)
        self.assertGreater(plan["truncated_context_tokens"], 0)
        self.assertEqual(plan["target_start"] + plan["continuation_tokens"], 1024)
        with self.assertRaises(ValueError):
            m.token_plan(FixtureLM(), SimpleNamespace(args=("prefix", "x" * 1025)))

    def test_greedy_requires_actual_bool_for_the_complete_target(self):
        self.assertEqual(m.valid_response((-2., False)), (-2., False))
        for response in ((-2., 0), (-2., 1), (float("nan"), False), (float("inf"), True),
                         (1., True), (True, False), (-2., False, True), None):
            with self.subTest(response=response), self.assertRaises(ValueError):
                m.valid_response(response)

    def test_acc_and_perplexity_are_itemwise_not_token_normalized(self):
        value = m.independent_metrics([(-1., True), (-3., False)])
        self.assertEqual(value["acc"], .5)
        self.assertAlmostEqual(value["perplexity"], math.exp(2.))
        with self.assertRaises(ValueError):
            m.independent_metrics([])

    def test_official_metric_and_independent_oracles_must_agree(self):
        task = FixtureTask()
        records = [self.record(task, 0, (-1., True)), self.record(task, 1, (-3., False))]
        self.assertEqual(m.aggregate(task, records), dict(acc=.5, perplexity=math.exp(2.)))
        with self.assertRaises(ValueError):
            m.aggregate(BadAggregationTask(), records)
        with self.assertRaises(ValueError):
            self.record(WrongMetricTask())

    def test_lossless_raw_recount_preserves_order_docs_args_metrics_and_lengths(self):
        task = FixtureTask()
        records = [self.record(task, i, (-i - 1., i == 0)) for i in range(3)]
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); manifest = self.write(directory, records)
            self.assertGreater(len(manifest["shards"]), 1)
            recount = m.recount_raw(task, directory, manifest, 3)
            self.assertEqual(recount["rows"], 3)
            self.assertAlmostEqual(recount["metrics"]["acc"], 1 / 3)
            self.assertTrue(recount["raw_sha_verified"])
            self.assertEqual(recount["total_continuation_tokens"], sum(r["token_plan"]["continuation_tokens"] for r in records))

    def test_recount_refuses_recorded_target_rewrites_or_partial_denominators(self):
        task = FixtureTask()
        changes = (lambda row: row.update(doc_id=2), lambda row: row.update(doc=dict(text="다른 원문")),
                   lambda row: row.update(arguments=["A short context", " last"]),
                   lambda row: row["official_metrics"].update(acc=1),
                   lambda row: row["token_plan"].update(continuation_tokens=0),
                   lambda row: row["token_plan"].update(kept_context_tokens=0),
                   lambda row: row["token_plan"].update(target_start=100))
        for change in changes:
            row = self.record(task); change(row)
            with tempfile.TemporaryDirectory() as name:
                directory = Path(name); manifest = self.write(directory, [row])
                with self.assertRaises(ValueError):
                    m.recount_raw(task, directory, manifest, 1)
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); manifest = self.write(directory, [self.record(task)])
            with self.assertRaises(ValueError):
                m.recount_raw(task, directory, manifest, 2)

    def test_cost_evaluation_is_first32_without_quality_claim(self):
        task = FixtureTask([f"synthetic context target{i}" for i in range(33)])
        with tempfile.TemporaryDirectory() as name:
            report = dict(model="falcon90m")
            m.evaluate(task, FixtureLM(), "cost", Path(name), report, lambda: None)
            self.assertEqual(report["actual_rows"], 32)
            self.assertFalse(report["quality_claim"])
            self.assertTrue(report["raw_independent_recount"])
            self.assertEqual(report["sample_manifest"]["rows"], 32)

    def test_timeout_retains_completed_raw_without_promoting_partial(self):
        task = FixtureTask([f"synthetic context target{i}" for i in range(32)])
        calls = []
        def check():
            calls.append(1)
            if len(calls) > 1:
                raise TimeoutError("합성 fixture 시간 상한")
        with tempfile.TemporaryDirectory() as name:
            report = dict(model="falcon90m")
            with self.assertRaises(TimeoutError):
                m.evaluate(task, FixtureLM(), "cost", Path(name), report, check)
            manifest = report["partial_pair_manifest"]
            self.assertEqual(manifest["rows"], 8)
            verify(Path(name), manifest)
            self.assertNotIn("raw_independent_recount", report)

    def test_boundary_canary_is_synthetic_and_not_a_quality_result(self):
        result = m.boundary_canary(FixtureTask(), FixtureLM())
        self.assertTrue(result["passed"])
        self.assertFalse(result["quality_claim"])
        self.assertEqual(result["request_arguments"][1], ["One ", " two"])
        with self.assertRaises(ValueError):
            m.boundary_canary(FixtureTask(), MissingResponseLM())

    def test_forecast_uses_exact5153_cost32_multiplier_overhead_and_cleanup(self):
        value = m.full_admission(self.cost(), {"fixture": True}, "falcon90m", self.admission(),
                                 "fixture-canary", now=m.control.LATEST_DEADLINE - 10000)
        self.assertAlmostEqual(value["forecast_seconds"], 10 * 5153 / 32 * 1.5 + 10 + 120)
        self.assertEqual(value["hard_cap_seconds"], 7200)

    def test_cost_requires_same_source_model_canary_policy_and_full_raw32(self):
        changes = (("schema", "old"), ("tag", "old"), ("task", "lambada_openai_mt_en"),
                   ("source_identity", {}), ("model", "gemma270"), ("policy", {}),
                   ("actual_rows", 31), ("canary_report_sha256", "old"), ("returncode", 9),
                   ("raw_independent_recount", False), ("sources_unchanged", False), ("inputs_unchanged", False))
        for key, value in changes:
            cost = self.cost(); cost[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.full_admission(cost, {"fixture": True}, "falcon90m", self.admission(),
                                 "fixture-canary", now=m.control.LATEST_DEADLINE - 10000)

    def test_v2_namespace_does_not_relabel_preserved_v1_cost(self):
        self.assertEqual(m.TAG, "p106b_lambada_default_v2_s1337")
        self.assertEqual(m.SCHEMA, "P106B_LAMBADA_DEFAULT_V2")
        cost = self.cost()
        cost.update(tag="p106b_lambada_default_v1_s1337", schema="P106B_LAMBADA_DEFAULT_V1")
        with self.assertRaises(ValueError):
            m.full_admission(cost, {"fixture": True}, "falcon90m", self.admission(),
                             "fixture-canary", now=m.control.LATEST_DEADLINE - 10000)

    def test_nonfinite_or_overbudget_forecast_does_not_enter_full(self):
        for key, value in (("evaluation_seconds", float("nan")), ("evaluation_seconds", -1.),
                           ("wall_seconds", True), ("wall_seconds", 1.), ("evaluation_seconds", 1000.)):
            cost = self.cost(); cost[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                m.full_admission(cost, {"fixture": True}, "falcon90m", self.admission(),
                                 "fixture-canary", now=m.control.LATEST_DEADLINE - 10000)
        with self.assertRaises(ValueError):
            m.full_admission(self.cost(), {"fixture": True}, "falcon90m", self.admission(),
                             "fixture-canary", now=m.control.LATEST_DEADLINE - 2000)

    def test_model_identity_includes_hf_tokenizer_assets_and_implementation(self):
        proof = dict(initial_core_sha256="core", model_source_sha256="source")
        one = m.model_identity("gemma270", proof, dict(tokenizer="A"))
        two = m.model_identity("gemma270", proof, dict(tokenizer="B"))
        self.assertNotEqual(one, two)
        self.assertEqual(one["model_source_sha256"], "source")
        native = m.model_identity("native595-f", dict(provenance=dict(checkpoint_sha256="cp", tokenizer_sha256="tok")))
        self.assertEqual(native["tokenizer_sha256"], "tok")

    def test_existing_strict_model_proof_binds_native_and_falcon_exit_pins(self):
        pins = {}
        proof = dict(provenance=dict(checkpoint="runs/ckpt/synthetic.pt", checkpoint_sha256="cp", tokenizer_sha256="tok"))
        m.bind_model_pins("native595-f", proof, pins)
        self.assertEqual(pins["runs/ckpt/synthetic.pt"], "cp")
        self.assertIn("data_cache/tok-ko-en-32768-chat32.json", pins)
        with self.assertRaises(ValueError):
            m.bind_model_pins("falcon90m", dict(asset_sha256={"../escape": "bad"}), {})
        proof["provenance"]["checkpoint"] = "../escape"
        with self.assertRaises(ValueError):
            m.bind_model_pins("native595-f", proof, {})

    def test_exit_audit_failure_cannot_leave_full_quality_claim_true(self):
        for verify_fn, identity_fn in ((lambda pins: False, lambda: {"source": True}),
                                       (lambda pins: None, lambda: {"source": False})):
            with tempfile.TemporaryDirectory() as name:
                report = dict(returncode=0, status="LAMBADA_DEFAULT_COMPLETE", quality_claim=True)
                m.finalize(report, Path(name), m.time.perf_counter(), {"source": True}, {"fixture": "pin"},
                           verify_fn=verify_fn, identity_fn=identity_fn)
                saved = json.loads((Path(name) / "report.json").read_text())
                self.assertEqual(saved["returncode"], 9)
                self.assertFalse(saved["quality_claim"])
                self.assertFalse(report["quality_claim"])

    def test_partial_runtime_import_failure_keeps_original_error_with_unbound_idle(self):
        tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
        execute = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute")
        guarded = next(index for index, node in enumerate(execute.body) if isinstance(node, ast.Try))
        initialized = {target.id for node in execute.body[:guarded]
                       if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is None
                       for target in node.targets if isinstance(target, ast.Name)}
        self.assertTrue({"torch", "require_idle_gpu", "primary_error"}.issubset(initialized))
        for torch_loaded in (False, True):
            with self.subTest(torch_loaded=torch_loaded), tempfile.TemporaryDirectory() as name:
                calls = []
                torch = SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda: calls.append("empty_cache"))) if torch_loaded else None
                primary = ImportError("합성 attention/helper import 실패; idle callback은 아직 없다")
                report = dict(returncode=9, status="LAMBADA_DEFAULT_PARTIAL", quality_claim=False,
                              error_type=type(primary).__name__, error=str(primary))
                m.finish_execution(report, Path(name), m.time.perf_counter(), {"source": True}, {"fixture": "pin"},
                    torch=torch, idle_fn=None, primary_error=primary,
                    identity_fn=lambda: {"source": True}, verify_fn=lambda pins: None)
                saved = json.loads((Path(name) / "report.json").read_text())
                self.assertEqual(saved["error_type"], "ImportError")
                self.assertEqual(saved["error"], str(primary))
                self.assertEqual(saved["returncode"], 9)
                self.assertEqual(calls, ["empty_cache"] if torch_loaded else [])
                self.assertEqual(saved.get("owned_cleanup_complete", False), torch_loaded)

    def test_evaluation_and_report_serialization_failure_preserve_original_error(self):
        with tempfile.TemporaryDirectory() as name:
            primary = TimeoutError("합성 평가의 원 시간 상한 오류")
            report = dict(schema=m.SCHEMA, tag=m.TAG, model="falcon90m", mode="full",
                returncode=9, status="LAMBADA_DEFAULT_PARTIAL", quality_claim=False,
                error_type=type(primary).__name__, error=str(primary), unsupported=object())
            result = m.finalize(report, Path(name), m.time.perf_counter(), {"source": True}, {"fixture": "pin"},
                primary_error=primary, identity_fn=lambda: {"source": True}, verify_fn=lambda pins: None)
            self.assertIs(result, report)
            saved = json.loads((Path(name) / "report.json").read_text())
            self.assertEqual(saved["original_error"], dict(type="TimeoutError", message=str(primary)))
            self.assertEqual(saved["report_closure_error"]["type"], "TypeError")
            self.assertEqual(saved["status"], "LAMBADA_DEFAULT_PARTIAL")
            self.assertEqual(saved["returncode"], 9)
            self.assertFalse(saved["quality_claim"])

    def test_cli_requires_explicit_action_source_and_model_but_prepare_is_common(self):
        for args in ((), ("--execute",), ("--execute", "--source-sha256", "x", "--mode", "cost"),
                     ("--execute", "--source-sha256", "x", "--model", "falcon90m"),
                     ("--check-only", "--model", "qwen3508")):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                m.main(args)
        self.assertEqual(len(m.MODELS), 7)

    def test_no_model_import_at_module_load_and_no_runtime_monkeypatch(self):
        source = Path(m.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
        self.assertFalse(any(name.startswith(("torch", "transformers", "datasets", "pyarrow", "lm_eval")) for name in imports))
        self.assertNotIn("patch.object", source)
        self.assertNotIn("globals()", source)
        assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
        self.assertFalse(any(isinstance(target, ast.Attribute) and target.attr.startswith("_loglikelihood")
                             for node in assignments for target in node.targets))


if __name__ == "__main__":
    unittest.main()
