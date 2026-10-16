"""CPU-only completeness/native contracts for the prompt evaluator adapter."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_prompt_eval as d


class PromptEvalTests(unittest.TestCase):
    def test_exact_four_endpoints_and_separate_namespace(self):
        self.assertEqual(d.ENDPOINTS, ('prompt0', 'prompt01', 'prompt0_best', 'prompt01_best'))
        self.assertNotEqual(d.FROZEN, d.evaluation.FROZEN)
        self.assertNotEqual(d.EVIDENCE, d.evaluation.EVIDENCE)
        with self.assertRaises(ValueError): d.checkpoint_spec('wrong')

    def test_no_missing_lane_can_be_complete(self):
        report = dict(status='ACTUAL_EVALUATION_COMPLETE', endpoint='prompt0', updates=0,
            checkpoints_written=0, body_unchanged=True,
            directory=str((d.LOCAL / 'prompt0').relative_to(ROOT)), outputs={}, receipt_sha256={})
        with self.assertRaises(ValueError): d.endpoint_contract(report, 'prompt0', {})

    def test_prior_native_contract_rejects_wrong_units(self):
        inputs = dict(native_val_sha256='VAL', native256_val_offsets=[32])
        spec = dict(ce=2., val_sha256='VAL', crops=32, targets=32768)
        d.evaluation.native_contract('native32', spec, inputs)
        with self.assertRaises(ValueError): d.evaluation.native_contract('native32', dict(spec, targets=32), inputs)

    def test_raw_fixed_cube_uses_original_code_and_preserves_wrong_zero_score(self):
        cases = dict(cube=d.evaluation.method.cube_rows())
        values = [dict(row, answer='', generation=dict(finish_reason='STOP_SEQUENCE')) for row in cases['cube']]
        from tinylm.chat.serialize import serialize
        for event in values:
            event['generation'].update(actual_prompt_sha256=d.qa.data.sha(serialize(dict(messages=event['messages']), 'chatml', add_generation_prompt=True)),
                raw_answer_sha256=d.qa.data.sha(event['answer']))
        result = d.evaluation.recount('cube', values, cases)
        self.assertEqual(result['summary']['n'], 64)
        self.assertEqual(result['summary']['literal'], 0)
        self.assertEqual(result['summary']['empty'], 64)
        with self.assertRaises(ValueError): d.evaluation.recount('cube', values[:-1], cases)


if __name__ == '__main__': unittest.main()
