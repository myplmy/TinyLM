from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from unittest.mock import patch
from scripts import diag_p106b_binding_factor_probe as code


class Contracts(unittest.TestCase):
    def test_missing_execute_is_rejected_before_report(self):
        from contextlib import redirect_stderr
        from io import StringIO
        captured=StringIO()
        with patch.object(sys,'argv',['diag']),patch.object(code,'run') as runner,redirect_stderr(captured):
            with self.assertRaises(SystemExit) as stopped:code.main()
            self.assertEqual(stopped.exception.code,2);runner.assert_not_called()
        self.assertIn('--execute',captured.getvalue())

    def test_explicit_execute_dispatches_only_requested_cpu_action(self):
        with patch.object(sys,'argv',['diag','--execute','--max-wall-sec','60']),\
             patch.object(code,'run',return_value=77) as runner:
            self.assertEqual(code.main(),77)
            args=runner.call_args.args[0]
            self.assertTrue(args.execute);self.assertEqual(args.max_wall_sec,60)


if __name__=='__main__':unittest.main()
