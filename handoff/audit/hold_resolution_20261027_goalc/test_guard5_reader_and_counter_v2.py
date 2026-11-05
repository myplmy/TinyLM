"""Keep prior25 regressions and verify the legacy materializer is never reached."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_guard5_reader_and_counter_v1 import CurrentTransport,Guard5Cases
import active_guard_v5_preflight_v1 as guard
import counter_quarantine_materializer_v1 as route


class QuarantineRouting(unittest.TestCase):
    def test_protected_hold_never_calls_legacy_payload_path(self):
        contract=guard.checked_contract()
        for item in contract['newly_quarantined_entries']:
            source=dict(id=item['id'],role=item['role'],occurrences=item['occurrences'],
                original=item['original'],candidate=item['derived_candidate'])
            row=dict(id=item['id'],decision='NEEDS_ROOT',body_references=[],declared_output_cell='—')
            callback=Mock(side_effect=AssertionError('legacy payload materializer called'))
            route.materialize(row,source,Path('/tmp'),callback)
            callback.assert_not_called();self.assertTrue(row['metadata_only'])
            self.assertFalse(row['protected_payload_opened']);self.assertNotIn('body',row)

    def test_ordinary_row_keeps_original_materializer_and_arguments(self):
        callback=Mock(return_value='original_result');row={'id':'expanded_train:7'};source={}
        directory=Path('/tmp');self.assertEqual(route.materialize(row,source,directory,callback),'original_result')
        callback.assert_called_once_with(row,source,directory)


if __name__=='__main__':unittest.main(verbosity=2)
