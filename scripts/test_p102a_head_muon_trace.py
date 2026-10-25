"""CPU synthetic fixtures only. No TinyLM model, corpus, checkpoint, or CUDA."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
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
from scripts import diag_p102a_head_muon_trace as diag


OPTIONS = dict(lr=2e-4, momentum=.95, nesterov=True, ns_steps=5,
               weight_decay=0., scale_mode='rms')


class TraceTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_original_private_exact_and_hooks(self):
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')):
            result = diag.cpu_control(torch, muon)
        self.assertTrue(result['exact'])
        self.assertTrue(result['hooks_preserved'])
        self.assertEqual(result['cuda_calls'], 0)

    def test_replay_actual_nonzero_weight_and_no_mutation(self):
        initial = torch.tensor([[.1, -.2], [.3, .4], [-.5, .6]])
        gradient = torch.tensor([[.2, -.1], [.05, .4], [-.3, .15]])
        initial_copy, gradient_copy = initial.clone(), gradient.clone()
        original_ns, old_stop = muon._newton_schulz, diag.old.HARD_STOP
        a = diag.replay_one(torch, muon, initial, gradient, OPTIONS, device='cpu')
        b = diag.replay_one(torch, muon, initial, gradient, OPTIONS, device='cpu')
        for key in a:
            self.assertTrue(torch.equal(a[key], b[key]), key)
        self.assertTrue(torch.equal(initial, initial_copy))
        self.assertTrue(torch.equal(gradient, gradient_copy))
        self.assertFalse(torch.equal(a['weight'], initial))
        self.assertIs(muon._newton_schulz, original_ns)
        self.assertIs(diag.old.HARD_STOP, old_stop)

    def test_fp32_facade_prefix_and_nonmutation(self):
        gradient = torch.tensor([[.7, -.1], [.05, -.4], [-.3, .15]])
        original = gradient.clone()
        diag.validate_ns_interface(muon._newton_schulz)
        answer = diag.ns_value(torch, muon._newton_schulz, gradient, fp32=True)
        self.assertEqual(answer.dtype, torch.float32)
        self.assertTrue(bool(torch.isfinite(answer).all()))
        self.assertTrue(torch.equal(gradient, original))
        actual = muon._newton_schulz(gradient)
        result = diag.prefix_trace(torch, muon, gradient, gradient.clone(), actual, actual.clone(),
            dict(atol=2e-6, rtol=1e-5), device='cpu')
        self.assertTrue(result['original_bf16']['actual_ns_output_exact'])
        self.assertTrue(result['original_bf16']['stages']['exact'])
        self.assertTrue(result['fp32_diagnostic']['stages']['exact'])

    def test_prefix_must_reproduce_actual(self):
        g = torch.tensor([[.7, -.1], [.05, -.4]])
        wrong = torch.zeros_like(g)
        with self.assertRaisesRegex(ValueError, 'prefix5'):
            diag.prefix_trace(torch, muon, g, g, wrong, wrong,
                dict(atol=2e-6, rtol=1e-5), device='cpu')

    def test_actual_matrix_replay_orchestration_all85_cpu_synthetic(self):
        names = (*diag.REPRESENTATIVES, *(f'synthetic.{i}' for i in range(82)))
        initial, captures = {}, []
        for arm in range(2):
            capture = {key: {} for key in ('options', 'clipped', 'ns_input', 'ns_output', 'updated', 'buffers')}
            for index, name in enumerate(names):
                initial[name] = torch.tensor([[.1, -.2], [.3, .4]])
                gradient = torch.tensor([[.2, -.1], [.05, .4]]) + arm * 1e-8
                value = diag.replay_one(torch, muon, initial[name], gradient, OPTIONS, device='cpu')
                capture['options'][name] = dict(OPTIONS)
                capture['clipped'][name] = gradient
                for source, target in (('ns_input', 'ns_input'), ('ns_output', 'ns_output'),
                                       ('updated', 'weight'), ('buffers', 'buffer')):
                    capture[source][name] = value[target]
            captures.append(capture)
        class Journal:
            def __init__(self): self.rows = []
            def append(self, value): self.rows.append(value)
        journal = Journal()
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')):
            report = diag.replay_all(torch, muon, initial, *captures,
                dict(atol=2e-6, rtol=1e-5), None, journal, device='cpu')
        self.assertEqual(report['matrix_count'], 85)
        self.assertEqual(len(journal.rows), 85)
        self.assertTrue(report['actual_updates_reproduced_exactly'])
        self.assertEqual(set(report['prefixes']), set(diag.REPRESENTATIVES))
        del captures[1]['ns_input'][names[0]]
        with self.assertRaisesRegex(ValueError, 'missing actual'):
            diag.replay_all(torch, muon, initial, *captures,
                dict(atol=2e-6, rtol=1e-5), None, journal, device='cpu')

    def test_nonfinite_cannot_be_exact_control(self):
        values = {'p': torch.tensor([float('nan')])}
        table = diag.comparison(torch, values, values, dict(atol=2e-6, rtol=1e-5))
        self.assertFalse(table['exact'])
        self.assertFalse(table['close'])

    def test_capture_budget_rejects_without_model_or_assets(self):
        class Parameter:
            requires_grad = True
            def numel(self): return 1000000000
            def element_size(self): return 4
        class FakeModel:
            def state_dict(self): return {'p': Parameter()}
            def parameters(self): return [Parameter()]
        fake_muon = SimpleNamespace(split_params=lambda model: ([Parameter()] * 85, []))
        with self.assertRaisesRegex(ValueError, 'CPU capture'):
            diag.memory_plan(FakeModel(), fake_muon)

    def test_missing_gradient_fails_before_optimizer(self):
        p = torch.nn.Parameter(torch.ones(2, 2))
        capture = diag.PostClipCapture({'p': p}, expected=1)
        optimizer = torch.optim.SGD([p], lr=.1)
        proxy = diag.OptimizerProxy(optimizer, capture)
        with self.assertRaisesRegex(ValueError, 'non-None'):
            proxy.step()
        self.assertTrue(torch.equal(p, torch.ones_like(p)))

    def test_proxy_captures_before_step_without_aliases(self):
        p = torch.nn.Parameter(torch.ones(2, 2))
        p.grad = torch.full_like(p, .25)
        capture = diag.PostClipCapture({'p': p}, expected=1)
        optimizer = torch.optim.SGD([p], lr=.1)
        proxy = diag.OptimizerProxy(optimizer, capture)
        self.assertIs(proxy.param_groups, optimizer.param_groups)
        proxy.step()
        p.grad.fill_(4.)
        self.assertTrue(torch.equal(capture.values['p'], torch.full_like(p, .25)))
        proxy.zero_grad(set_to_none=True)
        self.assertIsNone(p.grad)

    def test_observer_rejects_missing_and_extra_matrices(self):
        observer = diag.NSObserver(torch, muon._newton_schulz, ('p',))
        with self.assertRaisesRegex(ValueError, 'not every'):
            observer.finish()
        observer(torch.eye(2))
        observer.finish()
        with self.assertRaisesRegex(ValueError, 'call count'):
            observer(torch.eye(2))

    def test_namespace_is_exact_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / 'test_result/evidence' / diag.TAG
            self.assertEqual(diag.output_path(root), expected)
            expected.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                diag.output_path(root)

    def test_new_deadline_without_mutating_old(self):
        now = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
        args = SimpleNamespace(deadline='2026-10-24T08:40:00+09:00', max_wall_sec=1200)
        old_stop = diag.old.HARD_STOP
        self.assertEqual(diag.validate_execution(args, now), diag.HARD_STOP)
        self.assertIs(diag.old.HARD_STOP, old_stop)
        for deadline, wall in (('2026-10-24T08:41:00+09:00', 60),
                               ('2026-10-23T19:00:30+09:00', 60),
                               ('2026-10-23T19:00:00+09:00', 60),
                               ('2026-10-24T08:40:00', 60),
                               ('2026-10-24T08:40:00+09:00', 59),
                               ('2026-10-24T08:40:00+09:00', 1201)):
            with self.subTest(deadline=deadline, wall=wall), self.assertRaises(ValueError):
                diag.validate_execution(SimpleNamespace(deadline=deadline, max_wall_sec=wall), now)

    def test_missing_tensor_never_passes_comparator(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            diag.comparison(torch, {'p': None}, {'p': None}, dict(atol=2e-6, rtol=1e-5))

    def test_source_only_cli_imports_no_torch_and_reads_no_assets(self):
        code = ("import sys; from scripts import diag_p102a_head_muon_trace as d; "
                "assert 'torch' not in sys.modules; "
                "d.main(['--check-only']); assert 'torch' not in sys.modules")
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            text=True, capture_output=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['model_calls'], 0)
        self.assertEqual(receipt['cuda_calls'], 0)
        self.assertEqual(receipt['asset_reads'], 0)
        self.assertEqual(receipt['tag'], diag.TAG)

    def test_modes_are_exclusive_and_execute_receipt_precedes_admission(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            diag.main(['--execute', '--check-only'])
        args = SimpleNamespace(deadline='2026-10-24T08:40:00+09:00', max_wall_sec=600,
                               source_sha256='WRONG')
        with patch.object(diag, 'validate_execution', return_value=diag.HARD_STOP), \
                patch.object(diag.old, 'gpu_admission', side_effect=AssertionError('no GPU query')), \
                self.assertRaisesRegex(ValueError, 'receipt'):
            diag.run(args, {})

    def test_namespace_guard_detects_original_ns_rebinding(self):
        # No mutation of the real module: a synthetic module exercises the guard.
        fake = SimpleNamespace(Muon=muon.Muon, _newton_schulz=muon._newton_schulz)
        guard = diag.GlobalIdentity(fake)
        fake._newton_schulz = object()
        with self.assertRaisesRegex(ValueError, 'globals'):
            guard.check()


if __name__ == '__main__':
    unittest.main()
