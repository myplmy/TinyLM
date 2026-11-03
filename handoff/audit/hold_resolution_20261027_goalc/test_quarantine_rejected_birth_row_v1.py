"""Negative review rows cannot acquire bodies or masquerade as valid inputs."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import unittest

path = Path(__file__).with_name('quarantine_rejected_birth_row_v1.py')
spec = importlib.util.spec_from_file_location('negative_birth_review', path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
quarantine = helper.quarantine_rejected_row


class RejectedRowTest(unittest.TestCase):
    def setUp(self):
        self.source = dict(id='expanded_train:42', role='synthetic_role',
                           original=dict(path='synthetic_original.txt', sha256='A' * 64))
        self.review = dict(path='synthetic_review.md', sha256='B' * 64, archive='synthetic_archive.md')
        self.row = dict(id=self.source['id'], role=self.source['role'], cohort='synthetic_cohort',
                        status='MECHANICAL_REJECTION_NOT_APPLIED', review=dict(self.review),
                        error='ACCEPT_OUTPUT_IS_NOT_EXACT_ASSIGNED_INPUT')
        self.error = {key: self.row[key] for key in ('id', 'role', 'review', 'error')}

    def test_rejection_without_original_gets_only_manifest_identity(self):
        result = quarantine(self.row, self.source, [self.error])
        self.assertEqual(result['original'], self.source['original'])
        self.assertTrue(result['original_pin_from_source_manifest'])
        self.assertFalse(result['cache_admitted'])
        self.assertFalse(result['root_approved'])
        self.assertEqual(result['status'], 'BLOCKED_BY_RAW_MECHANICAL_REJECTION')

    def test_partial_body_and_output_references_cannot_survive_rejection(self):
        row = dict(self.row, original=self.source['original'], body='synthetic_body.txt',
                   clean_text_sha256='C' * 64, author_output=dict(path='synthetic_body.txt'),
                   body_references=['synthetic_body.txt'], cache_admitted=True, root_approved=True)
        result = quarantine(row, self.source, [self.error])
        self.assertFalse(result['original_pin_from_source_manifest'])
        self.assertFalse(result['cache_admitted'])
        for key in ('body', 'clean_text_sha256', 'author_output', 'body_references'):
            self.assertNotIn(key, result)

    def test_normal_complete_row_is_not_quarantined(self):
        row = dict(self.row, status='PINNED_BODY_NOT_ROOT_ADMISSION', original=self.source['original'])
        self.assertIsNone(quarantine(row, self.source, []))

    def test_normal_missing_original_is_explicit_failure(self):
        with self.assertRaisesRegex(ValueError, 'non-rejected raw row lacks'):
            quarantine(dict(self.row, status='PINNED_BODY_NOT_ROOT_ADMISSION'), self.source, [])

    def test_mismatched_original_fails_even_for_rejected_row(self):
        with self.assertRaisesRegex(ValueError, 'raw source binding changed'):
            quarantine(dict(self.row, original=dict(path='wrong.txt', sha256='A' * 64)),
                       self.source, [self.error])

    def test_wrong_source_identity_or_role_cannot_borrow_error(self):
        for update in (dict(id='expanded_train:43'), dict(role='different_role')):
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, 'identity or role'):
                quarantine(dict(self.row, **update), self.source, [self.error])

    def test_wrong_review_sha_wrong_error_missing_or_duplicate_match_fail(self):
        cases = [[], [self.error, self.error],
                 [dict(self.error, review=dict(self.review, sha256='D' * 64))],
                 [dict(self.error, error='different_error')]]
        for errors in cases:
            with self.subTest(errors=errors), self.assertRaisesRegex(ValueError, 'exact recorded error'):
                quarantine(self.row, self.source, errors)

    def test_real_validator_entry_parses_without_starting_a_snapshot(self):
        validator = path.with_name('validate_birth_delivery_snapshot_v3.py')
        result = subprocess.run([sys.executable, '-I', '-B', str(validator), '--help'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--snapshot-version', result.stdout)
        self.assertIn('--output-version', result.stdout)


if __name__ == '__main__':
    unittest.main()
