"""새 Falcon 창의 순수 CPU 회귀. 원문·모델·GPU를 열지 않는다."""
from __future__ import annotations

import ast
import copy
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts import diag_p106b_babylm_window as m
from scripts.p106b_shards import ShardWriter


class WindowTests(unittest.TestCase):
    def cost(self):
        return dict(schema=m.SCHEMA, tag=m.TAG, model=m.MODEL, mode="cost", returncode=0,
            status="BABYLM_WINDOW_COST_COMPLETE", source_identity={"fixture": True},
            policy=m.original.policy(), inputs_unchanged=True, sources_unchanged=True,
            group_audits=dict(main=dict(rows=536), supplement=dict(rows=40)),
            evaluation_seconds=dict(main=26.823737824001, supplement=1.9981936499971198),
            wall_seconds=36.5329598160024, raw_independent_recount=True, numerical_canary_passed=True)

    def admission(self, mode="full"):
        return m.window(m.DEADLINE_ISO, 7200 if mode == "full" else 600, mode, now=m.LATEST_DEADLINE - 10000)

    def test_original_policy_is_reused_without_semantic_changes(self):
        self.assertEqual(m.original.policy(), m.original.policy())
        self.assertEqual(m.MODEL, "falcon90m")
        self.assertEqual(m.original.EXPECTED, dict(main=dict(files=67, rows=59875), supplement=dict(files=5, rows=5218)))

    def test_new_cap_admits_the_previous_cost_shape_but_not_old_receipt(self):
        value = m.full_admission(self.cost(), {"fixture": True}, self.admission(), now=m.LATEST_DEADLINE - 10000)
        self.assertAlmostEqual(value["forecast_seconds"], 5013.310095652373)
        self.assertEqual(value["hard_cap_seconds"], 7200)
        cost = self.cost(); cost["status"] = "BABYLM_CAUSAL_COST_COMPLETE"
        with self.assertRaises(ValueError):
            m.full_admission(cost, {"fixture": True}, self.admission(), now=m.LATEST_DEADLINE - 10000)

    def test_changed_source_model_policy_or_partial_recount_is_rejected(self):
        for key, value in (("model", "native595-f"), ("source_identity", {}), ("returncode", 9),
                           ("policy", {}), ("raw_independent_recount", False), ("numerical_canary_passed", False),
                           ("inputs_unchanged", False), ("sources_unchanged", False)):
            cost = self.cost(); cost[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.full_admission(cost, {"fixture": True}, self.admission(), now=m.LATEST_DEADLINE - 10000)

    def test_bad_counts_and_nonfinite_cost_are_rejected(self):
        for change in (lambda r: r["group_audits"]["main"].update(rows=535),
                       lambda r: r["evaluation_seconds"].update(main=float("nan")),
                       lambda r: r["evaluation_seconds"].update(main=-1),
                       lambda r: r.update(wall_seconds=True)):
            cost = self.cost(); change(cost)
            with self.assertRaises(ValueError):
                m.full_admission(cost, {"fixture": True}, self.admission(), now=m.LATEST_DEADLINE - 10000)

    def test_exact_deadline_and_phase_caps(self):
        for deadline, cap, mode in (("2026-10-24T09:00:00+09:00", 600, "cost"),
                                    ("2026-10-24T08:40:00", 600, "cost"),
                                    (m.DEADLINE_ISO, 601, "cost"), (m.DEADLINE_ISO, 7201, "full")):
            with self.subTest(mode=mode, cap=cap), self.assertRaises(ValueError):
                m.window(deadline, cap, mode, now=m.LATEST_DEADLINE - 10000)
        with self.assertRaises(ValueError):
            m.window(m.DEADLINE_ISO, 600, "cost", now=m.LATEST_DEADLINE - 59)

    def test_forecast_cannot_consume_cleanup_or_exceed_admitted_cap(self):
        with self.assertRaises(ValueError):
            m.full_admission(self.cost(), {"fixture": True}, self.admission(), now=m.LATEST_DEADLINE - 5000)
        admission = self.admission(); admission["hard_cap_seconds"] = 3600
        with self.assertRaises(ValueError):
            m.full_admission(self.cost(), {"fixture": True}, admission, now=m.LATEST_DEADLINE - 10000)

    def test_time_check_guards_both_real_and_elapsed_clocks(self):
        admission = self.admission("cost")
        m.check_time(admission, 0, now=m.LATEST_DEADLINE - 1000, elapsed=1)
        for now, elapsed in ((m.LATEST_DEADLINE - 19, 1), (m.LATEST_DEADLINE - 1000, 580)):
            with self.assertRaises(TimeoutError):
                m.check_time(admission, 0, now=now, elapsed=elapsed)

    def rows(self):
        return [dict(index=i, uid="a" if i < 2 else "b", label=0, chosen=0 if i != 2 else 1,
                     scores=[-1., -2.] if i != 2 else [-2., -1.], exact_tie=False) for i in range(3)]

    def summary(self, rows):
        digest = hashlib.sha256()
        for row in rows:
            digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False).encode())
        return dict(rows=3, uids=2, by_uid=dict(a=dict(total=2, correct=2), b=dict(total=1, correct=0)),
                    scores_sha256=digest.hexdigest().upper(), exact_ties=0, uid_macro_percent=50.)

    def test_raw_recount_is_uid_macro_not_micro(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); writer = ShardWriter(directory, "pairs", limit=1000)
            rows = self.rows()
            for row in rows: writer.append(row)
            manifest = writer.close(lineage={})
            result = m.recount_pairs(directory, manifest, 3, 2, self.summary(rows))
            self.assertEqual(result["uid_macro_percent"], 50.)
            bad = self.summary(rows); bad["uid_macro_percent"] = 100 * 2 / 3
            with self.assertRaises(ValueError): m.recount_pairs(directory, manifest, 3, 2, bad)

    def test_recount_refuses_bad_sequence_or_nonmax_prediction(self):
        for field, value in (("index", 7), ("chosen", 1), ("exact_tie", True)):
            with tempfile.TemporaryDirectory() as name:
                directory = Path(name); writer = ShardWriter(directory, "pairs")
                rows = self.rows(); rows[0][field] = value
                for row in rows: writer.append(row)
                manifest = writer.close(lineage={})
                with self.assertRaises(ValueError): m.recount_pairs(directory, manifest, 3, 2, self.summary(rows))

    def test_exclusive_output_and_no_symlink(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name) / "new"; m.reserve(directory)
            with self.assertRaises(FileExistsError): m.reserve(directory)
            link = Path(name) / "link"; link.symlink_to(directory, target_is_directory=True)
            with self.assertRaises(ValueError): m.reserve(link / "new")

    def test_failure_cause_survives_exit_audit_failure(self):
        with tempfile.TemporaryDirectory() as name:
            report = dict(returncode=9, status="PARTIAL", error_type="TimeoutError", error="fixture")
            def bad(_): raise ValueError("fixture pin changed")
            m.finalize(report, Path(name), m.time.perf_counter(), {}, {}, identity_fn=lambda: {}, verify_fn=bad)
            saved = json.loads((Path(name) / "report.json").read_text())
            self.assertEqual(saved["error_type"], "TimeoutError")
            self.assertFalse(saved["inputs_unchanged"])

    def test_owned_cleanup_uses_no_foreign_process_operation(self):
        calls = []
        fake = SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda: calls.append("empty_cache")))
        report = dict(returncode=0)
        m.cleanup_owned(fake, report, lambda: {"fixture": True})
        self.assertEqual(calls, ["empty_cache"])
        self.assertTrue(report["owned_cleanup_complete"])
        def failed(): raise RuntimeError("fixture cleanup failure")
        bad = SimpleNamespace(cuda=SimpleNamespace(empty_cache=failed))
        report = dict(returncode=9, error_type="TimeoutError")
        m.cleanup_owned(bad, report)
        self.assertEqual(report["error_type"], "TimeoutError")
        self.assertFalse(report["owned_cleanup_complete"])

    def test_cli_never_accepts_tiny_model_or_implicit_execution(self):
        for args in (("--check-only", "--model", "native595-f"), ("--execute",)):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit): m.main(args)

    def test_no_top_level_model_import_or_monkeypatch(self):
        tree = ast.parse(Path(m.__file__).read_text())
        names = [getattr(n, "module", "") or "" for n in tree.body if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(n.startswith(("torch", "transformers", "datasets")) for n in names))
        self.assertNotIn("patch.object", Path(m.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
