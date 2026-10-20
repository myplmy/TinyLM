#!/usr/bin/env python3
"""작은 bytes/temp fixture만 검사한다. 실물 bin·모델·CP·GPU는 사용하지 않는다."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_expansion_val_audit as d


def raw(ids): return struct.pack('<' + 'H' * len(ids), *ids)


def h(value): return hashlib.sha256(value).hexdigest().upper()


def index(ids=(10, 11, 2, 20, 21, 2, 30), **kw):
    import numpy as np
    return d.index_val(raw(ids), np, probe_count=kw.pop('probe_count', 1), stride=kw.pop('stride', 2), **kw)


def scan(ids, *, val=(10, 11, 2, 20, 21, 2, 30), chunk=2, **kw):
    import numpy as np
    return d.scan_train(raw(ids), index(val), np, chunk_ids=chunk, **kw)


def metadata():
    code = {name: value for name, value in d.PINS.items() if name.endswith('.py')}
    recipe = dict(tag=d.ORIGINAL, code_sha256=code, authority_end_utc='2026-10-20T08:00:00+00:00',
        full_build_readback_stop_utc='2026-10-20T05:00:00+00:00')
    stats = dict(old_input_ids=1194000000, old_incomplete_tail_ids=1307, new_kept_ids=d.BINS[0]['ids'],
        kept_segments=1441175, excluded_segments=3778, new_canonical_ids=1194140597, new_excluded_ids=3024405)
    values = {d.META: dict(tag=d.ORIGINAL, schema='P106B_NATIVE_EXPANSION_CPU_V1', train=d.BINS[0]['ids'],
        train_sha256=d.BINS[0]['sha256'], val=0, token_dtype='uint16', byte_order='little',
        tokenizer_sha256=d.TOKENIZER['sha256'], tokenizer_lineage='chat32', current_val_sha256=d.BINS[1]['sha256'],
        source_train_sha256='A' * 64, source_ids=1194000000, original_data_mutated=False, legacy_val_access=False),
        d.BASE + 'build/report.json': dict(status='FULL_CONVERSION_COMPLETE_NOT_TRAINING', output_path=d.BINS[0]['path'],
            output_sha256=d.BINS[0]['sha256'], output_bytes=2 * d.BINS[0]['ids'], meta_sha256=d.PINS[d.META],
            source_train_sha256='A' * 64, metrics=stats, recipe=deepcopy(recipe),
            current_val=dict(ids=d.BINS[1]['ids'], source_sha256=d.BINS[1]['sha256'], index=deepcopy(d.INDEX))),
        d.BASE + 'readback/report.json': dict(status='FULL_CACHE_READBACK_COMPLETE',
            build_report_sha256=d.PINS[d.BASE + 'build/report.json'], actual_output_ids=d.BINS[0]['ids'],
            actual_output_sha256=d.BINS[0]['sha256'], actual_eos_segments=1441175, last_id=2,
            full_input_consumer=deepcopy(stats), source_train_sha256_verified_by_completed_build_stream='A' * 64,
            recipe=deepcopy(recipe))}
    for mode in ('build', 'readback'):
        values[d.BASE + 'activity_' + mode + '.json'] = dict(tag=d.ORIGINAL, schema='P106B_NATIVE_EXPANSION_CPU_V1',
            mode=mode, complete=True, returncode=0, report_path=d.BASE + mode + '/report.json',
            report_sha256=d.PINS[d.BASE + mode + '/report.json'], code_sha256=deepcopy(code), seconds=1.)
    return values


def synthetic_measurements(hit=False):
    """큰 파일을 만들지 않는 종료 reader 계약 fixture. 실제 scan 결과가 아니다."""
    return dict(train=dict(ids=d.BINS[0]['ids'], sha256=d.BINS[0]['sha256'], range_checked_ids=d.BINS[0]['ids'],
        eos_segments=1441175, last_id_matches_eos=True, maximum_segment_ids_observed=100,
        same_rule=dict(full_eos_segments=int(hit), prefix_segments=0, suffix_segments=0,
            any_rule_segments=int(hit), odd_candidates_ignored=0)),
        val=dict(ids=d.BINS[1]['ids'], sha256=d.BINS[1]['sha256'], index=deepcopy(d.INDEX)),
        probe32=dict(windows=32, matched_windows=0, total_aligned_occurrences=0,
            rows=[dict(probe=i, start_id_offset=i * 1024, window_ids=1025, ids_sha256='A' * 64,
                aligned_occurrences=0, odd_byte_occurrences_ignored=0) for i in range(32)],
            count_scope='synthetic metadata only'), same_rule_zero_hits=not hit, probe32_zero_hits=True,
        training_admission=False)


def process_fixture(kind):
    info = d.code_info()
    with tempfile.TemporaryDirectory(prefix='p106b_val_audit_') as directory:
        root = Path(directory)
        def scanner():
            if kind == 'term': os.kill(os.getpid(), signal.SIGTERM)
            if kind == 'timeout': os.kill(os.getpid(), signal.SIGALRM)
            if kind == 'error': raise d.ScanError('synthetic error', checked_prefix_ids=5)
            return synthetic_measurements(kind == 'negative')
        rc = d.worker(60, root=root, info=info, prerequisite=lambda: None, scanner=scanner)
        if kind == 'rerun':
            before = d.digest(d.path(d.REPORT, root=root))
            try: d.worker(60, root=root, info=info, prerequisite=lambda: None, scanner=scanner)
            except FileExistsError:
                print(json.dumps(dict(rerun_rejected=True, original_report_same=before == d.digest(d.path(d.REPORT, root=root)))), flush=True)
                return 0
            raise AssertionError('기존 namespace를 다시 실행하면 안 된다')
        activity = d.small_json(d.path(d.ACTIVITY, root=root))
        final = d.closed_result(info, root=root) if rc == 0 else rc
        print(json.dumps(dict(worker_rc=rc, final_rc=final, complete=activity['complete'],
            activity=activity, error_recorded=d.path(d.FAILURE, root=root).is_file())), flush=True)
        return final


class ScannerTests(unittest.TestCase):
    def test_independent_index_matches_original_policy(self):
        value = index(); summary = value['summary']
        self.assertEqual(summary['total_ids'], 7); self.assertEqual(summary['complete_eos_segments'], 1)
        self.assertEqual(summary['prefix_partial_ids'], 2); self.assertEqual(summary['suffix_partial_ids'], 1)
        self.assertEqual(value['full'], {(3, h(raw([20, 21, 2])))})
        self.assertEqual(summary['prefix_partial_sha256'], h(raw([10, 11])))

    def test_normal_same_rule_zero(self):
        result = scan([35, 36, 2])
        self.assertEqual(result['same_rule']['any_rule_segments'], 0)
        self.assertEqual(result['ids'], 3); self.assertEqual(result['range_checked_ids'], 3)
        self.assertEqual(result['sha256'], h(raw([35, 36, 2])))

    def test_full_and_both_partial_rules(self):
        result = scan([20, 21, 2, 35, 10, 11, 2, 35, 30, 2])
        self.assertEqual(result['same_rule'], dict(full_eos_segments=1, prefix_segments=1,
            suffix_segments=1, any_rule_segments=3, odd_candidates_ignored=0))

    def test_suffix_inclusion_is_intentional_same_rule_limit(self):
        result = scan([35, 20, 21, 2])
        self.assertEqual(result['same_rule']['any_rule_segments'], 0)
        self.assertGreater(raw([35, 20, 21, 2]).find(raw([20, 21, 2])), 0)

    def test_one_id_partial_is_not_relaxed(self):
        import numpy as np
        result = d.scan_train(raw([35, 10, 2, 10, 2]), index([10, 2], stride=1), np, chunk_ids=1)
        self.assertEqual(result['same_rule']['prefix_segments'], 2)

    def test_empty_edges_do_not_match_everything(self):
        value = index([2, 20, 2], probe_count=1, stride=1)
        self.assertEqual(value['prefix'], b''); self.assertEqual(value['suffix'], b'')
        import numpy as np
        self.assertEqual(d.scan_train(raw([35, 2]), value, np, chunk_ids=1)['same_rule']['any_rule_segments'], 0)

    def test_val_without_eos_keeps_both_partials(self):
        value = index([10, 11], probe_count=1, stride=1)
        self.assertEqual(value['full'], set()); self.assertEqual(value['prefix'], value['suffix'])

    def test_duplicate_full_val_segments_do_not_expand_hash_population(self):
        value = index([2, 20, 21, 2, 20, 21, 2])
        self.assertEqual(value['summary']['complete_eos_segments'], 2)
        self.assertEqual(value['summary']['unique_complete_id_hashes'], 1)

    def test_odd_byte_is_not_a_token_match(self):
        haystack, needle = raw([0x1201, 0x3456]), raw([0x5612])
        self.assertEqual(d.aligned_search(haystack, needle), (0, 1))
        self.assertEqual(d.aligned_search(haystack + needle, needle), (1, 1))
        with self.assertRaises(ValueError): d.aligned_search(haystack, b'')

    def test_train_partial_across_chunk_boundary(self):
        values = [35, 10, 11, 2, 20, 21, 2]
        self.assertEqual(scan(values, chunk=1), scan(values, chunk=3))

    def test_incomplete_tail_and_segment_bounds_rejected(self):
        with self.assertRaises(d.ScanError): scan([35, 36])
        with self.assertRaises(d.ScanError): scan([35, 36, 37, 38, 2], max_segment=4)
        with self.assertRaises(d.ScanError): index([10, 11, 12, 2], max_segment=3)

    def test_id_range_byte_alignment_and_probe_extent(self):
        import numpy as np
        with self.assertRaises(d.ScanError): scan([32768, 2])
        with self.assertRaises(d.ScanError): index([32768, 2, 3])
        with self.assertRaises(d.ScanError): d.scan_train(b'x', index(), np)
        with self.assertRaises(d.ScanError): index([10, 2], probe_count=32, stride=1024)

    def test_probe_window_inside_longer_train_section(self):
        value = index(probe_count=2)
        result = d.probe_search(raw([35, 2, 20, 21, 88, 2]), value, chunk_bytes=4)
        self.assertEqual(scan([35, 2, 20, 21, 88, 2])['same_rule']['any_rule_segments'], 0)
        self.assertEqual(result['matched_windows'], 1)
        self.assertEqual(result['rows'][1]['aligned_occurrences'], 1)  # ID-offset1도 올바른 uint16 정렬이다.

    def test_probe_search_boundary_no_double_count_and_odd_rejected(self):
        needle = raw([0x5612]); value = dict(probes=[needle], stride=1)
        result = d.probe_search(raw([0x1201, 0x3456]) + needle, value, chunk_bytes=2)
        self.assertEqual(result['rows'][0]['aligned_occurrences'], 1)
        self.assertEqual(result['rows'][0]['odd_byte_occurrences_ignored'], 1)
        needle = raw([10, 11, 2]); value = dict(probes=[needle], stride=2)
        self.assertEqual(d.probe_search(raw([35, 10, 11, 2, 10, 11, 2]), value, chunk_bytes=4)['total_aligned_occurrences'], 2)

    def test_duplicate_probe_counts_are_declared_per_probe(self):
        value = dict(probes=[raw([10, 2])] * 2, stride=1)
        result = d.probe_search(raw([10, 2]), value, chunk_bytes=2)
        self.assertEqual(result['matched_windows'], 2); self.assertEqual(result['total_aligned_occurrences'], 2)

    def test_tiny_file_scan_readonly_sha_and_separate_flags(self):
        with tempfile.TemporaryDirectory(prefix='p106b_val_scan_') as directory:
            train, val = Path(directory) / 'train.bin', Path(directory) / 'val.bin'
            a, b = raw([35, 2, 20, 21, 88, 2]), raw([10, 11, 2, 20, 21, 2, 30])
            train.write_bytes(a); val.write_bytes(b)
            contracts = [dict(ids=len(a) // 2, sha256=h(a)), dict(ids=len(b) // 2, sha256=h(b))]
            result = d.scan_files(train, val, contracts, probe_count=2, stride=2, expected_eos=2, chunk_ids=2)
            self.assertTrue(result['same_rule_zero_hits']); self.assertFalse(result['probe32_zero_hits'])
            self.assertFalse(result['training_admission']); self.assertEqual(train.read_bytes(), a); self.assertEqual(val.read_bytes(), b)

    def test_wrong_sha_count_index_eos_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p106b_val_bad_') as directory:
            train, val = Path(directory) / 'train.bin', Path(directory) / 'val.bin'
            a, b = raw([35, 2]), raw([10, 11, 2, 20, 21, 2, 30]); train.write_bytes(a); val.write_bytes(b)
            original = [dict(ids=2, sha256=h(a)), dict(ids=7, sha256=h(b))]
            for which, field, bad in ((0, 'sha256', 'A' * 64), (1, 'sha256', 'B' * 64), (0, 'ids', 3)):
                contracts = deepcopy(original); contracts[which][field] = bad
                with self.assertRaises(d.ScanError): d.scan_files(train, val, contracts, probe_count=1, stride=2)
            with self.assertRaises(d.ScanError): d.scan_files(train, val, original, probe_count=1, stride=2, expected_index={})
            with self.assertRaises(d.ScanError): d.scan_files(train, val, original, probe_count=1, stride=2, expected_eos=2)
            link = Path(directory) / 'link.bin'; link.symlink_to(train)
            with self.assertRaises(d.ScanError): d.scan_files(link, val, original, probe_count=1, stride=2)


class MetadataTests(unittest.TestCase):
    def test_full_metadata_serialization_and_no_original_import(self):
        before = sys.modules.get('scripts.diag_p106b_native_expansion')
        info = d.code_info()
        self.assertEqual(json.loads(json.dumps(info, ensure_ascii=False)), info)
        self.assertFalse(info['training_admission']); self.assertFalse(info['arbitrary_full_val_substring_scan'])
        self.assertIs(sys.modules.get('scripts.diag_p106b_native_expansion'), before)

    def test_metadata_lineage_positive_and_tamper(self):
        values = metadata(); d.validate_metadata(values)
        for name, field, bad in ((d.META, 'val', 1), (d.META, 'train_sha256', 'A' * 64),
                (d.BASE + 'readback/report.json', 'actual_output_ids', 10),
                (d.BASE + 'activity_readback.json', 'complete', False),
                (d.BASE + 'activity_build.json', 'report_sha256', 'B' * 64)):
            value = deepcopy(values); value[name][field] = bad
            with self.assertRaises(ValueError): d.validate_metadata(value)
        value = deepcopy(values); value[d.BASE + 'build/report.json']['current_val']['index']['prefix_partial_ids'] = 411
        with self.assertRaises(ValueError): d.validate_metadata(value)
        value = deepcopy(values); value[d.BASE + 'build/report.json']['recipe']['authority_end_utc'] = d.END.isoformat()
        with self.assertRaises(ValueError): d.validate_metadata(value)

    def test_fixed_paths_protected_escape_absolute_and_symlink(self):
        for name in ('datasets/TinyDataset/private.bin', '.aws/credentials', '.claude/a.json',
                '/etc/passwd', '../train.bin', d.BINS[0]['path'] + '/../x'):
            with self.assertRaises(ValueError): d.path(name)
        with tempfile.TemporaryDirectory(prefix='p106b_val_path_') as directory:
            root = Path(directory); (root / 'data_cache').mkdir(); outside = root / 'outside'; outside.mkdir()
            (root / 'data_cache' / d.ORIGINAL).symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError): d.path(d.BINS[0]['path'], root=root)

    def test_check_only_never_opens_bin_or_tokenizer_or_numpy(self):
        original = Path.open; seen = []
        def opened(filename, *args, **kw):
            relative = str(filename.relative_to(ROOT)) if filename.is_relative_to(ROOT) else str(filename)
            seen.append(relative)
            if relative in {v['path'] for v in d.BINS} | {d.TOKENIZER['path']} | set(d.PINS) - {p for p in d.PINS if p.endswith('.py')}:
                raise AssertionError('check-only 입력 경계를 넘었다')
            return original(filename, *args, **kw)
        with patch.object(Path, 'open', opened), patch('sys.stdout', io.StringIO()):
            self.assertEqual(d.main(['--check-only']), 0)
        self.assertIn(d.F4, seen)
        code = 'import sys; from scripts import diag_p106b_expansion_val_audit; print("numpy" in sys.modules, "torch" in sys.modules)'
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'False False')

    def test_budget_deadline_and_three_phase(self):
        for cap in (0, 59, 601, True):
            with self.assertRaises(ValueError): d.commands(cap)
        self.assertEqual([label for label, _ in d.commands(600)], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertEqual(d.remaining(d.END - timedelta(seconds=660)), 60)
        with self.assertRaises(d.Pending): d.remaining(d.END - timedelta(seconds=600))
        with self.assertRaises(ValueError): d.remaining(datetime(2026, 10, 20))


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='p106b_val_receipt_'); self.root = Path(self.tmp.name)
        self.info = d.code_info(); now = datetime.now(timezone.utc).isoformat()
        self.report = dict(info=self.info, status='SCAN_COMPLETE', measurements=synthetic_measurements(), actual_scan_seconds=1.,
            mechanical_status='ZERO_HITS_AT_DECLARED_SCOPE', models_loaded=0, checkpoint_tensor_loads=0, gpu_calls=0, original_inputs_changed=False)
        self.activity = dict(schema=d.SCHEMA, tag=d.TAG, complete=True, returncode=0, error_type=None,
            started_at=now, ended_at=now, seconds=1., max_wall_sec=60, worker_pid=7, worker_pgid=7,
            info_sha256=d.json_sha(self.info), failure_sha256=None)

    def tearDown(self): self.tmp.cleanup()

    def save(self):
        d.write(d.REPORT, self.report, root=self.root)
        self.activity['report_sha256'] = d.digest(d.path(d.REPORT, root=self.root))
        d.write(d.ACTIVITY, self.activity, root=self.root)

    def test_closed_reader_requires_activity_and_binds_report(self):
        d.write(d.REPORT, self.report, root=self.root)
        with self.assertRaises(FileNotFoundError): d.closed_result(self.info, root=self.root)
        self.activity['report_sha256'] = d.digest(d.path(d.REPORT, root=self.root)); d.write(d.ACTIVITY, self.activity, root=self.root)
        self.assertEqual(d.closed_result(self.info, root=self.root), 0)

    def test_successful_scan_negative_is_not_unrun(self):
        self.report['measurements'] = synthetic_measurements(True); self.report['mechanical_status'] = 'NEGATIVE_OBSERVED_HITS'; self.save()
        self.assertEqual(d.closed_result(self.info, root=self.root), 8)
        self.assertTrue(d.small_json(d.path(d.ACTIVITY, root=self.root))['complete'])

    def test_write_once_20mb_and_wrong_namespace(self):
        self.save()
        with self.assertRaises(FileExistsError): d.write(d.REPORT, {}, root=self.root)
        with self.assertRaises(ValueError): d.write('test_result/evidence/other/report.json', {}, root=self.root)
        with self.assertRaises(ValueError): d.write(d.FAILURE, dict(x='x' * d.LIMIT), root=self.root)

    def test_corrupted_activity_not_promoted(self):
        for changes in (dict(complete=False), dict(seconds=9000), dict(worker_pgid=8), dict(info_sha256='B' * 64),
                        dict(started_at=d.END.isoformat()), dict(returncode=9)):
            with self.subTest(changes=changes):
                with tempfile.TemporaryDirectory(prefix='p106b_val_bad_receipt_') as directory:
                    root = Path(directory); d.write(d.REPORT, self.report, root=root)
                    activity = dict(self.activity, report_sha256=d.digest(d.path(d.REPORT, root=root)), **changes)
                    d.write(d.ACTIVITY, activity, root=root)
                    with self.assertRaises(ValueError): d.closed_result(self.info, root=root)

    def test_measurement_forgery_count_hash_and_false_zero_rejected(self):
        for key, value in (('ids', 1), ('sha256', 'A' * 64), ('last_id_matches_eos', False), ('maximum_segment_ids_observed', d.MAX_SEGMENT_IDS + 1)):
            report = deepcopy(self.report); report['measurements']['train'][key] = value
            with tempfile.TemporaryDirectory(prefix='p106b_val_bad_result_') as directory:
                root = Path(directory); d.write(d.REPORT, report, root=root)
                d.write(d.ACTIVITY, dict(self.activity, report_sha256=d.digest(d.path(d.REPORT, root=root))), root=root)
                with self.assertRaises(ValueError): d.closed_result(self.info, root=root)
        self.report['measurements']['train']['same_rule']['full_eos_segments'] = 1; self.save()
        with self.assertRaises(ValueError): d.closed_result(self.info, root=self.root)

    def pipeline(self):
        original = d.closed_result; commands = []
        with patch.object(d, 'launch', side_effect=lambda c, t: commands.append(c) or 0), patch.object(d, 'preflight_after_claim', return_value=None):
            with patch.object(d, 'closed_result', side_effect=lambda info: original(info, root=self.root)):
                with patch('sys.stdout', io.StringIO()) as output, patch('sys.stderr', io.StringIO()):
                    result = d.main(['--execute', '--max-wall-sec', '60'])
        self.assertEqual(len(commands), 3)
        return result, output.getvalue()

    def test_three_phase_post_worker_uses_real_closed_reader(self):
        self.save(); result, output = self.pipeline()
        self.assertEqual(result, 0); self.assertIn('ZERO_HITS_AT_DECLARED_SCOPE', output)

    def test_three_phase_completed_negative_is_hold8(self):
        self.report['measurements'] = synthetic_measurements(True); self.report['mechanical_status'] = 'NEGATIVE_OBSERVED_HITS'; self.save()
        result, output = self.pipeline()
        self.assertEqual(result, 8); self.assertIn('NEGATIVE_OBSERVED_HITS', output)
        self.assertTrue(d.small_json(d.path(d.ACTIVITY, root=self.root))['complete'])

    def test_three_phase_worker0_strict_failure_is_not_complete(self):
        self.activity['complete'] = False; self.activity['returncode'] = 9; self.save()
        result, output = self.pipeline()
        self.assertEqual(result, 9); self.assertIn('EXECUTED_STRICT_VERIFY_FAILED', output)


class WorkerTests(unittest.TestCase):
    def child(self, kind):
        code = 'from scripts.test_p106b_expansion_val_audit import process_fixture; raise SystemExit(process_fixture(' + repr(kind) + '))'
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            stdin=subprocess.DEVNULL, start_new_session=True, capture_output=True, text=True, timeout=20,
            env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'))

    def test_real_own_worker_closed_activity_then_strict_reader(self):
        result = self.child('normal'); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertTrue(value['complete'])
        self.assertEqual(value['activity']['worker_pid'], value['activity']['worker_pgid'])

    def test_completed_negative_final_is8(self):
        result = self.child('negative'); self.assertEqual(result.returncode, 8, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertEqual(value['worker_rc'], 0); self.assertTrue(value['complete'])

    def test_term_timeout_error_recorded(self):
        for kind, code in (('term', 130), ('timeout', 124), ('error', 9)):
            result = self.child(kind); self.assertEqual(result.returncode, code, result.stdout + result.stderr)
            value = json.loads(result.stdout.splitlines()[-1]); self.assertFalse(value['complete']); self.assertTrue(value['error_recorded'])

    def test_signal_handlers_restored(self):
        previous = (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGALRM))
        with self.assertRaises(KeyboardInterrupt):
            with d.bounded(60): os.kill(os.getpid(), signal.SIGTERM)
        self.assertEqual((signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGALRM)), previous)

    def test_existing_namespace_rejected_without_overwrite(self):
        result = self.child('rerun'); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertTrue(value['rerun_rejected']); self.assertTrue(value['original_report_same'])


if __name__ == '__main__': unittest.main()
