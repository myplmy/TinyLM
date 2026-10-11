"""CPU signal/lifecycle fixtures; no actual deadline waiting or data/model IO."""
from __future__ import annotations
from contextlib import contextmanager
import io
from pathlib import Path
import signal
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_budget_resume as new
from scripts.p106b_gate_runtime import wall_limit,disposition
from scripts.diag_p106b_online_rate5 import ToolFailure

class BudgetTests(unittest.TestCase):
    def test_old_owned_alarm_is_error9_not_a_resume_failure(self):
        before=signal.getsignal(signal.SIGALRM)
        with self.assertRaises(ToolFailure) as caught,wall_limit(60):
            signal.getsignal(signal.SIGALRM)(signal.SIGALRM,None)
        self.assertEqual(disposition(caught.exception),("TOOL_FAILURE",9))
        self.assertIs(signal.getsignal(signal.SIGALRM),before)

    def test_new_owned_alarm_is_pause8_and_restores_original_handler(self):
        before=(new.producer.wall_limit,signal.getsignal(signal.SIGALRM));proof={"expired":False}
        with self.assertRaises(new.ProductionBudgetPause) as caught,new.production_budget_scope(proof):
            with new.producer.wall_limit(60):
                signal.getsignal(signal.SIGALRM)(signal.SIGALRM,None)
        self.assertEqual(disposition(caught.exception),("GATE_NEGATIVE",8))
        self.assertTrue(proof["expired"])
        self.assertEqual((new.producer.wall_limit,signal.getsignal(signal.SIGALRM)),before)

    def test_real_server_error_is_never_reclassified(self):
        proof={"expired":False}
        with self.assertRaises(ToolFailure) as caught,new.production_budget_scope(proof):
            with new.producer.wall_limit(60):raise ToolFailure("teacher server died")
        self.assertEqual(disposition(caught.exception),("TOOL_FAILURE",9))
        self.assertFalse(proof["expired"])

    def test_context_restores_producer_on_arbitrary_failure(self):
        original=new.producer.wall_limit
        with self.assertRaises(ValueError),new.production_budget_scope({"expired":False}):
            raise ValueError("fixture")
        self.assertIs(new.producer.wall_limit,original)

    def test_checkonly_never_executes_budget_or_gpu(self):
        with patch.object(sys,"argv",["fixture","--mode","resume","--check-only"]), \
             patch.object(new.prior,"run_resume",return_value=0) as child, \
             patch.object(new,"execute_resume",side_effect=AssertionError("no model")), \
             patch("sys.stdout",new=io.StringIO()):
            self.assertEqual(new.main(),0)
        self.assertFalse(child.call_args.kwargs["execute"])

if __name__=="__main__":unittest.main(verbosity=2)
