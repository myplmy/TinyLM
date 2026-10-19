"""CPU/code-only and tiny temp fixtures; no real corpus/model/checkpoint reads."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_broad_recovery as r
from scripts.test_p106b_broad_curriculum import Tokens, conversation

d = r.legacy


def original_info():
    with r._attributes(TAG=r.ORIGINAL_TAG):
        return r._INFO()


def frozen_pair():
    original = original_info()
    admission = dict(status='ADMISSIBLE', selected_source_indices=[7, 11])
    manifests = {stem: dict(rows=2, bytes=100, concat_sha256='PAYLOAD',
        shards=[dict(path=stem + '_000000.jsonl', rows=2, bytes=100, sha256='LINES')],
        lineage=dict(tag=r.ORIGINAL_TAG, stem=stem)) for stem in ('train', 'dev', 'monitor', 'dialogues')}
    reference = dict(original, status='BROAD_CPU_FROZEN', source_admission=admission,
        manifests=manifests, model_loaded=False, optimizer_updates=0, checkpoints_written=0,
        course_report_sha256='COURSE', dev_rows=2, dev_targets=4,
        monitor_overlap={}, dialogue_selection={'source_indices': [1, 2]},
        monitor_display_ids=['CASE'], monitor_display_selection_sha256='DISPLAY',
        dialogue_source_turns=2, source_pins={})
    current = copy.deepcopy(reference); current.update(r.info())
    for stem, manifest in current['manifests'].items():
        manifest['lineage'] = dict(tag=r.TAG, stem=stem)
    return original, reference, current


@contextmanager
def tiny_payloads():
    """Independent adapter audit fixture, not production-course preparation."""
    from tinylm.train.mtp_sft import Record
    with tempfile.TemporaryDirectory(prefix='broad_recovery_') as temporary:
        root = Path(temporary); old_cache, cache = root / 'old', root / 'new'
        old_evidence, evidence = root / 'old_evidence', root / 'evidence'
        with patch.object(d, 'safe', side_effect=Path), \
             patch.object(d.monitor, 'safe', side_effect=Path), \
             patch.object(d.monitor, 'required', side_effect=lambda path: json.loads(Path(path).read_text())), \
             patch.object(r, 'ORIGINAL_CACHE', old_cache), patch.object(r, 'CACHE', cache), \
             patch.object(r, 'ORIGINAL_EVIDENCE', old_evidence), patch.object(r, 'EVIDENCE', evidence), \
             patch.object(r, 'REFERENCE_PINS', {}), r.runtime_scope():
            old_info, reference, current = frozen_pair()
            records = [Record([8, 9, 10], [-100, 5, 4], [1, 1, 1]), Record([8], [4], [1])]
            metadata = [d.builder._metadata(conversation(i, turns=1), rec, 'replay', i)
                        for i, rec in enumerate(records)]
            train = [d._wire(rec, meta) for rec, meta in zip(records, metadata)]
            populations = dict(train=train, dev=train[:1], monitor=[{'id': 'FIXTURE'}],
                dialogues=[{'id': 'DIALOGUE_FIXTURE', 'expected_source_turns': 2}])
            for directory, target, tag in ((old_cache, reference, r.ORIGINAL_TAG), (cache, current, r.TAG)):
                with r._attributes(CACHE=directory, TAG=tag):
                    target['manifests'] = {stem: d._put(stem, rows) for stem, rows in populations.items()}
            course = dict(schema=d.builder.VERSION, selection_key=d.builder.SELECTION_KEY,
                groups_per_pass=176, updates=352, per_pass=d.builder._aggregate(metadata),
                ordered_record_hashes_sha256=d.sha([meta['record_sha256'] for meta in metadata]),
                schedules_sha256='SAME_FIXED_ORDER')
            for directory in (old_cache, cache):
                d.write(directory / 'course.json', course)
            for value in (reference, current):
                value.update(course_report_sha256=d.digest(cache / 'course.json'), dev_rows=1,
                    dev_targets=records[0].targets, dialogue_source_turns=2)
            d.write(old_cache / 'frozen.json', reference); d.write(cache / 'frozen.json', current)
            d.write(old_evidence / 'activity_prepare.json', dict(complete=False, returncode=None))
            with patch.object(d, 'completed_activity', return_value={'complete': True}):
                yield root, reference, current, course, populations


class MetadataTests(unittest.TestCase):
    def test_full_production_info_separates_policy_and_result_and_pins_both_files(self):
        baseline, current = original_info(), r.info()
        self.assertGreaterEqual(len(baseline), 43)
        self.assertEqual(baseline['source_admission'], 'CPU_PREPARE_ONLY')
        self.assertNotIn('source_admission', current)
        self.assertEqual(current['source_admission_policy'], baseline['source_admission'])
        self.assertEqual(current['tag'], r.TAG)
        self.assertTrue(current['code_complete'])
        for key, value in baseline.items():
            if key not in ('tag', 'source_admission', 'code_sha256', 'code_complete'):
                self.assertEqual(current[key], value, key)
        self.assertEqual(set(current['code_sha256']), set(baseline['code_sha256']) | set(r.OWN_CODE))
        for path in r.OWN_CODE:
            self.assertEqual(current['code_sha256'][path], d.digest(ROOT / path))

    def test_missing_adapter_code_recalculates_complete(self):
        with patch.object(r, 'OWN_CODE', ('scripts/not_created_recovery_fixture.py',)):
            current = r.info()
        self.assertFalse(current['code_complete'])
        self.assertEqual(current['code_sha256']['scripts/not_created_recovery_fixture.py'], 'NOT_CREATED')

    def test_original_full_info_serialization_reproduces_failure_not_hidden_by_minimal_mock(self):
        baseline, reference, _ = frozen_pair()
        serialized = json.loads(json.dumps(reference))
        self.assertEqual({k for k, v in baseline.items() if serialized.get(k) != v}, {'source_admission'})
        with patch.object(d, 'required', return_value=serialized):
            with self.assertRaisesRegex(ValueError, 'same exact prepared code/recipe'):
                d.prepared(completed=False)

    def test_full_production_info_writer_reader_and_prepared_metadata_roundtrip(self):
        # Keep the real full info() and real JSON writer/reader/hash/contract code.
        # Stop precisely at the row reader; do not substitute a tiny info mock.
        class MetadataReached(Exception):
            pass
        with tempfile.TemporaryDirectory(prefix='broad_full_info_') as temporary:
            root = Path(temporary)
            with r.runtime_scope(), patch.object(d, 'CACHE', root / 'cache'), \
                 patch.object(d, 'EVIDENCE', root / 'evidence'), patch.object(d, 'safe', side_effect=Path):
                _, _, value = frozen_pair()
                d.write(d.CACHE / 'course.json', {'fixture': 'metadata boundary only'})
                value['course_report_sha256'] = d.digest(d.CACHE / 'course.json')
                d.write(d.CACHE / 'frozen.json', value)
                d.write(d.EVIDENCE / 'cpu_contract.json', d.public_contract(value))
                loaded = d.required(d.CACHE / 'frozen.json')
                self.assertEqual(loaded['source_admission_policy'], 'CPU_PREPARE_ONLY')
                self.assertEqual(loaded['source_admission']['status'], 'ADMISSIBLE')
                self.assertGreaterEqual(len(d.info()), 43)
                with patch.object(d, '_read', side_effect=MetadataReached) as rows, \
                     patch.object(d, 'completed_activity') as activity:
                    with self.assertRaises(MetadataReached):
                        d.prepared(completed=False)
                rows.assert_called_once(); activity.assert_not_called()

    def test_strict_frozen_comparison_allows_only_new_info_and_lineage(self):
        baseline, reference, current = frozen_pair()
        payloads = r.compare_frozen(reference, current, reference_info=baseline, current_info=r.info())
        self.assertEqual(set(payloads), {'train', 'dev', 'monitor', 'dialogues'})
        for mutate in (
            lambda value: value['source_admission']['selected_source_indices'].reverse(),
            lambda value: value.update(dev_targets=5),
            lambda value: value.update(optimizer_updates=True),
            lambda value: value.update(dialogue_source_turns=3),
            lambda value: value['manifests']['train']['shards'][0].update(sha256='CHANGED'),
            lambda value: value['manifests']['monitor']['lineage'].update(tag=r.ORIGINAL_TAG),
            lambda value: value.update(course_report_sha256='DIFFERENT'),
        ):
            changed = copy.deepcopy(current); mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaisesRegex(ValueError, 'v2 changed'):
                r.compare_frozen(reference, changed, reference_info=baseline, current_info=r.info())

    def test_other_original_failure_or_completed_experiment_cannot_be_recovered(self):
        baseline, reference, current = frozen_pair()
        for key, value in (('source_admission', {}), ('optimizer_updates', 1), ('model_loaded', True),
                           ('parent_sha256', 'OTHER'), ('tag', r.TAG)):
            changed = copy.deepcopy(reference); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                r.compare_frozen(changed, current, reference_info=baseline, current_info=r.info())


class ScopeTests(unittest.TestCase):
    def test_scope_changes_only_eight_approved_globals_and_restores_on_exception(self):
        before = dict(vars(d))
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with r.runtime_scope():
                changed = {key for key, value in before.items() if getattr(d, key) is not value}
                self.assertEqual(changed, {'TAG', 'CACHE', 'RAW', 'EVIDENCE', 'info', 'phase_commands',
                                          'select_dialogues', 'monitor_display_ids'})
                for name in ('prepare', 'prepared', 'train', 'train_updates', 'evaluate', 'run_dialogue',
                             'readback', 'budget', 'launch', 'worker'):
                    self.assertIs(getattr(d, name), before[name])
                self.assertEqual(d.builder.SELECTION_KEY, r.ORIGINAL_TAG)
                self.assertEqual(d.builder.VERSION, 'P106B_BROAD_COURSE_ORDER_V1')
                raise RuntimeError('fixture')
        for key, value in before.items():
            self.assertIs(getattr(d, key), value, key)

    def test_nested_scope_restores_outer_then_original(self):
        original = d.info
        with r.runtime_scope():
            with r.runtime_scope():
                self.assertIs(d.info, r.info)
            self.assertIs(d.info, r.info)
            self.assertEqual(d.TAG, r.TAG)
        self.assertIs(d.info, original)

    def test_pure_dialogue_and_monitor_hash_selection_are_identical_to_v1(self):
        rows = [conversation(i, 'ko', 1) for i in range(10)] + [conversation(100 + i, 'en', 2) for i in range(12)]
        cases = [dict(id=str(i), lane='coded') for i in range(20)] + [dict(id='U' + str(i), lane='user_seen') for i in range(6)]
        original_dialogues = r._DIALOGUES(rows, Tokens()); original_display = r._DISPLAY(cases)
        before = d.sha(rows)
        with r.runtime_scope():
            self.assertEqual(d.select_dialogues(rows, Tokens()), original_dialogues)
            self.assertEqual(d.monitor_display_ids(cases), original_display)
            self.assertEqual(d.TAG, r.TAG)
        self.assertEqual(d.sha(rows), before)

    def test_failed_pure_selector_restores_v2_tag(self):
        with r.runtime_scope(), patch.object(r, '_DIALOGUES', side_effect=ValueError('fixture')):
            with self.assertRaisesRegex(ValueError, 'fixture'):
                d.select_dialogues([], Tokens())
            self.assertEqual(d.TAG, r.TAG)

    def test_all_worker_commands_use_wrapper_and_regression_adds_new_test(self):
        for mode in d.MODES:
            arms = d.ARMS if mode in ('cost', 'train') else (None, *d.ARMS) if mode == 'evaluate' else (None,)
            for arm in arms:
                original = r._PHASES(mode, arm, 600)
                phases = r.phase_commands(mode, arm, 600)
                expected = copy.deepcopy(original)
                for _, command in expected:
                    command[:] = [r.SCRIPT if part == r.OLD_SCRIPT else part for part in command]
                expected[0][1].insert(expected[0][1].index('-v'), r.TEST)
                self.assertEqual(phases, expected)
                self.assertNotIn(r.OLD_SCRIPT, repr(phases))
        for mode, arm in (('prepare', 'mixed'), ('train', None), ('evaluate', 'foreign')):
            with self.assertRaises(ValueError): r.phase_commands(mode, arm, 600)

    def test_check_only_uses_legacy_main_without_assets_receipts_or_launches(self):
        with patch.object(r, 'validate_equivalence') as receipt, patch.object(r, 'audit_equivalence') as audit, \
             patch.object(d, 'source_pins') as sources, patch.object(d, 'launch') as launch, \
             patch.object(d, 'worker') as worker, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(r.main(['--mode', 'evaluate', '--check-only']), 0)
        for spy in (receipt, audit, sources, launch, worker): spy.assert_not_called()
        self.assertEqual(json.loads(output.getvalue().split(' ', 1)[1])['tag'], r.TAG)

    def test_parent_and_both_student_selectors_are_unchanged(self):
        with r.runtime_scope():
            self.assertEqual(d.activity_key('evaluate', None), 'evaluate_parent')
            self.assertIn(r.TAG, str(d.checkpoint('mixed')))
            self.assertEqual(d.info()['parent_sha256'], original_info()['parent_sha256'])
            self.assertEqual(d.info()['expected_parent_core'], original_info()['expected_parent_core'])
            self.assertEqual(d.info()['updates'], 352)
            self.assertEqual(d.info()['active_limit_seconds'], 10800)
            for arm in (None, 'parent', '../other'):
                with self.assertRaises(ValueError): d.checkpoint(arm)


class EquivalenceTests(unittest.TestCase):
    def test_independent_tiny_wire_audit_verifies_real_encoded_counts_masks_and_order_hash(self):
        with tiny_payloads() as (_, reference, current, course, _):
            report = r.audit_equivalence()
            self.assertEqual(report['status'], 'BROAD_V1_PAYLOAD_EQUIVALENT')
            self.assertEqual(report['verified_counts']['train']['masked_positive_owner_tokens'], 1)
            self.assertEqual(report['verified_counts']['train']['eot_targets'], 2)
            self.assertEqual(report['verified_counts']['train']['assistant_targets'], 3)
            self.assertEqual(report['schedules_sha256'], course['schedules_sha256'])
            self.assertFalse(report['original_prepare_complete'])
            self.assertEqual(reference['source_admission'], current['source_admission'])
            self.assertFalse((r.EVIDENCE / 'v1_payload_equivalence.json').exists())

    def test_changed_payload_is_rejected_even_with_unchanged_manifests(self):
        with tiny_payloads() as (_, _, current, _, _):
            spec = current['manifests']['train']['shards'][0]
            path = r.CACHE / 'wire' / spec['path']
            path.write_bytes(path.read_bytes().replace(b'"y":[-100,5,4]', b'"y":[-100,6,4]'))
            with self.assertRaisesRegex(ValueError, 'shard byte/line/hash'):
                r.audit_equivalence()

    def test_changed_course_standalone_manifest_or_old_complete_is_rejected(self):
        for kind in ('course', 'manifest', 'old_complete'):
            with self.subTest(kind=kind), tiny_payloads():
                if kind == 'course':
                    path = r.CACHE / 'course.json'; path.write_bytes(path.read_bytes() + b' ')
                elif kind == 'manifest':
                    path = r.CACHE / 'wire/train_shards_manifest.json'
                    value = json.loads(path.read_text()); value['lineage']['tag'] = 'OTHER'
                    path.write_text(json.dumps(value))
                else:
                    path = r.ORIGINAL_EVIDENCE / 'activity_prepare.json'
                    path.write_text(json.dumps(dict(complete=True, returncode=0)))
                with self.assertRaises(ValueError): r.audit_equivalence()

    def test_receipt_requires_exact_code_frozen_and_completed_report_binding(self):
        with tiny_payloads() as (_, _, _, _, _):
            report = r.audit_equivalence(); d.write(r.equivalence_path(), report)
            full_info = r.info()
            activity = dict(schema=r.RECOVERY_SCHEMA, tag=r.TAG, key='recovery_equivalence',
                scope=r.ACTIVITY_SCOPE, complete=True, returncode=0, max_wall_sec=600,
                recorded_at=d.END.isoformat(), code_sha256=full_info['code_sha256'], seconds=1.)
            with patch.object(r, 'ROOT', Path('/')), patch.object(r, 'info', return_value=full_info):
                activity['report_path'] = str(r.equivalence_path().relative_to(Path('/')))
                activity['report_sha256'] = d.digest(r.equivalence_path())
                d.write(r.equivalence_activity_path(), activity)
                r.validate_equivalence()
                changed = copy.deepcopy(report); changed['frozen_sha256'] = 'WRONG'
                with patch.object(d, 'required', wraps=d.required) as required:
                    original = required._mock_wraps
                    required.side_effect = lambda path: changed if Path(path) == r.equivalence_path() else original(path)
                    with self.assertRaisesRegex(ValueError, 'exact-frozen'): r.validate_equivalence()
                for key, value in (('complete', False), ('returncode', False), ('report_sha256', 'OTHER'),
                                   ('code_sha256', {}), ('key', 'prepare'), ('seconds', float('nan'))):
                    changed_activity = dict(activity); changed_activity[key] = value
                    with self.subTest(key=key), patch.object(d, 'required', wraps=d.required) as required:
                        original = required._mock_wraps
                        required.side_effect = lambda path: (changed_activity if Path(path) ==
                            r.equivalence_activity_path() else original(path))
                        with self.assertRaisesRegex(ValueError, 'completed exact-code/report'):
                            r.validate_equivalence()

    def test_reference_pins_fail_before_any_payload_or_model_read(self):
        with patch.object(d, 'digest', return_value='CHANGED'), patch.object(d, 'required') as required:
            with self.assertRaisesRegex(ValueError, 'v1 partial/log/activity changed'):
                r._equivalence_metadata()
        required.assert_not_called()

    def test_every_downstream_worker_is_blocked_before_legacy_main_without_receipt(self):
        for mode in ('preflight', 'cost', 'budget', 'train', 'evaluate', 'readback'):
            argv = ['--mode', mode, '--worker', '--execute', '--max-wall-sec', '600']
            if mode in ('cost', 'train'): argv += ['--arm', 'mixed']
            with self.subTest(mode=mode), patch.object(r, 'validate_equivalence', side_effect=d.Pending('receipt absent')), \
                 patch.object(d, 'main') as main, redirect_stdout(io.StringIO()):
                self.assertEqual(r.main(argv), 8)
            main.assert_not_called()

    def test_prepare_success_audits_after_legacy_and_failure_does_not_audit(self):
        argv = ['--mode', 'prepare', '--worker', '--execute', '--max-wall-sec', '600']
        order = []
        with patch.object(d, 'main', side_effect=lambda args: order.append(('core', d.TAG, args)) or 0), \
             patch.object(r, 'finish_prepare_equivalence', side_effect=lambda *args: order.append(('audit', d.TAG))), \
             patch.object(r, 'validate_equivalence') as validation:
            self.assertEqual(r.main(argv), 0)
        self.assertEqual([item[0] for item in order], ['core', 'audit'])
        self.assertTrue(all(item[1] == r.TAG for item in order)); validation.assert_not_called()
        with patch.object(d, 'main', return_value=9), patch.object(r, 'finish_prepare_equivalence') as audit:
            self.assertEqual(r.main(argv), 9)
        audit.assert_not_called()

    def test_validated_receipt_precedes_unchanged_downstream_main(self):
        order = []
        with patch.object(r, 'validate_equivalence', side_effect=lambda: order.append('receipt')), \
             patch.object(d, 'main', side_effect=lambda args: order.append(('main', d.TAG, args)) or 0), \
             patch.object(r, 'finish_prepare_equivalence') as audit:
            argv = ['--mode', 'evaluate', '--worker', '--execute']
            self.assertEqual(r.main(argv), 0)
        self.assertEqual(order, ['receipt', ('main', r.TAG, argv)])
        audit.assert_not_called()

    def test_adapter_audit_failure_does_not_turn_core_success_into_overall_success(self):
        with patch.object(d, 'main', return_value=0), \
             patch.object(r, 'finish_prepare_equivalence', side_effect=ValueError('payload differs')), \
             redirect_stdout(io.StringIO()), patch('traceback.print_exc'):
            self.assertEqual(r.main(['--mode', 'prepare', '--worker', '--execute']), 9)

    def test_audit_wall_is_separately_counted_without_mutating_core_activity(self):
        with tempfile.TemporaryDirectory(prefix='broad_recovery_wall_') as temporary:
            root = Path(temporary); evidence = root / 'evidence'
            complete = dict(schema=r.RECOVERY_SCHEMA, tag=r.TAG, seconds=7.)
            with patch.object(r, 'ROOT', root), patch.object(r, 'EVIDENCE', evidence), \
                 patch.object(d, 'EVIDENCE', evidence), patch.object(d, 'TAG', r.TAG), \
                 patch.object(d, 'safe', side_effect=Path), \
                 patch.object(r, 'info', return_value=dict(code_sha256={'fixture': 'CODE'})), \
                 patch.object(r, 'audit_equivalence', return_value=complete), \
                 patch.object(d, 'authority', return_value=10000), redirect_stdout(io.StringIO()):
                core = evidence / 'activity_prepare.json'
                d.write(core, dict(tag=r.TAG, seconds=2., complete=True))
                before = core.read_bytes()
                r.finish_prepare_equivalence(600, time.perf_counter())
                activity = d.required(r.equivalence_activity_path())
                self.assertEqual(core.read_bytes(), before)
                self.assertTrue(activity['complete'])
                self.assertEqual(activity['report_sha256'], d.digest(r.equivalence_path()))
                self.assertAlmostEqual(d.spent_seconds(), 2. + activity['seconds'])
                with self.assertRaises(FileExistsError):
                    r.finish_prepare_equivalence(600, time.perf_counter())

    def test_audit_cannot_spend_record_reserve_or_exceed_original_worker_cap(self):
        with tempfile.TemporaryDirectory(prefix='broad_recovery_limit_') as temporary:
            root = Path(temporary)
            with patch.object(r, 'ROOT', root), patch.object(r, 'EVIDENCE', root / 'evidence'), \
                 patch.object(d, 'safe', side_effect=Path), patch.object(d, 'authority', return_value=10000), \
                 patch.object(d, 'spent_seconds', return_value=0.), \
                 patch.object(r, 'info', return_value=dict(code_sha256={'fixture': 'CODE'})), \
                 patch.object(r, 'audit_equivalence') as audit:
                with self.assertRaises(d.Pending):
                    r.finish_prepare_equivalence(60, time.perf_counter() - 1)
                self.assertFalse(d.required(r.equivalence_activity_path())['complete'])
                self.assertFalse(r.equivalence_path().exists())
                audit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
