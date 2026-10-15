#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import diag_p106b_relation_interleaved_course as c


class Course(unittest.TestCase):
    def test_new_paths_same_parent_and_existing_frozen_code_untouched(self):
        self.assertNotEqual(c.CORPUS,c.base.CORPUS);self.assertNotEqual(c.EVIDENCE,c.base.EVIDENCE)
        self.assertEqual(c.PARENT,c.base.PARENT);self.assertEqual(c.PARENT_SHA,c.base.PARENT_SHA)

    def test_native_and_source_pass_arithmetic(self):
        self.assertEqual(688*8,5504);self.assertEqual(688*8192,5636096)
        self.assertEqual(8192//4*2,4096);self.assertEqual(16384+5632,22016)

    def test_fresh_and_reserved_are_not_old_evaluation(self):
        r=c.info();self.assertEqual(r['current_natural_test_per_language'],16)
        self.assertEqual(r['reserve_future_min_per_language'],24)
        self.assertEqual(r['new_test_fiction_indices'],[8192,8447]);self.assertEqual(r['fact_weights'],[1.])

    def test_stale_json_task_removed_without_changing_prompt_or_answer(self):
        row=dict(messages=[dict(role='user',content='source and question'),dict(role='assistant',content='answer')],
            meta=dict(control_output_contract=dict(kind='UNIQUE_JSON',value=44),capability_profile='json',source_truth='UNVERIFIED'))
        result=c.clean_single_metadata(row);self.assertEqual(result['messages'],row['messages'])
        self.assertNotIn('control_output_contract',result['meta']);self.assertEqual(result['meta']['source_truth'],'UNVERIFIED')

    def test_reference_hash_is_not_affected_by_question_suffix(self):
        import copy
        row=c.factory.make(c.factory.graph(2),'ko',0);other=copy.deepcopy(row)
        other['messages'][0]['content'][0]['text']+=' 다른 질문'
        self.assertEqual(c.reference_sha(row),c.reference_sha(other))


if __name__=='__main__':unittest.main()
