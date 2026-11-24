"""Closure serializer and preselected failed-case boundaries; no model is loaded."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diag_p106b_dvlm_native_closure_v2 as closure


class ClosureContracts(unittest.TestCase):
    def test_nested_loader_sets_are_losslessly_written_with_primary_negative(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(closure,'NEWBASE',Path(directory)):
            path=Path(directory)/'report.json'
            closure.write_scoped(path,dict(schema='test',expected_cases=1,status='NATIVE_HPA_NUMERICAL_NEGATIVE',
                returncode=2,loading_info=dict(missing_keys=set(),unexpected_keys={'b','a'})))
            result=json.loads(path.read_text())
            self.assertEqual(result['returncode'],2)
            self.assertEqual(result['loading_info'],dict(missing_keys=[],unexpected_keys=['a','b']))
            self.assertEqual(result['original_remaining_cases_NOT_RUN'],7)

    def test_scope_writer_cannot_touch_the_frozen_original_namespace(self):
        with self.assertRaisesRegex(ValueError,'outside'):
            closure.write_scoped(closure.V1BASE/'actual/never_write.json',{'test':1})

    def test_new_report_never_claims_original8_as_executed(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(closure,'NEWBASE',Path(directory)):
            path=Path(directory)/'report.json'
            with self.assertRaisesRegex(ValueError,'exactly1'):
                closure.write_scoped(path,dict(expected_cases=8,returncode=0))
            self.assertFalse(path.exists())

    def test_secondary_serialization_error_preserves_primary_failure_in_minimal_report(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(closure,'NEWBASE',Path(directory)):
            path=Path(directory)/'report.json'
            with self.assertRaises(TypeError):
                closure.write_scoped(path,dict(expected_cases=1,status='NATIVE_HPA_NUMERICAL_NEGATIVE',returncode=2,bad=object()))
            result=json.loads(path.read_text())
            self.assertEqual(result['returncode'],9)
            self.assertEqual(result['original_primary_returncode'],2)
            self.assertEqual(result['original_remaining_cases_NOT_RUN'],7)

    def test_only_original_first_negative_case_is_selected(self):
        cases=[{'row_id':str(i)} for i in range(8)]
        evidence=dict(row_id='0',ordinal=0,report=dict(passed=False))
        self.assertEqual(closure.select_case0(cases,evidence),cases[:1])

    def test_positive_or_changed_order_does_not_unlock_a_recovery_run(self):
        cases=[{'row_id':str(i)} for i in range(8)]
        for evidence in (dict(row_id='0',ordinal=0,report=dict(passed=True)),dict(row_id='1',ordinal=0,report=dict(passed=False))):
            with self.assertRaises(ValueError):closure.select_case0(cases,evidence)


if __name__=='__main__':unittest.main()
