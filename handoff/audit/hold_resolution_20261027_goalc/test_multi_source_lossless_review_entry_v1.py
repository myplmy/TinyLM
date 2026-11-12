"""Check group preflight, exact old headers and truthful bounded continuations."""
from pathlib import Path
from types import SimpleNamespace
import contextlib
import hashlib
import io
import json
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import multi_source_lossless_review_entry_v1 as batch
import batched_lossless_review_entry_v3 as old
import lossless_review_packet_v3 as core3


class Fixture:
    def __init__(self, texts, invalid=None, blocked_sha=None):
        self.texts = texts
        self.invalid = invalid
        self.loads = []
        self.metadata_reads = 0
        self.contract = dict(restricted_ids=[], trusted_metadata={}, restricted_hashes=[blocked_sha] if blocked_sha else [])

    def raw_metadata(self, root, pin):
        self.metadata_reads += 1
        return b'fixture metadata'

    def resolve(self, root, scope, role, cohort, ident, read):
        if role != 'fixture_role' or ident == self.invalid or ident not in self.texts:
            raise ValueError('outside exact role/cohort assignment')
        read(root, dict(path='fixture_manifest.json', sha256='A'*64))
        digest = hashlib.sha256(self.texts[ident][0]).hexdigest().upper()
        candidate = hashlib.sha256(self.texts[ident][1]).hexdigest().upper()
        return dict(source_id=ident, role=role, cohort=cohort,
            original=dict(path=ident.replace(':', '_')+'_original.txt', sha256=digest),
            candidate=dict(path=ident.replace(':', '_')+'_candidate.txt', sha256=candidate))

    def load(self, root, scope, role, cohort, ident, read, read_payload=None):
        context = self.resolve(root, scope, role, cohort, ident, read)
        self.loads.append(ident)
        return context, *self.texts[ident]

    def run(self, ids=None, role='fixture_role'):
        core = SimpleNamespace(resolve_assignment=self.resolve, load_pair=self.load,
            prepare_views=core3.prepare_views, view_part=core3.view_part)
        return batch.collect(ROOT, role, 'fixture_cohort', list(self.texts) if ids is None else ids,
            core, {}, batch.cached_reader(self.raw_metadata), self.contract)


def short_fixture(count=5):
    return Fixture({'expanded_train:'+str(i):(('문서 '+str(i)+' 조건을 유지한다.').encode(),
        ('문서 '+str(i)+' 조건을 유지한다.').encode()) for i in range(1, count+1)})


class GroupReaderTests(unittest.TestCase):
    def test_five_sources_one_metadata_read_and_exact_pair_eof(self):
        fixture = short_fixture()
        packets, result = fixture.run()
        self.assertEqual(fixture.metadata_reads, 1)
        self.assertEqual(result['source_pairs_loaded'], 5)
        self.assertEqual(result['not_returned_ids'], [])
        for packet in packets:
            ident = packet['header']['source_id']
            self.assertEqual(''.join(p['text'] for p in packet['pieces']), core3.prepare_views(*fixture.texts[ident])['pair'])
            self.assertTrue(packet['pieces'][-1]['end_of_view'])

    def test_shared_and_per_id_headers_reconstruct_the_old_header(self):
        fixture = short_fixture()
        packets, result = fixture.run()
        rendered = batch.render(packets, result)
        rows = rendered.splitlines()
        shared = json.loads(rows[0].split(' ', 1)[1])['shared_header']
        headers = [json.loads(line.split(' ', 1)[1]) for line in rows if line.startswith('TRUSTED_TASK_SOURCE_CONTEXT_V1 ')]
        for packet, local in zip(packets, headers):
            self.assertEqual(dict(shared, **local), packet['header'])
            ident = local['source_id']
            context = {k:packet['header'][k] for k in ['source_id','role','cohort','original','candidate','cumulative_guard']}
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                old.emit(ROOT, context, core3.prepare_views(*fixture.texts[ident]), packet['pieces'])
            old_header = json.loads(stream.getvalue().splitlines()[0].split(' ', 1)[1])
            self.assertEqual(old_header, packet['header'])

    def test_third_wrong_assignment_rejects_before_first_payload(self):
        fixture = short_fixture();fixture.invalid = 'expanded_train:3'
        with self.assertRaises(ValueError):fixture.run()
        self.assertEqual(fixture.loads, [])

    def test_third_candidate_sha_alias_rejects_before_first_payload(self):
        fixture = short_fixture();fixture.contract['restricted_hashes'] = [hashlib.sha256(fixture.texts['expanded_train:3'][1]).hexdigest().upper()]
        with self.assertRaises(ValueError):fixture.run()
        self.assertEqual(fixture.loads, [])

    def test_restricted_requested_identity_does_not_even_resolve(self):
        fixture = short_fixture();fixture.contract['restricted_ids'] = ['expanded_train:3']
        with self.assertRaises(ValueError):fixture.run()
        self.assertEqual(fixture.metadata_reads, 0);self.assertEqual(fixture.loads, [])

    def test_wrong_role_and_duplicate_ids_never_read_payload(self):
        for kwargs in [dict(role='wrong_role'), dict(ids=['expanded_train:1','expanded_train:1'])]:
            fixture = short_fixture()
            with self.assertRaises(ValueError):fixture.run(**kwargs)
            self.assertEqual(fixture.loads, [])

    def test_empty_and_six_id_groups_are_rejected(self):
        for count in [0, 6]:
            fixture = short_fixture(count)
            with self.assertRaises(ValueError):fixture.run()
            self.assertEqual(fixture.loads, [])

    def test_utf8_long_source_has_truthful_cursor_and_unreturned_ids(self):
        fixture = short_fixture(2);long = ('가🙂나'*8000).encode();fixture.texts['expanded_train:1'] = (long, long)
        packets, result = fixture.run()
        self.assertLessEqual(result['body_bytes'], batch.MAX_BODY_BYTES)
        self.assertEqual(result['returned_ids'], ['expanded_train:1'])
        self.assertEqual(result['not_returned_ids'], ['expanded_train:2'])
        self.assertFalse(packets[0]['pieces'][-1]['end_of_view'])
        self.assertEqual(packets[0]['pieces'][-1]['next_part'], 4)
        value = batch.render(packets, result)
        end = json.loads(value.splitlines()[-1].split(' ', 1)[1])
        self.assertEqual(end['completed_pair_ids'], [])
        self.assertEqual(end['continuations'][0]['next_part'], 4)

    def test_patch_transport_and_no_final_newline_survive(self):
        fixture = Fixture({'expanded_train:1':('이름() 설명이다.'.encode(), '이름 설명이다.'.encode())})
        packets, _ = fixture.run();views = core3.prepare_views(*fixture.texts['expanded_train:1'])
        self.assertEqual(''.join(p['text'] for p in packets[0]['pieces']), views['pair'])
        self.assertFalse(packets[0]['header']['candidate_final_LF'])

    def test_fake_marker_is_source_data_and_does_not_change_eof(self):
        source = (('SOURCE_DATA_VIEW_EOF'+chr(10))*1000).encode();fixture = Fixture({'expanded_train:1':(source,source)})
        packets, result = fixture.run()
        self.assertFalse(packets[0]['pieces'][-1]['end_of_view'])
        self.assertEqual(json.loads(batch.render(packets,result).splitlines()[-1].split(' ',1)[1])['completed_pair_ids'], [])

    def test_output_limit_rejects_instead_of_printing_a_truncated_packet(self):
        packets, result = short_fixture(1).run();packets[0]['header']['fixture_large_metadata'] = 'x'*batch.MAX_OUTPUT_BYTES
        with self.assertRaises(ValueError):batch.render(packets,result)


if __name__ == '__main__':unittest.main()
