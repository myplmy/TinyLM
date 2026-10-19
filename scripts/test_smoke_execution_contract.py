"""Pure/temp regressions for shared smoke helpers and recorded aliases.

No actual corpus/model payloads, host signals or children are
needed. ``destinations`` is a pure namespace lookup, not the runner's exclusive
mkdir/reservation operation.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import smoke_execution_contract as contract
from scripts import smoke_module


BAT = r'''@echo off
setlocal enabledelayedexpansion
python scripts\runlog.py --name !TL_LOGNAME! --note "source fixture"
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_handoff.py
timeout /t 15 /nobreak
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --tiny --data synthetic --steps 1 --tag sm_fixture
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_smoke.py
exit /b 0
'''


class Cancelled(RuntimeError):
    pass


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='smoke_contract_fixture_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write(contract.CANONICAL_SOURCE, BAT)
        for name in (contract.NEW_DRIVER, contract.CONTRACT_MODULE,
                     contract.CODEX_CHECKER, 'scripts/runlog.py',
                     'scripts/smoke_module.py', 'scripts/summarize_smoke.py',
                     'scripts/check_smoke.py', 'scripts/smoke_diag_contract.tsv',
                     'scripts/check_handoff.py', 'run100m.py'):
            self.write(name, '# FAKE bounded source: ' + name + '\n')

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
        return path

    def actions(self):
        return smoke_module.parse_smoke_module(
            self.root / contract.CANONICAL_SOURCE, log_name='smoke_codex_fixture')

    def adapted(self, actions=None, **kwargs):
        return contract.adapt_actions(
            self.actions() if actions is None else actions,
            driver=kwargs.pop('driver', contract.NEW_DRIVER),
            contract_args=kwargs.pop('contract_args',
                                     ['--mode', 'contract', '--session-id', 'fixture']),
            **kwargs)

    def deny_linked_target_access(self, link, target):
        """Allow lstat of the link itself, never its target/descendants."""
        original_stat, original_iterdir, original_open = Path.stat, Path.iterdir, Path.open
        observed = []

        def touches(path):
            return path == target or target in path.parents or link in path.parents

        def stat(path, *a, **k):
            if touches(path) or (path == link and k.get('follow_symlinks', True)):
                observed.append(('stat', str(path)))
                raise AssertionError('linked target metadata must not be inspected')
            return original_stat(path, *a, **k)

        def iterdir(path):
            if touches(path) or path == link:
                observed.append(('iterdir', str(path)))
                raise AssertionError('linked target must not be traversed')
            return original_iterdir(path)

        def opened(path, *a, **k):
            if touches(path) or path == link:
                observed.append(('open', str(path)))
                raise AssertionError('linked target must not be opened')
            return original_open(path, *a, **k)

        stack = ExitStack()
        stack.enter_context(mock.patch.object(Path, 'stat', autospec=True, side_effect=stat))
        stack.enter_context(mock.patch.object(Path, 'iterdir', autospec=True, side_effect=iterdir))
        stack.enter_context(mock.patch.object(Path, 'open', autospec=True, side_effect=opened))
        return stack, observed


class DestinationTests(Fixture):
    def test_versioned_constants(self):
        self.assertEqual(contract.NEW_SCHEMA, 'TINYLM_CODEX_SMOKE_EXECUTION_V1')
        self.assertEqual(contract.NEW_PROFILE_ID, 'codex_isolated_smoke_v1')
        self.assertEqual(contract.NEW_DRIVER, 'scripts/codex_smoke.py')
        self.assertEqual(contract.CONTRACT_MODULE, 'scripts/smoke_execution_contract.py')

    def test_safe_single_component_session_ids(self):
        for value in ('a', '0', 'Session-01_a', 'x' * 64):
            with self.subTest(value=value):
                dest = contract.destinations(self.root, value)
                self.assertEqual(dest['runtime'], self.root / 'runs/validation/codex_smoke' / value)
                self.assertEqual(dest['evidence'], self.root / 'test_result/evidence/codex_smoke' / value)
                self.assertEqual(dest['report'], dest['evidence'] / 'smoke_report.json')
                self.assertEqual(dest['log_name'], 'smoke_codex_' + value)

    def test_unsafe_ids_rejected_before_filesystem_queries(self):
        for value in ('', '.', '..', '../old', '/absolute', 'a/b', 'a\\b', 'a.b',
                      '-first', '_first', 'a b', 'a\n', '한글', 'x' * 65,
                      None, 1, True, Path('path')):
            with self.subTest(value=value), \
                    mock.patch.object(Path, 'is_symlink') as link, \
                    self.assertRaises(ValueError):
                contract.destinations(self.root, value)
            link.assert_not_called()

    def test_different_sessions_have_nonoverlapping_owned_leaf_namespaces(self):
        first = contract.destinations(self.root, 'first')
        second = contract.destinations(self.root, 'second')
        for key in ('runtime', 'evidence', 'report', 'log_name'):
            self.assertNotEqual(first[key], second[key])
        self.assertNotIn(first['runtime'], second['runtime'].parents)
        self.assertNotIn(second['runtime'], first['runtime'].parents)

    def test_lookup_creates_nothing_and_existing_lookup_does_not_overwrite(self):
        first = contract.destinations(self.root, 'same')
        self.assertFalse(first['runtime'].exists())
        self.assertFalse(first['evidence'].exists())
        first['runtime'].mkdir(parents=True)
        first['evidence'].mkdir(parents=True)
        first['report'].write_bytes(b'historical fixture receipt\n')
        self.assertEqual(contract.destinations(self.root, 'same'), first)
        self.assertEqual(first['report'].read_bytes(), b'historical fixture receipt\n')

    def test_linked_runtime_or_evidence_or_raw_directory_rejected(self):
        for name in ('runs/validation/codex_smoke/linked',
                     'test_result/evidence/codex_smoke/linked', 'smoketest_logs'):
            with self.subTest(name=name):
                target = self.root / ('fake_target_' + name.replace('/', '_'))
                target.mkdir()
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(target, target_is_directory=True)
                with self.assertRaises(ValueError):
                    contract.destinations(self.root, 'linked')
                path.unlink()  # Temporary fixture only; never a repository path.

    def test_linked_repository_root_is_rejected(self):
        link = self.root / 'repo_alias'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            contract.destinations(link, 'fixture')


class AdaptationTests(Fixture):
    def test_only_exact_two_edits_with_full_topology_and_argv_preserved(self):
        actions = self.actions()
        before = [asdict(a) for a in actions]
        adapted, edits = self.adapted(actions)
        self.assertEqual([e['kind'] for e in edits],
                         ['codex_document_checker', 'isolated_field_log_path'])
        self.assertEqual([asdict(a) for a in actions], before)
        self.assertEqual(len(actions), len(adapted))
        changed = []
        for original, actual in zip(actions, adapted):
            self.assertEqual((original.kind, original.line, original.seconds),
                             (actual.kind, actual.line, actual.seconds))
            if original.argv != actual.argv:
                changed.append(original.line)
            if 'run100m.py' in original.argv:
                self.assertEqual(original.argv, actual.argv)
        self.assertEqual(changed, [e['line'] for e in edits])
        doc, field = edits
        self.assertEqual(doc['before'], list(actions[1].argv))
        self.assertEqual(doc['after'], list(adapted[1].argv))
        self.assertEqual(doc['after'][-4:], [sys.executable, '-I', '-B', contract.CODEX_CHECKER])
        self.assertEqual(field['after'][-5:],
                         [contract.NEW_DRIVER, '--mode', 'contract', '--session-id', 'fixture'])

    def test_note_strings_and_training_arguments_are_not_global_replacements(self):
        actions = self.actions()
        note = smoke_module.Action('run', 1, (sys.executable, 'scripts/runlog.py', '--name',
                                              'smoke', '--note', 'scripts/check_handoff.py'))
        train = smoke_module.Action('run', 2, (sys.executable, 'scripts/runlog.py', '--name',
                                               'smoke', '--', sys.executable, 'run100m.py',
                                               'train', '--literal', 'scripts/check_smoke.py'))
        adapted, edits = self.adapted([note, train, *actions])
        self.assertEqual(adapted[0], note)
        self.assertEqual(adapted[1], train)
        self.assertEqual(len(edits), 2)

    def test_missing_duplicate_reordered_and_extra_flag_document_checks_rejected(self):
        actions = self.actions()
        malformed = (
            [a for a in actions if 'scripts/check_handoff.py' not in a.argv],
            [actions[0], actions[1], actions[1], *actions[2:]],
            [actions[0], actions[-1], *actions[1:-1]],
            [actions[0], smoke_module.Action('run', actions[1].line,
                 (*actions[1].argv, '--extra')), *actions[2:]],
        )
        for rows in malformed:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.adapted(rows)

    def test_bad_driver_or_contract_argument_types_rejected(self):
        for driver in ('/absolute.py', '../parent.py', 'scripts/../parent.py',
                       'scripts/tool.txt', None, 7):
            with self.subTest(driver=driver), self.assertRaises(ValueError):
                self.adapted(driver=driver)
        for args in (None, '--mode contract', [1], ['--mode', None]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.adapted(contract_args=args)

    def test_tuple_contract_args_supported_without_mutation(self):
        args = ('--mode', 'contract', '--session-id', 'tuple')
        changed, _ = self.adapted(contract_args=args)
        self.assertEqual(changed[-1].argv[-len(args):], args)
        self.assertEqual(args, ('--mode', 'contract', '--session-id', 'tuple'))


class HashGuardTests(Fixture):
    def test_legacy_single_positional_file_sha_and_empty_sha(self):
        path = self.root / 'empty.bin'
        path.write_bytes(b'')
        self.assertEqual(contract.file_sha256(path), hashlib.sha256(b'').hexdigest().upper())

    def test_file_sha_guard_is_called_at_start_each_chunk_and_finish(self):
        path = self.root / 'chunk_fixture.bin'
        content = b'x' * (1024 * 1024 + 7)
        path.write_bytes(content)
        guard = mock.Mock()
        got = contract.file_sha256(path, guard=guard)
        self.assertEqual(got, hashlib.sha256(content).hexdigest().upper())
        self.assertEqual(guard.call_count, 4)

    def test_immediate_file_guard_cancellation_precedes_metadata_and_open(self):
        with mock.patch.object(contract, '_regular') as regular, \
                self.assertRaises(Cancelled):
            contract.file_sha256(self.root / 'never-opened',
                                 guard=mock.Mock(side_effect=Cancelled('cancel first')))
        regular.assert_not_called()

    def test_chunk_guard_cancellation_closes_stream_and_never_returns_partial_sha(self):
        path = self.write('source_for_mocked_stream.py', '# fixture')

        class Stream(io.BytesIO):
            def __init__(self):
                super().__init__(b'a' * (2 * 1024 * 1024 + 1))
                self.read_calls = 0

            def read(self, *a):
                self.read_calls += 1
                return super().read(*a)

        stream = Stream()
        count = [0]

        def guard():
            count[0] += 1
            if count[0] == 2:
                raise Cancelled('cancel on first data chunk')

        with mock.patch.object(Path, 'open', return_value=stream), self.assertRaises(Cancelled):
            contract.file_sha256(path, guard=guard)
        self.assertTrue(stream.closed)
        self.assertEqual(stream.read_calls, 1)

    def test_finish_guard_cancellation_is_not_a_complete_hash(self):
        path = self.write('one_chunk.py', '# fixture')
        count = [0]

        def guard():
            count[0] += 1
            if count[0] == 3:
                raise Cancelled('cancel final completion')

        with self.assertRaises(Cancelled):
            contract.file_sha256(path, guard=guard)
        self.assertEqual(count[0], 3)

    def test_missing_directory_and_linked_file_never_opened_as_a_regular_source(self):
        target = self.write('regular.py', '# fake')
        link = self.root / 'linked.py'
        link.symlink_to(target)
        for path in (self.root / 'missing.py', self.root, link):
            with self.subTest(path=path), mock.patch.object(Path, 'open') as opened, \
                    self.assertRaises(ValueError):
                contract.file_sha256(path)
            opened.assert_not_called()


class SourcePinTests(Fixture):
    def test_source_pins_cover_only_declared_code_and_model_source_tree(self):
        core = self.write('tinylm/model/fake_core.py', '# source text, never imported')
        self.write('tinylm/model/ignored.txt', 'not source')
        for name in ('runs/ckpt/never.pt', 'datasets/TinyDataset/never.json',
                     'HF/never/model.pt', 'data_cache/never/train.bin'):
            self.write(name, 'FAKE ASSET NEVER READ')
        actual_hash = contract.file_sha256
        observed = []

        def restricted(path, *, guard=None):
            rel = path.relative_to(self.root).as_posix()
            self.assertFalse(rel.startswith(('runs/', 'datasets/', 'HF/', 'data_cache/')))
            self.assertTrue(rel.endswith(('.py', '.bat', '.tsv')))
            observed.append(rel)
            return actual_hash(path, guard=guard)

        with mock.patch.object(contract, 'file_sha256', side_effect=restricted), \
                mock.patch.object(Path, 'rglob', side_effect=AssertionError('no following rglob')):
            pins = contract.execution_source_pins(self.root)
        self.assertEqual(set(pins), set(observed))
        self.assertIn('run100m.py', pins)
        self.assertIn(contract.NEW_DRIVER, pins)
        self.assertIn(contract.CONTRACT_MODULE, pins)
        self.assertIn('tinylm/model/fake_core.py', pins)
        self.assertNotIn('tinylm/model/ignored.txt', pins)
        self.assertEqual(pins['tinylm/model/fake_core.py'],
                         hashlib.sha256(core.read_bytes()).hexdigest().upper())

    def test_source_guard_cancels_before_canonical_parse_or_any_hash(self):
        with mock.patch.object(smoke_module, 'parse_smoke_module') as parse, \
                mock.patch.object(contract, 'file_sha256') as hashed, \
                self.assertRaises(Cancelled):
            contract.execution_source_pins(
                self.root, guard=mock.Mock(side_effect=Cancelled('before parse')))
        parse.assert_not_called()
        hashed.assert_not_called()

    def test_guard_propagates_to_each_hash_and_precedes_parse_and_hash(self):
        events = []
        original_parse, original_hash = smoke_module.parse_smoke_module, contract.file_sha256

        def guard():
            events.append('guard')

        def parse(*a, **k):
            self.assertEqual(events[-1], 'guard')
            events.append('parse')
            return original_parse(*a, **k)

        def hashed(path, *, guard=None):
            self.assertEqual(events[-1], 'guard')
            self.assertIs(guard, callback)
            events.append('hash')
            return original_hash(path, guard=guard)

        callback = guard
        with mock.patch.object(smoke_module, 'parse_smoke_module', side_effect=parse), \
                mock.patch.object(contract, 'file_sha256', side_effect=hashed):
            pins = contract.execution_source_pins(self.root, guard=callback)
        self.assertEqual(events.count('hash'), len(pins))
        self.assertGreater(events.count('guard'), len(pins) * 2)

    def test_guard_cancellation_after_parse_prevents_all_hashes(self):
        parsed = [False]
        real_parse = smoke_module.parse_smoke_module

        def parse(*a, **k):
            parsed[0] = True
            return real_parse(*a, **k)

        def guard():
            if parsed[0]:
                raise Cancelled('cancel before any source hash')

        with mock.patch.object(smoke_module, 'parse_smoke_module', side_effect=parse), \
                mock.patch.object(contract, 'file_sha256') as hashed, self.assertRaises(Cancelled):
            contract.execution_source_pins(self.root, guard=guard)
        hashed.assert_not_called()

    def test_missing_required_source_is_not_reported_as_complete(self):
        (self.root / contract.NEW_DRIVER).unlink()
        with self.assertRaises(ValueError):
            contract.execution_source_pins(self.root)

    def test_top_level_model_tree_link_rejected_before_target_stat_or_traversal(self):
        target = self.root / 'fake_protected_target'
        target.mkdir()
        (target / 'never.py').write_text('# fake target')
        link = self.root / 'tinylm'
        link.symlink_to(target, target_is_directory=True)
        guard, observed = self.deny_linked_target_access(link, target)
        with guard, self.assertRaises(ValueError):
            contract.execution_source_pins(self.root)
        self.assertEqual(observed, [])

    def test_nested_model_directory_link_rejected_before_target_stat_or_traversal(self):
        tree = self.root / 'tinylm'
        tree.mkdir()
        target = self.root / 'fake_protected_target'
        target.mkdir()
        link = tree / 'linked'
        link.symlink_to(target, target_is_directory=True)
        guard, observed = self.deny_linked_target_access(link, target)
        with guard, self.assertRaises(ValueError):
            contract.execution_source_pins(self.root)
        self.assertEqual(observed, [])

    def test_model_source_file_link_rejected_before_following_target(self):
        target = self.write('fake_protected_target.py', '# not source')
        link = self.root / 'tinylm/linked.py'
        link.parent.mkdir()
        link.symlink_to(target)
        guard, observed = self.deny_linked_target_access(link, target)
        with guard, self.assertRaises(ValueError):
            contract.execution_source_pins(self.root)
        self.assertEqual(observed, [])

    def test_canonical_file_link_rejected_before_parser_or_target_metadata(self):
        target = self.write('fake_protected_target.bat', BAT)
        link = self.root / contract.CANONICAL_SOURCE
        link.unlink()
        link.symlink_to(target)
        guard, observed = self.deny_linked_target_access(link, target)
        with guard, mock.patch.object(smoke_module, 'parse_smoke_module') as parse, \
                self.assertRaises(ValueError):
            contract.execution_source_pins(self.root)
        self.assertEqual(observed, [])
        parse.assert_not_called()

    def test_canonical_ancestor_link_rejected_before_descendant_lstat(self):
        # lstat(link/child) follows the ancestor link too. Only lstat(link)
        # itself is safe before rejecting that ancestor.
        target = self.root / 'fake_protected_scripts'
        (self.root / 'scripts').rename(target)
        link = self.root / 'scripts'
        link.symlink_to(target, target_is_directory=True)
        guard, observed = self.deny_linked_target_access(link, target)
        with guard, mock.patch.object(smoke_module, 'parse_smoke_module') as parse, \
                self.assertRaises(ValueError):
            contract.execution_source_pins(self.root)
        self.assertEqual(observed, [])
        parse.assert_not_called()



class ModernReceiptTests(Fixture):
    """Normalized aliases use only temporary sources/raw/receipts."""
    def setUp(self):
        super().setUp()
        import json
        from scripts import check_smoke_diag
        self.json = json
        self.check = check_smoke_diag
        self.session_id = 'fixture'
        self.target = contract.destinations(self.root, self.session_id)
        self.log = self.write(
            'smoketest_logs/202610190000_smoke_codex_fixture_abcdef0.txt', '')
        self.actions0 = smoke_module.parse_smoke_module(
            self.root / contract.CANONICAL_SOURCE, log_name=self.target['log_name'])
        self.actions1, edits = contract.adapt_actions(
            self.actions0, driver=contract.NEW_DRIVER,
            contract_args=['--mode', 'contract', '--session-id', self.session_id])
        self.py = self.actions0[0].argv[0]
        self.summary = [self.py, 'scripts/summarize_smoke.py', '--log', str(self.log)]
        self.make_raw(self.actions1, self.summary)
        env = dict(TINYLM_DIR=str(self.target['runtime']),
                   TINYLM_HF=str(self.target['runtime'] / 'HF'),
                   HF_HOME=str(self.target['runtime'] / 'HF'),
                   TL_OUTDIR='smoketest_logs', TL_LOGNAME=self.target['log_name'],
                   TL_NOPAUSE='1', TL_WANDB_AUTO='0', WANDB_MODE='disabled',
                   WANDB_DISABLED='true', HF_HUB_OFFLINE='1',
                   HF_DATASETS_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        self.write(contract.NEW_DRIVER, 'ENVIRONMENT_KEYS = ' + repr(tuple(env)) + '\n')
        pins = contract.execution_source_pins(self.root)
        self.data = dict(
            schema=contract.NEW_SCHEMA, profile_id=contract.NEW_PROFILE_ID,
            session_id=self.session_id, source=contract.CANONICAL_SOURCE,
            driver=contract.NEW_DRIVER,
            runtime=self.target['runtime'].relative_to(self.root).as_posix(),
            log_name=self.target['log_name'], raw_log_directory='smoketest_logs',
            source_sha256=pins[contract.CANONICAL_SOURCE],
            driver_sha256=pins[contract.NEW_DRIVER],
            contract_module_sha256=pins[contract.CONTRACT_MODULE],
            action_count=len(self.actions0),
            child_count=sum(a.kind == 'run' and '--' in a.argv for a in self.actions0),
            training_count=sum('run100m.py' in a.argv for a in self.actions0),
            action_manifest=[asdict(a) for a in self.actions1],
            substitutions=edits, source_pins_before=pins,
            source_pins_after=dict(pins), source_pins_unchanged=True,
            receipts=[dict(index=i, kind=a.kind, line=a.line,
                original_argv=list(o.argv), executed_argv=list(a.argv),
                seconds=a.seconds, status='COMPLETE', returncode=0,
                child=a.kind == 'run' and '--' in a.argv,
                duration_sec=float(a.seconds) if a.kind == 'sleep' else 1.,
                error=None, termination=[],
                process_started=a.kind == 'run')
                for i, (o, a) in enumerate(zip(self.actions0, self.actions1))],
            summary_command=[self.py, 'scripts/runlog.py', '--name',
                             self.target['log_name'], '--', *self.summary],
            summary_returncode=0, summary_status='COMPLETE',
            summary_receipt=dict(status='COMPLETE', returncode=0,
                                 error=None, process_started=True, duration_sec=1.),
            failed_calls=0, failed_run_calls=0, returncode=0, complete=True,
            snapshot_errors=[], safety_errors=[], interrupted=False, timed_out=False,
            original_synthetic_before={}, original_synthetic_after={},
            original_synthetic_before_complete=True,
            original_synthetic_after_complete=True, original_synthetic_unchanged=True,
            environment=env, started_at='2026-10-19T00:00:00+00:00',
            finished_at='2026-10-19T00:01:00+00:00',
            deadline_utc='2026-10-19T00:20:00+00:00',
            max_wall_sec=1200, whole_sec=60.,
        )
        success_state = dict(creation_attempted=True, launch_state='OWNED',
            unsafe_process_state=False, interrupted_during_cleanup=False,
            cleanup_duration_sec=0., launch_handler_errors=[],
            launch_restore_interrupted=False, deferred_launch_signals=[],
            preserved_ignored_launch_signals=[], termination=[])
        for receipt in self.data['receipts']:
            if receipt['kind'] == 'run':
                receipt.update(success_state)
        self.data['summary_receipt'].update(success_state)
        self.refresh_raw_hash()
        self.save()

    def make_raw(self, actions, summary):
        blocks = []
        for action in actions:
            if action.kind != 'run' or '--' not in action.argv:
                continue
            child = list(action.argv[action.argv.index('--') + 1:])
            body = ('\n'.join(contract.CODEX_ITEMS)
                    if contract.CODEX_CHECKER in child else 'field marker')
            blocks.append('[runlog] cmd=' + ' '.join(child) + '\n' + body
                          + '\n[runlog] 종료코드 0 소요 0분')
        blocks.append('[runlog] cmd=' + ' '.join(summary)
                      + '\n스모크 종료코드 요약: 실패 0개; 총 에러 0건'
                      + '\n[runlog] 종료코드 0 소요 0분')
        self.log.write_text('\n'.join(blocks), encoding='utf-8')

    def refresh_raw_hash(self):
        self.data.update(
            log=self.log.relative_to(self.root).as_posix(),
            raw_logs=[self.log.relative_to(self.root).as_posix()],
            log_bytes=self.log.stat().st_size,
            log_sha256=contract.file_sha256(self.log))

    def save(self):
        path = self.target['report']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.json.dumps(self.data), encoding='utf-8')

    def validate(self):
        return contract.validate_modern_adaptation(
            self.root, self.root / contract.CANONICAL_SOURCE,
            self.log, self.check.log_records(self.log))

    def reject(self):
        self.save()
        with self.assertRaises((ValueError, TypeError, KeyError, IndexError, OSError)):
            self.validate()

    def test_valid_normalized_receipt_and_only_two_aliases(self):
        aliases = self.validate()
        self.assertEqual(set(aliases), {'check_handoff.py', 'check_smoke.py'})
        self.assertEqual(aliases['check_handoff.py'][2], contract.CODEX_ITEMS)
        self.assertEqual(self.check.log_blocks(self.log)['codex_smoke.py'][1], 0)

    def test_reader_never_inspects_original_runtime_or_model_payloads(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            relative = Path(path).relative_to(self.root).as_posix()
            self.assertFalse(relative.startswith(('runs/', 'data_cache/', 'HF/')))
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', guarded):
            self.assertEqual(len(self.validate()), 2)

    def test_generic_source_driver_helper_or_raw_byte_change_is_rejected(self):
        for name in (contract.CANONICAL_SOURCE, contract.NEW_DRIVER,
                     contract.CONTRACT_MODULE, self.log.relative_to(self.root).as_posix()):
            with self.subTest(name=name):
                path = self.root / name
                before = path.read_bytes()
                path.write_bytes(before + b'\nchanged')
                with self.assertRaises(ValueError):
                    self.validate()
                path.write_bytes(before)

    def test_identity_counts_and_booleans_fail_closed(self):
        import copy
        pristine = copy.deepcopy(self.data)
        mutations = [
            ('schema', 'OTHER'), ('profile_id', 'OTHER'), ('session_id', 'other'),
            ('runtime', 'runs'), ('log_name', 'smoke'), ('log', '../raw.txt'),
            ('raw_logs', []), ('raw_log_directory', 'test_result'),
            ('log_bytes', True), ('action_count', True), ('training_count', 99),
            ('child_count', 0), ('source_sha256', '0' * 64),
            ('driver_sha256', '0' * 64), ('contract_module_sha256', '0' * 64),
            ('source_pins_before', {}), ('source_pins_after', {}),
            ('source_pins_unchanged', False), ('substitutions', []),
            ('action_manifest', []), ('failed_calls', True),
            ('failed_run_calls', 1), ('returncode', False), ('complete', False),
            ('summary_status', 'NOT_RUN'), ('summary_returncode', 1),
            ('interrupted', True), ('timed_out', True),
            ('snapshot_errors', ['missing']), ('safety_errors', ['unknown child']),
        ]
        for key, value in mutations:
            with self.subTest(key=key):
                self.data = copy.deepcopy(pristine)
                self.data[key] = value
                self.reject()

    def test_action_receipts_cannot_hide_missing_order_errors_or_unknown_creation(self):
        import copy
        pristine = copy.deepcopy(self.data)
        for key, value in (
                ('index', 99), ('line', -1), ('kind', 'sleep'),
                ('seconds', True), ('status', 'NOT_RUN'), ('returncode', False),
                ('child', True), ('duration_sec', float('nan')),
                ('duration_sec', -1.), ('error', 'failure'),
                ('unsafe_process_state', True), ('process_started', None),
                ('original_argv', ['FAKE']), ('executed_argv', ['FAKE'])):
            with self.subTest(key=key, value=value):
                self.data = copy.deepcopy(pristine)
                self.data['receipts'][0][key] = value
                self.reject()
        self.data = copy.deepcopy(pristine)
        self.data['receipts'].reverse()
        self.reject()
        self.data = copy.deepcopy(pristine)
        self.data['receipts'].pop()
        self.reject()

    def test_raw_missing_duplicate_wrong_order_or_nonzero_cannot_be_rehashed_into_pass(self):
        raw = self.log.read_text()
        mutations = [
            raw.replace('[runlog] 종료코드 0', '[runlog] 종료코드 1', 1),
            raw.replace('[runlog] 종료코드 0', '[runlog] 종료코드 -15', 1),
            raw + '\n[runlog] cmd=python scripts/extra.py\n[runlog] 종료코드 0 소요 0분',
            '[runlog] cmd=python scripts/unfinished.py\n' + raw,
            raw.replace('scripts/check_handoff_codex.py', 'scripts/not_approved.py', 1),
            raw.replace('총 에러 0건', '총 에러 1건'),
            raw.replace('scripts/summarize_smoke.py', 'scripts/other_summary.py'),
        ]
        for changed in mutations:
            with self.subTest(changed=changed[-70:]):
                self.log.write_text(changed, encoding='utf-8')
                self.refresh_raw_hash()
                self.reject()
        self.log.write_text(raw, encoding='utf-8')

    def test_summary_receipt_and_wrapper_cannot_be_omitted_or_unknown(self):
        import copy
        pristine = copy.deepcopy(self.data)
        for key, value in (('summary_command', []), ('summary_receipt', None)):
            self.data = copy.deepcopy(pristine)
            self.data[key] = value
            self.reject()
        for key, value in (('status', 'TOOL_ERROR'), ('returncode', False),
                           ('error', 'bad'), ('process_started', None),
                           ('unsafe_process_state', True)):
            self.data = copy.deepcopy(pristine)
            self.data['summary_receipt'][key] = value
            self.reject()

    def test_success_cannot_coexist_with_unknown_or_interrupted_process_state(self):
        import copy
        pristine = copy.deepcopy(self.data)
        for owner in ('action', 'summary'):
            for key, value in (
                    ('launch_state', 'UNKNOWN'), ('creation_attempted', False),
                    ('unsafe_process_state', None), ('interrupted_during_cleanup', True),
                    ('cleanup_duration_sec', 1.), ('launch_handler_errors', ['restore error']),
                    ('launch_restore_interrupted', True), ('deferred_launch_signals', [2]),
                    ('termination', ['CLEANUP_ERROR:missing']),
                    ('preserved_ignored_launch_signals', [True]),
                    ('preserved_ignored_launch_signals', [2, 2])):
                with self.subTest(owner=owner, key=key):
                    self.data = copy.deepcopy(pristine)
                    receipt = (self.data['receipts'][0] if owner == 'action'
                               else self.data['summary_receipt'])
                    receipt[key] = value
                    self.reject()
            self.data = copy.deepcopy(pristine)
            receipt = (self.data['receipts'][0] if owner == 'action'
                       else self.data['summary_receipt'])
            receipt.pop('unsafe_process_state')
            self.reject()

    def test_pause_and_total_sequential_wall_cannot_be_underreported(self):
        import copy
        pristine = copy.deepcopy(self.data)
        pause = next(r for r in self.data['receipts'] if r['kind'] == 'sleep')
        pause['duration_sec'] = 0.
        self.reject()
        self.data = copy.deepcopy(pristine)
        self.data['whole_sec'] = 1.
        self.reject()
        self.data = copy.deepcopy(pristine)
        self.data['summary_receipt']['duration_sec'] = float('nan')
        self.reject()

    def test_preservation_maps_are_scope_bound_without_reopening_assets(self):
        import copy
        pristine = copy.deepcopy(self.data)
        for key in ('original_synthetic_before_complete',
                    'original_synthetic_after_complete', 'original_synthetic_unchanged'):
            self.data = copy.deepcopy(pristine)
            self.data[key] = False
            self.reject()
        for value in ({'runs/ckpt/real_parent.pt': 'A' * 64},
                      {'data_cache/other/train.bin': 'A' * 64},
                      {'../outside': 'A' * 64},
                      {'runs/logs/tiny_synthetic_a.json': 'bad'}):
            self.data = copy.deepcopy(pristine)
            self.data['original_synthetic_before'] = value
            self.data['original_synthetic_after'] = dict(value)
            self.reject()
        self.data = copy.deepcopy(pristine)
        self.data['original_synthetic_before'] = {'runs/logs/tiny_synthetic_a.json': 'A' * 64}
        self.reject()
        self.data['original_synthetic_after'] = dict(self.data['original_synthetic_before'])
        self.save()
        self.assertEqual(len(self.validate()), 2)

    def test_environment_stays_isolated_and_metadata_cannot_include_secret_keys(self):
        import copy
        pristine = copy.deepcopy(self.data)
        for key, value in (('TINYLM_DIR', '/other'), ('HF_HOME', '/other'),
                           ('WANDB_MODE', 'online'), ('HF_HUB_OFFLINE', '0'),
                           ('ACCESS_TOKEN', 'secret')):
            self.data = copy.deepcopy(pristine)
            self.data['environment'][key] = value
            self.reject()
        self.data = copy.deepcopy(pristine)
        self.data['environment'][5] = 'not a string key'
        self.reject()

    def test_wall_and_aware_absolute_deadline_are_required(self):
        import copy
        pristine = copy.deepcopy(self.data)
        for key, value in (
                ('started_at', '2026-10-19T00:00:00'),
                ('finished_at', '2026-10-19T00:21:00+00:00'),
                ('deadline_utc', 'bad'), ('whole_sec', float('nan')),
                ('whole_sec', 1201.), ('whole_sec', True),
                ('max_wall_sec', True), ('max_wall_sec', 0)):
            self.data = copy.deepcopy(pristine)
            self.data[key] = value
            self.reject()

    def test_valid_float_wall_matches_producer_without_inventing_sixty_second_floor(self):
        self.data.update(max_wall_sec=30.5, whole_sec=20.)
        self.save()
        self.assertEqual(len(self.validate()), 2)

    def test_actual_writer_report_roundtrip_with_mock_children_only(self):
        from scripts import codex_smoke as writer
        from scripts import test_codex_smoke as fixture_module
        fixture = fixture_module.TemporaryRepo()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.write(writer.NEW_DRIVER,
                      'ENVIRONMENT_KEYS = ' + repr(writer.ENVIRONMENT_KEYS) + '\n')

        def launch(argv, **kwargs):
            env = kwargs['env']
            path = fixture.root / 'smoketest_logs' / (
                env['TL_STAMP'] + '_' + env['TL_LOGNAME'] + '_nogit.txt')
            with path.open('a', encoding='utf-8') as stream:
                if '--' in argv:
                    child = argv[argv.index('--') + 1:]
                    stream.write('[runlog] cmd=' + ' '.join(child) + '\n')
                    if contract.CODEX_CHECKER in child:
                        stream.write('\n'.join(contract.CODEX_ITEMS) + '\n')
                    elif 'scripts/summarize_smoke.py' in child:
                        stream.write('스모크 종료코드 요약: 실패 0개; 총 에러 0건\n')
                    else:
                        stream.write('field marker\n')
                    stream.write('[runlog] 종료코드 0 소요 0분\n')
                else:
                    stream.write('[note] canonical fixture note\n')
            return fixture_module.FakeProcess(fixture.clock)

        code, _ = fixture.full(launcher=launch, wall=1200)
        self.assertEqual(code, 0)
        data = fixture.report()
        self.assertIs(type(data['max_wall_sec']), float)
        path = fixture.root / data['log']
        aliases = contract.validate_modern_adaptation(
            fixture.root, fixture.root / contract.CANONICAL_SOURCE,
            path, self.check.log_records(path))
        self.assertEqual(set(aliases), {'check_handoff.py', 'check_smoke.py'})

    def test_report_link_is_rejected_without_opening_target(self):
        path = self.target['report']
        target = self.write('fake_forbidden_receipt', 'not a receipt')
        path.unlink()
        path.symlink_to(target)
        original = Path.open
        def guarded(current, *args, **kwargs):
            self.assertNotEqual(Path(current), target)
            return original(current, *args, **kwargs)
        with mock.patch.object(Path, 'open', guarded), self.assertRaises(ValueError):
            self.validate()

    def test_bad_session_and_multiple_modern_drivers_are_rejected(self):
        raw = self.log.read_text()
        for changed in (
                raw.replace('--session-id fixture', '--session-id ../outside'),
                raw.replace('--mode contract', '--mode full'),
                raw + '\n[runlog] cmd=python ' + contract.HISTORICAL_DRIVER
                    + '\n[runlog] 종료코드 0 소요 0분'):
            self.log.write_text(changed, encoding='utf-8')
            with self.assertRaises(ValueError):
                self.validate()

    def test_canonical_log_is_not_an_alias_even_without_a_receipt(self):
        self.log.write_text('[runlog] cmd=python scripts/check_handoff.py\nmarker'
                            '\n[runlog] 종료코드 0 소요 0분', encoding='utf-8')
        self.target['report'].unlink()
        self.assertIsNone(self.validate())

    def test_historical_only_accepts_exact_bound_manifest_and_raw(self):
        from dataclasses import replace
        self.write(contract.HISTORICAL_DRIVER, '# historical fixture\n')
        self.log = self.write(contract.HISTORICAL_RAW, '')
        canonical = smoke_module.parse_smoke_module(
            self.root / contract.CANONICAL_SOURCE, log_name='smoke')
        adapted = []
        for action in canonical:
            argv = list(action.argv)
            if action.kind == 'run' and '--' in argv:
                at = argv.index('--')
                if argv[at + 1:] == [self.py, 'scripts/check_handoff.py']:
                    argv[at + 1:] = [self.py, '-I', '-B', contract.CODEX_CHECKER]
                elif argv[at + 1:] == [self.py, 'scripts/check_smoke.py']:
                    argv[at + 1:] = [self.py, '-B', '-X', 'utf8',
                        contract.HISTORICAL_DRIVER, '--contract', '--root',
                        str(self.root / contract.HISTORICAL_RUNTIME)]
            adapted.append(replace(action, argv=tuple(argv)))
        summary = [self.py, '-B', '-X', 'utf8', 'scripts/summarize_smoke.py']
        self.make_raw(adapted, summary)
        proof = dict(source=contract.CANONICAL_SOURCE,
            canonical_sha256=contract.file_sha256(self.root / contract.CANONICAL_SOURCE),
            output_root=str(self.root / contract.HISTORICAL_RUNTIME),
            adaptations=['legacy_handoff_to_codex', 'contract_reads_fresh_isolated_logs'],
            canonical_actions=len(canonical), actual_actions=len(adapted),
            action_manifest=[asdict(a) for a in adapted])
        path = self.write(contract.HISTORICAL_RUNTIME + '/isolation.json',
                          self.json.dumps(proof))
        with mock.patch.object(contract, 'HISTORICAL_DRIVER_SHA',
                               contract.file_sha256(self.root / contract.HISTORICAL_DRIVER)), \
                mock.patch.object(contract, 'HISTORICAL_RAW_SHA', contract.file_sha256(self.log)), \
                mock.patch.object(contract, 'HISTORICAL_ISOLATION_SHA', contract.file_sha256(path)):
            self.assertEqual(len(self.validate()), 2)
            proof['action_manifest'][0]['argv'] = list(proof['action_manifest'][0]['argv']) + ['EXTRA']
            path.write_text(self.json.dumps(proof))
            with self.assertRaises(ValueError):
                self.validate()



if __name__ == '__main__':
    unittest.main()
