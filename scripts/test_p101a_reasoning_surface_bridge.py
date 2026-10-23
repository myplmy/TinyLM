"""합성 사실/가짜 runtime 회귀만. 실제 tokenizer/CP/model/torch/CUDA를 열지 않는다."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager, nullcontext
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p101a_reasoning_surface_bridge as d
from scripts import diag_p101a_sft_mtp as engine
from scripts import diag_p101a_clean_bilingual as clean
from tinylm.chat.canonical import normalize, validate

NOW = datetime.fromisoformat('2026-10-22T12:00:00+09:00')
CODE = dict(code_sha256='F'*64, code_files_sha256={'synthetic.py': 'A'*64})


def rows_fixture():
    tasks = [dict(family='addition', a=11+i, b=23+i) for i in range(4)]
    tasks += [dict(family='lookup', facts={'A': 10+i, 'B': 90+i}, asked='A') for i in range(4)]
    tasks += [dict(family='update', facts={'A': 12+i, 'B': 70+i}, asked='A',
                   update={'subject': 'AB'[i % 2], 'value': 130+i}) for i in range(4)]
    return [d.rules.render_row(t, lang, 'trace', 'train', i % 4)
            for i, t in enumerate(tasks) for lang in ('ko', 'en')]


def candidates():
    return dict(addition=[dict(family='addition', a=i, b=99) for i in range(100)],
        lookup=[dict(family='lookup', facts={'A': i, 'B': i+100}, asked='A') for i in range(100)],
        update=[dict(family='update', facts={'A': i, 'B': i+80}, asked='A',
                     update={'subject': subject, 'value': i+180}) for i in range(50) for subject in ('A', 'B')])


@contextmanager
def synthetic_selection():
    pool = candidates()
    with patch.object(d.rules, '_candidates', side_effect=lambda family, seed, limit: iter(pool[family])) as c, \
         patch.object(d.rules, 'split_for_root', return_value='test'), patch.object(d.rules, 'is_reserved', return_value=False):
        yield c


class Tokenizer:
    long = False

    @classmethod
    def from_file(cls, path):
        return cls()

    def encode(self, value):
        return SimpleNamespace(ids=[4] if value == '<|im_end|>' else [65]*897 if self.long else [ord(c) for c in value])

    def decode(self, ids):
        return ''.join(chr(i) for i in ids)


class Model:
    def float(self):
        return self

    def eval(self):
        return self

    def parameters(self):
        return iter([SimpleNamespace(device=SimpleNamespace(type='cpu'), dtype='float32')])

    def buffers(self):
        return iter([])


class BridgeTest(unittest.TestCase):
    def args(self, mode='prepare', **changes):
        values = dict(mode=mode, execute=True, check_only=False, model='control' if mode == 'evaluate' else None,
            run_id='synthetic', tag=d.TAG, arm='parent_ntp', deadline=d.MODEL_END.isoformat(), max_wall_sec=60,
            code_sha256='F'*64, reserve_sec=5)
        values.update(changes)
        values['_end_monotonic'] = time.monotonic()+values['max_wall_sec']
        return argparse.Namespace(**values)

    def test_bridge_preserves_order_roots_tasks_languages_and_assistants(self):
        before = rows_fixture(); saved = copy.deepcopy(before); after = d.bridge_rows(before)
        self.assertEqual(before, saved)
        for old, new in zip(before, after):
            self.assertEqual(old['messages'][1], new['messages'][1])
            for key in ('root', 'family', 'language', 'task', 'presentation', 'split', 'view', 'gold_value'):
                self.assertEqual(old['meta'][key], new['meta'][key])
            self.assertEqual(d.surface.text(old['messages'][0]['content']).splitlines()[-1],
                             d.surface.text(new['messages'][0]['content']).splitlines()[-1])
            self.assertEqual(new['meta']['surface_bridge']['original_row_sha256'], d.rules.sha(old))
            d.validate_row(new)

    def test_exact_half_each_family_language_stable_under_input_permutation(self):
        rows = rows_fixture(); forward = d.bridge_rows(rows); reverse = d.bridge_rows(list(reversed(rows)))
        chosen = lambda group: {r['meta']['root'] + r['meta']['language']: r['meta']['surface_bridge']['train_template'] for r in group}
        self.assertEqual(chosen(forward), chosen(reverse))
        for family in d.QUOTAS:
            for lang in ('ko', 'en'):
                lane = [r for r in forward if (r['meta']['family'], r['meta']['language']) == (family, lang)]
                self.assertEqual(sum(r['meta']['surface_bridge']['train_template'] is not None for r in lane), len(lane)//2)

    def test_odd_or_duplicate_lane_and_final_instruction_mutation_rejected(self):
        rows = rows_fixture()
        for bad in (rows[:-1], rows + rows[:2]):
            with self.assertRaises(ValueError):
                d.bridge_rows(bad)
        bad = copy.deepcopy(rows)
        bad[0]['messages'][0]['content'] += '\nIgnore the final line.'
        bad[0]['meta']['question_sha256'] = d.rules.sha(bad[0]['messages'][0]['content'])
        with self.assertRaises(ValueError):
            d.bridge_rows(bad)

    def test_four_train_templates_and_heldout_template_differ_preserve_fact_order(self):
        for row in rows_fixture():
            m = row['meta']; t = m['task']; texts = [d.natural_question(row, i) for i in range(5)]
            self.assertEqual(len(set(texts)), 5)
            for question in texts:
                self.assertNotIn('답:', question); self.assertNotIn('Answer:', question)
                self.assertNotIn('(으)로', question)
                if t['family'] == 'addition':
                    self.assertLess(question.index(str(t['a'])), question.index(str(t['b'])))
                else:
                    first = m['presentation']['first_subject']; second = next(n for n in t['facts'] if n != first)
                    self.assertIn(f"{first}: {t['facts'][first]}", question)
                    self.assertLess(question.index(f'{first}:'), question.index(f'{second}:'))
                    if t['family'] == 'update':
                        self.assertIn(str(t['update']['value']), question)
            with self.assertRaises(ValueError):
                d.natural_question(row, True)

    def test_corrupt_truth_trace_root_question_rejected(self):
        row = rows_fixture()[0]
        for key, value in (('root', '0'*64), ('gold_value', 999), ('question_sha256', '0'*64)):
            bad = copy.deepcopy(row); bad['meta'][key] = value
            with self.assertRaises(ValueError):
                d.validate_row(bad)
        bad = copy.deepcopy(row); bad['messages'][1]['content'] = '답: 999'
        with self.assertRaises(ValueError):
            d.validate_row(bad)

    def test_supervision_token_and_owner_sequence_not_just_count(self):
        row = rows_fixture()[0]; after = copy.deepcopy(row)
        before = SimpleNamespace(y=[-100, 7, 8, 9], segments=[0, 1, 1, 1])
        moved = SimpleNamespace(y=[-100, -100, 7, 8, 9], segments=[0, 0, 1, 1, 1])
        d.assert_same_supervision(row, after, before, moved)
        for y, owner in (([-100, 7, 8, 10], [0, 1, 1, 1]), ([-100, 7, 8, 9], [0, 1, 1, 2])):
            with self.assertRaises(ValueError):
                d.assert_same_supervision(row, after, before, SimpleNamespace(y=y, segments=owner))
        after['messages'][1]['content'] += '\nextra'
        with self.assertRaises(ValueError):
            d.assert_same_supervision(row, after, before, moved)

    def test_prepare_mock_wrong_target_mass_keeps_partial_shards_not_ready_report(self):
        rows = rows_fixture(); datasets = {'train': rows, 'val': rows[:2], 'test': rows[2:4]}
        record = SimpleNamespace(y=[-100, 7, 8], segments=[0, 1, 1], targets=2, x_tokens=10)
        old_report = dict(counts={'train': {'assistant_targets': 128116}}, actual_unique_train_x_tokens=100)
        with tempfile.TemporaryDirectory() as temp, synthetic_selection():
            root = Path(temp); corpus = root/'corpus'
            with patch.object(d, 'ROOT', root), patch.object(engine, 'paths', return_value=(corpus, root/'evidence')), \
                 patch.object(d, 'original_inputs', return_value=(datasets, old_report, {}, {})), \
                 patch.dict(sys.modules, {'tokenizers': SimpleNamespace(Tokenizer=Tokenizer)}), \
                 patch.object(clean, 'masked_record', return_value=record), patch.object(d.surface, 'digest', return_value=d.surface.TOK_SHA):
                with self.assertRaisesRegex(ValueError, '512464'):
                    d.prepare(self.args(), CODE)
            self.assertTrue((corpus/'train_000000.jsonl').is_file())
            self.assertFalse((corpus/'report.json').exists())
            self.assertNotIn('torch', sys.modules)

    def test_new_test_128_roots_768_rows_old_root_exclusion_and_seed(self):
        old = {d.rules.canonical_root(t) for t in candidates()['addition'][:3]}
        with synthetic_selection() as called:
            rows, report = d.select_test(old)
            again, repeated = d.select_test(old)
        self.assertEqual(rows, again); self.assertEqual(report, repeated)
        self.assertEqual(len(rows), 768); self.assertEqual(len(set(report['roots'])), 128)
        self.assertFalse(set(report['roots']) & old)
        self.assertEqual([c.args for c in called.call_args_list[:3]], [(f, 20261022, 50_000) for f in d.QUOTAS])
        for family, expected in d.QUOTAS.items():
            self.assertEqual(len({r['meta']['root'] for r in rows if r['meta']['family'] == family}), expected)

    def test_8_joint_cells_and_update_low_high16_each(self):
        with synthetic_selection():
            rows, report = d.select_test(set())
        update = [r for r in rows if r['meta']['family'] == 'update' and r['meta']['language'] == 'ko'
                  and r['meta']['surface_profile'] == 'STRUCTURED']
        self.assertEqual(Counter(r['meta']['selection']['update_canonical_stratum'] for r in update), {0: 16, 1: 16})
        for family in ('lookup', 'update'):
            for lang in ('ko', 'en'):
                summary = report['presentation_counts'][family+':'+lang]
                cells = [n for key, n in summary.items() if key.startswith('joint:')]
                self.assertEqual(cells, [4]*8)
        shortcut = report['shortcut_baselines']['update']
        self.assertEqual(shortcut['last_update_value'], dict(correct=32, total=64))
        self.assertEqual(shortcut['stale_asked_value'], dict(correct=32, total=64))

    def test_each_root_has_same_task_gold_order_across_six_renderings(self):
        with synthetic_selection():
            rows, _ = d.select_test(set())
        groups = defaultdict(list)
        for row in rows:
            groups[row['meta']['root']].append(row)
        for group in groups.values():
            self.assertEqual(len(group), 6)
            self.assertEqual(len({d.rules.sha(r['meta']['task']) for r in group}), 1)
            self.assertEqual(len({r['meta']['gold_value'] for r in group}), 1)
            for lang in ('ko', 'en'):
                structured, natural, final = [r for r in group if r['meta']['language'] == lang]
                self.assertEqual(d.surface.text(final['messages'][0]['content']),
                    d.surface.text(natural['messages'][0]['content'])+'\n'+d.surface.FINAL_INSTRUCTION[lang])
                self.assertEqual(structured['messages'][1], final['messages'][1])

    def test_reserved_wrong_split_and_insufficient_supply_do_not_shrink(self):
        with synthetic_selection(), patch.object(d.rules, 'is_reserved', return_value=True), self.assertRaises(ValueError):
            d.select_test(set())
        with synthetic_selection(), patch.object(d.rules, 'split_for_root', return_value='train'), self.assertRaises(ValueError):
            d.select_test(set())

    def test_exact_number_strict_final_wrong_trace_and_unparsed_are_separate(self):
        case = dict(source=rows_fixture()[0]); gold = case['source']['meta']['gold_value']
        bare = d.surface.surface_score(case, str(gold), 'trace')
        self.assertFalse(bare['final_contract']); self.assertTrue(bare['bare_numeric_exact'])
        self.assertEqual(bare['content_value_status'], 'EXACT_VALUE_MATCH')
        self.assertEqual(d.surface.surface_score(case, f'아마 {gold} 같아요.', 'trace')['content_value_status'], 'UNJUDGED_READ_RAW')
        broken = d.surface.surface_score(case, f'Q:wrong\n답: {gold}', 'trace')
        self.assertTrue(broken['final_correct']); self.assertFalse(broken['trace_valid'])

    def test_deadline_timezone_boundary_and_bounded_remaining_window(self):
        with patch.object(d.surface, 'utc_now', return_value=NOW):
            self.assertEqual(d.check_time(self.args()), d.MODEL_END)
            for changes in (dict(deadline='2026-10-22T16:30:00'), dict(max_wall_sec=0), dict(max_wall_sec=20000),
                            dict(deadline='2026-10-22T12:00:10+09:00'), dict(deadline='2026-10-23T16:30:00+09:00')):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    d.check_time(self.args(**changes))
            with self.assertRaises(ValueError):
                d.check_time(self.args('train', deadline=d.USER_END.isoformat()))
            self.assertEqual(d.check_time(self.args(deadline=d.USER_END.isoformat())), d.USER_END)

    def test_original_guard_budget_is_floor_of_all_caps_and_remaining_restored(self):
        for fail in (False, True):
            wall = [100.0]; now = [NOW]; calls = []
            @contextmanager
            def original(seconds):
                calls.append(seconds)
                try:
                    yield
                finally:
                    wall[0] += 7.5; now[0] += timedelta(seconds=7.5)
            gate = SimpleNamespace(wall_limit=original)
            a = self.args('train', max_wall_sec=300, deadline=(NOW+timedelta(seconds=200.8)).isoformat())
            a._end_monotonic = 250.9  # 총 wall 남음150.9초; 이미 쓴 준비149.1초는 돌려주지 않음
            with patch.object(d.time, 'monotonic', side_effect=lambda: wall[0]), \
                 patch.object(d.surface, 'utc_now', side_effect=lambda: now[0]), patch.object(d.signal, 'setitimer') as timer:
                with d.bounded_engine_wall(a, gate):
                    try:
                        with gate.wall_limit(180):
                            if fail:
                                raise RuntimeError('합성 guard 본문 오류')
                    except RuntimeError:
                        self.assertTrue(fail)
                self.assertEqual(calls, [150])
                self.assertLessEqual(calls[0], min(180, 200.8, 150.9))
                self.assertAlmostEqual(timer.call_args.args[1], 143.4)
                self.assertIs(gate.wall_limit, original)

    def test_expired_or_fractional_zero_budget_never_enters_model_or_disarms_alarm(self):
        for remaining in (0, .8, -.1, 59.9):
            calls = []
            @contextmanager
            def original(seconds):
                calls.append(seconds); yield
            gate = SimpleNamespace(wall_limit=original); a = self.args('train'); a._end_monotonic = 100+remaining
            with patch.object(d.time, 'monotonic', return_value=100), patch.object(d.surface, 'utc_now', return_value=NOW), \
                 patch.object(d.signal, 'setitimer') as timer, d.bounded_engine_wall(a, gate):
                with self.assertRaises(d.surface.BudgetExpired):
                    with gate.wall_limit(300):
                        self.fail('기한 부족인데 모델 본문 진입')
            self.assertEqual(calls, []); timer.assert_not_called()

    def test_cli_modes_no_control_training_model_and_explicit_code_pin(self):
        base = ['--mode', 'prepare', '--deadline', d.MODEL_END.isoformat(), '--max-wall-sec', '60']
        with patch.object(d.surface, 'utc_now', return_value=NOW):
            a = d.arguments(base+['--check-only']); self.assertEqual((a.tag, a.arm), (d.TAG, 'parent_ntp'))
            for extra in (['--execute'], ['--check-only', '--model', 'control'], ['--check-only', '--run-id', '../bad']):
                with self.assertRaises(ValueError):
                    d.arguments(base+extra)

    def test_check_only_python_reads_no_assets_torch_tokenizers_or_writes(self):
        real = d.surface.digest; touched = []
        def digest(path):
            self.assertEqual(path.suffix, '.py'); touched.append(path)
            return real(path)
        with patch.object(d, 'arguments', return_value=self.args(execute=False, check_only=True)), \
             patch.object(d.surface, 'digest', side_effect=digest), patch.object(d, 'execute', side_effect=AssertionError('실행 금지')), \
             patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(d.main([]), 0)
        self.assertTrue(touched); self.assertNotIn('torch', sys.modules); self.assertNotIn('tokenizers', sys.modules)

    def test_direct_script_import_in_fresh_process_and_no_heavy_imports(self):
        source = "import runpy,sys; x=runpy.run_path('scripts/p101a_reasoning_surface_bridge.py',run_name='not_main'); assert 'torch' not in sys.modules; assert 'tokenizers' not in sys.modules; print(x['TAG'])"
        completed = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', source], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr); self.assertIn(d.TAG, completed.stdout)

    def test_source_pin_mutation_and_execute_pin_mismatch_rejected(self):
        with patch.object(d.surface, 'digest', return_value='0'*64), self.assertRaises(ValueError):
            d.source_contract()
        with patch.object(d, 'arguments', return_value=self.args(code_sha256='0'*64)), \
             patch.object(d, 'source_contract', return_value=CODE), patch.object(d, 'execute', side_effect=AssertionError('실행')), \
             self.assertRaises(ValueError):
            d.main([])

    def test_snapshot_mutation_symlink_and_write_once_guards(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(d, 'ROOT', Path(temp)):
            path = Path(temp)/'source.json'; path.write_text('{}', encoding='utf-8'); files = d.snapshot([path]); d.unchanged(files)
            path.write_text('{"changed":true}', encoding='utf-8')
            with self.assertRaises(ValueError):
                d.unchanged(files)
            link = Path(temp)/'linked'; link.symlink_to(Path(temp), target_is_directory=True)
            with self.assertRaises(ValueError):
                d.safe(link/'new.json')
            output = Path(temp)/'report.json'; d.surface.write_json(output, {'a': 1}); before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                d.surface.write_json(output, {'a': 2})
            self.assertEqual(output.read_bytes(), before)

    def test_partial_or_late_receipt_never_admitted(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp); path = d.receipt(evidence, 'train'); path.parent.mkdir()
            good = dict(status='ADAPTER_COMPLETE', returncode=0, mode='train', code_sha256=CODE['code_sha256'],
                        finished_at=NOW.isoformat(), deadline=d.MODEL_END.isoformat())
            for changes in (dict(status='PARTIAL_OR_FAILED'), dict(returncode=124), dict(code_sha256='0'*64),
                            dict(finished_at=d.USER_END.isoformat()), dict(deadline=d.USER_END.isoformat())):
                path.write_text(json.dumps(dict(good, **changes)), encoding='utf-8')
                with self.assertRaises(ValueError):
                    d.require_receipt(evidence, 'train', CODE)
            path.write_text(json.dumps(good), encoding='utf-8'); self.assertEqual(d.require_receipt(evidence, 'train', CODE), good)

    def test_execute_success_error_deadline_and_existing_namespace_preserved(self):
        for failure, expected in ((None, 0), (ValueError('합성 오류'), 9), (d.surface.BudgetExpired('기한'), 124)):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with patch.object(engine, 'paths', return_value=(root/'corpus', root/'evidence')), \
                     patch.object(d.surface, 'utc_now', return_value=NOW), patch.object(d, 'source_contract', return_value=CODE), \
                     patch.object(d, 'prepare', return_value={'synthetic': True}, side_effect=failure):
                    self.assertEqual(d.execute(self.args(), CODE), expected)
                    report = json.loads((root/'evidence/adapter_prepare/report.json').read_text())
                    self.assertEqual(report['returncode'], expected)
                    with self.assertRaises(FileExistsError):
                        d.execute(self.args(), CODE)

    def test_train_calls_frozen_engine_clean_factories_and_restores_patch_state(self):
        report = dict(initial_core_sha256='I'*64, original_inputs_sha256={}, actual_unique_train_x_tokens=8192,
            target_processed_x_tokens=32768, original_control={'tag': d.CONTROL}, independent_variable='user expression', semantic_quality='code')
        result = dict(updates=32, assistant_targets=128116, initial_core_sha256='I'*64,
                      status='COST_CALIBRATION_COMPLETE', checkpoint_saved=False)
        old_encoded, old_optimizer, old_runtime, old_factory = engine.encoded, engine.optimizers, engine.load_runtime, clean.ORIGINAL_OPTIMIZERS
        def called(args, corpus, evidence, meta, **kw):
            self.assertEqual(args.tag, d.TAG); self.assertEqual(args.arm, 'parent_ntp')
            self.assertEqual(kw, dict(calibrate=True, epochs=4)); self.assertEqual(meta['lr'], 5e-5); self.assertEqual(meta['muon_lr'], 2e-4)
            self.assertIs(engine.optimizers, clean.optimizers); self.assertIs(clean.ORIGINAL_OPTIMIZERS, old_optimizer)
            self.assertEqual(engine.load_runtime('parent_ntp')[4], 'I'*64)
            records = [SimpleNamespace(targets=32 if i < 1140 else 31, x_tokens=2) for i in range(4096)]
            with patch.object(clean, 'encoded', return_value={'train': records, 'val': []}) as encoder:
                self.assertEqual(len(engine.encoded(corpus, report, None)['train']), 4096); encoder.assert_called_once()
            self.assertNotIn('train_wrong_assistant', meta); self.assertFalse(meta['mtp_aux'])
            return 0
        with patch.object(d, 'prepared_inputs', return_value=(Path('/synthetic/corpus'), Path('/synthetic/evidence'), report)), \
             patch.object(d, 'corpus_snapshot', return_value={}), patch.object(d, 'snapshot', return_value={}), \
             patch.object(d, 'bounded_engine_wall', return_value=nullcontext()), \
             patch.object(d, 'unchanged'), patch.object(engine, 'info', return_value={}), patch.object(engine, 'train_arm', side_effect=called), \
             patch.object(engine, 'load_runtime', return_value=(None, None, SimpleNamespace(mtp_aux=False, grad_checkpoint=True), None, 'I'*64)), \
             patch.object(d, 'read_json', return_value=result), patch.object(d.surface, 'digest', return_value='A'*64):
            self.assertEqual(d.train(self.args('calibrate'), CODE)['updates'], 32)
        self.assertEqual((engine.encoded, engine.optimizers, engine.load_runtime, clean.ORIGINAL_OPTIMIZERS),
                         (old_encoded, old_optimizer, old_runtime, old_factory))

    def test_training_requires_new_cost32_and_enough_explicit_reserve(self):
        report = dict(original_inputs_sha256={})
        cost = dict(status='COST_CALIBRATION_COMPLETE', updates=32, code_sha256=CODE['code_files_sha256'], corpus_sha256='A'*64,
                    estimated_full_update_sec=100, whole_wall_sec=40, update_seconds=[2]*32)
        prior = {'result': {'engine_report_sha256': 'A'*64}}
        with patch.object(d, 'prepared_inputs', return_value=(Path('/mock'), Path('/mock'), report)), \
             patch.object(d, 'corpus_snapshot', return_value={}), patch.object(d, 'snapshot', return_value={}), \
             patch.object(d, 'require_receipt', return_value=prior), patch.object(d, 'read_json', return_value=cost), \
             patch.object(d.surface, 'digest', return_value='A'*64), patch.object(engine, 'train_arm', side_effect=AssertionError('학습 금지')):
            with self.assertRaises(ValueError):
                d.train(self.args('train', max_wall_sec=60), CODE)
            cost['updates'] = 31
            with self.assertRaises(ValueError):
                d.train(self.args('train', max_wall_sec=1000), CODE)

    def fake_runtime(self, answers='20', fail_at=None):
        from tinylm.chat.serialize import serialize
        calls = []
        def sample(model, cfg, tok, prompt, **kw):
            calls.append(kw)
            if fail_at is not None and len(calls) == fail_at:
                raise d.surface.BudgetExpired('합성 중단')
            self.assertEqual((kw['temperature'], kw['top_k'], kw['device'], kw['mtp_tokens']), (0, 1, 'cpu', 1))
            return prompt+answers+'<|im_end|>', dict(generated_tokens=2, finish_reason='STOP_SEQUENCE')
        rt = SimpleNamespace(Tokenizer=Tokenizer, load_model=lambda **kw: (Model(), SimpleNamespace(max_seq_len=1024, mtp_aux=False), 'cpu'),
            PrecisionForward=lambda model, mode: model, serialize=serialize, sample=sample, torch=SimpleNamespace(float32='float32'))
        @contextmanager
        def runtime():
            yield rt
        return runtime, calls

    def collect(self, temp, fail_at=None, long=False, changed_cp=False):
        root = Path(temp); folder = root/'raw'; folder.mkdir()
        row = rows_fixture()[0]; row['meta']['surface_profile'] = 'UNSEEN_NATURAL'; rows = [row]*768
        runtime, calls = self.fake_runtime(fail_at=fail_at)
        identity = dict(checkpoint_sha256='C'*64, original_inputs_sha256={}, input_files_sha256={})
        with patch.object(d, 'ROOT', root), patch.object(d, 'evaluation_inputs', return_value=(rows, root/'never_opened.pt', identity)), \
             patch.object(d.surface, 'cpu_runtime', runtime), patch.object(d.surface, 'utc_now', return_value=NOW), \
             patch.object(d.surface, 'digest', return_value=('X' if changed_cp else 'C')*64), patch.object(Tokenizer, 'long', long), \
             patch('sys.stdout', new_callable=io.StringIO):
            if fail_at or long or changed_cp:
                with self.assertRaises(d.surface.BudgetExpired if fail_at else ValueError):
                    d.evaluate(self.args('evaluate'), CODE, folder)
            else:
                self.assertEqual(d.evaluate(self.args('evaluate'), CODE, folder)['completed'], 768)
        return root, folder, calls

    def test_mock_cpu_full768_first32_are_kept_once_and_review_raw_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root, folder, calls = self.collect(temp)
            result = json.loads((folder/'collection.json').read_text()); self.assertEqual(len(calls), 768)
            self.assertEqual(result['completed'], 768); self.assertEqual(result['raw_manifest']['rows'], 768)
            self.assertEqual(result['summaries']['UNSEEN_NATURAL:ko']['bare_numeric_exact'], 0)  # gold is34, fake20 is wrong
            raw = [json.loads(line) for s in result['raw_manifest']['shards'] for line in (folder/s['path']).read_text().splitlines()]
            self.assertEqual([r['index'] for r in raw], list(range(768))); self.assertEqual(raw[0]['answer'], '20')
            self.assertIn('20', (root/result['reviews'][0]).read_text())
            self.assertTrue(all((root/p).stat().st_size < 20_000_000 for p in result['reviews']))

    def test_mock_timeout_partial_raw_review_and_context_rejection_no_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            _, folder, calls = self.collect(temp, fail_at=4)
            report = json.loads((folder/'collection.json').read_text()); self.assertEqual(report['completed'], 3)
            self.assertEqual(report['status'], 'PARTIAL'); self.assertEqual(report['raw_manifest']['rows'], 3); self.assertEqual(len(calls), 4)
        with tempfile.TemporaryDirectory() as temp:
            _, folder, calls = self.collect(temp, long=True)
            report = json.loads((folder/'collection.json').read_text()); self.assertEqual(report['completed'], 0)
            self.assertEqual(calls, []); self.assertIsNone(report['raw_manifest'])

    def test_mock_768_answers_but_changed_cp_is_partial_not_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            _, folder, calls = self.collect(temp, changed_cp=True)
            report = json.loads((folder/'collection.json').read_text())
            self.assertEqual(len(calls), 768); self.assertEqual(report['completed'], 768)
            self.assertEqual(report['status'], 'PARTIAL'); self.assertEqual(report['error']['type'], 'ValueError')


if __name__ == '__main__':
    unittest.main()
