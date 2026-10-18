"""Synthetic CPU controller contracts; real model/GPU/source entrypoints blocked."""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
from tinylm.train.mtp_sft import Record
from scripts import diag_p106b_relation_bind as d
from scripts.p106b_relation_bind_loss import Micro


def synthetic_record(targets, length=9):
    return Record([1] * length, [-100] * (length - targets) + [2] * targets,
                  [0] * (length - targets) + [1] * targets)


def natural_source():
    rows = []
    for language in ('ko', 'en'):
        for index in range(32):
            answer = '서울' if language == 'ko' else 'Seoul'
            context = answer + ' fixture ' + str(index)
            rows.append(dict(root=language + '_root_' + str(index), language=language,
                split='test', article_id=language + '_article_' + str(index // 2),
                article_title='Synthetic title ' + str(index), context_id=language + '_ctx_' + str(index),
                qa_id=language + '_qa_' + str(index), question='Synthetic question ' + str(index),
                context=context, answers=[dict(text=answer, answer_start=0)], aliases=[answer],
                source_path='synthetic_' + language + '.json', source_sha256='A' * 64))
    return dict(test=rows)


def small_evaluation():
    relations = d.data.generate(dict(train=8, dev=8, test=8))
    return d.evaluation_cases(natural_source(), relations)


def actual_events(cases):
    events = []
    for case in cases:
        answer = case.get('gold', case.get('aliases', ['unadjudicated'])[0])
        events.append(dict(id=case['id'], case=copy.deepcopy(case), answer=answer,
            generation=dict(generated_tokens=1, finish_reason='STOP_SEQUENCE')))
    return events


def cost_reports():
    return {arm: dict(status='COST8_COMPLETE', updates=8, arm=arm,
        code_sha256={'synthetic.py': 'C' * 64}, corpus_sha256='D' * 64,
        initial_core_sha256=d.PARENT_CORE, crossed_rows=8, checkpoint_written=False,
        step_seconds=[999.] + [float(2 + index)] * 7)
        for index, arm in enumerate(d.ARMS)}


def identity_fixture(label='ce'):
    return dict(endpoint=label, checkpoint='runs/ckpt/synthetic_' + label + '.pt',
        checkpoint_sha256='E' * 64, expected_core_sha256='F' * 64,
        training_report_sha256='9' * 64)


def report_fixture(identity):
    lineage = dict(tag=d.TAG, **identity)
    return dict(status='ACTUAL_FIRST_ANSWERS_RECORDED', endpoint=identity['endpoint'],
        lineage=copy.deepcopy(lineage), code_sha256={'synthetic.py': 'C' * 64},
        corpus_sha256='D' * 64, cases_sha256='A' * 64,
        checkpoint_sha256=identity['checkpoint_sha256'],
        core_before=identity['expected_core_sha256'], core_after=identity['expected_core_sha256'],
        answer_manifest=dict(lineage=copy.deepcopy(lineage)), rank_manifest=dict(lineage=copy.deepcopy(lineage)))


def rank_events(bundles, matrix):
    output = []
    for bundle in bundles:
        first = [dict(question_index=qi, branch_content_index=0, correct_token=2, crossed_token=3,
            correct_logit=matrix[qi][qi], crossed_logit=matrix[qi][1 - qi],
            gap=matrix[qi][qi] - matrix[qi][1 - qi]) for qi in (0, 1)]
        output.append(dict(bundle_id=bundle['bundle_id'], group_id=bundle['group_id'],
            language=bundle['language'], family=bundle['family'], matrix=copy.deepcopy(matrix),
            content_counts=[1, 1], first_divergence=first,
            source_spec_sha256=d.data.sha(rank_specs([bundle])[bundle['bundle_id']])))
    return output


def rank_specs(bundles):
    return {b['bundle_id']: dict(content_counts=[1, 1], candidate_records_sha256='C' * 64,
        branches=[dict(question_index=qi, branch_content_index=0, correct_token=2, crossed_token=3)
                  for qi in (0, 1)]) for b in bundles}


class TinyParameterGroups(torch.nn.Module):
    """Only44 random CPU parameters; no TinyLM architecture, forward or weights."""
    def __init__(self):
        super().__init__(); self.embedding = torch.nn.Embedding(8, 3); self.linear = torch.nn.Linear(3, 5)
    def param_groups(self, lr):
        return [dict(params=[self.embedding.weight], lr=lr, weight_decay=.1),
                dict(params=[self.linear.weight, self.linear.bias], lr=lr, weight_decay=.1)]


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name in ('run', 'evaluate', 'load_parent', 'native_probe', 'emit_answer', 'dev_probe', 'rank_probe'):
            self.stack.enter_context(patch.object(d, name,
                side_effect=AssertionError('forbidden real model/GPU entrypoint: ' + name)))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('interactive input forbidden')))
        self.stack.enter_context(patch('torch.load', side_effect=AssertionError('weight loading forbidden')))
        self.stack.enter_context(patch('torch.save', side_effect=AssertionError('checkpoint writing forbidden')))


class ScheduleAndDenominatorTests(Guarded):
    def test_four_pass_schedule_proof_has192_updates_each_and_unique_epoch_hash(self):
        proof = d.schedule_proof()
        self.assertEqual([row['epoch'] for row in proof], [1, 2, 3, 4])
        self.assertEqual([row['updates'] for row in proof], [192] * 4)
        self.assertEqual(sum(row['updates'] for row in proof), 768)
        self.assertEqual(len({row['schedule_sha256'] for row in proof}), 4)
        self.assertEqual(proof, d.schedule_proof())

    def test_denominator_counts_only_positive_records_and_two_questions_per_bundle(self):
        natural = [[synthetic_record(2), synthetic_record(3)]]
        positive = [synthetic_record(4), synthetic_record(2)]
        crossed = [synthetic_record(8), synthetic_record(7)]
        relations = [(positive, crossed)]
        replay = [synthetic_record(5)]
        group = [Micro('natural', (0,)), Micro('relation', (0,)), Micro('replay', (0,))]
        self.assertEqual(d.denominators(group, natural, relations, replay), (16, 2))
        self.assertEqual(d.micro_records(group[1], natural, relations, replay), positive)
        self.assertNotIn(crossed[0], d.micro_records(group[1], natural, relations, replay))

    def test_replay_only_denominator_and_zero_target_update(self):
        group = [Micro('replay', (0,))]
        self.assertEqual(d.denominators(group, [], [], [synthetic_record(3)]), (3, 0))
        with self.assertRaises(ValueError): d.denominators(group, [], [], [synthetic_record(0)])
        with self.assertRaises(ValueError): d.micro_records(Micro('unknown', (0,)), [], [], [])

    def test_exposure_keeps_crossed_work_separate_from_positive_supervision(self):
        relation = dict(counts=dict(positive_rows=2, x_tokens=7, assistant_targets=4,
            crossed_rows=2, crossed_x_tokens=8, crossed_scored_content_targets=2))
        value = d.exposures([[synthetic_record(2), synthetic_record(3)]], [synthetic_record(4)], relation)
        self.assertEqual(value['per_pass']['positive_rows'], 5)
        self.assertEqual(value['per_pass']['assistant_targets'], 13)
        self.assertEqual(value['per_pass']['crossed_rows'], 2)
        self.assertEqual(value['four_pass']['crossed_rows'], 8)
        self.assertEqual(value['native_targets_four_pass'], 768 * 8192)
        self.assertTrue(value['cross_is_not_positive_supervision'])


class BudgetTests(Guarded):
    def setUp(self):
        super().setUp(); self.reports = cost_reports()
        self.stack.enter_context(patch.object(d, 'info', return_value=dict(code_sha256={'synthetic.py': 'C' * 64})))
        self.stack.enter_context(patch.object(d.original, 'digest', return_value='D' * 64))
        def required(path):
            arm = Path(path).parent.name.removeprefix('cost_')
            return copy.deepcopy(self.reports[arm])
        self.stack.enter_context(patch.object(d, 'stage_report', side_effect=required))

    def test_cost_budget_uses_worst_warm_step_and_both_arms_with_evaluation_reserve(self):
        result = d.cost_budget(2.5)
        self.assertEqual(result['per_arm_seconds'], {'ce': 2136., 'contrast': 2904.})
        self.assertEqual(result['forecast_including_evaluation_sec'], 8640.)
        self.assertTrue(result['fits']); self.assertFalse(d.cost_budget(2.)['fits'])
        self.assertEqual(result['user_budget_sec'], 9000.)

    def test_mismatched_cost_receipt_cannot_authorize_full_training(self):
        changes = dict(status='ERROR', updates=7, arm='other', code_sha256={}, corpus_sha256='wrong',
                       initial_core_sha256='wrong', crossed_rows=0, checkpoint_written=True)
        for field, value in changes.items():
            with self.subTest(field=field):
                self.reports = cost_reports(); self.reports['contrast'][field] = value
                with self.assertRaises(ValueError): d.cost_budget(4.)

    def test_incomplete_nonfinite_or_nonpositive_warmed_times_fail(self):
        for times in ([1.] * 7, [1.] * 9, [1., 0.] + [1.] * 6,
                      [1., float('nan')] + [1.] * 6, [1., float('inf')] + [1.] * 6):
            with self.subTest(times=times):
                self.reports = cost_reports(); self.reports['ce']['step_seconds'] = times
                with self.assertRaises(ValueError): d.cost_budget(4.)
        for hours in (0., -1., float('nan'), float('inf')):
            with self.assertRaises(ValueError): d.cost_budget(hours)


class StageAndIdentityTests(Guarded):
    def test_absent_stage_is_not_run_and_does_not_open_a_source(self):
        with tempfile.TemporaryDirectory(prefix='relation_controller_stage_') as folder, \
                patch.object(d, 'required', side_effect=AssertionError('absent stage must not be read')):
            with self.assertRaises(d.PrerequisitePending): d.stage_report(Path(folder) / 'missing.json')

    def test_failure_status_keeps_missing_resource_oom_error_and_interrupt_distinct(self):
        from scripts.p106b_gate_runtime import PrerequisiteHold
        oom = type('OutOfMemoryError', (RuntimeError,), {'__module__': 'torch.cuda'})
        self.assertEqual(d.failure_status(d.PrerequisitePending('not executed')), ('PREREQUISITE_NOT_RUN', 8))
        self.assertEqual(d.failure_status(PrerequisiteHold('not started')), ('RESOURCE_PRECONDITION_NOT_RUN', 8))
        self.assertEqual(d.failure_status(oom('synthetic type only')), ('ACTUAL_RESOURCE_OOM', 8))
        self.assertEqual(d.failure_status(ValueError('out of memory text is not an OOM type')), ('TOOL_ERROR', 9))
        self.assertEqual(d.failure_status(KeyboardInterrupt()), ('INTERRUPTED', 130))

    def test_old_optimizer_embedding_decay_and_new_explicit_all_group_zero_are_observed(self):
        from scripts import diag_p101a_sft_mtp as runtime
        model = TinyParameterGroups()
        with patch.object(runtime, 'load_runtime', side_effect=AssertionError('real model loading forbidden')):
            old_adam, old_muon = runtime.optimizers(model)
            old_embedding_decay = [g['weight_decay'] for g in old_adam.param_groups
                                   if any(p is model.embedding.weight for p in g['params'])]
            self.assertEqual(old_embedding_decay, [.1])
            adam, muon, receipts = d.make_optimizers(model)
        self.assertTrue(all(g['weight_decay'] == 0. for opt in (adam, muon) for g in opt.param_groups))
        self.assertEqual(sum(r['parameters'] for r in receipts), 44)
        self.assertEqual(sum(r['tensors'] for r in receipts), 3)
        self.assertTrue(all(r['lr'] == (5e-5 if r['optimizer'] == 'adamw' else 2e-4) for r in receipts))
        self.assertEqual(len(old_adam.state), 0); self.assertEqual(len(old_muon.state), 0)
        self.assertEqual(len(adam.state), 0); self.assertEqual(len(muon.state), 0)

    def test_parent_identity_checks_immutable_hash_without_loading_weights(self):
        with patch.object(d.original, 'digest', return_value=d.PARENT_SHA) as digest:
            result = d.endpoint_identity('parent')
        digest.assert_called_once_with(d.PARENT)
        self.assertEqual(result['expected_core_sha256'], d.PARENT_CORE)
        self.assertIsNone(result['training_report_sha256'])
        with patch.object(d.original, 'digest', return_value='changed'):
            with self.assertRaises(ValueError): d.endpoint_identity('parent')
        with self.assertRaises(ValueError): d.endpoint_identity('unregistered')

    def test_child_identity_binds_complete_training_receipt_code_corpus_checkpoint_and_body(self):
        arm = 'ce'; cp = d.checkpoint(arm); training_path = d.EVIDENCE / 'train_ce' / 'report.json'
        report = dict(status='TRAIN_COMPLETE_EVALUATION_PENDING', arm=arm, updates=768, weight=0.,
            code_sha256={'synthetic.py': 'C' * 64}, corpus_sha256='D' * 64,
            initial_core_sha256=d.PARENT_CORE, checkpoint=str(cp.relative_to(d.ROOT)),
            checkpoint_sha256='E' * 64, final_core_sha256='F' * 64)
        def digest(path):
            return {cp: 'E' * 64, training_path: '9' * 64, d.CORPUS / 'report.json': 'D' * 64}[Path(path)]
        with patch.object(d, 'info', return_value=dict(code_sha256={'synthetic.py': 'C' * 64})), \
                patch.object(d.original, 'digest', side_effect=digest), \
                patch.object(d, 'stage_report', side_effect=lambda path: copy.deepcopy(report)):
            identity = d.endpoint_identity(arm)
            self.assertEqual(identity['checkpoint_sha256'], 'E' * 64)
            self.assertEqual(identity['expected_core_sha256'], 'F' * 64)
            self.assertEqual(identity['training_report_sha256'], '9' * 64)
            baseline = copy.deepcopy(report)
            for field, value in dict(status='COST8_COMPLETE', arm='contrast', updates=767, weight=.1,
                    code_sha256={}, corpus_sha256='changed', initial_core_sha256='changed',
                    checkpoint='wrong.pt', checkpoint_sha256='changed', final_core_sha256='short').items():
                report.clear(); report.update(baseline); report[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError): d.endpoint_identity(arm)

    def test_valid_evaluation_receipt_binds_both_raw_manifest_lineages(self):
        identity = identity_fixture(); report = report_fixture(identity)
        self.assertTrue(d.validate_evaluation_report(report, identity, 'A' * 64, 'D' * 64,
                                                   {'synthetic.py': 'C' * 64}))

    def test_source_checkpoint_case_core_or_training_lineage_mutations_are_rejected(self):
        identity = identity_fixture(); original = report_fixture(identity)
        changes = dict(status='ERROR', endpoint='contrast', code_sha256={}, corpus_sha256='wrong',
            cases_sha256='wrong', checkpoint_sha256='wrong', core_before='wrong', core_after='wrong')
        for field, value in changes.items():
            changed = copy.deepcopy(original); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                d.validate_evaluation_report(changed, identity, 'A' * 64, 'D' * 64, {'synthetic.py': 'C' * 64})
        for field in ('checkpoint', 'checkpoint_sha256', 'expected_core_sha256', 'training_report_sha256'):
            changed = copy.deepcopy(original); changed['lineage'][field] = 'changed'
            with self.subTest(lineage_field=field), self.assertRaises(ValueError):
                d.validate_evaluation_report(changed, identity, 'A' * 64, 'D' * 64, {'synthetic.py': 'C' * 64})

    def test_other_arm_receipt_and_swapped_answer_or_rank_lineages_are_rejected(self):
        identity = identity_fixture(); other = identity_fixture('contrast'); original = report_fixture(identity)
        with self.assertRaises(ValueError):
            d.validate_evaluation_report(original, other, 'A' * 64, 'D' * 64, {'synthetic.py': 'C' * 64})
        for manifest in ('answer_manifest', 'rank_manifest'):
            changed = copy.deepcopy(original); changed[manifest]['lineage'] = dict(tag=d.TAG, **other)
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                d.validate_evaluation_report(changed, identity, 'A' * 64, 'D' * 64, {'synthetic.py': 'C' * 64})


class RankSummaryTests(Guarded):
    @classmethod
    def setUpClass(cls):
        cls.bundles = d.data.generate(dict(train=8, dev=8, test=8))['test']
        cls.specs = rank_specs(cls.bundles)

    def test_positive_two_column_gaps_cannot_be_reported_as_two_correct_answer_rows(self):
        raw = rank_events(self.bundles, [[-4., -1.], [-12., -.5]])
        report = d.summarize_ranks(raw, self.bundles, self.specs)
        for language in ('ko', 'en'):
            self.assertEqual(report[language]['bundles'], 4)
            self.assertEqual(report[language]['column_both_positive'], 4)
            self.assertEqual(report[language]['row_both_positive'], 0)
            self.assertEqual(report[language]['first_divergence_both_positive'], 0)

    def test_both_correct_rows_and_first_branches_are_separately_counted(self):
        raw = rank_events(self.bundles, [[-.5, -3.], [-4., -1.]])
        report = d.summarize_ranks(raw, self.bundles, self.specs)
        for values in report.values():
            self.assertEqual(values['row_both_positive'], 4)
            self.assertEqual(values['first_divergence_both_positive'], 4)

    def test_missing_duplicate_nonfinite_or_changed_rank_source_is_rejected(self):
        raw = rank_events(self.bundles, [[-.5, -3.], [-4., -1.]])
        variants = [raw[:-1], raw + [raw[0]]]
        for field, value in (('group_id', 'changed'), ('language', 'changed'), ('family', 'changed'),
                             ('matrix', [[float('nan'), -1.], [-2., -3.]])):
            bad = copy.deepcopy(raw); bad[0][field] = value; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['first_divergence'][0]['gap'] += 1.; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): d.summarize_ranks(bad, self.bundles, self.specs)

    def test_branch_position_token_count_and_candidate_record_spec_mutations_are_rejected(self):
        raw = rank_events(self.bundles, [[-.5, -3.], [-4., -1.]])
        variants = []
        for field, value in (('branch_content_index', 1), ('correct_token', 9), ('crossed_token', 8)):
            bad = copy.deepcopy(raw); bad[0]['first_divergence'][0][field] = value; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['content_counts'] = [2, 1]; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['source_spec_sha256'] = 'changed'; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): d.summarize_ranks(bad, self.bundles, self.specs)
        bad_specs = copy.deepcopy(self.specs)
        bad_specs[self.bundles[0]['bundle_id']]['candidate_records_sha256'] = 'changed'
        with self.assertRaises(ValueError): d.summarize_ranks(raw, self.bundles, bad_specs)

    def test_rank_specifications_recompute_exact_shared_prefix_branch_from_mock_records(self):
        def rec(content):
            ids = [1, 1] + list(content) + [4, 1]
            labels = [-100, -100] + list(content) + [4, -100]
            y = labels[1:]
            return Record(ids[:-1], y, [int(v != -100) for v in y])
        positive = [rec((5, 2)), rec((5, 3))]
        crossed = [rec((5, 3)), rec((5, 2))]
        bundle = self.bundles[0]
        with patch.object(d.data, 'encode_bundle', return_value=(positive, crossed)):
            specification = d.rank_specifications([bundle], object())[bundle['bundle_id']]
        self.assertEqual(specification['content_counts'], [2, 2])
        self.assertEqual(specification['branches'], [
            dict(question_index=0, branch_content_index=1, correct_token=2, crossed_token=3),
            dict(question_index=1, branch_content_index=1, correct_token=3, crossed_token=2)])
        self.assertEqual(specification['candidate_records_sha256'],
                         d.data.sha([d.record_identity(r) for r in positive + crossed]))


class EvaluationTests(Guarded):
    @classmethod
    def setUpClass(cls): cls.cases = small_evaluation()

    def test_small_evaluation_has_complete_relation_views_natural64_and_no_assistant_gold(self):
        self.assertEqual(Counter(c['lane'] for c in self.cases),
                         {'relation': 48, 'natural': 192, 'canary': 24, 'user_seen': 6})
        self.assertEqual(len({c['id'] for c in self.cases}), 270)
        for case in self.cases:
            self.assertEqual(len(case['messages']), 1)
            self.assertEqual(case['messages'][0]['role'], 'user')
        for language in ('ko', 'en'):
            relation = [c for c in self.cases if c['lane'] == 'relation' and c['language'] == language]
            self.assertEqual(Counter(c['view'] for c in relation), {0: 8, 1: 8, 2: 8})
        self.assertEqual(self.cases, small_evaluation())

    def test_cpu_input_proof_uses_complete_candidate_free_actual_prompt_ids(self):
        from scripts.test_p106b_relation_bind_data import CharTokenizer
        proof = d.evaluation_input_proof(self.cases, CharTokenizer())
        self.assertEqual(proof['responses'], len(self.cases))
        self.assertEqual(proof['cases_sha256'], d.data.sha(self.cases))
        self.assertFalse(proof['oracle_candidates_in_generation'])
        self.assertLessEqual(proof['max_prompt_tokens'] + proof['generation_budget'], proof['context'])
        self.assertEqual(proof, d.evaluation_input_proof(self.cases, CharTokenizer()))

    def test_cpu_input_proof_rejects_assistant_gold_and_exhausted_context(self):
        from types import SimpleNamespace
        from scripts.test_p106b_relation_bind_data import CharTokenizer
        bad = copy.deepcopy(self.cases[:1])
        bad[0]['messages'].append(dict(role='assistant', content='oracle answer'))
        with self.assertRaises(ValueError): d.evaluation_input_proof(bad, CharTokenizer())
        class TooLong:
            def encode(self, value): return SimpleNamespace(ids=[1] * 897)
        with self.assertRaises(ValueError): d.evaluation_input_proof(self.cases[:1], TooLong())

    def test_natural_monitor_requires32_source_questions_in_each_language(self):
        rows = natural_source(); rows['test'] = rows['test'][:-1]
        relations = d.data.generate(dict(train=8, dev=8, test=8))
        with self.assertRaises(ValueError): d.evaluation_cases(rows, relations)

    def test_summary_separates_exact_pair_success_natural_metrics_and_unadjudicated(self):
        report = d.summarize_answers(actual_events(self.cases), self.cases)
        self.assertEqual(report['actual_responses'], 270)
        self.assertEqual(report['relation_both_correct']['ko|v0'], {'bundles': 4, 'both_correct': 4})
        self.assertEqual(report['counts']['natural|en|v0']['em'], 32.)
        self.assertEqual(report['counts']['canary|en|v0']['exact'], 12)
        self.assertEqual(report['counts']['user_seen|ko|v0']['unadjudicated'], 6)
        self.assertEqual(report['user_seen_semantic_quality'], 'NOT_ADJUDICATED')

    def test_one_correct_question_does_not_make_the_bundle_correct(self):
        raw = actual_events(self.cases)
        selected = next(c for c in self.cases if c['lane'] == 'relation' and c['language'] == 'ko'
                        and c['view'] == 0 and c['question_index'] == 0)
        next(e for e in raw if e['id'] == selected['id'])['answer'] = 'wrong'
        report = d.summarize_answers(raw, self.cases)
        self.assertEqual(report['relation_both_correct']['ko|v0'], {'bundles': 4, 'both_correct': 3})
        self.assertEqual(report['counts']['relation|ko|v0']['exact'], 7)

    def test_missing_duplicate_unknown_or_changed_source_events_are_rejected(self):
        variants = []
        raw = actual_events(self.cases); variants.extend((raw[:-1], raw + [raw[0]]))
        bad = copy.deepcopy(raw); bad[0]['id'] = 'unknown'; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['case']['source_mutated'] = True; variants.append(bad)
        for events in variants:
            with self.assertRaises(ValueError): d.summarize_answers(events, self.cases)

    def test_invalid_actual_generation_accounting_is_rejected(self):
        for field, value in (('generated_tokens', 0), ('generated_tokens', True), ('finish_reason', None)):
            raw = actual_events(self.cases); raw[0]['generation'][field] = value
            with self.assertRaises(ValueError): d.summarize_answers(raw, self.cases)
        raw = actual_events(self.cases); raw[0]['answer'] = None
        with self.assertRaises(ValueError): d.summarize_answers(raw, self.cases)

    def test_paired_relation_positive_and_negative_changes_count_graphs_not_questions(self):
        wrong = actual_events(self.cases); right = actual_events(self.cases)
        for event in wrong:
            case = event['case']
            if case['lane'] == 'relation' and case['question_index'] == 1: event['answer'] = 'wrong'
        positive = d.paired_relation(wrong, right, self.cases, draws=64)
        negative = d.paired_relation(right, wrong, self.cases, draws=64)
        for language in ('ko', 'en'):
            for view in range(3):
                key = language + '|v' + str(view)
                self.assertEqual(positive[key]['independent_graphs'], 4)
                self.assertEqual(positive[key]['delta_both_correct_pp'], 100.)
                self.assertEqual(positive[key]['descriptive_ci95_pp'], [100., 100.])
                self.assertEqual(negative[key]['delta_both_correct_pp'], -100.)
                self.assertEqual(negative[key]['descriptive_ci95_pp'], [-100., -100.])

    def test_paired_relation_mixed_counterfactual_changes_have_expected25pp(self):
        graph_ids = sorted({c['group_id'] for c in self.cases if c['lane'] == 'relation'})
        left_good = {graph_ids[2]}; right_good = {graph_ids[0], graph_ids[1]}
        left, right = actual_events(self.cases), actual_events(self.cases)
        for raw, good in ((left, left_good), (right, right_good)):
            for event in raw:
                case = event['case']
                if case['lane'] == 'relation' and case['question_index'] == 1 and case['group_id'] not in good:
                    event['answer'] = 'wrong'
        report = d.paired_relation(left, right, self.cases, draws=256)
        reverse = d.paired_relation(right, left, self.cases, draws=256)
        for key, value in report.items():
            self.assertEqual(value['delta_both_correct_pp'], 25.)
            self.assertEqual(reverse[key]['delta_both_correct_pp'], -25.)
            self.assertEqual(value['independent_graphs'], 4)
            self.assertLess(value['descriptive_ci95_pp'][0], 0.)
            self.assertGreater(value['descriptive_ci95_pp'][1], 0.)
            self.assertEqual(value['learning_seeds'], 1)

    def test_paired_relation_invalid_draws_and_incomplete_graphs_are_rejected(self):
        raw = actual_events(self.cases)
        for draws in (0, -1, True):
            with self.assertRaises(ValueError): d.paired_relation(raw, raw, self.cases, draws=draws)
        with self.assertRaises(ValueError): d.paired_relation(raw[:-1], raw, self.cases, draws=64)
        cases = copy.deepcopy(self.cases)
        relation = [c for c in cases if c['lane'] == 'relation' and c['language'] == 'ko' and c['view'] == 0]
        first, second = list(dict.fromkeys(c['group_id'] for c in relation))[:2]
        for case in relation:
            if case['group_id'] == second: case['group_id'] = first
        raw = actual_events(cases)
        with self.assertRaises(ValueError): d.paired_relation(raw, raw, cases, draws=64)


class OutputTests(Guarded):
    def test_write_is_utf8_newfile_only_and_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory(prefix='relation_controller_output_') as folder:
            root = Path(folder)
            with patch.object(d, 'ROOT', root):
                target = root / 'evidence' / 'small.json'
                d.write(target, dict(한글='값', finite=1.))
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), dict(한글='값', finite=1.))
                before = target.read_bytes()
                with self.assertRaises(FileExistsError): d.write(target, dict(replaced=True))
                self.assertEqual(target.read_bytes(), before)

    def test_twenty_mb_or_nonfinite_evidence_is_rejected_before_file_creation(self):
        with tempfile.TemporaryDirectory(prefix='relation_controller_limit_') as folder:
            root = Path(folder)
            with patch.object(d, 'ROOT', root):
                target = root / 'never_created' / 'large.json'
                with patch.object(d.json, 'dumps', return_value='x' * 19_999_999):
                    with self.assertRaises(ValueError): d.write(target, {})
                self.assertFalse(target.exists()); self.assertFalse(target.parent.exists())
                with self.assertRaises(ValueError): d.write(target, dict(bad=float('nan')))
                self.assertFalse(target.exists())

    def test_output_escape_parent_traversal_and_link_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='relation_controller_paths_') as folder:
            root = Path(folder)
            with patch.object(d, 'ROOT', root):
                with self.assertRaises(ValueError): d.safe(root.parent / 'outside.json')
                with self.assertRaises(ValueError): d.safe(root / 'unused' / '..' / 'ambiguous.json')
                (root / 'target').mkdir(); (root / 'linked').symlink_to(root / 'target', target_is_directory=True)
                with self.assertRaises(ValueError): d.write(root / 'linked' / 'bad.json', {})
                self.assertFalse((root / 'target' / 'bad.json').exists())


class CliTests(Guarded):
    def main_with(self, argv):
        with patch.object(sys, 'argv', ['diag_p106b_relation_bind.py', *argv]), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return d.main()

    def test_all_check_only_modes_are_noninteractive_and_skip_asset_readers(self):
        with patch.object(d, 'info', return_value={'status': 'SYNTHETIC_CHECK_ONLY'}), \
                patch.object(d, 'prepare', side_effect=AssertionError('prepare forbidden in check-only')), \
                patch.object(d, 'readback', side_effect=AssertionError('readback forbidden in check-only')), \
                patch.object(d, 'cost_budget', side_effect=AssertionError('budget forbidden in check-only')), \
                patch.object(d, 'old_source', side_effect=AssertionError('real source forbidden')), \
                patch.object(d, 'read_prepared', side_effect=AssertionError('actual assets forbidden')):
            for mode in ('prepare', 'cost', 'train', 'evaluate', 'readback', 'budget'):
                self.assertEqual(self.main_with(['--mode', mode, '--check-only']), 0)

    def test_invalid_mode_action_arm_wall_and_budget_fail_in_argument_parser(self):
        variants = ([], ['--mode', 'prepare'], ['--mode', 'bad', '--check-only'],
            ['--mode', 'prepare', '--check-only', '--execute'],
            ['--mode', 'cost', '--execute'], ['--mode', 'train', '--execute'],
            ['--mode', 'cost', '--arm', 'unknown', '--check-only'],
            ['--mode', 'prepare', '--check-only', '--max-wall-sec', '59'],
            ['--mode', 'prepare', '--check-only', '--max-wall-sec', '21601'],
            ['--mode', 'prepare', '--check-only', '--budget-hours', '0'],
            ['--mode', 'prepare', '--check-only', '--budget-hours', '25'],
            ['--mode', 'prepare', '--check-only', '--budget-hours', 'nan'])
        with patch.object(d, 'info', side_effect=AssertionError('invalid args reached info')):
            for argv in variants:
                with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised: self.main_with(argv)
                self.assertEqual(raised.exception.code, 2)

    def test_budget_mode_dispatches_cpu_estimate_only(self):
        with patch.object(d, 'cost_budget', return_value=dict(fits=True)) as budget:
            self.assertEqual(self.main_with(['--mode', 'budget', '--budget-hours', '3', '--execute']), 0)
        budget.assert_called_once_with(3.)

    def test_unexecuted_budget_stage_exits8_and_tool_error_exits9(self):
        with patch.object(d, 'cost_budget', side_effect=d.PrerequisitePending('synthetic absent stage')):
            self.assertEqual(self.main_with(['--mode', 'budget', '--execute']), 8)
        with patch.object(d, 'cost_budget', side_effect=ValueError('synthetic tool failure')):
            self.assertEqual(self.main_with(['--mode', 'budget', '--execute']), 9)

    def test_direct_help_exits_without_models_assets_or_input(self):
        result = subprocess.run([sys.executable, '-B', '-I', str(ROOT / 'scripts/diag_p106b_relation_bind.py'), '--help'],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--check-only', result.stdout); self.assertIn('--mode', result.stdout)
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__': unittest.main()
