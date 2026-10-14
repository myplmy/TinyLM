"""CPU compare collision and optional execution-flag fixtures; no source/model reads."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from scripts import diag_p106b_source_compare as compare

class SourceCompareTests(unittest.TestCase):
    def test_no_existing_report_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='source_compare_fixture_') as directory:
            path=Path(directory);out=path/'pair_report.json';out.write_text('fixture-original')
            with patch.object(compare.gate,'EVIDENCE',path),patch.object(sys,'argv',['compare','--execute']),redirect_stdout(io.StringIO()):
                self.assertEqual(compare.main(),8)
            self.assertEqual(out.read_text(),'fixture-original')
    def test_missing_execution_flag_fails_before_reads(self):
        with patch.object(sys,'argv',['compare']),redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:compare.main()
        self.assertEqual(raised.exception.code,2)

if __name__=='__main__':unittest.main()
