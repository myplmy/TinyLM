#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import ast
import subprocess
import unittest
from scripts import diag_p106b_relation_interleaved_train as new
from scripts import diag_p106b_relation_train as old


class Runtime(unittest.TestCase):
    def test_every_training_function_ast_identical(self):
        def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)}
        a,b=functions(old.__file__),functions(new.__file__);self.assertEqual(set(a),set(b));self.assertGreaterEqual(len(a),9)
        for k in a:self.assertEqual(a[k],b[k],k)

    def test_exact_parent_and_only_selected_objective(self):
        self.assertEqual(new.ARMS,dict(fact1=1.));self.assertEqual(new.course.PARENT_SHA,old.course.PARENT_SHA)
        self.assertEqual(new.course.PARENT,old.course.PARENT)

    def test_fresh_checkpoint_namespace_and_preserved_old_outputs(self):
        paths=[new.checkpoint('fact1',e) for e in (None,1,2,3)]
        self.assertEqual(len(set(paths)),4);self.assertTrue(all(p!=old.checkpoint('fact1') for p in paths))
        self.assertNotEqual(new.course.EVIDENCE,old.course.EVIDENCE)

    def test_same_full_marginal_steps_and_native(self):
        self.assertEqual(new.course.info()['updates'],688);self.assertEqual(688*8192,5636096)

    def test_cli_check_only_no_new_namespace(self):
        before=(new.course.CORPUS.parent.exists(),new.course.EVIDENCE.exists())
        p=subprocess.run([sys.executable,'-B','-X','utf8',new.__file__,'--mode','cost','--arm','fact1','--check-only'],capture_output=True,text=True,timeout=30,cwd=ROOT)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('INTERLEAVED',p.stdout)
        self.assertEqual(before,(new.course.CORPUS.parent.exists(),new.course.EVIDENCE.exists()))


if __name__=='__main__':unittest.main()
