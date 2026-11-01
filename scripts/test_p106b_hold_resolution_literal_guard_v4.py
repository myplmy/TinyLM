"""Exact nonprogram approvals do not authorize any other source/body pair."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_literal_guard_v4 as guard


class ExactNonprogramPairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = guard.load_registry()

    def test_all_existing_and_new_actual_pairs_are_hash_bound(self):
        self.assertEqual(len(self.cases), 13)
        for ident, row in self.cases.items():
            raw = (ROOT / row["original"]).read_text(encoding="utf-8")
            clean = (ROOT / row["body"]).read_text(encoding="utf-8")
            self.assertTrue(guard.exact_pair_preserved(raw, clean, ident, self.cases), ident)

    def test_a_different_or_reordered_body_cannot_borrow_the_math_case(self):
        row = self.cases["expanded_train:940988"]
        raw = (ROOT / row["original"]).read_text(encoding="utf-8")
        clean = (ROOT / row["body"]).read_text(encoding="utf-8")
        self.assertFalse(guard.exact_pair_preserved(raw, clean + "New claim.", row["id"], self.cases))
        self.assertFalse(guard.exact_pair_preserved(raw, chr(10).join(reversed(clean.splitlines())), row["id"], self.cases))
        self.assertFalse(guard.exact_pair_preserved(raw, clean, "expanded_train:940989", self.cases))

    def test_actual_code_cannot_use_a_nonprogram_exact_pair(self):
        row = self.cases["expanded_train:513632"]
        clean = (ROOT / row["body"]).read_text(encoding="utf-8")
        fence = chr(96) * 3
        source = fence + "python" + chr(10) + "print('preserve')" + chr(10) + fence
        self.assertFalse(guard.exact_pair_preserved(source, clean, row["id"], self.cases))


if __name__ == "__main__":
    unittest.main(verbosity=2)
