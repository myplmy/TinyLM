#!/usr/bin/env python3
"""Synthetic CPU contracts only; no actual source, checkpoint or GPU loading."""
from __future__ import annotations

import ast
from contextlib import ExitStack, nullcontext, redirect_stdout
import copy
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import torch  # CPU fixture tensors; import before patch.dict(sys.modules) snapshots.

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_span_readout as driver


def serialize(conv, kind='chatml', *, add_generation_prompt=False):
    assert kind == 'chatml'
    out = ''
    for message in conv['messages']:
        out += '<|im_start|>' + message['role'] + '\n' + driver.text(message) + '<|im_end|>\n'
    return out + ('<|im_start|>assistant\n' if add_generation_prompt else '')


class TinyTokenizer:
    """ASCII fixture with genuine multi-character control-token offsets."""
    controls = {'<|im_start|>': 3, '<|im_end|>': 4, '<eos>': 2}

    def encode(self, value):
        ids, offsets = [], []
        at = 0
        while at < len(value):
            matched = next((s for s in self.controls if value.startswith(s, at)), None)
            width = len(matched) if matched else 1
            ids.append(self.controls[matched] if matched else ord(value[at]) + 100)
            offsets.append((at, at + width)); at += width
        return types.SimpleNamespace(ids=ids, offsets=offsets)

    def decode(self, ids, skip_special_tokens=False):
        reverse = {v: k for k, v in self.controls.items()}
        return ''.join(('' if skip_special_tokens else reverse[v]) if v in reverse else chr(v - 100) for v in ids)

    def token_to_id(self, token):
        return self.controls.get(token)

    def to_str(self):
        return 'SYNTHETIC_TOKENIZER_ONLY'


def source_row(index, language='en', split='train'):
    reference = 'A' + str(index) + ' Z'
    user = 'Reference:\n' + reference + '\nQuestion:\nWhich final letter?'
    lo = user.index(reference); start = lo + reference.index('Z')
    row = dict(messages=[dict(role='user', content=user), dict(role='assistant', content='Z')],
        meta=dict(kind='natural_first_qa', language=language, semantic_root_id=driver.sha([split, language, index]),
                  user_reference_range=[lo, lo + len(reference)], user_answer_range=[start, start + 1]))
    prompt = serialize(dict(messages=row['messages'][:1]), add_generation_prompt=True)
    origin = prompt.index(user); bank = driver.method.build_bank(TinyTokenizer(), prompt, [origin + lo, origin + lo + len(reference)])
    position = next(i for i, token in enumerate(bank.positions) if bank.offsets[token] == (origin + start, origin + start + 1))
    label = dict(query=bank.query, positions=list(bank.positions), start=position, end=position)
    return row, label


def generation(case, answer='Z', reason='STOP_SEQUENCE'):
    tokenizer = TinyTokenizer(); content = tokenizer.encode(answer).ids
    terminal = [4] if reason == 'STOP_SEQUENCE' else [2] if reason == 'EOS' else []
    ids = content + terminal
    g = dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        max_new=driver.MAX_NEW, eos_token_available=True, stop_at_eos_requested=True,
        stop_at_eos_effective=True, stop_token_sequences=[[4]],
        candidate_answers_supplied=False, terminal_only_removed=True,
        prompt_sha256=driver.sha(case['inference']['prompt']), prompt_ids_sha256=driver.sha(case['encoding']['ids']),
        prompt_tokens=len(case['encoding']['ids']), generated_ids=ids, terminal_ids=terminal,
        generated_tokens=len(ids), finish_reason=reason, matched_stop_sequence=terminal if reason == 'STOP_SEQUENCE' else None,
        generated_ids_sha256=driver.sha(ids), content_ids_sha256=driver.sha(content),
        body_utf8_sha256=__import__('hashlib').sha256(answer.encode()).hexdigest().upper())
    return dict(answer=answer, generation=g)


def event_for(case, *, start=None, end=None):
    bank = driver.method.build_bank(TinyTokenizer(), case['inference']['prompt'], case['inference']['reference_range'])
    starts = [0.] * len(bank.positions) if start is None else start
    ends = [0.] * len(bank.positions) if end is None else end
    return dict(id=case['id'], case_sha256=driver.sha(case), bank_sha256=case['bank_sha256'],
        start_scores=starts, end_scores=ends,
        policies={p: asdict(driver.method.select_span(bank, starts, ends, p)) for p in driver.method.POLICIES},
        vocabulary=generation(case))


@dataclass
class FakeConfig:
    dim: int = 768
    n_layers: int = 14
    vocab_size: int = 32768
    tie_mlp: bool = False
    max_seq_len: int = 1024
    mtp_aux: bool = False


class Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='p106b_span_readout_fixture_')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name, value in dict(ROOT=root, CACHE=root / 'cache', RAW=root / 'raw', EVIDENCE=root / 'small').items():
            self.stack.enter_context(patch.object(driver, name, value))
        self.metadata = dict(schema=driver.SCHEMA, tag=driver.TAG, code_sha256={'fixture': 'A' * 64})
        self.stack.enter_context(patch.object(driver, 'info', return_value=copy.deepcopy(self.metadata)))
        serializer = types.ModuleType('tinylm.chat.serialize'); serializer.serialize = serialize
        gate = types.ModuleType('scripts.p106b_gate_runtime')
        gate.wall_limit = lambda _: nullcontext(); gate.idle_before_gpu = Mock()
        tokenizer = types.ModuleType('tokenizers')
        tokenizer.Tokenizer = types.SimpleNamespace(from_file=lambda _: TinyTokenizer())
        self.stack.enter_context(patch.dict(sys.modules, {'tinylm.chat.serialize': serializer,
            'scripts.p106b_gate_runtime': gate, 'tokenizers': tokenizer}))
        self.stack.enter_context(patch.object(driver, 'authority', return_value=10000.))
        self.row, self.location = source_row(0)
        self.case = driver.make_case('train', self.row, self.location, TinyTokenizer())

    def test_case_separates_inference_and_gold(self):
        self.assertEqual(set(self.case['inference']), {'prompt', 'reference_range'})
        self.assertNotIn('gold', self.case['encoding'])
        self.assertIn('gold_audit', self.case)
        self.assertEqual(self.case['encoding']['query'], len(self.case['encoding']['ids']) - 1)

    def test_wrong_original_label_cannot_be_frozen(self):
        bad = dict(self.location, start=0, end=0)
        with self.assertRaises(ValueError):
            driver.make_case('train', self.row, bad, TinyTokenizer())

    def test_no_silent_context_crop(self):
        with patch.object(driver, 'CONTEXT', 20), self.assertRaises((ValueError, driver.Pending)):
            driver.make_case('train', self.row, self.location, TinyTokenizer())

    def test_original_gold_annotation_must_match(self):
        bad = copy.deepcopy(self.row); bad['messages'][-1]['content'] = 'X'
        with self.assertRaises(ValueError):
            driver.make_case('train', bad, self.location, TinyTokenizer())

    def test_duplicate_source_identity_rejected(self):
        rows = {s: [] for s in ('train', 'dev', 'test')}
        for split in rows:
            for lang in ('ko', 'en'):
                count = 64 if split == 'train' else 128
                rows[split].extend(source_row(i, lang, split)[0] for i in range(count))
        selected = driver.selected_rows(rows)
        self.assertEqual(len(selected), 640)
        changed = copy.deepcopy(rows)
        for row in changed['train']:
            row['messages'][-1]['content'] = 'CHANGED_GOLD'
        self.assertEqual([r['meta']['semantic_root_id'] for _, r in selected],
                         [r['meta']['semantic_root_id'] for _, r in driver.selected_rows(changed)])
        rows['train'].append(rows['train'][0])
        with self.assertRaises(ValueError):
            driver.selected_rows(rows)

    def test_replay_is_not_a_readout_case(self):
        with self.assertRaises(ValueError):
            row = copy.deepcopy(self.row); row['meta']['kind'] = 'replay'
            driver.make_case('train', row, self.location, TinyTokenizer())

    def test_prefix_must_be_single_answer_free_user(self):
        self.assertEqual(driver.prefix_messages(self.case['inference']['prompt']), self.row['messages'][:1])
        for text in ('anything', self.case['inference']['prompt'] + 'future',
                     '<|im_start|>user\nx<|im_end|>x<|im_end|>\n<|im_start|>assistant\n'):
            with self.assertRaises(ValueError):
                driver.prefix_messages(text)

    def test_inference_signature_rejects_gold_location_inputs(self):
        params = inspect.signature(driver.infer_prefix).parameters
        self.assertTrue({'prompt', 'reference_range'} <= set(params))
        for bad in ('gold', 'locations', 'user_answer_range', 'case'):
            self.assertNotIn(bad, params)
            with self.assertRaises(TypeError):
                driver.infer_prefix(None, None, None, None, prompt='x', reference_range=[0, 1], **{bad: 'forbidden'})
        tree = ast.parse(inspect.getsource(driver.infer_prefix))
        self.assertFalse(any(isinstance(n, ast.Constant) and n.value in ('gold', 'gold_audit', 'user_answer_range', 'locations') for n in ast.walk(tree)))

    def test_saved_score_reselection_and_vocab_decode(self):
        event = event_for(self.case)
        value = driver.score_event(event, self.case, TinyTokenizer())
        self.assertTrue(value['vocabulary']['literal'])
        self.assertTrue(value['source_boundary_oracle']['literal'])
        self.assertFalse(value['independent']['literal'])

    def test_reversed_argmax_does_not_get_repaired(self):
        n = len(self.case['encoding']['positions']); start = [0.] * n; end = [0.] * n
        start[-1] = 9.; end[0] = 8.
        event = event_for(self.case, start=start, end=end)
        score = driver.score_event(event, self.case, TinyTokenizer())
        self.assertTrue(score['independent']['invalid'])
        self.assertFalse(score['valid_joint']['invalid'])

    def test_nan_and_forged_selected_span_are_rejected(self):
        event = event_for(self.case); event['start_scores'][0] = float('nan')
        with self.assertRaises(ValueError): driver.score_event(event, self.case, TinyTokenizer())
        event = event_for(self.case); event['policies']['independent']['text'] = 'FORGED'
        with self.assertRaises(ValueError): driver.score_event(event, self.case, TinyTokenizer())

    def test_vocab_ids_and_protocol_are_not_just_report_strings(self):
        for key, value in [('answer', 'wrong'), ('generated_ids_sha256', 'B' * 64), ('use_cache', False), ('generated_tokens', True)]:
            v = generation(self.case)
            if key == 'answer': v[key] = value
            else: v['generation'][key] = value
            with self.assertRaises(ValueError): driver.validate_vocabulary(v, self.case, TinyTokenizer())
        v = generation(self.case); v['generation']['terminal_ids'] = []
        with self.assertRaises(ValueError): driver.validate_vocabulary(v, self.case, TinyTokenizer())
        v = generation(self.case, answer=''); v['generation']['generated_tokens'] = True
        with self.assertRaises(ValueError): driver.validate_vocabulary(v, self.case, TinyTokenizer())

    def test_vocab_requested_budget_and_terminal_policy_cannot_be_forged(self):
        for key, value in [('max_new', 2), ('eos_token_available', False),
                           ('stop_at_eos_requested', False), ('stop_at_eos_effective', False),
                           ('stop_token_sequences', [[2]])]:
            wrong = generation(self.case)
            wrong['generation'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                driver.validate_vocabulary(wrong, self.case, TinyTokenizer())

    def test_malformed_manifest_is_rejected_before_verifier_or_file_io(self):
        m = dict(rows=1, shards=[dict(path='../outside_000000.jsonl')])
        with patch.object(driver, 'verify') as verify, self.assertRaises(ValueError):
            driver.read_shards(driver.CACHE, m, 'cases', 1)
        verify.assert_not_called()

    def test_write_once_and_output_allowlist(self):
        path = driver.CACHE / 'one.json'; driver.write(path, {'ok': 1})
        with self.assertRaises(FileExistsError): driver.write(path, {'ok': 2})
        with self.assertRaises(ValueError): driver.write(driver.ROOT / 'other.json', {})
        with self.assertRaises(ValueError): driver.write(driver.CACHE / 'bad.json', {'n': float('nan')})
        self.assertEqual(json.loads(path.read_text()), {'ok': 1})

    def test_linked_output_rejected(self):
        target = driver.ROOT / 'real'; target.mkdir()
        driver.CACHE.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError): driver.write(driver.CACHE / 'bad.json', {})

    def activity(self):
        now = datetime.now(timezone.utc).isoformat()
        return dict(schema=driver.SCHEMA, tag=driver.TAG, mode='prepare', key='prepare', max_wall_sec=60,
            seconds=1., complete=True, returncode=0, error_type=None, started_at=now, ended_at=now,
            code_sha256=self.metadata['code_sha256'], result_sha256='A' * 64)

    def test_activity_requires_complete_finite_owned_metadata(self):
        driver.validate_activity(self.activity(), 'prepare', complete=True)
        for key, value in [('seconds', float('nan')), ('seconds', -1.), ('returncode', True),
                           ('complete', False), ('tag', 'other'), ('mode', 'evaluate'), ('error_type', 'ValueError')]:
            bad = dict(self.activity(), **{key: value})
            with self.assertRaises((ValueError, driver.Pending)):
                driver.validate_activity(bad, 'prepare', complete=True)

    def test_failure_activity_is_saved_and_blocks_downstream(self):
        with patch.object(driver, 'prepare', side_effect=ValueError('fixture failure')):
            with self.assertRaises(ValueError): driver.worker('prepare', 60)
        value = driver.required(driver.EVIDENCE / 'activity_prepare.json')
        self.assertFalse(value['complete']); self.assertEqual(value['returncode'], 9)
        self.assertEqual(value['error_type'], 'ValueError')
        with self.assertRaises(driver.Pending): driver.completed_activity('prepare')
        with self.assertRaises(FileExistsError): driver.worker('prepare', 60)

    def test_zero_return_without_owned_result_is_not_success(self):
        with patch.object(driver, 'prepare', return_value=0), self.assertRaises(ValueError):
            driver.worker('prepare', 60)
        value = driver.required(driver.EVIDENCE / 'activity_prepare.json')
        self.assertFalse(value['complete']); self.assertEqual(value['returncode'], 9)

    def test_wrong_source_sha_fails_before_old_source_consumption(self):
        old = types.SimpleNamespace(read_course=Mock())
        with patch.object(driver, 'historical_modules', return_value=(old, object())), \
                patch.object(driver, 'info', return_value=dict(code_complete=True)), \
                patch.object(driver, 'digest', return_value='0' * 64), self.assertRaises(ValueError):
            driver.source_state()
        old.read_course.assert_not_called()

    def test_phase_wall_and_processgroup_contract(self):
        phases = driver.phase_commands('evaluate', 1200)
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('--worker', phases[-1][1])
        for value in (True, 0, 59, 1801):
            with self.assertRaises(ValueError): driver.phase_commands('evaluate', value)
        with self.assertRaises(ValueError): driver.worker('unknown', 60)

    def test_watchdog_signals_only_its_own_child_group(self):
        process = Mock(pid=42)
        process.wait.side_effect = [subprocess.TimeoutExpired('fixture', 1), 0]
        process.poll.return_value = None
        with patch.object(driver.subprocess, 'Popen', return_value=process) as popen, \
                patch.object(driver.os, 'getpgid', return_value=42), patch.object(driver.os, 'killpg') as kill:
            self.assertEqual(driver.launch(['fixture'], 1), 124)
        self.assertTrue(popen.call_args.kwargs['start_new_session']); kill.assert_called_once_with(42, driver.signal.SIGTERM)
        process.wait.side_effect = [subprocess.TimeoutExpired('fixture', 1)]
        with patch.object(driver.subprocess, 'Popen', return_value=process), \
                patch.object(driver.os, 'getpgid', return_value=7), patch.object(driver.os, 'killpg') as kill:
            self.assertEqual(driver.launch(['fixture'], 1), 124)
        kill.assert_not_called()

    def test_synthetic_prepare_evaluate_readback_pipeline(self):
        import torch
        rows = {s: [] for s in ('train', 'dev', 'test')}; labels = {}
        for split in rows:
            for language in ('ko', 'en'):
                for i in range(65 if split == 'train' else 128):
                    row, label = source_row(i, language, split); rows[split].append(row)
                    labels[driver.sha(row['messages'])] = label
        binding = dict(source='SYNTHETIC_ONLY', checkpoint_sha256=driver.CHECKPOINT_SHA)

        class ToyBody(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.w = torch.nn.Parameter(torch.zeros(1))
            def cuda(self): return self
            def freeze_quant(self): pass
            def clear_quant(self): pass

        class ToyHead(torch.nn.ModuleDict):
            def cuda(self): return self

        body = ToyBody(); head = ToyHead({k: torch.nn.Linear(8, 2, bias=False) for k in ('qs', 'ks', 'qe', 'ke')})
        def infer(model, cfg, tokenizer, auxiliary, *, prompt, reference_range):
            bank = driver.method.build_bank(tokenizer, prompt, reference_range)
            starts = ends = [0.] * len(bank.positions)
            pseudo = dict(inference=dict(prompt=prompt), encoding=dict(ids=list(bank.ids)))
            return dict(bank_sha256=driver.sha(driver.bank_snapshot(bank)), start_scores=starts, end_scores=ends,
                policies={p: asdict(driver.method.select_span(bank, starts, ends, p)) for p in driver.method.POLICIES},
                vocabulary=generation(pseudo))
        def exact_digest(path):
            return driver.CHECKPOINT_SHA if path == driver.CHECKPOINT else original_digest(path)
        original_digest = driver.digest
        with patch.object(driver, 'source_state', return_value=({}, rows, labels, binding)), \
                patch.object(driver, 'load_saved_runtime', return_value=(torch, body, FakeConfig(), TinyTokenizer(), head)), \
                patch.object(driver, 'infer_prefix', side_effect=infer) as inferred, \
                patch.object(driver, 'digest', side_effect=exact_digest), patch.object(torch.cuda, 'empty_cache'):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(driver.worker('prepare', 60), 0)
                self.assertEqual(driver.worker('evaluate', 60), 0)
                self.assertEqual(driver.worker('readback', 60), 0)
            self.assertEqual(inferred.call_count, 640)
            for call in inferred.call_args_list:
                self.assertEqual(set(call.kwargs), {'prompt', 'reference_range'})
            final = driver.required(driver.EVIDENCE / 'readback/report.json')
            self.assertEqual(final['cases'], 640)
            self.assertEqual(driver.completed_activity('readback')['returncode'], 0)
            self.assertEqual(sum(v['cases'] for v in final['summary'] if v['lane'] == 'all'), 2560)
            vocabulary = next(v for v in final['summary'] if v['lane'] == 'all' and v['policy'] == 'vocabulary')
            self.assertEqual(vocabulary['token_f1_sum'], 640.)
            self.assertEqual(vocabulary['token_f1_mean'], 1.)
            span = next(v for v in final['summary'] if v['lane'] == 'all' and v['policy'] == 'independent')
            self.assertEqual(span['literal_vs_vocab_01'], 640)


class PureRuntime(unittest.TestCase):
    def test_authority_aware_and_reserved(self):
        self.assertEqual(driver.authority(driver.END - timedelta(seconds=660)), 60.)
        with self.assertRaises(driver.Pending): driver.authority(driver.END - timedelta(seconds=600))
        with self.assertRaises(ValueError): driver.authority(datetime(2026, 10, 19))

    def test_checkpoint_payload_exact_metadata_and_saved_head(self):
        import torch
        cfg = FakeConfig()
        payload = dict(model={}, cfg=asdict(cfg), step=96, tokenizer_sha256=driver.TOKENIZER_SHA,
            tokenizer_lineage='chat32', auxiliary_method=dict(tag=driver.TRAIN_TAG, arm='span03'),
            training_only_auxiliary={k + '.weight': torch.zeros(64, 768) for k in ('qs', 'ks', 'qe', 'ke')})
        driver.validate_checkpoint_payload(payload, cfg)
        for key, value in [('step', 95), ('tokenizer_sha256', 'A' * 64), ('auxiliary_method', dict(tag='other', arm='span03'))]:
            bad = dict(payload, **{key: value})
            with self.assertRaises(ValueError): driver.validate_checkpoint_payload(bad, cfg)
        for tensor in (torch.zeros(63, 768), torch.zeros(64, 768, dtype=torch.float64), torch.full((64, 768), float('nan'))):
            bad = dict(payload, training_only_auxiliary=dict(payload['training_only_auxiliary'], **{'qs.weight': tensor}))
            with self.assertRaises(ValueError): driver.validate_checkpoint_payload(bad, cfg)
        bad = dict(payload, unexpected=True)
        with self.assertRaises(ValueError): driver.validate_checkpoint_payload(bad, cfg)

    def test_inference_is_eval_prefix_only_no_kv_and_no_annotations(self):
        import torch
        tokenizer = TinyTokenizer(); row, _ = source_row(2)
        prompt = serialize(dict(messages=row['messages'][:1]), add_generation_prompt=True)
        user = driver.text(row['messages'][0]); origin = prompt.index(user)
        lo, hi = row['meta']['user_reference_range']; calls = []
        class ToyModel:
            training = False
            def __call__(self, x, **kwargs):
                calls.append((x.tolist(), kwargs, torch.is_grad_enabled()))
                return torch.zeros(1, x.shape[1], 8)
        head = torch.nn.ModuleDict({k: torch.nn.Linear(8, 2, bias=False) for k in ('qs', 'ks', 'qe', 'ke')}).eval()
        with patch.object(driver, 'emit_vocab', return_value=('fixture', {})):
            out = driver.infer_prefix(ToyModel(), FakeConfig(), tokenizer, head,
                                      prompt=prompt, reference_range=[origin + lo, origin + hi])
        self.assertEqual(calls[0][0], [tokenizer.encode(prompt).ids])
        self.assertEqual(calls[0][1], {'return_hidden': True}); self.assertFalse(calls[0][2])
        self.assertEqual(set(out['policies']), {'independent', 'valid_joint'})

    def test_direct_script_check_only_outside_repository_has_no_model_import(self):
        with tempfile.TemporaryDirectory(prefix='p106b_span_direct_') as tmp:
            result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/diag_p106b_span_readout.py'),
                '--mode', 'evaluate', '--check-only', '--max-wall-sec', '60'], cwd=tmp,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[SPAN_READOUT_CHECK_ONLY]', result.stdout)
            value = json.loads(result.stdout.split('[SPAN_READOUT_CHECK_ONLY] ', 1)[1])
            self.assertEqual(value['model_modules_present'], [])
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
