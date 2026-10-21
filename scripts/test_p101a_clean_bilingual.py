from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import unittest
from unittest.mock import patch
from scripts.diag_p101a_clean_bilingual import masked_record, TAGS
from tinylm.train.mtp_sft import Record, count_record


class BilingualTests(unittest.TestCase):
    def test_namespaces_independent(self):
        self.assertEqual(len(set(TAGS.values())), 3)
        self.assertNotIn("p101a_sft_mtp_v1_s1337", TAGS.values())

    def test_old_wrong_turn_is_not_target(self):
        original = Record([9, 8, 7, 6], [5, 4, 3, 4], [1, 1, 2, 2])
        with patch("tinylm.train.mtp_sft.encode_record", return_value=original):
            result = masked_record({"meta": {"supervised_assistant_turns": [2]}}, None)
        self.assertEqual(result.y, [-100, -100, 3, 4])
        self.assertEqual(result.segments, [0, 0, 2, 2])
        self.assertEqual(count_record(result)[2], 1)

    def test_all_correct_turns_preserved(self):
        original = Record([1, 2], [3, 4], [1, 1])
        with patch("tinylm.train.mtp_sft.encode_record", return_value=original):
            self.assertIs(masked_record({"meta": {}}, None), original)

    def test_zero_supervision_refused(self):
        original = Record([1, 2], [3, 4], [1, 1])
        with patch("tinylm.train.mtp_sft.encode_record", return_value=original):
            with self.assertRaises(ValueError): masked_record({"meta": {"supervised_assistant_turns": [2]}}, None)


if __name__ == "__main__": unittest.main()
