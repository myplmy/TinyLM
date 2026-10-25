"""Synthetic CPU/control tests only; no TinyLM model, real batch, CP or CUDA."""
from __future__ import annotations

import copy
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import tinylm
import torch
from tinylm.train import muon
from scripts import diag_p102a_fused_ce as diag

OPTIONS = dict(lr=2e-4, momentum=.95, nesterov=True, ns_steps=5,
               weight_decay=0., scale_mode='rms')
TOLERANCE = dict(atol=2e-6, rtol=1e-5)


class Journal:
    def __init__(self):
        self.rows = []

    def append(self, value):
        self.rows.append(value)

    def close(self):
        pass


class ControlledGuard:
    def __init__(self):
        self.expired = False
        self.checks = []

    def check(self, stage):
        self.checks.append(stage)
        if self.expired:
            raise TimeoutError('synthetic expired clock at ' + stage)


def cpu_capture():
    """Tiny nonzero Parameter/Muon fixtures; never construct a TinyLM model."""
    initial = {}
    capture = {key: {} for key in (*diag.FULL_FIELDS, *diag.MATRIX_FIELDS, 'optimizer', 'options')}
    for index in range(diag.ALL_COUNT):
        name = 'synthetic.' + str(index)
        is_matrix = index < diag.MATRIX_COUNT
        initial[name] = torch.tensor([[.1, -.2], [.3, .4]]) if is_matrix else torch.tensor([.1])
        gradient = torch.tensor([[.2, -.1], [.05, .4]]) if is_matrix else torch.tensor([.2])
        capture['raw'][name] = gradient.clone()
        capture['clipped'][name] = gradient.clone()
        if is_matrix:
            replay = diag.trace.replay_one(torch, muon, initial[name], gradient,
                OPTIONS, device='cpu')
            capture['options'][name] = dict(OPTIONS)
            for key, source in (('ns_input', 'ns_input'), ('ns_output', 'ns_output'),
                                ('updated', 'weight'), ('buffers', 'buffer')):
                capture[key][name] = replay[source]
            capture['parameters'][name] = capture['updated'][name]
            capture['optimizer']['muon:' + name + ':buf'] = capture['buffers'][name]
        else:
            capture['parameters'][name] = initial[name] - .001
            for slot in ('step', 'exp_avg', 'exp_avg_sq'):
                capture['optimizer']['adamw:' + name + ':' + slot] = torch.tensor(1.)
    capture.update(update=dict(all_parameter_count=diag.ALL_COUNT,
        non_none_gradient_count=diag.ALL_COUNT, none_gradient_names=[], loss=3., preclip_norm=.4),
        initial_rng={'synthetic': 1}, final_rng={'synthetic': 2})
    return initial, capture


def report_fixture():
    comparisons = {}
    for key in (*diag.FULL_FIELDS, *diag.MATRIX_FIELDS, 'optimizer'):
        count = diag.ALL_COUNT if key in diag.FULL_FIELDS else diag.MATRIX_COUNT
        if key == 'optimizer':
            count = diag.MATRIX_COUNT + 3 * (diag.ALL_COUNT - diag.MATRIX_COUNT)
        comparisons[key] = dict(close=True, tensors=count)
    for key in ('loss', 'preclip_norm'):
        comparisons[key] = dict(close=True)
    matrix = dict(identical_gradient_control=dict(exact=True),
        actual_reproduction={label: dict(exact=True) for label in ('reference', 'candidate')})
    replay = dict(complete=True, matrix_count=diag.MATRIX_COUNT,
        same_gradient_controls_exact=True, actual_updates_reproduced_exactly=True,
        matrices={'synthetic.' + str(i): copy.deepcopy(matrix) for i in range(diag.MATRIX_COUNT)})
    pair = dict(close=True, comparisons=comparisons, replay=replay)
    return dict(schema=diag.SCHEMA, tag=diag.TAG_PREFIX + 'cpu_fixture', checkpoint_writes=0,
        actual_process_exit='PENDING_CALLER_CHECK',
        canaries=dict(complete=True, close=True), errors=[], cleanup_errors=[],
        updates=[dict(precision=p, ce_backend=b) for p in diag.PRECISIONS for b in diag.BACKENDS],
        pairs={p: {b: copy.deepcopy(pair) for b in diag.BACKENDS[1:]} for p in diag.PRECISIONS})


class DriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')):
            cls.initial, cls.capture = cpu_capture()

    def arguments(self, **values):
        args = dict(execute=True, check_only=False, tag=diag.TAG_PREFIX + 'cpu_fixture',
            deadline='2099-01-01T00:00:00+00:00', max_wall_sec=600,
            source_sha256='X', dependency_sha256='Y')
        args.update(values)
        return SimpleNamespace(**args)

    def test_future_window_requires_explicit_aware_deadline_and_wall(self):
        now = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
        historical = (diag.old.HARD_STOP, diag.trace.HARD_STOP)
        args = self.arguments(deadline=(now + timedelta(minutes=10)).isoformat())
        self.assertEqual(diag.validate_execution(args, now), now + timedelta(minutes=10))
        self.assertEqual(historical, (diag.old.HARD_STOP, diag.trace.HARD_STOP))
        for changes in (dict(deadline=None), dict(deadline='2026-10-24T11:00:00'),
                        dict(deadline=now.isoformat()), dict(max_wall_sec=None),
                        dict(max_wall_sec=59), dict(max_wall_sec=1201),
                        dict(deadline=(now + timedelta(seconds=599)).isoformat()),
                        dict(execute=False), dict(check_only=True)):
            values = dict(vars(args), **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                diag.validate_execution(SimpleNamespace(**values), now)

    def test_guard_checks_both_monotonic_and_calendar_clocks_without_old_guard(self):
        now = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
        with patch.object(diag.time, 'perf_counter', return_value=1.), \
                patch.object(diag.old, 'Guard', side_effect=AssertionError('historical guard forbidden')):
            guard = diag.Guard(now + timedelta(minutes=2), 60)
        with patch.object(diag.old, 'utc_now', return_value=now), \
                patch.object(diag.time, 'perf_counter', return_value=60.9):
            guard.check('within reservation')
        with patch.object(diag.old, 'utc_now', return_value=now), \
                patch.object(diag.time, 'perf_counter', return_value=61.), self.assertRaises(TimeoutError):
            guard.check('wall expired')
        with patch.object(diag.old, 'utc_now', return_value=guard.deadline), \
                patch.object(diag.time, 'perf_counter', return_value=2.), self.assertRaises(TimeoutError):
            guard.check('calendar expired')

    def test_fresh_namespace_cannot_escape_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tag = diag.TAG_PREFIX + 'fixture_01'
            target = diag.output_path(tag, root)
            self.assertEqual(target, root / 'test_result/evidence' / tag)
            target.mkdir(parents=True)
            (target / 'partial.json').write_text('historical negative', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                diag.output_path(tag, root)
            self.assertEqual((target / 'partial.json').read_text(encoding='utf-8'), 'historical negative')
            for value in ('../escape', diag.TAG_PREFIX + '../escape', diag.TAG_PREFIX, 'legacy_tag'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    diag.output_path(value, root)

    def test_missing_receipts_block_before_gpu_query_or_namespace_creation(self):
        args = self.arguments()
        with patch.object(diag.old, 'gpu_admission', side_effect=AssertionError('GPU forbidden')), \
                patch.object(diag, 'output_path', side_effect=AssertionError('write forbidden')):
            with self.assertRaisesRegex(ValueError, 'source-only receipt'):
                diag.run(args, {})
            args.source_sha256 = diag.old.identity({})
            with patch.object(diag, 'dependency_metadata', return_value={'ready': False}), \
                    self.assertRaisesRegex(ValueError, 'dependency receipt'):
                diag.run(args, {})

    def test_source_only_fresh_process_imports_no_torch_or_asset_engine(self):
        code = """
import sys
from scripts import diag_p102a_fused_ce as d
assert 'torch' not in sys.modules
assert 'scripts.diag_p101a_sft_mtp' not in sys.modules
assert 'tinylm.train.fused_ce' not in sys.modules
assert d.main(['--check-only']) == 0
assert 'torch' not in sys.modules
assert 'scripts.diag_p101a_sft_mtp' not in sys.modules
assert 'tinylm.train.fused_ce' not in sys.modules
"""
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            capture_output=True, text=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['evidence'], 'STATIC_ONLY_NOT_KERNEL_PASS')
        for key in ('model_calls', 'cuda_calls', 'kernel_calls', 'asset_reads'):
            self.assertEqual(receipt[key], 0)
        self.assertEqual(len(receipt['source_sha256']), 64)
        self.assertEqual(len(receipt['dependency_sha256']), 64)
        self.assertIn('deadline', receipt['mandatory_execute_arguments'])

    def test_cli_has_no_execute_defaults_or_bypass_modes(self):
        for values in ([], ['--execute', '--check-only'], ['--execute'],
                       ['--check-only', '--skip-canary'], ['--check-only', '--skip-replay']):
            with self.subTest(values=values), redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit), \
                    patch.object(diag.old, 'gpu_admission', side_effect=AssertionError('GPU forbidden')):
                diag.main(values)

    def test_original_mask_denominator_and_backend_seam_reused(self):
        for backend in diag.BACKENDS:
            core = diag.HeadCore(backend)
            with patch.object(core.core, 'components', return_value=({1: 3.}, {1: 7})) as operation:
                self.assertEqual(core.components('m', 'h', 'y', 'segments', horizons=()), ({1: 3.}, {1: 7}))
                operation.assert_called_once_with('m', 'h', 'y', 'segments', horizons=(), chunk=64,
                    checkpoint_heads=True, ce_backend=backend)
            with self.assertRaisesRegex(ValueError, 'main-only'):
                core.components('m', 'h', 'y', 'segments', horizons=(2,))

    def test_full_capture_rejects_missing_gradients_and_optimizer_slots(self):
        diag.validate_capture(self.capture)
        for field in (*diag.FULL_FIELDS, *diag.MATRIX_FIELDS, 'options', 'optimizer'):
            capture = {key: dict(value) if isinstance(value, dict) else value
                       for key, value in self.capture.items()}
            capture[field].pop(next(iter(capture[field])))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'complete actual'):
                diag.validate_capture(capture)
        capture = copy.copy(self.capture)
        capture['raw'] = dict(capture['raw'])
        capture['raw'][next(iter(capture['raw']))] = None
        with self.assertRaisesRegex(ValueError, 'complete actual'):
            diag.validate_capture(capture)

    def test_complete157_comparison_includes_clip_adam_muon_and_shared_scope(self):
        report = diag.compare_pair(torch, self.capture, self.capture,
            dict(gradients_and_update=TOLERANCE, loss_and_norm=TOLERANCE))
        self.assertTrue(report['close'])
        for field in diag.FULL_FIELDS:
            self.assertEqual(report['comparisons'][field]['tensors'], diag.ALL_COUNT)
        self.assertEqual(report['comparisons']['optimizer']['tensors'], 301)
        changed = copy.copy(self.capture)
        changed['initial_rng'] = {'synthetic': 99}
        with self.assertRaisesRegex(ValueError, 'RNG'):
            diag.compare_pair(torch, self.capture, changed,
                dict(gradients_and_update=TOLERANCE, loss_and_norm=TOLERANCE))

    def test_all85_original_matrices_replay_exactly_on_synthetic_cpu(self):
        journal, report = Journal(), {}
        original_ns = muon._newton_schulz
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')):
            diag.replay_pair(torch, muon, self.initial, self.capture, self.capture,
                TOLERANCE, None, journal, report, device='cpu')
        self.assertTrue(report['complete'])
        self.assertTrue(report['same_gradient_controls_exact'])
        self.assertTrue(report['actual_updates_reproduced_exactly'])
        self.assertEqual(report['matrix_count'], 85)
        self.assertEqual(len(journal.rows), 85)
        self.assertIs(muon._newton_schulz, original_ns)
        self.assertFalse(torch.cuda.is_initialized())

    def test_replay_preserves_partial_matrix_failure_and_original_error(self):
        capture = copy.copy(self.capture)
        capture['updated'] = dict(capture['updated'])
        name = next(iter(capture['updated']))
        capture['updated'][name] = capture['updated'][name] + 1.
        journal, report = Journal(), {}
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')), \
                self.assertRaisesRegex(ValueError, 'exact actual-step'):
            diag.replay_pair(torch, muon, self.initial, self.capture, capture,
                TOLERANCE, None, journal, report, device='cpu')
        self.assertFalse(report['complete'])
        self.assertEqual(report['matrix_count'], 1)
        self.assertFalse(report['matrices'][name]['actual_reproduction']['candidate']['exact'])
        self.assertEqual(len(journal.rows), 1)

    def test_result_zero_and_empty_tables_never_suffice_for_success(self):
        result = report_fixture()
        self.assertEqual(diag.classify(result), ('NUMERICAL_PASS_NOT_ADOPTED', 0))
        for field in ('updates', 'pairs', 'canaries'):
            incomplete = copy.deepcopy(result)
            incomplete[field] = [] if field == 'updates' else {}
            incomplete['returncode'] = 0
            with self.subTest(field=field):
                self.assertEqual(diag.classify(incomplete)[1], 9)
        incomplete = copy.deepcopy(result)
        incomplete['updates'][-1] = dict(incomplete['updates'][0])
        self.assertEqual(diag.classify(incomplete)[1], 9)
        for path in ('comparisons', 'matrices'):
            incomplete = copy.deepcopy(result)
            pair = incomplete['pairs'][diag.PRECISIONS[0]][diag.BACKENDS[1]]
            if path == 'comparisons':
                pair[path] = {}
            else:
                pair['replay'][path] = {}
            with self.subTest(path=path):
                self.assertEqual(diag.classify(incomplete)[1], 9)

    def test_numeric_negative_and_any_prior_error_veto_positive(self):
        result = report_fixture()
        result['pairs'][diag.PRECISIONS[0]][diag.BACKENDS[1]]['close'] = False
        self.assertEqual(diag.classify(result), ('VALID_NUMERICAL_NEGATIVE_NOT_ADOPTED', 8))
        for field in ('errors', 'cleanup_errors'):
            positive = report_fixture()
            positive[field] = ['original failure retained']
            with self.subTest(field=field):
                self.assertEqual(diag.classify(positive)[1], 9)
                self.assertEqual(positive[field], ['original failure retained'])

    def test_matrix_schedules_six_fresh_arms_with_same_parent_groups_and_plan(self):
        sentinel = [object() for _ in range(13)]
        torch_fake, engine, muon_fake, cls, cfg, initial, initial_sha, pad, groups, plan, guard, journal, _ = sentinel
        guard = SimpleNamespace(check=lambda stage: None)
        result = dict(pairs={}, updates=[], tolerances={'gradients_and_update': TOLERANCE})
        calls = []
        def capture(*args):
            calls.append(args)
            return dict(update=dict(precision=args[9], ce_backend=args[8]))
        def replay(*args, **kwargs):
            args[8].update(complete=True)
        with patch.object(diag, 'released_capture', side_effect=capture), \
                patch.object(diag, 'capture_bytes', return_value=1), \
                patch.object(diag, 'compare_pair', return_value={'close': True}), \
                patch.object(diag, 'replay_pair', side_effect=replay), \
                patch.object(diag.old, 'gpu_admission', return_value={}), \
                patch.object(diag.trace, 'release_cuda'):
            diag.execute_matrix(torch_fake, engine, muon_fake, cls, cfg, initial, initial_sha,
                pad, groups, plan, guard, journal, result)
        self.assertEqual(len(calls), 6)
        self.assertEqual([(args[9], args[8]) for args in calls],
            [(p, b) for p in diag.PRECISIONS for b in diag.BACKENDS])
        for args in calls:
            self.assertIs(args[5], initial)
            self.assertIs(args[10], groups)
            self.assertIs(args[11], plan)

    def test_canary_failure_veto_keeps_independent_backend_and_precision_evidence(self):
        report, journal = {}, Journal()
        def operation(torch_arg, projected, table, labels, backend, precision, guard):
            if backend == 'liger' and precision == 'fp32_math':
                raise RuntimeError('original kernel error')
            return dict(loss=1., gradients={'g': torch.tensor([1.])})
        with patch.object(diag, 'kernel_canary_arm', side_effect=operation), \
                patch.object(diag.trace, 'release_cuda'), \
                patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')), \
                self.assertRaisesRegex(ValueError, 'mandatory official kernel canary'):
            diag.run_canaries(torch, dict(loss_and_norm=TOLERANCE, gradients_and_update=TOLERANCE),
                SimpleNamespace(check=lambda stage: None), journal, report)
        self.assertEqual(len(journal.rows), 6)
        self.assertEqual(report['precisions']['fp32_math']['liger']['error'], 'original kernel error')
        self.assertEqual(report['precisions']['bf16_eager']['cce_exact']['status'], 'COMPLETE')
        self.assertFalse(report['close'])

    def test_final_mutation_and_cleanup_error_cannot_erase_original_failure(self):
        result = dict(errors=[dict(type='RuntimeError', message='original kernel failure')])
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_initialized=lambda: True))
        with patch.object(diag.trace, 'release_cuda', side_effect=RuntimeError('live tensors')), \
                patch.object(diag, 'sources', return_value={'changed': 'source'}), \
                patch.object(diag, 'dependency_metadata', return_value={'changed': 'metadata'}), \
                patch.object(diag.old, 'digest', return_value='changed'):
            diag.audit_final(fake_torch, None, {}, {}, {'some/asset': 'original'}, result)
        self.assertEqual(result['errors'][0]['message'], 'original kernel failure')
        self.assertEqual(len(result['cleanup_errors']), 4)
        self.assertFalse(result['sources_unchanged'])
        self.assertFalse(result['dependencies_unchanged'])
        self.assertFalse(result['assets_unchanged'])
        self.assertEqual(diag.classify(result)[1], 9)

    def test_source_manifest_is_python_only_and_preserves_original_sources(self):
        hashes = diag.sources()
        self.assertTrue(all(name.endswith('.py') for name in hashes))
        self.assertFalse(any(name.startswith(('datasets/', 'HF/', 'runs/', 'data_cache/')) for name in hashes))
        self.assertIn('scripts/diag_p102a_streaming_head.py', hashes)
        self.assertIn('scripts/diag_p102a_head_muon_trace.py', hashes)
        self.assertIn('tinylm/train/fused_ce.py', hashes)
        self.assertEqual(diag.old.literal_tolerances()['gradients_and_update'], TOLERANCE)

    def test_wheel_record_provenance_works_without_direct_url_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'fixed.whl'
            record = 'example/a.py,sha256=original,12\nexample-1.dist-info/RECORD,,\n'
            with diag.zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('example-1.dist-info/RECORD', record)
            wheel = dict(path='fixed.whl', sha256=diag.old.digest(path))
            dist = SimpleNamespace(read_text=lambda name: record if name == 'RECORD' else None)
            metadata = diag.wheel_metadata(dist, wheel, root)
            self.assertTrue(metadata['archive_matches'])
            self.assertTrue(metadata['payload_records_match'])
            dist.read_text = lambda name: record.replace('original', 'changed')
            self.assertFalse(diag.wheel_metadata(dist, wheel, root)['payload_records_match'])
            wrong_archive = dict(wheel, sha256='WRONG')
            self.assertFalse(diag.wheel_metadata(dist, wrong_archive, root)['archive_matches'])

    def test_installed_source_verifier_rejects_modified_python_payload_on_cpu(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            distributions, metadata = {}, {'packages': {}}
            for name, namespace in (('liger-kernel', 'liger_kernel'), ('cut-cross-entropy', 'cut_cross_entropy')):
                relative = namespace + '/example.py'
                path = root / relative
                path.parent.mkdir()
                path.write_text('synthetic = 1\n', encoding='utf-8')
                digest = diag.old.digest(path)
                class Entry(str):
                    pass
                entry = Entry(relative)
                entry.hash = SimpleNamespace(mode='sha256',
                    value=diag.base64.urlsafe_b64encode(bytes.fromhex(digest)).decode('ascii').rstrip('='))
                distributions[name] = SimpleNamespace(files=[entry], locate_file=lambda item: root / item)
                metadata['packages'][name] = {'prepared_python_source_files': 1}
            with patch.object(diag.importlib.metadata, 'distribution', side_effect=lambda name: distributions[name]):
                self.assertTrue(all(row['unchanged'] for row in diag.verify_installed_sources(metadata).values()))
                (root / 'liger_kernel/example.py').write_text('synthetic = 2\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'differs from pinned RECORD'):
                    diag.verify_installed_sources(metadata)

    def test_complete_finite_canary_mismatch_is_numeric_negative_not_api_error(self):
        report = {}
        def operation(torch_arg, projected, table, labels, backend, precision, guard):
            return dict(loss=1. if backend == 'reference' else 2., gradients={'g': torch.tensor([1.])})
        with patch.object(diag, 'kernel_canary_arm', side_effect=operation), \
                patch.object(diag.trace, 'release_cuda'), \
                patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')), \
                self.assertRaises(diag.NumericalCanaryNegative):
            diag.run_canaries(torch, dict(loss_and_norm=TOLERANCE, gradients_and_update=TOLERANCE),
                ControlledGuard(), Journal(), report)
        self.assertTrue(report['complete'])
        self.assertFalse(report['close'])
        result = dict(canaries=report, canary_negative={'message': 'strict mismatch'},
            updates=[], pairs={}, assets_before=None)
        self.assertEqual(diag.classify(result)[1], 8)
        result['errors'] = ['real API error also occurred']
        self.assertEqual(diag.classify(result)[1], 9)

    def test_actual_run_arm_preserves_step_error_when_clear_quant_also_fails(self):
        parameters = {'synthetic.' + str(i): torch.nn.Parameter(torch.ones(2, 2))
                      for i in range(diag.ALL_COUNT)}
        class FakeModel:
            def load_state_dict(self, initial, strict):
                pass
            def set_anneal(self, value):
                pass
            def train(self):
                pass
            def cuda(self):
                return self
            def named_parameters(self):
                return parameters.items()
            def clear_quant(self):
                raise OSError('cleanup quant failed')
        values = list(parameters.values())
        opts = (SimpleNamespace(state={}, param_groups=[{'params': values[85:]}]),
                SimpleNamespace(state={}, param_groups=[{'params': values[:85]}]))
        engine = SimpleNamespace(state_fingerprint=lambda model: 'initial')
        options = {name: dict(OPTIONS) for name in list(parameters)[:85]}
        with patch.object(diag.old, 'gpu_admission', return_value={}), \
                patch.object(diag, 'fresh_optimizers', return_value=opts), \
                patch.object(diag.trace, 'matrix_options', return_value=options), \
                patch.object(diag.trace, 'private_muon_step', return_value=lambda: None), \
                patch.object(diag.old, 'rng_identity', return_value={}), \
                patch.object(diag.old, 'one_update', side_effect=ValueError('primary step failed')), \
                patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')), \
                self.assertRaisesRegex(ValueError, 'primary step failed') as caught:
            diag.run_arm(torch, engine, muon, lambda cfg: FakeModel(), SimpleNamespace(), {},
                'initial', 0, 'reference', 'fp32_math', [], {}, ControlledGuard(), Journal(), 0)
        record = diag.error_record(caught.exception, 'runtime')
        self.assertEqual(record['message'], 'primary step failed')
        self.assertEqual(record['cleanup_errors'][0]['message'], 'cleanup quant failed')

    def test_execute_preparation_and_metadata_delays_consume_the_original_wall_budget(self):
        now = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
        for stage in ('source', 'metadata'):
            clock = [0.]
            args = self.arguments(deadline=(now + timedelta(seconds=120)).isoformat(), max_wall_sec=60,
                                  source_sha256=diag.old.identity({}))
            def source():
                if stage == 'source':
                    clock[0] += 70.
                return {}
            def metadata():
                clock[0] += 70.
                return {'ready': True}
            with self.subTest(stage=stage), \
                    patch.object(diag.old, 'utc_now', return_value=now), \
                    patch.object(diag.time, 'perf_counter', side_effect=lambda: clock[0]), \
                    patch.object(diag, 'sources', side_effect=source), \
                    patch.object(diag, 'dependency_metadata', side_effect=metadata), \
                    patch.object(diag.old, 'gpu_admission', side_effect=AssertionError('GPU forbidden')), \
                    self.assertRaisesRegex(TimeoutError, 'reservation reached'):
                diag.run(args)

    def test_execute_main_delegates_preparation_inside_the_budget(self):
        with patch.object(diag, 'sources', side_effect=AssertionError('pre-budget source forbidden')), \
                patch.object(diag, 'run', return_value=9) as operation:
            self.assertEqual(diag.main(['--execute']), 9)
        self.assertEqual(len(operation.call_args.args), 1)

    def test_total_alarm_reserves_only_the_remaining_budget(self):
        now = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
        with patch.object(diag.time, 'perf_counter', return_value=0.):
            guard = diag.Guard(now + timedelta(seconds=120), 60)
        with patch.object(diag.old, 'utc_now', return_value=now), \
                patch.object(diag.time, 'perf_counter', return_value=11.), \
                patch.object(diag.signal, 'getitimer', return_value=(0., 0.)), \
                patch.object(diag.signal, 'getsignal', return_value='original'), \
                patch.object(diag.signal, 'signal') as install, \
                patch.object(diag.signal, 'setitimer') as timer:
            with diag.total_budget(guard):
                pass
        self.assertEqual(timer.call_args_list[0].args[1], 49.)
        self.assertEqual(timer.call_args_list[-1].args[1], 0)
        self.assertEqual(install.call_args_list[-1].args[1], 'original')

    def test_terminal_late_write_reread_and_stdout_each_append_a_veto(self):
        for stage in ('report write', 'report reread', 'stdout flush', 'terminal audit append'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                target, guard, result = Path(directory), ControlledGuard(), report_fixture()
                write_original, read_original, terminal_original = diag.old.write_new, Path.read_text, diag.append_terminal
                if stage == 'report write':
                    def write(path, value):
                        write_original(path, value)
                        guard.expired = True
                    stack.enter_context(patch.object(diag.old, 'write_new', side_effect=write))
                elif stage == 'report reread':
                    def read(path, *args, **kwargs):
                        value = read_original(path, *args, **kwargs)
                        if path.name == 'report.json':
                            guard.expired = True
                        return value
                    stack.enter_context(patch.object(Path, 'read_text', read))
                elif stage == 'stdout flush':
                    stack.enter_context(patch('builtins.print', side_effect=lambda *a, **k: setattr(guard, 'expired', True)))
                else:
                    def terminal(path, value):
                        terminal_original(path, value)
                        guard.expired = True
                    stack.enter_context(patch.object(diag, 'append_terminal', side_effect=terminal))
                stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(diag.terminalize(target, Journal(), guard, result, 0.), 9)
                rows = [json.loads(line) for line in read_original(target / 'terminal.jsonl', encoding='utf-8').splitlines()]
                self.assertTrue(any(row['event'] == 'TERMINAL_VETO' for row in rows))
                self.assertIn('after ' + stage, guard.checks)
                self.assertEqual(result['returncode'], 9)

    def test_storage_failure_preserves_primary_error_in_append_only_terminal_veto(self):
        for stage in ('journal', 'report', 'reread', 'stdout'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                result, target = report_fixture(), Path(directory)
                result['errors'] = [dict(type='ValueError', message='primary runtime error')]
                journal = Journal()
                if stage == 'journal':
                    journal.close = lambda: (_ for _ in ()).throw(OSError('journal storage error'))
                elif stage == 'report':
                    stack.enter_context(patch.object(diag.old, 'write_new', side_effect=OSError('report storage error')))
                elif stage == 'reread':
                    stack.enter_context(patch.object(Path, 'read_text', side_effect=OSError('reread storage error')))
                else:
                    stack.enter_context(patch('builtins.print', side_effect=BrokenPipeError('stdout storage error')))
                stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(diag.terminalize(target, journal, ControlledGuard(), result, 0.), 9)
                self.assertEqual(result['errors'][0]['message'], 'primary runtime error')
                with (target / 'terminal.jsonl').open(encoding='utf-8') as stream:
                    rows = [json.loads(line) for line in stream]
                self.assertTrue(all(row['event'] == 'TERMINAL_VETO' for row in rows))
                self.assertTrue(any(row.get('errors', [{}])[0].get('message') == 'primary runtime error' for row in rows))

    def test_terminal_positive_requires_roundtrip_and_follows_stdout(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            target, guard, result = Path(directory), ControlledGuard(), report_fixture()
            self.assertEqual(diag.terminalize(target, Journal(), guard, result, 0.), 0)
            rows = [json.loads(line) for line in (target / 'terminal.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['event'], 'TERMINAL_AUDIT_COMPLETE')
            self.assertTrue(rows[0]['report_roundtrip'])
            self.assertEqual(rows[0]['actual_process_exit'], 'PENDING_CALLER_EXIT_AND_GPU_PROCESS_CHECK')
            self.assertIn('PENDING_TERMINAL_JSONL_AND_CALLER_EXIT', output.getvalue())

    def test_canary_error_and_negative_runs_write_partial_without_parent_or_data(self):
        for negative in (False, True):
            with self.subTest(negative=negative), tempfile.TemporaryDirectory() as directory, \
                    redirect_stdout(io.StringIO()), \
                    patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')):
                root = Path(directory)
                target = root / 'fixture'
                dependencies = {'ready': True}
                args = self.arguments(source_sha256=diag.old.identity({}),
                    dependency_sha256=diag.old.identity(dependencies))
                def canary(*values):
                    values[-1].update(complete=negative, close=False, original_error='canary test')
                    if negative:
                        raise diag.NumericalCanaryNegative('strict numerical canary negative')
                    raise RuntimeError('primary canary API error')
                with patch.object(diag, 'sources', return_value={}), \
                        patch.object(diag, 'dependency_metadata', return_value=dependencies), \
                        patch.object(diag, 'verify_installed_sources', return_value={}), \
                        patch.object(diag, 'output_path', return_value=target), \
                        patch.object(diag.old, 'gpu_admission', return_value={}), \
                        patch.object(diag, 'run_canaries', side_effect=canary), \
                        patch.object(diag.old, 'asset_manifest', side_effect=AssertionError('assets forbidden')):
                    self.assertEqual(diag.run(args), 8 if negative else 9)
                report = json.loads((target / 'report.json').read_text(encoding='utf-8'))
                if negative:
                    self.assertEqual(report['errors'], [])
                    self.assertEqual(report['canary_negative']['message'], 'strict numerical canary negative')
                else:
                    self.assertEqual(report['errors'][0]['message'], 'primary canary API error')
                self.assertIsNone(report['assets_before'])
                self.assertEqual(report['updates'], [])
                self.assertEqual(report['pairs'], {})
                self.assertFalse(report['matrix_complete'])
                self.assertFalse(torch.cuda.is_initialized())

    def test_terminal_storage_failure_still_returns_nonzero_and_keeps_primary_on_stderr(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()), \
                redirect_stderr(io.StringIO()) as error_output:
            result = report_fixture()
            result['errors'] = [dict(type='ValueError', message='primary runtime error')]
            with patch.object(diag, 'append_terminal', side_effect=OSError('terminal filesystem failed')):
                self.assertEqual(diag.terminalize(Path(directory), Journal(), ControlledGuard(), result, 0.), 9)
            self.assertEqual(result['errors'][0]['message'], 'primary runtime error')
            self.assertIn('primary runtime error', error_output.getvalue())
            self.assertIn('TERMINAL_VETO_STORAGE_ERROR', error_output.getvalue())

    def test_expiry_during_alarm_teardown_vetoes_previously_complete_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            now = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
            clock, target, result = [0.], Path(directory), report_fixture()
            args = self.arguments(max_wall_sec=60, deadline=(now + timedelta(seconds=120)).isoformat())
            @diag.contextmanager
            def budget(guard):
                yield
                clock[0] = 61.
            def body(args, source_map, deadline, began, guard, state):
                state.update(target=target, result=result, journal=Journal())
                diag.append_terminal(target, dict(event='TERMINAL_AUDIT_COMPLETE', returncode=0))
                return 0
            with patch.object(diag.old, 'utc_now', return_value=now), \
                    patch.object(diag.time, 'perf_counter', side_effect=lambda: clock[0]), \
                    patch.object(diag, 'total_budget', side_effect=budget), \
                    patch.object(diag, 'run_guarded', side_effect=body):
                self.assertEqual(diag.run(args), 9)
            rows = [json.loads(line) for line in (target / 'terminal.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(rows[0]['event'], 'TERMINAL_AUDIT_COMPLETE')
            self.assertEqual(rows[-1]['event'], 'TERMINAL_VETO')


if __name__ == '__main__':
    unittest.main()
