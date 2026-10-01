"""CPU fixtures for document-specific freshness, no real logs/models/smoke."""
from pathlib import Path
import os
import contextlib
import io
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_smoke_diag as check


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


if __name__ == "__main__":
    unittest.main()
