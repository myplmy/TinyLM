"""CPU 메타데이터·toy 회귀이며 실제 자산·모델·CP·GPU는 읽지 않는다."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
import copy
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
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p078_route_protocol as p
from scripts import diag_p078_route_training as d


def args(mode='budget'):
    return p.parser_for(d).parse_args(['--mode', mode, '--execute', '--corpus-sha256', 'A' * 64])


def toy_plan(cfg, owners, policy, index, total, phase='train'):
    return dict(arm=policy.arm, index=index, total=total, phase=phase,
        route=((0, 0), (1, 0)), atomic_trace=dict(order=(0, 1)),
        visits=2, actual_repeats=2, route_sha256='B' * 64,
        receipt_sha256=d.route.sha([policy.arm, index, total, phase]))


@contextmanager
def actual_readers(mode='cost', damage=None):
    """원 V1 cost/readback 본문을 생성한 JSON으로 검사하며 텐서는 쓰지 않는다."""
    from scripts.p106b_shards import ShardWriter
    a = args(mode); geometry = SimpleNamespace(n_layers=2)
    corpus = dict(manifests=dict(train=dict(rows=1024), val=dict(rows=8)))
    with tempfile.TemporaryDirectory(prefix='p078_protocol_cpu_') as temporary:
        root = Path(temporary); reports = {}
        def path(name): return root / name
        def read(name): return json.loads(path(name).read_text())
        for arm in d.route.ARMS:
            directory = path('runs/eval/' + d.namespace(a) + '/' + mode + '_' + arm)
            writer = ShardWriter(directory, 'updates')
            events = []
            for i in range(32):
                event = dict(route=p.json_plan(toy_plan(geometry, [], d.route.Policy(arm), i, 32)),
                    update=i + 1, epoch=i // 8 + 1, actual_rows=128, actual_x_tokens=128,
                    assistant_targets=128, dummy_rows=0, padded_slots=131072, layer_visit_slots=262144,
                    model_id=1, optimizer_ids=[2, 3], ce=1.25, seconds=.5, gradient_max=2.)
                if damage is not None: damage(event, i)
                writer.append(event); events.append(event)
            manifest = writer.close(lineage=dict(toy=True))
            report = dict(status='COST32_COMPLETE', updates=32, checkpoint_writes=0,
                raw_manifest=manifest, geometry=vars(geometry), owners=[],
                update_seconds=[.5] * 32, grad_max=2., train_ce=1.25,
                checkpoint_sha256='C' * 64, initial_core_sha256='D' * 64)
            for key in ('actual_rows', 'actual_x_tokens', 'assistant_targets', 'dummy_rows', 'padded_slots', 'layer_visit_slots'):
                report[key] = sum(e[key] for e in events)
            def validation(secondary=False):
                policy = d.route.Policy('uniform_r2' if secondary else arm)
                expected = toy_plan(geometry, [], policy, 0, 1, 'secondary' if secondary else 'val')
                receipt = {k: expected[k] for k in ('actual_repeats', 'visits', 'route_sha256', 'receipt_sha256')}
                receipt['assistant_targets'] = 8
                return dict(scope='COMMON_UNIFORM_MISMATCH_SECONDARY' if secondary else 'MATCHED_TRAIN_POLICY_PRIMARY',
                    rows=8, batches=1, route_receipts=[receipt], assistant_targets=8, sum_layer_visits=2)
            answers = [dict(route=p.json_plan(toy_plan(geometry, [], d.route.Policy(arm), i, 8, 'probe')),
                attempts=1, precision='FP32_MATH', use_cache=False, mtp=False) for i in range(8)]
            report.update(before=dict(val=validation(), answers=answers), history=[dict(val=validation()) for _ in range(4)],
                final_primary=validation(), final_secondary=validation(True), final_answers=answers)
            reports[arm] = report
            for name, value in ((d.report_name(mode, arm, a), report), (d.activity_name(mode, arm, a), dict(toy=True))):
                target = path(name); target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value), encoding='utf-8')
        originals = {x: x.read_bytes() for x in root.rglob('*.json')}
        with patch.object(d, 'path', path), patch.object(d, 'read', read), \
             patch.object(d, 'inputs', return_value=corpus), \
             patch.object(d, 'closed', side_effect=lambda _a, _m, arm: copy.deepcopy(reports[arm])), \
             patch.object(d, 'digest', side_effect=lambda target: d.PARENT_SHA if target == path(d.PARENT) else 'C' * 64), \
             patch.object(d.route, 'plan', toy_plan):
            yield a, originals
        for target, original in originals.items():
            if target.read_bytes() != original: raise AssertionError('toy 원형 메타데이터가 바뀌었다')


class RepresentationTests(unittest.TestCase):
    def test_nested_tuple_list_equivalence_without_mutating_original(self):
        value = toy_plan(None, [], d.route.Policy('uniform_r2'), 0, 32)
        original = copy.deepcopy(value); normalized = p.json_plan(value)
        self.assertIsInstance(value['route'], tuple)
        self.assertIsInstance(normalized['route'], list)
        self.assertEqual(value, original)
        self.assertEqual(d.route.sha(value), d.route.sha(normalized))

    def test_order_difference_is_not_normalized_away(self):
        a = dict(route=((0, 0), (1, 0))); b = dict(route=((1, 0), (0, 0)))
        self.assertNotEqual(p.json_plan(a), p.json_plan(b))

    def test_value_difference_is_not_normalized_away(self):
        self.assertNotEqual(p.json_plan(dict(route=(1, 2))), p.json_plan(dict(route=[1, 3])))

    def test_nonfinite_is_rejected(self):
        with self.assertRaises(ValueError): p.json_plan(dict(value=float('nan')))

    def test_only_verifier_calls_get_lists(self):
        route = SimpleNamespace(plan=lambda: ((1, 0), (2, 0)))
        native = route.plan
        driver = SimpleNamespace(route=route, cost_receipt=lambda: route.plan(), budget=lambda: route.plan(), readback=lambda: route.plan())
        originals = [driver.cost_receipt, driver.budget, driver.readback]
        with p.verification_scope(driver):
            self.assertIs(route.plan, native)
            self.assertIsInstance(route.plan(), tuple)  # 실제 train/forward는 검산 변환 범위 밖이다.
            for call in (driver.cost_receipt, driver.budget, driver.readback): self.assertIsInstance(call(), list)
            self.assertIs(route.plan, native)
        self.assertEqual(originals, [driver.cost_receipt, driver.budget, driver.readback])

    def test_exception_restores_native_plan(self):
        route = SimpleNamespace(plan=lambda: (1, 2)); original = route.plan
        def broken():
            self.assertIsInstance(route.plan(), list)
            raise ValueError('fixture 오류')
        driver = SimpleNamespace(route=route, cost_receipt=broken, budget=broken, readback=broken)
        with p.verification_scope(driver):
            with self.assertRaises(ValueError): driver.cost_receipt()
            self.assertIs(route.plan, original)


class OriginalReaderTests(unittest.TestCase):
    def test_original_cost_body_fails_without_protocol_and_passes_with_it(self):
        with actual_readers() as (a, originals):
            with self.assertRaisesRegex(ValueError, 'route/compute'): d.cost_receipt(a, 'uniform_r2')
            with p.verification_scope(d): self.assertEqual(d.cost_receipt(a, 'uniform_r2')['updates'], 32)
            self.assertTrue(originals)

    def test_original_cost_reordered_route_still_fails(self):
        def damage(event, i):
            if i == 0: event['route']['route'].reverse()
        with actual_readers(damage=damage) as (a, _), p.verification_scope(d):
            with self.assertRaisesRegex(ValueError, 'route/compute'): d.cost_receipt(a, 'uniform_r2')

    def test_original_cost_changed_value_still_fails(self):
        def damage(event, i):
            if i == 0: event['route']['visits'] += 1
        with actual_readers(damage=damage) as (a, _), p.verification_scope(d):
            with self.assertRaisesRegex(ValueError, 'route/compute'): d.cost_receipt(a, 'uniform_r2')

    def test_original_readback_body_recounts_all_four_arms(self):
        with actual_readers('train') as (a, _):
            with self.assertRaisesRegex(ValueError, 'route/order'): d.readback(a)
            with p.verification_scope(d):
                result = d.readback(a)
            self.assertEqual(set(result['results']), set(d.route.ARMS))
            self.assertEqual(result['model_loads'], 0)

    def test_original_readback_wrong_route_is_not_excused(self):
        def damage(event, i):
            if i == 0: event['route']['route'][0][0] = 9
        with actual_readers('train', damage) as (a, _), p.verification_scope(d):
            with self.assertRaisesRegex(ValueError, 'route/order'): d.readback(a)


class SafetyTests(unittest.TestCase):
    def test_exact_original_source_pins(self):
        sources = p.source_identity()
        self.assertEqual({k: v['sha256'] for k, v in sources.items() if k in p.PINS}, p.PINS)

    def test_changed_source_rejected_before_import(self):
        with patch.object(p, 'identity', return_value=dict(sha256='0' * 64)), \
             patch.object(p.importlib, 'import_module', side_effect=AssertionError('import에 도달했다')):
            with self.assertRaisesRegex(ValueError, '고정한 원 소스'): p.load_driver()

    def test_check_only_is_model_corpus_checkpoint_torch_free(self):
        code = ("from scripts import diag_p078_route_protocol as p; import sys; "
                "assert 'torch' not in sys.modules; assert p.main(['--mode','train','--check-only']) == 0; "
                "assert 'torch' not in sys.modules")
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"model_loads": 0', result.stdout)

    def test_launches_adapter_not_original_in_new_session(self):
        process = SimpleNamespace(pid=123, wait=lambda **_: 0)
        with patch.object(p.subprocess, 'Popen', return_value=process) as launch:
            self.assertEqual(p.launch(['--mode', 'train', '--execute'], 60), 0)
        command = launch.call_args.args[0]
        self.assertIn(str(ROOT / p.SCRIPT), command)
        self.assertNotIn(str(ROOT / 'scripts/diag_p078_route_training.py'), command)
        self.assertEqual(command[-1], '--worker')
        self.assertTrue(launch.call_args.kwargs['start_new_session'])

    def test_worker_forwards_exact_original_argv_and_keeps_training_plan_native(self):
        argv = ['--mode', 'train', '--execute', '--worker', '--corpus-sha256', 'A' * 64]
        native = lambda: ((1, 0), (2, 0))
        def original_main(received):
            self.assertEqual(received, argv)
            self.assertIs(d.route.plan, native)
            self.assertIsInstance(d.route.plan(), tuple)
            self.assertEqual(d.cost_receipt(), [[1, 0], [2, 0]])
            self.assertIs(d.route.plan, native)
            return 0
        def record(_driver, _args, _argv, action, role):
            self.assertEqual(role, 'OWNED_WORKER')
            return action()
        with patch.object(p, 'load_driver', return_value=d), patch.object(p, 'recorded', side_effect=record), \
             patch.object(d.route, 'plan', native), patch.object(d, 'cost_receipt', side_effect=lambda: d.route.plan()), \
             patch.object(d, 'main', side_effect=original_main):
            self.assertEqual(p.main(argv), 0)

    def test_preview_cli_never_enters_original_main_worker_or_subprocess(self):
        with patch.object(p, 'load_driver', return_value=d), patch.object(p, 'budget_preview', return_value={'returncode': 8}) as preview, \
             patch.object(d, 'main', side_effect=AssertionError('원 main에 도달했다')), \
             patch.object(p.subprocess, 'Popen', side_effect=AssertionError('worker를 시작했다')):
            self.assertEqual(p.main(['--mode=budget-preview', '--execute']), 8)
        self.assertEqual(preview.call_args.args[0].mode, 'budget-preview')

    def test_preview_check_only_accepts_original_equal_form_and_abbreviation(self):
        for option in ('--mode', '--mo'):
            argv = [option + '=budget-preview', '--check-only']
            with patch.object(p, 'load_driver', return_value=d), patch.object(d, 'main', return_value=0) as original:
                self.assertEqual(p.main(argv), 0)
            self.assertEqual(original.call_args.args[0], [option + '=budget', '--check-only'])

    def test_timeout_kills_only_owned_group_and_preserves_original_semantics(self):
        process = SimpleNamespace(pid=123, wait=unittest.mock.Mock(side_effect=[subprocess.TimeoutExpired('fixture', 60), 0]))
        with patch.object(p.subprocess, 'Popen', return_value=process), patch.object(p.os, 'killpg') as kill:
            self.assertEqual(p.launch(['--mode', 'train', '--execute'], 60), 130)
        kill.assert_called_once_with(123, p.signal.SIGTERM)

    def test_path_escape_and_symlink_are_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'linked').symlink_to(root, target_is_directory=True)
            for name in ('../outside', 'datasets/TinyDataset/report.json', 'linked/report.json'):
                with self.assertRaises(ValueError): p.identity(name, root)

    def test_recorded_success_and_failure_preserve_originals(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(p, 'ROOT', Path(temporary)), \
             patch.object(p, 'source_identity', return_value={'fixture': 'source'}), \
             patch.object(d, 'signature', return_value=dict(toy=True)), redirect_stdout(io.StringIO()):
            a = args(); target = p.safe(d.report_name('cost', 'uniform_r2', a))
            target.parent.mkdir(parents=True); target.write_text('{"original":true}')
            original = target.read_bytes()
            for code in (0, 9): self.assertEqual(p.recorded(d, a, [], lambda: code, 'CPU_FIXTURE'), code)
            self.assertEqual(target.read_bytes(), original)
            receipts = list(p.safe('test_result/evidence/' + p.TAG).glob('*.json'))
            self.assertEqual(len(receipts), 2)
            self.assertEqual(sorted(json.loads(x.read_text())['returncode'] for x in receipts), [0, 9])

    def test_receipt_never_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(p, 'ROOT', Path(temporary)), redirect_stdout(io.StringIO()):
            first = p.write_receipt(dict(toy=True)); before = p.safe(first).read_bytes()
            second = p.write_receipt(dict(toy=False))
            self.assertNotEqual(first, second); self.assertEqual(p.safe(first).read_bytes(), before)

    def test_metadata_mutation_is_detected_not_repaired(self):
        with self.assertRaisesRegex(ValueError, '원형'): p.unchanged({'report': {'sha256': 'A'}}, {'report': {'sha256': 'B'}})

    def test_metadata_failure_after_original_failure_keeps_protocol_error_receipt(self):
        receipts = []
        with patch.object(p, 'source_identity', return_value={}), \
             patch.object(p, 'original_metadata', side_effect=[{}, ValueError('안전하지 않은 메타데이터')]), \
             patch.object(d, 'signature', return_value={}), \
             patch.object(p, 'write_receipt', side_effect=lambda value: receipts.append(value)), redirect_stdout(io.StringIO()):
            self.assertEqual(p.recorded(d, args(), [], lambda: 8, 'CPU_FIXTURE'), 9)
        self.assertEqual(receipts[0]['original_returncode'], 8)
        self.assertEqual(receipts[0]['returncode'], 9)
        self.assertIn('안전하지 않은 메타데이터', receipts[0]['error'])

    def test_preview_hold_writes_no_original_stage_and_retains_forecast(self):
        a = args('budget-preview'); captured = []
        with patch.object(p, 'source_identity', return_value={}), patch.object(p, 'original_metadata', return_value={}), \
             patch.object(d, 'signature', return_value=dict(toy=True)), \
             patch.object(d, 'budget', return_value=dict(fits=False, family_cap_seconds=144000, total_pending_seconds=99999.)), \
             patch.object(d, 'main', side_effect=AssertionError('원 main에 도달했다')), \
             patch.object(d, 'worker', side_effect=AssertionError('원 worker에 도달했다')), \
             patch.object(d, 'write', side_effect=AssertionError('원 write에 도달했다')), \
             patch.object(p, 'write_receipt', side_effect=lambda value: captured.append(copy.deepcopy(value))), redirect_stdout(io.StringIO()):
            result = p.budget_preview(a, d)
        self.assertEqual(result['returncode'], 8)
        self.assertEqual(result['status'], 'PREVIEW_HOLD_NOT_EXECUTED')
        self.assertEqual(result['original_activity_writes'], 0)
        self.assertEqual(captured[0]['details']['forecast']['family_cap_seconds'], 144000)

    def test_preview_expired_authority_remains_hold_without_activity(self):
        a = args('budget-preview')
        with patch.object(p, 'source_identity', return_value={}), patch.object(p, 'original_metadata', return_value={}), \
             patch.object(d, 'signature', return_value={}), patch.object(d, 'budget', side_effect=d.Hold('expired')), \
             patch.object(p, 'write_receipt'), patch.object(d, 'write', side_effect=AssertionError('원 activity 쓰기에 도달했다')), redirect_stdout(io.StringIO()):
            self.assertEqual(p.budget_preview(a, d)['returncode'], 8)

    def test_preview_missing_corpus_pin_does_not_reach_budget(self):
        a = args('budget-preview'); a.corpus_sha256 = None
        with patch.object(p, 'source_identity', return_value={}), patch.object(p, 'original_metadata', return_value={}), \
             patch.object(d, 'signature', return_value={}), \
             patch.object(d, 'budget', side_effect=AssertionError('정확한 SHA 없이 budget에 도달했다')), \
             patch.object(p, 'write_receipt'), redirect_stdout(io.StringIO()):
            result = p.budget_preview(a, d)
        self.assertEqual(result['returncode'], 8)
        self.assertEqual(result['original_activity_writes'], 0)


if __name__ == '__main__': unittest.main()
