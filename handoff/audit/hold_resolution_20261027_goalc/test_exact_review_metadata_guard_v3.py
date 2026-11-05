"""Exercise real metadata only; protected source/candidate files stay unopened."""
from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exact_review_metadata_guard_v3 import (ROOT, inv, checked_contract, load_receipts,
    validate_sources, validate_review, materialize_metadata_only, NEW_ID)


class MetadataOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = checked_contract()
        cls.receipts = load_receipts(cls.contract)
        cls.sources = {}
        for key, receipt in cls.receipts.items():
            manifest = inv.cache.read(ROOT/receipt['manifest']['path'])
            cls.sources[key] = next(row for row in manifest['rows'] if row['id'] == key)

    def test_new_source_identity_is_closed_without_payload(self):
        self.assertEqual(validate_sources({NEW_ID: self.sources[NEW_ID]}, self.contract,
            self.receipts[NEW_ID]['cohort'], self.receipts), {NEW_ID})

    def test_old_source_exact_hold_rule_remains_closed(self):
        key = 'expanded_train:28876'
        self.assertEqual(validate_sources({key: self.sources[key]}, self.contract,
            self.receipts[key]['cohort'], self.receipts), {key})

    def test_wrong_role_or_candidate_hash_fails(self):
        for change in ['role', 'candidate']:
            source = copy.deepcopy(self.sources[NEW_ID])
            if change == 'role': source['role'] = 'context_controls'
            else: source['candidate']['sha256'] = '0'*64
            with self.assertRaises(ValueError):
                validate_sources({NEW_ID: source}, self.contract,
                    self.receipts[NEW_ID]['cohort'], self.receipts)

    def test_authored_candidate_is_preserved_as_unadmitted_metadata(self):
        row = dict(id=NEW_ID, decision='EDIT', original_status='REVISE_TEXT',
            review=self.receipts[NEW_ID]['author_review'], declared_output_cell='synthetic-unadmitted-body.txt',
            body_references=['synthetic-unadmitted-body.txt'])
        materialize_metadata_only(row, self.sources[NEW_ID], self.receipts)
        self.assertEqual(row['decision'], 'NEEDS_ROOT')
        self.assertEqual(row['authored_decision_before_metadata_nonadmission'], 'EDIT')
        self.assertEqual(row['authored_body_references'], ['synthetic-unadmitted-body.txt'])
        self.assertEqual(row['body_references'], [])
        self.assertFalse(row['protected_payload_opened'])
        self.assertFalse(row['root_approved'])
        self.assertNotIn('body', row)

    def test_changed_review_or_materialized_body_fails(self):
        row = dict(id=NEW_ID, review=self.receipts[NEW_ID]['author_review'])
        with self.assertRaises(ValueError): validate_review(dict(row, body='anything'), self.receipts)
        with self.assertRaises(ValueError):
            validate_review(dict(row, review=dict(row['review'], sha256='0'*64)), self.receipts)


if __name__ == '__main__': unittest.main(verbosity=2)
