"""Pure tests of split/config boundaries; no official package or asset imports."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import prepare_p106b_official_eval as m


def manifest():
    return dict(harness_revision=m.COMMIT,files=[dict(kind='evaluation_parquet',task=task,
        split=split,expected_rows=count,local_relative_path=task+'.parquet',
        revision='a'*40,repo_id='public/'+task,config='default',sha256='b'*64)
        for task,(_,split,count,_) in m.TASKS.items()])


class Contracts(unittest.TestCase):
    def test_only_evaluation_files_zero_shot_no_train_lookup(self):
        with patch.object(m,'digest',return_value='C'*64):specs=m.task_specs(manifest())
        self.assertEqual(len(specs),6)
        for spec in specs:
            o=spec['overrides'];self.assertEqual(o['num_fewshot'],0)
            self.assertIsNone(o['training_split']);self.assertIsNone(o['fewshot_split'])
            self.assertEqual(o['fewshot_config'],{'samples':[]})
            self.assertNotIn('train',o['dataset_kwargs']['data_files'])
            self.assertIsNone(o['dataset_name'])
            for field in ['doc_to_text','doc_to_choice','doc_to_target','metric_list','process_docs']:
                self.assertNotIn(field,o)

    def test_wrong_revision_missing_duplicate_split_or_denominator_rejected(self):
        variants=[]
        d=manifest();d['harness_revision']='wrong';variants.append(d)
        d=manifest();d['files'].pop();variants.append(d)
        for field,value in [('split','train'),('expected_rows',123),('task','other')]:
            d=manifest();d['files'][0][field]=value;variants.append(d)
        for d in variants:
            with self.subTest(d=d),patch.object(m,'digest',return_value='C'*64):
                with self.assertRaises(ValueError):m.task_specs(d)

    def test_asset_paths_cannot_escape_or_use_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for path in ['../other','/tmp/other']:
                with self.assertRaises(ValueError):m.local_path(root,path)
            (root/'linked').symlink_to(root/'absent')
            with self.assertRaises(ValueError):m.local_path(root,'linked')

    def test_report_never_overwrites_or_exceeds_result_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'report.json';m.write_report(p,{'ok':True})
            before=p.read_bytes()
            with self.assertRaises(FileExistsError):m.write_report(p,{'ok':False})
            self.assertEqual(before,p.read_bytes())
            with self.assertRaises(ValueError):m.write_report(p,{'text':'x'*20_000_000})


if __name__=='__main__':unittest.main()
