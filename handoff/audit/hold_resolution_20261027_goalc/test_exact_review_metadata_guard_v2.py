"""Boundary tests use invented metadata, never a real protected payload."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exact_review_metadata_guard_v2 as guard


class MetadataGuardTests(unittest.TestCase):
    def setUp(self):
        key = guard.KNOWN_ID
        self.source = dict(id=key, role='context_controls', occurrences=2,
            original=dict(path='invented/original.txt', sha256='ORIGINAL'),
            candidate=dict(path='invented/candidate.txt', sha256='CANDIDATE'),
            source='expanded_train', split='train', source_ids=[5, 9],
            source_ids_sha256='IDS', input_ids=4, original_text_sha256='ORIGINAL')
        trusted = {name:self.source[name] for name in ('source', 'split', 'source_ids',
            'source_ids_sha256', 'input_ids', 'original_text_sha256')}
        self.contract = dict(restricted_ids=[key, 'expanded_train:999'],
            restricted_hashes=['ORIGINAL', 'CANDIDATE', 'OTHER_PROTECTED'],
            trusted_metadata={key:trusted}, new_restricted_entry=dict(id=key,
                original=deepcopy(self.source['original']),
                derived_candidate=deepcopy(self.source['candidate']), occurrences=2))
        self.receipt = dict(id=key, cohort=guard.KNOWN_COHORT, role='context_controls',
            root_hold_disposition_approved=True, body_admission_approved=False,
            decision='NEEDS_ROOT', occurrences=2,
            original=deepcopy(self.source['original']), candidate=deepcopy(self.source['candidate']),
            author_review=dict(path='invented/review_001.md', sha256='REVIEW'),
            receipt_pin=dict(path='invented/receipt.json', sha256='RECEIPT'))
        self.row = dict(id=key, decision='NEEDS_ROOT', original_status='NEEDS_ROOT',
            review=deepcopy(self.receipt['author_review']), body_references=[],
            declared_output_cell='본문 없음')

    def validate(self):
        return guard.validate_sources({self.source['id']:self.source}, self.contract,
            guard.KNOWN_COHORT, self.receipt)

    def test_exact_hold_is_metadata_only_without_any_payload_open(self):
        with patch.object(Path, 'open', side_effect=AssertionError('payload access')):
            self.assertEqual(self.validate(), {guard.KNOWN_ID})
            guard.materialize_metadata_only(self.row, self.source, self.receipt)
        self.assertTrue(self.row['metadata_only'])
        self.assertFalse(self.row['protected_payload_opened'])
        self.assertFalse(self.row['cache_admitted'])
        self.assertNotIn('body', self.row)

    def test_normal_source_needs_no_exception(self):
        self.source.update(id='expanded_train:123', original=dict(path='normal.txt', sha256='NORMAL'),
                           candidate=dict(path='normal2.txt', sha256='NORMAL2'))
        self.assertEqual(self.validate(), set())

    def test_unknown_protected_id_fails(self):
        self.source['id'] = 'expanded_train:999'
        with self.assertRaises(ValueError): self.validate()

    def test_nonprotected_id_with_original_hash_collision_fails(self):
        self.source['id'] = 'expanded_train:123'
        with self.assertRaises(ValueError): self.validate()

    def test_nonprotected_id_with_candidate_hash_collision_fails(self):
        self.source.update(id='expanded_train:123', original=dict(path='normal.txt', sha256='NORMAL'))
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_cohort_fails(self):
        with self.assertRaises(ValueError):
            guard.validate_sources({self.source['id']:self.source}, self.contract, 'other', self.receipt)

    def test_original_candidate_lineage_and_role_mutations_fail(self):
        for label in ('original', 'candidate', 'source_ids_sha256', 'role', 'occurrences'):
            original = deepcopy(self.source)
            if label in ('original', 'candidate'): self.source[label]['path'] += '.changed'
            elif label == 'occurrences': self.source[label] = 3
            else: self.source[label] = 'CHANGED'
            with self.subTest(label=label), self.assertRaises(ValueError): self.validate()
            self.source = original

    def test_body_decisions_fail_before_materialization(self):
        for decision in ('EDIT_TEXT', 'ADOPT_CANDIDATE', 'KEEP_SOURCE', 'EDIT_RECIPE', 'EXCLUDE'):
            self.row['decision'] = decision
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                guard.materialize_metadata_only(self.row, self.source, self.receipt)
            self.assertNotIn('body', self.row)

    def test_changed_review_pin_fails(self):
        self.row['review']['sha256'] = 'CHANGED'
        with self.assertRaises(ValueError): guard.validate_review(self.row, self.receipt)

    def test_declared_txt_fails(self):
        self.row['declared_output_cell'] = 'new.txt'
        with self.assertRaises(ValueError): guard.validate_review(self.row, self.receipt)

    def test_nonempty_body_reference_fails(self):
        self.row['body_references'] = ['new.txt']
        with self.assertRaises(ValueError): guard.validate_review(self.row, self.receipt)

    def test_preexisting_body_fails(self):
        self.row['body'] = 'new.txt'
        with self.assertRaises(ValueError): guard.validate_review(self.row, self.receipt)

    def test_unapproved_hold_fails(self):
        self.receipt['root_hold_disposition_approved'] = False
        with self.assertRaises(ValueError): self.validate()


if __name__ == '__main__':
    unittest.main(verbosity=2)
