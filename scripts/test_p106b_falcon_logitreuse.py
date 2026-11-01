"""CPU checks of the official-scoring reuse adapter, never model/GPU execution."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p106b_falcon_logitreuse as driver


class LogitReuse(unittest.TestCase):
    def test_only_logit_cache_policy_differs(self):
        before=driver.ORIGIN_PRIOR.policy(0);after=driver.policy(0)
        self.assertFalse(before['logits_cache']);self.assertTrue(after['logits_cache'])
        self.assertEqual({k:v for k,v in before.items() if k!='logits_cache'},
                         {k:v for k,v in after.items() if k!='logits_cache'})

    def test_official_evaluate_body_reused(self):
        self.assertEqual(driver.base.evaluate.__code__.co_filename,driver.base.__file__)

    def test_instance_only_runtime_flag(self):
        lm=SimpleNamespace(logits_cache=False)
        @contextmanager
        def old(*_,**__):yield lm,{}
        with patch.object(driver.ORIGIN_OLD,'model_runtime',old):
            with driver.RuntimeProxy().model_runtime('fixture',None) as (model,proof):
                self.assertTrue(model.logits_cache)
                self.assertTrue(proof['official_context_logit_reuse_enabled'])

    def test_existing_parity_function_extracted_without_driver_import(self):
        self.assertEqual(driver.require_cost_parity.__code__.co_filename,
            str(driver.ROOT/'scripts/diag_p106b_falcon_tokenbatch.py')+'::parity_only')


if __name__=='__main__':unittest.main()
