"""CPU fixtures for document-specific freshness, no real logs/models/smoke."""
from pathlib import Path
import os
import contextlib
import io
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_smoke_diag as check
from smoke_module import parse_smoke_module


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "handoff").mkdir()
        self.log = self.root / "log.txt"
        self.log.write_text("fixture")
        os.utime(self.log, (100, 100))
        self.old = self.root / "handoff/202610010001_HANDOFF.md"
        self.old.write_text("old")
        os.utime(self.old, (50, 50))
        self.body = "[FAIL] 202610010001_HANDOFF.md"

    def tearDown(self):
        self.temp.cleanup()

    def test_unchanged_document_failure_is_not_downgraded(self):
        with patch.object(check, "ROOT", self.root):
            self.assertFalse(check.handoff_input_stale("check_handoff.py", self.body, self.log))

    def test_new_selected_handoff_is_a_changed_input(self):
        new = self.root / "handoff/202610020001_HANDOFF.md"
        new.write_text("new")
        with patch.object(check, "ROOT", self.root):
            self.assertTrue(check.handoff_input_stale("check_handoff.py", self.body, self.log))
            self.assertFalse(check.handoff_input_stale("other.py", self.body, self.log))

    def test_same_document_modified_after_log_is_stale(self):
        os.utime(self.old, (200, 200))
        with patch.object(check, "ROOT", self.root):
            self.assertTrue(check.handoff_input_stale("check_handoff.py", self.body, self.log))

    def test_missing_identity_does_not_hide_failure(self):
        with patch.object(check, "ROOT", self.root):
            self.assertFalse(check.handoff_input_stale("check_handoff.py", "traceback only", self.log))

    def run_main_fixture(self, other_exit):
        new = self.root / "handoff/202610020001_HANDOFF.md"
        new.write_text("new")
        scripts = self.root / "scripts"
        scripts.mkdir()
        batch = scripts / "fixture.bat"
        batch.write_text("fixture")
        os.utime(batch, (50, 50))
        rows = []
        for script, item in (("check_handoff.py", "hmark"), ("other.py", "omark")):
            source = scripts / script
            source.write_text(item)
            os.utime(source, (50, 50))
            rows.append({"script": script, "items": [item], "axis": script, "exit0": "fixture"})
        blocks = {"check_handoff.py": (self.body + " hmark", 1), "other.py": ("omark", other_exit)}
        out = io.StringIO()
        with patch.object(check, "ROOT", self.root), patch.object(check, "BATCH", batch), \
             patch.object(check, "load_tsv", return_value=rows), \
             patch.object(check, "batch_scripts", return_value=[r["script"] for r in rows]), \
             patch.object(check, "newest_log", return_value=self.log), \
             patch.object(check, "log_blocks", return_value=blocks), \
             patch.object(sys, "argv", ["check"]), contextlib.redirect_stdout(out):
            return check.main(), out.getvalue()

    def test_old_handoff_failure_preserved_but_current_execution_unverified(self):
        rc, text = self.run_main_fixture(0)
        self.assertEqual(rc, 0)
        self.assertIn("check_handoff.py           exit 1", text)
        self.assertIn("[NOT_RUN]", text)

    def test_another_current_failure_still_fails_main(self):
        rc, text = self.run_main_fixture(1)
        self.assertEqual(rc, 1)
        self.assertIn("other.py: exit 1", text)


class AdaptationTests(unittest.TestCase):
    """Only local text fixtures; never import/execute a smoke or model driver."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.batch = self.root / "scripts/batch/tool_smoke.bat"
        self.batch.parent.mkdir(parents=True)
        self.batch.write_text("@echo off\n" + "\n".join(
            "python scripts\\runlog.py --name !TL_LOGNAME! -- python " + name
            for name in ("scripts\\check_handoff.py", "scripts\\other.py",
                         "run100m.py", "scripts\\check_smoke.py")), encoding="ascii")
        self.driver = self.root / check.ISOLATED_CHECKER
        self.driver.write_text("fixture driver", encoding="utf-8")
        checker = self.root / check.CODEX_HANDOFF
        checker.parent.mkdir(parents=True)
        checker.write_text("fixture document checker", encoding="utf-8")
        self.log = self.root / "log.txt"
        self.receipt = self.root / "test_result/evidence" / check.AUTHORIZED_TAG / "smoke_report.json"
        self.receipt.parent.mkdir(parents=True)
        actions = parse_smoke_module(self.batch, log_name="smoke_codex_20261016_v1")
        edits, commands = [], []
        for action in actions:
            before = list(action.argv)
            before[0] = before[5] = "/fixture/python"
            after = list(before)
            for path, kind, replacement in (
                ("scripts/check_handoff.py", "codex_document_checker", ["-I", "-B", check.CODEX_HANDOFF]),
                ("scripts/check_smoke.py", "isolated_field_log_path", [check.ISOLATED_CHECKER, "--mode", "contract"])):
                if path in after:
                    i = after.index(path)
                    after[i:i+1] = replacement
                    edits.append(dict(line=action.line, kind=kind, before=before, after=after))
            commands.append(after[after.index("--")+1:])
        bodies = ["\n".join(check.CODEX_ITEMS) + "\nCHECK handoff/202610010001_HANDOFF.md",
                  "omark", "training fixture", "이면 계측 계약이 지켜지고 있습니다"]
        commands.append(["/fixture/python", "scripts/summarize_smoke.py", "--log", str(self.log)])
        bodies.append("스모크 종료코드 요약: 실패 0개; 총 에러 0건")
        self.log.write_text("\n".join(
            "[runlog] cmd=" + " ".join(command) + "\n" + body + "\n[runlog] 종료코드 0 소요 0분"
            for command, body in zip(commands, bodies)), encoding="utf-8")
        self.data = dict(schema="P106B_AUTHORIZED_CODEX_COMPLETE_SMOKE_V1",
                         source="scripts/batch/tool_smoke.bat", runtime=f"runs/validation/{check.AUTHORIZED_TAG}",
                         log="log.txt", source_sha256=self.sha(self.batch), driver_sha256=self.sha(self.driver),
                         log_sha256=self.sha(self.log), substitutions=edits,
                         action_count=4, child_count=4, training_count=1,
                         receipts=[dict(line=a.line, returncode=0, child=True) for a in actions],
                         failed_calls=0, summary_returncode=0,
                         original_synthetic_unchanged=True, protected_originals_modified=False)
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()

    def save(self, rehash=False):
        if rehash:
            self.data["log_sha256"] = self.sha(self.log)
        self.receipt.write_text(json.dumps(self.data), encoding="utf-8")

    def aliases(self):
        with patch.object(check, "ROOT", self.root), patch.object(check, "BATCH", self.batch):
            return check.authorized_aliases(self.log)

    def test_valid_receipt_and_real_command_identity(self):
        aliases, errors = self.aliases()
        self.assertEqual(errors, [])
        self.assertEqual(set(aliases), {"check_handoff.py", "check_smoke.py"})
        self.assertEqual(aliases["check_handoff.py"][2], check.CODEX_ITEMS)
        self.assertIn("check_handoff_codex.py", check.log_blocks(self.log))
        self.assertNotIn("check_handoff.py", check.log_blocks(self.log))

    def test_canonical_log_needs_no_receipt_or_alias(self):
        self.log.write_text("[runlog] cmd=python scripts/check_handoff.py\nlegacy marker\n[runlog] 종료코드 0 소요 0분")
        self.receipt.unlink()
        self.assertEqual(self.aliases(), ({}, []))
        self.assertEqual(check.log_blocks(self.log)["check_handoff.py"][1], 0)

    def test_missing_receipt_is_not_an_alias_whitelist(self):
        self.receipt.unlink()
        self.assertTrue(self.aliases()[1])

    def test_malformed_json_shapes_fail_cleanly(self):
        for value in ([], {**self.data, "substitutions": [None]}):
            self.receipt.write_text(json.dumps(value), encoding="utf-8")
            self.assertTrue(self.aliases()[1])

    def test_missing_or_failed_summary_is_rejected(self):
        self.log.write_text(self.log.read_text().replace("총 에러 0건", "총 에러 1건"))
        self.save(rehash=True)
        self.assertTrue(self.aliases()[1])

    def test_log_or_driver_or_source_hash_change_fails_closed(self):
        for path in (self.log, self.driver, self.batch):
            with self.subTest(path=path.name):
                before = path.read_bytes()
                path.write_bytes(before + b"\nchanged")
                self.assertTrue(self.aliases()[1])
                path.write_bytes(before)

    def test_wrong_helper_mode_even_with_updated_log_hash_is_rejected(self):
        self.log.write_text(self.log.read_text().replace("--mode contract", "--mode check"))
        self.save(rehash=True)
        self.assertTrue(self.aliases()[1])

    def test_changed_actual_executable_is_not_hidden_by_alias(self):
        self.log.write_text(self.log.read_text().replace("/fixture/python", "/other/python", 1))
        self.save(rehash=True)
        self.assertTrue(self.aliases()[1])

    def test_missing_duplicate_or_nonzero_actual_child_is_rejected(self):
        original = self.log.read_text()
        variants = [original.replace("[runlog] 종료코드 0", "[runlog] 종료코드 1", 1),
                    original.split("[runlog] cmd=", 2)[0] + "[runlog] cmd=" + original.split("[runlog] cmd=", 2)[2],
                    original + "\n" + original]
        for variant in variants:
            with self.subTest(variant=variant[:70]):
                self.log.write_text(variant)
                self.save(rehash=True)
                self.assertTrue(self.aliases()[1])

    def test_incomplete_or_forged_receipt_is_rejected(self):
        original = json.dumps(self.data)
        for change in (lambda d: d["receipts"].pop(),
                       lambda d: d["substitutions"][0]["after"].append("--skip"),
                       lambda d: d.update(child_count=0),
                       lambda d: d.update(log="other.txt"),
                       lambda d: d.update(original_synthetic_unchanged=False)):
            with self.subTest(change=change):
                self.data = json.loads(original)
                change(self.data)
                self.save()
                self.assertTrue(self.aliases()[1])

    def test_actual_adapted_markers_are_checked_not_legacy_markers(self):
        rows = [dict(script="check_handoff.py", items=["legacy-only-marker"], axis="handoff", exit0="fixture")]
        (self.root / "scripts/check_handoff.py").write_text("legacy-only-marker")
        os.utime(self.root / "scripts/check_handoff.py", (50, 50))
        for missing, expected_code in ((False, 0), (True, 1)):
            if missing:
                self.log.write_text(self.log.read_text().replace("PASS static structure and local links", "missing"))
                self.save(rehash=True)
            with patch.object(check, "ROOT", self.root), patch.object(check, "BATCH", self.batch), \
                 patch.object(check, "load_tsv", return_value=rows), \
                 patch.object(check, "batch_scripts", return_value=["check_handoff.py"]), \
                 patch.object(check, "newest_log", return_value=self.log), \
                 patch.object(sys, "argv", ["check"]), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(check.main(), expected_code)
                self.assertIn("[ADAPTED]", out.getvalue())

    def use_night_profile(self):
        driver='scripts/diag_p106b_night_final_smoke.py'
        path=self.root/driver;path.write_bytes(self.driver.read_bytes())
        self.log.write_text(self.log.read_text().replace(check.ISOLATED_CHECKER,driver))
        self.data['substitutions']=json.loads(json.dumps(self.data['substitutions']).replace(check.ISOLATED_CHECKER,driver)
            .replace('smoke_codex_20261016_v1','smoke_codex_20261017_night_final_v1'))
        self.data.update(schema='P106B_AUTHORIZED_CODEX_COMPLETE_SMOKE_NIGHT_FINAL_V1',
            runtime='runs/validation/p106b_night_final_smoke_v1_s1337',driver_sha256=self.sha(path))
        self.receipt=self.root/'test_result/evidence/p106b_night_final_smoke_v1_s1337/smoke_report.json'
        self.receipt.parent.mkdir(parents=True);self.save(rehash=True)
        return path

    def test_night_profile_uses_own_exact_receipt_not_original(self):
        self.use_night_profile();self.assertEqual(self.aliases()[1],[])

    def test_night_profile_cannot_use_original_runtime_or_unknown_schema(self):
        self.use_night_profile();original=dict(self.data)
        for change in (dict(runtime='runs/validation/'+check.AUTHORIZED_TAG),dict(schema='UNKNOWN')):
            self.data=dict(original,**change);self.save();self.assertTrue(self.aliases()[1])

    def test_night_driver_hash_and_missing_receipt_fail_closed(self):
        path=self.use_night_profile();path.write_text('changed')
        self.assertTrue(self.aliases()[1]);self.receipt.unlink();self.assertTrue(self.aliases()[1])

    def test_mixed_profiles_not_accepted_as_either(self):
        self.use_night_profile()
        self.log.write_text(self.log.read_text()+'\n[runlog] cmd=python '+check.ISOLATED_CHECKER+'\n[runlog] 종료코드 0 소요 0분')
        self.save(rehash=True);self.assertTrue(self.aliases()[1])


if __name__ == "__main__":
    unittest.main()
