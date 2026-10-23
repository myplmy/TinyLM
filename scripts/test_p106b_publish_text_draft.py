"""Temporary synthetic text only; never publish any live author/source object."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_publish_text_draft as m
from scripts import p106b_source_cleanup as cleanup


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        folder = self.stack.enter_context(tempfile.TemporaryDirectory(prefix='text_publish_synthetic_'))
        self.temporary = Path(folder); self.root = self.temporary / 'repo'; self.root.mkdir()
        self.base = self.root / m.BASE_REL
        for name, value in ((m, self.root), (cleanup, self.root)):
            self.stack.enter_context(patch.object(name, 'ROOT', value))
        self.stack.enter_context(patch.object(m, 'BASE', self.base))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('noninteractive CLI only')))
        self.packet = self.base / 'packets/native_unit.json'; self.packet.parent.mkdir(parents=True)
        self.scratch = self.base / 'author_scratch/luna/input_unique.json'; self.scratch.parent.mkdir(parents=True)

    def write(self, path, value, *, raw=None):
        body = raw if raw is not None else (json.dumps(value, ensure_ascii=False, indent=3) + '  \n').encode('utf-8')
        path.write_bytes(body); return body

    def native(self, **overrides):
        text = '본문\n외부 링크\n'
        self.write(self.packet, dict(edit_contract=m.b.LINE_EDIT_CONTRACT,
            documents=[dict(id=7, eos_segment_index=7, text=text, sha256=m.b.sha(text))]))
        row = dict(id=7, decision='KEEP', changes=[], review_notes='합성 원형 보존')
        row.update(overrides); return row

    def sft(self):
        self.packet = self.base / 'packets/sft_unit.json'
        messages = [dict(role=r, content=c) for r, c in
            (('user', 'first question'), ('assistant', 'first answer'), ('user', 'correction'), ('assistant', 'new answer'))]
        source = dict(source_index=702, source_id='exact-sealed-uuid-702', root_id='R' * 64,
            source_line_sha256='A' * 64, source_split='train', messages=messages,
            meta=dict(source_id='exact-sealed-uuid-702', supervised_assistant_turns=[2]))
        self.write(self.packet, dict(sources=[source], required_variants=list(m.b.KINDS)))
        row = dict(source_index=702, triage_reason='', variants=[dict(kind=k, messages=copy.deepcopy(messages)) for k in m.b.KINDS])
        return source, row

    def call(self, row=None, *, raw=None, kind='native', scratch=None):
        scratch = scratch or self.scratch
        body = self.write(scratch, row, raw=raw)
        rc, receipt = m.publish(str(self.packet), str(scratch), kind)
        return rc, receipt, body

    def receipt_files(self): return sorted((self.base / 'publish_receipts').glob('*/receipt.json'))

    def assert_failure_receipt(self, result):
        rc, receipt, _ = result
        self.assertEqual(rc, 9); self.assertFalse(receipt['published_by_this_attempt'])
        self.assertEqual(receipt['status'], 'INCOMPLETE')
        log = self.root / receipt['attempt']
        self.assertEqual(json.loads((log / 'receipt.json').read_text()), receipt)
        self.assertTrue((log / 'request.json').is_file())
        return log

    def test_native_copy_is_exact_raw_bytes_and_final_path_is_code_owned(self):
        row = self.native(); packet_before = self.packet.read_bytes()
        rc, receipt, body = self.call(row)
        self.assertEqual(rc, 0); self.assertEqual(receipt['status'], 'PUBLISHED_COPY_ONLY_DRAFT')
        final = self.base / 'published/native_unit/7.json'
        self.assertEqual(final.read_bytes(), body); self.assertEqual(self.scratch.read_bytes(), body)
        self.assertEqual(self.packet.read_bytes(), packet_before)
        self.assertEqual(receipt['input_before'], receipt['input_after'])
        self.assertEqual(receipt['packet_before'], receipt['packet_after'])
        self.assertEqual(receipt['source_before'], receipt['source_after'])
        self.assertEqual(receipt['code_sha256_before'], receipt['code_sha256_after'])
        self.assertEqual(receipt['final_observation']['sha256'], m.bytes_sha(body))
        log = self.root / receipt['attempt']
        self.assertEqual((log / 'input.raw.json').read_bytes(), body)
        reference = receipt['packet_raw_reference']
        self.assertEqual((self.root / reference['path']).read_bytes(), packet_before)
        self.assertEqual((reference['sha256'], reference['bytes']), (m.bytes_sha(packet_before), len(packet_before)))
        self.assertFalse((log / 'packet.raw.json').exists())
        self.assertEqual(receipt['training_admission'], 'NOT_ADMITTED')
        self.assertEqual(receipt['language_truth'], 'NOT_VERIFIED')

    def test_relative_paths_are_accepted_only_inside_exact_scoped_locations(self):
        row = self.native(); body = self.write(self.scratch, row)
        rc, receipt = m.publish(str(self.packet.relative_to(self.root)), str(self.scratch.relative_to(self.root)), 'native')
        self.assertEqual(rc, 0); self.assertEqual((self.root / receipt['final']).read_bytes(), body)

    def test_packet_raw_is_shared_once_but_candidate_raw_remains_per_attempt(self):
        first = self.native(); packet = json.loads(self.packet.read_text())
        text = 'second source body\n'
        packet['documents'].append(dict(id=8, eos_segment_index=8, text=text, sha256=m.b.sha(text)))
        raw_packet = self.write(self.packet, packet)
        one = self.call(first); cache = self.root / one[1]['packet_raw_reference']['path']; before = cache.stat()
        second = self.call(dict(id=8, decision='HOLD', changes=[], review_notes='uncertain source'))
        self.assertEqual((one[0], second[0]), (0, 0))
        self.assertEqual(one[1]['packet_raw_reference'], second[1]['packet_raw_reference'])
        self.assertEqual(cache.read_bytes(), raw_packet)
        self.assertEqual((cache.stat().st_ino, cache.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
        self.assertEqual(len(list((self.base / 'publish_receipts/source_packets').glob('*.json'))), 1)
        for result in (one, second):
            log = self.root / result[1]['attempt']
            self.assertEqual((log / 'input.raw.json').read_bytes(), result[2])
            self.assertFalse((log / 'packet.raw.json').exists())

    def test_partial_or_mismatched_shared_packet_is_never_repaired(self):
        row = self.native(); raw = self.packet.read_bytes()
        cache = self.base / 'publish_receipts/source_packets' / (m.bytes_sha(raw) + '.json')
        cache.parent.mkdir(parents=True)
        for bad in (raw[:8], b'x' * len(raw)):
            cache.write_bytes(bad); before = cache.stat()
            self.assert_failure_receipt(self.call(row))
            self.assertEqual(cache.read_bytes(), bad)
            self.assertEqual((cache.stat().st_ino, cache.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
            self.assertFalse((self.base / 'published/native_unit/7.json').exists())

    def test_shared_packet_symlink_is_refused_without_reading_or_writing_target(self):
        row = self.native(); raw = self.packet.read_bytes(); outside = self.temporary / 'outside.json'
        outside.write_bytes(b'outside unchanged')
        cache = self.base / 'publish_receipts/source_packets' / (m.bytes_sha(raw) + '.json')
        cache.parent.mkdir(parents=True); cache.symlink_to(outside)
        self.assert_failure_receipt(self.call(row))
        self.assertTrue(cache.is_symlink()); self.assertEqual(outside.read_bytes(), b'outside unchanged')

    def test_simultaneous_first_archive_writes_exactly_one_complete_copy(self):
        self.native(); raw = self.packet.read_bytes(); barrier = threading.Barrier(2)
        actual_writes = []; write = m.exclusive_bytes
        def counted(parent, name, value):
            result = write(parent, name, value)
            if name == m.bytes_sha(raw) + '.json': actual_writes.append(name)
            return result
        def worker():
            barrier.wait(timeout=10); return m.archive_packet(raw)
        with patch.object(m, 'exclusive_bytes', side_effect=counted), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]; references = [f.result(timeout=20) for f in futures]
        self.assertEqual(references[0], references[1]); self.assertEqual(len(actual_writes), 1)
        self.assertEqual((self.root / references[0]['path']).read_bytes(), raw)

    def test_existing_final_is_preserved_even_for_identical_input(self):
        row = self.native(); first = self.call(row); final = self.root / first[1]['final']
        original = final.read_bytes(); before = final.stat()
        for notes in (row['review_notes'], 'different author notes'):
            other = dict(row, review_notes=notes); rc, receipt, _ = self.call(other)
            self.assertEqual(rc, 8); self.assertEqual(receipt['status'], 'ALREADY_EXISTS_NOT_A_COMPLETION_PROOF')
            self.assertFalse(receipt['published_by_this_attempt']); self.assertEqual(final.read_bytes(), original)
            self.assertEqual((final.stat().st_ino, final.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
        self.assertEqual(len(self.receipt_files()), 3)

    def test_wrong_native_id_bool_id_and_packet_duplicate_ids_are_rejected(self):
        for ident in (8, True, '7', -1):
            result = self.call(self.native(id=ident)); self.assert_failure_receipt(result)
        packet = json.loads(self.packet.read_text()); packet['documents'].append(packet['documents'][0])
        self.write(self.packet, packet); self.assert_failure_receipt(self.call(dict(id=7, decision='KEEP', changes=[])))

    def test_positioned_edits_reuse_the_existing_helper_without_rewriting_input(self):
        changes = [dict(source_lines=[2, 2], source_start='外부', source_end='링크', action='REMOVE', replacement='')]
        row = self.native(decision='REWRITE', changes=changes)
        bad = self.call(row); self.assert_failure_receipt(bad)
        row['changes'][0]['source_start'] = '외부'; row['proposed_text'] = '본문\n'
        with patch.object(m.b, 'apply_positioned_edits', wraps=m.b.apply_positioned_edits) as helper:
            rc, receipt, raw = self.call(row)
        self.assertEqual(rc, 0); self.assertGreaterEqual(helper.call_count, 2)
        self.assertEqual((self.root / receipt['final']).read_bytes(), raw)
        self.assertEqual(receipt['source_before']['reconstructed_text_sha256'], m.b.sha('본문\n'))

    def test_wrong_original_sha_span_bounds_overlap_and_hidden_changes_fail(self):
        variants = [dict(source_sha256='F' * 64), dict(proposed_text='undeclared replacement'),
            dict(decision='REWRITE', changes=[dict(source_lines=[99, 99], source_start='x', source_end='x', action='REMOVE', replacement='')]),
            dict(decision='REWRITE', changes=[dict(source_lines=[2, 2], source_start='외부', source_end='링크', action='REMOVE', replacement='', source_span_sha256='F' * 64)])]
        for change in variants: self.assert_failure_receipt(self.call(self.native(**change)))
        change = dict(source_lines=[2, 2], source_start='외부', source_end='링크', action='REMOVE', replacement='')
        self.assert_failure_receipt(self.call(self.native(decision='REWRITE', changes=[change, change])))

    def test_keep_and_hold_cannot_hide_a_source_edit(self):
        change = dict(source_lines=[2, 2], source_start='외부', source_end='링크', action='REMOVE', replacement='')
        for decision in ('KEEP', 'HOLD'):
            self.assert_failure_receipt(self.call(self.native(decision=decision, changes=[change])))

    def test_sft_source_index_only_is_sufficient_and_unchanged_language_is_not_certified(self):
        _, row = self.sft(); rc, receipt, raw = self.call(row, kind='sft')
        self.assertEqual(rc, 0); self.assertEqual(receipt['source_before']['authored_variant_count'], 3)
        self.assertEqual((self.base / 'published/sft_unit/702.json').read_bytes(), raw)
        self.assertNotIn('source_id', json.loads(raw)); self.assertNotIn('root_id', json.loads(raw))
        self.assertEqual(receipt['language_truth'], 'NOT_VERIFIED')

    def test_sft_wrong_provided_uuid_root_hash_split_or_variant_metadata_is_not_relabelled(self):
        source, row = self.sft()
        for field, value in (('source_id', 'typo-uuid-702'), ('root_id', 'wrong-root'),
                ('source_line_sha256', 'B' * 64), ('source_split', 'dev')):
            current = dict(row, **{field: value}); result = self.call(current, kind='sft')
            log = self.assert_failure_receipt(result)
            self.assertEqual(json.loads((log / 'input.raw.json').read_bytes())[field], value)
            self.assertEqual(self.scratch.read_bytes(), result[2])
        current = copy.deepcopy(row); current['variants'][0]['source_id'] = 'typo-uuid-702'
        self.assert_failure_receipt(self.call(current, kind='sft'))
        current = dict(row, source_id=source['source_id'], root_id=source['root_id'])
        self.assertEqual(self.call(current, kind='sft')[0], 0)

    def test_all_three_variants_and_source_turn_roles_are_required(self):
        _, row = self.sft(); variants = []
        current = copy.deepcopy(row); current['variants'].pop(); variants.append(current)
        current = copy.deepcopy(row); current['variants'][1]['kind'] = current['variants'][0]['kind']; variants.append(current)
        current = copy.deepcopy(row); current['variants'][0]['messages'] = current['variants'][0]['messages'][:2]; variants.append(current)
        current = copy.deepcopy(row); current['variants'][0]['messages'][0]['role'] = 'assistant'; variants.append(current)
        current = copy.deepcopy(row); current['variants'][0]['messages'][0]['content'] = ''; variants.append(current)
        current = copy.deepcopy(row); current['variants'][0]['requested_language'] = 'en'; variants.append(current)
        for current in variants: self.assert_failure_receipt(self.call(current, kind='sft'))

    def test_nested_supplied_metadata_does_not_treat_bool_as_integer(self):
        _, row = self.sft(); packet = json.loads(self.packet.read_text())
        packet['sources'][0]['meta']['count'] = 1; self.write(self.packet, packet)
        row['meta'] = copy.deepcopy(packet['sources'][0]['meta']); row['meta']['count'] = True
        self.assert_failure_receipt(self.call(row, kind='sft'))

    def test_triage_only_publication_is_not_authored_or_admitted(self):
        _, row = self.sft(); row.update(variants=[], triage_reason='source needs human review')
        rc, receipt, raw = self.call(row, kind='sft')
        self.assertEqual(rc, 0); self.assertEqual(receipt['source_before']['classification'], 'NOT_AUTHORED_TRIAGE_ONLY')
        self.assertEqual(receipt['source_before']['authored_variant_count'], 0)
        self.assertEqual(receipt['training_admission'], 'NOT_ADMITTED')
        self.assertEqual(json.loads(raw)['variants'], [])
        row['triage_reason'] = ''; self.assert_failure_receipt(self.call(row, kind='sft'))

    def test_duplicate_fields_nonfinite_invalid_utf8_and_arrays_preserve_raw_failure(self):
        self.native()
        for raw in (b'{"id":7,"id":7}', b'{"id":NaN}', b'\xff', b'[]',
                b'{"id":7,"decision":"KEEP","changes":[],"extra":{"x":1,"x":2}}'):
            result = self.call(raw=raw); log = self.assert_failure_receipt(result)
            self.assertEqual((log / 'input.raw.json').read_bytes(), raw)
            self.assertEqual(self.scratch.read_bytes(), raw)

    def test_invalid_scope_traversal_environment_and_other_worker_depth_are_rejected(self):
        row = self.native(); self.write(self.scratch, row)
        bad = [self.root / '.codex/input.json', self.root / 'datasets/TinyDataset/input.json',
            self.root / 'data_cache/other/input.json', self.base / 'author_scratch/luna/deep/file.json',
            self.base / 'author_scratch/luna/input_unique.txt', self.temporary / 'outside.json']
        for value in [*(str(x) for x in bad), str(self.base) + '/author_scratch/luna/../escape.json']:
            rc, receipt = m.publish(str(self.packet), value, 'native')
            self.assertEqual(rc, 9); self.assertFalse(receipt['published_by_this_attempt'])
        rc, _ = m.publish(str(self.base / 'packets/deep/packet.json'), str(self.scratch), 'native')
        self.assertEqual(rc, 9)

    def test_symlink_input_final_or_ancestor_cannot_redirect_reads_or_writes(self):
        row = self.native(); self.write(self.scratch, row)
        outside = self.temporary / 'outside'; outside.mkdir(); sentinel = outside / 'sentinel.json'
        sentinel.write_bytes(b'private unchanged')
        linked = self.scratch.with_name('linked.json'); linked.symlink_to(sentinel)
        self.assertEqual(m.publish(str(self.packet), str(linked), 'native')[0], 9)
        destination = self.base / 'published/native_unit'; destination.mkdir(parents=True)
        (destination / '7.json').symlink_to(sentinel)
        self.assertEqual(m.publish(str(self.packet), str(self.scratch), 'native')[0], 9)
        self.assertEqual(sentinel.read_bytes(), b'private unchanged')
        # A separate packet stem tests a linked publication parent, no unlink.
        second = self.base / 'packets/native_other.json'; self.write(second, json.loads(self.packet.read_text()))
        (self.base / 'published/native_other').symlink_to(outside, target_is_directory=True)
        self.assertEqual(m.publish(str(second), str(self.scratch), 'native')[0], 9)
        self.assertEqual({p.name for p in outside.iterdir()}, {'sentinel.json'})

    def test_hard_link_input_is_refused_without_touching_either_name(self):
        row = self.native(); raw = self.write(self.scratch, row)
        alias = self.scratch.with_name('other.json'); os.link(self.scratch, alias)
        self.assertEqual(m.publish(str(self.packet), str(self.scratch), 'native')[0], 9)
        self.assertEqual(alias.read_bytes(), raw); self.assertEqual(self.scratch.read_bytes(), raw)

    def test_size20mb_is_rejected_before_open_read_or_raw_copy(self):
        self.native()
        with self.scratch.open('wb') as stream: stream.truncate(m.LIMIT)
        original_open = m.os.open
        def guarded(name, flags, *args, **kwargs):
            if str(name) == self.scratch.name and not flags & os.O_DIRECTORY:
                raise AssertionError('oversized input must not be opened')
            return original_open(name, flags, *args, **kwargs)
        with patch.object(m.os, 'open', side_effect=guarded):
            rc, receipt = m.publish(str(self.packet), str(self.scratch), 'native')
        self.assertEqual(rc, 9); self.assertEqual(receipt['oversize_observation']['bytes'], m.LIMIT)
        log = self.root / receipt['attempt']; self.assertFalse((log / 'input.raw.json').exists())
        self.assertFalse((log / 'packet.raw.json').exists()); self.assertTrue((log / 'receipt.json').exists())
        self.assertEqual(self.scratch.stat().st_size, m.LIMIT)

    def test_concurrent_creators_have_exactly_one_winner_and_no_overwrite(self):
        first = self.native(review_notes='first'); self.write(self.scratch, first)
        other = self.scratch.with_name('second_unique.json'); second = dict(first, review_notes='second'); self.write(other, second)
        barrier = threading.Barrier(2); write = m.exclusive_bytes
        def racing(parent, name, raw):
            if name == '7.json': barrier.wait(timeout=10)
            return write(parent, name, raw)
        with patch.object(m, 'exclusive_bytes', side_effect=racing), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(m.publish, str(self.packet), str(path), 'native') for path in (self.scratch, other)]
            results = [f.result(timeout=20) for f in futures]
        self.assertEqual(sorted(code for code, _ in results), [0, 8]); self.assertEqual(len(self.receipt_files()), 2)
        final = self.base / 'published/native_unit/7.json'; raw = final.read_bytes()
        self.assertIn(raw, (self.scratch.read_bytes(), other.read_bytes()))
        winner = next(r for code, r in results if code == 0)
        self.assertEqual(m.bytes_sha(raw), winner['final_observation']['sha256'])

    def test_partial_final_failure_preserves_tombstone_and_never_turns_into_success(self):
        row = self.native(); write = m.exclusive_bytes
        def failing(parent, name, raw):
            if name == '7.json':
                write(parent, name, raw[:8]); raise OSError('synthetic crash after partial final')
            return write(parent, name, raw)
        with patch.object(m, 'exclusive_bytes', side_effect=failing): result = self.call(row)
        self.assert_failure_receipt(result); final = self.base / 'published/native_unit/7.json'
        self.assertEqual(final.read_bytes(), result[2][:8])
        again = self.call(row); self.assertEqual(again[0], 8)
        self.assertFalse(again[1]['published_by_this_attempt']); self.assertEqual(final.read_bytes(), result[2][:8])

    def test_input_or_packet_mutation_during_validation_fails_before_final_creation(self):
        row = self.native(); validation = m.validate
        def changing(packet, draft, kind):
            result = validation(packet, draft, kind)
            self.packet.write_bytes(self.packet.read_bytes() + b' '); return result
        with patch.object(m, 'validate', side_effect=changing): result = self.call(row)
        self.assert_failure_receipt(result); self.assertFalse((self.base / 'published/native_unit/7.json').exists())
        self.assertNotEqual(result[1]['packet_before'], result[1]['packet_after'])

    def test_receipt_failure_is_not_success_and_keeps_raw_final_and_pending_evidence(self):
        row = self.native(); write = m.exclusive_bytes
        def failing(parent, name, raw):
            if name == 'receipt.pending.json':
                write(parent, name, raw[:30]); raise OSError('synthetic receipt interruption')
            return write(parent, name, raw)
        with patch.object(m, 'exclusive_bytes', side_effect=failing): rc, receipt, raw = self.call(row)
        self.assertEqual(rc, 9); self.assertEqual(receipt['status'], 'INCOMPLETE_RECEIPT_UNAVAILABLE')
        self.assertFalse(receipt['published_by_this_attempt']); self.assertFalse(self.receipt_files())
        self.assertEqual((self.base / 'published/native_unit/7.json').read_bytes(), raw)
        self.assertTrue(list((self.base / 'publish_receipts').glob('*/receipt.pending.json')))

    def test_invalid_kind_and_missing_arguments_get_failure_receipts(self):
        for kind in ('other', None):
            rc, receipt = m.publish(None, None, kind)
            self.assertEqual(rc, 9); self.assertEqual(receipt['status'], 'INCOMPLETE')
            self.assertTrue((self.root / receipt['attempt'] / 'receipt.json').exists())

    def test_invalid_cli_options_are_logged_without_honoring_a_final_path(self):
        arbitrary = self.temporary / 'must_not_be_written.json'
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--final', str(arbitrary)]), 9)
        self.assertFalse(arbitrary.exists())
        receipt = json.loads(self.receipt_files()[0].read_text())
        self.assertEqual(receipt['command_argv'], ['--final', str(arbitrary)])
        self.assertFalse(receipt['published_by_this_attempt'])


class CodeOnlyTests(unittest.TestCase):
    def test_check_only_opens_no_assets_and_writes_nothing(self):
        with patch.object(m, 'publish', side_effect=AssertionError('no publish')), \
                patch.object(m, 'read_owned', side_effect=AssertionError('no assets')), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main(['--check-only']), 0)
        value = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertEqual((value['asset_reads'], value['writes'], value['torch_imports']), (0, 0, 0))

    def test_malformed_check_only_is_also_strictly_read_only(self):
        with patch.object(m, 'publish', side_effect=AssertionError('no attempt or writes')), redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--check-only', '--final', '/tmp/not-owned.json']), 2)

    def test_direct_script_import_and_check_only_forbid_ml_framework_imports(self):
        script = ROOT / 'scripts/p106b_publish_text_draft.py'
        program = """import builtins,runpy,sys
previous=builtins.__import__
def checked(name,*args,**kwargs):
    if name.split('.')[0] in ('torch','tokenizers','numpy','tinylm'):
        raise AssertionError('forbidden model/data framework import: '+name)
    return previous(name,*args,**kwargs)
builtins.__import__=checked
sys.argv=[sys.argv[1],'--check-only']
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', program, str(script)],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__': unittest.main()
