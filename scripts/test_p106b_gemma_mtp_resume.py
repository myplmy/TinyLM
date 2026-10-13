"""CPU fixtures: no teacher, student, old corpus or GPU is opened."""
import contextlib
import json
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import diag_p106b_gemma_mtp_resume as gate


class ForkTests(unittest.TestCase):
    def test_on_paths_are_disjoint_from_all_literal_outputs(self):
        self.assertFalse(set(gate.PATHS.values()) & set(gate.literal.PATHS.values()))
        self.assertNotEqual(gate.TAG, gate.literal.TAG)

    def test_only_fixed_four_off_ancestors_are_declared(self):
        self.assertEqual(len(gate.PARENT_REPORT_SHAS), 4)
        self.assertEqual(len(set(gate.PARENT_REPORT_SHAS)), 4)
        self.assertTrue(all(len(s) == 64 for s in gate.PARENT_REPORT_SHAS))

    def test_combined_reader_keeps_ancestors_without_copying(self):
        with tempfile.TemporaryDirectory() as name:
            ancestor = (Path(name)/'old', {'cursor':[1,5]})
            rows = list(gate.combined_batches([ancestor], Path(name)/'new'))
            self.assertEqual(rows, [ancestor])
            self.assertFalse((Path(name)/'new').exists())

    def test_combined_reader_requires_contiguous_on_batches(self):
        with tempfile.TemporaryDirectory() as name, patch.object(gate,'safe_repo_path',lambda p:p):
            root=Path(name); (root/'batch_000005').mkdir()
            with self.assertRaises(ValueError): list(gate.combined_batches([None]*4,root))
            (root/'batch_000005').rmdir(); (root/'batch_000004').mkdir()
            with self.assertRaises(FileExistsError): list(gate.combined_batches([None]*4,root))
            file=root/'batch_000004/report.json'
            file.write_text(json.dumps({'input':{'production_fork':gate.VERSION,'mtp':False}}))
            with self.assertRaises(ValueError): list(gate.combined_batches([None]*4,root))
            file.write_text(json.dumps({'input':{'production_fork':gate.VERSION,'mtp':True}}))
            self.assertEqual(len(list(gate.combined_batches([None]*4,root))),5)

    def test_scope_restores_modules_and_requests_real_on_session(self):
        control=gate.producer.control; original_output=control.OUTPUT
        original_quota=control.Quotas
        original_session=gate.producer.teacher.GemmaSession
        info={'mtp':False,'context':8192,'thinking':1024,'max_output':3072}
        calls=[]
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); (root/'inputs.json').write_text(json.dumps(info))
            with patch.object(gate,'PARENT',root), \
                    patch.object(gate.literal,'literal_scope',contextlib.nullcontext), \
                    patch.object(gate.literal.previous,'recovery_scope',contextlib.nullcontext), \
                    patch.object(gate,'pinned_ancestors',return_value=[]), \
                    patch.object(gate,'require_pair',return_value=gate.PAIR_SHA), \
                    patch.object(gate.producer,'require_pilots',return_value=info), \
                    patch.object(gate.producer,'produce_group',return_value={'meta':{}}), \
                    patch.object(gate,'digest',return_value='A'*64), \
                    patch.object(gate.producer.teacher,'GemmaSession',side_effect=lambda flag:calls.append(flag)):
                before=gate.producer.teacher.GemmaSession
                with gate.on_scope():
                    current=gate.producer.require_pilots()
                    self.assertIs(current['mtp'],True)
                    for k in ('context','thinking','max_output'): self.assertEqual(current[k],info[k])
                    gate.producer.teacher.GemmaSession(False)
                    self.assertEqual(calls,[True])
                    self.assertTrue(gate.producer.produce_group()['meta']['teacher_mtp'])
                    self.assertEqual(control.OUTPUT,gate.PATHS['OUTPUT'])
                self.assertIs(gate.producer.teacher.GemmaSession,before)
        self.assertIs(gate.producer.teacher.GemmaSession,original_session)
        self.assertIs(control.Quotas,original_quota)
        self.assertEqual(control.OUTPUT,original_output)

    def test_original_producer_files_are_not_written_or_modified(self):
        text=Path(gate.__file__).read_text()
        self.assertNotIn('write_text(',text)
        self.assertNotIn('shutil.copy',text)
        self.assertIn('saved != original_info',text)
        self.assertIn('original_require()',text)


if __name__=='__main__': unittest.main(verbosity=2)
