#!/usr/bin/env python3
"""Exercise optimized-Python veto and held second-arm closure without models."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
BASE = Path(__file__).resolve().parent

def load(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class RootClosureTests(unittest.TestCase):
    def test_dialogue_rejects_nonzero_parent_even_with_optimization(self):
        source = '''import importlib.util
from pathlib import Path
from unittest.mock import patch
p=Path("handoff/audit/oct26_research/run_native_dialogue.py")
s=importlib.util.spec_from_file_location("root_dialogue",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with patch.object(m.diag.official,"read_ref",return_value={"schema":m.diag.SCHEMA,"returncode":9}):
 try:m.close({}, {}, Path("/tmp"),1.)
 except ValueError as e:
  if "actual dialogue report" not in str(e):raise
 else:raise RuntimeError("optimized Python bypassed the terminal veto")
print("OPTIMIZED_VETO_PRESERVED")
'''
        actual = subprocess.run([sys.executable, "-O", "-B", "-X", "utf8", "-c", source], cwd=ROOT,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(actual.returncode, 0, actual.stdout)
        self.assertIn("OPTIMIZED_VETO_PRESERVED", actual.stdout)

    def test_time_hold_records_no_model_and_preserves_admission(self):
        module = load("continue_native_pair")
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            report = Path(directory) / "report.json"
            admission = Path(directory) / "budget_v2.json"
            admission.write_bytes(b'{"original":true}')
            before = admission.read_bytes()
            args = SimpleNamespace(budget_sha256="A" * 64)
            with patch.object(module.train, "budget_admission", side_effect=module.train.Hold("time window")), contextlib.redirect_stdout(io.StringIO()):
                result = module.admit_second(args, {}, {"actual_supervisor_exit": 0}, time.monotonic(), report)
            self.assertIsNone(result)
            value = json.loads(report.read_text())
            self.assertEqual(value["status"], "SECOND_ARM_TIME_HOLD")
            self.assertEqual(value["returncode"], 8)
            self.assertIsNone(value["actual_second_launcher_exit"])
            self.assertFalse(value["second_model_started"])
            self.assertEqual(admission.read_bytes(), before)

    def test_readback_budgets_start_at_each_call(self):
        for name, method in (("run_native_dialogue", "make_budget"), ("run_native_official", "budget")):
            module = load(name)
            before = time.monotonic()
            value = getattr(module, method)()
            after = time.monotonic()
            self.assertGreaterEqual(value.started, before)
            self.assertLessEqual(value.started, after)
            self.assertGreater(value.remaining(), 599)
            self.assertEqual(value.reserve, 120)

if __name__ == "__main__":
    unittest.main(verbosity=2)
