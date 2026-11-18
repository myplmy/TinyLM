"""Check complete suspect coverage, including semantic counterexamples."""
from pathlib import Path
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
from read_authored_native_windows_v1 import native_windows, render


class NativeWindowsTests(unittest.TestCase):
    def test_far_apart_matches_in_one_large_paragraph_are_all_delivered(self):
        text = 'prose '*9000+' foo() '+'more '*9000+' bar()'
        result = native_windows(text)
        self.assertEqual(result['match_count'], 2)
        self.assertEqual({i for w in result['windows'] for i in w['match_numbers']}, {1, 2})
        self.assertLess(sum(len(w['text']) for w in result['windows']), len(text)//20)

    def test_biological_empty_annotation_is_never_discarded_as_a_call(self):
        result = native_windows('positivesense ssRNA(+) or negativesense ssRNA()')
        self.assertEqual(result['match_count'], 1)
        self.assertIn('ssRNA()', render(result))
        self.assertTrue(result['matches_are_not_automatically_approved'])

    def test_table_marker_dangling_alias_and_empty_title_all_remain_visible(self):
        result = native_windows('( ) Number of cows; name(, 1927 ~ ); title《》')
        self.assertGreaterEqual(result['match_count'], 3)
        self.assertIn('Number of cows', render(result))
        self.assertIn('1927 ~', render(result))
        self.assertIn('《》', render(result))

    def test_no_match_is_not_a_semantic_or_other_flag_pass(self):
        result = native_windows('unbalanced “quotation and a value =')
        self.assertEqual(result['match_count'], 0)
        self.assertTrue(result['other_deferral_types_not_resolved'])
        self.assertIn('UNBALANCED_CURLY_DOUBLE_QUOTES_NEED_CONTEXT', result['non_native_readiness_deferrals'])


if __name__ == '__main__':
    unittest.main()
