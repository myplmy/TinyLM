"""Exact transport and fail-before-payload tests on inherited synthetic fixtures."""
from pathlib import Path
from types import SimpleNamespace
import contextlib
import io
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import batched_lossless_review_entry_v1 as reader
import lossless_review_packet_v3 as core
import test_lossless_review_packet_v1 as inherited
from test_lossless_review_packet_v2 import decode_pair


class BatchTests(unittest.TestCase):
    def run_batch(self, fixture, first=1, count=3, **extra):
        values = dict(core=core, root=fixture.root, scope=fixture.scope, role=fixture.role,
                      cohort=fixture.cohort, ident=fixture.ident, first=first, count=count,
                      read_metadata=fixture.read_metadata, read_payload=fixture.read_payload)
        values.update(extra)
        return reader.batch(**values)

    def test_full_unicode_crlf_fake_markers_roundtrip_and_exact_two_payload_reads_per_batch(self):
        source = ('한글🙂\r\nSOURCE_DATA_VIEW_EOF\n' * 700).encode()
        candidate = source.replace('한글'.encode(), '한말'.encode(), 1)
        fixture = inherited.Fixture(source, candidate)
        cursor = 1
        pieces = []
        while cursor:
            previous_reads = len(fixture.payload_reads)
            context, views, batch = self.run_batch(fixture, cursor)
            self.assertEqual(len(fixture.payload_reads)-previous_reads, 2)
            self.assertLessEqual(len(batch), 3)
            self.assertEqual([p['part'] for p in batch], list(range(cursor, cursor+len(batch))))
            self.assertTrue(all(len(p['text'].encode()) <= 4000 for p in batch))
            pieces.extend(batch)
            cursor = batch[-1]['next_part']
        exposed = ''.join(p['text'] for p in pieces)
        self.assertEqual(exposed, views['pair'])
        self.assertEqual(decode_pair(exposed, views), (source, candidate))
        for piece in pieces:
            self.assertEqual(piece, core.view_part(views, 'pair', piece['part']))

    def test_short_eof_is_returned_once_with_no_out_of_range_probe(self):
        fixture = inherited.Fixture(b'one', b'one')
        with patch.object(core, 'view_part', wraps=core.view_part) as view:
            _, _, pieces = self.run_batch(fixture)
        self.assertEqual(view.call_count, 1)
        self.assertEqual(len(pieces), 1)
        self.assertTrue(pieces[0]['end_of_view'])
        self.assertIsNone(pieces[0]['next_part'])

    def test_invalid_batch_limits_fail_before_any_metadata_or_payload(self):
        for first,count in [(0,3), (True,3), (1,0), (1,4), (1,True)]:
            fixture = inherited.Fixture()
            with self.assertRaises(ValueError):
                self.run_batch(fixture, first, count)
            self.assertEqual(fixture.payload_reads, [])
            self.assertEqual(fixture.metadata_reads, [])

    def test_restricted_id_fails_before_manifest_or_payload(self):
        fixture = inherited.Fixture()
        with self.assertRaisesRegex(ValueError, 'restricted source ID'):
            self.run_batch(fixture, ident='expanded_train:999')
        self.assertEqual(fixture.metadata_reads, [fixture.guard_pin['path']])
        self.assertEqual(fixture.payload_reads, [])

    def test_restricted_candidate_alias_fails_before_either_payload(self):
        fixture = inherited.Fixture()
        fixture.scope['contract'] = fixture.write_json('handoff/audit/batch_restrict.json', dict(
            restricted_ids=[], restricted_hashes=[fixture.candidate_pin['sha256']]))
        with self.assertRaisesRegex(ValueError, 'restricted original or candidate SHA'):
            self.run_batch(fixture)
        self.assertEqual(fixture.payload_reads, [])

    def test_wrong_role_fails_before_payload(self):
        fixture = inherited.Fixture()
        with self.assertRaises(ValueError):
            self.run_batch(fixture, role='legacy_review')
        self.assertEqual(fixture.payload_reads, [])

    def test_wrong_guard_contract_precedes_core_or_payload_loading(self):
        scope = dict(contract=dict(path='old_guard', sha256='F'*64))
        metadata = SimpleNamespace(pinned=lambda *args: json.dumps(scope).encode())
        entry = SimpleNamespace(load_module=unittest.mock.Mock(return_value=metadata),
                                CONTRACT=('current_guard', 'A'*64))
        with self.assertRaisesRegex(ValueError, 'guard5'):
            reader.setup(Path('/tmp'), entry)
        self.assertEqual(entry.load_module.call_count, 1)

    def test_emission_keeps_frame_boundaries_and_explicit_batch_next_cursor(self):
        fixture = inherited.Fixture(b'x'*17000, b'x'*17000)
        context, views, pieces = self.run_batch(fixture)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            reader.emit(fixture.root, context, views, pieces)
        text = output.getvalue()
        self.assertEqual(text.count('TRUSTED_LOSSLESS_VIEW_V2 '), 3)
        end = json.loads(text.split('TRUSTED_LOSSLESS_BATCH_END ')[-1])
        self.assertEqual(end['next_part'], 4)
        self.assertEqual(end['payload_copies_written'], 0)
        self.assertFalse(end['semantic_review_complete'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
