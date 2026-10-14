"""CPU version/sequence boundaries only; no real sources, models or GPU."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts import diag_p106b_gemma_stream_fork as gate

class StreamForkTests(unittest.TestCase):
    def test_ancestors_preserved_and_new_batch_contiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'batch_000006';p.mkdir()
            (p/'report.json').write_text(json.dumps({'input':{'production_fork':gate.VERSION}}))
            # Safe repo path is a boundary; fixture replaces only filesystem checker.
            from unittest.mock import patch
            ancestors=[(Path(f'old{i}'),{'i':i}) for i in range(6)]
            with patch.object(gate,'safe_repo_path',lambda p:p):
                rows=list(gate.combined(ancestors,root))
            self.assertEqual(rows[:6],ancestors);self.assertEqual(rows[-1][0],p)
    def test_gap_or_other_version_is_not_silently_resumed(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'batch_000007';p.mkdir()
            (p/'report.json').write_text('{}')
            with patch.object(gate,'safe_repo_path',lambda p:p),self.assertRaises(ValueError):
                list(gate.combined([None]*6,root))
    def test_new_paths_not_old_source_namespace(self):
        self.assertNotEqual(gate.PATHS['OUTPUT'],gate.PARENT)
        self.assertTrue(all('mtpstream' in str(p) for p in gate.PATHS.values()))

if __name__=='__main__':unittest.main(verbosity=2)
