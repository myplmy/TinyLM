"""Pure stdlib/small in-memory fixtures. No tokenizer/model/assets/GPU import."""
from __future__ import annotations

import ast
import builtins
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p106b_verified_trace_data as d
IMPORT_BASELINE = set(sys.modules)
from scripts import diag_p106b_verified_trace_recovery as driver


def addition(a=23, b=19): return dict(family='addition', a=a, b=b)
def lookup(asked='A'): return dict(family='lookup', facts={'A': 0, 'B': 7}, asked=asked)
def update(asked='A'): return dict(family='update', facts={'A': 0, 'B': 7}, asked=asked, update=dict(subject='A', value=1))


class RootTests(unittest.TestCase):
    def test_addition_exchange_and_render_views_share_root(self):
        root = d.canonical_root(addition())
        self.assertEqual(root, d.canonical_root(addition(19, 23)))
        for lang in ('ko', 'en'):
            for view in range(4):
                self.assertEqual(d.render_row(addition(), lang, 'direct', 'train', view)['meta']['root'], root)

    def test_names_fact_order_language_and_asked_subject_not_split_units(self):
        original = lookup(); variant = dict(family='lookup', facts={'RenamedB': 7, 'RenamedA': 0}, asked='RenamedB')
        root = d.canonical_root(original)
        self.assertEqual(root, d.canonical_root(variant))
        self.assertEqual(root, d.canonical_root(lookup('B')))
        self.assertEqual(d.split_for_root(root), d.split_for_root(d.canonical_root(variant)))

    def test_update_operation_is_part_of_root_but_asked_subject_is_not(self):
        root = d.canonical_root(update())
        self.assertEqual(root, d.canonical_root(update('B')))
        other = update(); other['update']['value'] = 2
        self.assertNotEqual(root, d.canonical_root(other))
        other = update(); other['update']['subject'] = 'B'
        self.assertNotEqual(root, d.canonical_root(other))
        renamed = dict(family='update', facts={'Y': 7, 'X': 0}, asked='Y', update=dict(subject='X', value=1))
        self.assertEqual(root, d.canonical_root(renamed))

    def test_reservations_preserve_entire_fact_roots(self):
        for a, b in ((1, 1), (2, 2), *d.CANARY_PAIRS):
            self.assertTrue(d.is_reserved(addition(a, b))); self.assertTrue(d.is_reserved(addition(b, a)))
        self.assertFalse(d.is_reserved(addition(0, 1)))
        self.assertFalse(d.is_reserved(addition(1, 9)))
        for family in ('lookup', 'update'):
            task = dict(family=family, facts={'Y': 5, 'X': 3}, asked='Y')
            if family == 'update': task['update'] = dict(subject='X', value=8)
            self.assertTrue(d.is_reserved(task))

    def test_user_question_source_literal_and_canary_formula_match_owner_code(self):
        tree = ast.parse((ROOT / 'scripts/diag_p106b_question_transfer.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'evaluation_cases')
        assignment = next(n for n in ast.walk(function) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'questions' for t in n.targets))
        self.assertEqual(ast.literal_eval(assignment.value), d.USER6)
        original = next(n for n in ast.walk(function) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Tuple) and [getattr(v, 'id', None) for v in t.elts] == ['a', 'b'] for t in n.targets))
        expected = ast.parse('a,b=i+2,(i*7+3)%17+1').body[0]
        self.assertEqual(ast.dump(original, include_attributes=False), ast.dump(expected, include_attributes=False))


class StepTests(unittest.TestCase):
    def test_digit_carry_chain_and_final_assembly(self):
        for a, b in ((0, 1), (9, 1), (23, 19), (99, 99), (0, 0), (10, 90)):
            task = addition(a, b); steps = d.build_steps(task)
            self.assertEqual(d.validate_steps(task, steps), a + b)
            self.assertEqual(d.validate_steps(task, d.parse_steps([d.step_text(s) for s in steps])), a + b)

    def test_every_digit_field_is_checked_against_original_problem(self):
        task = addition(); steps = d.build_steps(task)
        for key in ('position', 'a', 'b', 'carry_in', 'total', 'digit', 'carry_out'):
            broken = copy.deepcopy(steps); broken[0][key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError): d.validate_steps(task, broken)
        with self.assertRaises(ValueError): d.validate_steps(task, steps[::-1])
        with self.assertRaises(ValueError): d.validate_steps(task, steps[:-1])

    def test_query_update_and_selection_are_independently_checked(self):
        for task in (lookup(), lookup('B'), update(), update('B')):
            steps = d.build_steps(task)
            self.assertEqual(d.validate_steps(task, steps), d.truth(task))
            bad = copy.deepcopy(steps); bad[-1]['value'] += 1
            with self.assertRaises(ValueError): d.validate_steps(task, bad)
            bad = copy.deepcopy(steps); bad[-2]['subject'] = 'B' if task['asked'] == 'A' else 'A'
            with self.assertRaises(ValueError): d.validate_steps(task, bad)
        steps = d.build_steps(update()); steps[0]['subject'] = 'B'
        with self.assertRaises(ValueError): d.validate_steps(update(), steps)

    def test_wrong_trace_with_right_answer_and_right_trace_with_wrong_answer(self):
        row = d.render_row(addition(), 'en', 'trace', 'test')
        correct = row['messages'][-1]['content']
        wrong_final = correct.rsplit('Answer:', 1)[0] + 'Answer: 41'
        score = d.score_response(addition(), wrong_final, 'en', 'trace')
        self.assertFalse(score['final_correct']); self.assertTrue(score['trace_valid']); self.assertFalse(score['trace_final_agree'])
        wrong_trace = correct.replace('d=2', 'd=3', 1)
        score = d.score_response(addition(), wrong_trace, 'en', 'trace')
        self.assertTrue(score['final_correct']); self.assertFalse(score['trace_valid'])

    def test_input_and_step_domains_reject_bool_float_unknown_fields(self):
        for bad in (dict(family='addition', a=True, b=1), dict(family='addition', a=1., b=2),
                    dict(family='addition', a=-1, b=2), dict(family='addition', a=100, b=2)):
            with self.assertRaises(ValueError): d.canonical_root(bad)
        bad = lookup(); bad['facts']['B'] = 0
        with self.assertRaises(ValueError): d.build_steps(bad)
        bad = update(); bad['update']['value'] = 7
        with self.assertRaises(ValueError): d.build_steps(bad)
        steps = d.build_steps(update()); steps[0]['old'] = False
        with self.assertRaises(ValueError): d.validate_steps(update(), steps)
        steps = d.build_steps(update()); steps[-1]['value'] = True
        with self.assertRaises(ValueError): d.validate_steps(update(), steps)


class ParserTests(unittest.TestCase):
    def test_exact_final_line_and_language(self):
        self.assertTrue(d.parse_final_line('Answer: 42\n', 'en')['ok'])
        self.assertTrue(d.parse_final_line('답: 0', 'ko')['ok'])
        self.assertFalse(d.parse_final_line('Answer: 42', 'ko')['ok'])
        self.assertEqual(d.score_response(addition(), 'Answer: 142', 'en')['final_correct'], False)

    def test_no_substring_duplicate_json_or_special_token_false_positive(self):
        for text in ('42', 'The answer is 42', 'Answer: 42 extra', 'x Answer: 42', 'Answer: 042',
                     'Answer: -42', 'Answer: 42\nAnswer: 42', '답: 42\nAnswer: 42',
                     '{"Answer:":42}', 'Answer: 42<|im_end|>', 'Answer: 42\n<eos>',
                     'Answer: 42\nmore', 'Answer: ４２', 'Answer: 42\x00'):
            with self.subTest(text=text): self.assertFalse(d.parse_final_line(text)['ok'])
        self.assertFalse(d.parse_final_line('Answer: ' + '9' * 5000)['ok'])

    def test_direct_and_trace_use_identical_question_and_final_requirement(self):
        for task in (addition(), lookup(), update()):
            for language in ('ko', 'en'):
                for view in range(4):
                    direct = d.render_row(task, language, 'direct', 'train', view)
                    trace = d.render_row(task, language, 'trace', 'train', view)
                    self.assertEqual(direct['messages'][0], trace['messages'][0])
                    self.assertEqual(direct['messages'][-1]['content'], trace['messages'][-1]['content'].splitlines()[-1])
                    self.assertFalse(trace['meta']['gold_trace_in_prompt'])
                    self.assertNotIn('D0:', trace['messages'][0]['content'])


class CourseTests(unittest.TestCase):
    def small(self, seed=1337):
        counts = {s: {f: 4 if s == 'train' else 2 for f in d.FAMILIES} for s in d.COUNTS}
        return d._build_course(counts, seed, 1000)

    def test_small_course_is_deterministic_split_before_views_and_bilingual(self):
        course = self.small(); other = self.small()
        self.assertEqual(course, other)
        self.assertFalse(course['report']['production_geometry'])
        self.assertEqual(course['report']['train_languages'], {'ko': 6, 'en': 6})
        ids = course['report']['root_ids']
        for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
            self.assertFalse(set(ids[a]) & set(ids[b]))
        for split in d.COUNTS:
            direct, trace = course[split]['direct'], course[split]['trace']
            self.assertEqual(len(direct), len(trace))
            self.assertEqual(len({r['meta']['root'] for r in direct}), len(course['roots'][split]))
            for row in trace:
                m = row['meta']; score = d.score_response(m['task'], row['messages'][-1]['content'], m['language'], 'trace')
                self.assertTrue(score['final_correct']); self.assertTrue(score['trace_valid'])
                self.assertFalse(d.is_reserved(m['task']))

    def test_insufficient_space_never_duplicates_or_shrinks(self):
        with self.assertRaises(d.SupplyExhausted): d.build_course(candidate_limit=1)
        with self.assertRaises(ValueError): d.build_course(candidate_limit=0)

    def test_counterfactual_asked_target_and_order_keep_split_change_correct_value(self):
        for task in (lookup(), update()):
            rows = [d.render_row(task, 'ko', 'trace', 'test', view) for view in (0, 1)]
            self.assertEqual(rows[0]['meta']['root'], rows[1]['meta']['root'])
            self.assertNotEqual(rows[0]['meta']['gold_value'], rows[1]['meta']['gold_value'])
            self.assertEqual(d.split_for_root(rows[0]['meta']['root']), d.split_for_root(rows[1]['meta']['root']))
            self.assertEqual(rows[0]['meta']['presentation']['first_subject'], rows[1]['meta']['presentation']['first_subject'])
            self.assertNotEqual(rows[0]['meta']['presentation']['asked'], rows[1]['meta']['presentation']['asked'])

    def test_name_mapping_swap_and_fixed_shortcut_baseline_counterexamples(self):
        for task in (lookup(), update()):
            rows = [d.render_row(d.oriented_task(task, flip), lang, 'trace', 'test', view)
                    for flip in (False, True) for lang in ('ko', 'en') for view in range(4)]
            self.assertEqual(len(rows), 16)
            self.assertEqual(len({r['meta']['root'] for r in rows}), 1)
            counts = d.shortcut_baselines(rows)[task['family']]
            for name in ('first_current_value', 'maximum_current_value'):
                self.assertEqual(counts[name], dict(correct=8, total=16))
            if task['family'] == 'update':
                self.assertEqual(counts['stale_asked_value'], dict(correct=8, total=16))
                self.assertEqual(counts['last_update_value'], dict(correct=8, total=16))
                self.assertEqual(counts['first_initial_value'], dict(correct=4, total=16))
            else: self.assertEqual(counts['first_initial_value'], dict(correct=8, total=16))

    def test_independent_presentation_counterbalance_by_family_and_language(self):
        counts = {s: {f: 64 if s == 'train' else 4 for f in d.FAMILIES} for s in d.COUNTS}
        course = d._build_course(counts, 1337, 3000)
        for family in ('lookup', 'update'):
            for lang in ('ko', 'en'):
                c = course['report']['presentation_counts']['train'][family + ':' + lang]
                self.assertEqual(c['rows'], 32)
                for prefix in ('raw_A_lt_B=',):
                    self.assertEqual(c[prefix + 'True'], 16); self.assertEqual(c[prefix + 'False'], 16)
                for prefix in ('asked=', 'first_subject='):
                    self.assertEqual(c[prefix + 'A'], 16); self.assertEqual(c[prefix + 'B'], 16)
                for view in range(4): self.assertEqual(c['view=' + str(view)], 8)
                if family == 'update':
                    self.assertEqual(c['target_updated=True'], 16); self.assertEqual(c['target_updated=False'], 16)
                    self.assertEqual(c['answer_changed=True'], 16); self.assertEqual(c['answer_changed=False'], 16)
        self.assertEqual(course['report']['rows_per_policy']['test'], 12 * 8)

    def test_124_through_127_are_not_partial_updates_128_is_full(self):
        for count in range(124, 128):
            with self.subTest(count=count), self.assertRaises(ValueError): d.batch_groups(range(count))
        micros = d.batch_groups(range(128))
        self.assertEqual([len(m) for m in micros], [8] * 16)
        with self.assertRaises(ValueError): d.batch_groups([0] * 128)
        with self.assertRaises(ValueError): d.batch_groups(range(129))

    def test_fixed_production_four_pass_schedule_is_exact128_updates(self):
        schedule = d.training_schedule()
        self.assertEqual(len(schedule), 128)
        self.assertEqual([g['update'] for g in schedule], list(range(1, 129)))
        for epoch in range(1, 5):
            groups = [g for g in schedule if g['epoch'] == epoch]
            rows = [i for g in groups for micro in g['micros'] for i in micro]
            self.assertEqual(len(groups), 32); self.assertEqual(sorted(rows), list(range(4096)))
        self.assertEqual(schedule, d.training_schedule())
        for count in (124, 127, 129, 4095):
            with self.assertRaises(ValueError): d.training_schedule(count)


class DriverFixtureTests(unittest.TestCase):
    def activity(self, mode='cost', arm='direct', endpoint=None):
        invocation = dict(mode=mode, arm=arm, endpoint=endpoint, max_wall_sec=driver.CAPS[mode])
        begin = driver.boundary(mode) - timedelta(seconds=driver.CAPS[mode] + 100)
        key = driver.phase_key(mode, arm, endpoint); identity = {'fixture': True}
        value = dict(info=identity, key=key, mode=mode, arm=arm, endpoint=endpoint, complete=True,
            returncode=0, error_type=None, started_at=begin.isoformat(), ended_at=(begin + timedelta(seconds=20)).isoformat(),
            seconds=17., utc_seconds=20., worker_pid=123, worker_pgid=123, max_wall_sec=driver.CAPS[mode],
            admission=dict(requested_cap=driver.CAPS[mode], utc_remaining=driver.CAPS[mode] + 100,
                           family_remaining=10000))
        return value, key, identity, invocation

    def wire(self):
        record = dict(x=[3, 9, 10], y=[-100, 10, 4], segments=[0, 1, 1])
        counts = driver.record_counts(SimpleNamespace(**record))
        return dict(record=record, record_sha256=d.sha(record), counts=counts)

    def event_cases(self):
        cases = []; events = []
        for task in (addition(), lookup(), update()):
            for language in ('ko', 'en'):
                for view in range(4):
                    row = d.render_row(task, language, 'trace', 'test', view)
                    case = dict(lane='test', row=row, prompt_sha256='P', prompt_ids_sha256='I', prompt_tokens=7)
                    answer = row['messages'][-1]['content']
                    cases.append(case); events.append(dict(index=len(events), lane='test', case_sha256=d.sha(case), answer=answer,
                        question=row['messages'][0]['content'],
                        score=d.score_response(row['meta']['task'], answer, language),
                        generation=dict(finish_reason='STOP_SEQUENCE', generated_tokens=8, gold_trace_in_prompt=False)))
        return events, cases

    def generation(self):
        case = dict(prompt_sha256='P', prompt_ids_sha256='I', prompt_tokens=7)
        generation = dict(generated_ids=[8, 9, 4], generated_tokens=3, finish_reason='STOP_SEQUENCE', terminal_ids=[4],
            matched_stop_sequence=[4], stop_token_sequences=[[4]], max_new=128, eos_token_available=True,
            stop_at_eos_requested=True, stop_at_eos_effective=True, precision='FP32_MATH', tf32=False,
            mtp=False, gold_trace_in_prompt=False, gold_history_used=False, **case)
        return dict(answer='Answer: 42', generation=generation), case

    def test_driver_import_and_false_gate_never_import_torch_tokenizer_or_model(self):
        with patch.object(driver, 'IMPLEMENTATION_READY', False), \
                patch.object(driver, 'info', side_effect=AssertionError('metadata reached while closed')):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(driver.main(['--mode', 'prepare', '--check-only']), 8)
        introduced = set(sys.modules) - IMPORT_BASELINE
        self.assertFalse(any(name.startswith(('torch', 'tokenizers', 'tinylm')) for name in introduced))

    def test_guard_precedes_first_project_import(self):
        original = builtins.__import__; seen = []
        def spy(name, *args, **kwargs):
            if name.startswith(('scripts', 'tinylm', 'torch', 'tokenizers')):
                seen.append(name); raise AssertionError('project import before environment boundary')
            return original(name, *args, **kwargs)
        with patch.dict(os.environ, {'TINYLM_DIR': '../bad'}), patch('builtins.__import__', side_effect=spy):
            with self.assertRaisesRegex(ValueError, 'TINYLM_DIR'):
                runpy.run_path(str(ROOT / driver.SCRIPT), run_name='blocked_fixture')
        self.assertEqual(seen, [])

    def test_existing_import_directories_are_stat_only_and_strict(self):
        with tempfile.TemporaryDirectory(prefix='trace_import_fixture_') as temporary:
            root = Path(temporary)
            with patch.dict(os.environ, {'TINYLM_DIR': str(root), 'TINYLM_HF': str(root / 'HF')}):
                with self.assertRaises(FileNotFoundError): driver.import_environment(root)
                for rel in ('HF/hub', 'data_cache', 'runs/ckpt', 'runs/logs'):
                    (root / rel).mkdir(parents=True, exist_ok=True)
                driver.import_environment(root)
                for bad in (str(root / '..' / root.name), './' + str(root), str(root) + '/'):
                    with patch.dict(os.environ, {'TINYLM_DIR': bad}):
                        with self.assertRaises(ValueError): driver.import_environment(root)
                (root / 'HF/hub').rmdir(); (root / 'HF/hub').symlink_to(root / 'data_cache', target_is_directory=True)
                with self.assertRaises(ValueError): driver.import_environment(root)

    def test_helper_entry_import_spies_are_behind_guard(self):
        original = builtins.__import__; seen = []
        def spy(name, *args, **kwargs):
            if name.startswith(('torch', 'tokenizers', 'tinylm', 'scripts.p106b', 'scripts.diag_p106b')):
                seen.append(name); raise AssertionError('helper side effect before guard')
            return original(name, *args, **kwargs)
        calls = [lambda: driver.optimizer_groups(None), lambda: driver.dev_ce(None, None, None, []),
                 lambda: driver.native32(None), lambda: driver.emit(None, None, None, None, 'x'),
                 lambda: driver.tokenizer(), lambda: driver.put_rows(driver.CACHE, 'x', []),
                 lambda: driver.get_rows(driver.CACHE, 'x', {}), lambda: driver.execute(None),
                 lambda: driver.train('direct')]
        with patch.dict(os.environ, {'TINYLM_HF': 'HF'}), patch.object(driver, 'prepared', return_value={}), \
                patch.object(driver, 'authority', return_value=10000), patch('builtins.__import__', side_effect=spy):
            for call in calls:
                with self.assertRaisesRegex(ValueError, 'TINYLM_HF'): call()
            with patch.object(driver, 'parent_reference', return_value={}):
                with self.assertRaisesRegex(ValueError, 'TINYLM_HF'):
                    with driver.loaded(): pass
        self.assertEqual(seen, [])

    def test_raw_ancestor_symlink_blocks_write_before_mkdir_or_helper_import(self):
        with tempfile.TemporaryDirectory(prefix='trace_path_fixture_') as temporary:
            root = Path(temporary); (root / 'outside').mkdir(); (root / 'runs').mkdir()
            (root / 'runs/eval').symlink_to(root / 'outside', target_is_directory=True)
            raw = root / 'runs/eval' / driver.TAG
            with patch.object(driver, 'ROOT', root), patch.object(driver, 'RAW', raw), \
                    patch.object(driver, 'CACHE', root / 'data_cache' / driver.TAG), patch.object(driver, 'EVIDENCE', root / 'evidence' / driver.TAG):
                with self.assertRaises(ValueError): driver.write(raw / 'x/report.json', {})
                with self.assertRaises(ValueError): driver.put_rows(raw / 'x', 'rows', [])
                with self.assertRaises(ValueError): driver.get_rows(raw / 'x', 'rows', {})
            self.assertEqual(list((root / 'outside').iterdir()), [])

    def test_closed_activity_accepts_independent_perf_and_utc_but_rejects_false_receipts(self):
        value, key, identity, invocation = self.activity()
        driver.validate_activity(value, key, identity, invocation)
        bad_cases = []
        for field, bad in (('seconds', math.nan), ('seconds', math.inf), ('seconds', -1), ('worker_pgid', 124),
                           ('worker_pgid', True), ('max_wall_sec', 901), ('returncode', True), ('complete', False),
                           ('utc_seconds', 17), ('error_type', 'Interrupted')):
            changed = copy.deepcopy(value); changed[field] = bad; bad_cases.append(changed)
        changed = copy.deepcopy(value); changed['ended_at'] = (driver.boundary('cost') + timedelta(seconds=31)).isoformat(); bad_cases.append(changed)
        changed = copy.deepcopy(value); changed['admission']['utc_remaining'] = 899; bad_cases.append(changed)
        for changed in bad_cases:
            with self.assertRaises(ValueError): driver.validate_activity(changed, key, identity, invocation)
        for mode, arm, endpoint in (('prepare', None, None), ('train', 'trace', None), ('evaluate', None, 'parent'), ('readback', None, None)):
            driver.validate_activity(*self.activity(mode, arm, endpoint))

    def test_authority_boundaries_keep_prepare_train_and_reporting_distinct(self):
        for mode in driver.MODES:
            cutoff = driver.boundary(mode)
            self.assertEqual(driver.authority(mode, cutoff - timedelta(seconds=1)), 1)
            with self.assertRaises(driver.Pending): driver.authority(mode, cutoff)
        with self.assertRaises(ValueError): driver.authority('cost', datetime(2026, 10, 21))

    def test_actual_wall_alarm_is_installed_and_prior_timer_restored(self):
        calls = []
        with patch.object(driver.signal, 'getsignal', return_value='old'), patch.object(driver.signal, 'getitimer', return_value=(0., 0.)), \
                patch.object(driver.signal, 'signal', side_effect=lambda *v: calls.append(('handler', v))), \
                patch.object(driver.signal, 'setitimer', side_effect=lambda *v: calls.append(('timer', v))):
            with self.assertRaises(driver.Pending):
                with driver.wall_limit(60):
                    handler = next(v[1][1] for v in calls if v[0] == 'handler'); handler(0, None)
        self.assertEqual([v for kind, v in calls if kind == 'timer'], [(driver.signal.ITIMER_REAL, 60), (driver.signal.ITIMER_REAL, 0., 0.)])

    def test_cap_admission_applies_to_direct_worker_and_all_modes(self):
        with patch.object(driver, 'actual_spent', return_value=0), patch.object(driver, 'authority', return_value=100000):
            for mode in driver.MODES:
                arm = 'direct' if mode in ('cost', 'train') else None; endpoint = 'parent' if mode == 'evaluate' else None
                self.assertEqual(driver.admission(mode, driver.phase_key(mode, arm, endpoint), driver.CAPS[mode], {})['requested_cap'], driver.CAPS[mode])
        with patch.object(driver, 'actual_spent', return_value=0), patch.object(driver, 'authority', return_value=59):
            with self.assertRaises(driver.Pending): driver.admission('train', 'train_direct', 60, {})
        with patch.object(driver, 'actual_spent', return_value=10741), patch.object(driver, 'authority', return_value=100000):
            with self.assertRaises(driver.Pending): driver.admission('evaluate', 'evaluate_parent', 60, {})

    def test_readonly_uses_17h_not_historical_train_gate_and_limits_own_wall(self):
        cutoff = datetime.fromisoformat(driver.LIMITS['authority_end'])
        self.assertEqual(driver.readonly_remaining(cutoff - timedelta(seconds=1)), 1)
        with self.assertRaises(driver.Pending): driver.readonly_remaining(cutoff)
        args = SimpleNamespace(mode='train', arm='direct', endpoint=None, max_wall_sec=1800)
        caps = []
        @contextmanager
        def limit(cap):
            caps.append(cap); yield
        with patch.object(driver, 'readonly_remaining', return_value=37.), patch.object(driver, 'wall_limit', side_effect=limit), \
                patch.object(driver, 'authority', side_effect=AssertionError('historical train gate reapplied')), \
                patch.object(driver, '_verify_readonly', return_value={'status': 'FIXTURE'}):
            with redirect_stdout(io.StringIO()): self.assertEqual(driver.verify_readonly(args), 0)
        self.assertEqual(caps, [37.])
        with patch.object(driver, 'readonly_remaining', side_effect=driver.Pending('expired')), patch.object(driver, '_verify_readonly') as read:
            with self.assertRaises(driver.Pending): driver.verify_readonly(args)
            read.assert_not_called()

    def test_execute_final_receipt_waits_for_readonly_and_uses_remaining_cap(self):
        tree = ast.parse((ROOT / 'scripts/p106b_stage_receipt.py').read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pipeline')
        namespace = dict(json=json, sys=sys)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<pure receipt fixture>', 'exec'), namespace)
        helper = SimpleNamespace(pipeline=namespace['pipeline'])
        args = SimpleNamespace(mode='train', arm='direct', endpoint=None, max_wall_sec=1800)
        output = io.StringIO()
        with patch.dict(sys.modules, {'scripts.p106b_stage_receipt': helper}), patch.object(driver, 'import_environment'), \
                patch.object(driver, 'launch', side_effect=[0, 0, 0, 8]) as launch, patch.object(driver, 'readonly_remaining', return_value=123.5):
            with redirect_stdout(output): self.assertEqual(driver.execute(args), 8)
        self.assertEqual(launch.call_count, 4); self.assertEqual(launch.call_args.args[1], 123.5)
        final = json.loads(output.getvalue().split('[EXPERIMENT_FINAL] ')[-1])
        self.assertEqual(final['status'], 'HOLD'); self.assertEqual(final['phases'][-1]['status'], 'HOLD')
        self.assertNotIn('"status": "COMPLETE"', output.getvalue())

    def test_original_descriptor_bytes_are_not_self_canonicalized(self):
        with tempfile.TemporaryDirectory(prefix='trace_parent_fixture_') as temporary:
            root = Path(temporary); path = root / driver.PARENT_REF; path.parent.mkdir(parents=True)
            path.write_text('{"schema":"changed"}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'immutable root parent descriptor bytes changed'):
                driver.parent_reference(root=root)
        self.assertEqual(len(driver.PARENT_REF_SHA), 64)
        tree = ast.parse((ROOT / driver.SCRIPT).read_text(encoding='utf-8'))
        parent = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parent_reference')
        self.assertIn("parent['source_sha256'] != report.get('code_sha256')", ast.get_source_segment((ROOT / driver.SCRIPT).read_text(encoding='utf-8'), parent))

    def test_f4_requires_independent_descriptor_sha_and_pins_package_import_dependencies(self):
        f4 = dict(schema='TINYLM_VERIFIED_SHORT_TRACE_F4_V1', tag=driver.TAG,
            allowed_new_implementation_files=['scripts/p106b_verified_trace_data.py', driver.SCRIPT, driver.TEST],
            root_owned_metadata=[driver.PARENT_REF], training_contract=dict(parent=driver.PARENT_SHA), execution_gates=driver.LIMITS)
        with patch.object(driver, 'required', return_value=f4), patch.object(driver, 'parent_reference', return_value={'source_sha256': {}}), \
                patch.object(driver, 'digest', return_value='F' * 64):
            with self.assertRaisesRegex(ValueError, 'exact root F4'): driver.info()
            f4['parent_descriptor_sha256'] = driver.PARENT_REF_SHA
            contract = driver.info()
        for name in ('tinylm/train/trainer.py', 'tinylm/train/lr_finder.py', 'tinylm/train/init_utils.py',
                     'tinylm/train/init_mapping.py', 'tinylm/eval/__init__.py', 'tinylm/eval/evaluate.py',
                     'tinylm/eval/compare.py', 'tinylm/training_defaults.py', 'tinylm/audit_io.py'):
            self.assertIn(name, contract['code_sha256'])

    def test_changed_frozen_bytes_rejected_before_encoded_rows(self):
        with patch.object(driver, 'closed', return_value={'frozen_sha256': 'A' * 64}), \
                patch.object(driver, 'digest', return_value='B' * 64), patch.object(driver, 'required') as read:
            with self.assertRaisesRegex(ValueError, 'actual frozen bytes'): driver.prepared()
            read.assert_not_called()

    def test_tokenizer_uses_verified_bytes_and_rejects_changed_bytes_before_import(self):
        raw = b'{"fixture":"same verified bytes"}'; decoded = []
        tok = SimpleNamespace(get_vocab_size=lambda: 32768,
            token_to_id=lambda text: {'<|im_start|>': 3, '<|im_end|>': 4, '<eos>': 2}[text])
        def from_str(text): decoded.append(text); return tok
        module = SimpleNamespace(Tokenizer=SimpleNamespace(from_str=from_str))
        with patch.object(driver, 'import_environment'), patch.object(driver, 'safe', return_value=SimpleNamespace(read_bytes=lambda: raw)), \
                patch.object(driver, 'TOKENIZER_SHA', hashlib.sha256(raw).hexdigest().upper()), patch.dict(sys.modules, {'tokenizers': module}):
            self.assertIs(driver.tokenizer(), tok); self.assertEqual(decoded, [raw.decode('utf-8')])
            with patch.object(driver, 'TOKENIZER_SHA', '0' * 64):
                with self.assertRaisesRegex(ValueError, 'pinned tokenizer bytes changed'): driver.tokenizer()
            self.assertEqual(len(decoded), 1)
            tok.token_to_id = lambda _: 0
            with self.assertRaisesRegex(ValueError, 'terminal map'): driver.tokenizer()

    def test_mock_only_loader_checks_cpu_core_before_cuda_and_cleans_route_on_session_error(self):
        @dataclass
        class FixtureConfig:
            grad_checkpoint: bool = True
            mtp_aux: bool = False
        calls = []; cfg = FixtureConfig()
        payload = dict(cfg=asdict(cfg), step=704, tokenizer_sha256=driver.TOKENIZER_SHA,
            tokenizer_lineage='chat32', quantization_route=dict(mode='float'), experiment={}, model={'fixture': 7})
        parent = dict(header_sha256=d.sha({k: v for k, v in payload.items() if k != 'model'}), cfg_sha256=d.sha(asdict(cfg)))
        class FixtureModel:
            def __init__(self, config): self.cfg = config; self.requires_grad = True; calls.append('CPU_CONSTRUCT_FIXTURE')
            def clear_quant(self): calls.append('clear')
            def set_anneal(self, value): calls.append(('anneal', value))
            def train(self): calls.append('train')
            def eval(self): calls.append('eval')
            def freeze_quant(self): calls.append('freeze')
            def cuda(self): calls.append('MOCK_CUDA_TRANSFER'); return self
        @contextmanager
        def context(*_args): yield
        @contextmanager
        def route(model, mode):
            calls.append(('route_enter', mode))
            try: yield SimpleNamespace(assert_active=lambda: calls.append('active'))
            finally: calls.append(('route_exit', mode))
        torch = ModuleType('torch'); torch.device = context; torch.no_grad = context
        torch.load = lambda *args, **kwargs: copy.deepcopy(payload)
        torch.manual_seed = lambda value: calls.append(('seed', value))
        torch.backends = SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True)), cudnn=SimpleNamespace(allow_tf32=True))
        torch.cuda = SimpleNamespace(empty_cache=lambda: calls.append('MOCK_CACHE_CLEAR'))
        modules = {'torch': torch, 'tinylm': ModuleType('tinylm'),
            'tinylm.config': SimpleNamespace(TMTConfig=FixtureConfig), 'tinylm.model': SimpleNamespace(TiedMLPTransformer=FixtureModel),
            'scripts.p106b_weight_route': SimpleNamespace(weight_route=route,
                load_routed_state=lambda model, state, mode: calls.append(('strict_state_fixture', mode))),
            'scripts.diag_p101a_sft_mtp': SimpleNamespace(state_fingerprint=lambda model: calls.append('fingerprint') or driver.PARENT_CORE)}
        modules['tinylm'].__path__ = []
        with patch.dict(sys.modules, modules), patch.object(driver, 'parent_reference', return_value=parent), \
                patch.object(driver, 'import_environment'), patch.object(driver, 'tokenizer', return_value='TOKENIZER_FIXTURE'), \
                patch.object(driver, 'safe', return_value=Path('/fixture_parent.pt')), patch.object(driver, 'digest', return_value=driver.PARENT_SHA), \
                patch.object(driver, 'authority', return_value=10000), patch.object(driver, 'gpu_idle', side_effect=lambda: calls.append('idle_gate')):
            with self.assertRaisesRegex(RuntimeError, 'fixture session failure'):
                with driver.loaded(training=True) as (_, model, _, tok, _, fingerprint):
                    self.assertEqual(tok, 'TOKENIZER_FIXTURE'); self.assertTrue(model.requires_grad)
                    self.assertEqual(fingerprint.runtime_counts, dict(checkpoint_tensor_loads=1, model_constructions=1, cuda_transfers=1))
                    raise RuntimeError('fixture session failure')
            self.assertLess(calls.index('fingerprint'), calls.index('idle_gate'))
            self.assertLess(calls.index('idle_gate'), calls.index('MOCK_CUDA_TRANSFER'))
            self.assertEqual(calls.count(('route_exit', 'float')), 2)
            self.assertEqual(calls[-1], 'MOCK_CACHE_CLEAR')
            calls.clear(); modules['scripts.diag_p101a_sft_mtp'].state_fingerprint = lambda _: 'BAD_CORE'
            with self.assertRaisesRegex(ValueError, 'strict CPU core mismatch'):
                with driver.loaded(training=True): pass
            self.assertNotIn('idle_gate', calls); self.assertNotIn('MOCK_CUDA_TRANSFER', calls)

    def test_replay_metadata_freezes_first1024_and_rejects_oob_overlap_or_bad_selection(self):
        offsets = [i * 1025 for i in range(5632)]
        def reference(values):
            selection = d.sha(values)
            return dict(binding=dict(native_train_file=driver.NATIVE, native_train_sha256=driver.NATIVE_SHA,
                native_train_offsets=values, native_selection=dict(offsets_sha256=selection))), \
                dict(header=dict(experiment=dict(native_offsets_sha256=selection, reference_sha256='R' * 64)))
        ref, parent = reference(offsets)
        with patch.object(driver, 'required', return_value=ref), patch.object(driver, 'parent_reference', return_value=parent), \
                patch.object(driver, 'digest', return_value='R' * 64):
            result = driver.replay_reference(); self.assertEqual(result['native_train_offsets'], offsets[:1024])
            self.assertEqual(result['offsets_sha256'], d.sha(offsets[:1024])); self.assertEqual(len(result['native_train_offsets']) * 1024, 1048576)
        for bad in ([-1] + offsets[1:], [0, 1024] + offsets[2:], [597995000] + offsets[1:], offsets[:-1]):
            ref, parent = reference(bad)
            with patch.object(driver, 'required', return_value=ref), patch.object(driver, 'parent_reference', return_value=parent), \
                    patch.object(driver, 'digest', return_value='R' * 64):
                with self.assertRaises(ValueError): driver.replay_reference()

    def test_record_mask_counts_and_full_update_denominators_are_measured(self):
        wire = self.wire(); self.assertEqual(wire['counts'], dict(x_tokens=3, assistant_targets=2, content_targets=1, eot_targets=1))
        for field, bad in (('x', [3, True, 9]), ('y', [-100, 10, 2]), ('segments', [1, 1, 1]), ('y', [-100, 4, 4])):
            record = copy.deepcopy(wire['record']); record[field] = bad
            with self.assertRaises(ValueError): driver.record_counts(SimpleNamespace(**record))
        wires = [wire] * 128; micros = d.batch_groups(range(128)); result = driver.group_totals(wires, micros)
        self.assertEqual(result, dict(x_tokens=384, assistant_targets=256, content_targets=128, eot_targets=128, positive_rows=128, native_targets=8192))
        for group in ([list(range(8))] * 16, micros[:-1], [list(range(-8, 0))] + micros[1:]):
            with self.assertRaises(ValueError): driver.group_totals(wires, group)
        wires = [copy.deepcopy(wire) for _ in range(1024)]
        contract = dict(manifests={'dev_direct': {}}, counts={'dev_direct': {k: v * 1024 for k, v in wire['counts'].items()}})
        with patch.object(driver, 'get_rows', return_value=wires):
            driver.corpus(contract, 'dev', 'direct')
            contract['counts']['dev_direct']['content_targets'] += 1
            with self.assertRaisesRegex(ValueError, 'actual encoded corpus totals'): driver.corpus(contract, 'dev', 'direct')

    def test_all_six_frozen_corpora_require_truth_full_split_views_and_same_questions(self):
        counts = {split: {family: 4 if split == 'train' else 2 for family in d.FAMILIES} for split in d.COUNTS}
        course = d._build_course(counts, 1337, 1000); wires = {}
        for split in counts:
            for arm in driver.ARMS:
                lane = []
                for row in course[split][arm]:
                    wire = self.wire(); wire.update(row=copy.deepcopy(row), prompt_tokens=2,
                        prompt_sha256=d.sha(row['messages'][0]['content']), prompt_ids_sha256=d.sha([3, 9]))
                    lane.append(wire)
                wires[(split, arm)] = lane
        stems = {s + '_' + a: {} for s in counts for a in driver.ARMS}
        value = dict(manifests=copy.deepcopy(stems), counts=copy.deepcopy(stems), course_report=course['report'])
        with patch.object(d, 'COUNTS', counts), patch.object(driver, 'corpus', side_effect=lambda _, split, arm: wires[(split, arm)]):
            driver.validate_frozen_corpora(value)
            row = wires[('train', 'direct')][0]['row']; original = row['messages'][1]['content']
            row['messages'][1]['content'] = '답: 999' if row['meta']['language'] == 'ko' else 'Answer: 999'
            with self.assertRaisesRegex(ValueError, 'actual encoded row'): driver.validate_frozen_corpora(value)
            row['messages'][1]['content'] = original
            wires[('test', 'trace')][0]['prompt_sha256'] = 'CHANGED'
            with self.assertRaisesRegex(ValueError, 'prefixes must match'): driver.validate_frozen_corpora(value)
            del value['manifests']['test_trace']
            with self.assertRaisesRegex(ValueError, 'all six original'): driver.validate_frozen_corpora(value)

    def test_both_actual_costs_pending_evals_and_nonfinite_budget_inputs(self):
        costs = {arm: [2.] * 8 for arm in driver.ARMS}
        result = driver.forecast(costs, list(driver.ARMS), list(driver.ENDPOINTS), 100, 10000, 20000)
        self.assertTrue(result['fits']); self.assertEqual(result['evaluation_reserved_seconds'], 3600)
        self.assertEqual(result['record_reserved_seconds'], 600)
        self.assertFalse(driver.forecast(costs, list(driver.ARMS), list(driver.ENDPOINTS), 10700, 10000, 20000)['fits'])
        self.assertFalse(driver.forecast(costs, list(driver.ARMS), list(driver.ENDPOINTS), 0, 1, 20000)['fits'])
        for bad in ([], [1.] * 7, [math.nan] * 8, [0.] * 8, [True] * 8):
            with self.assertRaises(ValueError): driver.forecast(dict(costs, trace=bad), [], [], 0, 10000, 20000)
        with self.assertRaises(ValueError): driver.forecast({'direct': [1.] * 8}, [], [], 0, 10000, 20000)

    def test_optimizer_receipts_reject_double_half_or_uppercase_or_false_counts(self):
        groups = [dict(optimizer='adamw', group=0, lr=5e-5, weight_decay=0., tensors=3, parameters=42),
                  dict(optimizer='muon', group=0, lr=2e-4, weight_decay=0., tensors=7, parameters=84)]
        driver.validate_optimizer_receipts(groups)
        for index, field, value in ((0, 'lr', 2.5e-5), (1, 'lr', 1e-4), (0, 'optimizer', 'AdamW'),
                                    (1, 'group', 1), (0, 'tensors', True), (1, 'parameters', 0), (0, 'weight_decay', .1)):
            changed = copy.deepcopy(groups); changed[index][field] = value
            with self.assertRaises(ValueError): driver.validate_optimizer_receipts(changed)

    def test_training_raw_recount_checks_all_actual_denominators_and_optimizer_receipt(self):
        schedule = d.training_schedule(); counts = dict(x_tokens=384, assistant_targets=256, content_targets=128,
            eot_targets=128, positive_rows=128, native_targets=8192)
        value = dict(schedule=schedule, updates={'direct': [counts] * 128}, native_window_ids_sha256=[d.sha(i) for i in range(1024)])
        events = []
        for index, actual in enumerate(driver.COST_GROUPS):
            events.append(dict(update=index + 1, source_update=actual, epoch=schedule[actual]['epoch'], **counts,
                native_indices=list(range(actual * 8, (actual + 1) * 8)),
                native_window_ids_sha256=d.sha(value['native_window_ids_sha256'][actual * 8:(actual + 1) * 8]),
                assistant_ce=1., content_ce=1., eot_ce=1., native_ce=1., gradient_norm=.5, clipped=False, step_seconds=2.))
        groups = [dict(optimizer='adamw', group=0, lr=5e-5, weight_decay=0., tensors=3, parameters=42),
                  dict(optimizer='muon', group=0, lr=2e-4, weight_decay=0., tensors=7, parameters=84)]
        report = dict(status='COST8_COMPLETE', cost=True, arm='direct', actual_updates=8, parent_checkpoint_sha256=driver.PARENT_SHA,
            initial_core_sha256=driver.PARENT_CORE, final_core_sha256='C' * 64, frozen_sha256='F' * 64, actual_optimizer_groups=groups,
            runtime_counts=dict(checkpoint_tensor_loads=1, model_constructions=1, cuda_transfers=1),
            fresh_optimizer=True, optimizer_saved=False, optimizer_contract=dict(adam_betas=[.9, .95], adam_eps=1e-8,
                muon_scale_mode='rms', muon_group_scale_modes=['rms']), sft_padded_slots=8 * 128 * 128, checkpoint_writes=0,
            raw_manifest={}, step_seconds=[2.] * 8, grad_max=.5, clip_events=0, optimizer_factory_calls=1,
            whole_seconds=20., peak_allocated_mib=10., peak_reserved_mib=12.,
            optimizer_reset_between_updates=False, totals={key: val * 8 for key, val in counts.items()})
        with patch.object(driver, 'closed', return_value=report), patch.object(driver, 'prepared', return_value=value), \
                patch.object(driver, 'get_rows', return_value=events), patch.object(driver, 'digest', return_value='F' * 64):
            self.assertIs(driver.read_training('direct', cost=True), report)
            for field in ('assistant_targets', 'content_targets', 'eot_targets', 'native_targets', 'positive_rows', 'x_tokens'):
                events[0][field] += 1
                with self.assertRaises(ValueError): driver.read_training('direct', cost=True)
                events[0][field] -= 1
            report['totals']['content_targets'] += 1
            with self.assertRaisesRegex(ValueError, 'full raw sum'): driver.read_training('direct', cost=True)

    def test_summary_reaggregates_text_roots_presentations_and_counterfactual_pairs(self):
        events, cases = self.event_cases(); summary = driver.evaluation_summary(events, cases)
        self.assertEqual(summary['lanes']['test']['rows'], 24); self.assertEqual(summary['lanes']['test']['final_correct'], 24)
        self.assertEqual(len(summary['roots']), 3)
        for family in d.FAMILIES:
            group = summary['counterfactual'][family]; self.assertEqual(group['all_four_final_correct'], 2)
            kind = 'operand_order' if family == 'addition' else 'asked_target'
            self.assertEqual(group[kind + '_pairs'], 4); self.assertEqual(group[kind + '_both_final_correct'], 4)
        events[0]['answer'] = events[0]['answer'].rsplit('답:', 1)[0] + '답: 41'
        events[0]['score'] = d.score_response(cases[0]['row']['meta']['task'], events[0]['answer'], 'ko')
        changed = driver.evaluation_summary(events, cases)
        self.assertEqual(changed['lanes']['test']['final_correct'], 23)
        self.assertEqual(changed['lanes']['test']['valid_trace_wrong_final'], 1)
        events[1]['answer'] = events[1]['answer'].replace('d=2', 'd=3', 1)
        events[1]['score'] = d.score_response(cases[1]['row']['meta']['task'], events[1]['answer'], 'ko')
        changed = driver.evaluation_summary(events, cases)
        self.assertEqual(changed['lanes']['test']['right_final_invalid_trace'], 1)
        events[0]['score'] = copy.deepcopy(events[1]['score'])
        with self.assertRaisesRegex(ValueError, 'independent text'): driver.evaluation_summary(events, cases)

    def test_generated_ids_terminal_and_pinned_decode_are_verified(self):
        event, case = self.generation(); tok = SimpleNamespace(decode=lambda ids, **kw: 'Answer: 42' if ids == [8, 9] else 'wrong')
        driver.validate_generation(event, case, tok)
        for field, bad in (('generated_ids', [8, 2, 4]), ('generated_ids', [8, 9, True]), ('generated_tokens', True),
                           ('generated_tokens', 2), ('terminal_ids', []), ('matched_stop_sequence', None),
                           ('gold_history_used', True), ('gold_trace_in_prompt', True), ('tf32', True), ('precision', 'BF16')):
            changed = copy.deepcopy(event); changed['generation'][field] = bad
            with self.assertRaises(ValueError): driver.validate_generation(changed, case, tok)
        event['answer'] = 'Answer: 142'
        with self.assertRaisesRegex(ValueError, 'pinned-tokenizer decoding'): driver.validate_generation(event, case, tok)
        event, case = self.generation(); event['generation'].update(generated_ids=[8, 9, 2], terminal_ids=[2], finish_reason='EOS', matched_stop_sequence=None)
        driver.validate_generation(event, case, tok)
        event['generation'].update(generated_ids=[8] * 128, generated_tokens=128, terminal_ids=[], finish_reason='MAX_NEW')
        event['answer'] = 'wrong'; driver.validate_generation(event, case, tok)

    def test_read_evaluation_rejects_tampered_summary_from_raw_recount(self):
        events, cases = self.event_cases()
        events = (events * 45)[:1062]; cases = (cases * 45)[:1062]
        for index, event in enumerate(events):
            events[index] = dict(event, index=index)
        report = dict(status='EVALUATION_COMPLETE', endpoint='parent', cases_sha256=d.sha(cases), raw_manifest={},
            runtime_counts=dict(checkpoint_tensor_loads=1, model_constructions=1, cuda_transfers=1),
            core_before=driver.PARENT_CORE, core_after=driver.PARENT_CORE, weights_changed=False, checkpoint_writes=0,
            counts=dict(test=1024, train_observation=32, user=6, total=1062), user_semantic_truth='HUMAN_REVIEW_REQUIRED', summary={'tampered': True})
        with patch.object(driver, 'closed', return_value=report), patch.object(driver, 'prepared', return_value={}), \
                patch.object(driver, 'evaluation_cases', return_value=cases), patch.object(driver, 'get_rows', return_value=events), \
                patch.object(driver, 'tokenizer', return_value=None), patch.object(driver, 'validate_generation'), \
                patch.object(driver, 'evaluation_summary', return_value={'actual_raw': 1062}):
            with self.assertRaisesRegex(ValueError, 'report summary differs'): driver.read_evaluation('parent')

    def test_worker_sigterm_is_130_and_closes_failed_activity_without_success_report(self):
        args = SimpleNamespace(mode='prepare', arm=None, endpoint=None, max_wall_sec=60)
        writes = []; identity = {'fixture': True}
        with patch.object(driver, 'info', return_value=identity), patch.object(driver.Path, 'exists', return_value=False), \
                patch.object(driver.os, 'getpid', return_value=123), patch.object(driver.os, 'getpgrp', return_value=123), \
                patch.object(driver, 'admission', return_value={}), patch.object(driver, 'prepare', side_effect=KeyboardInterrupt), \
                patch.object(driver.Path, 'is_file', return_value=False), \
                patch.object(driver, 'digest', side_effect=AssertionError('isolated fixture must not hash actual report')), \
                patch.object(driver, 'write', side_effect=lambda path, value: writes.append((path, value))):
            with redirect_stdout(io.StringIO()): self.assertEqual(driver.worker(args), 130)
        self.assertEqual(len(writes), 1); self.assertFalse(writes[0][1]['complete'])
        self.assertEqual(writes[0][1]['returncode'], 130); self.assertIsNone(writes[0][1]['result_sha256'])

    def test_static_check_only_has_no_model_or_helper_import(self):
        with patch.object(driver, 'IMPLEMENTATION_READY', True), patch.object(driver, 'info', return_value={'code_sha256': {}}), \
                patch.object(driver, 'worker', side_effect=AssertionError('worker reached')):
            output = io.StringIO()
            with redirect_stdout(output): self.assertEqual(driver.main(['--mode', 'prepare', '--check-only']), 0)
            self.assertIn('"torch_imports": 0', output.getvalue())
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertEqual(driver.main(['--mode', 'prepare', '--worker', '--check-only']), 9)


    def test_recovery_keeps_original_numerical_and_all_runtime_function_bodies(self):
        original = ast.parse((ROOT / 'scripts/diag_p106b_verified_trace.py').read_text())
        recovered = ast.parse((ROOT / driver.SCRIPT).read_text())
        left = {n.name: ast.dump(n, include_attributes=False) for n in original.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        right = {n.name: ast.dump(n, include_attributes=False) for n in recovered.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        # Only the regression module literal in execute changes namespace.
        right['execute'] = right['execute'].replace('scripts.test_p106b_verified_trace_recovery', 'scripts.test_p106b_verified_trace')
        self.assertEqual(left, right)
        self.assertEqual(driver.TAG, 'p106b_verified_trace_recovery_v2_s1337')

    def test_sigterm_fixture_stays_isolated_from_an_existing_namespace_path(self):
        with patch.object(driver, 'report_path', return_value=ROOT / 'test_result' / 'must_not_be_read.json'):
            self.test_worker_sigterm_is_130_and_closes_failed_activity_without_success_report()


if __name__ == '__main__': unittest.main()
