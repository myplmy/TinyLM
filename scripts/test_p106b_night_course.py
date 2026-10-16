from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from scripts import p106b_night_course as c


class Course(unittest.TestCase):
    def test_stratified_and_deterministic(self):
        rows = [dict(meta=dict(language=l, kind=k), id=i) for l in ('ko', 'en')
                for k in ('a', 'b') for i in range(8)]
        a = c.stratified(rows, 16, ('language', 'kind'))
        self.assertEqual(a, c.stratified(list(reversed(rows)), 16, ('language', 'kind')))
        self.assertEqual(len(a), 16)

    def test_no_repetition_to_fill(self):
        rows = [dict(meta=dict(language='ko'), id=0)]
        with self.assertRaises(ValueError): c.stratified(rows, 2, ('language',))

    def test_native_nonoverlap_including_previous_windows(self):
        old = [4300, 11000]
        result = c.choose_native(100000, 30, old)
        self.assertEqual(len(result), 30)
        self.assertTrue(all(abs(a - b) >= 1025 for a in result for b in old))
        ordered = sorted(result)
        self.assertTrue(all(b - a >= 1025 for a, b in zip(ordered, ordered[1:])))

    def test_native_off_by_one_end(self):
        self.assertEqual(c.choose_native(1025, 1, []), [0])
        with self.assertRaises(ValueError): c.choose_native(1024, 1, [])

    def test_deadline_aware(self):
        self.assertEqual(c.DEADLINE.isoformat(), '2026-10-17T01:00:00+00:00')
        self.assertEqual((c.DEADLINE - c.TRAIN_STOP).total_seconds(), 3600)


if __name__ == '__main__': unittest.main()
