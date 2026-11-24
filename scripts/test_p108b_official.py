"""CPU source/policy reuse guards for the new official evaluation adapter."""
from unittest.mock import patch
import unittest
from scripts import diag_p108b_official as api


class OfficialTests(unittest.TestCase):
    def test_original11_full_denominators_and_policy_are_reused(self):
        r=api.baseline_reference()
        self.assertEqual(len(r['actual_counts']),11)
        self.assertEqual(r['actual_counts']['piqa'],1838)
        self.assertEqual(r['actual_counts']['hellaswag'],10042)
        self.assertEqual(sum(n for k,n in r['actual_counts'].items()if k.startswith('kobest_')),4561)
        self.assertEqual(r['origin']['name'],'new595-broad-f')

    def test_private_evaluator_changes_only_namespace_not_owner(self):
        before=dict(api.owner.evaluate.__globals__)
        def digest(_):return 'frozen'
        with patch.object(api.manual,'file_sha',side_effect=digest):
            fn=api.evaluator()
        self.assertIs(fn.__code__,api.owner.evaluate.__code__)
        self.assertIs(fn.__globals__['model_runtime'],api.model_runtime)
        self.assertEqual(api.owner.evaluate.__globals__['OUTPUT'],before['OUTPUT'])
        self.assertIs(api.owner.evaluate.__globals__['model_runtime'],before['model_runtime'])


if __name__=='__main__':unittest.main()
