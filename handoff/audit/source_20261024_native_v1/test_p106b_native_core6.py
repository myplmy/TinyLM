"""Pure CPU native protocol/orchestration contracts; no compiled worker run."""
from __future__ import annotations
import ast
import base64
import builtins
from contextlib import nullcontext, redirect_stdout
import io
import json
import math
from pathlib import Path
import runpy
import struct
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import p106b_native_core6 as run


def original_template_fixture():
    """Compile exact original encoding bodies, without importing model libraries."""
    path = run.ROOT / "data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/api/model.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TemplateLM")
    nodes = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in {"_encode_pair", "loglikelihood"}]
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    namespace = {"tqdm": lambda iterable, **kwargs: iterable}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future]+nodes, type_ignores=[])), str(path), "exec"), namespace)
    return type("OriginalTemplateFixture", (), {name: namespace[name] for name in ("_encode_pair", "loglikelihood")})


class NativeContracts(unittest.TestCase):
    def test_pure_import_and_check_only_never_start_backend_or_read_models(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "tokenizers", "datasets", "lm_eval", "tinylm"}:
                raise AssertionError("unexpected heavy import: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded), patch.object(run, "asset_identity") as assets, \
                patch.object(run.subprocess, "Popen") as popen:
            runpy.run_path(str(Path(run.__file__)), run_name="pure_native_import")
            out = io.StringIO()
            with redirect_stdout(out): self.assertEqual(run.main(["--check-only"]), 0)
            receipt = json.loads(out.getvalue())
            self.assertEqual((receipt["models"], receipt["backend_initializations"]), (0, 0))
            assets.assert_not_called(); popen.assert_not_called()

    def test_exact_compile_header_closure_and_existing_hf_source_are_pinned(self):
        signature = run.identity()
        self.assertEqual(signature["build"]["commit"], run.COMMIT)
        manifest = run.read_json(run.HEADERS / "headers_manifest.json")
        self.assertEqual(len(manifest["files"]), 8)
        allowed = {Path(name).name for name in manifest["files"]}
        for name in manifest["files"]:
            path = run.HEADERS / name
            if path.suffix != ".h": continue
            for line in path.read_text().splitlines():
                if line.startswith('#include "'):
                    self.assertIn(line.split('"')[1], allowed)
        self.assertEqual(run.digest(run.ROOT / "scripts/diag_p106b_external_core6.py"),
            "4B06EFAA64A31C7E4C9F879531B662CA7EABFBEB0A848DB67668FC0F3370605A")
        self.assertEqual(run.digest(run.ROOT / "scripts/test_p106b_external_core6.py"),
            "325C87E67DDA17AE55137EBFACB39B11D02E2930257BD9228FDA327824E1E7CA")

    def test_compiled_worker_is_not_invoked_by_tests_and_has_no_sampler(self):
        source = (run.ROOT / "scripts/p106b_native_llama_worker.cpp").read_text()
        self.assertNotIn("llama_sampler_sample(", source)
        self.assertNotIn("llama_model_params {", source)
        self.assertIn('if(argv[2]!=allowed)', source)
        self.assertIn("llama_memory_clear(llama_get_memory(ctx),true)", source)
        self.assertIn("batch.pos[i]=int32_t(i)", source)
        self.assertIn("cp.type_k=GGML_TYPE_F32;cp.type_v=GGML_TYPE_F32", source)

    def test_deadline_and_per_model_whole_phase_bounds(self):
        deadline = "2026-10-24T08:40:00+09:00"
        for model in run.REGISTRY:
            self.assertEqual(run.validate_execution(model, "canary", deadline, 300, now=run.DEADLINE-301)["hard_cap_seconds"], 300)
        for model, mode, cap, stop, now in (("other", "canary", 300, deadline, 0),
                ("gpt2_q4km", "canary", 299, deadline, 0), ("gpt2_q4km", "cost", 599, deadline, 0),
                ("gpt2_q4km", "full", 7201, deadline, 0), ("gpt2_q4km", "cost", 600, deadline, run.DEADLINE-599),
                ("gpt2_q4km", "canary", 300, "2026-10-24T08:41:00+09:00", 0)):
            with self.subTest(model=model, cap=cap), self.assertRaises(run.AdmissionHold):
                run.validate_execution(model, mode, stop, cap, now=now)

    def test_source_mismatch_and_existing_partial_stop_before_model(self):
        with patch.object(run, "identity", return_value={"sha256": "A"}), patch.object(run, "asset_identity") as assets:
            with self.assertRaises(run.AdmissionHold): run.execute("gpt2_q4km", "canary", "B", "2026-10-24T08:40:00+09:00", 300)
            assets.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/"gpt2_q4km/canary"; target.mkdir(parents=True)
            with patch.object(run, "OUTPUT", Path(tmp)), patch.object(run, "identity", return_value={"sha256": "A"}), \
                    patch.object(run, "validate_execution", return_value={}):
                with self.assertRaises(FileExistsError): run.execute("gpt2_q4km", "canary", "A", "2026-10-24T08:40:00+09:00", 300)

    def test_wire_reader_requires_complete_bounded_values(self):
        self.assertEqual(run.Reader(struct.pack("<I", 7)).u32(), 7)
        for raw in (b"", b"abc"):
            with self.assertRaises(ValueError): run.Reader(raw).u32()
        with self.assertRaises(ValueError): run.Reader(b"trailing").end()
        with self.assertRaises(ValueError): run.Reader(struct.pack("<I", 100)+b"x").string()
        for ids in ([True], [-1], [1.5], [2**31]):
            with self.assertRaises(ValueError): run.ints(ids)
        self.assertEqual(run.ints([0, 1]), struct.pack("<I2i", 2, 0, 1))

    def worker(self):
        records = []
        worker = run.Worker({}, {}, run.DEADLINE, SimpleNamespace(append=records.append), {})
        worker.process = SimpleNamespace(stdin=SimpleNamespace(fileno=lambda: 11), stdout=SimpleNamespace(fileno=lambda: 12))
        worker.info = dict(vocab_size=256, eos_id=255, prefix_id=255)
        return worker, records

    def test_rpc_preserves_exact_bytes_and_checks_reply_id_and_status(self):
        for actual_id, status in ((1, 0), (9, 0), (1, 1)):
            with self.subTest(actual_id=actual_id, status=status):
                worker, records = self.worker()
                body = b"ok" if status == 0 else struct.pack("<I", 5)+b"error"
                response = struct.pack("<III", 2, actual_id, status)+body
                with patch.object(worker, "transfer", side_effect=[b"", struct.pack("<I", len(response)), response]) as transport:
                    if actual_id == 1 and status == 0: self.assertEqual(worker.rpc(2, b"input"), b"ok")
                    else:
                        with self.assertRaises((ValueError, RuntimeError)): worker.rpc(2, b"input")
                self.assertEqual(base64.b64decode(records[0]["wire_b64"]), struct.pack("<II", 2, 1)+b"input")
                self.assertEqual(base64.b64decode(records[1]["wire_b64"]), response)
                self.assertEqual(transport.call_args_list[0].kwargs["data"], struct.pack("<I", 13)+struct.pack("<II", 2, 1)+b"input")

    def test_rpc_frame_cap_fails_without_sending(self):
        worker, _ = self.worker()
        with patch.object(run, "MAX_FRAME", 16), patch.object(worker, "transfer") as transfer:
            with self.assertRaises(ValueError): worker.rpc(3, b"x"*20)
            transfer.assert_not_called()
        worker, _ = self.worker()
        with patch.object(worker, "transfer", side_effect=[b"", struct.pack("<I", run.MAX_FRAME+1)]) as transfer:
            with self.assertRaises(ValueError): worker.rpc(3)
            self.assertEqual(transfer.call_count, 2)

    def test_native_tokenizer_sends_raw_utf8_and_explicit_special_flags(self):
        worker, _ = self.worker()
        with patch.object(worker, "rpc", return_value=run.ints([1, 2])) as rpc:
            self.assertEqual(worker.tokenize("한국어"), [1, 2])
            self.assertEqual(rpc.call_args.args[1], struct.pack("<II", 2, len("한국어".encode()))+"한국어".encode())
            worker.tokenize("A", True)
            self.assertEqual(struct.unpack("<I", rpc.call_args.args[1][:4]), (3,))
        with patch.object(worker, "rpc", return_value=struct.pack("<I", 2)+b"\xff\x00"):
            self.assertEqual(worker.detokenize([1]), b"\xff\x00")

    def test_complete_sum_target_logp_and_greedy_are_independently_checked(self):
        plan = run.plan_tokens([1, 2], [3, 4], 256)
        response = struct.pack("<IdI", 2, -3., 0)+struct.pack("<dIdI", -1., 1, -2., 0)
        worker, _ = self.worker()
        with patch.object(worker, "rpc", return_value=response) as rpc:
            self.assertEqual(worker.score(plan), ((-3., False), [(-1., 1), (-2., 0)]))
            self.assertEqual(rpc.call_args.args, (3, run.ints(plan.input_ids)+struct.pack("<I", 1)+run.ints([3, 4])))
        for total, greedy, p in ((-2., 0, -1.), (float("nan"), 0, -1.), (-3., 1, -1.), (-1., 0, 1.)):
            response = struct.pack("<IdI", 2, total, greedy)+struct.pack("<dIdI", p, 1, -2., 0)
            with patch.object(worker, "rpc", return_value=response), self.assertRaises(ValueError): worker.score(plan)

    def test_raw_full_logits_frame_dimensions_and_bytes_are_preserved(self):
        worker, _ = self.worker(); worker.info["vocab_size"] = 3
        raw = struct.pack("<6f", 1, 2, 3, 4, 5, 6)
        with patch.object(worker, "rpc", return_value=struct.pack("<II", 2, 3)+raw):
            self.assertEqual(worker.logits([0, 1], [0, 1]), raw)
        with patch.object(worker, "rpc", return_value=struct.pack("<II", 3, 3)+raw), self.assertRaises(ValueError):
            worker.logits([0, 1], [0, 1])

    def scorer(self):
        original = original_template_fixture()
        worker = SimpleNamespace(info=dict(vocab_size=256, eos_id=255, prefix_id=255), calls=[])
        mapping = {"ab": [8], "abc": [9, 10], "a": [1], "a b": [1, 4], " b": [4], "x": [7], "": []}
        worker.tokenize = lambda text, add_special=False: mapping.get(text, list(text.encode()))
        def score(plan): worker.calls.append(plan); return (-float(len(plan.continuation_ids)), False), []
        worker.score = score
        lm = run.adapter_type(original)(worker)
        self.assertIs(type(lm)._encode_pair, original._encode_pair)
        return lm

    def test_original_bpe_whole_then_split_and_trailing_space_contract(self):
        lm = self.scorer()
        self.assertEqual(lm._encode_pair("ab", "c"), ([8], [10]))
        self.assertEqual(lm._encode_pair("a ", "b"), ([1], [4]))
        self.assertEqual(lm.loglikelihood([SimpleNamespace(args=("", "x"))]), [(-1., False)])
        self.assertEqual(lm.worker.calls[-1].input_ids, (255,))
        self.assertEqual(lm.worker.calls[-1].continuation_ids, (7,))
        with self.assertRaises(ValueError): lm.loglikelihood([SimpleNamespace(args=("", ""))])

    def test_every_candidate_is_admitted_before_any_forward(self):
        lm = self.scorer()
        with self.assertRaises(ValueError): lm._loglikelihood_tokens([(("a", "b"), [1], [2]), (("x", "y"), [1], [256])])
        self.assertEqual(lm.worker.calls, [])
        with self.assertRaises(ValueError): lm._loglikelihood_tokens([(("x", "y"), [1], [2]*1025)])
        self.assertEqual(lm.worker.calls, [])

    def test_loss_shift_and_1024_context_keep_every_target(self):
        plan = run.plan_tokens([1]*1030, [2, 3], 256)
        self.assertEqual((len(plan.input_ids), plan.target_start, plan.truncated_context_tokens), (1024, 1022, 7))
        self.assertEqual(plan.labels[-2:], (2, 3))
        self.assertEqual(plan.input_ids[-1], 2)
        for position, target in enumerate(plan.continuation_ids, plan.target_start):
            single = run.plan_tokens(plan.input_ids[:position+1], [target], 256)
            self.assertEqual(single.input_ids, plan.input_ids[:position+1])
            self.assertEqual(single.labels[-1], target)

    def test_cleanup_failure_does_not_replace_active_primary_error(self):
        worker, _ = self.worker()
        with patch.object(worker, "close", side_effect=RuntimeError("cleanup failed")):
            worker.__exit__(ValueError, None, None)
            self.assertEqual(worker.proof["cleanup_error"], "cleanup failed")
            with self.assertRaisesRegex(RuntimeError, "cleanup failed"): worker.__exit__(None, None, None)

    def test_existing_memory_retry_recovers_only_bounded_timeouts_and_discloses_gaps(self):
        worker, _ = self.worker(); worker.process.poll = lambda: None
        outcomes = iter([run.subprocess.TimeoutExpired("fixture", 5), run.subprocess.TimeoutExpired("fixture", 5), (9000, 7000)])
        calls = []
        def source():
            calls.append(1); result = next(outcomes)
            if isinstance(result, Exception): raise result
            return result
        reader = worker.retrying_memory(source, emit=lambda _: None); reader.pause = lambda _: None
        self.assertEqual(reader(), (9000, 7000)); self.assertEqual(len(calls), 3)
        proof = reader.snapshot()
        self.assertEqual((proof["maximum_attempts"], proof["per_query_timeout_sec"], proof["retry_delay_sec"]), (3, 5, .2))
        self.assertEqual(proof["measurement_coverage"], "GAPPED")
        self.assertEqual(proof["timeout_attempts"], 2)
        self.assertFalse(proof["continuous_peak_verified"]); self.assertEqual(proof["oom_safety"], "NOT_ESTABLISHED")

    def test_persistent_query_failure_and_low_free_are_never_recovered_as_safe(self):
        worker, _ = self.worker(); worker.process.poll = lambda: None; worker.process.pid = 123
        for error, expected in ((run.subprocess.TimeoutExpired("fixture", 5), 3), (RuntimeError("driver"), 1)):
            calls = []
            def source(): calls.append(1); raise error
            reader = worker.retrying_memory(source, emit=lambda _: None); reader.pause = lambda _: None
            with self.assertRaises(type(error)): reader()
            self.assertEqual(len(calls), expected); self.assertEqual(reader.snapshot()["fatal_calls"], 1)
        calls = []
        def low(): calls.append(1); return 16000, 62
        reader = worker.retrying_memory(low, emit=lambda _: None)
        with self.assertRaises(MemoryError): worker.observe_memory(reader, lambda _: 100)
        self.assertEqual(len(calls), 1); self.assertEqual(worker.samples, [])
        self.assertEqual(reader.snapshot()["observed_min_free_mib"], 62)

    def test_worker_death_and_deadline_guard_do_not_retry_or_query(self):
        worker, _ = self.worker(); worker.process.poll = lambda: 9
        def forbidden(): raise AssertionError("query must not start")
        reader = worker.retrying_memory(forbidden, emit=lambda _: None)
        with self.assertRaises(ChildProcessError): reader()
        worker.process.poll = lambda: None
        with patch.object(run.time, "time", return_value=worker.stop-4):
            with self.assertRaises(TimeoutError): reader()
        worker.sample_stop.set()
        with self.assertRaises(InterruptedError): reader()

    def test_cleanup_cancellation_does_not_hide_persistent_timeout_or_low_free(self):
        worker, _ = self.worker(); worker.sample_stop.set()
        worker.sampling_error(InterruptedError("explicit shutdown"))
        worker.sampling_error(ChildProcessError("expected owned exit"))
        self.assertEqual(worker.telemetry_errors, [])
        worker.sampling_error(run.subprocess.TimeoutExpired("fixture", 5))
        worker.sampling_error(MemoryError("low free"))
        self.assertEqual(worker.telemetry_errors, ["TimeoutExpired", "MemoryError"])

    def test_source_and_native_precision_receipts_do_not_claim_hf_equivalence(self):
        value = run.policy()
        self.assertTrue(value["use_cache"])
        self.assertFalse(value["cross_choice_prefix_reuse"])
        self.assertIn("NOT_HF_FP32", value["precision"])
        self.assertIn("qwen35_08b_iq2xxs", run.REGISTRY)
        self.assertIn("bonsai2_2b_ptq1", value["unsupported_models"])

    def test_same_model_closed_canary_and_weighted_cost_are_mandatory(self):
        signature, assets = {"sha256": "A"}, {"native": True}
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)):
            common = dict(schema=run.SCHEMA, tag=run.TAG, model="gpt2_q4km", source_identity=signature,
                assets=assets, policy=run.policy(), returncode=0)
            for mode in ("canary", "cost"): (Path(tmp)/"gpt2_q4km"/mode).mkdir(parents=True)
            canary = Path(tmp)/"gpt2_q4km/canary/report.json"
            run.write_json(canary, dict(common, mode="canary", status="NATIVE_CANARY_COMPLETE", numerical_canary={"passed": True}))
            times = {name: 2. if name == "hellaswag" else 1. for name in run.official.TASK_COUNTS}
            run.write_json(Path(tmp)/"gpt2_q4km/cost/report.json", dict(common, mode="cost", status="NATIVE_LIMITED_COST_DIAGNOSTIC",
                actual_counts=run.official.expected_counts("cost"), raw_independent_recount=True,
                task_evaluation_seconds=times, pre_evaluation_seconds=10., prerequisites={"canary_report_sha256": run.digest(canary)}))
            value = run.prerequisites("gpt2_q4km", "full", signature, assets)
            self.assertAlmostEqual(value["forecast_seconds"], 1.3*sum(run.official.TASK_COUNTS[name]*v/32 for name, v in times.items())+70)
            with self.assertRaises(run.AdmissionHold): run.prerequisites("gpt2_q4km", "full", {"sha256": "B"}, assets)
            with self.assertRaises(run.AdmissionHold): run.prerequisites("qwen35_08b_iq2xxs", "cost", signature, assets)

    def test_report_retains_native_integer_labels_sets_and_unknown_type_rejection(self):
        value = dict(model_proof={"loading_info": {"keys": set()}}, independent_audits={"task": {"labels": {0: 19, 1: 13}}})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.json"; run.close_report(path, value)
            self.assertEqual(run.read_json(path)["independent_audits"]["task"]["labels"], {"0": 19, "1": 13})
            with self.assertRaises(FileExistsError): run.write_json(path, value)
        with self.assertRaises(TypeError): run.support.json_ready({"unsupported": object()})
        with self.assertRaises(ValueError): run.support.json_ready({"labels": {0: 1, "0": 2}})

    def test_limited_http_crosscheck_has_strict_small_scope(self):
        with self.assertRaises(ValueError): run.limited_http_canary(None, None, [])
        with self.assertRaises(ValueError): run.limited_http_canary(None, None, [("a", "b")]*5)

    def test_six_first32_cost_orchestration_closes_raw_and_serializes_integer_audits(self):
        class Task:
            multiple_input = False
            def __init__(self, name):
                self.name = name
                self.eval_docs = [dict(choices=["A", "BB"], gold=index%2) for index in range(32)]
            def doc_to_choice(self, doc): return doc["choices"]
            def doc_to_target(self, doc): return doc["gold"]
        tasks = {name: Task(name) for name in run.official.TASK_COUNTS}
        def evaluate(**kwargs):
            task = kwargs["tasks"][0]
            kwargs["model"]._loglikelihood_tokens([(("A", "B"), [1], [2]) for _ in range(64)])
            rows = [dict(doc_id=index, doc=doc, filtered_resps=[[-1., True], [-2., False]],
                acc=int(doc["gold"]==0), acc_norm=int(doc["gold"]==0)) for index, doc in enumerate(task.eval_docs)]
            return dict(samples={task.name: rows}, results={task.name: {"acc,none": .5, "acc_norm,none": .5}}, configs={})
        evaluator = ModuleType("lm_eval.evaluator"); evaluator.simple_evaluate = evaluate
        manager = ModuleType("lm_eval.tasks"); manager.TaskManager = lambda: object()
        utilities = ModuleType("lm_eval.utils")
        def refuse(value): raise TypeError(type(value).__name__)
        utilities.handle_non_serializable = refuse
        lm = SimpleNamespace(_loglikelihood_tokens=lambda requests, **kwargs: [(-1., True)]*len(requests))
        report = dict(model="SYNTHETIC_NOT_A_NATIVE_EVALUATION", quality_claim=False)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {
                "lm_eval.evaluator": evaluator, "lm_eval.tasks": manager, "lm_eval.utils": utilities}):
            run.evaluate_tasks(lm, Path(tmp), report, tasks, "cost")
            self.assertEqual(report["actual_counts"], run.official.expected_counts("cost"))
            self.assertEqual(report["choice_likelihoods"], 384)
            self.assertTrue(report["raw_independent_recount"])
            self.assertEqual(report["token_lengths_summary"]["requests"], 384)
            self.assertEqual(report["independent_audits"]["piqa"]["posthoc_label_counts"], {0: 16, 1: 16})
            path = Path(tmp)/"cpu_fixture_only.json"; run.close_report(path, report)
            self.assertEqual(run.read_json(path)["independent_audits"]["piqa"]["posthoc_label_counts"], {"0": 16, "1": 16})

    def test_idle_admission_failure_preserves_primary_report_without_worker(self):
        from scripts import prepare_p106b_official_eval as prepare
        from scripts import p106b_official_tasks as tasks
        from scripts import interactive_research_infer as inference
        primary = run.AdmissionHold("synthetic native GPU occupied")
        signature = {"sha256": "S", "build": {}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, "OUTPUT", Path(tmp)), \
                patch.object(run, "identity", return_value=signature), patch.object(run, "asset_identity", return_value={}), \
                patch.object(run, "validate_execution", return_value={"deadline_epoch": run.DEADLINE, "hard_cap_seconds": 300}), \
                patch.object(run, "prerequisites", return_value={}), patch.object(run.support, "phase_wall_limit", return_value=nullcontext()), \
                patch.object(prepare, "configure_hf_cache", return_value={}), patch.object(tasks, "load_tasks", return_value=({}, [], {})), \
                patch.object(inference, "require_idle_gpu", side_effect=primary), patch.object(run, "Worker") as worker:
            with self.assertRaises(run.AdmissionHold) as caught:
                run.execute("gpt2_q4km", "canary", "S", "2026-10-24T08:40:00+09:00", 300)
            self.assertIs(caught.exception, primary); worker.assert_not_called()
            report = run.read_json(Path(tmp)/"gpt2_q4km/canary/report.json")
            self.assertEqual(report["status"], "NATIVE_PREREQUISITE_HOLD")
            self.assertEqual(report["error"], str(primary)); self.assertTrue(report["sources_unchanged"])


if __name__ == "__main__": unittest.main()
