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

    def test_student_stages_dispatch_under_new_scope_without_teacher(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import patch
        @contextmanager
        def scope():yield {'fixture':'new-v5'}
        for mode in ('wire','train','eval'):
            with patch.object(gate,'fork_scope',scope),patch.object(gate,'safe_repo_path',lambda p:p),\
                 patch.object(gate.producer.control,'base_report',return_value={}),\
                 patch.object(gate.producer.control,'learner',return_value={'fixture':True}) as learn,\
                 patch.object(gate.producer.control,'evaluate',return_value={'fixture':True}) as evaluate,\
                 patch.object(gate,'PersistentMemory',side_effect=AssertionError('teacher monitor forbidden')):
                self.assertEqual(gate.dispatch(SimpleNamespace(mode=mode,max_wall_sec=60),False),0)
                if mode=='eval':evaluate.assert_called_once_with(execute=False);learn.assert_not_called()
                else:learn.assert_called_once_with(mode=='wire',execute=False);evaluate.assert_not_called()

    def test_finalize_refuses_absent_fork_before_creation(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import patch
        @contextmanager
        def scope():yield {'fixture':'new-v5'}
        with tempfile.TemporaryDirectory() as tmp,patch.object(gate,'fork_scope',scope),\
             patch.object(gate,'PATHS',dict(gate.PATHS,OUTPUT=Path(tmp)/'absent')),\
             patch.object(gate,'safe_repo_path',lambda p:p),\
             patch.object(gate.producer.control,'base_report',return_value={}),\
             patch.object(gate.producer.control,'finalize',side_effect=AssertionError('write forbidden')):
            with self.assertRaises(FileNotFoundError):gate.dispatch(SimpleNamespace(mode='finalize',max_wall_sec=60),False)

if __name__=='__main__':unittest.main(verbosity=2)
