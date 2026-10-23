"""합성 자료·가짜 런타임만 사용하는 CPU 표현 진단 회귀. 모델 로드는 없다."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import copy
from datetime import datetime, timedelta, timezone
import gc
import io
import json
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_reasoning_surface_cpu as d
from scripts.p106b_verified_trace_data import render_row, truth
from tinylm.chat.serialize import serialize


def rows_fixture():
    tasks = [dict(family='addition', a=a, b=b) for a, b in ((12, 8), (19, 26), (30, 5))]
    tasks += [dict(family='lookup', facts={'A': 3, 'B': 17}, asked='A'),
              dict(family='lookup', facts={'A': 6, 'B': 29}, asked='A'),
              dict(family='update', facts={'A': 8, 'B': 31}, asked='A', update={'subject': 'A', 'value': 19}),
              dict(family='update', facts={'A': 13, 'B': 47}, asked='A', update={'subject': 'B', 'value': 55})]
    return [render_row(t, lang, 'direct', 'test', view) for t in tasks
            for lang in ('ko', 'en') for view in range(4)]


class Tokenizer:
    long = False

    @classmethod
    def from_file(cls, path):
        return cls()

    def encode(self, s):
        return SimpleNamespace(ids=[4] if s == '<|im_end|>' else [65] * 897 if self.long else [ord(c) for c in s])

    def decode(self, ids):
        return '<|im_end|>' if ids == [4] else ''.join(chr(i) for i in ids)


class Model:
    def __init__(self, family):
        self.family = family

    def float(self):
        return self

    def eval(self):
        return self

    def parameters(self):
        return iter([SimpleNamespace(device=SimpleNamespace(type='cpu'), dtype='float32')])

    def buffers(self):
        return iter([])


class SurfaceTest(unittest.TestCase):
    def setUp(self):
        self.rows = rows_fixture()
        self.cases = d.select_cases(self.rows)

    def args(self, execute=True):
        return argparse.Namespace(execute=execute, check_only=not execute, run_id='synthetic',
            deadline=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            max_wall_sec=60, code_sha256='F' * 64)

    def test_fixed_selection_is_root_order_not_answer(self):
        self.assertEqual(len(self.cases), 8)
        self.assertEqual(len({c['source']['meta']['root'] for c in self.cases}), 4)
        for family, count in (('addition', 2), ('lookup', 1), ('update', 1)):
            chosen = {c['source']['meta']['root'] for c in self.cases if c['source']['meta']['family'] == family}
            self.assertEqual(chosen, set(sorted({r['meta']['root'] for r in self.rows if r['meta']['family'] == family})[:count]))
        edited = copy.deepcopy(self.rows)
        for r in edited:
            r['meta']['gold_value'] = 999
            r['grading'] = {'primary_correct': False}
        self.assertEqual([c['index'] for c in self.cases], [c['index'] for c in d.select_cases(edited)])

    def test_casual_preserves_facts_asked_update_and_source(self):
        before = copy.deepcopy(self.rows)
        for r in self.rows:
            if r['meta']['view'] != 0:
                continue
            c = dict(source=r)
            t = c['source']['meta']['task']; lang = c['source']['meta']['language']
            q = d.profile_question(c, 'CASUAL')
            self.assertNotIn('답:', q); self.assertNotIn('Answer:', q)
            if t['family'] == 'addition':
                self.assertIn(str(t['a']), q); self.assertIn(str(t['b']), q)
            else:
                for name, value in t['facts'].items():
                    self.assertIn(name, q); self.assertIn(str(value), q)
                self.assertTrue(q.endswith(f"{t['asked']} 값이 뭐야?" if lang == 'ko' else f"{t['asked']} now?"))
                if t['family'] == 'update':
                    u = t['update']
                    self.assertIn(f"{u['subject']} 값을 {u['value']}로 바꿨어." if lang == 'ko'
                                  else f"I changed {u['subject']} to {u['value']}.", q)
                first = c['source']['meta']['presentation']['first_subject']
                second = next(n for n in t['facts'] if n != first)
                expected = (f"{first}는 {t['facts'][first]}, {second}는 {t['facts'][second]}야." if lang == 'ko'
                            else f"{first} is {t['facts'][first]} and {second} is {t['facts'][second]}.")
                self.assertTrue(q.startswith(expected))
            self.assertEqual(d.profile_question(c, 'CASUAL_FINAL'), q + '\n' + d.FINAL_INSTRUCTION[lang])
            self.assertEqual(d.profile_question(c, 'ORIGINAL'), d.text(c['source']['messages'][0]['content']))
        self.assertEqual(self.rows, before)

    def test_missing_language_and_bad_question_sha_rejected(self):
        with self.assertRaises(ValueError):
            d.select_cases([r for r in self.rows if r['meta']['language'] != 'en'])
        rows = copy.deepcopy(self.rows)
        for r in rows:
            r['meta']['question_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            d.select_cases(rows)

    def test_bare_value_is_not_semantically_wrong_for_missing_marker(self):
        c = self.cases[0]; gold = truth(c['source']['meta']['task'])
        s = d.surface_score(c, str(gold), 'direct')
        self.assertFalse(s['final_contract']); self.assertTrue(s['bare_numeric_exact'])
        self.assertEqual(s['content_value_status'], 'EXACT_VALUE_MATCH')
        self.assertEqual(d.surface_score(c, str(gold + 1), 'direct')['content_value_status'], 'EXPLICIT_VALUE_WRONG')
        self.assertEqual(d.surface_score(c, f'아마 {gold} 같아요', 'direct')['content_value_status'], 'UNJUDGED_READ_RAW')

    def test_trace_and_final_value_remain_separate(self):
        c = self.cases[0]; m = c['source']['meta']
        body = render_row(m['task'], m['language'], 'trace', 'test', 0)['messages'][1]['content']
        body = body.rsplit(': ', 1)[0] + ': 999'
        s = d.surface_score(c, body, 'trace')
        self.assertTrue(s['trace_valid']); self.assertFalse(s['trace_final_agree'])
        self.assertEqual(s['content_value_status'], 'EXPLICIT_VALUE_WRONG')

    def test_explicit_execution_aware_deadline_and_boundaries(self):
        for changes in ({'max_wall_sec': 59}, {'max_wall_sec': 901}, {'deadline': '2099-01-01T00:00:00'},
                        {'deadline': '2000-01-01T00:00:00+00:00'}, {'code_sha256': None},
                        {'run_id': '../escape'}, {'execute': False, 'check_only': False}):
            a = self.args(); vars(a).update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                d.validate_arguments(a)

    def test_check_only_reads_python_sources_not_assets(self):
        real = d.digest; touched = []
        def source_only(path):
            self.assertEqual(path.suffix, '.py'); touched.append(path)
            return real(path)
        a = self.args(False)
        with patch.object(d, 'arguments', return_value=a), patch.object(d, 'digest', side_effect=source_only), \
             patch.object(d, 'load_inputs', side_effect=AssertionError('자료 접근')), \
             patch.object(d, 'cpu_runtime', side_effect=AssertionError('런타임 접근')), \
             patch.object(d, 'new_namespace', side_effect=AssertionError('쓰기')), patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(d.main([]), 0)
        self.assertTrue(touched)

    def test_changed_dependency_pin_rejected(self):
        with patch.object(d, 'digest', return_value='0' * 64), self.assertRaises(ValueError):
            d.source_contract()

    def test_fake_runtime_blocks_cuda_before_importing_model_code(self):
        original = lambda: '금지 전 원형'
        torch = SimpleNamespace(cuda=SimpleNamespace(_lazy_init=original), float32='float32',
            set_num_threads=lambda n: None, set_num_interop_threads=lambda n: None,
            get_num_threads=lambda: 2, get_num_interop_threads=lambda: 2, no_grad=nullcontext)
        modules = {'torch': torch, 'tinylm.infer.generate': SimpleNamespace(load_model=None, sample=None),
            'tokenizers': SimpleNamespace(Tokenizer=Tokenizer),
            'scripts.diag_p101a_mtp_parity': SimpleNamespace(PrecisionForward=None),
            'tinylm.chat.serialize': SimpleNamespace(serialize=serialize)}
        def importing(name):
            if name != 'torch':
                with self.assertRaisesRegex(RuntimeError, 'CUDA'):
                    torch.cuda._lazy_init()
            return modules[name]
        with patch.object(d.importlib, 'import_module', side_effect=importing), patch.dict(d.os.environ):
            with d.cpu_runtime() as rt:
                with self.assertRaisesRegex(RuntimeError, 'CUDA'):
                    rt.torch.cuda._lazy_init()
                self.assertEqual(d.os.environ['OMP_NUM_THREADS'], '2')
        self.assertIs(torch.cuda._lazy_init, original)

    def test_pinned_json_rejects_changed_report(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'closed.json'; p.write_text('{"status":"CLOSED"}', encoding='utf-8')
            expected = hashlib.sha256(p.read_bytes()).hexdigest().upper()
            with patch.object(d, 'ROOT', Path(temp)):
                self.assertEqual(d.pinned_json('closed.json', expected)['status'], 'CLOSED')
                with self.assertRaises(ValueError):
                    d.pinned_json('closed.json', '0' * 64)

    def test_signal_guard_restores_handlers_without_waiting(self):
        before = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM)}
        with d.wall_guard(60):
            with self.assertRaises(d.BudgetExpired):
                signal.getsignal(signal.SIGTERM)()
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL)[0], 0)
        self.assertEqual({s: signal.getsignal(s) for s in before}, before)

    def test_admission_checks_cp_tokenizer_status_and_caller_source(self):
        tasks = [dict(family='addition', a=i, b=99) for i in range(64)]
        tasks += [dict(family='lookup', facts={'A': i, 'B': i+100}, asked='A') for i in range(32)]
        tasks += [dict(family='update', facts={'A': i, 'B': i+100}, asked='A',
                      update={'subject': 'A', 'value': i+200}) for i in range(32)]
        data = {p: [render_row(t, l, p, 'test', v) for t in tasks for l in ('ko', 'en') for v in range(4)]
                for p in d.MODELS}
        def fixtures(fault=None):
            def reading(rel, expected):
                model = 'trace' if 'verified_trace' in rel else 'direct'; pin = d.PINS[model]
                tag = f'p101a_sft_mtp_verified_{model}_v3_s1337'
                if '/corpus/' in rel:
                    return dict(status='CORPUS_READY', tokenizer_sha256=d.TOK_SHA,
                        manifests={'test': dict(kind='test', model=model)})
                if '/first_answer_' in rel:
                    return dict(status='FIRST_ANSWER_COLLECTION_COMPLETE', returncode=0,
                        corpus_sha256=pin['corpus'], trained_report_sha256=pin['report'],
                        checkpoint_sha256=pin['checkpoint'], tokenizer_sha256=d.TOK_SHA,
                        source_sha256={'dep': 'A' * 64}, raw_manifest=dict(kind='gpu', model=model))
                return dict(status='OPEN' if fault == 'status' else 'SFT_MTP_TRAINED_EVAL_PENDING',
                    checkpoint_saved=True, updates=128, corpus_sha256=pin['corpus'], tokenizer_sha256=d.TOK_SHA,
                    checkpoint=f'runs/ckpt/m100s10_ko-en_32M_dense_chat32_{tag}_parent_ntp.pt',
                    code_sha256={'dep': '0' * 64 if fault == 'source' else 'A' * 64},
                    initial_core_sha256='C'*64, parent_sha256='D'*64, seed=1337)
            def stream(folder, manifest):
                vals = data[manifest['model']]
                return iter(vals if manifest['kind'] == 'test' else [dict(index=i, source=r, answer='합성') for i, r in enumerate(vals)])
            def hashing(path):
                if path.name.endswith('.pt'):
                    model = 'trace' if 'verified_trace' in path.name else 'direct'
                    return '0' * 64 if fault == 'cp' else d.PINS[model]['checkpoint']
                return '0' * 64 if fault == 'tokenizer' else d.TOK_SHA
            return reading, stream, hashing
        for fault in (None, 'cp', 'tokenizer', 'status', 'source'):
            reading, stream, hashing = fixtures(fault)
            with self.subTest(fault=fault), patch.object(d, 'pinned_json', side_effect=reading), \
                 patch.object(d, 'digest', side_effect=hashing), \
                 patch('scripts.p101a_sft_mtp_data.stream_rows', side_effect=stream):
                if fault is None:
                    self.assertEqual(len(d.load_inputs(dict(code_files_sha256={'dep': 'A'*64}))['cases']), 8)
                else:
                    with self.assertRaises(ValueError):
                        d.load_inputs(dict(code_files_sha256={'dep': 'A'*64}))

    @contextmanager
    def harness(self, folder, *, expire_after=None, fail_trace=False, device='cpu', long_context=False):
        cp = {m: folder / (m + '.pt') for m in d.MODELS}
        for m in d.MODELS:
            cp[m].write_bytes('합성 CP 파일 표지'.encode())
        sentinel = folder / 'old_first_answer_report.json'; sentinel.write_text('기존 결과', encoding='utf-8')
        immutable = {p: p.read_bytes() for p in [*cp.values(), sentinel]}
        gpu = {m: [{'answer': '원 GPU 합성 답'} for _ in self.rows] for m in d.MODELS}
        inputs = dict(cases=self.cases, checkpoints=cp, gpu=gpu, receipt={'synthetic': True})
        source_before = copy.deepcopy(self.rows)
        calls = []; loaded = []; weak = []
        def load_model(**kw):
            self.assertEqual(kw['device'], 'cpu'); self.assertEqual(kw['mtp_heads'], 'off')
            if weak:
                gc.collect(); self.assertIsNone(weak[-1]())
            m = next(m for m in d.MODELS if cp[m] == kw['ckpt_path'])
            if fail_trace and m == 'trace':
                raise RuntimeError('합성 두 번째 로드 실패')
            model = Model(m); weak.append(weakref.ref(model)); loaded.append(m)
            return model, SimpleNamespace(max_seq_len=1024, mtp_aux=False), device
        def sample(model, cfg, tok, prompt, **kw):
            self.assertEqual(kw['device'], 'cpu'); self.assertTrue(kw['use_cache'])
            self.assertEqual((kw['max_new'], kw['temperature'], kw['top_k'], kw['mtp_tokens']), (128, 0, 1, 1))
            matches = [(c, p) for c in self.cases for p in d.PROFILES if serialize(dict(messages=[dict(
                role='user', content=d.profile_question(c, p))]), 'chatml', add_generation_prompt=True) == prompt]
            self.assertEqual(len(matches), 1)
            c, profile = matches[0]; meta = c['source']['meta']; gold = truth(meta['task'])
            answer = str(gold) if profile == 'CASUAL' else render_row(meta['task'], meta['language'], model.family, 'test', 0)['messages'][1]['content']
            calls.append((model.family, profile, c['index']))
            if expire_after and len(calls) == expire_after:
                raise d.BudgetExpired('합성 기한')
            return tok.decode(tok.encode(prompt).ids) + answer, dict(generated_tokens=8, finish_reason='STOP_SEQUENCE')
        @contextmanager
        def runtime():
            yield SimpleNamespace(Tokenizer=Tokenizer, load_model=load_model, sample=sample,
                torch=SimpleNamespace(float32='float32'), PrecisionForward=lambda model, _: model, serialize=serialize)
        with patch.object(d, 'ROOT', folder), patch.object(d, 'load_inputs', return_value=inputs), \
             patch.object(d, 'cpu_runtime', runtime), patch.object(d, 'wall_guard', lambda _: nullcontext()), \
             patch.object(d, 'digest', side_effect=lambda p: d.PINS[next(m for m in d.MODELS if cp[m] == p)]['checkpoint']), \
             patch.object(Tokenizer, 'long', long_context):
            yield SimpleNamespace(calls=calls, loaded=loaded, inputs=inputs,
                report=folder / 'test_result/evidence/p101a_reasoning_surface_cpu_v1/synthetic/report.json')
        for p, before in immutable.items():
            self.assertEqual(p.read_bytes(), before)
        self.assertEqual(self.rows, source_before)

    def code(self):
        return dict(code_sha256='F' * 64, code_files_sha256={}, dependency_sha256=d.DEPENDENCY_SHA)

    def test_48_requests_six_cells_sequential_models_and_readable_raw(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp)) as h:
            self.assertEqual(d.execute(self.args(), self.code()), 0)
            r = json.loads(h.report.read_text()); self.assertEqual(r['completed_requests'], 48)
            self.assertEqual(h.loaded, ['direct', 'trace']); self.assertEqual(len(set(h.calls)), 48)
            self.assertTrue(all(c['rows'] == 8 and c['status'] == 'CELL_COMPLETE' for c in r['cells']))
            self.assertEqual(r['training_updates'], 0); self.assertEqual(r['checkpoint_writes'], 0)
            review = Path(temp) / r['review']; self.assertIn('CPU 실제 답', review.read_text())
            cell = h.report.parent / 'direct_casual' / 'answers_000000.jsonl'
            row = json.loads(cell.read_text().splitlines()[0])
            self.assertTrue(row['grading']['bare_numeric_exact']); self.assertFalse(row['grading']['final_contract'])

    def test_partial_deadline_preserves_rows_and_never_completes(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp), expire_after=4) as h:
            self.assertEqual(d.execute(self.args(), self.code()), 124)
            r = json.loads(h.report.read_text()); self.assertEqual(r['status'], 'PARTIAL_DEADLINE')
            self.assertEqual(r['completed_requests'], 3); self.assertNotIn('trace', h.loaded)
            self.assertEqual(r['cells'][0]['raw_manifest']['rows'], 3)

    def test_second_model_error_preserves_first_24(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp), fail_trace=True) as h:
            self.assertEqual(d.execute(self.args(), self.code()), 9)
            r = json.loads(h.report.read_text()); self.assertEqual(r['completed_requests'], 24)
            self.assertEqual(r['status'], 'EXECUTION_ERROR')

    def test_context_overflow_is_rejected_without_sample(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp), long_context=True) as h:
            self.assertEqual(d.execute(self.args(), self.code()), 9)
            self.assertEqual(h.calls, [])
            self.assertEqual(json.loads(h.report.read_text())['completed_requests'], 0)

    def test_non_cpu_model_rejected_without_sample(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp), device='cuda') as h:
            self.assertEqual(d.execute(self.args(), self.code()), 9)
            self.assertEqual(h.calls, [])

    def test_existing_namespace_and_review_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp)) as h:
            self.assertEqual(d.execute(self.args(), self.code()), 0)
            before = h.report.read_bytes()
            with self.assertRaises(FileExistsError):
                d.execute(self.args(), self.code())
            self.assertEqual(h.report.read_bytes(), before)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); review = folder / 'review_request/20261022_reasoning_surface_cpu_synthetic.md'
            review.parent.mkdir(); review.write_text('기존 문서', encoding='utf-8')
            with patch.object(d, 'ROOT', folder), self.assertRaises(FileExistsError):
                d.new_namespace(self.args())
            self.assertEqual(review.read_text(), '기존 문서')

    def test_wrong_code_signature_stops_before_assets(self):
        a = self.args(); a.code_sha256 = '0' * 64
        with patch.object(d, 'new_namespace', side_effect=AssertionError('쓰기')), self.assertRaises(ValueError):
            d.execute(a, self.code())

    def test_checkpoint_change_before_load_stops_without_model(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp)) as h:
            with patch.object(d, 'digest', return_value='0' * 64):
                self.assertEqual(d.execute(self.args(), self.code()), 9)
            self.assertEqual(h.loaded, [])
            self.assertEqual(json.loads(h.report.read_text())['completed_requests'], 0)

    def test_review_creation_race_cannot_report_complete(self):
        with tempfile.TemporaryDirectory() as temp, self.harness(Path(temp)) as h:
            original = d.new_namespace
            def occupied(a):
                target, review = original(a)
                review.write_text('동시 소유 문서', encoding='utf-8')
                return target, review
            with patch.object(d, 'new_namespace', side_effect=occupied):
                self.assertEqual(d.execute(self.args(), self.code()), 9)
            r = json.loads(h.report.read_text())
            self.assertEqual(r['status'], 'EXECUTION_ERROR')
            self.assertIn('review_error', r)
            self.assertEqual((Path(temp) / r['review']).read_text(), '동시 소유 문서')


if __name__ == '__main__':
    unittest.main()
