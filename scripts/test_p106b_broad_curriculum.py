"""Small CPU/temp controller fixtures; never read actual corpora or checkpoints."""
from __future__ import annotations

from collections import Counter
from contextlib import redirect_stdout, nullcontext
import copy
from datetime import datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_broad_curriculum as d
from tinylm.chat.canonical import normalize
from tinylm.train.mtp_sft import Record


class Tokens:
    def encode(self, text):
        return SimpleNamespace(ids=[10 + ord(c) % 1000 for c in text])
    def decode(self, ids, skip_special_tokens=False):
        return ''.join({5: 'MODEL_A', 6: 'MODEL_B', 7: 'MODEL_C'}.get(i, '?') for i in ids)
    def token_to_id(self, value):
        return {'<pad>': 0, '<eos>': 2, '<|im_end|>': 4}[value]


def conversation(index=0, language='en', turns=3):
    messages = []
    for turn in range(turns):
        messages.extend([dict(role='user', content=f'Original question {index} turn {turn}.'),
                         dict(role='assistant', content=f'SOURCE_GOLD_{index}_{turn}')])
    return normalize(dict(messages=messages, meta=dict(language=language, source='fixture',
        source_id=str(index), source_revision='fixture', source_license='FIXTURE_ONLY')))


def dialogue_case(index=0, language='en', turns=3):
    row = conversation(index, language, turns)
    return dict(id=d.sha(['case', index, language]), language=language, source_index=index,
        source_meta=row['meta'], source_messages=row['messages'], turns=d.dialogue_turns(row))


def emitter(tok, captured=None):
    def emit(messages):
        if captured is not None:
            captured.append(copy.deepcopy(messages))
        prompt = d.serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
        answer = 'MODEL_A'
        generation = dict(max_new=128, precision='FP32_MATH', use_cache=True, temperature=0., top_k=1,
            mtp=False, candidate_answers_supplied=False, stop_token_sequences=[[4]],
            prompt_sha256=d.sha(prompt), prompt_ids_sha256=d.sha(tok.encode(prompt).ids),
            prompt_tokens=len(tok.encode(prompt).ids), generated_ids=[5, 4], generated_tokens=2,
            generated_ids_sha256=d.sha([5, 4]), terminal_ids=[4], finish_reason='STOP_SEQUENCE',
            matched_stop_sequence=[4], content_ids_sha256=d.sha([5]),
            body_utf8_sha256=hashlib.sha256(answer.encode()).hexdigest().upper(), terminal_only_removed=True)
        return answer, generation
    return emit


def dialogue_fixture():
    tok, lineage = Tokens(), dict(endpoint='fixture')
    cases = [dialogue_case(i, 'ko' if i < 8 else 'en') for i in range(16)]
    with patch.object(d, 'authority', return_value=10000):
        events = [dict(d.run_dialogue(case, emitter(tok), tok), lineage=lineage) for case in cases]
    return tok, lineage, cases, events


class ControllerTests(unittest.TestCase):
    def test_deadlines_and_naive_clock(self):
        self.assertEqual(d.authority(training=True, now=d.TRAIN_STOP - timedelta(seconds=1)), 1.)
        self.assertEqual(d.authority(now=d.END - timedelta(seconds=1)), 1.)
        for kwargs in (dict(training=True, now=d.TRAIN_STOP), dict(now=d.END)):
            with self.assertRaises(d.Pending): d.authority(**kwargs)
        with self.assertRaises(ValueError): d.authority(now=datetime(2026, 10, 19))

    def test_only_evaluate_may_omit_arm_for_exact_parent(self):
        self.assertEqual(d.activity_key('evaluate', None), 'evaluate_parent')
        self.assertEqual(d.phase_commands('evaluate', None, 600)[2][1][-2:], ['--max-wall-sec', '600'])
        for mode, arm in (('train', None), ('cost', None), ('prepare', 'mixed'),
                          ('preflight', 'staged'), ('readback', 'mixed'), ('evaluate', 'other')):
            with self.subTest(mode=mode, arm=arm), self.assertRaises(ValueError):
                d.phase_commands(mode, arm, 600)

    def test_bounded_wall_and_exact_pipeline(self):
        for value in (True, 59, 7201, 600.):
            with self.assertRaises(ValueError): d.phase_commands('prepare', None, value)
        phases = d.phase_commands('prepare', None, 600)
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p106b_broad_course', phases[0][1])
        self.assertIn('scripts.test_p106b_broad_curriculum', phases[0][1])
        self.assertEqual(phases[1][1][phases[1][1].index('--mode') + 1], 'source')
        trained = d.phase_commands('train', 'mixed', 600)
        self.assertEqual(trained[1][1][trained[1][1].index('--mode') + 1], 'preflight')

    def test_check_only_reads_no_sources_and_launches_nothing(self):
        with patch.object(d, 'info', return_value={'code_only': True}), patch.object(d, 'worker') as worker, \
             patch.object(d, 'launch') as launch, patch.object(d, 'source_pins') as sources, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'evaluate', '--check-only']), 0)
        worker.assert_not_called(); launch.assert_not_called(); sources.assert_not_called()

    def test_failed_preflight_is_hold_not_student_training_failure(self):
        values = iter([0, 8]); calls = []
        def launch(command): calls.append(command); return next(values)
        result = d.pipeline(d.phase_commands('train', 'staged', 600), launch, lambda _: None, experiment='FIXTURE')
        self.assertEqual(result['status'], 'HOLD')
        self.assertFalse(result['main_experiment_invoked'])
        self.assertEqual(len(calls), 2)

    def test_source_unavailable_worker_maps_to8_and_keeps_diagnostic(self):
        diagnosis = dict(status='SOURCE_UNAVAILABLE', eligible_unique_rows=2000)
        with patch.object(d, 'phase_commands', return_value=[]), \
             patch.object(d, 'worker', side_effect=d.builder.SourceUnavailable(diagnosis)), \
             redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(d.main(['--mode', 'prepare', '--worker', '--execute']), 8)
        self.assertIn('SOURCE_UNAVAILABLE8', stdout.getvalue())

    def test_prepare_records_admission_before_any_wire_or_model(self):
        from types import ModuleType
        fake_tokenizers = ModuleType('tokenizers')
        fake_tokenizers.Tokenizer = SimpleNamespace(from_file=lambda _: Tokens())
        old = dict(upstream_course=dict(path='fixture_upstream', sha256='HASH'), manifests={})
        upstream = dict(manifests={key: {'rows': 1} for key in
            ('dev_code', 'dev_fiction', 'dev_role', 'dev_evidence', 'retention_fiction',
             'test_role_style0', 'test_role_style2', 'test_evidence')})
        diagnosis = dict(status='SOURCE_UNAVAILABLE', eligible_unique_rows=2000, requested_general_rows=2048)
        with tempfile.TemporaryDirectory(prefix='broad_admission_') as temporary:
            root = Path(temporary)
            with patch.dict(sys.modules, {'tokenizers': fake_tokenizers}), \
                 patch.object(d, 'CACHE', root / 'cache'), patch.object(d, 'RAW', root / 'raw'), \
                 patch.object(d, 'EVIDENCE', root / 'evidence'), patch.object(d, 'safe', side_effect=Path), \
                 patch.object(d, 'source_pins', return_value={}), patch.object(d, 'authority', return_value=10000), \
                 patch.object(d, 'digest', return_value='HASH'), patch.object(d, 'required', return_value=upstream), \
                 patch.object(d, 'info', return_value={'schema': 'FIXTURE'}), \
                 patch.object(d.grounded, 'read_night_course', return_value=(old, dict(train=[], replay=[], dev=[], test=[]))), \
                 patch.object(d.monitor, 'read_prepared', return_value=({}, None, None)), \
                 patch.object(d.monitor, 'read_rows', return_value=[]), \
                 patch.object(d, '_lines', side_effect=[[{}] * 2996, [{}] * 158]), \
                 patch.object(d.builder, 'inspect_general', return_value=diagnosis), \
                 patch.object(d.builder, 'build_course') as build, patch.object(d, '_put') as wire:
                # The source monitor manifest is a declared fixture, never a real asset.
                with patch.object(d.monitor, 'read_prepared', return_value=({'manifests': {'cases': {}}}, None, None)):
                    with self.assertRaises(d.builder.SourceUnavailable): d.prepare()
            saved = json.loads((root / 'evidence/source_admission.json').read_text())
            self.assertEqual(saved['status'], 'SOURCE_UNAVAILABLE')
            self.assertEqual(saved['admission'], diagnosis)
            self.assertFalse((root / 'cache').exists())
            build.assert_not_called(); wire.assert_not_called()

    def test_cost_plan_covers_lanes_and_warmed_long_general_targets(self):
        rows, groups = [], []
        for i in range(9):
            groups.append([i]); rows.append(dict(lane=('grounded', 'replay', 'general')[i // 3], assistant_targets=i + 1))
        course = SimpleNamespace(rows=rows, groups=groups)
        plan = d.cost_group_ids(course)
        self.assertEqual(len(plan), 8)
        self.assertEqual(len(set(plan)), 8)
        self.assertEqual({rows[groups[i][0]]['lane'] for i in plan}, {'grounded', 'replay', 'general'})
        self.assertEqual(plan[2], 8)
        self.assertIn(7, plan[1:])

    def test_incomplete_cost_activity_cannot_admit_training(self):
        with patch.object(d, 'prepared', return_value={}), \
             patch.object(d, 'completed_activity', side_effect=d.Pending('incomplete')), \
             patch.object(d, 'read_training') as training:
            with self.assertRaises(d.Pending): d.budget()
        training.assert_not_called()

    def test_budget_uses_both_complete_costs_and_actual_spent_time(self):
        with tempfile.TemporaryDirectory(prefix='broad_budget_') as temporary:
            with patch.object(d, 'EVIDENCE', Path(temporary)), patch.object(d, 'prepared', return_value={}), \
                 patch.object(d, 'completed_activity') as activity, \
                 patch.object(d, 'read_training', return_value={'step_seconds': [10.] + [2.] * 7}), \
                 patch.object(d, 'spent_seconds', return_value=60.), patch.object(d, 'authority', return_value=10000.):
                result = d.budget()
        self.assertEqual(activity.call_count, 2)
        self.assertAlmostEqual(result['total_reserved_seconds'], 60 + 2 * (10 + 2 * 351 * 1.35 + 300) + 1800)

    def test_eval_worker_preserves_record_reserve_at_real_deadline(self):
        with tempfile.TemporaryDirectory(prefix='broad_authority_') as temporary:
            with patch.object(d, 'EVIDENCE', Path(temporary)), patch.object(d, 'safe', side_effect=Path), \
                 patch.object(d, 'authority', return_value=1500.), patch.object(d, 'spent_seconds', return_value=0.), \
                 patch.object(d, 'evaluate') as evaluate:
                with self.assertRaises(d.Pending): d.worker('evaluate', None, 1500)
        evaluate.assert_not_called()

    def test_prepared_failure_prevents_parent_loading_or_gpu_gate(self):
        with patch.object(d, 'prepared', side_effect=d.Pending('missing source')), \
             patch.object(d.monitor.base, 'load_parent') as loader, \
             patch('scripts.p106b_gate_runtime.idle_before_gpu') as idle:
            with self.assertRaises(d.Pending): d.train('mixed', cost=True)
        loader.assert_not_called(); idle.assert_not_called()

    def test_new_parent_dialogue_baseline_is_required_before_full_training(self):
        with tempfile.TemporaryDirectory(prefix='broad_baseline_') as temporary:
            with patch.object(d, 'EVIDENCE', Path(temporary)), patch.object(d, 'prepared', return_value={}), \
                 patch.object(d, 'safe', side_effect=Path), \
                 patch.object(d, 'authority', return_value=10000), patch.object(d, 'budget', return_value={}), \
                 patch.object(d, 'completed_activity', side_effect=d.Pending('baseline missing')), \
                 patch.object(d.monitor.base, 'load_parent') as loader:
                with self.assertRaises(d.Pending): d.train('mixed', cost=False)
        loader.assert_not_called()

    def test_process_timeout_only_terminates_own_group(self):
        process = Mock(pid=4321)
        process.wait.side_effect = [subprocess.TimeoutExpired('fixture', 1), 0]
        process.poll.return_value = None
        with patch.object(d.subprocess, 'Popen', return_value=process) as popen, \
             patch.object(d.os, 'getpgid', return_value=4321), patch.object(d.os, 'killpg') as kill:
            self.assertEqual(d.launch(['fixture'], 1), 124)
        kill.assert_called_once_with(4321, signal.SIGTERM)
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertEqual(popen.call_args.kwargs['stdin'], subprocess.DEVNULL)

    def test_checkpoint_selector_is_not_arbitrary_old_parent_route(self):
        for arm in ('parent', '../foreign', None):
            with self.assertRaises(ValueError): d.checkpoint(arm)
        self.assertIn(d.TAG, d.checkpoint('staged').name)

    def test_public_contract_rejects_code_metadata_and_bool_integer_substitution(self):
        frozen = dict(course_report_sha256='COURSE', source_admission={}, monitor_overlap={},
            dialogue_selection={}, monitor_display_ids=['CASE'], monitor_display_selection_sha256='DISPLAY',
            dev_rows=4, dev_targets=8)
        with patch.object(d, 'digest', return_value='FROZEN'), \
             patch.object(d, 'info', return_value=dict(code_sha256={'fixture.py': 'CODE'}, mtp=False)):
            report = d.public_contract(frozen)
            d.validate_public_contract(frozen, report)
            for key, value in (('frozen_sha256', 'WRONG'), ('mtp', 0), ('code_sha256', {'fixture.py': 'WRONG'})):
                changed = copy.deepcopy(report); changed[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.validate_public_contract(frozen, changed)

    def test_complete_activity_is_bound_to_exact_current_report_sha(self):
        with tempfile.TemporaryDirectory(prefix='broad_activity_') as temporary:
            root = Path(temporary); evidence = root / 'evidence'; report_path = evidence / 'cost_mixed/report.json'
            report_path.parent.mkdir(parents=True); report_path.write_text('{"fixture":1}\n')
            report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest().upper()
            activity = dict(schema=d.SCHEMA, tag=d.TAG, key='cost_mixed', mode='cost', arm='mixed',
                complete=True, returncode=0, code_sha256={'fixture.py': 'CODE'}, seconds=1., max_wall_sec=600,
                recorded_at=d.END.isoformat(), report_path='evidence/cost_mixed/report.json', report_sha256=report_sha,
                scope='actual worker wall including full input verification; regression/wrapper excluded')
            with patch.object(d, 'ROOT', root), patch.object(d, 'EVIDENCE', evidence), \
                 patch.object(d, 'safe', side_effect=Path), patch.object(d, 'required', return_value=activity), \
                 patch.object(d, 'info', return_value=dict(code_sha256={'fixture.py': 'CODE'})):
                d.completed_activity('cost', 'mixed')
                report_path.write_text('{"fixture":2}\n')
                with self.assertRaisesRegex(ValueError, 'report SHA'): d.completed_activity('cost', 'mixed')
                activity['complete'] = False
                with self.assertRaises(d.Pending): d.completed_activity('cost', 'mixed')

    def test_pure_source_receipt_check_does_not_require_unfinished_activity(self):
        # The initial prepare can validate this receipt before its worker closes.
        frozen = dict(course_report_sha256='C', source_admission={}, monitor_overlap={}, dialogue_selection={},
                      monitor_display_ids=[], monitor_display_selection_sha256='D', dev_rows=1, dev_targets=2)
        with patch.object(d, 'info', return_value={}), patch.object(d, 'digest', return_value='F'), \
             patch.object(d, 'completed_activity') as activity:
            d.validate_public_contract(frozen, d.public_contract(frozen))
        activity.assert_not_called()


class DialogueTests(unittest.TestCase):
    def test_selection_is_fixed8_each_language_before_model_answers(self):
        rows = [conversation(i, 'ko') for i in range(9)] + [conversation(100 + i, 'en') for i in range(12)]
        before = d.sha(rows)
        first, report = d.select_dialogues(rows, Tokens())
        second, _ = d.select_dialogues(rows, Tokens())
        self.assertEqual(first, second)
        self.assertEqual(Counter(v['language'] for v in first), dict(ko=8, en=8))
        self.assertEqual(before, d.sha(rows))
        self.assertEqual(report['source_indices'], [v['source_index'] for v in first])

    def test_dialogue_shortage_is_source_unavailable(self):
        rows = [conversation(i, 'ko') for i in range(7)] + [conversation(100 + i, 'en') for i in range(9)]
        with self.assertRaises(d.builder.SourceUnavailable) as error: d.select_dialogues(rows, Tokens())
        self.assertEqual(error.exception.report['reason'], 'public_val_dialogue_supply')

    def test_later_prompts_use_model_answers_never_source_gold_history(self):
        case, tok, prompts = dialogue_case(), Tokens(), []
        with patch.object(d, 'authority', return_value=10000):
            event = d.run_dialogue(case, emitter(tok, prompts), tok)
        self.assertEqual(len(prompts), 3)
        self.assertIn('MODEL_A', repr(prompts[1]))
        self.assertNotIn('SOURCE_GOLD', repr(prompts[1]))
        self.assertEqual(event['turns'][0]['source_gold'], 'SOURCE_GOLD_0_0')
        self.assertFalse(event['source_gold_history_used'])

    def test_real_context_overflow_is_explicit_not_silent_turn_drop(self):
        case, tok = dialogue_case(), Tokens()
        case['turns'][1]['additions'][0]['content'][0]['text'] = 'X' * 1000
        with patch.object(d, 'authority', return_value=10000):
            result = d.run_dialogue(case, emitter(tok), tok)
        self.assertEqual([v['status'] for v in result['turns']], ['ACTUAL_MODEL_ANSWER', 'NOT_RUN_CONTEXT_BUDGET'])

    def test_actual_dialogue_receipts_validate_without_semantic_pass(self):
        tok, lineage, cases, events = dialogue_fixture()
        d.validate_dialogues(events, cases, tok, lineage)
        summary = d.dialogue_summary(events)
        self.assertIsNone(summary['semantic_pass'])
        self.assertEqual(summary['languages']['ko']['episodes'], 8)
        self.assertEqual(summary['languages']['en']['actual_answers'], 24)

    def test_gold_history_injection_is_rejected(self):
        tok, lineage, cases, events = dialogue_fixture()
        events[0]['turns'][1]['actual_prompt_messages'][1]['content'][0]['text'] = cases[0]['turns'][0]['source_gold']
        with self.assertRaisesRegex(ValueError, 'source-gold'): d.validate_dialogues(events, cases, tok, lineage)

    def test_missing_turn_and_fake_context_skip_rejected(self):
        tok, lineage, cases, events = dialogue_fixture()
        events[0]['turns'].pop()
        with self.assertRaisesRegex(ValueError, 'unreported'): d.validate_dialogues(events, cases, tok, lineage)
        tok, lineage, cases, events = dialogue_fixture()
        events[0]['turns'] = [dict(events[0]['turns'][0], status='NOT_RUN_CONTEXT_BUDGET')]
        with self.assertRaisesRegex(ValueError, 'shortage'): d.validate_dialogues(events, cases, tok, lineage)

    def test_terminal_flags_and_no_automatic_quality_pass_are_verified(self):
        for mutate in (lambda t: t.update(semantic_correct=True),
                       lambda t: t['generation'].update(use_cache=False),
                       lambda t: t['generation'].update(finish_reason='MAX_NEW'),
                       lambda t: t['generation'].update(generated_ids=[True, 4])):
            tok, lineage, cases, events = dialogue_fixture()
            mutate(events[0]['turns'][0])
            with self.assertRaises(ValueError): d.validate_dialogues(events, cases, tok, lineage)

    def test_old_parent_reuse_is_explicit_and_strictly_bound(self):
        bundle = dict(monitor=[dict(id='fixture')])
        lineage = dict(checkpoint=str(d.monitor.base.PARENT.relative_to(d.ROOT)),
                       checkpoint_sha256=d.monitor.base.PARENT_SHA)
        report = dict(status='ACTUAL_FIRST_ANSWERS_RECORDED', lineage=lineage,
            core_before=d.monitor.base.PARENT_CORE, core_after=d.monitor.base.PARENT_CORE,
            cases_sha256=d.sha(bundle['monitor']), answer_manifest_sha256='HASH', answer_manifest={}, summary={'fixture': 1})
        events = [dict(lineage=dict(tag=d.monitor.TAG, **lineage))]
        with patch.object(d.monitor, 'required', return_value=report), patch.object(d, 'digest', return_value='HASH'), \
             patch.object(d.monitor, 'read_rows', return_value=events), patch.object(d.monitor, 'recount', return_value={'fixture': 1}):
            _, reused = d.reused_parent_monitor(bundle, Tokens())
            self.assertIn('REUSED_EXACT_OLD_PARENT', reused['origin'])
            report['core_before'] = 'wrong'
            with self.assertRaises(ValueError): d.reused_parent_monitor(bundle, Tokens())

    def test_stdout_displays_actual_questions_answers_and_context_skips(self):
        case, tok, notes = dialogue_case(), Tokens(), []
        with patch.object(d, 'authority', return_value=10000):
            event = d.run_dialogue(case, emitter(tok), tok)
        d.show_dialogue(event, case, 'parent', notes.append)
        self.assertEqual(len(notes), 3)
        self.assertTrue(all(line.startswith('[BROAD_DIALOGUE] ') for line in notes))
        display = json.loads(notes[1].split(' ', 1)[1])
        self.assertIn('Original question', repr(display['source_user_additions']))
        self.assertEqual(display['answer'], 'MODEL_A')
        self.assertEqual(display['prior_actual_assistant_answers'], ['MODEL_A'])
        self.assertNotIn('SOURCE_GOLD', notes[1])

    def test_monitor_stdout_sample_is_hash8_plus_all_user6_before_answers(self):
        cases = [dict(id=f'case{i}', lane='coded', language='en', family='arithmetic',
                      messages=[dict(role='user', content='A real displayed question?')]) for i in range(20)]
        cases += [dict(id=f'user{i}', lane='user_seen', language='ko', family='user_seen',
                       messages=[dict(role='user', content='사용자 질문')]) for i in range(6)]
        selected = d.monitor_display_ids(cases)
        self.assertEqual(len(selected), 14)
        self.assertTrue({f'user{i}' for i in range(6)}.issubset(selected))
        self.assertEqual(selected, d.monitor_display_ids(cases))
        notes = []
        event = dict(answer='An actual answer.', generation={'finish_reason': 'STOP_SEQUENCE'}, metrics={'correct': None})
        d.show_monitor(cases[0], event, 'parent', 'REUSED_EXACT_OLD_PARENT_MONITOR', notes.append)
        self.assertIn('A real displayed question?', notes[0])
        self.assertIn('An actual answer.', notes[0])


class TrainingReaderTests(unittest.TestCase):
    def fixture(self, cost=False):
        count = 8 if cost else 352
        expected = dict(x_tokens=384, assistant_targets=256, content_targets=128, eot_targets=128)
        events = [dict(update=i + 1, epoch=i // 176 + 1, group=i % 176, native_targets=8192,
            positive_rows=128, native_indices=list(d.builder.native_indices(i)), gradient_norm=.5,
            clipped=False, step_seconds=1., assistant_ce=2., content_ce=2., eot_ce=2., native_ce=2., **expected)
            for i in range(count)]
        totals = {key: sum(v[key] for v in events) for key in
                  ('positive_rows', 'x_tokens', 'assistant_targets', 'content_targets', 'eot_targets', 'native_targets')}
        report = dict(status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING', arm='mixed',
            actual_updates=count, initial_core_sha256=d.monitor.base.PARENT_CORE, final_core_sha256='A' * 64,
            frozen_sha256='HASH', checkpoint_written=not cost, step_seconds=[1.] * count, grad_max=.5,
            clip_events=0, totals=totals, actual_optimizer_groups=[],
            event_manifest={'lineage': dict(tag=d.TAG, arm='mixed', cost=cost)},
            checkpoint=str(d.checkpoint('mixed').relative_to(d.ROOT)), checkpoint_sha256='HASH')
        return report, events, expected

    def test_training_reader_checks_latepass_counts_and_absolute_native(self):
        report, events, expected = self.fixture()
        def group(bundle, arm, update, cost=False): return update // 176, update % 176, update % 176, expected
        with patch.object(d, 'required', return_value=report), patch.object(d, 'info', return_value={}), \
             patch.object(d, 'digest', return_value='HASH'), patch.object(d.monitor, 'read_rows', return_value=events), \
             patch.object(d, 'expected_group', side_effect=group), patch.object(d.monitor.original, 'validate_groups'):
            d.read_training('mixed', cost=False, bundle={})
            events[200]['assistant_targets'] -= 1
            with self.assertRaises(ValueError): d.read_training('mixed', cost=False, bundle={})
            events[200]['assistant_targets'] += 1
            events[200]['native_indices'][0] += 8
            with self.assertRaises(ValueError): d.read_training('mixed', cost=False, bundle={})

    def test_cost_reader_does_not_promote_itself_to_completed_activity(self):
        report, events, expected = self.fixture(cost=True)
        with patch.object(d, 'required', return_value=report), patch.object(d, 'info', return_value={}), \
             patch.object(d, 'digest', return_value='HASH'), patch.object(d.monitor, 'read_rows', return_value=events), \
             patch.object(d, 'expected_group', side_effect=lambda b, a, i, c: (0, i, i, expected)), \
             patch.object(d.monitor.original, 'validate_groups'), patch.object(d, 'completed_activity') as activity:
            d.read_training('mixed', cost=True, bundle={})
        activity.assert_not_called()

    def test_cpu_update_core_uses_global128_denominator_and_absolute_native(self):
        import numpy as np
        import torch
        class Head(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.emb = torch.nn.Embedding(17, 4); self.head = torch.nn.Linear(4, 17, bias=False)
            def forward(self, x, return_hidden=True): return self.emb(x)
            def _head_logits(self, hidden): return self.head(hidden)
        class Windows:
            def __init__(self): self.used = []
            def __len__(self): return 2816
            def __getitem__(self, index): self.used.append(index); return np.full(1025, 7, dtype=np.uint16)
        torch.manual_seed(17); model, windows = Head(), Windows()
        cfg = SimpleNamespace(grad_checkpoint=True, mtp_aux=False, max_seq_len=1024)
        record = Record([1, 2, 3], [-100, 5, 4], [0, 1, 1])
        micros = [[record for _ in range(8)] for _ in range(16)]
        rows = [dict(lane=('grounded', 'replay', 'general')[i % 3]) for i in range(8)]
        fake_course = SimpleNamespace(rows=rows, groups=[[i] for i in range(8)])
        bundle = dict(course=fake_course)
        optimizers = (torch.optim.SGD(model.emb.parameters(), lr=5e-5),
                      torch.optim.SGD(model.head.parameters(), lr=2e-4), [])
        expected = dict(x_tokens=384, assistant_targets=256, content_targets=128, eot_targets=128)
        with tempfile.TemporaryDirectory(prefix='broad_update_') as temporary:
            with patch.object(d, 'authority', return_value=10000), patch.object(d.monitor.original, 'validate_groups'), \
                 patch.object(d, 'expected_group', side_effect=lambda b, a, i, c: (0, i, i, expected)), \
                 patch.object(d.builder, 'materialize_group', return_value=micros), \
                 patch('torch.load', side_effect=AssertionError('checkpoint forbidden')), \
                 patch('torch.cuda.init', side_effect=AssertionError('GPU forbidden')), redirect_stdout(io.StringIO()):
                result = d.train_updates(model, cfg, None, bundle, 'mixed', Path(temporary) / 'cost',
                    cost=True, native_windows=windows, optimizers=optimizers, device='cpu')
            path = Path(temporary) / 'cost' / result['event_manifest']['shards'][0]['path']
            events = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(result['actual_updates'], 8)
        self.assertEqual(result['totals']['assistant_targets'], 8 * 256)
        self.assertEqual(result['totals']['native_targets'], 8 * 8192)
        self.assertEqual(windows.used, list(range(64)))
        self.assertEqual(events[0]['assistant_targets'], 256)
        self.assertTrue(all(seconds > 0 for seconds in result['step_seconds']))


if __name__ == '__main__':
    unittest.main()
