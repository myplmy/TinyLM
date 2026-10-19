"""Registry runtime-root regressions using temporary assets, never live records."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock


SOURCE_ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    "LOGS": "runs/logs", "RESULTS": "test_result",
    "TSV": "runs/registry.tsv", "MD": "docs/RUN_REGISTRY.md",
    "DB": "runs/registry.db", "MANUAL": "runs/registry_manual.tsv",
}


def load_registry(root=None):
    # Import the actual source while avoiding cached module/global-root state.
    with mock.patch.dict(os.environ):
        if root is None:
            os.environ.pop("TINYLM_DIR", None)
        else:
            os.environ["TINYLM_DIR"] = str(root)
        spec = importlib.util.spec_from_file_location(
            "registry_runtime_fixture", SOURCE_ROOT / "scripts/registry.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class RegistryRuntimePaths(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="registry_runtime_fixture_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = load_registry(self.root)

    def isolated(self):
        # This assertion MUST precede every fixture I/O operation. With the old
        # source it fails without ever opening or scanning the actual registry.
        self.assertEqual(self.registry.ROOT, self.root)
        for name, suffix in PATHS.items():
            self.assertEqual(getattr(self.registry, name), self.root / suffix)
        return self.registry

    def write(self, suffix, text):
        self.isolated()
        path = self.root / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def train_json(self, tag="fixture", steps=30):
        return self.write("runs/logs/tiny_synthetic_1M_" + tag + ".json",
                          json.dumps(dict(steps=steps, tokens=steps * 8,
                                          final=dict(val_loss=3.25, bpb=1.5))))

    def test_default_paths_are_exactly_the_existing_repository_paths(self):
        registry = load_registry()
        self.assertEqual(registry.ROOT, SOURCE_ROOT)
        for name, suffix in PATHS.items():
            self.assertEqual(getattr(registry, name), SOURCE_ROOT / suffix)

    def test_override_binds_all_six_runtime_paths(self):
        self.isolated()

    def test_override_preserves_spaces_and_korean_path(self):
        root = self.root / "runtime space 한글"
        registry = load_registry(root)
        self.assertEqual(registry.ROOT, root)
        self.assertEqual(registry.MANUAL, root / PATHS["MANUAL"])

    def test_relative_override_matches_existing_tinylm_path_contract(self):
        registry = load_registry("relative_runtime")
        self.assertEqual(registry.ROOT, Path("relative_runtime"))
        self.assertEqual(registry.TSV, Path("relative_runtime/runs/registry.tsv"))

    def test_missing_tag_returns_two_without_creating_registry(self):
        registry = self.isolated()
        self.assertEqual(registry.record("missing", "P106B/stage0", "raw.txt"), 2)
        self.assertFalse(registry.TSV.exists())

    def test_record_stays_in_override_and_keeps_probe_loss_blank(self):
        self.train_json()
        registry = self.isolated()
        self.assertEqual(registry.record("fixture", "P106B/stage0", "raw.txt"), 0)
        row, = registry.read_tsv()
        self.assertEqual(row["tag"], "fixture")
        self.assertEqual(row["plan_stages"], "P106B/stage0")
        self.assertEqual(row["log_files"], "raw.txt")
        self.assertEqual(row["loss"], "")
        self.assertFalse(registry.TSV.with_suffix(".tsv.tmp").exists())

    def test_full_train_metric_schema_is_unchanged(self):
        path = self.train_json(steps=500)
        row = self.registry.row_from_json(path)
        self.assertEqual(set(row), set(self.registry.COLS))
        self.assertEqual(row["loss"], "3.2500000")
        self.assertEqual(row["bpb"], "1.500000")

    def test_separate_imports_and_same_tag_do_not_share_records(self):
        registry = self.isolated()
        self.train_json()
        self.assertEqual(registry.record("fixture", "P106B/stage0", "first.txt"), 0)
        other = load_registry(self.root / "second")
        self.assertEqual(other.ROOT, self.root / "second")
        self.assertEqual(other.record("fixture", "", "second.txt"), 2)
        self.assertEqual(other.read_tsv(), [])
        self.assertEqual(registry.read_tsv()[0]["log_files"], "first.txt")

    def test_result_harvest_and_manual_file_are_local(self):
        registry = self.isolated()
        self.write("test_result/101_fixture.txt", "[runlog] name=P106B_stage0_fixture\n"
                   "[runlog] cmd=python run100m.py train --tag fixture\n")
        self.write(PATHS["MANUAL"], "tag\tplan_stages\tlog_files\tnote\n"
                   "fixture\tP106B/stage0\t101_fixture.txt\tlocal\n")
        self.assertEqual(registry.harvest_plan_stages(),
                         {"fixture": {("P106B/stage0", "101_fixture.txt")}})
        self.assertEqual(registry.read_manual()["fixture"],
                         ("101_fixture.txt", "P106B/stage0", "local"))

    def test_render_database_and_scan_use_override_only(self):
        registry = self.isolated()
        self.train_json()
        self.write("docs/fixture.txt", "fixture")
        self.assertEqual(registry.record("fixture", "P106B/stage0", "raw.txt"), 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(registry.render(), 0)
            self.assertEqual(registry.build_db(), 0)
            self.assertEqual(registry.scan(), 0)
        self.assertIn("fixture", registry.MD.read_text(encoding="utf-8"))
        with sqlite3.connect(registry.DB) as connection:
            self.assertEqual(connection.execute("select tag from runs").fetchall(),
                             [("fixture",)])

    def test_scan_detects_only_the_fixture_unregistered_run(self):
        registry = self.isolated()
        self.train_json()
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(registry.scan(), 1)
        self.assertIn("fixture", output.getvalue())

    def test_real_runlog_registration_uses_the_imported_runtime_registry(self):
        registry = self.isolated()
        self.train_json()
        spec = importlib.util.spec_from_file_location(
            "runlog_runtime_fixture", SOURCE_ROOT / "scripts/runlog.py")
        runlog = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runlog)
        command = [sys.executable, "run100m.py", "train", "--tag", "fixture"]
        with mock.patch.dict(sys.modules, {"registry": registry}), \
                mock.patch.object(sys, "path", list(sys.path)), \
                redirect_stdout(io.StringIO()):
            runlog._register(0, "P106B_Stage0_fixture", self.root / "raw.txt", command)
        self.assertEqual(registry.read_tsv()[0]["log_files"], "raw.txt")


if __name__ == "__main__":
    unittest.main()
