"""CPU-only resource admission, global target denominator and partial-report tests."""
from pathlib import Path
import sys
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import hashlib
import io
import json
from contextlib import redirect_stdout
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from scripts import diag_p107_hybrid_mntp as d
from tinylm.train import hybrid_mntp as h

torch.set_num_threads(1)


class DriverContract(unittest.TestCase):
    def test_fixture_reproducible_complete_shift_last_target_and_uniform_selection(self):
        left = d.fixture(1, batch=2, length=128, micros=2)
        right = d.fixture(1, batch=2, length=128, micros=2)
        for (ca, ma), (cb, mb) in zip(left, right):
            self.assertTrue(torch.equal(ca.inputs, cb.inputs))
            self.assertTrue(torch.equal(ma.inputs, mb.inputs))
            self.assertTrue(torch.equal(ma.targets, mb.targets))
            self.assertTrue(bool((ca.targets[:, -1] >= 35).all()))
            self.assertEqual(ca.target_count, 2 * (128 - 3))
            self.assertEqual(ma.target_count, int(ma.selected_positions.sum()))
            self.assertTrue(bool((ma.inputs[ma.selected_positions[:, :-1]] == 13).all()))

    def test_all_conditions_execute_same_micro_count_and_hybrid_not_double_input(self):
        pairs = d.fixture(2, batch=2, length=128, micros=4)
        for name in set(d.ORDER):
            tasks, totals, weights = d.tasks(pairs, name)
            self.assertEqual(len(tasks), 4)
            self.assertEqual(sum(x.executed_input_tokens for x, _, _ in tasks), 1024)
            self.assertEqual(sum(totals.values()), sum(x.target_count for x, _, _ in tasks))
            self.assertEqual(sum(weights.values()), 1.)
        tasks, totals, _ = d.tasks(pairs, 'hybrid')
        self.assertEqual([kind for batch, kind, explicit in tasks], ['causal','causal','masked','masked'])
        self.assertEqual(totals['causal'], pairs[0][0].target_count + pairs[1][0].target_count)

    def test_different_target_counts_use_global_objective_means_not_micro_means(self):
        # Masked target counts deliberately differ; compare full sums independently.
        x = torch.tensor([[40,41,42,43,44,45,46,47,48]], dtype=torch.long)
        docs = torch.zeros_like(x)
        masks = [torch.tensor([[False,True,False,False,False,False,False,False,False]]),
                 torch.tensor([[False,True,True,True,False,False,False,False,False]])]
        pairs = [(h.causal_batch(x, docs, vocab_size=128), h.mntp_batch(x, docs, m, vocab_size=128)) for m in masks]
        chosen, totals, weights = d.tasks(pairs, 'mntp')
        torch.manual_seed(6)
        logits = [torch.randn(1,8,128,requires_grad=True) for _ in chosen]
        calculated = sum(weights[n] * h.objective_mean(z,b.targets)[0] * b.target_count / totals[n]
                         for z,(b,n,_) in zip(logits,chosen))
        losses = [torch.nn.functional.cross_entropy(z.reshape(-1,128),b.targets.flatten(),ignore_index=-100,reduction='sum')
                  for z,(b,n,_) in zip(logits,chosen)]
        expected = sum(losses) / 4
        self.assertTrue(torch.allclose(calculated, expected, atol=1e-7, rtol=1e-6))

    def test_invalid_profile_rejected_before_any_asset_reference_read(self):
        with patch.object(d.resource, 'read_ref', side_effect=AssertionError('asset read forbidden')) as read:
            with self.assertRaises(ValueError): d.validate({'schema':'BAD'}, SimpleNamespace(max_wall_sec=900))
            self.assertFalse(read.called)

    def test_odd_hybrid_micro_count_and_unknown_condition_rejected(self):
        pairs = d.fixture(2, batch=2, length=128, micros=3)
        with self.assertRaises(ValueError): d.tasks(pairs, 'hybrid')
        with self.assertRaises(ValueError): d.tasks(pairs, 'unexpected')

    def test_partial_block_preserves_warmup_first_measurement_and_peak(self):
        fake = SimpleNamespace(cuda=SimpleNamespace(memory_allocated=lambda:10, memory_reserved=lambda:20,
            reset_peak_memory_stats=lambda:None, max_memory_allocated=lambda:30, max_memory_reserved=lambda:40))
        report = {'blocks':[]}
        def run(index, progress):
            if index == 2:
                progress.update(completed_micro_batches=13, executed_input_tokens=13*8192, phase='BACKWARD_SYNC')
                raise RuntimeError('second measurement failed')
            progress.update(seconds=index+1., status='UPDATE_COMPLETE', completed_micro_batches=16, executed_input_tokens=131072)
            return progress
        with self.assertRaisesRegex(RuntimeError, 'second measurement'):
            d.record_block(report, 0, 'mntp', run, fake)
        row = report['blocks'][0]
        self.assertEqual(row['warmup']['seconds'], 1.)
        self.assertEqual(row['measured'][0]['seconds'], 2.)
        self.assertEqual(row['measured'][1]['completed_micro_batches'], 13)
        self.assertEqual(row['measured'][1]['executed_input_tokens'], 13*8192)
        self.assertEqual(row['measured'][1]['phase'], 'BACKWARD_SYNC')
        self.assertEqual(row['status'], 'PARTIAL_BLOCK_ERROR')
        self.assertEqual(row['peak_allocated_bytes'], 30)

    def test_reused_runtime_helpers_are_pinned_and_any_change_changes_identity(self):
        before = d.identity()
        required = {'scripts/diag_p013_context_curriculum.py', 'tinylm/train/context_curriculum.py',
                    'scripts/diag_p014e_packed_deploy.py', 'scripts/p014e_packed_g128.py', 'tinylm/model/lut.py'}
        self.assertTrue(required.issubset(before['files']))
        real_digest = d.resource.digest
        def changed(path):
            return 'F' * 64 if str(path).endswith('diag_p013_context_curriculum.py') else real_digest(path)
        with patch.object(d.resource, 'digest', side_effect=changed):
            self.assertNotEqual(before['sha256'], d.identity()['sha256'])

    def test_original_non_timeout_error_is_not_hidden_by_cleanup_timeout_chain(self):
        report = {}
        try:
            try:
                raise ValueError('original loader or reserved-token failure')
            finally:
                raise TimeoutError('later cleanup timeout')
        except TimeoutError as error:
            d.remember_error(report, error)
        self.assertEqual(report['primary_cost_error']['type'], 'ValueError')
        self.assertFalse(report['primary_cost_error_is_timeout'])
        self.assertEqual(len(report['exception_chains'][0]), 2)

    def test_independent_final_checks_continue_after_first_cleanup_error(self):
        seen = []; report = {}
        def fail_close(torch, proof):
            seen.append('cuda'); proof['entry'] = 123
            raise RuntimeError('injected cleanup failure')
        def source(): seen.append('source')
        def core(): seen.append('core')
        with patch.object(d.resource, 'close_cuda', side_effect=fail_close):
            result = d.independent_final_checks(report, [('cuda',lambda:d.close_owned_cuda(None,report)),('source',source),('core',core)])
        self.assertFalse(result)
        self.assertEqual(seen, ['cuda','source','core'])
        self.assertEqual(report['final_cuda_cleanup'], {'entry':123})
        self.assertEqual(report['final_verification_errors'][0]['stage'], 'cuda')

    def test_actual_tokenizer_byte_change_is_rejected_even_at_same_size(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'tokenizer.json'; path.write_bytes(b'ORIGINAL')
            ref = dict(path='explicit-fixture.json', bytes=8, sha256=hashlib.sha256(b'ORIGINAL').hexdigest().upper())
            with patch.object(d.resource, 'safe', return_value=path):
                self.assertEqual(d.verify_tokenizer_ref(ref), ref['sha256'])
                path.write_bytes(b'ALTERED!')
                with self.assertRaises(ValueError): d.verify_tokenizer_ref(ref)

    def test_metadata_admission_timeout_is_hold8_with_no_model_or_evidence_write(self):
        output = io.StringIO()
        args = ['diag','--profile','explicit.json','--profile-sha256','A'*64,'--max-wall-sec','900','--check-only']
        with patch.object(sys,'argv',args), patch.object(d.resource,'read_ref',return_value={}), \
             patch.object(d,'validate',side_effect=TimeoutError('deadline too short')), \
             patch.object(d.resource,'write_new',side_effect=AssertionError('metadata must not write')) as write, redirect_stdout(output):
            result = d.main()
        self.assertEqual(result,8); self.assertFalse(write.called)
        row = json.loads(output.getvalue()); self.assertEqual((row['models'],row['gpu_calls']),(0,0))


if __name__ == '__main__':
    unittest.main()
