"""Synthetic cache-boundary tests; no HF import, model, GPU or assets."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import prepare_p106b_official_eval as m


class CachePolicyTests(unittest.TestCase):
    def expected(self):
        return dict(HF_HOME=str(m.ROOT/'HF'),HF_HUB_CACHE=str(m.ROOT/'HF/hub'),
                    HF_DATASETS_CACHE=str(m.ROOT/'HF/datasets'))

    def fixture(self):
        module=ModuleType('tinylm')
        module.paths=SimpleNamespace(ROOT=m.ROOT,HF_DIR=m.ROOT/'HF')
        return module

    def test_pure_import_has_no_top_level_hf_or_model_import(self):
        tree=ast.parse(Path(m.__file__).read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node,ast.Import):
                self.assertFalse(any(alias.name.split('.')[0] in {'tinylm','torch','datasets','transformers','huggingface_hub'} for alias in node.names))
            elif isinstance(node,ast.ImportFrom):
                self.assertNotIn((node.module or '').split('.')[0],{'tinylm','torch','datasets','transformers','huggingface_hub'})

    def test_correct_existing_policy_is_recorded_and_idempotent(self):
        with patch.dict(os.environ,self.expected(),clear=True),patch.object(m,'_HF_CACHE_CONFIGURED',False),patch.dict(sys.modules,{'tinylm':self.fixture()}):
            first=m.configure_hf_cache()
            with patch.dict(sys.modules,{'datasets':ModuleType('datasets')}):
                self.assertEqual(m.configure_hf_cache(),first)
            self.assertTrue(first['process_only'])
            self.assertFalse(first['external_environment_files_modified'])

    def test_external_override_is_rejected_before_project_import(self):
        for key in ('TINYLM_DIR','TINYLM_HF'):
            with self.subTest(key=key),patch.dict(os.environ,{key:'/tmp/not_the_project'},clear=True),patch.object(m,'_HF_CACHE_CONFIGURED',False):
                with self.assertRaisesRegex(ValueError,'override'):m.configure_hf_cache()
                self.assertFalse(m._HF_CACHE_CONFIGURED)

    def test_hf_first_is_rejected_even_with_matching_environment(self):
        for name in ('datasets','transformers.utils','huggingface_hub'):
            with self.subTest(name=name),patch.dict(os.environ,self.expected(),clear=True),patch.object(m,'_HF_CACHE_CONFIGURED',False),patch.dict(sys.modules,{name:ModuleType(name)}):
                with self.assertRaisesRegex(RuntimeError,'already imported'):m.configure_hf_cache()
                self.assertFalse(m._HF_CACHE_CONFIGURED)

    def test_missing_policy_cannot_be_claimed_configured(self):
        with patch.dict(os.environ,{},clear=True),patch.object(m,'_HF_CACHE_CONFIGURED',False),patch.dict(sys.modules,{'tinylm':self.fixture()}):
            with self.assertRaisesRegex(ValueError,'did not take effect'):m.configure_hf_cache()
            self.assertFalse(m._HF_CACHE_CONFIGURED)

    def test_cached_module_with_wrong_root_is_rejected(self):
        fake=self.fixture();fake.paths.ROOT=Path('/tmp/not_the_project')
        with patch.dict(os.environ,self.expected(),clear=True),patch.object(m,'_HF_CACHE_CONFIGURED',False),patch.dict(sys.modules,{'tinylm':fake}):
            with self.assertRaisesRegex(ValueError,'different root'):m.configure_hf_cache()

    def test_late_environment_mutation_is_not_silently_repaired(self):
        for key in (*self.expected(),'TRANSFORMERS_CACHE'):
            values=self.expected();values[key]='/tmp/not_the_project'
            with self.subTest(key=key),patch.dict(os.environ,values,clear=True),patch.object(m,'_HF_CACHE_CONFIGURED',True):
                with self.assertRaisesRegex(ValueError,'changed'):m.configure_hf_cache()

    def test_call_order_precedes_harness_and_dataset_import(self):
        for filename,function,follow in (
            ('p106b_official_tasks.py','load_tasks','prepare_harness'),
            ('diag_p106b_official_core6.py','model_runtime','research_adapter'),
            ('prepare_p106b_official_eval.py','prepare','load_dataset')):
            with self.subTest(filename=filename):
                source=(ROOT/'scripts'/filename).read_text(encoding='utf-8')
                tree=ast.parse(source)
                node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==function)
                body=ast.get_source_segment(source,node)
                self.assertLess(body.index('configure_hf_cache()'),body.index(follow))


if __name__=='__main__':unittest.main()
