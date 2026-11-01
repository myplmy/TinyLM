"""합성 reader로 범위 밖 파일을 열지 않으면서 원 실패 조건이 남는지 검산한다."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


scope=module('private_scope',Path(__file__).with_name('scoped_plan_inventory_v1.py'))
original=module('original_plan',ROOT/'scripts/check_plan_numbers.py')
UNKNOWN='P'+('9'*3)


class ScopeContract(unittest.TestCase):
    def test_foreign_reader_never_called_and_wip_remains_skipped(self):
        called=[]
        def read(name):
            called.append(name)
            if name!='docs/owned.md':raise AssertionError('unowned read')
            return UNKNOWN
        refs=scope.reference_map(original,['docs/owned.md','handoff/WIP_owned.md'],read)
        self.assertEqual(called,['docs/owned.md'])
        self.assertEqual(refs,{UNKNOWN:{'docs/owned.md'}})

    def test_unknown_owned_reference_still_fails_original_criterion(self):
        refs=scope.reference_map(original,['docs/owned.md'],lambda _:UNKNOWN)
        missing,_=original.unresolved_refs(refs,{}, {})
        self.assertEqual(missing,{UNKNOWN:['docs/owned.md']})

    def test_registry_filters_only_targets_without_blanket_number_waiver(self):
        header=chr(9).join(['plan_id','path','reason'])
        raw=chr(10).join([header,chr(9).join([UNKNOWN,'docs/owned.md','fixture']),
            chr(9).join([UNKNOWN,'handoff/private/unowned.md','fixture'])])
        subset,metadata=scope.registry_subset(raw,['docs/owned.md'])
        self.assertIn('docs/owned.md',subset)
        self.assertNotIn('unowned.md',subset)
        self.assertEqual((metadata['included'],metadata['excluded']),(1,1))

    def test_malformed_and_unsafe_registry_metadata_still_rejected(self):
        header=chr(9).join(['plan_id','path','reason'])
        for line in ['broken',chr(9).join([UNKNOWN,'../unowned.md','fixture'])]:
            subset,_=scope.registry_subset(header+chr(10)+line,[])
            rows,errors=original.load_diagnostic_refs(scope.RegistryView(subset))
            self.assertTrue(errors)
            self.assertEqual(rows,{})

    def test_content_pin_failure_keeps_original_validation(self):
        header=chr(9).join(['plan_id','path','reason'])
        reason='sha256='+('0'*64)+'; fixture'
        text=header+chr(10)+chr(9).join([UNKNOWN,'docs/owned.md',reason])
        subset,_=scope.registry_subset(text,['docs/owned.md'])
        class FakeRoot:
            def __truediv__(self,name):
                if name!='docs/owned.md':raise AssertionError('unowned read')
                return SimpleNamespace(is_file=lambda:True,read_bytes=lambda:UNKNOWN.encode())
        with patch.object(original,'ROOT',FakeRoot()):
            rows,errors=original.load_diagnostic_refs(scope.RegistryView(subset))
        self.assertEqual(rows,{})
        self.assertTrue(any('content pin differs' in error for error in errors))

    def test_absolute_or_parent_reference_paths_rejected(self):
        for name in ['/unowned.md','../unowned.md']:
            with self.subTest(name=name),self.assertRaises(ValueError):
                scope.reference_map(original,[name],lambda _:UNKNOWN)


if __name__=='__main__':unittest.main()
