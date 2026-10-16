"""새 평가 경로와 동결 원형 계약의 합성 CPU 회귀."""
from __future__ import annotations
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_diversity_scope_eval_v2 as d


class ScopeEvalTests(unittest.TestCase):
    def test_independent_paths_and_same_two_endpoints(self):
        self.assertEqual(d.ENDPOINTS, ('unique32k', 'unique32k_best'))
        self.assertEqual(d.training.TAG, 'p106b_night_diversity_scope_v2_s1337')
        self.assertEqual(d.FROZEN, d.training.CORPUS.parent / 'evaluation')
        self.assertIn(d.training.TAG, str(d.LOCAL)); self.assertIn(d.training.TAG, str(d.EVIDENCE))
        self.assertNotEqual(d.FROZEN, d.evaluation.FROZEN)
        with self.assertRaises(ValueError): d.checkpoint_spec('base_parent')

    def test_all_reader_eval_functions_exact_original_ast_and_characters(self):
        original = (ROOT / 'scripts/diag_p106b_night_diversity_eval.py').read_text(encoding='utf-8')
        candidate = Path(d.__file__).read_text(encoding='utf-8')
        def functions(source):
            return {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        left, right = functions(original), functions(candidate)
        self.assertEqual(set(left), set(right))
        for name in set(left) - {'info'}:
            self.assertEqual(ast.dump(left[name], include_attributes=False), ast.dump(right[name], include_attributes=False), name)
            self.assertEqual(ast.get_source_segment(original, left[name]), ast.get_source_segment(candidate, right[name]), name)

    def test_info_only_schema_and_explicit_precision_metadata_change(self):
        original = (ROOT / 'scripts/diag_p106b_night_diversity_eval.py').read_text(encoding='utf-8')
        candidate = Path(d.__file__).read_text(encoding='utf-8')
        def node(source):
            return next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'info')
        left = node(original); right = node(candidate)
        call = right.body[0].value
        precision = next(k for k in call.keywords if k.arg == 'precision_by_lane')
        values = {k.arg: k.value.value for k in precision.value.keywords}
        self.assertEqual(values['native32'], 'CUDA_BF16_AUTOCAST_EXISTING_HELPER')
        self.assertEqual(values['native256'], 'FP32_MATH')
        self.assertEqual(len(values), 8)
        call.keywords.remove(precision)
        for n in ast.walk(right):
            if isinstance(n, ast.Constant) and n.value == 'P106B_NIGHT_DIVERSITY_SCOPE_EVALUATION_V2':
                n.value = 'P106B_NIGHT_DIVERSITY_ACTUAL_EVALUATION_V1'
        self.assertEqual(ast.dump(left, include_attributes=False), ast.dump(right, include_attributes=False))

    def report(self):
        outputs = {lane: dict(counts={'n': 1}, manifest=dict(rows=1, shards=[{'path': 'fixture'}])) for lane in d.evaluation.OUTPUTS}
        return dict(status='ACTUAL_EVALUATION_COMPLETE', endpoint='unique32k', updates=0,
            checkpoints_written=0, body_unchanged=True,
            directory=str((d.LOCAL / 'unique32k').relative_to(ROOT)), outputs=outputs,
            receipt_sha256={lane: 'SHA' for lane in outputs})

    def test_eight_lanes_and_complete_no_updates_contract(self):
        r = self.report()
        self.assertEqual(set(r['outputs']), {'natural', 'cube', 'role', 'recovery', 'code', 'public', 'native32', 'native256'})
        with patch.object(d, 'evaluation', NS(OUTPUTS=set(r['outputs']), native_contract=Mock())):
            d.endpoint_contract(r, 'unique32k', {})
            for change in (dict(updates=1), dict(checkpoints_written=1), dict(body_unchanged=False),
                    dict(outputs={}), dict(receipt_sha256={}), dict(endpoint='base_qa'), dict(directory='old')):
                with self.assertRaises(ValueError): d.endpoint_contract(dict(r, **change), 'unique32k', {})
            broken = deepcopy(r); broken['outputs']['natural']['manifest']['rows'] = 0
            with self.assertRaises(ValueError): d.endpoint_contract(broken, 'unique32k', {})

    def test_native_units_and_source_unchanged(self):
        inputs = dict(native_val_sha256='VAL', native256_val_offsets=[5, 10])
        spec = dict(ce=3., val_sha256='VAL', crops=32, targets=32768)
        d.evaluation.native_contract('native32', spec, inputs)
        with self.assertRaises(ValueError): d.evaluation.native_contract('native32', dict(spec, targets=32), inputs)
        with self.assertRaises(ValueError): d.evaluation.native_contract('native32', dict(spec, ce=float('nan')), inputs)

    def test_checkpoint_dev_only_final_and_best(self):
        report = dict(history=[{'dev': {'ce': x}} for x in (5., 3., 3., 4.)],
            best_dev_quarter=2, best_dev_ce=3., checkpoint='runs/final.pt', checkpoint_sha256='SHA',
            final_core_sha256='FINAL', best_dev_checkpoint='runs/best.pt', best_dev_checkpoint_sha256='SHA',
            best_dev_core_sha256='BEST')
        train = NS(CORPUS=Path('/synthetic/corpus'), EVIDENCE=Path('/synthetic/evidence'),
            completed=Mock(return_value=True), checkpoint=lambda best=False: ROOT / 'runs' / ('best.pt' if best else 'final.pt'))
        qa = NS(required=lambda path: {} if path.parent == train.CORPUS else report, data=NS(digest=lambda path: 'SHA'))
        with patch.object(d, 'training', train), patch.object(d, 'qa', qa):
            self.assertEqual(d.checkpoint_spec('unique32k'), (ROOT / 'runs/final.pt', 'SHA', 'FINAL'))
            self.assertEqual(d.checkpoint_spec('unique32k_best'), (ROOT / 'runs/best.pt', 'SHA', 'BEST'))
            report['best_dev_quarter'] = 3
            with self.assertRaises(ValueError): d.checkpoint_spec('unique32k_best')
            report['best_dev_quarter'] = 2; train.completed.return_value = False
            with self.assertRaises(ValueError): d.checkpoint_spec('unique32k')

    def test_read_inputs_requires_full_case_set_same_source_and_cpu(self):
        inputs = {'counts': {'natural': 512}}; cases = {'natural': [{'root': 'fixture'}]}
        report = dict(status='DIVERSITY_EVAL_INPUTS_FROZEN', code_sha256={'code': 'SHA'},
            recovery_input_sha256='INPUT', training_cpu_sha256='CPU', actual_case_sets_sha256={'natural': 'CASES'})
        qa = NS(required=lambda p: report, data=NS(sha=lambda rows: 'CASES'))
        evaluation = NS(read_inputs=Mock(return_value=({}, inputs, cases)))
        metadata = dict(code_sha256={'code': 'SHA'}, recovery_input_sha256='INPUT', training_cpu_sha256='CPU')
        with patch.object(d, 'qa', qa), patch.object(d, 'evaluation', evaluation), patch.object(d, 'info', return_value=metadata):
            actual_inputs, actual_cases = d.read_inputs()
            self.assertIs(actual_inputs, inputs); self.assertIs(actual_cases, cases)
            report['actual_case_sets_sha256'] = {'natural': 'CHANGED'}
            with self.assertRaises(ValueError): d.read_inputs()

    def test_receipt_raw_recount_body_and_source_proofs(self):
        output = dict(manifest={'rows': 1}, counts={'n': 1})
        body = dict(status='UNCHANGED_WITHIN_THIS_LANE', initial_core_sha256='CORE', final_core_sha256='CORE')
        receipt = dict(status='LANE_COMPLETE', endpoint='unique32k', lane='natural', code_sha256={'code': 'SHA'},
            checkpoint_sha256='CKPT', initial_core_sha256='CORE', body_proof=body,
            input_report_sha256='INPUT', output=output)
        qa = NS(required=lambda p: receipt, data=NS(digest=lambda p: 'INPUT'))
        recount = Mock(return_value={'n': 1})
        evaluation = NS(body_proof=lambda *args: body, old=NS(stream=lambda *args: iter([{'fixture': True}])), recount=recount)
        with patch.object(d, 'qa', qa), patch.object(d, 'evaluation', evaluation), \
                patch.object(d, 'checkpoint_spec', return_value=(Path('/synthetic/ckpt'), 'CKPT', 'CORE')), \
                patch.object(d, 'info', return_value={'code_sha256': {'code': 'SHA'}}):
            self.assertEqual(d.read_receipt('unique32k', 'natural', {}, {}), receipt)
            recount.assert_called_once()
            recount.return_value = {'n': 0}
            with self.assertRaises(ValueError): d.read_receipt('unique32k', 'natural', {}, {})
            recount.return_value = {'n': 1}; receipt['initial_core_sha256'] = 'OTHER'
            with self.assertRaises(ValueError): d.read_receipt('unique32k', 'natural', {}, {})

    def test_readback_keeps_baseline_final_best_and_all_eight_receipts(self):
        outputs = {lane: dict(manifest={'lane': lane}) for lane in d.evaluation.OUTPUTS}
        receipts = {lane: dict(output=output) for lane, output in outputs.items()}
        def report(path):
            endpoint = path.name.removesuffix('_report.json')
            return dict(code_sha256={'code': 'SHA'}, input_report_sha256='SHA', checkpoint='runs/' + endpoint + '.pt',
                checkpoint_sha256='SHA', initial_core_sha256='CORE', outputs=outputs,
                receipt_sha256={lane: 'SHA' for lane in outputs})
        written = []
        qa = NS(required=report, data=NS(digest=lambda path: 'SHA'), write=lambda p, value: written.append(value))
        paired = Mock(side_effect=lambda left, right: {'left': left[0]['endpoint'], 'right': right[0]['endpoint']})
        evaluation = NS(OUTPUTS=set(outputs), EVIDENCE=Path('/synthetic/baseline'), FROZEN=Path('/synthetic/frozen'),
            LOCAL=Path('/synthetic/raw'), info=lambda: dict(code_sha256={'code': 'SHA'}),
            endpoint_contract=Mock(), read_receipt=Mock(side_effect=lambda endpoint, lane, cases: receipts[lane]),
            receipt_path=lambda endpoint, lane: Path('/synthetic') / endpoint / lane,
            old=NS(stream=lambda directory, manifest: iter([{'endpoint': directory.name}])), method=NS(paired_natural=paired))
        own_receipt = Mock(side_effect=lambda endpoint, lane, cases, inputs: receipts[lane])
        with patch.object(d, 'qa', qa), patch.object(d, 'evaluation', evaluation), \
                patch.object(d, 'read_inputs', return_value=({}, {})), \
                patch.object(d, 'checkpoint_spec', side_effect=lambda endpoint: (ROOT / 'runs' / (endpoint + '.pt'), 'SHA', 'CORE')), \
                patch.object(d, 'endpoint_contract'), patch.object(d, 'read_receipt', own_receipt), \
                patch.object(d, 'info', return_value={'code_sha256': {'code': 'SHA'}}):
            d.readback()
        self.assertEqual(own_receipt.call_count, 16); self.assertEqual(evaluation.read_receipt.call_count, 16)
        self.assertEqual(set(written[0]['paired']), {'base_qa__unique32k', 'base_qa_best__unique32k_best', 'unique32k__unique32k_best'})
        self.assertEqual(set(written[0]['endpoints_sha256']), {'base_qa', 'base_qa_best', 'unique32k', 'unique32k_best'})
        self.assertFalse(written[0]['learning_seed_variance_measured'])


if __name__ == '__main__': unittest.main()
