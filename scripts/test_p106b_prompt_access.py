"""Small pure-stdlib/temp fixtures; no real tokenizer/CP/model/GPU or outputs."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout, redirect_stderr
import copy
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
BASELINE_IMPORTS = set(sys.modules)
from scripts import diag_p106b_prompt_access as d


@contextmanager
def noop(*_args, **_kwargs): yield


class FixtureTokenizer:
    def __init__(self):
        texts = [d.render_input(c, f)['text'] for c in d.cases() for f in d.FORMATS]
        texts += [c['oracle'] for c in d.cases() if c['oracle'] is not None] + ['Fixture reply.', 'corrupt']
        chars = sorted(set(''.join(texts))); self.enc = {c: i + 10 for i, c in enumerate(chars)}
        self.dec = {v: k for k, v in self.enc.items()}
    def encode(self, text): return SimpleNamespace(ids=[self.enc[c] for c in text])
    def decode(self, ids, **_kwargs): return ''.join(self.dec[i] for i in ids)


class Fixture:
    def __init__(self, root, fail_exit=None):
        self.root = root; self.tok = FixtureTokenizer(); self.loads = []; self.fail_exit = fail_exit
        self.manifest = {'fixture': 'not an actual model manifest'}
        bindings = {s.name: dict(checkpoint=s.checkpoint, checkpoint_sha256=d.sha(['CP', s.name]),
            core_sha256=d.sha(['CORE', s.name]), report_sha256=d.sha(['REPORT', s.name]),
            quantization_route=dict(mode=s.arm)) for s in d.ui.MODELS}
        self.info = dict(schema=d.SCHEMA, tag=d.TAG, bindings=bindings, source_sha256={'fixture.py': 'A' * 64},
            manifest_sha256=d.sha(self.manifest), tokenizer_sha256=d.ui.TOKENIZER_SHA, requests_sha256=d.sha(d.requests()))

    @contextmanager
    def selected(self, spec, root):
        self.loads.append(spec.name); binding = self.info['bindings'][spec.name]
        active = dict(binding, name=spec.name, tokenizer=self.tok, cfg=SimpleNamespace(max_seq_len=1024),
            route=SimpleNamespace(assert_active=lambda: None), model=SimpleNamespace(core=binding['core_sha256']),
            manifest_sha256=self.info['manifest_sha256'], tokenizer_sha256=d.ui.TOKENIZER_SHA, root=str(root),
            gpu_point_query=dict(scope='NVML_POINT_QUERY_ONLY_NOT_CONTINUOUS_OR_OOM_GUARANTEE'),
            precision='FP32_MATH', body_check_scope='CPU_LOAD_GPU_LOAD_AND_SESSION_EXIT')
        try:
            yield active
            if spec.name == self.fail_exit: raise RuntimeError('fixture final context core check failed')
        finally: active.clear()

    def emit(self, active, case, form):
        rendered = d.render_input(case, form); prefix = self.tok.encode(rendered['text']).ids
        answer = case['oracle'] if case['oracle'] is not None else 'Fixture reply.'
        generated = self.tok.encode(answer).ids + [4]
        metadata = dict(finish_reason='STOP_SEQUENCE', generated_tokens=len(generated), max_new=64,
            eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True,
            stop_token_sequences=[[4]], matched_stop_sequence=[4])
        text, generation = d.ui.answer_from_tokens(self.tok, prefix, prefix + generated, metadata, 64)
        generation.update(precision='FP32_MATH', tf32=False, use_cache=True, mtp=False, temperature=0., top_k=1,
            actual_history=False, prompt_sha256=d.text_sha(rendered['text']), prompt_ids=prefix, prompt_ids_sha256=d.sha(prefix))
        return text, generation, rendered

    @contextmanager
    def patches(self):
        fixed = datetime(2026, 10, 21, 3, 30, tzinfo=timezone.utc)
        with patch.object(d, 'metadata', return_value=self.info), patch.object(d, 'authority', return_value=10000), \
                patch.object(d, 'utc_now', return_value=fixed), patch.object(d, 'bounded', side_effect=noop), \
                patch.object(d.os, 'getpid', return_value=123), patch.object(d.os, 'getpgrp', return_value=123), \
                patch.object(d.ui, 'selected_runtime', side_effect=self.selected), patch.object(d, 'emit_request', side_effect=self.emit), \
                patch.object(d.ui, 'state_fingerprint', side_effect=lambda model: model.core), \
                patch.object(d.ui, 'verify_manifest', return_value=self.manifest), patch.object(d.ui, 'validate_import_environment'), \
                patch.object(d.ui, 'local_tokenizer', return_value=self.tok):
            yield


class ProbeTests(unittest.TestCase):
    def test_frozen_24_bilingual_probes_16_oracles_8_human_and_exact_576_order(self):
        cases = d.cases(); requests = d.requests()
        self.assertEqual(len(cases), 24); self.assertEqual(len({c['root'] for c in cases}), 12)
        self.assertEqual(sum(c['oracle'] is not None for c in cases), 16)
        self.assertEqual(sum(c['oracle'] is None for c in cases), 8)
        self.assertEqual([c['oracle'] for c in cases[:8]], ['2', '2', '4', '4', '12', '12', '12', '12'])
        self.assertEqual([c['oracle'] for c in cases[8:16]], ['당근', 'carrot', '5', '5', '파랑', 'blue', '3', '3'])
        self.assertEqual(len(requests), 576); self.assertEqual(requests, d.requests())
        for i, name in enumerate(d.MODEL_NAMES):
            lane = requests[i * 96:(i + 1) * 96]
            self.assertEqual({r['model'] for r in lane}, {name})
            self.assertEqual([r['format'] for r in lane], [f for f in d.FORMATS for _ in range(24)])

    def test_four_inputs_keep_original_question_and_fewshot_is_one_explicit_user_not_history(self):
        for case in d.cases():
            for form in d.FORMATS:
                rendered = d.render_input(case, form)
                self.assertEqual(rendered['question'], case['question']); self.assertIn(case['question'], rendered['text'])
                self.assertFalse(rendered['actual_history'])
                if form == 'raw_qa':
                    self.assertIsNone(rendered['user_text']); self.assertNotIn('<|', rendered['text'])
                    self.assertTrue(rendered['text'].endswith('답:' if case['language'] == 'ko' else 'Answer:'))
                else:
                    self.assertEqual(rendered['text'].count('<|im_start|>'), 2)
                    self.assertEqual(rendered['text'], '<|im_start|>user\n' + rendered['user_text'] + '<|im_end|>\n<|im_start|>assistant\n')
                if form == 'chat_bare': self.assertEqual(rendered['user_text'], case['question'])
                if form == 'chat_fewshot':
                    self.assertTrue(2 <= len(rendered['demonstrations']) <= 3)
                    for demo in rendered['demonstrations']:
                        self.assertNotEqual(demo['root'], case['root']); self.assertNotEqual(demo['question'], case['question'])
                        if case['family'] == 'general': self.assertNotIn('apples', demo['question']); self.assertNotIn('농구', demo['question'])
        with self.assertRaises(ValueError): d.render_input(d.cases()[0], 'adaptive_best')

    def test_strict_literal_is_not_semantic_correctness_and_general_has_no_automatic_score(self):
        case = d.cases()[0]
        self.assertTrue(d.score(case, '2'))
        for answer in (' 2', '2\n', 'The answer is 2.', '12', '답: 2'):
            self.assertFalse(d.score(case, answer))
        for case in d.cases()[16:]: self.assertIsNone(d.score(case, 'anything including a good reply'))

    def test_predeclared_whitespace_secondary_leaves_primary_and_raw_unchanged(self):
        case = d.cases()[0]
        for answer in ('2\n', ' 2', '\t2\r\n', '\u20032\u2003'):
            original = answer; self.assertFalse(d.score(case, answer)); self.assertTrue(d.whitespace_score(case, answer))
            self.assertEqual(answer, original)
        for answer in ('The answer is 2.', 'Answer: 2', '2 2', '12'):
            self.assertFalse(d.score(case, answer)); self.assertFalse(d.whitespace_score(case, answer))
        for case in d.cases()[16:]:
            self.assertIsNone(d.score(case, 'good reply\n')); self.assertIsNone(d.whitespace_score(case, 'good reply\n'))

    def test_fixed_sample_selection_does_not_depend_on_answer_or_score(self):
        self.assertEqual(d.SAMPLE_CASE_IDS, ('add_1_1_ko', 'younghee_5_ko', 'apple_general_ko', 'greeting_general_en'))
        selected = []
        for request in d.requests():
            case = request['case']; row = dict(request=request, input=d.render_input(case, request['format']),
                answer='deliberately wrong\n', generation=dict(finish_reason='MAX_NEW'),
                exact_literal_match=d.score(case, 'deliberately wrong\n'),
                whitespace_literal_match=d.whitespace_score(case, 'deliberately wrong\n'))
            sample = d.sample_payload(row)
            self.assertEqual(sample is not None, case['id'] in d.SAMPLE_CASE_IDS)
            if sample is not None:
                self.assertEqual(sample['actual_answer'], row['answer']); self.assertEqual(sample['input_text'], row['input']['text'])
                selected.append((sample['model'], sample['format'], sample['case_id']))
        self.assertEqual(len(selected), 96)
        self.assertEqual(set(selected), {(m, f, c) for m in d.MODEL_NAMES for f in d.FORMATS for c in d.SAMPLE_CASE_IDS})

    def test_oracles_have_independent_arithmetic_and_fact_state_checks(self):
        by_id = {case['id']: case for case in d.cases()}
        for root, value in (('add_1_1', 1 + 1), ('add_2_2', 2 + 2), ('add_7_5', 7 + 5), ('sub_20_8', 20 - 8)):
            for language in ('ko', 'en'): self.assertEqual(by_id[root + '_' + language]['oracle'], str(value))
        self.assertEqual(by_id['food_B_ko']['oracle'], {'A': '사과', 'B': '당근'}['B'])
        self.assertEqual(by_id['food_B_en']['oracle'], {'A': 'apple', 'B': 'carrot'}['B'])
        self.assertEqual(by_id['younghee_5_ko']['oracle'], str({'민수': 3, '영희': 5}['영희']))
        self.assertEqual(by_id['book_blue_en']['oracle'], {'book': 'blue', 'card': 'red'}['book'])
        values = {'A': 1, 'B': 8}; values['B'] = 3
        self.assertEqual(by_id['update_B_3_ko']['oracle'], str(values['B']))


class SafetyTests(unittest.TestCase):
    def test_false_gate_is_patched_not_an_assertion_about_release_source_and_imports_are_stdlib(self):
        with patch.object(d, 'IMPLEMENTATION_READY', False), patch.object(d, 'metadata', side_effect=AssertionError('actual metadata reached')):
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--mode', 'evaluate', '--execute']), 8)
        introduced = set(sys.modules) - BASELINE_IMPORTS
        self.assertFalse(any(n.startswith(('torch', 'tokenizers', 'tinylm')) for n in introduced))

    def test_guarded_temp_output_paths_and_write_once_ignore_real_outputs(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_paths_') as temporary:
            root = Path(temporary); relative = d.report_path('evaluate')
            d.write_json(relative, {'fixture': 1}, root); self.assertEqual(d.read_json(relative, root), {'fixture': 1})
            with self.assertRaises(FileExistsError): d.write_json(relative, {'fixture': 2}, root)
            for bad in ('../outside.json', 'HF/raw.json', 'datasets/TinyDataset/a.json', 'data_cache/a.json', '/tmp/outside.json'):
                with self.assertRaises(ValueError): d.owned_path(bad, root)
            with self.assertRaises(ValueError): d.write_json('test_result/evidence/other/report.json', {}, root)
            (root / 'outside').mkdir(); (root / 'runs').mkdir(); (root / 'runs/eval').symlink_to(root / 'outside', target_is_directory=True)
            with self.assertRaises(ValueError): d.write_json(d.raw_path() + '/report.json', {}, root)
            self.assertEqual(list((root / 'outside').iterdir()), [])

    def test_own_evaluate16h40_and_readback17h_no_training_clock(self):
        evaluate_end = datetime.fromisoformat(d.LIMITS['end_utc']); report_end = datetime.fromisoformat(d.REPORT_END)
        self.assertEqual(d.authority('evaluate', evaluate_end - timedelta(seconds=1)), 1)
        with self.assertRaises(d.Hold): d.authority('evaluate', evaluate_end)
        self.assertEqual(d.authority('readback', report_end - timedelta(seconds=1)), 1)
        with self.assertRaises(d.Hold): d.authority('readback', report_end)
        with self.assertRaises(ValueError): d.authority('evaluate', datetime(2026, 10, 21))

    def test_alarm_and_sigterm_are_real_handlers_with_restored_prior_timer_no_sleep(self):
        handlers = {}; timers = []
        with patch.object(d.signal, 'getsignal', return_value='old'), patch.object(d.signal, 'getitimer', return_value=(0., 0.)), \
                patch.object(d.signal, 'signal', side_effect=lambda number, handler: handlers.__setitem__(number, handler)), \
                patch.object(d.signal, 'setitimer', side_effect=lambda *args: timers.append(args)):
            with self.assertRaises(d.Hold):
                with d.bounded(600): handlers[d.signal.SIGALRM](0, None)
            with self.assertRaises(KeyboardInterrupt):
                with d.bounded(600): handlers[d.signal.SIGTERM](0, None)
        self.assertEqual(timers, [(d.signal.ITIMER_REAL, 600), (d.signal.ITIMER_REAL, 0., 0.)] * 2)

    def test_external_wait_cap600_then_sigterm30_not_660(self):
        process = SimpleNamespace(pid=123, wait=unittest.mock.Mock(side_effect=[d.subprocess.TimeoutExpired('fixture', 600), 130]))
        with patch.object(d.subprocess, 'Popen', return_value=process) as popen, patch.object(d.os, 'killpg') as kill:
            self.assertEqual(d.launch(['fixture'], 600), 130)
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertEqual([c.kwargs['timeout'] for c in process.wait.call_args_list], [600, 30]); kill.assert_called_once_with(123, d.signal.SIGTERM)

    def test_static_true_fixture_does_not_reach_worker(self):
        with patch.object(d, 'IMPLEMENTATION_READY', True), patch.object(d, 'metadata', return_value={'source_sha256': {}}), \
                patch.object(d, 'worker', side_effect=AssertionError('worker')):
            out = io.StringIO()
            with redirect_stdout(out): self.assertEqual(d.main(['--mode', 'evaluate', '--check-only']), 0)
            self.assertIn('"torch_imports": 0', out.getvalue())
        with redirect_stderr(io.StringIO()): self.assertEqual(d.main(['--mode', 'evaluate', '--max-wall-sec', '30', '--check-only']), 9)

    def test_metadata_reads_only_fixture_f4_sources_and_ui_metadata_no_assets_or_model(self):
        design = dict(models=list(d.MODEL_NAMES), formats=list(d.FORMATS), cases=24, oracle_cases=16, qualitative_cases=8,
            requests=576, max_new=64, precision='FP32_MATH', tf32=False, kv=True, mtp=False, greedy=True,
            temperature=0, top_k=1, weight_updates=0, checkpoint_writes=0, teacher_calls=0)
        f4 = dict(schema='TINYLM_PROMPT_ACCESS_F4_V1', tag=d.TAG, design=design, limits=d.LIMITS)
        manifest = dict(source_sha256={'fixture_ui.py': 'A' * 64}, entries={})
        for spec in d.ui.MODELS:
            manifest['entries'][spec.name] = dict(checkpoint=dict(path=spec.checkpoint, sha256='B' * 64),
                core_sha256='C' * 64, report=dict(sha256='D' * 64), header=dict(quantization_route=dict(mode=spec.arm)))
        with tempfile.TemporaryDirectory(prefix='prompt_access_metadata_') as temporary:
            root = Path(temporary); path = root / d.F4; path.parent.mkdir(parents=True); path.write_text(json.dumps(f4), encoding='utf-8')
            for name in d.EXTRA_SOURCES:
                source = root / name; source.parent.mkdir(parents=True, exist_ok=True); source.write_text('fixture source\n', encoding='utf-8')
            with patch.object(d.ui, 'verify_manifest', return_value=manifest) as verify, \
                    patch.object(d.ui, 'local_tokenizer', side_effect=AssertionError('tokenizer asset reached')), \
                    patch.object(d.ui, 'inference_modules', side_effect=AssertionError('model import reached')), \
                    patch.object(d.ui, 'selected_runtime', side_effect=AssertionError('runtime reached')):
                info = d.metadata(root); verify.assert_called_once_with(root)
                self.assertEqual(info['design']['requests'], 576); self.assertEqual(len(info['bindings']), 6)
                self.assertTrue(set(d.EXTRA_SOURCES) <= set(info['source_sha256']))
                f4['design']['tf32'] = 0; path.write_text(json.dumps(f4), encoding='utf-8')
                with self.assertRaises(ValueError): d.metadata(root)

    def test_readonly_has_own_report_deadline_and_smaller_remaining_alarm(self):
        args = SimpleNamespace(mode='evaluate'); caps = []
        @contextmanager
        def limit(seconds): caps.append(seconds); yield
        with patch.object(d, 'authority', return_value=37.), patch.object(d, 'bounded', side_effect=limit), \
                patch.object(d, 'metadata', return_value={}), patch.object(d, 'readback', return_value={'status': 'FIXTURE', 'rows': 576}):
            with redirect_stdout(io.StringIO()): self.assertEqual(d.verify_readonly(args), 0)
        self.assertEqual(caps, [37.])
        with patch.object(d, 'authority', side_effect=d.Hold('expired')), patch.object(d, 'metadata') as metadata:
            with self.assertRaises(d.Hold): d.verify_readonly(args)
            metadata.assert_not_called()

    def test_final_three_phase_receipt_waits_for_raw_readonly_not_worker_only(self):
        args = SimpleNamespace(mode='evaluate'); output = io.StringIO()
        with patch.object(d, 'launch', side_effect=[0, 0, 0, 8]) as launch, patch.object(d, 'authority', return_value=37.):
            with redirect_stdout(output): self.assertEqual(d.execute(args), 8)
        self.assertEqual(launch.call_count, 4); self.assertEqual(launch.call_args.args[1], 37.)
        final = json.loads(output.getvalue().split('[EXPERIMENT_FINAL] ')[-1])
        self.assertEqual(final['status'], 'HOLD'); self.assertEqual(final['phases'][-1]['status'], 'HOLD')
        self.assertNotIn('"status": "COMPLETE"', output.getvalue())


class EndToEndFixtureTests(unittest.TestCase):
    def args(self, mode='evaluate'): return SimpleNamespace(mode=mode, max_wall_sec=600)

    def run_fixture(self, root, fail_exit=None):
        fixture = Fixture(root, fail_exit)
        output = io.StringIO()
        with fixture.patches(), redirect_stdout(output): code = d.worker(self.args(), root)
        fixture.stdout = output.getvalue()
        return fixture, code

    def update_report_hash(self, root, mode):
        activity = d.read_json(d.activity_path(mode), root)
        activity['result_sha256'] = d.ui.file_sha(root / d.report_path(mode))
        (root / d.activity_path(mode)).write_text(json.dumps(activity), encoding='utf-8')

    def test_all576_one_load_per_model_raw_full_summary_and_readback_no_model(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_complete_') as temporary:
            root = Path(temporary); fixture, code = self.run_fixture(root)
            self.assertEqual(code, 0); self.assertEqual(fixture.loads, list(d.MODEL_NAMES))
            with fixture.patches(): result = d.readback(fixture.info, root)
            self.assertEqual(result['rows'], 576); self.assertEqual(result['models_loaded'], 0)
            self.assertEqual(result['summary']['total'], dict(requests=576, oracle=384, qualitative=192, exact_literal_match=384, whitespace_literal_match=384))
            self.assertEqual(len(result['summary']['by_model_format']), 24)
            for group in result['summary']['by_model_format'].values():
                self.assertEqual((group['rows'], group['oracle'], group['qualitative']), (24, 16, 8))
            report = d.read_json(d.report_path('evaluate'), root)
            samples = [json.loads(line.split('] ', 1)[1]) for line in fixture.stdout.splitlines() if line.startswith('[PROMPT_ACCESS_SAMPLE] ')]
            progress = [json.loads(line.split('] ', 1)[1]) for line in fixture.stdout.splitlines() if line.startswith('[PROMPT_ACCESS_PROGRESS] ')]
            self.assertEqual(len(samples), 96); self.assertEqual(len(progress), 24)
            self.assertEqual({(s['model'], s['format'], s['case_id']) for s in samples},
                             {(m, f, c) for m in d.MODEL_NAMES for f in d.FORMATS for c in d.SAMPLE_CASE_IDS})
            self.assertEqual([p['total_answers'] for p in progress], list(range(24, 577, 24)))
            self.assertTrue(all(p['format_answers'] == 24 for p in progress))
            self.assertEqual(report['stdout_sample_lines'], 96); self.assertEqual(report['stdout_progress_lines'], 24)
            for group in result['summary']['by_model_format'].values():
                self.assertIn('question_substring_present', group); self.assertNotIn('question_copied', group)
            self.assertEqual(len(report['sessions']), 6); self.assertTrue(all(s['session_exit_verified'] and s['answers'] == 96 for s in report['sessions']))
            with fixture.patches(), redirect_stdout(io.StringIO()): self.assertEqual(d.worker(self.args('readback'), root), 0)
            with fixture.patches(), redirect_stdout(io.StringIO()): self.assertEqual(d.verify_readonly(self.args('readback'), root), 0)

    def test_last_session_exit_failure_preserves576_raw_but_never_complete(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_exit_fail_') as temporary:
            root = Path(temporary); fixture, code = self.run_fixture(root, d.MODEL_NAMES[-1])
            self.assertEqual(code, 9); self.assertFalse((root / d.report_path('evaluate')).exists())
            activity = d.read_json(d.activity_path('evaluate'), root); self.assertFalse(activity['complete'])
            manifest = d.read_json(d.raw_path() + '/answers_shards_manifest.json', root)
            self.assertEqual(manifest['rows'], 576); self.assertTrue(manifest['lineage']['partial'])
            with fixture.patches(), self.assertRaises(FileNotFoundError): d.readback(fixture.info, root)

    def test_readback_independently_rejects_changed_summary_even_if_report_hash_is_rebound(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_summary_fail_') as temporary:
            root = Path(temporary); fixture, code = self.run_fixture(root); self.assertEqual(code, 0)
            original = d.read_json(d.report_path('evaluate'), root)
            for metric in ('exact_literal_match', 'whitespace_literal_match'):
                report = copy.deepcopy(original); report['summary']['total'][metric] = 0
                (root / d.report_path('evaluate')).write_text(json.dumps(report), encoding='utf-8'); self.update_report_hash(root, 'evaluate')
                with fixture.patches(), self.assertRaisesRegex(ValueError, 'summary differs'): d.readback(fixture.info, root)

    def test_bad_ids_input_request_or_literal_cannot_pass_raw_regrade(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_raw_fail_') as temporary:
            root = Path(temporary); fixture, code = self.run_fixture(root); self.assertEqual(code, 0)
            report = d.read_json(d.report_path('evaluate'), root); rows = []
            for part in report['raw_manifest']['shards']:
                rows.extend(json.loads(line) for line in (root / d.raw_path() / part['path']).read_text(encoding='utf-8').splitlines())
            changed = copy.deepcopy(rows); changed[0]['exact_literal_match'] = False
            with self.assertRaisesRegex(ValueError, 'literal regrade'): d.summarize(changed)
            changed = copy.deepcopy(rows); changed[0]['whitespace_literal_match'] = False
            with self.assertRaisesRegex(ValueError, 'literal regrade'): d.summarize(changed)
            changed = copy.deepcopy(rows); changed[0]['answer'] = '2\n'; changed[0]['exact_literal_match'] = False
            secondary = d.summarize(changed)
            self.assertEqual(secondary['total']['exact_literal_match'], 383)
            self.assertEqual(secondary['total']['whitespace_literal_match'], 384)
            changed = copy.deepcopy(rows); changed[0]['request']['case']['oracle'] = '999'
            with self.assertRaises(ValueError): d.summarize(changed)
            for field, value in (('prompt_ids', [2]), ('generated_ids', [2, 4]), ('mtp', True), ('precision', 'BF16'), ('actual_history', True)):
                changed = copy.deepcopy(rows[0]); changed['generation'][field] = value
                with self.assertRaises((ValueError, KeyError)): d.validate_generation(changed, fixture.tok)
            changed = copy.deepcopy(rows[0]); changed['input']['text'] += ' gold target injection'
            with self.assertRaises(ValueError): d.validate_generation(changed, fixture.tok)

    def test_previous_outputs_are_preserved_and_low_remaining_or_bad_pgid_fail_before_runtime(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_admission_') as temporary:
            root = Path(temporary); fixture = Fixture(root)
            with fixture.patches(), patch.object(d, 'authority', return_value=599), redirect_stdout(io.StringIO()):
                self.assertEqual(d.worker(self.args(), root), 8)
            self.assertEqual(fixture.loads, [])
            old = (root / d.activity_path('evaluate')).read_bytes()
            with fixture.patches(), self.assertRaises(FileExistsError): d.worker(self.args(), root)
            self.assertEqual((root / d.activity_path('evaluate')).read_bytes(), old)
        with tempfile.TemporaryDirectory(prefix='prompt_access_pgid_') as temporary:
            root = Path(temporary); fixture = Fixture(root)
            with fixture.patches(), patch.object(d.os, 'getpgrp', return_value=124), redirect_stdout(io.StringIO()):
                self.assertEqual(d.worker(self.args(), root), 8)
            self.assertEqual(fixture.loads, [])

    def test_closed_activity_rejects_nonfinite_cap_pgid_and_original_deadline(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_activity_') as temporary:
            root = Path(temporary); fixture, code = self.run_fixture(root); self.assertEqual(code, 0)
            original = d.read_json(d.activity_path('evaluate'), root)
            for key, value in (('seconds', float('nan')), ('seconds', 631), ('max_wall_sec', 601), ('pgid', 124), ('utc_seconds', 9)):
                changed = copy.deepcopy(original); changed[key] = value
                (root / d.activity_path('evaluate')).write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaises(ValueError): d.closed('evaluate', fixture.info, root)
            changed = copy.deepcopy(original); changed['ended_at'] = '2026-10-21T07:40:01+00:00'
            (root / d.activity_path('evaluate')).write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaises(ValueError): d.closed('evaluate', fixture.info, root)

    def test_keyboard_interrupt_closes_130_activity_without_a_success_report(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_interrupt_') as temporary:
            root = Path(temporary); fixture = Fixture(root)
            with fixture.patches(), patch.object(d, 'evaluate', side_effect=KeyboardInterrupt):
                self.assertEqual(d.worker(self.args(), root), 130)
            self.assertFalse((root / d.report_path('evaluate')).exists())
            activity = d.read_json(d.activity_path('evaluate'), root)
            self.assertFalse(activity['complete']); self.assertEqual(activity['returncode'], 130)

    def test_missing_final_body_verification_or_different_core_cannot_pass_readback(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_body_') as temporary:
            root = Path(temporary); fixture, code = self.run_fixture(root); self.assertEqual(code, 0)
            report = d.read_json(d.report_path('evaluate'), root); report['sessions'][-1]['session_exit_verified'] = False
            (root / d.report_path('evaluate')).write_text(json.dumps(report), encoding='utf-8'); self.update_report_hash(root, 'evaluate')
            with fixture.patches(), self.assertRaisesRegex(ValueError, 'successful final UI context exit'): d.readback(fixture.info, root)
            report['sessions'][-1]['session_exit_verified'] = True; report['sessions'][-1]['core_after'] = 'B' * 64
            (root / d.report_path('evaluate')).write_text(json.dumps(report), encoding='utf-8'); self.update_report_hash(root, 'evaluate')
            with fixture.patches(), self.assertRaises(ValueError): d.readback(fixture.info, root)


class EmitFixtureTests(unittest.TestCase):
    def test_chat_uses_ui_emit_and_raw_qa_uses_same_capture_forward_boundary(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_emit_') as temporary:
            fixture = Fixture(Path(temporary)); case = d.cases()[0]; binding = fixture.info['bindings'][d.MODEL_NAMES[0]]
            active = dict(root=temporary, tokenizer=fixture.tok, cfg=SimpleNamespace(max_seq_len=1024),
                route=SimpleNamespace(assert_active=lambda: None), model='MODEL_FIXTURE', torch=SimpleNamespace(no_grad=noop))
            def chat_emit(a, question, max_new, history):
                self.assertIs(a, active); self.assertEqual(max_new, 64); self.assertEqual(history, ())
                answer, generation, _ = fixture.emit(active, case, 'chat_bare'); return answer, generation
            with patch.object(d.ui, 'emit', side_effect=chat_emit) as emit:
                answer, generation, rendered = d.emit_request(active, case, 'chat_bare')
                self.assertEqual(answer, '2'); emit.assert_called_once(); self.assertEqual(rendered['user_text'], case['question'])
            class Capture:
                def __init__(self, tok): self.decoded_ids = None
            def sample(forward, cfg, capture, prompt, **options):
                self.assertEqual(forward, ('MODEL_FIXTURE', 'fp32_math')); self.assertNotIn('<|', prompt)
                self.assertEqual(options, dict(max_new=64, temperature=0., top_k=1, device='cuda', use_cache=True,
                    logits_last_only=True, return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]]))
                capture.decoded_ids = fixture.tok.encode(prompt).ids + fixture.tok.encode('2').ids + [4]
                return '', dict(finish_reason='STOP_SEQUENCE', generated_tokens=2, max_new=64, eos_token_available=True,
                    stop_at_eos_requested=True, stop_at_eos_effective=True, stop_token_sequences=[[4]], matched_stop_sequence=[4])
            with patch.object(d.ui, 'generation_tools', return_value=(sample, Capture, lambda model, policy: (model, policy))):
                answer, generation, rendered = d.emit_request(active, case, 'raw_qa')
                row = dict(request=dict(model=d.MODEL_NAMES[0], case=case, format='raw_qa'), input=rendered, answer=answer, generation=generation)
                d.validate_generation(row, fixture.tok); self.assertEqual(answer, '2')
            active['cfg'].max_seq_len = 20
            with patch.object(d.ui, 'emit', side_effect=AssertionError('must refuse before generation')):
                with self.assertRaisesRegex(ValueError, 'never truncate'): d.emit_request(active, case, 'chat_bare')

    def test_eos_and_max64_are_preserved_separately_and_internal_eos_rejected(self):
        with tempfile.TemporaryDirectory(prefix='prompt_access_terminals_') as temporary:
            fixture = Fixture(Path(temporary)); case = d.cases()[0]
            active = dict(tokenizer=fixture.tok); answer, generation, rendered = fixture.emit(active, case, 'raw_qa')
            row = dict(request=dict(model=d.MODEL_NAMES[0], case=case, format='raw_qa'), input=rendered, answer=answer, generation=generation)
            generation.update(finish_reason='EOS', generated_ids=fixture.tok.encode('2').ids + [2], terminal_ids=[2], matched_stop_sequence=None)
            d.validate_generation(row, fixture.tok)
            generation.update(finish_reason='MAX_NEW', generated_ids=fixture.tok.encode('2' * 64).ids, generated_tokens=64,
                content_tokens=64, terminal_ids=[]); row['answer'] = '2' * 64
            d.validate_generation(row, fixture.tok); self.assertFalse(d.score(case, row['answer']))
            generation['generated_ids'][2] = 2
            with self.assertRaises(ValueError): d.validate_generation(row, fixture.tok)


if __name__ == '__main__': unittest.main()
