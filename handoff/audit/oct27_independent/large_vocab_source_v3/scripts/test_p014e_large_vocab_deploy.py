"""Shared source rejection, actual product EOS1 and separate prefill budgeting."""
from copy import deepcopy
import math
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import torch
from torch import nn
from scripts import diag_p014e_large_vocab_deploy as d


class AliasModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.a = nn.Linear(4, 4, bias=False)
        self.b = self.a


class Tokenizer:
    def decode(self, ids, skip_special_tokens=False):
        return ','.join(str(x) for x in ids)

    def token_to_id(self, token):
        return {'<eos>': 1, '<bos>': 2}.get(token)


class ScriptedModel(nn.Module):
    """CPU numeric fixture, no checkpoint or learned-language quality claim."""
    def __init__(self, choices):
        super().__init__()
        self.choices = choices
        self.index = 0

    def forward(self, tokens, **kwargs):
        logits = torch.full((1, 1, 16), -20.)
        logits[0, 0, self.choices[self.index]] = 20.
        self.index += 1
        old = kwargs.get('past_kv')
        count = tokens.shape[1] + (old[0][0].shape[2] if old else 0)
        key = torch.zeros(1, 1, count, 1)
        return logits, {0: (key, key.clone())}


class LargeVocabContract(unittest.TestCase):
    def test_workload_name_cannot_disguise_wrong_lengths_or_language(self):
        base = dict(workloads=[dict(id=name, language=language, prompt_tokens=count, text='source')
                    for name, language, count in [('ko128','ko',128),('en128','en',128),('ko512','ko',512),('en512','en',512)]],
            answer_cases=[dict(id=name, language=language, mode='plain', question='question')
                    for name, language in [('ko_arithmetic','ko'),('en_arithmetic','en'),('ko_context','ko'),('en_context','en')]])
        d.validate_texts(base)
        for kind in ('length','language','duplicate','chatml'):
            altered = deepcopy(base)
            if kind == 'length':
                altered['workloads'][2]['prompt_tokens'] = 128
            elif kind == 'language':
                altered['workloads'][1]['language'] = 'ko'
            elif kind == 'duplicate':
                altered['answer_cases'][1] = altered['answer_cases'][0]
            else:
                altered['answer_cases'][2]['mode'] = 'chatml'
            with self.assertRaises(ValueError):
                d.validate_texts(altered)

    def test_alias_conflict_rejected_before_strict_load(self):
        model = AliasModel()
        saved = {k: v.clone() for k, v in model.state_dict().items()}
        before = {k: v.clone() for k, v in saved.items()}
        d.checked_state(model, saved)
        saved['b.weight'][0, 0] += 1
        with self.assertRaises(ValueError):
            d.checked_state(model, saved)
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in model.state_dict().items()))

    def test_nonfinite_or_dtype_rejected_without_copy(self):
        model = AliasModel()
        for kind in ('dtype', 'nan', 'missing'):
            state = {k: v.clone() for k, v in model.state_dict().items()}
            if kind == 'dtype':
                state['a.weight'] = state['a.weight'].half()
            elif kind == 'nan':
                state['a.weight'][0, 0] = math.nan
            else:
                del state['b.weight']
            with self.assertRaises(ValueError):
                d.checked_state(model, state)

    def test_actual_product_sampler_uses_gemma_eos1(self):
        cfg = SimpleNamespace(vocab_size=16, max_seq_len=32)
        budget = SimpleNamespace(check=lambda: None)
        row = d.generation(ScriptedModel([7, 1, 9]), cfg, Tokenizer(), [2, 8], 'cpu', 3,
                           budget, natural=True, observed=True)
        self.assertEqual(row['generated_ids'], [7, 1])
        self.assertEqual(row['metadata']['finish_reason'], 'EOS')
        self.assertEqual(len(row['pick_times_seconds']), 2)
        self.assertEqual(row['eos_id'], 1)

    def test_forced_generation_keeps_eos_token_and_full_count(self):
        cfg = SimpleNamespace(vocab_size=16, max_seq_len=32)
        row = d.generation(ScriptedModel([7, 1, 9]), cfg, Tokenizer(), [2, 8], 'cpu', 3,
                           SimpleNamespace(check=lambda: None), observed=False)
        self.assertEqual(row['generated_ids'], [7, 1, 9])
        self.assertEqual(row['metadata']['generated_tokens'], 3)
        self.assertFalse(row['eos_stop_enabled'])

    def test_input_outside_declared_output_vocab_is_refused(self):
        with self.assertRaises(ValueError):
            d.generation(ScriptedModel([1]), SimpleNamespace(vocab_size=16), Tokenizer(), [16],
                         'cpu', 1, SimpleNamespace(check=lambda: None))

    def test_prefill_cost_is_per_request_not_per_output_token(self):
        probes = [dict(pick_times_seconds=[1., 1.01, 1.02, 1.03]),
                  dict(pick_times_seconds=[2., 2.01, 2.02, 2.03])]
        r = d.forecast(probes)
        expected = 3*(4*((2+.03)+5*(2+.15))+4*(2+.31))+60
        self.assertAlmostEqual(r['conservative_seconds'], expected)
        for bad in ([], probes[:1], [dict(pick_times_seconds=[1.])]*2):
            with self.assertRaises(ValueError):
                d.forecast(bad)

    def test_deployment_refuses_old_checkpoint_before_any_tensor_read(self):
        report = {}
        with patch.object(torch, 'load', side_effect=AssertionError('tensor read forbidden')) as reader:
            with d.guarded_deploy_loads(report):
                with self.assertRaises(ValueError):
                    torch.load(d.CP, weights_only=True)
                with self.assertRaises(ValueError):
                    torch.load(d.folder()/'candidate.pt', weights_only=False)
            self.assertFalse(reader.called)
        self.assertEqual(report['torch_load_files'], [])

    def test_existing_upstream_hold_is_not_a_new_model_error(self):
        profile = {'_sha256': 'A'*64}
        source = {'files': {}, 'sha256': 'B'*64}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'export.json').write_text(json.dumps(dict(mode='export', source=source,
                profile_sha256='A'*64, exit_code=8, status='BUDGET_HOLD_NOT_FULL_SUITE')))
            with patch.object(d, 'report_path', lambda mode: folder/(mode+'.json')), patch.object(d, 'identity', lambda: source):
                pending = d.pending_predecessors('deploy-cpu', profile)
                self.assertEqual(pending[0]['actual_exit'], 8)
                self.assertEqual(pending[1]['reason'], 'NOT_RUN')
                with self.assertRaises(ValueError):
                    d.pending_predecessors('deploy-cpu', {'_sha256': 'C'*64})

    def test_cleanup_failures_do_not_skip_later_checkpoint_verification(self):
        calls = []
        class Broken:
            def parameters(self):
                return ()
            def clear_quant(self):
                calls.append('clear')
                raise RuntimeError('clear failed')
            def to(self, device):
                calls.append('move')
                raise RuntimeError('move failed')
        proof = {'primary_error': {'type': 'ValueError', 'message': 'original cause'}}
        def digest(_):
            calls.append('checkpoint')
            return d.CP_SHA
        with (patch('scripts.interactive_research_infer.state_fingerprint', side_effect=RuntimeError('fingerprint failed')),
              patch.object(d.resource, 'digest', digest)):
            errors = d.cleanup_legacy_source(Broken(), 'expected', Path('unused'),
                SimpleNamespace(check=lambda: calls.append('budget')), proof)
        self.assertEqual([x['stage'] for x in errors], ['final_core', 'clear_quant', 'model_to_cpu'])
        self.assertEqual(calls, ['clear', 'move', 'checkpoint', 'budget'])
        self.assertEqual(proof['primary_error']['message'], 'original cause')
        self.assertTrue(proof['original_checkpoint_unchanged'])


if __name__ == '__main__':
    unittest.main()
