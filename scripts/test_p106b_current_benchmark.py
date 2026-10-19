#!/usr/bin/env python3
"""합성 메모리 원형과 작은 CPU 연산만 사용하는 현재 benchmark 회귀.

실제 tagged prepare·자료·CP tensor·모델·GPU·파일 생성은 하지 않는다.
production sampler의 CUDA 입력 생성만 CPU로 연결하며 실제 forward와
scorer/SDPA/자동캐스트·토큰 선택은 실행한다. CUDA kernel 증명은 아니다.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import warnings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F
from scripts import diag_p106b_current_benchmark as d


def tiny_info():
    return dict(schema=d.SCHEMA, tag=d.TAG, code_sha256={'fixture.py': 'A' * 64}, code_complete=True)


class Tokens:
    """실제 자료와 무관한 가역 문자 fixture. control ID만 사전 선언한다."""
    def encode(self, text):
        out = []; i = 0
        while i < len(text):
            marker = next((m for m in ('<|im_end|>', '<eos>') if text.startswith(m, i)), None)
            if marker: out.append(self.token_to_id(marker)); i += len(marker)
            else: out.append(ord(text[i])); i += 1
        return SimpleNamespace(ids=out)

    def decode(self, ids, skip_special_tokens=True):
        special = {2: '<eos>', 4: '<|im_end|>'}
        return ''.join('' if skip_special_tokens and i in special else special.get(i, chr(i)) for i in ids)

    def token_to_id(self, text): return {'<eos>': 2, '<|im_end|>': 4}.get(text)


def row(task='piqa', index=0):
    if task in d.GENERATIVE:
        prompt = 'Q: fixture ' + str(index) + '\nA:'
        return dict(task=task, kind='gen', index=index, id=task + str(index), prompt=prompt,
            question='fixture ' + str(index), golds=['X'], prompt_tokens=len(Tokens().encode(prompt).ids))
    return dict(task=task, kind='mc', index=index,
        item=dict(ctx='Q ' + str(index), choices=[' a', ' bb'], gold=index % 2, _iid=task + '#' + str(index)))


def all_rows():
    rows = [row(task, i) for task in d.public.TASKS for i in range(256)]
    rows += [row(task, i) for task in d.GENERATIVE for i in range(64)]
    rejected = next(r for r in rows if r['task'] == 'korquad_free' and r['index'] == 63)
    rejected.update(prompt='L' * 897, prompt_tokens=897)
    return rows


def scores(case, pred=None):
    pairs = d.audit._pairs(case['item']); gold = case['item']['gold']
    pred = gold if pred is None else pred
    lengths = [len(Tokens().encode(c).ids) for _, c in pairs]
    sums = [1. if i == pred else 6. + i for i in range(len(pairs))]
    means = [v / n for v, n in zip(sums, lengths)]
    internal = min(range(len(pairs)), key=lambda i: means[i])
    wrong = [v for i, v in enumerate(means) if i != gold]
    return dict(id=case['item']['_iid'], gold=gold, pred_harness=pred,
        pred_harness_norm=min(range(len(pairs)), key=lambda i: sums[i] / max(1, len(pairs[i][1]))),
        pred_internal=internal, pred_internal_norm=internal, sum_nll=sums, mean_nll=means, score=means,
        n_tokens=lengths, n_chars=[max(1, len(c)) for _, c in pairs],
        margin_mean=sum(wrong) / len(wrong) - means[gold], margin_decision=min(wrong) - means[gold])


def cache_fixture(public_rows):
    originals, events = [], []
    limits = dict(piqa=170, hellaswag=89, arc_easy=139)
    for value in public_rows:
        if value['task'] not in d.ENGLISH: continue
        original = deepcopy(value); original['expected_skip'] = None
        original['case_id'] = d.sha([original['task'], original['index'], original])
        pred = value['item']['gold'] if value['index'] < limits[value['task']] else 1 - value['item']['gold']
        event = dict(kind='mc', task=value['task'], index=value['index'], case_id=original['case_id'],
            source_item=value['item'], skipped=False, scores=scores(value, pred))
        originals.append(original); events.append(event)
    return originals, events


class Memory:
    """실제 파일 없이 닫힌 JSON/JSONL 바이트만 보존한다."""
    def __init__(self): self.files = {}
    def raw(self, path):
        if path not in self.files: raise d.Pending('합성 원형 없음')
        return self.files[path]
    def read(self, path): return json.loads(self.raw(path))
    def digest(self, path): return hashlib.sha256(self.raw(path)).hexdigest().upper()
    def exists(self, path): return path in self.files
    def write(self, path, value):
        if path in self.files: raise FileExistsError('합성 원형 덮어쓰기 금지')
        self.files[path] = (json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n').encode()
    def shards(self, directory, stem, rows, lineage=None):
        data = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode()
        part = dict(path=stem + '_000000.jsonl', bytes=len(data), rows=len(rows), sha256=hashlib.sha256(data).hexdigest().upper())
        manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', limit_bytes=19_999_999, rows=len(rows), bytes=len(data),
            concat_sha256=part['sha256'], shards=[part], lineage=lineage or {})
        self.files[directory / part['path']] = data; self.write(directory / (stem + '_shards_manifest.json'), manifest)
        return manifest


@dataclass
class Cfg:
    max_seq_len: int = 1024
    mtp_aux: bool = False


class Toy(torch.nn.Module):
    """작은 실제 embedding/matmul/SDPA. KV와 출력 ID도 합성으로 고정한다."""
    def __init__(self):
        super().__init__()
        self.embedding = torch.nn.Embedding(128, 4)
        self.projection = torch.nn.Linear(4, 128, bias=False)
        self.observed = []; self.calls = 0

    def forward(self, x, past_kv=None, use_cache=False, logits_last_only=False):
        hidden = self.embedding(x); q = hidden.unsqueeze(1)
        hidden = F.scaled_dot_product_attention(q, q, q).squeeze(1)
        logits = self.projection(hidden)
        self.observed.append(dict(dtype=logits.dtype, cpu_autocast=torch.is_autocast_enabled('cpu'),
            flash=torch.backends.cuda.flash_sdp_enabled(), efficient=torch.backends.cuda.mem_efficient_sdp_enabled(),
            math=torch.backends.cuda.math_sdp_enabled(), use_cache=use_cache, tokens=x.shape[1]))
        self.calls += 1
        target = 88 if self.calls == 1 else 4
        logits = logits * 0.; logits[..., target] = 100.
        if logits_last_only: logits = logits[:, -1:]
        if not use_cache: return logits
        size = (past_kv['toy'][0].shape[2] if past_kv else 0) + x.shape[1]
        past = torch.zeros(1, 1, size, 1)
        return logits, {'toy': (past, past)}

    def clear_quant(self): self.cleared = True


class FullMetadataContracts(unittest.TestCase):
    def test_full_production_info_prepare_roundtrip_keeps_nested_models(self):
        memory, cases = Memory(), all_rows()
        production_info, real_digest, real_exists = d.info(), d.digest, d.exists
        code_paths = {d.ROOT / relative for relative in d.CODE}
        binding = dict(models={name: dict(fixture=True) for name in d.MODELS})
        def checksum(path):
            return memory.digest(path) if path in memory.files else real_digest(path)
        with patch.object(d, 'source_state', return_value=(binding, cases, Tokens(), [])), \
                patch.multiple(d, exists=lambda path: real_exists(path) if path in code_paths else memory.exists(path), write=memory.write,
                    required=memory.read, digest=checksum), patch.object(d, 'completed_activity'), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(d.prepare(), 0)
            frozen, observed, *_ = d.prepared()
        self.assertEqual(observed, cases)
        for key, value in production_info.items():
            self.assertEqual(frozen[key], value, key)
        self.assertEqual(frozen['models'], list(d.MODELS))
        self.assertEqual(frozen['binding']['models'], binding['models'])
        self.assertEqual(frozen['models_loaded'], 0)
        self.assertEqual(frozen['checkpoint_tensor_loads'], 0)
        self.assertEqual(set(memory.files), {
            d.CACHE / 'frozen_reference.json', d.result_path('prepare')})


class Contracts(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(d, 'info', tiny_info))

    def memory(self, memory):
        for name, value in (('required', memory.read), ('raw_bytes', memory.raw), ('digest', memory.digest),
                            ('exists', memory.exists), ('write', memory.write)):
            self.stack.enter_context(patch.object(d, name, value))

    def test_model_cohorts_and_9216_9212_denominators(self):
        rows = all_rows(); requested = sum(len(d.cohort(rows, model)) for model in d.MODELS)
        scored = sum(sum(d.eligibility(r, Tokens()) is None for r in d.cohort(rows, model)) for model in d.MODELS)
        self.assertEqual((requested, scored), (9216, 9212))
        self.assertEqual([len(d.cohort(rows, m)) for m in d.MODELS], [768, 768, 1920, 1920, 1920, 1920])
        self.assertNotIn('actualhistory', d.TASKS)

    def test_phase_selection_rejects_ambiguous_models(self):
        for mode, model in (('evaluate', None), ('prepare', 'sft_float'), ('wrong', None), ('evaluate', 'float')):
            with self.subTest(mode=mode, model=model), self.assertRaises(ValueError): d.phase_key(mode, model)

    def test_mc_boundaries_are_encoded_separately_not_joined(self):
        class Boundary(Tokens):
            def encode(self, text): return SimpleNamespace(ids=[1] if text == 'Q a' else list(range(len(text))))
        value = row(); value['item'].update(ctx='Q', choices=[' a', ' b'])
        receipt = d.mc_encoding(value, Boundary())
        self.assertEqual(receipt['prefix_tokens'], [1, 1]); self.assertEqual(receipt['continuation_tokens'], [2, 2])
        self.assertNotEqual(receipt['separate_boundaries_sha256'], d.sha([[Boundary().encode('Q a').ids]]))

    def test_mc_sum_argmin_char_metric_and_ties(self):
        value = row(); event = dict(d.event_base(value, {}), skipped=False, scores=scores(value), encoding=d.mc_encoding(value, Tokens()))
        d.validate_event(event, value, Tokens(), {}, None)
        event['scores']['pred_harness'] = 1
        with self.assertRaises(ValueError): d.validate_event(event, value, Tokens(), {}, None)
        event['scores'] = scores(value)
        event['scores'].update(sum_nll=[2., 2.], mean_nll=[1., 2 / 3], score=[1., 2 / 3],
            pred_harness=0, pred_harness_norm=1, pred_internal=1, pred_internal_norm=1,
            margin_mean=-1 / 3, margin_decision=-1 / 3)
        d.validate_event(event, value, Tokens(), {}, None)

    def test_mc_nonfinite_or_corrupt_token_count_is_rejected(self):
        value = row(); base = dict(d.event_base(value, {}), skipped=False, scores=scores(value), encoding=d.mc_encoding(value, Tokens()))
        for name, replacement in (('sum_nll', [float('nan'), 6.]), ('n_tokens', [999, 3]), ('score', [3., 1.])):
            bad = deepcopy(base); bad['scores'][name] = replacement
            with self.subTest(name=name), self.assertRaises(ValueError): d.validate_event(bad, value, Tokens(), {}, None)

    def test_exact_cached_768_ids_scores_and_original_items(self):
        rows = all_rows(); original, events = cache_fixture(rows)
        outcomes = d.validate_cached_mc(original, events, rows, Tokens())
        self.assertEqual(sum(r['correct'] for r in outcomes), 398)
        self.assertEqual(len(outcomes), 768)

    def test_cached_duplicates_changed_ids_items_or_sums_are_rejected(self):
        rows = all_rows(); original, events = cache_fixture(rows)
        mutations = [lambda a, b: b.__setitem__(0, deepcopy(b[1])),
            lambda a, b: a[0]['item'].__setitem__('ctx', 'changed'),
            lambda a, b: b[0]['scores'].__setitem__('pred_harness', 1 - b[0]['scores']['pred_harness'])]
        for mutate in mutations:
            a, b = deepcopy(original), deepcopy(events); mutate(a, b)
            with self.assertRaises(ValueError): d.validate_cached_mc(a, b, rows, Tokens())

    def test_shards_closed_hash_count_and_order(self):
        memory = Memory(); directory = d.RAW / 'fixture'; rows = [dict(i=i) for i in range(3)]
        manifest = memory.shards(directory, 'answers', rows); self.memory(memory)
        self.assertEqual(d.read_shards(directory, manifest, 'answers', 3), rows)
        for key, value in (('rows', 2), ('bytes', 1), ('concat_sha256', 'F' * 64), ('limit_bytes', 20_000_001)):
            bad = deepcopy(manifest); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): d.read_shards(directory, bad, 'answers', 3)
        memory.files[directory / 'answers_000000.jsonl'] += b'\n'
        with self.assertRaises(ValueError): d.read_shards(directory, manifest, 'answers', 3)

    def test_shards_path_injection_is_rejected_before_read(self):
        manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=1, limit_bytes=19_999_999, shards=[dict(path='../answers_000000.jsonl')])
        with self.assertRaises(ValueError): d.read_shards(d.RAW, manifest, 'answers', 1)

    def test_public_pins_counts_and_exact_one_length_exclusion(self):
        rows = all_rows()
        report = dict(status='FROZEN_CPU_STRICT_LOAD_PASSED', driver_sha256='F' * 64,
            tokenizer_sha256=d.public.TOKENIZER_SHA, context=1024, max_new=128, manifest={})
        def pin(path): return d.FIXED.get(path, 'F' * 64)
        with patch.object(d, 'digest', pin), patch.object(d, 'required', return_value=report),\
                patch.object(d, 'read_shards', return_value=rows):
            _, values, excluded = d.read_public(Tokens())
            self.assertEqual(len(values), 1920); self.assertEqual(sum(v is not None for v in excluded.values()), 1)
            report['max_new'] = 64
            with self.assertRaises(ValueError): d.read_public(Tokens())

    def test_write_scope_nan_size_and_write_once_are_not_bypassed(self):
        with self.assertRaises(ValueError): d.write(d.ROOT / 'test_result/not_current/report.json', {})
        with self.assertRaises(ValueError): d.write(d.EVIDENCE / 'fixture.json', {'bad': float('nan')})
        with patch.object(Path, 'mkdir') as mkdir, patch.object(Path, 'open', side_effect=FileExistsError('합성 이전 산출물')) as opened:
            with self.assertRaises(FileExistsError): d.write(d.EVIDENCE / 'fixture.json', {})
        self.assertEqual(opened.call_args.args, ('xb',)); mkdir.assert_called_once()

    def test_protected_and_outside_paths_are_rejected(self):
        for value in (d.ROOT / 'datasets/TinyDataset/secret', Path('/tmp/outside'), d.ROOT / '.claude/x', d.ROOT / '..' / 'x'):
            with self.subTest(path=value), self.assertRaises(ValueError): d.safe(value)

    def test_cpu_bf16_outer_real_scorer_math_and_fp32(self):
        model = Toy(); was_cuda = torch.cuda.is_initialized()
        with warnings.catch_warnings(), torch.autocast('cpu', dtype=torch.bfloat16):
            warnings.simplefilter('ignore', UserWarning)
            output = d.suite.run_mc('piqa', [row()['item']], d.FP32Forward(model), Tokens(), 'cpu', 1024, torch, F, True)
        self.assertEqual(len(output['rows']), 1); self.assertFalse(output['skip_rows'])
        self.assertTrue(all(v['dtype'] == torch.float32 and not v['cpu_autocast'] and v['math']
                            and not v['flash'] and not v['efficient'] for v in model.observed))
        self.assertEqual(torch.cuda.is_initialized(), was_cuda)

    def production_generation(self):
        model = Toy(); original_tensor = torch.tensor; case = row('gsm8k_free')
        def cpu_tensor(*args, **kwargs):
            if kwargs.get('device') == 'cuda': kwargs['device'] = 'cpu'
            return original_tensor(*args, **kwargs)
        with patch.object(torch, 'tensor', cpu_tensor), warnings.catch_warnings(), torch.autocast('cpu', dtype=torch.bfloat16):
            warnings.simplefilter('ignore', UserWarning)
            answer, receipt = d.emit_public(model, Cfg(), Tokens(), case['prompt'])
        return model, case, answer, receipt

    def test_real_production_sampler_ids_eot_cache_and_fp32(self):
        was_cuda = torch.cuda.is_initialized(); model, case, answer, receipt = self.production_generation()
        self.assertEqual(answer, 'X'); self.assertEqual(receipt['generated_ids'], [88, 4])
        self.assertEqual(receipt['terminal_ids'], [4]); self.assertEqual(receipt['body'], 'X')
        self.assertEqual(receipt['raw_new_text'], 'X<|im_end|>')
        self.assertEqual([v['tokens'] for v in model.observed], [case['prompt_tokens'], 1])
        self.assertTrue(all(v['use_cache'] and v['dtype'] == torch.float32 and not v['cpu_autocast'] and v['math'] for v in model.observed))
        d.validate_generation(answer, receipt, case, Tokens())
        self.assertEqual(torch.cuda.is_initialized(), was_cuda)

    def test_generation_corrupt_requested_effective_body_stop_or_ids_rejected(self):
        _, case, answer, receipt = self.production_generation()
        for name, value in (('effective_max_new', 64), ('prompt_ids', [99]), ('terminal_ids', []),
                            ('body', 'tampered'), ('generated_ids', [88, 2]), ('finish_reason', 'MAX_NEW')):
            bad = deepcopy(receipt); bad[name] = value
            with self.subTest(name=name), self.assertRaises(ValueError): d.validate_generation(answer, bad, case, Tokens())

    def test_historical_nfkc_answer_and_gsm_parser_not_suffix_guess(self):
        self.assertEqual(d.public.answer_scores(' Ａ  b ', ['a b'])['whitespace_nfkc_exact'], 1)
        self.assertEqual(d.public.numerical('steps\n#### -1,200.00'), '-1.2E+3')
        self.assertIsNone(d.public.numerical('answer is 12')); self.assertIsNone(d.public.numerical('1/2'))
        case = row('gsm8k_free'); case['golds'] = ['12']
        self.assertEqual(d.score_free(case, 'answer is 12')['numeric_exact'], 0)
        self.assertEqual(d.score_free(case, 'work #### 12')['numeric_exact'], 1)

    def test_predeclared_length_exclusion_cannot_become_model_exception(self):
        value = row('korquad_free'); value.update(prompt='L' * 897, prompt_tokens=897)
        reason = d.eligibility(value, Tokens()); self.assertEqual(reason, 'full_prompt_plus128_exceeds1024')
        event = dict(d.event_base(value, {}), skipped=True, reason=reason)
        d.validate_event(event, value, Tokens(), {}, reason)
        event['reason'] = 'model exception'
        with self.assertRaises(ValueError): d.validate_event(event, value, Tokens(), {}, reason)

    def test_fixed_display_ignores_correctness_and_model_output(self):
        rows = all_rows(); first = d.display_ids(rows)
        self.assertEqual(first, d.display_ids(deepcopy(rows)))
        self.assertEqual(len(first), 18)
        self.assertEqual(len(set(first)), 18)

    def test_broad_payload_strict_cfg_dtype_alias_and_no_float_guard_relaxation(self):
        class Alias(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.a = torch.nn.Linear(2, 2, bias=False); self.alias = self.a
        model = Alias(); saved = dict(model=deepcopy(model.state_dict()), cfg=asdict(Cfg()), step=352,
            tokenizer_sha256=d.public.TOKENIZER_SHA,
            broad_curriculum=dict(tag=d.recovery.TAG, arm='mixed', passes=2, objective='token'))
        d.validate_broad_payload(saved, model, Cfg(), 'mixed', torch)
        mutations = [lambda p: p.__setitem__('step', 351), lambda p: p.__setitem__('quantization_route', {'mode': 'float'}),
            lambda p: p['model'].__setitem__('a.weight', p['model']['a.weight'].to(torch.bfloat16)),
            lambda p: p['model'].__setitem__('alias.weight', p['model']['alias.weight'] + 1)]
        for mutate in mutations:
            bad = deepcopy(saved); mutate(bad)
            with self.assertRaises(ValueError): d.validate_broad_payload(bad, model, Cfg(), 'mixed', torch)

    def test_native_runtime_uses_official_route_without_disabling_grad(self):
        class Small(torch.nn.Linear):
            def set_anneal(self, value): self.anneal = value
            def freeze_quant(self): self.frozen = True
        model = Small(2, 2); active = SimpleNamespace(assert_active=Mock()); cfg = Cfg()
        calls = []
        @contextmanager
        def runtime(arm, endpoint):
            calls.append((arm, endpoint)); yield torch, model, cfg, Tokens(), 'scratch', active
        reference = dict(model_id='sft_float', family='native_weight_route', arm='float', endpoint='sft', core_sha256='B' * 64)
        with patch.object(d.n, 'routed_runtime', runtime), patch('scripts.diag_p101a_sft_mtp.state_fingerprint', return_value='B' * 64):
            with d.model_runtime('sft_float', reference) as (_, actual, _, _, route):
                self.assertIs(actual, model); self.assertIs(route, active); self.assertFalse(model.training)
                self.assertTrue(all(p.requires_grad for p in model.parameters()))
        self.assertEqual(calls, [('float', 'sft')]); active.assert_active.assert_called_once()

    def test_generic_or_mismatched_runtime_is_rejected_before_load(self):
        for reference in (dict(model_id='sft_float', family='generic'), dict(model_id='native_float', family='native_weight_route')):
            with self.assertRaises(ValueError), d.model_runtime('sft_float', reference): pass

    def test_native_model_reference_requires_closed_training_and_checkpoint_hash(self):
        report = dict(quantization_route={'mode': 'float'}, checkpoint_sha256='B' * 64, final_core_sha256='C' * 64)
        with patch.object(d.n, 'train_report', return_value=report) as read, patch.object(d, 'digest', return_value='B' * 64):
            result = d.model_reference('sft_float')
        read.assert_called_once_with('sft', 'float'); self.assertEqual(result['family'], 'native_weight_route')
        with patch.object(d.n, 'train_report', return_value=report), patch.object(d, 'digest', return_value='F' * 64):
            with self.assertRaises(ValueError): d.model_reference('sft_float')

    def test_broad_metadata_uses_original_closed_activity_and_reader_without_wire(self):
        memory = Memory(); self.memory(memory)
        course = dict(updates=352, groups_per_pass=176, schedules={'mixed': [list(range(176))] * 2})
        cache = d.ROOT / 'data_cache/fixture_broad'
        checkpoint = d.ROOT / 'runs/ckpt/fixture_broad.pt'; parent = d.ROOT / 'runs/ckpt/fixture_parent.pt'
        memory.files[checkpoint] = b'fixture marker, not tensor'
        memory.files[parent] = b'fixture parent marker, not tensor'
        memory.write(cache / 'course.json', course)
        memory.write(cache / 'frozen.json', dict(tag=d.recovery.TAG, course_report_sha256=memory.digest(cache / 'course.json')))
        report = dict(checkpoint_sha256=memory.digest(checkpoint), final_core_sha256='B' * 64)
        report_path = d.ROOT / 'test_result/evidence/fixture_broad/train_mixed/report.json'
        memory.write(report_path, report)
        base = SimpleNamespace(PARENT=parent, PARENT_SHA=memory.digest(parent), PARENT_CORE='C' * 64)
        broad = SimpleNamespace(CACHE=cache, EVIDENCE=report_path.parents[1], UPDATES=352,
            required=memory.read, digest=memory.digest, info=lambda: dict(tag=d.recovery.TAG),
            checkpoint=lambda arm: checkpoint, monitor=SimpleNamespace(base=base),
            completed_activity=Mock(), read_training=Mock(return_value=report))
        with patch.object(d.recovery, 'legacy', broad), patch.object(d.recovery, 'runtime_scope', nullcontext),\
                patch.object(d.recovery, 'validate_equivalence') as equivalent:
            result = d.model_reference('broad_mixed')
        equivalent.assert_called_once(); broad.completed_activity.assert_called_once_with('train', 'mixed')
        self.assertEqual(result['parent_checkpoint_sha256'], base.PARENT_SHA)
        args, kwargs = broad.read_training.call_args; self.assertEqual(args, ('mixed',)); self.assertIs(kwargs['cost'], False)
        self.assertEqual(kwargs['bundle']['course'].report, course)

    def test_tiny_evaluate_to_raw_readback_keeps_state_and_no_pmi(self):
        memory = Memory(); self.memory(memory)
        values = [row('piqa'), row('kobest_copa'), row('gsm8k_free'), row('korquad_free'), row('korquad_free', 1)]
        values[-1].update(prompt='L' * 897, prompt_tokens=897)
        model = Toy(); model.eval(); cfg = Cfg(); tok = Tokens(); original_tensor = torch.tensor
        def core(actual):
            h = hashlib.sha256()
            for key, tensor in sorted(actual.state_dict().items()): h.update(key.encode()); h.update(tensor.detach().numpy().tobytes())
            return h.hexdigest().upper()
        checkpoint = d.ROOT / 'runs/ckpt/fixture.pt'; memory.files[checkpoint] = b'fixture marker, not tensor'
        spec = dict(model_id='broad_mixed', family='broad_v2', route='PRODUCT_TERNARY', arm='mixed',
            checkpoint=str(checkpoint.relative_to(d.ROOT)), checkpoint_sha256=memory.digest(checkpoint), core_sha256=core(model))
        reference = dict(display_ids=d.display_ids(values), binding=dict(models={'broad_mixed': spec},
            exclusions={d.row_id(r): d.eligibility(r, tok) for r in values}))
        memory.write(d.CACHE / 'frozen_reference.json', reference)
        @contextmanager
        def runtime(*args):
            cuda = SimpleNamespace(reset_peak_memory_stats=lambda: None, max_memory_reserved=lambda: 0)
            yield SimpleNamespace(cuda=cuda, no_grad=torch.no_grad), model, cfg, tok, None
        class Writer:
            def __init__(self, directory, stem, limit): self.directory, self.stem, self.rows = directory, stem, []
            def append(self, event): self.rows.append(deepcopy(event))
            def close(self, lineage): return memory.shards(self.directory, self.stem, self.rows, lineage)
        old_run = d.suite.run_mc; no_pmi = []
        def scorer(task, items, wrapped, tokenizer, device, seq, torch_api, f_api, no_pmi_flag):
            no_pmi.append(no_pmi_flag)
            return old_run(task, items, wrapped, tokenizer, 'cpu', seq, torch, f_api, no_pmi_flag)
        def cpu_tensor(*args, **kwargs):
            if kwargs.get('device') == 'cuda': kwargs['device'] = 'cpu'
            return original_tensor(*args, **kwargs)
        with patch.object(d, 'prepared', return_value=(reference, values, tok, [])), patch.object(d, 'model_runtime', runtime),\
                patch.object(d, 'ShardWriter', Writer), patch.object(d, 'authority', return_value=3600),\
                patch.object(d, 'completed_activity'), patch('scripts.p106b_gate_runtime.idle_before_gpu'),\
                patch('scripts.diag_p101a_sft_mtp.state_fingerprint', core), patch.object(d.suite, 'run_mc', scorer),\
                patch.object(torch, 'tensor', cpu_tensor), redirect_stdout(io.StringIO()), warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.assertEqual(d.evaluate('broad_mixed'), 0)
            report, events = d.read_model('broad_mixed', reference, values, tok)
            self.assertEqual((report['requested'], report['scored'], report['length_excluded']), (5, 4, 1))
            self.assertEqual(report['core_before'], core(model)); self.assertEqual(report['core_before'], report['core_after'])
            self.assertTrue(all(p.requires_grad for p in model.parameters())); self.assertEqual(no_pmi, [True, True])
            self.assertEqual(len(events), 5)
            memory.read(d.result_path('evaluate_broad_mixed'))
            bad = memory.read(d.result_path('evaluate_broad_mixed')); bad['scored'] = 5
            memory.files[d.result_path('evaluate_broad_mixed')] = json.dumps(bad).encode()
            with self.assertRaises(ValueError): d.read_model('broad_mixed', reference, values, tok)

    def test_source_requires_all_six_not_missing_as_zero(self):
        with patch.object(d, 'tokenizer', return_value=Tokens()), patch.object(d, 'read_public', return_value=({}, [], {})),\
                patch.object(d, 'cached_falcon', return_value=({}, [])), patch.object(d, 'model_reference', side_effect=d.Pending('미완료')):
            with self.assertRaises(d.Pending): d.source_state()

    def activity(self):
        return dict(schema=d.SCHEMA, tag=d.TAG, key='evaluate_sft_float', mode='evaluate', model_id='sft_float',
            code_sha256=tiny_info()['code_sha256'], seconds=3., max_wall_sec=60, returncode=0, complete=True,
            worker_pid=123, worker_pgid=123, error_type=None,
            started_at=(d.END - timedelta(hours=2)).isoformat(), ended_at=(d.END - timedelta(hours=2) + timedelta(seconds=3)).isoformat())

    def test_activity_requires_code_pgid_time_and_terminal_success(self):
        value = self.activity(); d.validate_activity(value, value['key'], True)
        for key, replacement in (('worker_pgid', 124), ('complete', False), ('seconds', float('nan')),
                                 ('ended_at', d.END.replace(tzinfo=None).isoformat()), ('error_type', 'RuntimeError')):
            bad = deepcopy(value); bad[key] = replacement
            with self.subTest(key=key), self.assertRaises((ValueError, d.Pending)): d.validate_activity(bad, value['key'], True)

    def test_deadline_and_stage_total_limit_are_distinct(self):
        self.assertEqual(d.authority(d.END - timedelta(seconds=601)), 1)
        with self.assertRaises(d.Pending): d.authority(d.END - timedelta(seconds=600))
        with patch.object(d, 'authority', return_value=2000), patch.object(d, 'spent_seconds', return_value=3599):
            self.assertEqual(d.remaining_activity(), 1)
        with patch.object(d, 'authority', return_value=2000), patch.object(d, 'spent_seconds', return_value=3600):
            with self.assertRaises(d.Pending): d.remaining_activity()

    def test_total_activity_includes_regression_preflight_and_failed_worker(self):
        memory = Memory(); self.memory(memory)
        failed = self.activity(); failed.update(returncode=9, complete=False, error_type='ValueError')
        worker_path = d.EVIDENCE / 'activity_evaluate_sft_float.json'; memory.write(worker_path, failed)
        aux_path = d.EVIDENCE / 'aux_fixture.json'
        memory.write(aux_path, dict(tag=d.TAG, code_sha256=tiny_info()['code_sha256'], command_sha256='C' * 64, seconds=2., returncode=8))
        directory = SimpleNamespace(glob=lambda pattern: [worker_path] if pattern == 'activity_*.json' else [aux_path])
        with patch.object(d, 'exists', return_value=True), patch.object(d, 'safe', return_value=directory):
            self.assertEqual(d.spent_seconds(), 5.)
        # 완전한 launcher 경과시간5초에는 같은 worker3초가 이미 포함된다.
        receipt = memory.read(aux_path); receipt.update(seconds=5., new_worker_key=failed['key'], new_worker_sha256=memory.digest(worker_path))
        memory.files[aux_path] = json.dumps(receipt).encode()
        with patch.object(d, 'exists', return_value=True), patch.object(d, 'safe', return_value=directory):
            self.assertEqual(d.spent_seconds(), 5.)

    def test_auxiliary_launcher_bounds_owned_child_and_records_repeated_commands(self):
        memory = Memory(); self.memory(memory)
        with patch.object(d, 'remaining_activity', return_value=70), patch.object(d.n, 'launch', return_value=8) as launch:
            self.assertEqual(d.launch_phase(['fixture regression'], 60), 8)
            self.assertEqual(d.launch_phase(['fixture regression'], 60), 8)
        self.assertEqual(launch.call_args.args[1], 70)
        receipts = [memory.read(p) for p in memory.files]
        self.assertEqual(len(receipts), 2); self.assertTrue(all(r['returncode'] == 8 for r in receipts))

    def test_pipeline_has_exact_regression_preflight_execute(self):
        phases = d.phase_commands('evaluate', 'native_float', 600)
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('native_float', phases[2][1]); self.assertNotIn('--model-id', phases[1][1])
        for limit in (True, 59, 3601):
            with self.assertRaises(ValueError): d.phase_commands('prepare', None, limit)
        lines = []; calls = iter((0, 8))
        receipt = d.pipeline(phases, lambda _: next(calls), lines.append, experiment='합성')
        self.assertEqual(receipt['returncode'], 8); self.assertFalse(receipt['main_experiment_invoked'])

    def test_worker_error_keeps_failure_activity_and_does_not_mark_complete(self):
        memory = Memory(); self.memory(memory)
        with patch.object(d, 'remaining_activity', return_value=3600), patch.object(d.os, 'getpid', return_value=123),\
                patch.object(d.os, 'getpgid', return_value=123), patch.object(d.n, 'termination_guard', nullcontext),\
                patch('scripts.p106b_gate_runtime.wall_limit', lambda _: nullcontext()), patch.object(d, 'prepare', side_effect=ValueError('합성 오류')):
            with self.assertRaises(ValueError): d.worker('prepare', None, 60)
        receipt = memory.read(d.EVIDENCE / 'activity_prepare.json')
        self.assertEqual(receipt['returncode'], 9); self.assertFalse(receipt['complete']); self.assertEqual(receipt['error_type'], 'ValueError')

    def test_worker_wrong_process_group_fails_before_work(self):
        with patch.object(d, 'remaining_activity', return_value=3600), patch.object(d.os, 'getpid', return_value=123),\
                patch.object(d.os, 'getpgid', return_value=124), patch.object(d, 'prepare') as prepare:
            with self.assertRaises(ValueError): d.worker('prepare', None, 60)
        prepare.assert_not_called()

    def test_main_error_prints_traceback_and_nonzero_final(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(d, 'worker', side_effect=ValueError('합성 오류')), redirect_stdout(output), redirect_stderr(errors):
            code = d.main(['--mode', 'prepare', '--worker', '--execute', '--max-wall-sec', '60'])
        self.assertEqual(code, 9); self.assertIn('Traceback', errors.getvalue()); self.assertIn('CURRENT_BENCHMARK_FINAL', output.getvalue())

    def test_check_only_does_not_prepare_load_or_write(self):
        with patch.object(d, 'worker', side_effect=AssertionError('실행 금지')), patch.object(d, 'write', side_effect=AssertionError('쓰기 금지')), redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'prepare', '--check-only']), 0)


if __name__ == '__main__': unittest.main()
