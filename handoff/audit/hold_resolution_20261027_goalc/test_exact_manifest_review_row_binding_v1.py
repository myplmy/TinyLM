"""Prevent historical numeric rows from crossing source namespaces."""
from pathlib import Path
import importlib.util
import unittest

path = Path(__file__).with_name('exact_manifest_review_row_binding_v1.py')
spec = importlib.util.spec_from_file_location('exact_manifest_binding_test', path)
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)
resolve, parse, _ = binding.load_parser()


class BindingTest(unittest.TestCase):
    def bound(self, row, expected, allowed):
        payload = ('| ID | 판정 | 실제 판독 범위 | 출력 | 근거 |' + chr(10) + row + chr(10)).encode()
        return binding.exact_entry(payload, expected, set(allowed), resolve, parse)

    def test_historical_bare_row_with_unique_manifest_identity(self):
        row = '| 1053429 | REVISE_TEXT | full source and diff | source.txt | reason |'
        self.assertEqual(self.bound(row, 'expanded_train:1053429', ['expanded_train:1053429'])['raw'], row)

    def test_numeric_collision_between_source_namespaces_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'multiple source namespaces'):
            self.bound('| 1053429 | ACCEPT_CANDIDATE | full | input.txt | reason |',
                       'expanded_train:1053429', ['expanded_train:1053429', 'validation:1053429'])

    def test_outside_manifest_cannot_borrow_an_existing_row(self):
        with self.assertRaisesRegex(ValueError, 'outside the exact manifest'):
            self.bound('| expanded_train:1 | ACCEPT_CANDIDATE | full | input.txt | reason |',
                       'expanded_train:1', ['validation:1'])

    def test_duplicate_source_rows_do_not_silently_pick_one(self):
        row = '| expanded_train:1 | ACCEPT_CANDIDATE | full | input.txt | reason |'
        with self.assertRaisesRegex(ValueError, 'not uniquely bound'):
            self.bound(row + chr(10) + row, 'expanded_train:1', ['expanded_train:1'])

    def test_prose_mention_does_not_become_a_review_row(self):
        with self.assertRaisesRegex(ValueError, 'not uniquely bound'):
            self.bound('Some prose mentions expanded_train:1 and an output.txt.',
                       'expanded_train:1', ['expanded_train:1'])


if __name__ == '__main__':
    unittest.main()
