"""native 경로 드라이버의 합성 CPU 회귀. 실제 자료·모델·CUDA는 사용하지 않는다."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
from scripts import diag_p106b_native_weight_route as driver
from scripts import p106b_weight_route as route_helper

REAL_ROOT = driver.ROOT
ORIGINAL_SCHEDULE = __import__('runpy').run_path(str(REAL_ROOT / 'tinylm/train/anneal_schedule.py'))


def fixture_schedule(step, updates=2281):
    start = ORIGINAL_SCHEDULE['resolve_quant_start'](100, updates)
    return dict(lr_factor=ORIGINAL_SCHEDULE['lr_factor'](step, 100, updates, 'wsd', .2),
        anneal=ORIGINAL_SCHEDULE['quant_anneal_factor'](step, updates, 'wsd', 'linear', start, .8), quant_start=start)


@dataclass
class FixtureCfg:
    n_layers: int = 14
    dim: int = 768
    tie_mlp: bool = False
    vocab_size: int = 32768
    max_seq_len: int = 1024
    grad_checkpoint: bool = True
    mtp_aux: bool = False
    quant_anneal: float = 1.


def fixture_info():
    return dict(schema=driver.SCHEMA, tag=driver.TAG, code_sha256={'fixture.py': 'F' * 64})


def core_sha(model):
    h = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        h.update(name.encode()); h.update(value.detach().cpu().numpy().tobytes())
    return h.hexdigest().upper()


def route_receipt(arm='float'):
    return dict(mode=arm, metadata=route_helper.route_metadata(arm), tlinear_instances=1,
        owned_tlinear_instances=1, refreshed_tlinear_instances=1,
        forward_methods=['_guarded_forward'],
        refresh_methods=['_float_refresh' if arm == 'float' else '_ternary_refresh'])


def late_receipt():
    return dict(optimizer_updates=0, micro_batches=1, targets=8192, anneal=1., finite=True,
        gradient_norm=.5, seconds=3., peak_allocated_mib=2., peak_reserved_mib=4.,
        core_before='B' * 64, core_after='B' * 64)


def optimizer_groups(endpoint='native'):
    factor = 10. if endpoint == 'native' else .5
    return [dict(optimizer=name, group=0, lr=lr * factor, runtime_lr=lr,
        weight_decay=wd if endpoint == 'native' else 0., runtime_weight_decay=wd,
        lr_multiplier=factor, parameters=1, names_sha256='C' * 64, scale_mode=scale)
        for name, lr, wd, scale in (('AdamW', 1e-4, .1, None), ('Muon', 4e-4, 0., 'rms'))]


def cache_receipt(arm='float', core='B' * 64):
    return dict(quality_forwards=0, optimizer_updates=0, finite=True, route=route_receipt(arm),
        core_before=core, core_after=core, cache_tensors=1, cache_nominal_bytes=4,
        extra_cache_storage_bytes=0, seconds=1., peak_allocated_mib=1., peak_reserved_mib=2.)


class OwnedFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='p106b_native_route_fixture_')
        self.root = Path(self.temporary.name)
        self.stack = ExitStack()
        self.stack.enter_context(patch.multiple(driver, ROOT=self.root,
            CACHE=self.root / 'data_cache/fixture', RAW=self.root / 'runs/eval/fixture',
            EVIDENCE=self.root / 'test_result/evidence/fixture', TRAIN=self.root / 'train.bin',
            VAL=self.root / 'val.bin', PARENT=self.root / 'old.pt', TOKENIZER=self.root / 'tok.json'))
        self.stack.enter_context(patch.object(driver, 'info', side_effect=fixture_info))
        self.stack.enter_context(patch.object(driver, 'schedule', side_effect=fixture_schedule))
        self.stack.enter_context(patch.object(driver, 'authority', return_value=100000.))
        self.stack.enter_context(patch.object(driver, 'modules', return_value=(SimpleNamespace(), SimpleNamespace(), route_helper)))
        driver.write(driver.CACHE / 'frozen_reference.json', {'fixture_only': True})

    def tearDown(self):
        self.stack.close(); self.temporary.cleanup()

    def activity(self, mode='cost', arm='float', endpoint=None, **changes):
        start = driver.TRAIN_STOP - timedelta(hours=2)
        value = dict(schema=driver.SCHEMA, tag=driver.TAG, key=driver.phase_key(mode, arm, endpoint),
            mode=mode, arm=arm, endpoint=endpoint, seconds=5., max_wall_sec=60,
            started_at=start.isoformat(), ended_at=(start + timedelta(seconds=5)).isoformat(),
            returncode=0, complete=True, error_type=None, code_sha256=fixture_info()['code_sha256'])
        value.update(changes)
        return value

    def cost_report(self, arm='float'):
        key = driver.phase_key('cost', arm)
        events = [dict(update=i + 1, **driver.update_contract('native', i), ce=1.,
            gradient_norm=.5, clipped=False, step_seconds=2., native_replay_ce=None,
            actual_lrs=driver.actual_lrs(optimizer_groups(), fixture_schedule(i)['lr_factor'])) for i in range(8)]
        writer = driver.ShardWriter(driver.RAW / key, 'updates', limit=19_999_999)
        for event in events: writer.append(event)
        reference = driver.digest(driver.CACHE / 'frozen_reference.json')
        manifest = writer.close(lineage=dict(tag=driver.TAG, arm=arm, endpoint='native', cost=True,
            reference_sha256=reference))
        value = dict(fixture_info(), status='COST_COMPLETE', arm=arm, endpoint='native', cost=True,
            updates=8, checkpoint_writes=0, optimizer_saved=False, reference_sha256=reference,
            scratch_core_sha256='A' * 64, initial_core_sha256='A' * 64, final_core_sha256='B' * 64,
            parent_core_sha256=None, parent_checkpoint_sha256=None,
            actual_optimizer_groups=optimizer_groups(),
            max_preclip_gradient=.5, clip_events=0, cache_audit=cache_receipt(arm),
            quantization_route=route_helper.route_metadata(arm), route=route_receipt(arm),
            event_manifest=manifest, step_seconds=[2.] * 8,
            totals={k: sum(e[k] for e in events) for k in ('targets', 'x_tokens', 'native_replay_targets')},
            late_probe=late_receipt(), native32_fp32=None)
        return value, events

    def validate_cost(self, report):
        # 원시 shard와 닫힌 manifest는 실제 임시 fixture를 읽게 한다.
        actual_required = driver.required
        def required(path):
            return report if path == driver.result_path(driver.phase_key('cost', report['arm'])) else actual_required(path)
        with patch.object(driver, 'completed_activity'), patch.object(driver, 'required', side_effect=required):
            return driver.train_report('cost', report['arm'])


class RecipeTests(unittest.TestCase):
    def test_exact_draw_and_pool_arithmetic(self):
        self.assertEqual((driver.UPDATES, driver.TARGETS, driver.DRAW_TOKENS, driver.CROPS),
            (2281, 131072, 298975232, 291968))
        self.assertEqual(driver.TRAIN_TOKENS - 2 * driver.DRAW_TOKENS, 44536)
        self.assertEqual((driver.MICRO, driver.ACCUM, driver.SEQ), (8, 16, 1024))

    def test_crop_vector_rng_and_legal_last_start(self):
        state = np.random.get_state()
        first, receipt = driver.make_offsets()
        second, again = driver.make_offsets()
        expected = np.random.default_rng(1337).integers(0, 597995000 - 1024, 291968, dtype=np.int64)
        np.testing.assert_array_equal(first, expected); np.testing.assert_array_equal(first, second)
        self.assertEqual(receipt, again)
        self.assertEqual(receipt['twice_draw'], 597950464)
        self.assertLessEqual(int(first.max()) + 1025, driver.TRAIN_TOKENS)
        self.assertEqual(receipt['offsets_bytes_sha256'], hashlib.sha256(first.tobytes()).hexdigest().upper())
        after = np.random.get_state()
        self.assertEqual(state[0], after[0]); np.testing.assert_array_equal(state[1], after[1])
        self.assertEqual(state[2:], after[2:])

    def test_small_pool_refused_not_repaired(self):
        for kwargs in ({'pool_tokens': 597950463}, {'updates': True}, {'seed': -1}, {'seq': 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): driver.make_offsets(**kwargs)

    def test_original_schedule_and_zero_based_steps(self):
        original = __import__('runpy').run_path(str(driver.ROOT / 'tinylm/train/anneal_schedule.py'))
        for step in (0, 7, 99, 100, 214, 1000, 1825, 2280):
            value = driver.schedule(step)
            start = original['resolve_quant_start'](100, 2281)
            self.assertEqual(value['lr_factor'], original['lr_factor'](step, 100, 2281, 'wsd', .2))
            self.assertEqual(value['anneal'], original['quant_anneal_factor'](step, 2281, 'wsd', 'linear', start, .8))
        self.assertEqual(driver.schedule(0)['lr_factor'], .01)
        self.assertEqual(driver.schedule(2280)['anneal'], 1.)
        for value in (-1, 2281, 1., True):
            with self.assertRaises(ValueError): driver.schedule(value)

    def test_phase_selectors_are_used_or_rejected(self):
        self.assertEqual(driver.phase_key('train', 'float'), 'train_float')
        self.assertEqual(driver.phase_key('evaluate', 'ternary', 'sft'), 'evaluate_ternary_sft')
        self.assertEqual(driver.phase_key('budget', endpoint='native'), 'budget_native')
        for args in (('source', 'float'), ('train', None), ('train', 'float', 'native'),
                     ('evaluate', 'float'), ('budget', None, None), ('source', None, 'native')):
            with self.subTest(args=args), self.assertRaises(ValueError): driver.phase_key(*args)

    def test_native_update_contract_and_sft_absolute_384(self):
        frozen = {'exposure': {driver.SOURCE_ARM: [dict(update_target_denominators=list(range(100 + e * 96, 196 + e * 96))) for e in range(4)]}}
        value = driver.update_contract('native', 2280)
        self.assertEqual(value['crop_start'], 2280 * 128); self.assertEqual(value['targets'], 131072)
        for step in (0, 95, 96, 191, 287, 383):
            value = driver.update_contract('sft', step, frozen)
            self.assertEqual(value['targets'], 100 + step)
            self.assertEqual(value['native_replay_targets'], 8192)
            self.assertEqual(value['schedule'], dict(lr_factor=1., anneal=1.))

    def test_native_record_shift_and_extent(self):
        tokens = np.arange(2100, dtype=np.uint16)
        records = driver.native_records(tokens, [0, 1075])
        self.assertEqual(records[0].x[:3], [0, 1, 2]); self.assertEqual(records[0].y[:3], [1, 2, 3])
        self.assertEqual(records[1].y[-1], 2099)
        self.assertEqual([r.targets for r in records], [1024, 1024])
        for offset in (-1, 1076):
            with self.assertRaises(ValueError): driver.native_records(tokens, [offset])

    def test_aware_absolute_authority_and_three_hour_reserve(self):
        now = driver.TRAIN_STOP - timedelta(seconds=1)
        self.assertEqual(driver.authority(True, now), 1.)
        self.assertEqual(driver.authority(False, now), 10801.)
        with self.assertRaises(driver.Pending): driver.authority(True, driver.TRAIN_STOP)
        with self.assertRaises(driver.Pending): driver.authority(False, driver.END)
        with self.assertRaises(ValueError): driver.authority(now=datetime(2026, 10, 19))

    def test_every_nontraining_operation_preserves_final_ten_minutes(self):
        self.assertEqual(driver.execution_remaining(False, driver.END - timedelta(seconds=601)), 1.)
        with self.assertRaises(driver.Pending): driver.execution_remaining(False, driver.END - timedelta(seconds=600))
        self.assertEqual(driver.execution_remaining(True, driver.TRAIN_STOP - timedelta(seconds=1)), 1.)

    def test_direct_exec_check_only_outside_repository(self):
        path = driver.ROOT / 'scripts/diag_p106b_native_weight_route.py'
        result = subprocess.run([sys.executable, '-B', '-I', str(path), '--mode', 'source', '--check-only'],
            cwd='/tmp', text=True, encoding='utf-8', capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('[NATIVE_ROUTE_CHECK_ONLY]'))
        value = json.loads(result.stdout.split('] ', 1)[1])
        self.assertTrue(value['code_complete']); self.assertIs(value['parent_training_weights_copied'], False)
        self.assertEqual(value['native_language_ratio'], 'NOT_MEASURED')


class EvidenceTests(OwnedFixture):
    def test_safe_namespace_and_write_once(self):
        path = driver.CACHE / 'one.json'; driver.write(path, {'한글': 1})
        with self.assertRaises(FileExistsError): driver.write(path, {})
        for path in (self.root / 'old.json', Path('/tmp/escape.json'), self.root / 'data_cache/../old.json'):
            with self.subTest(path=path), self.assertRaises(ValueError): driver.write(path, {})

    def test_symlink_target_refused(self):
        (self.root / 'linked').symlink_to(driver.CACHE, target_is_directory=True)
        with self.assertRaises(ValueError): driver.safe(self.root / 'linked/file.json')

    def test_activity_success_and_failure_are_distinct(self):
        good = self.activity(); self.assertIs(driver.validate_activity(good, good['key'], True), good)
        bad = self.activity(complete=False, returncode=8, error_type='Pending')
        self.assertIs(driver.validate_activity(bad, bad['key']), bad)
        with self.assertRaises(driver.Pending): driver.validate_activity(bad, bad['key'], True)

    def test_bad_activity_clocks_types_and_deadline(self):
        for changes in ({'seconds': float('nan')}, {'seconds': True}, {'seconds': 91.},
                {'max_wall_sec': 59}, {'max_wall_sec': True}, {'complete': True, 'returncode': 8},
                {'code_sha256': {}}, {'ended_at': driver.END.isoformat()},
                {'started_at': datetime(2026, 10, 19).isoformat()}):
            value = self.activity(**changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): driver.validate_activity(value, value['key'])

    def test_complete_activity_requires_report_and_reference_hash(self):
        key = driver.phase_key('cost', 'float'); driver.write(driver.result_path(key), {'fixture': 2})
        value = self.activity(result_sha256=driver.digest(driver.result_path(key)),
            reference_sha256=driver.digest(driver.CACHE / 'frozen_reference.json'))
        driver.write(driver.EVIDENCE / ('activity_' + key + '.json'), value)
        driver.completed_activity('cost', 'float')
        with patch.object(driver, 'digest', return_value='0' * 64), self.assertRaises(ValueError):
            driver.completed_activity('cost', 'float')

    def test_closed_cost_report_recounts_all_actual_updates(self):
        report, _ = self.cost_report(); self.assertEqual(self.validate_cost(report), report)

    def test_cost_rejects_bad_route_initial_weights_or_late_probe(self):
        report, _ = self.cost_report()
        for key, value in (('checkpoint_writes', 1), ('scratch_core_sha256', driver.PARENT_CORE),
                ('initial_core_sha256', 'C' * 64), ('quantization_route', route_helper.route_metadata('ternary')),
                ('late_probe', dict(late_receipt(), optimizer_updates=1)),
                ('late_probe', dict(late_receipt(), gradient_norm=float('nan'))),
                ('late_probe', dict(late_receipt(), core_after='C' * 64)), ('max_preclip_gradient', .6),
                ('clip_events', 1), ('cache_audit', dict(cache_receipt(), quality_forwards=1)),
                ('cache_audit', dict(cache_receipt(), core_after='C' * 64)),
                ('route', dict(route_receipt(), refreshed_tlinear_instances=0))):
            wrong = dict(report, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): self.validate_cost(wrong)

    def test_raw_event_denominator_schedule_and_totals_are_not_report_only(self):
        report, _ = self.cost_report()
        wrong = dict(report, totals=dict(report['totals'], targets=1))
        with self.assertRaises(ValueError): self.validate_cost(wrong)
        wrong = dict(report, event_manifest=dict(report['event_manifest'], lineage={}))
        with self.assertRaises(ValueError): self.validate_cost(wrong)

    def test_update_manifest_traversal_refused_before_verify(self):
        manifest = dict(rows=1, limit_bytes=19_999_999, shards=[dict(path='../updates_000000.jsonl')])
        with patch.object(driver, 'verify') as verify, self.assertRaises(ValueError):
            driver.read_events(driver.RAW / 'x', manifest, 1)
        verify.assert_not_called()

    def test_native32_receipt_is_not_full_validation_claim(self):
        good = dict(ce=1., targets=32768, windows=32, val_sha256=driver.VAL_SHA, precision='FP32_MATH')
        driver.validate_native32(good)
        for key, value in (('ce', float('inf')), ('targets', 32767), ('precision', 'BF16'), ('windows', 31)):
            with self.assertRaises(ValueError): driver.validate_native32(dict(good, **{key: value}))

    def test_strict_checkpoint_recipe_and_no_implicit_route(self):
        cfg = FixtureCfg(); expected = dict(tag=driver.TAG, arm='float', endpoint='native')
        payload = dict(model={}, cfg=asdict(cfg), step=2281, tokenizer_sha256=driver.TOKENIZER_SHA,
            tokenizer_lineage='chat32', quantization_route=route_helper.route_metadata('float'), experiment=expected)
        driver.validate_payload(payload, cfg, 'float', 'native', expected)
        for key, value in (('step', 2289), ('cfg', dict(asdict(cfg), max_seq_len=2048)),
                ('quantization_route', route_helper.route_metadata('ternary')), ('experiment', dict(expected, tag='old')),
                ('tokenizer_sha256', '0' * 64)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                driver.validate_payload(dict(payload, **{key: value}), cfg, 'float', 'native', expected)
        with self.assertRaises(ValueError): driver.validate_payload([], cfg, 'float', 'native', expected)
        with self.assertRaises(RuntimeError): route_helper.generic_loader_guard(payload)

    def test_native_budget_has_unmeasured_sft_reserve_no_circular_cost(self):
        cost = dict(scratch_core_sha256='A' * 64, step_seconds=[2.] * 8, late_probe=dict(seconds=3.))
        with patch.object(driver, 'prepared'), patch.object(driver, 'spent_seconds', return_value=0.), \
                patch.object(driver, 'train_report', return_value=cost) as read:
            value = driver.budget('native')
        self.assertTrue(value['fits']); self.assertEqual(value['unmeasured_sft_reserve_seconds'], 3600.)
        self.assertEqual(value['evaluation_and_record_reserve_seconds'], 10800)
        self.assertEqual(read.call_args_list, [unittest.mock.call('cost', 'ternary'), unittest.mock.call('cost', 'float')])

    def test_resource_cap_is_not_silently_relaxed(self):
        cost = dict(scratch_core_sha256='A' * 64, step_seconds=[100.] * 8, late_probe=dict(seconds=30.))
        with patch.object(driver, 'prepared'), patch.object(driver, 'spent_seconds', return_value=0.), \
                patch.object(driver, 'train_report', return_value=cost):
            value = driver.budget('native')
        self.assertFalse(value['fits']); self.assertEqual(driver.ACTIVE_LIMIT, 43200)
        self.assertEqual(driver.NATIVE_WORKER_LIMIT, 14400)

    def test_sft_cost_budget_requires_both_native_first(self):
        cost = dict(scratch_core_sha256='A' * 64, step_seconds=[2.] * 8, late_probe=dict(seconds=3.))
        with patch.object(driver, 'prepared'), patch.object(driver, 'spent_seconds', return_value=0.), \
                patch.object(driver, 'train_report', return_value=cost) as read, self.assertRaises(driver.Pending):
            driver.budget('sft')
        self.assertTrue(all(call.args[0] == 'cost' for call in read.call_args_list))

    def test_sft_budget_uses_actual_own_parent_costs(self):
        cost = dict(scratch_core_sha256='A' * 64, step_seconds=[2.] * 8, late_probe=dict(seconds=3.))
        for arm in driver.ARMS: driver.write(driver.result_path(driver.phase_key('train', arm)), {'fixture': True})
        with patch.object(driver, 'prepared'), patch.object(driver, 'spent_seconds', return_value=100.), \
                patch.object(driver, 'train_report', return_value=cost) as read:
            value = driver.budget('sft')
        self.assertTrue(value['fits']); self.assertEqual(value['unmeasured_sft_reserve_seconds'], 0.)
        self.assertEqual(set(value['completed']), {'ternary_native', 'float_native'})
        self.assertEqual(sum(c.args[0] == 'sft_cost' for c in read.call_args_list), 2)

    def test_failed_same_code_source_is_before_idle_or_model(self):
        with patch.object(driver, 'prepared', side_effect=ValueError('fixture source changed')), \
                patch('scripts.p106b_gate_runtime.idle_before_gpu') as idle, \
                patch.object(driver, 'routed_runtime') as load, self.assertRaises(ValueError):
            driver.train('float', cost=True)
        idle.assert_not_called(); load.assert_not_called()

    def test_long_train_requires_completed_budget_and_fit_before_gpu(self):
        with patch.object(driver, 'prepared', return_value=({}, {}, [], [])), \
                patch.object(driver, 'completed_activity'), patch.object(driver, 'budget', return_value={'fits': False}), \
                patch('scripts.p106b_gate_runtime.idle_before_gpu') as idle, \
                patch.object(driver, 'routed_runtime') as load, self.assertRaises(driver.Pending):
            driver.train('float')
        idle.assert_not_called(); load.assert_not_called()

    def test_worker_failure_finally_records_once_and_no_retry(self):
        with patch.object(driver, 'train', side_effect=driver.Pending('fixture hold')), \
                patch('scripts.p106b_gate_runtime.wall_limit', side_effect=lambda _: nullcontext()), self.assertRaises(driver.Pending):
            driver.worker('cost', 'float', None, 60)
        activity = driver.required(driver.EVIDENCE / 'activity_cost_float.json')
        self.assertIs(activity['complete'], False); self.assertEqual(activity['returncode'], 8)
        self.assertEqual(activity['error_type'], 'Pending')
        with self.assertRaises(FileExistsError): driver.worker('cost', 'float', None, 60)

    def test_exit_zero_without_report_is_failure(self):
        with patch.object(driver, 'train', return_value=0), \
                patch('scripts.p106b_gate_runtime.wall_limit', side_effect=lambda _: nullcontext()), self.assertRaises(ValueError):
            driver.worker('cost', 'float', None, 60)
        activity = driver.required(driver.EVIDENCE / 'activity_cost_float.json')
        self.assertIs(activity['complete'], False); self.assertEqual(activity['returncode'], 9)

    def test_own_sigterm_preserves_failure_activity_and_restores_handler(self):
        previous = driver.signal.getsignal(driver.signal.SIGTERM)
        def terminate(*args): driver.signal.getsignal(driver.signal.SIGTERM)(driver.signal.SIGTERM, None)
        with patch.object(driver, 'train', side_effect=terminate), \
                patch('scripts.p106b_gate_runtime.wall_limit', side_effect=lambda _: nullcontext()), self.assertRaises(KeyboardInterrupt):
            driver.worker('cost', 'float', None, 60)
        activity = driver.required(driver.EVIDENCE / 'activity_cost_float.json')
        self.assertIs(activity['complete'], False); self.assertEqual(activity['returncode'], 130)
        self.assertIs(driver.signal.getsignal(driver.signal.SIGTERM), previous)

    def test_bad_wall_refused_before_source_or_activity(self):
        with patch.object(driver, 'source_state') as source:
            for value in (59, 21601, True):
                with self.assertRaises(ValueError): driver.worker('source', None, None, value)
        source.assert_not_called()
        self.assertFalse((driver.EVIDENCE / 'activity_source.json').exists())

    def test_native_wall_above_four_hours_refused_before_source(self):
        with patch.object(driver, 'prepared') as source:
            with self.assertRaises(ValueError): driver.worker('train', 'float', None, 14401)
            with self.assertRaises(ValueError): driver.phase_commands('train', 'float', None, 14401)
        source.assert_not_called()

    def test_record_reserve_blocks_worker_evaluate_and_readback(self):
        with patch.object(driver, 'authority', return_value=600.), patch.object(driver, 'evaluate') as infer:
            with self.assertRaises(driver.Pending): driver.worker('evaluate', 'float', 'sft', 60)
        infer.assert_not_called()
        with patch.object(driver, 'execution_remaining', side_effect=driver.Pending('기록 예비')), \
                patch.object(driver, 'prepared') as read:
            with self.assertRaises(driver.Pending): driver.evaluate('float', 'native')
            with self.assertRaises(driver.Pending): driver.readback()
        read.assert_not_called()


class FixtureModel(torch.nn.Module):
    def __init__(self):
        super().__init__(); self.embedding = torch.nn.Parameter(torch.tensor(.3))
        self.matrix = torch.nn.Parameter(torch.tensor(.7)); self.cfg = FixtureCfg()
        self.anneals = []

    def set_anneal(self, value): self.cfg.quant_anneal = float(value); self.anneals.append(float(value))
    def clear_quant(self): self._quant_frozen = False
    def freeze_quant(self): self._quant_frozen = True
    def cuda(self): return self


class DummyMuon(torch.optim.SGD):
    def __init__(self, params):
        super().__init__(params, lr=4e-4, weight_decay=0.); self.scale_mode = 'rms'
        self.param_groups[0]['scale_mode'] = 'rms'


def fixture_optimizers(model):
    return torch.optim.AdamW([dict(params=[model.embedding], lr=1e-4, weight_decay=.1)]), DummyMuon([model.matrix])


class TorchFacade:
    bfloat16 = torch.bfloat16
    nn = torch.nn
    isfinite = staticmethod(torch.isfinite)
    no_grad = staticmethod(torch.no_grad)
    autocast = staticmethod(lambda *args, **kwargs: nullcontext())
    compile = staticmethod(lambda model, **kwargs: model)
    cuda = SimpleNamespace(reset_peak_memory_stats=lambda: None, synchronize=lambda: None,
        max_memory_allocated=lambda: 1048576, max_memory_reserved=lambda: 2097152, empty_cache=lambda: None)
    backends = SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=False)),
        cudnn=SimpleNamespace(allow_tf32=False))


class ComputeFixtureTests(OwnedFixture):
    def test_optimizer_scaling_preserves_groups_and_native_embedding_decay(self):
        runtime = SimpleNamespace(optimizers=fixture_optimizers)
        with patch.object(driver, 'modules', return_value=(runtime, None, route_helper)):
            model = FixtureModel(); _, native = driver.make_optimizers(model, 'native')
            self.assertEqual([g['lr'] for g in native], [.001, .004])
            self.assertEqual([g['weight_decay'] for g in native], [.1, 0.])
            _, sft = driver.make_optimizers(FixtureModel(), 'sft')
            self.assertEqual([g['lr'] for g in sft], [5e-5, 2e-4])
            self.assertEqual([g['weight_decay'] for g in sft], [0., 0.])
        self.assertEqual(native[1]['scale_mode'], 'rms')

    def test_scratch_runtime_never_loads_trained_state(self):
        model = FixtureModel(); scratch = core_sha(model)
        runtime = SimpleNamespace(load_runtime=Mock(return_value=(TorchFacade, model, model.cfg, object(), scratch)))
        active = SimpleNamespace(assert_active=Mock())
        @contextmanager
        def context(base, mode):
            self.assertIs(base, model); self.assertEqual(mode, 'float'); yield active
        method = SimpleNamespace(weight_route=context, load_routed_state=Mock())
        with patch.object(driver, 'modules', return_value=(runtime, None, method)):
            with driver.routed_runtime('float') as values:
                self.assertEqual(values[4], scratch); self.assertIs(values[5], active)
        runtime.load_runtime.assert_called_once_with('scratch_ntp'); method.load_routed_state.assert_not_called()

    def test_learned_parent_fingerprint_refused_as_scratch(self):
        model = FixtureModel(); runtime = SimpleNamespace(load_runtime=Mock(return_value=(TorchFacade, model, model.cfg, None, driver.PARENT_CORE)))
        with patch.object(driver, 'modules', return_value=(runtime, None, route_helper)), self.assertRaises(ValueError):
            with driver.routed_runtime('float'): pass

    def test_unsupported_route_cfg_is_cpu_rejected_before_cuda(self):
        model = FixtureModel(); runtime = SimpleNamespace(load_runtime=Mock(return_value=(TorchFacade, model, model.cfg, None, core_sha(model))))
        method = SimpleNamespace(weight_route=Mock(side_effect=ValueError('지원하지 않는 CPU cfg')))
        with patch.object(driver, 'modules', return_value=(runtime, None, method)), patch.object(model, 'cuda') as cuda, self.assertRaises(ValueError):
            with driver.routed_runtime('float'): pass
        cuda.assert_not_called()

    def test_cpu_cp_shape_dtype_and_alias_conflict_rejected_without_copy(self):
        model = FixtureModel(); payload = dict(model={k: v.clone() for k, v in model.state_dict().items()})
        before = core_sha(model); driver.validate_cpu_state(model, payload, torch)
        for value in (torch.ones(2), torch.tensor(.5, dtype=torch.float64), '형식 오류'):
            wrong = dict(model=dict(payload['model'], matrix=value))
            with self.assertRaises(ValueError): driver.validate_cpu_state(model, wrong, torch)
        self.assertEqual(core_sha(model), before)

    def test_backward_micro_uses_sum_over_whole_update_denominator(self):
        from tinylm.train import mtp_sft as core
        records = driver.native_records(np.arange(2048, dtype=np.uint16), range(8))
        parameter = torch.tensor(2., requires_grad=True)
        def component(*args, **kwargs):
            self.assertEqual(kwargs['horizons'], ()); return {1: parameter * 8192}, {1: 8192}
        with patch.object(core, 'pad_records', return_value=(None, None, None)), patch.object(core, 'components', side_effect=component):
            result = driver.backward_micro(None, lambda *a, **k: None, records, 131072, TorchFacade)
        self.assertEqual(result, (16384., 8192, 8192)); self.assertEqual(float(parameter.grad), 8192 / 131072)

    def test_backward_micro_rejects_bad_count_and_nonfinite(self):
        from tinylm.train import mtp_sft as core
        records = driver.native_records(np.arange(2048, dtype=np.uint16), range(8))
        for numerator, count in ((float('nan'), 8192), (1., 8191)):
            with patch.object(core, 'pad_records', return_value=(None, None, None)), \
                    patch.object(core, 'components', return_value=({1: torch.tensor(numerator, requires_grad=True)}, {1: count})), self.assertRaises(ValueError):
                driver.backward_micro(None, lambda *a, **k: None, records, 131072, TorchFacade)

    def test_late_probe_has_no_optimizer_update_and_restores_anneal(self):
        model = FixtureModel(); model.set_anneal(.2); adam, muon = fixture_optimizers(model)
        runtime = SimpleNamespace(state_fingerprint=core_sha)
        def backward(*args):
            (model.embedding.square() + model.matrix.square()).backward(); return 1., 8192, 8192
        with patch.object(driver, 'modules', return_value=(runtime, None, route_helper)), \
                patch.object(driver, 'native_records', return_value=[]), patch.object(driver, 'backward_micro', side_effect=backward), \
                patch.object(adam, 'step', wraps=adam.step) as astep, patch.object(muon, 'step', wraps=muon.step) as mstep:
            value = driver.late_probe(TorchFacade, model, None, (adam, muon), [], list(range(8)))
        astep.assert_not_called(); mstep.assert_not_called()
        self.assertEqual(value['core_before'], value['core_after']); self.assertEqual(value['optimizer_updates'], 0)
        self.assertEqual(model.cfg.quant_anneal, .2); self.assertIsNone(model.embedding.grad)

    def test_late_probe_nonfinite_gradient_fails_and_restores(self):
        model = FixtureModel(); model.set_anneal(.2); optimizers = fixture_optimizers(model)
        runtime = SimpleNamespace(state_fingerprint=core_sha)
        def backward(*args): model.embedding.grad = torch.tensor(float('nan')); return 1., 8192, 8192
        with patch.object(driver, 'modules', return_value=(runtime, None, route_helper)), \
                patch.object(driver, 'native_records', return_value=[]), patch.object(driver, 'backward_micro', side_effect=backward), self.assertRaises(ValueError):
            driver.late_probe(TorchFacade, model, None, optimizers, [], list(range(8)))
        self.assertEqual(model.cfg.quant_anneal, .2); self.assertIsNone(model.embedding.grad)

    def test_real_tiny_route_cost_lifecycle_train8_late_cache_without_quality_forward(self):
        from scripts.test_p106b_weight_route import Mini
        for mode in driver.ARMS:
            with self.subTest(mode=mode):
                model = Mini(); runtime = SimpleNamespace(state_fingerprint=core_sha)
                optimizer = torch.optim.SGD(model.parameters(), lr=.01)
                self.assertFalse(torch.cuda.is_initialized())
                with route_helper.weight_route(model, mode) as route:
                    for step in range(8):
                        model.train(); model.set_anneal(fixture_schedule(step)['anneal']); optimizer.zero_grad(set_to_none=True)
                        for _ in range(16): (model(torch.tensor([[.2, -.3]])).square().sum() / 16).backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
                    self.assertEqual(len(route._versions), 0)
                    def late_backward(*args):
                        loss = model(torch.tensor([[.2, -.3]])).square().sum(); loss.backward()
                        return float(loss.detach()), 8192, 8192
                    with patch.object(driver, 'modules', return_value=(runtime, None, route_helper)), \
                            patch.object(driver, 'native_records', return_value=[]), \
                            patch.object(driver, 'backward_micro', side_effect=late_backward):
                        driver.late_probe(TorchFacade, model, model, (optimizer,), [], list(range(8)))
                    self.assertEqual(len(route._versions), 0)
                    with patch.object(driver, 'modules', return_value=(runtime, None, route_helper)), \
                            patch.object(model, 'forward', wraps=model.forward) as forward:
                        audit = driver.cache_audit(TorchFacade, model, route)
                    forward.assert_not_called(); self.assertEqual(audit['route']['refreshed_tlinear_instances'], 2)
                    self.assertEqual(audit['cache_tensors'], 2); self.assertEqual(audit['core_before'], audit['core_after'])
                    self.assertEqual(audit['extra_cache_storage_bytes'], 0 if mode == 'float' else 32)
                    self.assertTrue(model.training); self.assertFalse(model._quant_frozen)
                    self.assertTrue(all(p.requires_grad for p in model.parameters()))
                    self.assertTrue(all(m._wq is None for m in route.linears))
                self.assertFalse(torch.cuda.is_initialized())

    def test_native_cost_loop_eight_updates_sixteen_micro_and_no_checkpoint(self):
        model = FixtureModel(); runtime = SimpleNamespace(state_fingerprint=core_sha, optimizers=fixture_optimizers)
        offsets = np.arange(8 * 128, dtype=np.int64)
        # 임시 fixture만 uint16 원시 배열로 만들며 원본 cache는 열지 않는다.
        with driver.TRAIN.open('wb') as stream: stream.write((np.arange(4096, dtype=np.uint16) % 4).tobytes())
        active = SimpleNamespace(assert_active=Mock(), metadata=route_helper.route_metadata('float'))
        @contextmanager
        def context(*args): yield TorchFacade, model, model.cfg, None, core_sha(model), active
        calls = []
        def backward(base, forward, records, denominator, tensor_api):
            calls.append((len(records), denominator, records[0].x[0]))
            target = sum(r.targets for r in records)
            loss = (model.embedding.square() + model.matrix.square() + 1.) * target
            (loss / denominator).backward(); return float(loss.detach()), target, sum(r.x_tokens for r in records)
        with patch.multiple(driver, SEQ=2, TARGETS=256, TRAIN_TOKENS=4096), \
                patch.object(driver, 'prepared', return_value=({}, {}, [], offsets)), \
                patch.object(driver, 'modules', return_value=(runtime, None, route_helper)), \
                patch.object(driver, 'routed_runtime', side_effect=context), patch.object(driver, 'backward_micro', side_effect=backward), \
                patch.object(driver, 'late_probe', return_value=late_receipt()) as late, \
                patch.object(driver, 'cache_audit', return_value=cache_receipt()), \
                patch.object(driver, 'route_receipt', return_value=route_receipt()), \
                patch('scripts.p106b_gate_runtime.idle_before_gpu') as idle, redirect_stdout(io.StringIO()):
            self.assertEqual(driver.train('float', cost=True), 0)
        idle.assert_called_once(); late.assert_called_once()
        self.assertEqual(len(calls), 8 * 16); self.assertTrue(all(n == 8 and d == 256 for n, d, _ in calls))
        report = driver.required(driver.result_path('cost_float'))
        self.assertEqual(report['updates'], 8); self.assertEqual(report['checkpoint_writes'], 0)
        self.assertEqual(report['totals']['targets'], 8 * 256)
        self.assertEqual(report['initial_core_sha256'], report['scratch_core_sha256'])
        self.assertNotEqual(report['final_core_sha256'], report['scratch_core_sha256'])
        self.assertFalse((self.root / 'runs/ckpt').exists())
        events = driver.read_events(driver.RAW / 'cost_float', report['event_manifest'], 8)
        self.assertEqual([e['crop_start'] for e in events], list(range(0, 1024, 128)))


class ProcessTests(unittest.TestCase):
    def test_error9_preserves_traceback_in_stderr(self):
        error = io.StringIO()
        with patch.object(driver, 'worker', side_effect=ValueError('합성 내부 오류')), \
                redirect_stdout(io.StringIO()), __import__('contextlib').redirect_stderr(error):
            code = driver.main(['--mode', 'source', '--execute', '--worker'])
        self.assertEqual(code, 9); self.assertIn('Traceback', error.getvalue()); self.assertIn('합성 내부 오류', error.getvalue())

    def test_regression_preflight_execute_pipeline_and_explicit_selectors(self):
        phases = driver.phase_commands('evaluate', 'float', 'sft', 600)
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p106b_native_weight_route', phases[0][1])
        self.assertIn('--worker', phases[2][1]); self.assertIn('sft', phases[2][1]); self.assertIn('float', phases[2][1])
        self.assertIn('preflight', phases[1][1])

    def test_watchdog_signals_own_process_group_only(self):
        process = SimpleNamespace(pid=4321, poll=Mock(return_value=None),
            wait=Mock(side_effect=[subprocess.TimeoutExpired('fixture', 1), 0]))
        with patch.object(driver.subprocess, 'Popen', return_value=process) as popen, \
                patch.object(driver.os, 'getpgid', return_value=4321), patch.object(driver.os, 'killpg') as kill:
            self.assertEqual(driver.launch(['fixture'], 1), 124)
        self.assertTrue(popen.call_args.kwargs['start_new_session']); kill.assert_called_once_with(4321, driver.signal.SIGTERM)

    def test_watchdog_does_not_signal_other_process_group(self):
        process = SimpleNamespace(pid=4321, poll=Mock(return_value=None), wait=Mock(side_effect=subprocess.TimeoutExpired('fixture', 1)))
        with patch.object(driver.subprocess, 'Popen', return_value=process), patch.object(driver.os, 'getpgid', return_value=9999), \
                patch.object(driver.os, 'killpg') as kill:
            self.assertEqual(driver.launch(['fixture'], 1), 124)
        kill.assert_not_called()


class FixtureTokenizer:
    def encode(self, text): return SimpleNamespace(ids=[ord(c) % 30000 + 10 for c in text])
    def decode(self, ids, skip_special_tokens=False):
        if ids != [100] or skip_special_tokens: raise ValueError('합성 decode 계약 오류')
        return '합성 응답'
    def token_to_id(self, token): return {'<eos>': 2, '<|im_end|>': 4}.get(token)


class EvaluationFixtureTests(OwnedFixture):
    def test_four_endpoints_actual_receipt_readback_and_no_gold_inference(self):
        from tinylm.chat.serialize import serialize
        from tokenizers import Tokenizer
        cases = [dict(id='fixture_' + str(i), language=lang, lane='fixture', family='fixture',
            messages=[dict(role='user', content='합성 질문 ' + str(i))], gold='추론 함수에는 전달하면 안 됨')
            for i, lang in enumerate(('ko', 'en'))]
        model = FixtureModel(); tokenizer = FixtureTokenizer(); calls = []
        def emit(base, cfg, tok, messages):
            self.assertIs(base, model); self.assertIs(tok, tokenizer); self.assertFalse(base.training)
            self.assertTrue(all(p.requires_grad for p in base.parameters()))
            self.assertIn(messages, [c['messages'] for c in cases]); calls.append(messages)
            prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
            self.assertNotIn('추론 함수에는 전달하면 안 됨', prompt)
            body = '합성 응답'; ids = [100, 4]
            g = dict(max_new=64, precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
                eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True,
                stop_token_sequences=[[4]], candidate_answers_supplied=False, terminal_only_removed=True,
                prompt_sha256=driver.sha(prompt), prompt_ids_sha256=driver.sha(tok.encode(prompt).ids),
                prompt_tokens=len(tok.encode(prompt).ids), generated_ids=ids, terminal_ids=[4], generated_tokens=2,
                finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4], generated_ids_sha256=driver.sha(ids),
                content_ids_sha256=driver.sha([100]), body_utf8_sha256=hashlib.sha256(body.encode()).hexdigest().upper())
            return body, g
        source = SimpleNamespace(emit64=emit, classify_case=lambda case, answer: dict(correct=None),
            recount=Mock(side_effect=lambda events, frozen, tok: dict(actual_answers=len(events))))
        runtime = SimpleNamespace(state_fingerprint=core_sha)
        def cp_report(mode, arm):
            endpoint = 'native' if mode == 'train' else 'sft'
            return dict(checkpoint_sha256=driver.digest(driver.checkpoint(arm, endpoint)), final_core_sha256=core_sha(model))
        for arm in driver.ARMS:
            for endpoint in driver.ENDPOINTS:
                path = driver.checkpoint(arm, endpoint); path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(('합성 CP tensor가 아닌 표식 ' + arm + endpoint).encode())
        @contextmanager
        def context(arm, endpoint):
            yield TorchFacade, model, model.cfg, tokenizer, 'A' * 64, SimpleNamespace(
                assert_active=Mock(), metadata=route_helper.route_metadata(arm))
        native32 = dict(ce=1., targets=32768, windows=32, val_sha256=driver.VAL_SHA, precision='FP32_MATH')
        log = io.StringIO()
        with patch.object(driver, 'ANSWERS', 2), patch.object(driver, 'prepared', return_value=(
                {'display_ids': ['fixture_0']}, {}, cases, [])), patch.object(driver, 'completed_activity'), \
                patch.object(driver, 'modules', return_value=(runtime, source, route_helper)), \
                patch.object(driver, 'routed_runtime', side_effect=context), patch.object(driver, 'train_report', side_effect=cp_report), \
                patch.object(driver, 'route_receipt', side_effect=lambda base, route: route_receipt(route.metadata['mode'])), \
                patch.object(driver, 'native_probe', return_value=native32), \
                patch('scripts.p106b_gate_runtime.idle_before_gpu'), patch.object(Tokenizer, 'from_file', return_value=tokenizer), \
                redirect_stdout(log):
            for arm in driver.ARMS:
                for endpoint in driver.ENDPOINTS: self.assertEqual(driver.evaluate(arm, endpoint), 0)
            self.assertEqual(driver.readback(), 0)
        self.assertEqual(len(calls), 8); self.assertEqual(source.recount.call_count, 4)
        report = driver.required(driver.result_path('readback'))
        self.assertEqual([(r['arm'], r['endpoint']) for r in report['summaries']],
            [(a, e) for a in driver.ARMS for e in driver.ENDPOINTS])
        samples = [json.loads(line.split('] ', 1)[1]) for line in log.getvalue().splitlines() if line.startswith('[NATIVE_ROUTE_SAMPLE]')]
        self.assertEqual(len(samples), 4)
        self.assertTrue(all(r['id'] == 'fixture_0' and r['messages'] == cases[0]['messages']
            and r['finish_reason'] == 'STOP_SEQUENCE' and r['language'] == 'ko' and r['family'] == 'fixture' for r in samples))


if __name__ == '__main__': unittest.main()
