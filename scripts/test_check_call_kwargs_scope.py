"""AST-only lexical binding regressions; no repository model assets."""
from pathlib import Path
import ast
import tempfile
import unittest
from unittest.mock import patch
from scripts import check_call_kwargs as c


class ScopeTests(unittest.TestCase):
    def scan(self,text):
        with tempfile.TemporaryDirectory(prefix='tinylm_call_scope_') as folder:
            root=Path(folder);(root/'scripts').mkdir();path=root/'scripts/fixture.py';path.write_text(text)
            fake=ast.parse('def pairs(): pass\ndef compact(report): pass\ndef target(x): pass')
            idx={n.name:(root/'scripts/unrelated.py',c._sig(n)) for n in fake.body}
            errors=[]
            with patch.object(c,'ROOT',root):c.scan(path,idx,errors)
            return errors

    def test_nested_pairs_uses_actual_two_argument_definition(self):
        self.assertEqual(self.scan('def outer():\n def pairs(rows, encoded): return rows\n return pairs(1,2)\n'),[])

    def test_nested_compact_default_arity_is_not_unrelated_global(self):
        self.assertEqual(self.scan('def outer():\n def compact(value, limit=180): return value\n return compact(1,120)\n'),[])

    def test_actual_nested_excess_arity_and_unknown_keyword_still_fail(self):
        self.assertEqual(len(self.scan('def outer():\n def pairs(rows): return rows\n return pairs(1,2,bogus=3)\n')),2)

    def test_sibling_scope_does_not_supply_the_signature(self):
        text='def pairs(): return 1\ndef outer():\n def pairs(x,y): return x\n return pairs(1,2)\npairs(1,2)\n'
        errors=self.scan(text);self.assertEqual(len(errors),1);self.assertEqual(errors[0][1],5)

    def test_parameter_assignment_and_import_shadowing_are_not_globals(self):
        for body in ('def outer(pairs):\n return pairs(1,2)\n',
                     'def outer():\n pairs=lambda x,y: x\n return pairs(1,2)\n',
                     'def outer():\n from elsewhere import pairs\n return pairs(1,2)\n'):
            self.assertEqual(self.scan(body),[])

    def test_enclosing_closure_definition_resolves(self):
        self.assertEqual(self.scan('def outer():\n def pairs(x,y): return x\n def inner(): return pairs(1,2)\n return inner()\n'),[])

    def test_varargs_still_allowed_and_bad_keyword_still_checked(self):
        self.assertEqual(self.scan('def outer():\n def pairs(*args,**kwargs): return 1\n return pairs(1,2,x=3)\n'),[])

    def test_other_module_global_existing_policy_still_checked(self):
        self.assertEqual(len(self.scan('from scripts.unrelated import target\ntarget(1,2)\n')),1)

    def test_function_local_repository_import_still_checked(self):
        self.assertEqual(len(self.scan('def outer():\n from scripts.unrelated import target\n return target(1,2)\n')),1)

    def test_local_repository_import_shadows_outer_parameter(self):
        text='def outer(target):\n def inner():\n  from scripts.unrelated import target\n  return target(1,2)\n return inner()\n'
        self.assertEqual(len(self.scan(text)),1)

    def test_local_repository_import_shadows_outer_function(self):
        text='def outer():\n def target(x,y): return x\n def inner():\n  from scripts.unrelated import target\n  return target(1,2)\n return inner()\n'
        self.assertEqual(len(self.scan(text)),1)

    def test_global_declaration_is_not_a_blanket_exemption(self):
        self.assertEqual(len(self.scan('def target(x): return x\ndef outer():\n global target\n return target(1,2)\n')),1)

    def test_nonlocal_uses_actual_enclosing_definition(self):
        text='def outer():\n def target(x): return x\n def inner():\n  nonlocal target\n  return target(1,2)\n return inner()\n'
        self.assertEqual(len(self.scan(text)),1)

    def test_repeated_global_import_boundaries_are_not_ambiguous(self):
        text='def outer():\n global target\n from scripts.unrelated import target\n global target\n return target(1,2)\n'
        self.assertEqual(len(self.scan(text)),1)

    def test_repeated_nonlocal_boundary_still_checks_outer_definition(self):
        text='def outer():\n def target(x): return x\n def inner():\n  nonlocal target\n  nonlocal target\n  return target(1,2)\n return inner()\n'
        self.assertEqual(len(self.scan(text)),1)


if __name__=='__main__':unittest.main()
