"""Cache identity invalidation, including changed reviews at the same body SHA."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_authored_remaining_deltas_v2 import signature


class Invalidation(unittest.TestCase):
    def setUp(self):
        self.a = dict(path='assigned/review_001.md', sha256='A' * 64)
        self.b = dict(path='assigned/review_002.md', sha256='B' * 64)

    def test_review_order_alone_not_new_payload(self):
        self.assertEqual(signature('C' * 64, [self.a, self.b]), signature('C' * 64, [self.b, self.a]))

    def test_revised_body_is_new(self):
        self.assertNotEqual(signature('C' * 64, [self.a]), signature('D' * 64, [self.a]))

    def test_changed_review_at_same_path_is_new(self):
        self.assertNotEqual(signature('C' * 64, [self.a]), signature('C' * 64, [dict(self.a, sha256='E' * 64)]))

    def test_new_or_removed_counter_review_is_new(self):
        self.assertNotEqual(signature('C' * 64, [self.a]), signature('C' * 64, [self.a, self.b]))

    def test_new_review_path_is_new(self):
        self.assertNotEqual(signature('C' * 64, [self.a]), signature('C' * 64, [dict(self.a, path='assigned/review_001_v2.md')]))


if __name__ == '__main__':
    unittest.main()
