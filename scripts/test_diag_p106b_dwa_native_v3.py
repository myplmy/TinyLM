"""A block's row list must survive aggregate-accounting attachment."""
import unittest
from scripts.diag_p106b_dwa_native_v3 import merge_accounting
class DWAStorageContracts(unittest.TestCase):
    def test_per_row_records_and_row_count_have_distinct_fields(self):
        rows=[dict(row_id='a',student_count=3,teacher_count=5)]
        block=dict(rows=rows,raw_sums={'student_ce':2.})
        result=merge_accounting(block,dict(rows=1,student_targets=3,teacher_targets=5))
        self.assertIs(result['rows'],rows);self.assertEqual(result['rows_count'],1)
        self.assertIs(block['rows'],rows);self.assertEqual(result['raw_sums'],block['raw_sums'])
    def test_previously_overwritten_or_mismatched_row_list_is_refused(self):
        for block,count in [(dict(rows=128),128),(dict(rows=[dict(row_id='a')]),2)]:
            with self.assertRaisesRegex(ValueError,'per-row list'):merge_accounting(block,dict(rows=count))
if __name__=='__main__':unittest.main()
