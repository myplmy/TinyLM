"""CPU-only raw identities, actual frozen-row incidence and lane safety."""
from pathlib import Path
import copy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_eval_recovery as d
from scripts.test_p106b_night_retention_v2 import row


class RecoveryTests(unittest.TestCase):
    def cases(self):
        return {lane: [row('ko', 'A'), row('ko', 'B'), row('en', 'A')]
                for lane in ('role', 'recovery', 'code')}

    def test_frozen_row_incidence_and_shared_root_supported(self):
        r = d.source_wire(self.cases())
        self.assertEqual(r['identical_prompt_conflicting_gold'], 0)
        self.assertEqual(r['lanes']['code']['raw_events'], 9)
        self.assertFalse(r['model_forward'])

    def test_same_exact_input_conflicting_gold_rejected(self):
        cases = self.cases(); changed = copy.deepcopy(cases['code'][0])
        changed['messages'][1]['content'] = 'different contradictory gold'
        cases['code'].append(changed)
        with self.assertRaisesRegex(ValueError, 'conflicting gold'): d.source_wire(cases)

    def test_unknown_partial_raw_never_silently_resumed(self):
        with tempfile.TemporaryDirectory(prefix='p106b_eval_lane_') as temp:
            path = Path(temp)
            self.assertEqual(len(d.pending_lanes(path, {})), 8)
            (path / 'code_000000.jsonl').touch()
            with self.assertRaisesRegex(FileExistsError, 'partial'): d.pending_lanes(path, {})

    def test_native_wrong_count_or_nan_rejected(self):
        inputs = dict(native_val_sha256='A', native256_val_offsets=[0])
        valid = dict(ce=1., val_sha256='A', crops=32, targets=32768)
        d.native_contract('native32', valid, inputs)
        for key, value in (('targets', 0), ('crops', 31), ('ce', float('nan')), ('val_sha256', 'B')):
            with self.assertRaises(ValueError): d.native_contract('native32', dict(valid, **{key: value}), inputs)

    def test_missing_endpoint_lanes_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            d.endpoint_contract(dict(status='ACTUAL_EVALUATION_COMPLETE', endpoint='parent',
                current_inference_body_unchanged=True, updates=0, checkpoints_written=0,
                directory=str((d.LOCAL / 'parent').relative_to(ROOT)), outputs={}, receipt_sha256={}), 'parent', {})

    def test_original_evaluator_is_not_monkeypatched(self):
        self.assertNotEqual(d.FROZEN, d.old.FROZEN)
        self.assertNotEqual(d.LOCAL, d.old.LOCAL)
        self.assertEqual(d.old.ENDPOINTS, ('parent', 'ce', 'consistent'))

    def test_lane_body_must_be_unchanged_before_publishing_receipt(self):
        origin = dict(kind='NEW_MODEL_INFERENCE')
        good = d.body_proof(origin, 'A' * 64, 'A' * 64)
        self.assertEqual(good['status'], 'UNCHANGED_WITHIN_THIS_LANE')
        for initial, final in ((None, None), ('A' * 64, 'B' * 64), ('A', 'A')):
            with self.assertRaises(ValueError): d.body_proof(origin, initial, final)
        self.assertIn('NOT_RECORDED', d.body_proof(dict(kind='CARRIED_VERIFIED_RAW'), None, None)['status'])
        with self.assertRaises(ValueError): d.body_proof(dict(kind='UNKNOWN'), None, None)

    def test_partial_prepare_cannot_be_promoted_to_gpu_ready(self):
        record = dict(status='RECOVERY_CPU_FROZEN', code_sha256={'code': 'A'}, original_input_report_sha256='B')
        identity = dict(code_sha256={'code': 'A'}, original_input_report_sha256='B')
        with patch.object(d.old, 'read_inputs', return_value=({}, {})), patch.object(d, 'info', return_value=identity):
            with patch.object(d.c, 'required', side_effect=[record, FileNotFoundError('final marker absent')]):
                with self.assertRaises(FileNotFoundError): d.read_inputs()
            with patch.object(d.c, 'required', side_effect=[record, record]), patch.object(d, 'read_receipt', side_effect=FileNotFoundError('carry receipt absent')):
                with self.assertRaises(FileNotFoundError): d.read_inputs()

    def test_foundation_metadata_not_just_status_or_checkpoint_sha(self):
        expected = dict(updates=640, source_qa_sha256='QA', contract_sha256='CONTRACT', initializer_sha256='PARENT')
        valid = dict(status='FOUNDATION_TRAIN_COMPLETE', arm='base_qa', actual_oom=False,
            checkpoint_written=True, history=[dict(dev=dict(ce=x)) for x in (2., 1., 1.2, 1.3)],
            best_dev_epoch=2, best_dev_ce=1., **expected)
        d.validate_foundation_report(valid, 'base_qa', expected)
        for key, value in (('arm', 'native'), ('updates', 0), ('source_qa_sha256', 'WRONG'),
                           ('contract_sha256', 'WRONG'), ('initializer_sha256', 'WRONG'), ('best_dev_epoch', 4)):
            with self.assertRaises(ValueError, msg=key):
                d.validate_foundation_report(dict(valid, **{key: value}), 'base_qa', expected)


if __name__ == '__main__': unittest.main()
