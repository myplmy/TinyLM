from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewed_hold_partition_v1 import classify_hold, partition_occurrences


class ReviewedHoldTests(unittest.TestCase):
    def setUp(self):
        pin = dict(path='root_approval.json', sha256='A' * 64)
        self.row = dict(id='source:1', original_text_sha256='B' * 64,
            decision='HOLD', review_status='REVIEWED_NOT_ADMITTED',
            content_reviewed=True, root_disposition_approved=True,
            root_approved=False, hold_review_evidence=pin)
        self.cases = {'B' * 64: dict(id='source:1', decision='HOLD', reviewed=True,
            root_approved=True, authority_pin=pin)}

    def test_exact_reviewed_hold(self):
        self.assertEqual(classify_hold(self.row, self.cases), 'REVIEWED_NOT_ADMITTED')

    def test_unread_stays_unprocessed(self):
        row = dict(id='source:2', original_text_sha256='C' * 64, decision='HOLD',
            review_status='UNRESOLVED_NOT_ADMITTED', root_approved=False)
        self.assertEqual(classify_hold(row, self.cases), 'UNPROCESSED')

    def test_unread_cannot_be_renamed(self):
        row = dict(self.row, original_text_sha256='C' * 64)
        with self.assertRaises(ValueError): classify_hold(row, self.cases)

    def test_wrong_identity_rejected(self):
        with self.assertRaises(ValueError): classify_hold(dict(self.row, id='source:2'), self.cases)

    def test_changed_evidence_rejected(self):
        row = deepcopy(self.row); row['hold_review_evidence']['sha256'] = 'D' * 64
        with self.assertRaises(ValueError): classify_hold(row, self.cases)

    def test_body_leak_rejected(self):
        with self.assertRaises(ValueError): classify_hold(dict(self.row, text='leak'), self.cases)

    def test_body_sha_leak_rejected(self):
        with self.assertRaises(ValueError): classify_hold(dict(self.row, clean_text_sha256='E' * 64), self.cases)

    def test_training_body_approval_rejected(self):
        with self.assertRaises(ValueError): classify_hold(dict(self.row, root_approved=True), self.cases)

    def test_unresolved_claiming_review_rejected(self):
        row = dict(self.row, review_status='UNRESOLVED_NOT_ADMITTED')
        with self.assertRaises(ValueError): classify_hold(row, self.cases)

    def test_every_alias_position_counted(self):
        sources = [dict(id='source:1', original_text_sha256='B' * 64, input_ids=5),
            dict(id='source:11', original_text_sha256='B' * 64, input_ids=5)]
        result = partition_occurrences(sources, {'B' * 64:self.row}, self.cases)
        self.assertEqual(result, dict(documents=2, input_ids=10, remaining_hold=2,
            reviewed_hold=2, unprocessed=0))

    def test_duplicate_position_rejected(self):
        source = dict(id='source:1', original_text_sha256='B' * 64, input_ids=5)
        with self.assertRaises(ValueError): partition_occurrences([source, source], {'B' * 64:self.row}, self.cases)


if __name__ == '__main__': unittest.main()
