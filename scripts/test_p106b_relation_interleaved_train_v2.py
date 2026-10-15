#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import ast
import subprocess
import unittest
from scripts import diag_p106b_relation_interleaved_train_v2 as new
from scripts import diag_p106b_relation_interleaved_train as old


class Runtime(unittest.TestCase):
    def test_all_mathematical_training_functions_ast_identical(self):
        def defs(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(defs(old.__file__),defs(new.__file__))

    def test_same_parent_objective_data_but_fresh_output(self):
        self.assertEqual(new.ARMS,old.ARMS);self.assertEqual(new.course.PARENT_SHA,old.course.PARENT_SHA)
        self.assertEqual(new.course.CORPUS,old.course.CORPUS);self.assertNotEqual(new.course.EVIDENCE,old.course.EVIDENCE)
        self.assertNotEqual(new.checkpoint('fact1'),old.checkpoint('fact1'))

    def test_check_only_no_model_or_new_namespace(self):
        before=new.course.EVIDENCE.exists();p=subprocess.run([sys.executable,'-B','-X','utf8',new.__file__,'--mode','cost','--arm','fact1','--check-only'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('RUNTIME_V2',p.stdout);self.assertEqual(before,new.course.EVIDENCE.exists())


if __name__=='__main__':unittest.main()
