"""Exercise fail-closed use of the actual already reviewed pair without TXT writes."""
from pathlib import Path
import copy
import json
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens
from exact_counter74_numeric_context_v1 import verify_exact_context
from numeric_atom_integrity_v1 import numeric_atom_changes


class ExactNumericContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        activate()
        p = json.loads((AUDIT/'COUNTER74_TWO_NUMERIC_CONTEXT_CLOSURE_V1.json').read_bytes())
        item = p['records'][0]
        cls.args = dict(item=item, key=item['id'], source_pin=item['original'], body_pin=item['body'],
            review=item['review'], original=(ROOT/item['original']['path']).read_text(encoding='utf-8'),
            body=(ROOT/item['body']['path']).read_text(encoding='utf-8'))
        cls.args['flags'] = numeric_atom_changes(cls.args['original'], cls.args['body'])

    def call(self, **changes):
        args = copy.deepcopy(self.args)
        args.update(changes)
        return verify_exact_context(**args)

    def test_actual_closed_pair(self):
        self.assertTrue(self.call())

    def test_different_id_rejected(self):
        with self.assertRaises(AssertionError):
            self.call(key='expanded_train:75')

    def test_numeric_change_rejected(self):
        with self.assertRaises(AssertionError):
            self.call(body=self.args['body'].replace('4가지', '5가지'))

    def test_review_change_rejected(self):
        review = dict(self.args['review'], sha256='0'*64)
        with self.assertRaises(AssertionError):
            self.call(review=review)

    def test_changed_flag_span_rejected(self):
        flags = copy.deepcopy(self.args['flags'])
        flags[0]['body_span'] = [368, 369]
        with self.assertRaises(AssertionError):
            self.call(flags=flags)

    def test_changed_source_closure_span_rejected(self):
        item = copy.deepcopy(self.args['item'])
        item['closed_flags'][0]['source_span'] = [1275, 1276]
        with self.assertRaises(AssertionError):
            self.call(item=item)

    def test_changed_anchor_rejected(self):
        item = copy.deepcopy(self.args['item'])
        item['source_anchor'] = 'UNRELATED_ANCHOR'
        with self.assertRaises(AssertionError):
            self.call(item=item)

    @classmethod
    def tearDownClass(cls):
        assert_no_protected_opens()


if __name__ == '__main__':
    unittest.main(verbosity=2)
