"""합성 원형과 종결 영수증만 사용하는 CPU 회귀. 실제8모델 통계/모델/GPU는 실행하지 않는다."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import summarize_p106b_native_core6_pairs as m
from scripts.test_summarize_p106b_core6_pairs import FakeTask, requests, fixture_rows, fixture_report
from scripts.p106b_shards import ShardWriter


def replace_json(path, value):
    """Only newly created synthetic temporary evidence may be replaced by a test."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(m.canonical(value) + b"\n")
    return m.digest(path)


class BundleFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.source = dict(sha256="F" * 64, window=dict(sha256=m.WINDOW_SHA, synthetic=True))
        self.path = self.root / m.REPORT_REL
        self.terminal_path = self.path.parent / "terminal_receipt.json"
        self.audit_path = self.root / m.ROOT_AUDIT_REL
        self.prior = dict(synthetic_original_canary_cost_hold=True)
        self.original_pins = {}
        for mode in ("canary", "cost", "full"):
            path = self.root / "test_result/evidence" / m.window.native.TAG / m.MODEL / mode / "report.json"
            self.original_pins[mode] = replace_json(path, dict(synthetic_old_mode=mode))
        spec = m.window.native.REGISTRY[m.MODEL]
        acquisition = self.root / Path(spec["path"]).parent / "manifest.json"
        asset_sha = replace_json(acquisition, {key: spec[key] for key in ("revision", "bytes", "sha256")})
        self.report = dict(schema=m.window.SCHEMA, tag=m.window.TAG, model=m.MODEL, mode="full", returncode=9,
            status="NATIVE_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL", candidate_returncode=0,
            candidate_status="NATIVE_WINDOW_FULL_COMPLETE", source_identity=self.source["window"],
            sources_unchanged=True, source_assets_unchanged=True, original_prerequisites_unchanged=True,
            actual_counts=dict(m.shared.COUNTS), choice_likelihoods=67106, raw_independent_recount=True,
            framework_commit=m.shared.assets.COMMIT, data_manifest_sha256=m.shared.assets.MANIFEST_SHA,
            policy=m.window.native.policy(), training=False, optimizer_updates=0, checkpoint_writes=0,
            token_lengths_summary=dict(requests=67106), prerequisites=self.prior,
            assets=dict(model=m.MODEL, path=str(self.root / spec["path"]),
                **{key: spec[key] for key in ("architecture", "revision", "bytes", "sha256")},
                acquisition_manifest_sha256=asset_sha),
            admission=dict(hard_cap_seconds=10800, deadline_epoch=m.window.native.DEADLINE),
            started_at="2026-10-23T18:00:00+00:00", ended_at="2026-10-23T18:00:10+00:00", wall_seconds=10.,
            gpu_idle_after_worker=dict(competing_compute_pids=[]), model_proof=dict(owned_pid=123,
                worker_cleanup_complete=True, worker_returncode=0, telemetry_errors=[], resource_sample_count=1,
                native_info=dict(n_batch=1, n_ubatch=1, vocab_size=50257)),
            numerical_canary=dict(passed=True, status="COMPLETE", atol=m.window.native.ATOL, rtol=m.window.native.RTOL,
                boundary_input_tokens=1024, boundary_target_logits=2,
                checks=[dict(future_token=dict(passed=True)) for _ in range(6)],
                comparisons=[dict(status="PASSED", atol=m.window.native.ATOL, rtol=m.window.native.RTOL,
                    actual=[[-1., False]], expected=[[-1., False]]) for _ in range(19)]),
            sample_manifests={name: dict(lineage=dict(tag=m.window.native.TAG, model=m.MODEL, task=name, mode="full"))
                              for name in m.shared.COUNTS},
            independent_audits=dict.fromkeys(m.shared.COUNTS, {}), official_results=dict.fromkeys(m.shared.COUNTS, {}))
        self.terminal = dict(schema=m.window.SCHEMA, tag=m.window.TAG, model=m.MODEL, mode="full", returncode=0,
            status="NATIVE_WINDOW_FULL_COMPLETE", source_sha256=m.WINDOW_SHA, deadline_epoch=m.window.native.DEADLINE,
            hard_cap_seconds=10800, acceptance_requires="SUCCESS_CANDIDATE_ONLY_UNTIL_PROCESS_EXIT0_AND_NO_TERMINAL_FAILURE_RECEIPT",
            external_root_hardcap_required=True, final_exit_reserve_seconds=1,
            atomic_process_exit_or_storage_durability_guaranteed=False,
            observation_before_receipt_write=dict(spent_seconds=10., whole_remaining_seconds=10790., absolute_remaining_seconds=10000.))
        self.audit = dict(schema="ROOT_GPT2_FULL_CLOSURE_V1", report_path=m.REPORT_REL,
            actual_parent_exit=0, primary_report_returncode=9, primary_report_status=self.report["status"],
            terminal_returncode=0, terminal_status=self.terminal["status"], raw_recount=True,
            counts=dict(m.shared.COUNTS), choices=67106, host_gpu_compute_query_exit=0, host_competing_compute_pids=[],
            worker_cleanup_complete=True, worker_returncode=0, training=False, checkpoint_writes=0,
            owned_host_pids_absent=[123, 124], monotonic_wall_seconds=10., calendar_elapsed_seconds=10.,
            started_at=self.report["started_at"], ended_at=self.report["ended_at"], clock_difference_cause="UNKNOWN")
        self.save()

    def save(self):
        self.report_sha = replace_json(self.path, self.report)
        self.terminal["report_sha256"] = self.report_sha
        self.terminal_sha = replace_json(self.terminal_path, self.terminal)
        self.audit.update(report_sha256=self.report_sha, terminal_sha256=self.terminal_sha,
                          report_bytes=self.path.stat().st_size)
        self.audit_sha = replace_json(self.audit_path, self.audit)

    def patches(self):
        stack = ExitStack()
        for name, value in (("REPORT_SHA", self.report_sha), ("TERMINAL_SHA", self.terminal_sha),
                            ("ROOT_AUDIT_SHA", self.audit_sha), ("ORIGINAL_PINS", self.original_pins)):
            stack.enter_context(patch.object(m, name, value))
        stack.enter_context(patch.object(m, "verify_original_prerequisites", return_value=self.prior))
        return stack

    def read(self):
        return m.native_bundle(self.source, m.Evidence(), self.root)


class LargeTask(FakeTask):
    def __init__(self, name, count):
        self.multiple_input = name == "winogrande"
        self.config = SimpleNamespace(task=name, repeats=1)
        self.task_docs = []
        for index in range(count):
            choices = 2 if name in ("piqa", "winogrande", "boolq") else 4
            if name == "arc_easy" and index < 4:
                choices -= 1  # 19965/67106의 정확한 합성 분모를 유지한다.
            self.task_docs.append(dict(question=f"synthetic {name} question {index}",
                choices=list("ABCD"[:choices]), gold=index % choices))
        self.eval_docs = self.task_docs

    def fewshot_context(self, doc, **kwargs):
        assert kwargs == dict(num_fewshot=0, apply_chat_template=False, fewshot_as_multiturn=False, system_instruction=None)
        return doc["question"]

    def construct_requests(self, doc, ctx, metadata, apply_chat_template):
        assert not apply_chat_template and metadata[0] == self.config.task
        return [SimpleNamespace(args=request.args, request_type="loglikelihood") for request in requests(self, doc, metadata[1])[2]]


class BundleTests(unittest.TestCase):
    def test_exact_original_pending_object_not_normalized_or_mutated(self):
        with tempfile.TemporaryDirectory() as name:
            fixture = BundleFixture(name)
            before = fixture.path.read_bytes()
            with fixture.patches():
                path, report, proof = fixture.read()
            self.assertEqual(path, fixture.path)
            self.assertEqual(report["returncode"], 9)
            self.assertEqual(report["status"], "NATIVE_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL")
            self.assertEqual(proof["actual_parent_exit"], 0)
            self.assertEqual(fixture.path.read_bytes(), before)

    def test_fake_normalized_partial_changed_source_or_wrong_policy_is_rejected(self):
        mutations = [("returncode", 0), ("status", "OFFICIAL_CORE6_FULL_COMPLETE"), ("candidate_returncode", 9),
            ("actual_counts", {}), ("choice_likelihoods", 67105), ("raw_independent_recount", False),
            ("source_identity", {"sha256": "0" * 64}), ("source_assets_unchanged", False),
            ("original_prerequisites_unchanged", False), ("policy", {"precision": "HF_FP32"})]
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as name:
                fixture = BundleFixture(name)
                fixture.report[key] = value
                fixture.save()
                with fixture.patches(), self.assertRaises(ValueError):
                    fixture.read()

    def test_terminal_or_root_exit_cleanup_and_time_bounds_are_required(self):
        mutations = [("terminal", "returncode", 9), ("terminal", "returncode", False),
            ("terminal", "source_sha256", "0" * 64), ("terminal", "hard_cap_seconds", 7200),
            ("audit", "actual_parent_exit", 1), ("audit", "actual_parent_exit", False),
            ("audit", "host_competing_compute_pids", [999]), ("audit", "owned_host_pids_absent", []),
            ("audit", "worker_returncode", 9), ("audit", "calendar_elapsed_seconds", 10800.)]
        for target, key, value in mutations:
            with self.subTest(target=target, key=key), tempfile.TemporaryDirectory() as name:
                fixture = BundleFixture(name)
                getattr(fixture, target)[key] = value
                fixture.save()
                with fixture.patches(), self.assertRaises(ValueError):
                    fixture.read()

    def test_strict_native_numeric_telemetry_and_prerequisite_failures_are_not_holds(self):
        for kind in ("telemetry", "numeric", "future", "prerequisite", "origin"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                fixture = BundleFixture(name)
                if kind == "telemetry":
                    fixture.report["model_proof"]["telemetry_errors"] = ["synthetic unresolved gap"]
                elif kind == "numeric":
                    fixture.report["numerical_canary"]["comparisons"][0]["actual"][0][0] = -2.
                elif kind == "future":
                    fixture.report["numerical_canary"]["checks"][0]["future_token"]["passed"] = False
                elif kind == "origin":
                    fixture.report["sample_manifests"]["piqa"]["lineage"]["tag"] = m.window.TAG
                else:
                    fixture.report["prerequisites"] = {"wrong": True}
                fixture.save()
                with fixture.patches(), self.assertRaises(ValueError):
                    fixture.read()

    def test_pinned_bytes_changed_after_closure_and_existing_or_late_veto_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            fixture = BundleFixture(name)
            with fixture.patches():
                fixture.path.write_bytes(fixture.path.read_bytes() + b" ")
                with self.assertRaises(ValueError):
                    fixture.read()
            fixture.save()
            with fixture.patches():
                for veto in ("terminal_failure_receipt.json", "report_closure_failure.json"):
                    path = fixture.path.parent / veto
                    replace_json(path, dict(status="VETO"))
                    with self.assertRaises(ValueError):
                        fixture.read()
        with tempfile.TemporaryDirectory() as name:
            evidence = m.Evidence()
            path = Path(name) / "late.json"
            evidence.no_file(path)
            replace_json(path, dict(status="VETO"))
            with self.assertRaises(ValueError):
                evidence.unchanged()

    def test_missing_terminal_nan_and_20mb_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "fixture.json"
            for body in (b'{"x":NaN}', b'{"x":1e309}'):
                path.write_bytes(body)
                with self.assertRaises(ValueError):
                    m.Evidence().json(path)
            with path.open("wb") as stream:
                stream.truncate(20_000_000)
            with self.assertRaises(ValueError):
                m.Evidence().json(path)
            with self.assertRaises(ValueError):
                m.Evidence().json(Path(name) / "missing_terminal.json")


class FullInteroperabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="p106b_native_pairs_synthetic_")
        cls.fixture = BundleFixture(cls.temp.name)
        cls.tasks = {name: LargeTask(name, count) for name, count in m.shared.COUNTS.items()}
        cls.contracts, cls.values = {}, {}
        from scripts.p106b_official_tasks import task_requests
        cls.request_builder = staticmethod(task_requests)
        report = cls.fixture.report
        for name, task in cls.tasks.items():
            cls.contracts[name] = m.shared.CaseContracts(task, m.shared.COUNTS[name], task_requests)
            writer, rows = ShardWriter(cls.fixture.path.parent, name + "_samples", limit=20_000_000), []
            for index, contract in enumerate(cls.contracts[name].rows):
                gold = contract["gold"]
                chosen = gold if index % 3 else (gold + 1) % len(contract["choices"])
                filtered = [[-1. if i == chosen else -5., False] for i in range(len(contract["choices"]))]
                metrics = task.process_results(contract["doc"], filtered)
                row = dict(doc_id=index, doc=contract["doc"], target=contract["target"], arguments=contract["arguments"],
                    resps=[[value] for value in filtered], filtered_resps=filtered, filter="none", metrics=list(metrics),
                    **metrics, **contract["hashes"])
                writer.append(row)
                rows.append(row)
            manifest = writer.close(lineage=dict(tag=m.window.native.TAG, model=m.MODEL, task=name, mode="full"))
            counted = m.shared.recount_task(name, task, rows, expected=m.shared.COUNTS[name],
                request_builder=task_requests, contracts=cls.contracts[name])
            audit = dict(counted["audit"], choice_likelihoods=counted["choice_likelihoods"])
            report["sample_manifests"][name] = manifest
            report["independent_audits"][name] = audit
            report["official_results"][name] = dict(results={name: {metric + ",none": audit[field] / m.shared.COUNTS[name]
                for metric, field in (("acc", "correct"), ("acc_norm", "correct_norm"))}})
            cls.values[name] = counted["values"]
        cls.fixture.save()
        for peer in m.PEERS:
            replace_json(m.shared.report_path(peer, cls.fixture.root), fixture_report(peer))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def native_counted(self):
        f = self.fixture
        evidence = m.Evidence()
        with f.patches():
            path, report, proof = m.native_bundle(f.source, evidence, f.root)
        before = m.canonical(report)
        with redirect_stderr(io.StringIO()):
            result = m.shared.recount_model(m.MODEL, path, report, self.tasks, evidence.inputs,
                self.request_builder, self.contracts)
        self.assertEqual(m.canonical(report), before)
        self.assertEqual(report["returncode"], 9)
        self.assertTrue(evidence.unchanged())
        return result

    def test_real_reused_recount_model_accepts_unchanged_native9_full19965_67106(self):
        started = time.perf_counter()
        counted = self.native_counted()
        self.assertEqual(counted["rows"], 19965)
        self.assertEqual(counted["choice_likelihoods"], 67106)
        self.assertEqual(counted["values"], self.values)
        self.assertEqual(set(counted["correspondence"]), set(m.shared.PRIMARY))
        print(f"[SYNTHETIC_NATIVE_FULL] rows=19965 choices=67106 original_rc=9 unchanged=True seconds={time.perf_counter()-started:.6f}")

    def test_orchestration_uses_original_admission_contracts_and_only7_original_paired_calls(self):
        f, base = self.fixture, self.native_counted()
        calls, native_seen = [], []
        original_recount = m.shared.recount_model
        def synthetic_recount(model, path, report, tasks, inputs, builder, contracts):
            calls.append(model)
            if model == m.MODEL:
                native_seen.append((report["returncode"], report["status"]))
            return dict(base, model=model, values={name: [1 - v if model == m.PEERS[0] else v for v in values]
                                                  for name, values in self.values.items()})
        with f.patches(), patch.object(m, "read_tasks", return_value=(self.tasks, {"synthetic": True})), \
                patch.object(m, "source_identity", return_value=f.source), \
                patch.object(m, "recount_model", side_effect=synthetic_recount), \
                patch.object(m, "admit_peer", wraps=m.shared.admit_report) as admitted, \
                patch.object(m, "CaseContracts", wraps=m.shared.CaseContracts) as contracts, \
                patch.object(m, "paired_intervals", wraps=m.shared.paired_intervals) as paired:
            result, final_check = m.collect(f.source, root=f.root)
            self.assertTrue(final_check())
        self.assertIs(m.shared.recount_model, original_recount)
        self.assertEqual(calls, [*m.PEERS, m.MODEL])
        self.assertEqual(native_seen, [(9, "NATIVE_WINDOW_COMPUTE_CLOSED_PENDING_TERMINAL")])
        self.assertEqual(admitted.call_count, 7)
        self.assertEqual(contracts.call_count, 6)
        self.assertEqual(paired.call_count, 7)
        self.assertEqual(len(result["pairs"]), 7)
        self.assertTrue(all(value["resamples"] == 100000 and value["seed"] == 20261024 for value in result["pairs"].values()))
        self.assertTrue(all(key.endswith("__gpt2_q4km") for key in result["pairs"]))
        self.assertTrue(result["posthoc_after_observed_scores"])
        self.assertFalse(result["existing21_pairs_recomputed"])

    def test_wrong_order_gold_choice_and_partial_raw_still_rejected_by_original_recount(self):
        task, rows = fixture_rows()
        for kind in ("order", "gold", "choice", "partial", "nan"):
            altered = copy.deepcopy(rows)
            if kind == "order":
                altered.reverse()
            elif kind == "gold":
                altered[0]["target"] = 1
            elif kind == "choice":
                altered[0]["arguments"].reverse()
            elif kind == "partial":
                altered.pop()
            else:
                altered[0]["filtered_resps"][0][0] = float("nan")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                m.shared.recount_task("piqa", task, altered, expected=2, request_builder=requests)

    def test_ordered_correspondence_mismatch_prevents_any_bootstrap(self):
        f, base = self.fixture, self.native_counted()
        def wrong_correspondence(model, *args):
            return dict(base, correspondence={"wrong_order": True} if model == m.MODEL else base["correspondence"])
        with f.patches(), patch.object(m, "read_tasks", return_value=(self.tasks, {"synthetic": True})), \
                patch.object(m, "recount_model", side_effect=wrong_correspondence), patch.object(m, "paired_intervals") as paired:
            with self.assertRaisesRegex(ValueError, "correspondence"):
                m.collect(f.source, root=f.root)
            paired.assert_not_called()


class ClosureTests(unittest.TestCase):
    def setup_run(self, directory):
        source = dict(sha256="F" * 64)
        report = dict(synthetic=True, pairs={str(i): {} for i in range(7)})
        stack = ExitStack()
        stack.enter_context(patch.dict(m.os.environ, {m.SUPERVISOR_ENV: "1"}))
        stack.enter_context(patch.object(m, "source_identity", return_value=source))
        stack.enter_context(patch.object(m, "collect", return_value=(report, lambda: True)))
        return stack, Path(directory) / "new", source

    def test_terminal_success_keeps_pending_report_and_no_atomic_exit_claim(self):
        with tempfile.TemporaryDirectory() as name:
            stack, target, source = self.setup_run(name)
            with stack:
                result, budget = m.bounded_run(source["sha256"], target=target)
            saved, terminal = m.read_json(target / "report.json"), m.read_json(target / "terminal_receipt.json")
            self.assertEqual(saved["returncode"], 9)
            self.assertEqual(saved["status"], m.PENDING)
            self.assertEqual(terminal["returncode"], 0)
            self.assertEqual(terminal["report_sha256"], m.digest(target / "report.json"))
            self.assertTrue(result["terminal_receipt_verified"])
            self.assertTrue(saved["external_root_hardcap_required"])
            self.assertFalse(saved["atomic_process_exit_or_storage_guaranteed"])
            before = (target / "report.json").read_bytes()
            with self.setup_run(name)[0], self.assertRaises(FileExistsError):
                m.bounded_run(source["sha256"], target=target)
            self.assertEqual(before, (target / "report.json").read_bytes())
            self.assertFalse((target / "terminal_failure_receipt.json").exists())

    def test_delayed_report_terminal_write_and_readback_veto_success_candidate(self):
        for stage in ("report_write", "report_read", "terminal_write", "terminal_read"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as name:
                stack, target, source = self.setup_run(name)
                now = [0.]
                original_close, original_write, original_read = m.close_report, m.write_json, m.read_json
                def close(path, value, **kwargs):
                    result = original_close(path, value, **kwargs)
                    if stage == "report_write":
                        now[0] = 120.1
                    return result
                def write(path, value):
                    result = original_write(path, value)
                    if stage == "terminal_write" and path.name == "terminal_receipt.json":
                        now[0] = 120.1
                    return result
                def read(path):
                    result = original_read(path)
                    if stage == ("report_read" if path.name == "report.json" else "terminal_read"):
                        now[0] = 120.1
                    return result
                with stack, patch.object(m, "close_report", side_effect=close), \
                        patch.object(m, "write_json", side_effect=write), patch.object(m, "read_json", side_effect=read):
                    with self.assertRaises(TimeoutError):
                        m.bounded_run(source["sha256"], target=target, clock=lambda: now[0])
                self.assertEqual(m.read_json(target / "report.json")["returncode"], 9)
                self.assertTrue((target / "terminal_failure_receipt.json").exists())

    def test_original_exception_survives_failure_report_serialization_error(self):
        with tempfile.TemporaryDirectory() as name:
            stack, target, source = self.setup_run(name)
            primary = RuntimeError("synthetic raw recount failure")
            with stack, patch.object(m, "collect", side_effect=primary), \
                    patch.object(m, "close_report", side_effect=TypeError("synthetic writer failure")), redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "synthetic raw recount failure"):
                    m.bounded_run(source["sha256"], target=target)
            veto = m.read_json(target / "terminal_failure_receipt.json")
            self.assertEqual(veto["error_type"], "RuntimeError")

    def test_supervisor_acknowledgement_and_cpu_cap_are_required(self):
        with patch.dict(m.os.environ, {}, clear=True), patch.object(m, "collect") as collect:
            with self.assertRaises(ValueError):
                m.bounded_run("F" * 64)
            collect.assert_not_called()
        for cap in (0, 121, 1.5):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                m.bounded_run("F" * 64, max_wall_sec=cap)

    def test_real_cpu_alarm_timeout_never_produces_success_terminal(self):
        with tempfile.TemporaryDirectory() as name:
            stack, target, source = self.setup_run(name)
            with stack, patch.object(m, "collect", side_effect=lambda *_: time.sleep(2.)):
                with self.assertRaises(TimeoutError):
                    m.bounded_run(source["sha256"], target=target, max_wall_sec=1)
            self.assertFalse((target / "terminal_receipt.json").exists())
            self.assertEqual(m.read_json(target / "terminal_failure_receipt.json")["error_type"], "TimeoutError")

    def test_late_input_change_after_terminal_preserves_candidate_and_writes_veto(self):
        with tempfile.TemporaryDirectory() as name:
            stack, target, source = self.setup_run(name)
            calls = [0]
            def final_check():
                calls[0] += 1
                if calls[0] == 2:
                    raise ValueError("synthetic late input change")
                return True
            with stack, patch.object(m, "collect", return_value=({"synthetic": True}, final_check)):
                with self.assertRaisesRegex(ValueError, "late input change"):
                    m.bounded_run(source["sha256"], target=target)
            self.assertEqual(m.read_json(target / "terminal_receipt.json")["returncode"], 0)
            self.assertEqual(m.read_json(target / "report.json")["returncode"], 9)
            self.assertTrue((target / "terminal_failure_receipt.json").exists())

    def test_terminal_readback_mutation_is_error_even_when_candidate_is_on_disk(self):
        with tempfile.TemporaryDirectory() as name:
            stack, target, source = self.setup_run(name)
            original_read = m.read_json
            def corrupted(path):
                saved = original_read(path)
                if path.name == "terminal_receipt.json":
                    saved["returncode"] = 9
                return saved
            with stack, patch.object(m, "read_json", side_effect=corrupted):
                with self.assertRaisesRegex(ValueError, "readback"):
                    m.bounded_run(source["sha256"], target=target)
            self.assertEqual(original_read(target / "terminal_receipt.json")["returncode"], 0)
            self.assertTrue((target / "terminal_failure_receipt.json").exists())

    def test_source_only_has_no_raw_collect_or_heavy_import_requirement(self):
        output = io.StringIO()
        with patch.object(m, "source_identity", return_value={"sha256": "F" * 64}), \
                patch.object(m, "collect") as collect, redirect_stdout(output):
            self.assertEqual(m.main(["--check-only"]), 0)
        collect.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["raw_reads"], 0)
        self.assertEqual(json.loads(output.getvalue())["models_loaded"], 0)

    def test_main_late_stdout_budget_is_error9_and_veto_not_complete0(self):
        with tempfile.TemporaryDirectory() as name, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            target = Path(name)
            def expired():
                raise TimeoutError("synthetic post-output deadline")
            with patch.object(m, "output_path", return_value=target), \
                    patch.object(m, "bounded_run", return_value=({"status": m.COMPLETE, "returncode": 0}, expired)):
                code = m.main(["--execute", "--source-sha256", "F" * 64, "--output-stamp", "test"])
            self.assertEqual(code, 9)
            self.assertTrue((target / "terminal_failure_receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
