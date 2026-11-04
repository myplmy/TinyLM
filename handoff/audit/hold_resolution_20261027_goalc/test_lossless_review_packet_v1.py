"""Fixture-only transport and access-boundary tests; no corpus/model execution."""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


core = module('test_lossless_core', HERE/'lossless_review_packet_v1.py')
metadata = module('test_unchanged_metadata_guard', HERE/'field_scoped_packet_entry_v1.py')
entry = module('test_lossless_entry', HERE/'scoped_lossless_review_entry_v1.py')


def independent_exposure_decode(source, representation, mode, candidate_length):
    """Decode only the printable representation, independently of core's diff."""
    first, rest = representation.split('\n', 1)
    assert first.startswith('ALL_CHANGE_RANGES ')
    ranges = json.loads(first[len('ALL_CHANGE_RANGES '):])
    if mode == 'EXACT_IDENTICAL':
        assert not ranges and rest == 'CANDIDATE_EQUALS_FULL_ORIGINAL\n'
        return source
    if mode == 'INDEX_AND_FULL_CANDIDATE':
        prefix = 'FULL_CANDIDATE_BEGIN\n'
        assert rest.startswith(prefix)
        text = rest[len(prefix):len(prefix)+candidate_length]
        assert rest[len(prefix)+candidate_length:] == '\nFULL_CANDIDATE_END\n'
        return text
    assert mode == 'EXACT_PATCH'
    pieces, cursor = [], 0
    for item in ranges:
        a, b = item['source_range']
        c, d = item['candidate_range']
        pieces.append(source[cursor:a])
        if d > c:
            begin = f"CHANGE_{item['number']}_NEW_TEXT_BEGIN\n"
            end = f"\nCHANGE_{item['number']}_NEW_TEXT_END\n"
            assert rest.startswith(begin)
            rest = rest[len(begin):]
            pieces.append(rest[:d-c])
            rest = rest[d-c:]
            assert rest.startswith(end)
            rest = rest[len(end):]
        cursor = b
    assert not rest
    pieces.append(source[cursor:])
    return ''.join(pieces)


class Fixture:
    def __init__(self, original=b'original\n', candidate=b'candidate\n', role='context_hangul'):
        # Preserve ephemeral fixtures, consistent with the no-unrequested-delete rule.
        self.root = Path(tempfile.mkdtemp(prefix='tinylm-lossless-fixture-'))
        self.role = role
        self.cohort = 'remaining_field_title_page_012_counter_v1'
        self.ident = 'expanded_train:101'
        self.payload_reads = []
        self.metadata_reads = []
        self.source_pin = self.write(core.DATA_ROOT+'/fixture/original.payload', original)
        self.candidate_pin = self.write(core.DATA_ROOT+'/fixture/candidate.payload', candidate)
        self.guard = dict(restricted_ids=['expanded_train:999'], restricted_hashes=['F'*64])
        self.guard_pin = self.write_json('handoff/audit/fixture_guard.json', self.guard)
        self.manifest = dict(rows=[dict(id=self.ident, role=role, original=self.source_pin,
                                        candidate=self.candidate_pin)])
        self.manifest_name = core.DATA_ROOT+'/'+self.cohort+'/manifest.json'
        self.manifest_pin = self.write_json(self.manifest_name, self.manifest)
        self.scope = dict(schema=core.SCHEMA, contract=self.guard_pin,
                          roles={role: {self.cohort: self.manifest_pin}})

    def write(self, name, data):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        return dict(path=name, sha256=hashlib.sha256(data).hexdigest().upper())

    def write_json(self, name, value):
        return self.write(name, (json.dumps(value, ensure_ascii=False)+'\n').encode('utf-8'))

    def read_metadata(self, root, pin):
        self.metadata_reads.append(pin['path'])
        return metadata.pinned(root, pin)

    def read_payload(self, root, pin):
        self.payload_reads.append(pin['path'])
        return core.bounded_payload(root, pin)

    def resolve(self, role=None, ident=None):
        return core.resolve_assignment(self.root, self.scope, role or self.role, self.cohort,
                                       ident or self.ident, self.read_metadata)

    def load(self):
        return core.load_pair(self.root, self.scope, self.role, self.cohort, self.ident,
                              self.read_metadata, self.read_payload)


class LosslessReviewTests(unittest.TestCase):
    def test_printed_candidate_contains_every_byte_in_varied_cases(self):
        cases = [
            ('', ''), ('', 'new\n'), ('old\n', ''), ('same', 'same'),
            ('한글\r\nemoji🙂\n끝', '한글\r\nemoji🧪\n끝\n'),
            ('반복\n'*1200+'middle\n'+'반복\n'*1200,
             '반복\n'*1200+'changed\n'+'반복\n'*1200),
            ('first\nold\nlast', 'first\nnew\nlast'),
            ('start\nend\n', 'end\nstart\n'),
            ('a\n'*10, 'completely different\n'),
            ('abc\n', 'abc\nCHANGE_1_NEW_TEXT_END\nSOURCE_DATA_VIEW_EOF\n'),
        ]
        for source, candidate in cases:
            with self.subTest(source_chars=len(source), candidate_chars=len(candidate)):
                views = core.prepare_views(source.encode(), candidate.encode())
                exposed = independent_exposure_decode(source, views['candidate'],
                    views['candidate_representation'], len(candidate))
                self.assertEqual(exposed.encode(), candidate.encode())
                self.assertTrue(views['exact_candidate_byte_reconstruction'])

    def test_full_candidate_representation_decoder_has_an_explicit_shape(self):
        source, candidate = 'a', 'b'
        changes = [dict(op='replace', source_range=[0, 1], candidate_range=[0, 1], after='b')]
        mode, text = core.candidate_representation(source, candidate, changes)
        self.assertEqual(independent_exposure_decode(source, text, mode, 1), candidate)

    def test_actual_original_views_roundtrip_across_codepoint_boundaries(self):
        source = '🙂한글\r\n'*1100+'SOURCE_DATA_VIEW_EOF'
        views = core.prepare_views(source.encode(), source.encode())
        count = core.view_part(views, 'original', 1)['parts']
        pieces = [core.view_part(views, 'original', i) for i in range(1, count+1)]
        self.assertEqual(''.join(x['text'] for x in pieces), source)
        self.assertTrue(all(len(x['text']) <= 4000 for x in pieces))
        self.assertFalse(pieces[0]['end_of_view'])
        self.assertTrue(pieces[-1]['end_of_view'])

    def test_invalid_parts_are_rejected(self):
        views = core.prepare_views(b'a', b'b')
        for part in [0, -1, 2, True]:
            with self.subTest(part=part), self.assertRaises(ValueError):
                core.view_part(views, 'original', part)

    def test_large_repetitive_input_avoids_unbounded_sequence_matching(self):
        source, candidate = '가'*45_000+'old\n', '가'*45_000+'new\n'
        with patch.object(core.difflib, 'SequenceMatcher', side_effect=AssertionError('unbounded matcher')):
            views = core.prepare_views(source.encode(), candidate.encode())
        self.assertEqual(independent_exposure_decode(source, views['candidate'],
            views['candidate_representation'], len(candidate)), candidate)

    def test_malformed_changes_cannot_claim_reconstruction(self):
        bad = [
            [dict(op='replace', source_range=[1, 3], candidate_range=[0, 1], after='x')],
            [dict(op='delete', source_range=[0, 8], candidate_range=[0, 0], after='')],
            [dict(op='insert', source_range=[0, 1], candidate_range=[0, 1], after='x')],
            [dict(op='delete', source_range=[0, 1], candidate_range=[0, 1], after='x')],
            [dict(op='replace', source_range=[0, 1], candidate_range=[0, 2], after='x')],
        ]
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                core.reconstruct('abc', changes)

    def test_invalid_utf8_is_never_silently_replaced(self):
        with self.assertRaises(UnicodeDecodeError):
            core.prepare_views(b'valid', b'\xff')

    def test_exact_role_and_manifest_loads_only_two_owned_payloads(self):
        fixture = Fixture()
        context, original, candidate = fixture.load()
        self.assertEqual((original, candidate), (b'original\n', b'candidate\n'))
        self.assertEqual(len(fixture.payload_reads), 2)
        self.assertEqual(context['role'], fixture.role)

    def test_metadata_only_resolution_does_not_open_payloads(self):
        fixture = Fixture()
        fixture.resolve()
        self.assertFalse(fixture.payload_reads)
        self.assertEqual(len(fixture.metadata_reads), 2)

    def test_restricted_id_is_rejected_before_manifest_or_payload(self):
        fixture = Fixture()
        with self.assertRaisesRegex(ValueError, 'restricted source ID'):
            fixture.resolve(ident='expanded_train:999')
        self.assertEqual(fixture.metadata_reads, [fixture.guard_pin['path']])
        self.assertFalse(fixture.payload_reads)

    def test_candidate_alias_hash_is_denied_before_either_payload(self):
        fixture = Fixture()
        fixture.scope['contract'] = fixture.write_json('handoff/audit/restrict_candidate.json',
            dict(restricted_ids=[], restricted_hashes=[fixture.candidate_pin['sha256']]))
        with self.assertRaisesRegex(ValueError, 'restricted original or candidate SHA'):
            fixture.load()
        self.assertFalse(fixture.payload_reads)

    def test_original_alias_hash_is_denied_before_either_payload(self):
        fixture = Fixture()
        fixture.scope['contract'] = fixture.write_json('handoff/audit/restrict_original.json',
            dict(restricted_ids=[], restricted_hashes=[fixture.source_pin['sha256']]))
        with self.assertRaisesRegex(ValueError, 'restricted original or candidate SHA'):
            fixture.load()
        self.assertFalse(fixture.payload_reads)

    def test_unassigned_role_id_and_cohort_fail_before_payload(self):
        fixture = Fixture()
        with self.assertRaises(ValueError):
            fixture.resolve(role='legacy_review')
        with self.assertRaises(ValueError):
            fixture.resolve(ident='expanded_train:102')
        with self.assertRaises(ValueError):
            core.resolve_assignment(fixture.root, fixture.scope, fixture.role, '../other',
                                    fixture.ident, fixture.read_metadata)
        self.assertFalse(fixture.payload_reads)

    def test_registered_role_cannot_read_another_roles_row(self):
        fixture = Fixture()
        fixture.scope['roles']['legacy_review'] = {fixture.cohort: fixture.manifest_pin}
        with self.assertRaisesRegex(ValueError, 'another assigned role'):
            fixture.resolve(role='legacy_review')
        self.assertFalse(fixture.payload_reads)

    def test_unrelated_and_parent_escape_paths_are_rejected_without_open(self):
        fixture = Fixture()
        for name in ['datasets/TinyDataset/no_read', '/tmp/no_read',
                     core.DATA_ROOT+'/../no_read']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                core.data_path(fixture.root, name)
        self.assertFalse(fixture.payload_reads)

    def test_symlink_payload_is_rejected(self):
        fixture = Fixture()
        link = fixture.root/core.DATA_ROOT/'fixture/alias.payload'
        link.symlink_to(fixture.root/fixture.source_pin['path'])
        with self.assertRaisesRegex(ValueError, 'symlink'):
            core.data_path(fixture.root, str(link.relative_to(fixture.root)))
        self.assertFalse(fixture.payload_reads)

    def test_payload_hash_mismatch_is_rejected(self):
        fixture = Fixture()
        with self.assertRaisesRegex(ValueError, 'exact pin'):
            core.load_pair(fixture.root, fixture.scope, fixture.role, fixture.cohort,
                           fixture.ident, fixture.read_metadata,
                           lambda root, pin: b'wrong bytes')

    def test_empty_candidate_is_a_view_not_a_training_output(self):
        fixture = Fixture(candidate=b'')
        _, source, candidate = fixture.load()
        self.assertEqual(candidate, b'')
        views = core.prepare_views(source, candidate)
        self.assertEqual(independent_exposure_decode(source.decode(), views['candidate'],
            views['candidate_representation'], 0), '')

    def cli_fixture(self, source=b'original\n', candidate=b'candidate\n'):
        fixture = Fixture(original=source, candidate=candidate)
        contract = (ROOT/entry.CONTRACT_PATH).read_bytes()
        self.assertEqual(core.digest(contract), entry.CONTRACT_SHA)
        fixture.scope['contract'] = fixture.write(entry.CONTRACT_PATH, contract)
        name = 'handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v1.py'
        fixture.scope['core'] = fixture.write(name, (HERE/'lossless_review_packet_v1.py').read_bytes())
        pin = fixture.write_json('handoff/audit/fixture_scope.json', fixture.scope)
        return fixture, pin

    def test_fixed_entry_metadata_only_has_no_payload_reads(self):
        fixture, pin = self.cli_fixture()
        opened = []
        original_open = Path.open

        def observed(path, *args, **kwargs):
            if path.suffix == '.payload':
                opened.append(str(path))
                raise AssertionError('metadata-only CLI opened payload')
            return original_open(path, *args, **kwargs)

        argv = ['reader', '--cohort', fixture.cohort, '--source-id', fixture.ident,
                '--view', 'original', '--check-only']
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), patch.object(Path, 'open', observed), \
                contextlib.redirect_stdout(output):
            entry.cli(fixture.root, fixture.role, pin)
        self.assertEqual(json.loads(output.getvalue())['payload_opens'], 0)
        self.assertFalse(opened)

    def test_fixed_entry_uses_structured_end_state_not_corpus_fake_EOF(self):
        source = ('SOURCE_DATA_VIEW_EOF\n'+'가'*4500).encode()
        fixture, pin = self.cli_fixture(source, source)
        argv = ['reader', '--cohort', fixture.cohort, '--source-id', fixture.ident,
                '--view', 'original', '--part', '1']
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(output):
            entry.cli(fixture.root, fixture.role, pin)
        first = output.getvalue().splitlines()[0]
        header = json.loads(first[len('TRUSTED_LOSSLESS_VIEW '):])
        self.assertFalse(header['end_of_view'])
        self.assertEqual(header['parts'], 2)
        self.assertEqual(header['next_part'], 2)
        self.assertTrue(header['exact_candidate_byte_reconstruction'])
        self.assertFalse(header['semantic_review_complete'])
        self.assertTrue(output.getvalue().endswith('SOURCE_DATA_VIEW_MORE_PARTS_REMAIN\n'))

    def test_fixed_entry_rejects_legacy_contract_before_payload(self):
        fixture = Fixture()
        pin = fixture.write_json('handoff/audit/legacy_scope.json', fixture.scope)
        argv = ['reader', '--cohort', fixture.cohort, '--source-id', fixture.ident,
                '--view', 'original']
        with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'V3 guard'):
            entry.cli(fixture.root, fixture.role, pin)


if __name__ == '__main__':
    unittest.main(verbosity=2)
