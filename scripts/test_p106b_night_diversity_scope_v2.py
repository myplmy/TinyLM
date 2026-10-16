"""새 예산 범위의 합성 CPU 회귀. 실물 자료나 모델을 읽지 않는다."""
from __future__ import annotations
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_diversity_scope_v2 as d


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest().upper()


def courses():
    r = NS(x_tokens=10, targets=2, x=[7] * 10, y=[-100] * 8 + [9, 4], segments=[0] * 8 + [1, 1])
    natural = [[r, r] for _ in range(8192)]; replay = [r] * 4096
    return [(natural, replay)] * 4


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)

    def stub(self, target, name, value):
        return self.stack.enter_context(patch.object(target, name, value))

    def source_fixture(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); self.stub(d, 'ROOT', root)
        self.stub(d, 'CORPUS', root / 'new' / 'corpus'); self.stub(d, 'EVIDENCE', root / 'evidence')
        self.store = {}; self.courses = courses(); self.expanded = dict(train=[dict(root='train')], dev=[], test=[])
        self.tok = NS(to_str=lambda: 'synthetic-tokenizer')
        old = dict(status='DIVERSITY_CPU_FROZEN', code_sha256={'old': 'CODE'},
            actual_parent_loaded_cpu=True, cuda_initialized=False, padding=[0, 4],
            first160_actual_x_y_equal=True, checkpoints_written=0, optimizer_updates=0,
            initial_core_sha256='A' * 64, manifests={'train': {'rows': 32768}},
            source_contract={'source': 'synthetic'}, inventory={'unique': 32768},
            actual_exposure=dict(rows=81920, x_tokens=819200, assistant_targets=163840),
            schedules=[{'quarter': i + 1, 'updates': 160} for i in range(4)], same_replay_sha256='REPLAY')
        original = NS(CORPUS=root / 'original' / 'corpus', EVIDENCE=root / 'original_evidence',
            info=lambda: dict(code_sha256={'old': 'CODE'}),
            read_source=Mock(return_value=(old, self.expanded, self.tok, self.courses, {'qa': 'original'})))
        self.stub(d, 'original_driver', original)
        data = NS(PARENT=root / 'parent.pt', PARENT_SHA='PARENT', QA_REPORT='qa/report.json', LOCKED_QA_SHA='QA')
        self.stub(d, 'foundation', NS(data=data))
        self.stub(d, 'qa', NS(data=NS(digest=lambda p: 'DIGEST', sha=sha),
            required=lambda p: deepcopy(self.store[p]), write=lambda p, obj: self.store.__setitem__(p, deepcopy(obj))))
        self.stub(d, 'core_equivalence', lambda: {'run': {'ast_equal': True, 'character_equal': True}})
        self.stub(d, 'info', lambda: dict(code_sha256={'new': 'CODE'}, tag=d.TAG))
        binding = d._source_binding(old, self.expanded, self.courses)
        report = dict(d.info(), **binding, status='DIVERSITY_CPU_FROZEN', actual_parent_loaded_cpu=True,
            cuda_initialized=False, padding=[0, 4], actual_padded_shape=[8, 1024],
            initializer_sha256='PARENT', initializer='parent.pt', first160_actual_x_y_equal=True,
            source_corpus='original/corpus', source_rewritten=False, model_forward=False,
            checkpoints_written=0, optimizer_updates=0)
        self.store[d.CORPUS / 'report.json'] = report
        self.store[d.EVIDENCE / 'cpu_contract.json'] = deepcopy(report)
        self.original = original
        return report

    def cost_fixture(self):
        total, updates = d._first8(courses())
        proof = dict(cost8_expected=total, cost8_updates=updates, initial_core_sha256='BODY')
        report = dict(total, status='DIVERSITY_COST_COMPLETE', updates=8, tag=d.TAG,
            code_sha256={'new': 'CODE'}, cpu_contract_sha256='CPU', initializer_sha256=d.foundation.data.PARENT_SHA,
            initial_core_sha256='BODY', actual_oom=False, checkpoint_written=False,
            event_manifest=dict(rows=8, shards=[]), step_seconds=[20.] + [2.] * 7)
        events = [dict(row, ce=3., grad=.8, step_seconds=report['step_seconds'][i]) for i, row in enumerate(updates)]
        self.stub(d, 'info', lambda: dict(code_sha256={'new': 'CODE'}))
        self.stub(d, 'qa', NS(data=NS(digest=lambda p: 'CPU')))
        self.stub(d, '_cost_events', Mock(return_value=events))
        return proof, report, events

    def test_independent_namespace_and_paths(self):
        self.assertEqual(d.TAG, 'p106b_night_diversity_scope_v2_s1337')
        self.assertNotEqual(d.CORPUS, d.original_driver.CORPUS)
        self.assertNotEqual(d.EVIDENCE, d.original_driver.EVIDENCE)
        self.assertNotEqual(d.checkpoint(), d.original_driver.checkpoint())
        self.assertNotEqual(d.checkpoint(), d.checkpoint(True))

    def test_ast_and_character_core_equal(self):
        proof = d.core_equivalence()
        self.assertEqual(set(proof), {'checkpoint', 'completed', 'save', 'run'})
        self.assertTrue(all(p['ast_equal'] and p['character_equal'] for p in proof.values()))

    def test_core_math_optimizer_and_selection_mutations_rejected(self):
        source = Path(d.__file__).read_text(encoding='utf-8')
        for old, new in (('loss = values[0] / denom', 'loss = values[0] / (denom + 1)'),
                ('adam.step(); muon.step()', 'muon.step(); adam.step()'),
                ("entry['dev']['ce'] < best_ce", "entry['dev']['ce'] <= best_ce")):
            self.assertIn(old, source)
            with self.assertRaises(ValueError): d.core_equivalence(candidate_source=source.replace(old, new))

    def test_comment_only_core_mutation_rejected_by_character_hash(self):
        source = Path(d.__file__).read_text(encoding='utf-8')
        with self.assertRaises(ValueError):
            d.core_equivalence(candidate_source=source.replace('adam.step(); muon.step(); steps += 1',
                'adam.step(); muon.step(); steps += 1  # 다른 문자'))

    def test_source_calls_original_collector_and_returns_same_courses(self):
        report = self.source_fixture()
        result = d.read_source()
        self.original.read_source.assert_called_once_with()
        self.assertEqual(result[0], report)
        self.assertIs(result[1], self.expanded); self.assertIs(result[2], self.tok)
        self.assertIs(result[3], self.courses); self.assertEqual(result[4], {'qa': 'original'})

    def test_changed_original_binding_and_new_code_rejected(self):
        report = self.source_fixture()
        for key, value in (('original_cpu_sha256', 'OTHER'), ('actual_exposure', {}),
                ('schedules', []), ('initial_core_sha256', 'B' * 64), ('actual_split_sha256', {}),
                ('code_sha256', {'new': 'OTHER'}), ('source_rewritten', True), ('actual_padded_shape', [1, 1024])):
            broken = deepcopy(report); broken[key] = value
            self.store[d.CORPUS / 'report.json'] = broken
            self.store[d.EVIDENCE / 'cpu_contract.json'] = deepcopy(broken)
            with self.assertRaises(ValueError): d.read_source()

    def test_cpu_evidence_copy_must_match(self):
        self.source_fixture(); self.store[d.EVIDENCE / 'cpu_contract.json']['optimizer_updates'] = 1
        with self.assertRaises(ValueError): d.read_source()

    def test_prepare_strict_parent_and_actual_pad_without_forward(self):
        self.source_fixture(); self.store.clear()
        from tinylm.train import mtp_sft as core
        torch = NS(cuda=NS(is_initialized=lambda: False)); model = NS(forward=Mock())
        loader = Mock(return_value=(torch, model, None, self.tok, 'A' * 64,
            d.foundation.data.PARENT, d.foundation.data.PARENT_SHA))
        d.foundation.load_foundation_parent = loader
        shape = NS(shape=(8, 1024)); pad = Mock(return_value=(shape, shape, shape))
        self.stub(core, 'pad_records', pad)
        self.stub(d, 'previous', NS(deadline=Mock(), special_ids=lambda tok: (0, 4, '<pad>'),
            denominators=d.previous.denominators, micro_records=d.previous.micro_records))
        d.prepare()
        loader.assert_called_once_with('base_qa'); model.forward.assert_not_called()
        self.assertEqual(pad.call_args.kwargs, dict(fixed_width=1024, batch_size=8))
        self.assertEqual(self.store[d.CORPUS / 'report.json']['actual_padded_shape'], [8, 1024])
        self.assertEqual(len(self.store), 2)

    def test_prepare_rejects_wrong_actual_parent(self):
        self.source_fixture(); self.store.clear()
        d.foundation.load_foundation_parent = Mock(return_value=(None, None, None, self.tok, 'B' * 64,
            d.foundation.data.PARENT, d.foundation.data.PARENT_SHA))
        self.stub(d, 'previous', NS(deadline=Mock(), denominators=d.previous.denominators,
            micro_records=d.previous.micro_records))
        with self.assertRaises(ValueError): d.prepare()
        self.assertFalse(self.store)

    def test_cost8_counts_actual_rows_and_whole_update_targets(self):
        expected, updates = d._first8(courses())
        self.assertEqual(expected['padded_slots'], 1048576)
        self.assertEqual(expected['native_x_tokens'], 65536)
        self.assertEqual(expected['actual_x_tokens'], 10240)
        self.assertEqual(expected['assistant_targets'], 2048)
        self.assertEqual(updates[-1]['updates'], 8)

    def test_new_cost8_success_and_exact_event_recount(self):
        proof, report, _ = self.cost_fixture()
        self.assertEqual(d.cost_forecast(report, proof), 1880.)
        d._cost_events.assert_called_once_with(report)

    def test_old_partial_nonfinite_or_wrong_cost_never_opens(self):
        proof, report, _ = self.cost_fixture()
        for change in (dict(tag='old'), dict(status='ERROR'), dict(updates=7),
                dict(code_sha256={'old': 'CODE'}), dict(cpu_contract_sha256='OLD'),
                dict(initializer_sha256='OTHER'), dict(initial_core_sha256='OTHER'),
                dict(actual_oom=True), dict(checkpoint_written=True), dict(assistant_targets=1),
                dict(event_manifest={'rows': 7}), dict(step_seconds=[float('nan')] + [2.] * 7),
                dict(step_seconds=[1.] * 7), dict(step_seconds=[True] * 8)):
            with self.assertRaises(ValueError): d.cost_forecast(dict(report, **change), proof)

    def test_cost_event_missing_duplicate_or_timing_mutation_rejected(self):
        proof, report, events = self.cost_fixture()
        for bad in (events[:-1], [events[0]] * 8,
                [dict(e, x=0) for e in events], [dict(e, step_seconds=99) for e in events],
                [dict(e, ce=float('inf')) for e in events]):
            d._cost_events.return_value = bad
            with self.assertRaises(ValueError): d.cost_forecast(report, proof)

    def test_budget_excludes_hold_and_falcon_without_legacy_credit(self):
        self.stub(d, 'qa', NS(required=lambda p: {}, TRAIN_STOP=d.qa.TRAIN_STOP))
        self.stub(d, 'cost_forecast', lambda report, proof: 2000.)
        self.stub(d, 'pending_prompt_training', lambda: ({'prompt01': 2500.}, ['prompt0']))
        self.stub(d, 'pending_trained_evaluations', lambda: (['cpt_qa_best'], ['base_qa', 'base_qa_best', 'cpt_qa']))
        result = d.budget({}, now=d.qa.TRAIN_STOP - timedelta(seconds=20000))
        self.assertEqual(result['needed_seconds'], 2000 + 2500 + 6 * 900 + 2 * 900 + 900 + 600)
        self.assertFalse(result['legacy_gate_credited'])
        self.assertEqual(result['verified_completed_prompt_arms'], ['prompt0'])
        self.assertTrue(all(x['seconds'] == 0 for x in result['excluded_reservations'].values()))
        self.assertEqual(result['excluded_reservations']['bare_full512']['status'], 'HOLD_NOT_COMPLETE')

    def test_budget_equal_or_after_stop_rejected(self):
        self.stub(d, 'qa', NS(required=lambda p: {}, TRAIN_STOP=d.qa.TRAIN_STOP))
        self.stub(d, 'cost_forecast', lambda report, proof: 2000.)
        self.stub(d, 'pending_prompt_training', lambda: ({}, ['prompt0', 'prompt01']))
        self.stub(d, 'pending_trained_evaluations', lambda: ([], list(d.TRAINED_ENDPOINTS)))
        needed = 2000 + 5400 + 1800 + 600
        for seconds in (needed, 0, -1):
            with self.assertRaises(ValueError): d.budget({}, now=d.qa.TRAIN_STOP - timedelta(seconds=seconds))

    def test_prompt_budget_retains_validated_900_margin(self):
        proof = dict(initial_core_sha256='BODY', update_exposure=[dict(x=10, assistant_targets=2,
            prompt_targets=3, content_targets=1)] * 8)
        report = dict(status='PROMPT_COST_COMPLETE', arm='prompt01', beta=.1,
            cpu_contract_sha256='CPU', source_qa_sha256=d.foundation.data.LOCKED_QA_SHA,
            initializer_sha256=d.foundation.data.PARENT_SHA, initial_core_sha256='BODY',
            actual_x_tokens=80, assistant_targets=16, prompt_targets=24, content_targets=8,
            native_x_tokens=65536, padded_slots=1048576, event_manifest={'rows': 8},
            updates=8, actual_oom=False, checkpoint_written=False, code_sha256={'prompt': 'CODE'},
            step_seconds=[20.] + [2.] * 7)
        other = NS(read_source=lambda: (proof,), ARMS=('prompt0', 'prompt01'), BETAS=dict(prompt0=0., prompt01=.1),
            completed_prompt=Mock(side_effect=lambda arm, p: arm == 'prompt0'),
            EVIDENCE=Path('/synthetic/prompt'), CORPUS=Path('/synthetic/prompt/corpus'),
            cost_estimate=d.other.cost_estimate, info=lambda: dict(code_sha256={'prompt': 'CODE'}),
            budget=Mock(side_effect=AssertionError('옛 예산 호출 금지')))
        self.stub(d, 'other', other)
        self.stub(d, 'qa', NS(required=lambda p: report, data=NS(digest=lambda p: 'CPU')))
        self.stub(d, 'verify', Mock())
        remaining, completed = d.pending_prompt_training()
        self.assertEqual(remaining, {'prompt01': 2180.}); self.assertEqual(completed, ['prompt0'])
        other.budget.assert_not_called()
        report['cpu_contract_sha256'] = 'OLD'
        with self.assertRaises(ValueError): d.pending_prompt_training()

    def test_trained_presence_not_credit_and_receipt_mismatch_rejected(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup); root = Path(temporary.name)
        self.stub(d, 'ROOT', root)
        for endpoint in d.TRAINED_ENDPOINTS: (root / (endpoint + '_report.json')).touch()
        outputs = {'natural': {'counts': {'n': 1}}}
        reports = {endpoint: dict(code_sha256={'eval': 'CODE'}, input_report_sha256='SHA',
            checkpoint=endpoint + '.pt', checkpoint_sha256='SHA', outputs=outputs,
            receipt_sha256={'natural': 'SHA'}) for endpoint in d.TRAINED_ENDPOINTS}
        self.stub(d, 'qa', NS(required=lambda p: reports[p.name.removesuffix('_report.json')],
            data=NS(digest=lambda p: 'SHA')))
        evaluation = NS(EVIDENCE=root, FROZEN=root / 'frozen', OUTPUTS={'natural'},
            read_inputs=lambda: ({}, {}, {'natural': []}), endpoint_contract=Mock(),
            checkpoint_spec=lambda endpoint: (root / (endpoint + '.pt'), 'SHA'),
            info=lambda: dict(code_sha256={'eval': 'CODE'}),
            receipt_path=lambda endpoint, lane: root / endpoint / (lane + '.json'),
            read_receipt=Mock(return_value={'output': outputs['natural']}))
        self.assertEqual(d.pending_trained_evaluations(evaluation), ([], list(d.TRAINED_ENDPOINTS)))
        self.assertEqual(evaluation.read_receipt.call_count, 4)
        evaluation.read_receipt.return_value = {'output': {'changed': True}}
        with self.assertRaises(ValueError): d.pending_trained_evaluations(evaluation)
        evaluation.endpoint_contract.side_effect = ValueError('부분 보고서')
        with self.assertRaises(ValueError): d.pending_trained_evaluations(evaluation)

    def test_missing_trained_evaluations_stay_reserved(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        checkpoint_spec = Mock(side_effect=lambda endpoint: (Path(temporary.name) / (endpoint + '.pt'), 'SHA'))
        digest = Mock(return_value='SHA')
        self.stub(d, 'qa', NS(data=NS(digest=digest)))
        evaluation = NS(EVIDENCE=Path(temporary.name), read_inputs=lambda: ({}, {}, {}), checkpoint_spec=checkpoint_spec)
        self.assertEqual(d.pending_trained_evaluations(evaluation), (list(d.TRAINED_ENDPOINTS), []))
        self.assertEqual([call.args[0] for call in checkpoint_spec.call_args_list], list(d.TRAINED_ENDPOINTS))
        self.assertEqual(digest.call_count, 4)

    def test_absent_eval_report_cannot_hide_missing_checkpoint(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup); root = Path(temporary.name)
        evaluation = NS(EVIDENCE=root, read_inputs=Mock(return_value=({}, {}, {})),
            checkpoint_spec=lambda endpoint: (root / (endpoint + '.pt'), 'SHA'))
        def digest(path):
            if path.name == 'cpt_qa.pt': raise FileNotFoundError('합성 체크포인트 없음')
            return 'SHA'
        self.stub(d, 'qa', NS(data=NS(digest=digest)))
        with self.assertRaises(FileNotFoundError): d.pending_trained_evaluations(evaluation)
        evaluation.read_inputs.assert_not_called()

    def test_absent_eval_report_cannot_hide_changed_final_or_best_checkpoint(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup); root = Path(temporary.name)
        evaluation = NS(EVIDENCE=root, read_inputs=Mock(return_value=({}, {}, {})),
            checkpoint_spec=lambda endpoint: (root / (endpoint + '.pt'), 'SHA'))
        for endpoint in d.TRAINED_ENDPOINTS:
            with self.subTest(endpoint=endpoint), patch.object(d, 'qa', NS(data=NS(
                    digest=lambda path: 'CHANGED' if path.name == endpoint + '.pt' else 'SHA'))):
                with self.assertRaises(ValueError): d.pending_trained_evaluations(evaluation)
        evaluation.read_inputs.assert_not_called()

    def test_absent_eval_report_cannot_hide_unfinished_training(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup); root = Path(temporary.name)
        self.stub(d, 'qa', NS(data=NS(digest=lambda path: 'SHA')))
        for unfinished in d.TRAINED_ENDPOINTS:
            def checkpoint_spec(endpoint):
                if endpoint == unfinished: raise ValueError('합성 학습 미완료')
                return root / (endpoint + '.pt'), 'SHA'
            evaluation = NS(EVIDENCE=root, read_inputs=Mock(return_value=({}, {}, {})), checkpoint_spec=checkpoint_spec)
            with self.subTest(endpoint=unfinished), self.assertRaises(ValueError):
                d.pending_trained_evaluations(evaluation)
            evaluation.read_inputs.assert_not_called()

    def test_budget_stays_closed_when_any_required_training_is_incomplete(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        evaluation = NS(EVIDENCE=Path(temporary.name), read_inputs=Mock(),
            checkpoint_spec=Mock(side_effect=ValueError('합성 CPTQA 학습 미완료')))
        check_pending = d.pending_trained_evaluations
        self.stub(d, 'qa', NS(required=lambda p: {}, TRAIN_STOP=d.qa.TRAIN_STOP))
        self.stub(d, 'cost_forecast', lambda report, proof: 2000.)
        self.stub(d, 'pending_prompt_training', lambda: ({}, []))
        self.stub(d, 'pending_trained_evaluations', lambda: check_pending(evaluation))
        with self.assertRaises(ValueError):
            d.budget({}, now=d.qa.TRAIN_STOP - timedelta(seconds=50000))
        evaluation.read_inputs.assert_not_called()

    def test_no_imported_global_reassignment_or_old_budget_call(self):
        import ast
        tree = ast.parse(Path(d.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertFalse(isinstance(node.func.value, ast.Name) and node.func.value.id == 'other' and node.func.attr == 'budget')
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self.assertFalse(isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                        and target.value.id in ('original_driver', 'other', 'evaluation', 'data', 'foundation', 'previous'))


if __name__ == '__main__': unittest.main()
