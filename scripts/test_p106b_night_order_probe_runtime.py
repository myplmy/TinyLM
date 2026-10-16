"""Pure runtime scope/namespace/redecode contracts; no actual HF/model reads."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_order_probe as d
from scripts.test_p106b_night_order_probe import panel, events_for


class ProbeRuntimeTests(unittest.TestCase):
    def test_no_training_and_independent_namespace(self):
        self.assertEqual(d.ENDPOINTS, ('base_qa', 'unique32k'))
        self.assertNotEqual(d.EVIDENCE, d.panel.EVIDENCE)
        self.assertNotEqual(d.FROZEN, d.unique.FROZEN)
        with self.assertRaises(ValueError): d.full_endpoint('selected_by_test')

    def test_explicit_no_legacy_gate_credit(self):
        with patch.object(d.qa.data, 'digest', return_value='A' * 64): r = d.info()
        self.assertEqual(r['views'], [1, 3]); self.assertFalse(r['legacy_order_training_gate_credited'])
        self.assertEqual(r['updates'], 0); self.assertEqual(r['checkpoints_written'], 0)
        self.assertEqual(r['max_new'], 128)

    def test_real_wire_uses_actual_tokenizer_lengths_and_balanced_order(self):
        class Tok:
            def encode(self, text): return NS(ids=list(range(20)))
        r = d.wire(panel(), Tok())
        self.assertEqual(len(r['schedule']), 128); self.assertEqual(r['max_prompt_tokens'], 20)
        self.assertEqual(r['schedule'][:4], [[0, 1], [0, 3], [1, 3], [1, 1]])
        self.assertEqual(len(r['review_indices']), 8); self.assertEqual(len(set(r['review_indices'])), 8)

    def test_full_prompt_budget_does_not_truncate(self):
        tok = NS(encode=lambda text: NS(ids=[0] * 897))
        with self.assertRaises(ValueError): d.wire(panel(), tok)

    def test_recount_checks_actual_frozen_token_count(self):
        pairs = panel(); events = events_for(pairs)
        frozen = dict(wire=dict(prompt_tokens=[{'1': 40, '3': 40}] * 64))
        self.assertEqual(d.recount(events, pairs, frozen)['cases'], 128)
        frozen['wire']['prompt_tokens'] = [{'1': 41, '3': 40}] * 64
        with self.assertRaises(ValueError): d.recount(events, pairs, frozen)

    def test_redecode_equality_is_not_correctness_and_same_prompt_required(self):
        pairs = panel(); events = events_for(pairs); old = [dict(x) for x in events if x['view'] == 1]
        r = d.repeat_agreement(events, old); self.assertEqual(r['n'], 64); self.assertEqual(r['same_answer'], 64)
        old[0] = dict(old[0], answer='different')
        self.assertEqual(d.repeat_agreement(events, old)['same_answer'], 63)
        old[0] = dict(old[0], messages=[])
        with self.assertRaises(ValueError): d.repeat_agreement(events, old)

    def test_no_optimizer_or_checkpoint_save_or_old_completion_writes(self):
        source = (ROOT / 'scripts/diag_p106b_night_order_probe.py').read_text()
        self.assertNotIn('optimizer.step(', source); self.assertNotIn('torch.save(', source)
        self.assertNotIn('qa.write(e.EVIDENCE', source)

    def test_all_six_primary_evaluations_and_base_are_checked(self):
        expected = ['base_qa', *d.prompt.ENDPOINTS, *d.unique.ENDPOINTS]
        with patch.object(d, 'verified_primary', return_value=(None, None, None, 'A' * 64, [])) as verify:
            self.assertEqual(set(d.primary_prerequisites()), set(expected))
            self.assertEqual([c.args[1] for c in verify.call_args_list], expected)

    def test_missing_primary_evaluation_is_not_credited(self):
        def verify(provider, endpoint):
            if endpoint == 'prompt01_best': raise FileNotFoundError('primary evaluation missing')
            return None, None, None, 'A' * 64, []
        with patch.object(d, 'verified_primary', side_effect=verify):
            with self.assertRaises(FileNotFoundError): d.primary_prerequisites()

    def test_report_checkpoint_path_tampering_is_rejected(self):
        cp = ROOT / 'runs/ckpt/probe_synthetic.pt'; identity = 'A' * 64
        report = dict(status='READONLY_ORDER_PROBE_COMPLETE', endpoint='base_qa',
            code_sha256={}, input_report_sha256=identity, primary_full_report_sha256=identity,
            required_primary_report_sha256={}, checkpoint='runs/ckpt/wrong_synthetic.pt',
            checkpoint_sha256=identity, initial_core_sha256=identity, body_proof={},
            directory=str((d.LOCAL / 'base_qa').relative_to(ROOT)),
            updates=0, checkpoints_written=0, manifest=dict(rows=128))
        with patch.object(d, 'full_endpoint', return_value=(cp, identity, identity, identity, [])), \
                patch.object(d, 'primary_prerequisites', return_value={}), \
                patch.object(d, 'info', return_value=dict(code_sha256={})), \
                patch.object(d.qa, 'required', return_value=report), \
                patch.object(d.qa.data, 'digest', return_value=identity), \
                patch.object(d.e, 'body_proof', return_value={}):
            with self.assertRaises(ValueError): d.endpoint_report('base_qa', {}, [])


if __name__ == '__main__': unittest.main()
