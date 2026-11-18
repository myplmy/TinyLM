"""Safety regressions for assigned delta contexts; synthetic strings only."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_authored_workset_context_v1 as reader


def case(ident, source, body):
    return dict(id=ident, original=dict(path='data_cache/p106b_hold_resolution_v1_20261027_goalc/fixture_source.txt',
                sha256=hashlib.sha256(source.encode()).hexdigest().upper()),
                body=dict(path='data_cache/p106b_hold_resolution_v1_20261027_goalc/fixture_body.txt',
                sha256=hashlib.sha256(body.encode()).hexdigest().upper()))


class AssignedContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reader.guard.activate()

    def test_bad_later_id_cannot_open_earlier_valid_payload(self):
        calls = []
        scope = dict(role='test', cases=[case('expanded_train:9900001', '원문', '원문')])
        with self.assertRaisesRegex(AssertionError, 'unassigned'):
            reader.collect(scope, 'test', ['expanded_train:9900001', 'expanded_train:9900002'],
                           'changes', 1, 1, loader=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_restricted_identity_rejected_before_any_payload(self):
        calls = []
        scope = dict(role='test', cases=[case('expanded_train:360211', 'synthetic', 'synthetic')])
        with self.assertRaises(ValueError):
            reader.collect(scope, 'test', ['expanded_train:360211'], 'changes', 1, 1,
                           loader=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_changed_pinned_body_is_rejected_without_returning_context(self):
        scope = dict(role='test', cases=[case('expanded_train:9900001', '값()', '값')])
        with self.assertRaises(AssertionError):
            reader.collect(scope, 'test', ['expanded_train:9900001'], 'changes', 1, 1,
                           loader=lambda *args: '다른 값'.encode())

    def test_utf8_source_frames_reconstruct_all_bytes(self):
        source = '가나다🙂' * 900
        scope = dict(role='test', cases=[case('expanded_train:9900001', source, source)])
        pieces = [reader.core.view_part(dict(candidate=source), 'candidate', n, width=reader.WIDTH)
                  for n in range(1, 5)]
        self.assertEqual(''.join(p['text'] for p in pieces), source)
        self.assertTrue(pieces[-1]['end_of_view'])
        self.assertTrue(all(len(p['text'].encode()) <= reader.WIDTH for p in pieces))

    def test_exact_delta_context_retains_explicit_premise(self):
        source = '조건이 맞을 때만 성립한다.\n\n이름()의 실제 설명이다.\n\n다음 설명이다.'
        body = source.replace('이름()', '이름')
        changes = reader.exact_changes(source, body, reader.core)
        context = reader.view_text(source, body, changes, 'changes')
        self.assertIn('조건이 맞을 때만 성립한다.', context)
        self.assertIn('ALL_EXACT_CHARACTER_CHANGES_END', context)
        self.assertIn('SMALL_FINAL_BODY_EOF', context)
        self.assertEqual(reader.core.base.reconstruct(source, changes), body)


if __name__ == '__main__':
    unittest.main(verbosity=2)
