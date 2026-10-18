#!/usr/bin/env python3
"""Pure evaluation-source/body/receipt regression, no learned models."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import copy
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from scripts import diag_p106b_cpt_unique32k_eval as d


class FourthCellEvaluationTests(unittest.TestCase):
    def test_actual_admission_rechecks_remaining_and_record_reserve(self):
        for remaining, expected in ((7200.9, 3600), (3700.9, 100)):
            with patch.object(d.training, 'authority', return_value=remaining):
                self.assertEqual(d.evaluation_admission(3600), expected)
        with patch.object(d.training, 'authority', return_value=3659.9):
            with self.assertRaises(d.training.PrerequisitePending): d.evaluation_admission(3600)

    def test_inference_core_only_changes_authority(self):
        self.assertTrue(d.evaluation_core_equivalence()['ast_equal_after_authority_substitution'])

    def test_inference_core_rejects_changed_generation_path(self):
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            text = original_read(path, *args, **kwargs)
            if path == Path(d.__file__):
                return text.replace('for event in lane_events(lane, model, cfg, tok, device, cases):',
                    'for event in lane_events(lane, model, cfg, tok, device, {}):')
            return text
        with patch.object(Path, 'read_text', read):
            with self.assertRaises(ValueError):
                d.evaluation_core_equivalence()

    def test_endpoint_unregistered_rejected_before_checkpoint_read(self):
        with patch.object(d.qa, 'required') as read:
            with self.assertRaises(ValueError):
                d.checkpoint_spec('cpt_qa')
        read.assert_not_called()

    def test_endpoint_requires_completed_training(self):
        with patch.object(d.training, 'required', return_value={}), patch.object(d.training, 'completed', return_value=False):
            with self.assertRaises(d.training.PrerequisitePending):
                d.checkpoint_spec('cpt_unique32k')

    def test_dev_selection_must_be_exact_argmin(self):
        report = dict(history=[dict(dev=dict(ce=v)) for v in (3., 2., 1., 4.)],
            best_dev_quarter=2, best_dev_ce=2.)
        with patch.object(d.training, 'required', return_value={}), patch.object(d.qa, 'required', return_value=report), patch.object(d.training, 'completed', return_value=True):
            with self.assertRaises(ValueError):
                d.checkpoint_spec('cpt_unique32k_best')

    def test_checkpoint_binds_final_and_dev_paths_separately(self):
        report = dict(history=[dict(dev=dict(ce=v)) for v in (3., 2., 1., 4.)], best_dev_quarter=3,
            best_dev_ce=1., checkpoint='runs/final.pt', checkpoint_sha256='FINAL', final_core_sha256='FINALCORE',
            best_dev_checkpoint='runs/best.pt', best_dev_checkpoint_sha256='BEST', best_dev_core_sha256='BESTCORE')
        for endpoint, expected in (('cpt_unique32k', ('FINAL', 'FINALCORE')),
                                   ('cpt_unique32k_best', ('BEST', 'BESTCORE'))):
            with patch.object(d.training, 'required', return_value={}), patch.object(d.qa, 'required', return_value=report), \
                    patch.object(d.training, 'completed', return_value=True), \
                    patch.object(d.training, 'checkpoint', side_effect=lambda best: ROOT / 'runs' / ('best.pt' if best else 'final.pt')), \
                    patch.object(d.qa.data, 'digest', return_value=expected[0]):
                self.assertEqual(d.checkpoint_spec(endpoint)[1:], expected)

    def _provider_fixture(self, historical=False):
        lanes = {'natural', 'native32'}
        report = dict(code_sha256={'c': 'S'}, input_report_sha256='S', checkpoint='runs/fake.pt',
            checkpoint_sha256='CP', initial_core_sha256='C' * 64,
            outputs={lane: dict(manifest={'lane': lane}) for lane in lanes},
            receipt_sha256={lane: 'S' for lane in lanes})
        receipts = {lane: dict(output=output, origin=dict(kind='NEW_MODEL_INFERENCE'),
            body_proof=dict(initial_core_sha256='C' * 64, final_core_sha256='C' * 64))
            for lane, output in report['outputs'].items()}
        provider = NS(EVIDENCE=Path('/synthetic/evidence'), FROZEN=Path('/synthetic/frozen'),
            LOCAL=Path('/synthetic/local'), OUTPUTS=lanes, endpoint_contract=Mock(),
            info=lambda: dict(code_sha256={'c': 'S'}),
            checkpoint_spec=Mock(return_value=(ROOT / 'runs/fake.pt', 'CP') if historical else
                (ROOT / 'runs/fake.pt', 'CP', 'C' * 64)),
            read_receipt=Mock(side_effect=lambda endpoint, lane, *args: receipts[lane]),
            receipt_path=lambda endpoint, lane: Path('/synthetic') / endpoint / lane,
            old=NS(stream=lambda directory, manifest: iter([{'id': 'frozen'}])))
        qa = NS(required=lambda path: report, data=NS(digest=lambda path: 'S'))
        return provider, qa, report, receipts

    def test_historical_two_field_api_and_body_receipts_are_verified(self):
        provider, qa, _, _ = self._provider_fixture(historical=True)
        with patch.object(d, 'qa', qa), patch.object(d.training, 'required', qa.required), patch.object(d, 'evaluation', provider):
            summary, rows = d.verified_endpoint(provider, 'base_qa', {}, {})
        self.assertEqual(summary['checkpoint_sha256'], 'CP')
        self.assertEqual(rows, [{'id': 'frozen'}])
        self.assertEqual(provider.read_receipt.call_count, 2)

    def test_historical_changed_actual_body_is_rejected(self):
        provider, qa, _, receipts = self._provider_fixture(historical=True)
        receipts['natural']['body_proof']['final_core_sha256'] = 'OTHER'
        with patch.object(d, 'qa', qa), patch.object(d.training, 'required', qa.required), patch.object(d, 'evaluation', provider):
            with self.assertRaises(ValueError):
                d.verified_endpoint(provider, 'cpt_qa', {}, {})

    def test_new_three_field_api_is_verified(self):
        provider, qa, _, _ = self._provider_fixture()
        with patch.object(d, 'qa', qa), patch.object(d.training, 'required', qa.required), patch.object(d.evaluation, 'OUTPUTS', provider.OUTPUTS), \
                patch.object(d.evaluation.old, 'stream', provider.old.stream):
            summary, _ = d.verified_endpoint(provider, 'unique32k', {}, {})
        self.assertEqual(summary['initial_core_sha256'], 'C' * 64)

    def test_changed_receipt_or_source_is_rejected(self):
        for mutation in ('receipt', 'source', 'checkpoint'):
            provider, qa, report, receipts = self._provider_fixture(historical=True)
            if mutation == 'receipt': receipts['natural']['output'] = {'changed': True}
            elif mutation == 'source': report['input_report_sha256'] = 'OTHER'
            else: report['checkpoint_sha256'] = 'OTHER'
            with patch.object(d, 'qa', qa), patch.object(d.training, 'required', qa.required), patch.object(d, 'evaluation', provider):
                with self.assertRaises(ValueError):
                    d.verified_endpoint(provider, 'base_qa', {}, {})

    def test_readback_recounts_all_four_cells_final_and_dev(self):
        writes = []
        qa = NS(write=lambda path, value: writes.append(value))
        evaluation = NS(read_inputs=Mock(), method=NS(paired_natural=lambda left, right: {'a': left, 'b': right}))
        original = NS(read_inputs=lambda: ({'source': 1}, {'cases': 2}))
        def verified(provider, endpoint, inputs, cases):
            return {'endpoint': endpoint}, [endpoint]
        with patch.object(d, 'qa', qa), patch.object(d, 'evaluation', evaluation), \
                patch.object(d, 'original_eval', original), patch.object(d, 'read_inputs', return_value=({'source': 1}, {'cases': 2})), \
                patch.object(d, 'verified_endpoint', side_effect=verified) as checker, \
                patch.object(d, 'info', return_value={}), patch.object(d, 'EVIDENCE', Path('/synthetic/new-fourth-cell')), \
                redirect_stdout(StringIO()):
            self.assertEqual(d.readback(), 0)
        self.assertEqual(checker.call_count, 8)
        self.assertEqual(len(writes[0]['paired']), 9)
        self.assertFalse(writes[0]['automatic_adoption'])
        self.assertFalse(writes[0]['learning_seed_variance_measured'])
        self.assertEqual(set(writes[0]['primary_endpoints']), {'base_qa', 'cpt_qa', 'unique32k', 'cpt_unique32k'})

    def test_readback_rejects_different_evaluation_cases_before_outputs(self):
        with patch.object(d, 'read_inputs', return_value=({}, {'cases': 2})), \
                patch.object(d.original_eval, 'read_inputs', return_value=({}, {'cases': 3})), \
                patch.object(d, 'verified_endpoint') as checker:
            with self.assertRaises(ValueError):
                d.readback()
        checker.assert_not_called()

    def test_missing_endpoint_never_becomes_zero_accuracy(self):
        with patch.object(d, 'read_inputs', return_value=({}, {})), \
                patch.object(d.original_eval, 'read_inputs', return_value=({}, {})), \
                patch.object(d, 'verified_endpoint', side_effect=FileNotFoundError('missing raw')), \
                patch.object(d.qa, 'write') as write, patch.object(d, 'EVIDENCE', Path('/synthetic/new-fourth-cell')):
            with self.assertRaises(FileNotFoundError): d.readback()
        write.assert_not_called()

    def test_expired_authority_is_pending8_and_never_calls_gpu(self):
        with patch.object(sys, 'argv', ['eval', '--mode', 'evaluate', '--endpoint', 'cpt_unique32k', '--execute']), \
                patch.object(d.training, 'authority', side_effect=d.training.PrerequisitePending('expired')), \
                patch.object(d, 'evaluate') as evaluate, redirect_stdout(StringIO()):
            self.assertEqual(d.main(), 8)
        evaluate.assert_not_called()

    def test_corruption_remains_tool9_and_interrupt_remains130(self):
        for exc, expected in ((ValueError('changed source'), 9), (KeyboardInterrupt(), 130)):
            with patch.object(sys, 'argv', ['eval', '--mode', 'readback', '--execute']), \
                    patch.object(d.training, 'authority', side_effect=exc), redirect_stdout(StringIO()), \
                    patch('traceback.print_exc'):
                self.assertEqual(d.main(), expected)


if __name__ == '__main__':
    unittest.main()
