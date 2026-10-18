"""Small CPU tensors/canonical fixtures only; real assets/models/GPU blocked."""
from __future__ import annotations
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import copy
from datetime import timedelta
import io
import importlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from tinylm.train.mtp_sft import Record
from scripts import diag_p106b_subject_role as d
from scripts.test_p106b_subject_role_data import CharTokenizer
READ_PREPARED = d.read_prepared
READ_SHARDS = d.read_shards


def record(content=(1,)):
    content = list(content)
    return Record([0, 0, 0] + content, [-100, -100] + content + [4], [0, 0] + [1] * (len(content) + 1))


def relation_records():
    values = [(1,), (2,), (3, 5), (6,)]
    return ([record(values[q]) for q in range(4)], [record(values[a]) for q, a in d.data.CROSSED_LAYOUT])


def natural_source():
    values = []
    for language in ('ko', 'en'):
        for i in range(32):
            answer = '서울' if language == 'ko' else 'Seoul'
            values.append(dict(root=language + '_root_' + str(i), language=language, split='test',
                article_id=language + '_article_' + str(i // 2), article_title='Synthetic title' + str(i),
                context_id=language + '_context_' + str(i), qa_id=language + '_qa_' + str(i),
                context=answer + ' fixture ' + str(i), question='Synthetic question ' + str(i),
                source_path='synthetic_' + language + '.json', source_sha256='A' * 64,
                answers=[dict(text=answer, answer_start=0)], aliases=[answer]))
    return dict(test=values)


def bundles(count=8):
    parents = d.data.original.generate(dict(train=8, dev=8, test=count))
    return {s: [d.data.derive_bundle(b) for b in rows] for s, rows in parents.items()}


def metadata(messages, tok, finish='STOP_SEQUENCE'):
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True); ids = tok.encode(prompt).ids
    return dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        candidate_answers_supplied=False, prompt_sha256=d.natural_data.sha(prompt),
        prompt_ids_sha256=d.natural_data.sha(ids), prompt_tokens=len(ids), max_new=128,
        stop_token_sequences=[[4]], matched_stop_sequence=[4] if finish == 'STOP_SEQUENCE' else None,
        generated_tokens=3 if finish == 'STOP_SEQUENCE' else 128, finish_reason=finish,
        generated_ids_sha256='A' * 64)


def answers(cases, tok):
    return [dict(id=c['id'], case=copy.deepcopy(c), answer=c.get('gold', c.get('aliases', ['unadjudicated'])[0]),
        generation=metadata(c['messages'], tok)) for c in cases]


def group_receipt():
    return [dict(optimizer='adamw', group=0, lr=5e-5, weight_decay=0., parameters=24, tensors=1),
            dict(optimizer='muon', group=0, lr=2e-4, weight_decay=0., parameters=20, tensors=1)]


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name in ('source_inputs', 'read_prepared', 'old_source', 'load_parent', 'emit_answer', 'native_probe'):
            self.stack.enter_context(patch.object(d, name, side_effect=AssertionError('real asset/model path forbidden: ' + name)))
        self.stack.enter_context(patch('torch.load', side_effect=AssertionError('learned weights forbidden')))
        self.stack.enter_context(patch('torch.save', side_effect=AssertionError('checkpoint writes forbidden')))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('interactive input forbidden')))

    def stub(self, owner, name, value): return self.stack.enter_context(patch.object(owner, name, value))

    def paths(self):
        temp = TemporaryDirectory(prefix='subject_role_controller_'); self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name, value in (('ROOT', root), ('LOCAL', root / 'local'), ('CORPUS', root / 'local/corpus'), ('EVIDENCE', root / 'evidence')):
            self.stub(d, name, value)
        return root


class LayoutAndTensorTests(Guarded):
    def test_896_unique_schedule_and_separate_native_vector(self):
        proof = d.schedule_proof()
        self.assertEqual([v['updates'] for v in proof], [224] * 4)
        self.assertEqual(sum(v['updates'] for v in proof), 896)
        self.assertEqual(len({v['sha256'] for v in proof}), 4)
        offsets = d.native_offsets()
        self.assertEqual(offsets, d.native_offsets()); self.assertEqual(len(offsets), 7168)
        self.assertEqual(len(set(offsets)), 7168)
        self.assertTrue(all(v % 1025 == 0 and v + 1025 <= 597995000 for v in offsets))
        self.assertTrue(all(b - a >= 1025 for a, b in zip(sorted(offsets), sorted(offsets)[1:])))
        self.assertEqual(d.NATIVE_SEED, 20261017)
        with self.assertRaises(ValueError): d.native_offsets(1025, count=2)

    def test_whole_update_counts_questions_not_negative_edges(self):
        natural = [[record(), record((2, 3))]]; relation = [relation_records()] * 2; replay = [record()]
        group = [d.loss.Micro('natural', (0,)), d.loss.Micro('relation', (0, 1)), d.loss.Micro('replay', (0,))]
        words, questions = d.denominators(group, natural, relation, replay)
        expected = sum(r.targets for micro in group for r in d.micro_records(micro, natural, relation, replay))
        self.assertEqual(words, expected); self.assertEqual(questions, 8)
        self.assertNotEqual(questions, 24)
        with self.assertRaises(ValueError): d.micro_records(d.loss.Micro('unknown', (0,)), natural, relation, replay)

    def test_actual16_sequences_per_graph_all_arms_keep_physical8x4_forward_path(self):
        pos, cross = relation_records(); positive = pos * 2; crossed = cross * 2
        observed = []
        for arm in d.ARMS:
            calls = []; parameter = torch.tensor(.07, requires_grad=True)
            def forward(x, return_hidden=False):
                self.assertTrue(return_hidden); calls.append(tuple(x.shape))
                return (parameter * torch.arange(8.).reshape(1, 1, 8)).expand(x.shape[0], x.shape[1], 8)
            proxy = NS(_head_logits=lambda hidden: hidden)
            ce, ranking, counters = d.relation_micro(proxy, forward, positive, crossed, 0, 4, arm, device='cpu')
            objective = d.loss.normalized_loss(ce, sum(r.targets for r in positive), ranking, 8, d.WEIGHTS[arm])
            objective.backward()
            self.assertTrue(torch.isfinite(parameter.grad)); self.assertEqual(calls, [(8, 1024)] * 4)
            self.assertEqual(counters['full_scored_sequences'], 32)
            self.assertEqual(counters['relation_questions'], 8); self.assertEqual(counters['crossed_rows'], 24)
            observed.append((float(ce.detach()), float(ranking.detach())))
        self.assertEqual(observed[0][0], observed[1][0]); self.assertEqual(observed[1][0], observed[2][0])
        self.assertEqual(observed[0][1], 0.)
        self.assertGreater(observed[1][1], 0.); self.assertGreater(observed[2][1], 0.)

    def test_exposure_separates_padding_cross_work_and_native_targets(self):
        relation = dict(totals=dict(positive_rows=4, x_tokens=10, assistant_targets=8,
            crossed_rows=12, crossed_x_tokens=30, crossed_content_targets=12))
        value = d.exposure([[record(), record()]], [record()], relation)
        self.assertEqual(value['per_pass']['positive_rows'], 7)
        self.assertEqual(value['four_pass']['crossed_rows'], 48)
        self.assertEqual(value['padded_positive_slots'], 117440512)
        self.assertEqual(value['padded_crossed_slots'], 100663296)
        self.assertEqual(value['native_targets'], 7340032)
        self.assertNotEqual(value['per_pass']['x_tokens'], value['padded_positive_slots'])

    def test_content_prefix_compares_eot_against_next_content_not_missing_or_positive_tie(self):
        shorter = record((1,)); longer = record((1, 2))
        branch = d.first_divergence_spec(shorter, longer, 0, 2)
        self.assertEqual(branch['branch_index'], 1)
        self.assertEqual((branch['correct_token'], branch['crossed_token']), (4, 2))
        self.assertTrue(branch['includes_eot']); self.assertEqual(branch['branch_type'], 'CONTENT_PREFIX_EOT_BRANCH')
        reverse = d.first_divergence_spec(longer, shorter, 2, 0)
        self.assertEqual((reverse['correct_token'], reverse['crossed_token']), (2, 4))
        with self.assertRaises(ValueError): d.first_divergence_spec(shorter, shorter, 0, 1)


class EvaluationTests(Guarded):
    def setUp(self):
        super().setUp(); self.tok = CharTokenizer(); self.bundles = bundles()
        self.cases = d.evaluation_cases(natural_source(), self.bundles)
        self.events = answers(self.cases, self.tok)

    def test_full1758_counts_and_parent_graph_units(self):
        full = bundles(128); cases = d.evaluation_cases(natural_source(), full)
        self.assertEqual(len(cases), 1758)
        count = d.evaluation_proof(cases, self.tok)['lane_counts']
        self.assertEqual(count['subject_role|ko'], 768); self.assertEqual(count['subject_role|en'], 768)
        self.assertEqual(count['natural|ko'], 96); self.assertEqual(count['natural|en'], 96)
        self.assertEqual(count['canary|ko'], 12); self.assertEqual(count['canary|en'], 12)
        self.assertEqual(count['user_seen|ko'], 6)
        summary = d.summarize_answers(answers(cases, self.tok), cases, full['test'], self.tok)
        self.assertEqual(summary['graph_scores']['ko|v0']['graphs'], 64)
        self.assertEqual(summary['graph_scores']['ko|v0']['all_four_exact'], 64)

    def test_missing_duplicate_changed_case_or_generation_policy_refused(self):
        with self.assertRaises(ValueError): d.summarize_answers([], [], [], self.tok)
        for bad in (self.events[:-1], []):
            with self.assertRaises(d.Pending): d.summarize_answers(bad, self.cases, self.bundles['test'], self.tok)
        for mutate in ('duplicate', 'case', 'candidate', 'prefix', 'eot'):
            bad = copy.deepcopy(self.events)
            if mutate == 'duplicate': bad.append(bad[0])
            elif mutate == 'case': bad[0]['case']['gold'] = 'wrong'
            elif mutate == 'candidate': bad[0]['generation']['candidate_answers_supplied'] = True
            elif mutate == 'prefix': bad[0]['generation']['prompt_ids_sha256'] = 'wrong'
            else: bad[0]['generation']['matched_stop_sequence'] = None
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                d.summarize_answers(bad, self.cases, self.bundles['test'], self.tok)

    def test_other_subject_same_role_and_termination_are_separate(self):
        bad = copy.deepcopy(self.events); first = bad[0]; b = next(b for b in self.bundles['test'] if b['bundle_id'] == first['case']['bundle_id'])
        first['answer'] = b['answers'][first['case']['question_index'] ^ 2]
        summary = d.summarize_answers(bad, self.cases, self.bundles['test'], self.tok)
        key = 'subject_role|' + b['language'] + '|v0'
        self.assertEqual(summary['counts'][key][d.data.OTHER_SUBJECT_SAME_ROLE], 1)
        self.assertEqual(summary['counts'][key]['stopped'], summary['counts'][key]['responses'])
        self.assertLess(summary['counts'][key]['exact'], summary['counts'][key]['responses'])

    def rank_fixture(self):
        specs = d.rank_specifications(self.bundles['test'], self.tok); actual = {e['id']: e for e in self.events}; ranks = []
        for b in self.bundles['test']:
            spec = specs[b['bundle_id']]; lengths = spec['content_lengths']
            means = [[-1. if q == a else -2. for a in range(4)] for q in range(4)]
            sums = [[means[q][a] * lengths[a] for a in range(4)] for q in range(4)]
            first = [dict(v, correct_logit=1., crossed_logit=0., gap=1.) for v in spec['branches']]
            raw_answers = [dict(question_index=q, answer_sha256=d.natural_data.sha(actual[d.data.query_id(b, q)]['answer']), error_type=d.data.CORRECT)
                           for q in range(4)]
            ranks.append(dict(bundle_id=b['bundle_id'], group_id=b['parent_group_id'], language=b['language'], family=b['family'],
                content_sums=sums, content_means=means, eot_logp=[[-1.] * 4 for _ in range(4)], content_lengths=lengths,
                first_divergence=first, actual_view0_answers=raw_answers, source_spec_sha256=d.natural_data.sha(spec)))
        return ranks, specs

    def test_complete4x4_sums_means_eot_lengths_branches_and_actual_error_recount(self):
        ranks, specs = self.rank_fixture(); summary = d.summarize_ranks(ranks, self.bundles['test'], specs, self.events)
        self.assertEqual(summary['ko']['all4_rows_rank_correct'], 4)
        for field in ('content_lengths', 'content_means', 'actual_view0_answers', 'source_spec_sha256'):
            bad = copy.deepcopy(ranks)
            if field == 'content_lengths': bad[0][field][0] += 1
            elif field == 'content_means': bad[0][field][0][0] = -.5
            elif field == 'actual_view0_answers': bad[0][field][0]['error_type'] = 'wrong'
            else: bad[0][field] = 'wrong'
            with self.subTest(field=field), self.assertRaises(ValueError): d.summarize_ranks(bad, self.bundles['test'], specs, self.events)
        bad = copy.deepcopy(ranks); bad[0]['first_divergence'][0]['correct_token'] = -1
        with self.assertRaises(ValueError): d.summarize_ranks(bad, self.bundles['test'], specs, self.events)
        with self.assertRaises(d.Pending): d.summarize_ranks(ranks[:-1], self.bundles['test'], specs, self.events)

    def test_paired_graph_interval_is_not_question_or_translation_independence(self):
        result = d.paired_graphs(self.events, self.events, self.cases, draws=20)
        self.assertEqual(result['ko|v0']['independent_graphs'], 4)
        self.assertEqual(result['ko|v0']['delta_all_four_pp'], 0.)
        self.assertEqual(result['ko|v0']['descriptive_ci95_pp'], [0., 0.])

    def test_original_a_case_order_and_first_two_questions_stay990_schema(self):
        full = bundles(128); cases = d.old_cases(natural_source(), full)
        self.assertEqual(len(cases), 990)
        self.assertEqual([c['lane'] for c in cases[:768]], ['relation'] * 768)
        self.assertEqual([c['lane'] for c in cases[768:960]], ['natural'] * 192)
        self.assertTrue(all(c['question_index'] < 2 for c in cases if c['lane'] == 'relation'))

    def test_original990_reconstruction_matches_immutable_a_helper_on_synthetic_source(self):
        rows = natural_source(); parents = {s: [b['parent_bundle'] for b in values] for s, values in self.bundles.items()}
        expected = d.base.evaluation_cases(rows, parents)
        actual = d.old_cases(rows, self.bundles)
        self.assertEqual(actual, expected)
        self.assertEqual(d.old_input_proof(actual, self.tok), d.base.evaluation_input_proof(expected, self.tok))

    def test_immutable_emit_metadata_matches_new_validator_without_model_or_generation(self):
        class Decoder(CharTokenizer):
            def decode(self, ids, skip_special_tokens=False):
                special = {3: '<|im_start|>', 4: '<|im_end|>'}
                return ''.join('' if skip_special_tokens and t in special else special[t] if t in special else chr(t - 1000) for t in ids)
        tok = Decoder(); messages = [dict(role='user', content='Synthetic question')]
        cfg = NS(max_seq_len=1024); forbidden_forward = Mock(side_effect=AssertionError('actual model forward forbidden'))
        def sample(model, config, capture, prompt, **kwargs):
            self.assertEqual(kwargs['max_new'], 128); self.assertEqual(kwargs['temperature'], 0.)
            ids = tok.encode(prompt).ids + tok.encode('민수').ids + [4]
            capture.decode(ids)
            return 'ignored', dict(generated_tokens=3, finish_reason='STOP_SEQUENCE', max_new=128,
                stop_token_sequences=[[4]], matched_stop_sequence=[4])
        generation_module = importlib.import_module('tinylm.infer.generate')
        with patch.object(generation_module, 'sample', side_effect=sample) as generation:
            answer, meta = d.base.emit_answer(forbidden_forward, cfg, tok, messages)
        self.assertEqual(answer, '민수'); d.validate_generation(answer, meta, messages, tok)
        generation.assert_called_once(); forbidden_forward.assert_not_called()
        self.assertFalse(torch.cuda.is_initialized())


class BudgetIdentityAndCLITests(Guarded):
    def cost_fixture(self):
        self.paths(); info = dict(code_sha256={'fixture': 'CODE'})
        self.stub(d, 'info', lambda: info); self.stub(d, 'digest', lambda path: 'HASH')
        report = dict(status='COST8_COMPLETE', arm='ce', mode='CE', weight=0., updates=8,
            code_sha256=info['code_sha256'], corpus_sha256='HASH', initial_core_sha256=d.PARENT_CORE,
            checkpoint_written=False, actual_optimizer_groups=group_receipt(),
            event_manifest=dict(rows=8, lineage=dict(tag=d.TAG, arm='ce', mode='CE')),
            step_seconds=[9.] + [2.] * 7, grad_max=.7, clip_events=0,
            totals=dict(assistant_targets=128, relation_questions=64, crossed_rows=192))
        events = [dict(update=i + 1, step_seconds=report['step_seconds'][i], lambda_weight=0., correct_ce=2., native_ce=3.,
            gradient_norm=.7, assistant_targets=16, relation_questions=8, row_contrast=0.) for i in range(8)]
        self.stub(d, 'read_shards', Mock(return_value=events))
        return report, events

    def test_cost_report_exact8_raw_denominators_gradient_and_source_guards(self):
        report, events = self.cost_fixture(); self.assertEqual(d.verify_training_report(report, 'ce', {}, True), events)
        for field, value in dict(arm='all_axes', updates=7, mode='ALL_AXES', weight=.1, code_sha256={},
                initial_core_sha256='wrong', checkpoint_written=True, actual_optimizer_groups=[], grad_max=1.).items():
            bad = copy.deepcopy(report); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): d.verify_training_report(bad, 'ce', {}, True)
        bad = copy.deepcopy(events); bad[1]['update'] = 1; d.read_shards.return_value = bad
        with self.assertRaises(ValueError): d.verify_training_report(report, 'ce', {}, True)

    def test_budget_requires_all_three_actual_costs_and_reserves_eval_records(self):
        self.paths(); self.stub(d, 'verify_training_report', Mock(return_value=[]))
        self.stub(d, 'digest', lambda path: 'HASH')
        def report(path): return dict(step_seconds=[99.] + [2.] * 7, whole_seconds=10., actual_optimizer_groups=group_receipt())
        self.stub(d, 'stage_report', report)
        result = d.budget(now=d.END - timedelta(hours=5), frozen={})
        self.assertEqual(set(result['training_forecasts']), set(d.ARMS))
        self.assertEqual(result['future_seconds'], 3 * (2 * 896 + 600) + 5400 + 3600)
        self.assertEqual(result['total_study_forecast_seconds'], result['future_seconds'] + 30)
        self.assertEqual(result['record_reserve_seconds'], 3600)
        with self.assertRaises(d.Pending): d.budget(now=d.END - timedelta(hours=3), frozen={})
        with self.assertRaises(ValueError): d.budget(9., frozen={})

    def test_completed_training_not_counted_as_zero_or_reserved_twice(self):
        self.paths(); self.stub(d, 'verify_training_report', Mock(return_value=[])); self.stub(d, 'digest', lambda path: 'HASH')
        path = d.EVIDENCE / 'train_ce/report.json'; path.parent.mkdir(parents=True); path.write_text('{}')
        self.stub(d, 'stage_report', lambda p: dict(step_seconds=[99.] + [2.] * 7,
            whole_seconds=2000. if Path(p) == path else 10., actual_optimizer_groups=group_receipt()))
        result = d.budget(now=d.END - timedelta(hours=5), frozen={})
        self.assertEqual(result['completed_training_seconds'], dict(ce=2000.))
        self.assertEqual(set(result['pending_training_forecasts']), {'role_only', 'all_axes'})
        self.assertEqual(result['total_study_forecast_seconds'], result['future_seconds'] + 2000 + 30)

    def test_deadline_immutable_helpers_and_missing_native_supply(self):
        self.assertIs(d.safe, d.base.safe); self.assertIs(d.make_optimizers, d.base.make_optimizers)
        self.assertEqual(d.END.isoformat(), '2026-10-20T08:00:00+00:00')
        with self.assertRaises(d.Pending): d.authority(now=d.END)
        with self.assertRaises(ValueError): d.authority(now=d.END.replace(tzinfo=None))
        with self.assertRaises(ValueError): d.native_offsets(1024)
        with patch.object(d, 'authority', return_value=6001):
            self.assertEqual(d.bounded_wall(7200, reserve=3600), 2401)
        with patch.object(d, 'authority', return_value=3659):
            with self.assertRaises(d.Pending): d.bounded_wall(7200, reserve=3600)

    def test_check_only_all_modes_no_source_or_model_and_execute_dispatch(self):
        self.stub(d, 'info', lambda: dict(tag=d.TAG)); callbacks = {}
        for name in ('prepare', 'preflight', 'run', 'evaluate', 'readback', 'budget', 'probe_old'):
            callbacks[name] = self.stub(d, name, Mock(return_value={} if name == 'budget' else 0))
        args = dict(prepare=[], preflight=[], cost=['--arm', 'ce'], train=['--arm', 'all_axes'],
            evaluate=['--endpoint', 'role_only'], readback=[], budget=[], probe_old=['--model', 'contrast'])
        with redirect_stdout(io.StringIO()):
            for mode, extra in args.items(): self.assertEqual(d.main(['--mode', mode, *extra, '--check-only']), 0)
            for callback in callbacks.values(): callback.assert_not_called()
            for mode, extra in args.items(): self.assertEqual(d.main(['--mode', mode, *extra, '--execute']), 0)
        self.assertEqual(callbacks['run'].call_count, 2)
        self.assertEqual(callbacks['run'].call_args.args[-1], 8.)
        callbacks['evaluate'].assert_called_once_with('role_only', 7200)
        callbacks['probe_old'].assert_called_once_with('contrast', 7200)

    def test_cli_conflicting_roles_bounds_and_pending_are_explicit(self):
        with redirect_stderr(io.StringIO()):
            for args in (['--mode', 'cost', '--execute'], ['--mode', 'evaluate', '--execute'],
                ['--mode', 'prepare', '--arm', 'ce', '--check-only'], ['--mode', 'prepare', '--execute', '--check-only'],
                ['--mode', 'probe_old', '--endpoint', 'ce', '--execute'], ['--mode', 'budget', '--budget-hours', '9', '--execute']):
                with self.assertRaises(SystemExit): d.main(args)
        with patch.object(d, 'prepare', side_effect=d.Pending('missing')), redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'prepare', '--execute']), 8)

    def test_missing_original_a_readback_never_admits_model_or_gpu(self):
        self.stub(d, 'stage_report', Mock(side_effect=d.Pending('original readback not run')))
        with self.assertRaises(d.Pending): d.old_a_binding({}, {}, CharTokenizer())
        d.load_parent.assert_not_called(); d.emit_answer.assert_not_called()

    def test_fresh_process_help_and_check_only_use_no_source(self):
        script = ROOT / 'scripts/diag_p106b_subject_role.py'
        for args in (['--help'], ['--mode', 'prepare', '--check-only'], ['--mode', 'cost', '--arm', 'ce', '--check-only']):
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(script), *args], cwd=ROOT,
                stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


class SourceAndRawIdentityTests(Guarded):
    def source_fixture(self):
        self.paths(); self.derived = bundles(); self.raw = copy.deepcopy(self.derived); self.store = {}
        self.stub(d, 'RELATION_COUNTS', {s: len(v) for s, v in self.derived.items()})
        self.stub(d, 'info', lambda: dict(code_sha256={'fixture': 'CODE'}, code_complete=True, tag=d.TAG))
        self.stub(d, 'digest', lambda path: 'HASH')
        binding = dict(source='PINNED_A_AND_NATURAL')
        self.stub(d, 'source_inputs', Mock(return_value=({}, {}, self.derived, binding)))
        self.stub(d, 'stage_report', lambda path: copy.deepcopy(self.store[Path(path)]))
        self.stub(d, 'read_shards', lambda directory, manifest, stem, expected: copy.deepcopy(self.raw[stem]))
        manifests = {s: dict(rows=len(v), lineage=dict(tag=d.TAG, split=s, source_binding=binding)) for s, v in self.derived.items()}
        offsets = d.native_offsets()
        report = dict(d.info(), status='SUBJECT_ROLE_CPU_VERIFIED', source_binding=binding, schedules=d.schedule_proof(),
            manifests=manifests, native_train_offsets=offsets, native_train_offsets_sha256=d.natural_data.sha(offsets))
        report['ranking_specifications'] = d.rank_specifications(self.derived['test'], CharTokenizer())
        report['ranking_specifications_sha256'] = d.natural_data.sha(report['ranking_specifications'])
        self.store[d.CORPUS / 'report.json'] = report
        self.store[d.EVIDENCE / 'cpu_contract.json'] = {k: copy.deepcopy(v) for k, v in report.items() if k not in ('manifests', 'native_train_offsets')}
        self.store[d.EVIDENCE / 'cpu_contract.json']['corpus_report_sha256'] = 'HASH'
        return report

    def test_prepared_uses_exact_derived_parent_and_new7168_vector(self):
        report = self.source_fixture(); result = READ_PREPARED()
        self.assertEqual(result[0], report); self.assertIs(result[2], self.derived)
        self.assertEqual(len(result[0]['native_train_offsets']), 7168)
        d.load_parent.assert_not_called(); d.emit_answer.assert_not_called()

    def test_prepared_code_source_native_hash_or_manifest_label_tamper_refused(self):
        original = self.source_fixture()
        for field, value in dict(code_sha256={}, source_binding={}, schedules=[], native_train_offsets=[0] * 7168,
                native_train_offsets_sha256='WRONG', ranking_specifications_sha256='WRONG', ranking_specifications={}).items():
            changed = copy.deepcopy(original); changed[field] = value
            self.store[d.CORPUS / 'report.json'] = changed
            with self.subTest(field=field), self.assertRaises(ValueError): READ_PREPARED()
        self.store[d.CORPUS / 'report.json'] = copy.deepcopy(original)
        self.store[d.CORPUS / 'report.json']['manifests']['train']['lineage']['tag'] = 'other'
        with self.assertRaises(ValueError): READ_PREPARED()

    def test_resigned_raw_gold_and_missing_public_contract_are_rejected(self):
        self.source_fixture(); self.raw['train'][0]['answers'][0] = 'WRONG'
        with self.assertRaises(ValueError): READ_PREPARED()
        self.raw = copy.deepcopy(self.derived)
        self.store[d.EVIDENCE / 'cpu_contract.json']['corpus_report_sha256'] = 'OTHER'
        with self.assertRaises(ValueError): READ_PREPARED()

    def test_actual_small_shard_missing_duplicate_source_and_byte_tamper(self):
        from scripts.p106b_shards import ShardWriter
        root = self.paths(); self.stub(d, 'safe', lambda path: Path(path))
        directory = root / 'raw'; writer = ShardWriter(directory, 'answers')
        writer.append(dict(id='fixture')); manifest = writer.close(lineage=dict(tag=d.TAG))
        self.assertEqual(READ_SHARDS(directory, manifest, 'answers', 1), [dict(id='fixture')])
        with self.assertRaises(d.Pending): READ_SHARDS(directory, manifest, 'answers', 2)
        changed = copy.deepcopy(manifest); changed['rows'] = 2
        with self.assertRaises(ValueError): READ_SHARDS(directory, changed, 'answers', 2)
        raw = directory / manifest['shards'][0]['path']; raw.write_text('{"id":"tampered"}\n')
        with self.assertRaises(ValueError): READ_SHARDS(directory, manifest, 'answers', 1)

    def test_evaluation_identity_rejects_wrong_endpoint_checkpoint_body_or_manifest(self):
        self.paths(); self.stub(d, 'digest', lambda path: 'HASH')
        self.stub(d, 'info', lambda: dict(code_sha256={'fixture': 'CODE'}))
        identity = dict(endpoint='ce', checkpoint='child.pt', checkpoint_sha256='P' * 64,
            expected_core_sha256='C' * 64, training_report_sha256='T' * 64)
        lineage = dict(tag=d.TAG, **identity); cases = [dict(id='fixture')]
        report = dict(status='ACTUAL_FIRST_ANSWERS_RECORDED', endpoint='ce', lineage=lineage,
            code_sha256={'fixture': 'CODE'}, corpus_sha256='HASH', cases_sha256=d.natural_data.sha(cases),
            core_before='C' * 64, core_after='C' * 64, answer_manifest=dict(lineage=lineage), rank_manifest=dict(lineage=lineage),
            model_training=False, weights_changed=False)
        d.validate_evaluation(report, identity, cases, {})
        for key, value in dict(endpoint='all_axes', code_sha256={}, corpus_sha256='wrong', core_before='wrong', core_after='wrong',
                rank_manifest=dict(lineage={}), answer_manifest=dict(lineage={}), model_training=True).items():
            changed = copy.deepcopy(report); changed[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError): d.validate_evaluation(changed, identity, cases, {})


if __name__ == '__main__': unittest.main(verbosity=2)
