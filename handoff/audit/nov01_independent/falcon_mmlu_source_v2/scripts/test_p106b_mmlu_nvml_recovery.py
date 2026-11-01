"""감시 경계 복구가 원공식평가·자원정책을 바꾸지 않는지 CPU로 확인한다."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p106b_mmlu_nvml_recovery as driver
from scripts import diag_p106b_official_mmlu as original


def fixture(*, fail=False):
    core = SimpleNamespace(records=[])
    def score_batch(_):
        return [(-1., False), (-2., True)]
    core.score_batch = score_batch
    def score(requests, **kwargs):
        value = core.score_batch(requests)
        core.records.extend([dict(input_tokens=7), dict(input_tokens=11)])
        if fail:
            raise TimeoutError('fixture interruption after one completed batch')
        return value
    lm = SimpleNamespace(core=core, _loglikelihood_tokens=score)
    cuda = SimpleNamespace(synchronize=lambda:None, max_memory_allocated=lambda:23,
                           max_memory_reserved=lambda:29)
    return lm, SimpleNamespace(cuda=cuda)


class RecoveryContract(unittest.TestCase):
    def test_private_bindings_do_not_modify_original_module(self):
        before = {name:getattr(original, name) for name in ('VramWatch','identity','PROFILE','data','timed_backend')}
        output = original.data.OUTPUT
        private = driver.private_driver()
        self.assertIsNot(private, original)
        self.assertEqual(private.data.OUTPUT, driver.OUTPUT)
        self.assertEqual(original.data.OUTPUT, output)
        self.assertTrue(all(getattr(original, name) is value for name,value in before.items()))

    def test_policy_evaluate_admission_validation_bodies_unchanged(self):
        private = driver.private_driver()
        for name in driver.UNCHANGED:
            self.assertEqual(driver.function_ast(getattr(private,name)), driver.function_ast(getattr(original,name)))
        self.assertEqual(private.policy(5), original.policy(5))

    def test_successful_scores_unchanged_and_callbacks_restored(self):
        lm, torch = fixture()
        before, callback = lm._loglikelihood_tokens, lm.core.score_batch
        report = dict(scorer_seconds=0.)
        with driver.timed_backend(lm, torch, report):
            self.assertEqual(lm._loglikelihood_tokens([1,2]), [(-1.,False),(-2.,True)])
        self.assertIs(lm._loglikelihood_tokens, before)
        self.assertIs(lm.core.score_batch, callback)
        self.assertEqual(report['scored_input_positions'], 18)
        self.assertEqual(report['backend_requests_completed'], 2)
        self.assertGreater(report['scorer_seconds'], 0.)

    def test_interrupted_work_has_partial_cost_not_official_score(self):
        lm, torch = fixture(fail=True)
        before, callback = lm._loglikelihood_tokens, lm.core.score_batch
        report = dict(scorer_seconds=0.)
        with self.assertRaises(TimeoutError):
            with driver.timed_backend(lm, torch, report):
                lm._loglikelihood_tokens([1,2])
        self.assertIs(lm._loglikelihood_tokens, before)
        self.assertIs(lm.core.score_batch, callback)
        self.assertEqual(report['backend_forward_batches_completed'], 1)
        self.assertEqual(report['completed_record_requests'], 2)
        self.assertEqual(report['peak_reserved_bytes'], 29)
        self.assertTrue(report['partial_telemetry_is_not_official_score'])
        self.assertGreater(report['scorer_seconds'], 0.)

    def test_identity_extends_without_replacing_original_sources(self):
        original_files = original.identity()['files']
        actual = driver.identity()
        self.assertEqual({name:actual['files'][name] for name in original_files}, original_files)
        self.assertEqual(len(actual['files']), len(original_files) + len(driver.OWN))

    def test_no_reuse_of_original_source_cost(self):
        private = driver.private_driver()
        cost = dict(status='LIMITED_COST_DIAGNOSTIC', final_exit=0, model='native595-q',shots=5,
            profile_sha256='new', source=original.identity(),policy=original.policy(5),actual_rows=114,
            audits={str(i):{} for i in range(57)},scorer_seconds=1.,scored_input_positions=100.)
        with self.assertRaises(ValueError):
            private.admit_full(cost,'new','native595-q',5,1000,original.DEADLINE.timestamp()-20000)

    def test_model_source_data_bindings_are_evaluation_only(self):
        private = driver.private_driver()
        self.assertEqual(private.data.MODELS, original.data.MODELS)
        self.assertIs(private.data.load_tasks, original.data.load_tasks)
        self.assertIs(private.data.requests, original.data.requests)
        self.assertEqual(private.data.CACHE, original.data.CACHE)
        self.assertEqual(private.DEADLINE, original.DEADLINE)


if __name__ == '__main__':
    unittest.main()
