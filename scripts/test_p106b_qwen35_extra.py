import unittest
from scripts import p106b_qwen35_extra as e

EXAMPLE_VALUE='old'
def example():return EXAMPLE_VALUE


class QwenExtraContracts(unittest.TestCase):
    def test_private_bytecode_reuse_keeps_original_globals_and_defaults(self):
        new=e.private_function(example,EXAMPLE_VALUE='private')
        self.assertIs(new.__code__,example.__code__);self.assertIsNot(new.__globals__,example.__globals__)
        self.assertEqual(new(),'private');self.assertEqual(example(),'old')

    def test_whole_task_cost_requires_all_tasks_and_respects_deadline(self):
        c=dict(actual_counts={k:32 for k in ('kor_Hang','eng_Latn','lambada_openai')},
            task_seconds={k:1. for k in ('kor_Hang','eng_Latn','lambada_openai')},pre_evaluation_seconds=20.)
        self.assertGreater(e.admission(c,'lambada',5000)['forecast_seconds'],200)
        with self.assertRaises(TimeoutError):e.admission(c,'lambada',300)
        with self.assertRaises(ValueError):e.admission(dict(c,actual_counts={}), 'belebele',5000)
        with self.assertRaises(ValueError):e.admission(dict(c,task_seconds={}), 'belebele',5000)
        with self.assertRaises(ValueError):e.admission(dict(c,pre_evaluation_seconds=float('nan')), 'belebele',5000)

    def test_frozen_plan_matches_entire_arguments_without_doc_index_guess(self):
        from types import SimpleNamespace
        old=lambda lm,r:dict(tokens=len(r.args[1]))
        digest=lambda args:repr(args)
        f=e.matching_plan_callback(old,{repr(['context',' abc']):dict(tokens=4)},digest)
        self.assertEqual(f(None,SimpleNamespace(args=('context',' abc'))),dict(tokens=4))
        with self.assertRaises(ValueError):f(None,SimpleNamespace(args=('context',' ab')))

    def test_historical_projection_and_metadata_only_change_are_not_generic_hash_waivers(self):
        import hashlib,json
        digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
        before={'model_selector':'old','scorer':'same'};now=dict(before,model_selector='new')
        proof=e.historical_source_projection(now,before,digest,expected_base_sha=digest(before),allowed_drift={'model_selector'})
        self.assertEqual(proof['changed_paths'],['model_selector'])
        with self.assertRaises(ValueError):e.historical_source_projection(dict(now,scorer='different'),before,digest,
            expected_base_sha=digest(before),allowed_drift={'model_selector'})
        old="MANIFEST='old'\nREQUIRED_SOURCES=('a',)\ndef score():return 1"
        new="MANIFEST='new'\nREQUIRED_SOURCES=('b',)\ndef score():return 1"
        self.assertTrue(e.metadata_assignments_only(old,new,allowed_names={'MANIFEST','REQUIRED_SOURCES'})['all_other_ast_exact'])
        with self.assertRaises(ValueError):e.metadata_assignments_only(old,new.replace('return 1','return 2'),allowed_names={'MANIFEST','REQUIRED_SOURCES'})


if __name__=='__main__':unittest.main()
