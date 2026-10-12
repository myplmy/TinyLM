#!/usr/bin/env python3
"""CPU-only, no source/model/GPU access: frozen production MTP contracts."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_mtp_production as gate


def fixture():
    rows=[]
    for language in ('ko','en'):
        for task in ('qa','json','multiturn'):
            question=language+' fixed question '+task
            rows.append(dict(attempt=1,turn=3 if task=='multiturn' else 1,
                job=dict(language=language,task=task,source_group_id=language+task,
                    original=dict(messages=[{'role':'user','content':'public evidence'}])),
                producer_learner_turn=dict(user_text=question,assistant_text='old answer'),
                producer_output_trace=dict(output_contract=dict(version='P106B_PRODUCER_OUTPUT_V1',
                    authority='producer_code',producer='gemma_task_v2',kind='UNKNOWN')),
                payload=dict(seed=17,cache_prompt=True,messages=[dict(role='system',content='labels'),
                    dict(role='user',content=json.dumps(dict(producer_control={},source=dict(
                        public_context=['evidence'],explicit_previous_turns=['old context']))))])))
    return rows


class Contracts(unittest.TestCase):
    def test_profiles(self):
        units=gate.select_units(fixture())
        self.assertEqual([u['id'] for u in units],['ko_qa','ko_json','ko_multiturn','en_qa','en_json','en_multiturn'])

    def test_source_immutable(self):
        rows=fixture();original=copy.deepcopy(rows)
        units=gate.select_units(rows)
        self.assertEqual(rows,original)

    def test_production_request_exact(self):
        rows=fixture();original=copy.deepcopy(rows);units=gate.select_units(rows,protocol='production')
        for unit in units:
            self.assertEqual(unit['request'],unit['original_record']['payload'])
        units[0]['request']['seed']+=1
        self.assertEqual(rows,original)

    def test_student_json_instruction_is_not_teacher_question(self):
        row=fixture()[1]
        row['producer_output_trace']['original_teacher_question']='plain factual question'
        row['producer_learner_turn']['user_text']='plain factual question\nReply using answer-key JSON.'
        body=json.loads(gate.frozen_request(row)['messages'][1]['content'])
        self.assertEqual(body['producer_control']['learner_question_literal'],'plain factual question')
        unit=dict(language='ko',original_record=row)
        parsed=dict(format_status=gate.teacher.COMPLETE,
            parsed_content=dict(user_text='plain factual question',assistant_text='value'))
        with patch.object(gate.teacher,'parsed_response',return_value=parsed):
            turn,_,_=gate.rendered(unit,{})
        self.assertEqual(turn['user_text'],row['producer_learner_turn']['user_text'])

    def test_fixed_question_without_answer_leak(self):
        unit=gate.select_units(fixture())[0]
        text=unit['request']['messages'][1]['content'];body=json.loads(text)
        self.assertEqual(body['producer_control']['learner_question_literal'],unit['original_record']['producer_learner_turn']['user_text'])
        self.assertNotIn('old answer',text)
        self.assertEqual(body['source']['explicit_previous_turns'],['old context'])
        self.assertFalse(unit['request']['cache_prompt'])

    def test_missing_profile(self):
        with self.assertRaises(FileNotFoundError):gate.select_units(fixture()[:-1])

    def test_partial_old_turn_rejected(self):
        rows=fixture();rows[0]['producer_learner_turn']=None
        with self.assertRaises(FileNotFoundError):gate.select_units(rows)

    def test_long_sources_not_silently_cut(self):
        rows=fixture();rows[0]['job']['original']['messages'][0]['content']='x'*4000
        with self.assertRaises(FileNotFoundError):gate.select_units(rows)

    def test_never_claim_semantic_pass(self):
        text=(ROOT/'scripts/diag_p106b_gemma_mtp_production.py').read_text()
        self.assertIn("semantic_quality='NOT_REVIEWED'",text)
        self.assertIn('production_default_changed=False',text)
        self.assertNotIn('input(',text)

    def test_question_change_is_structure_not_truth(self):
        unit=gate.select_units(fixture())[0]
        parsed=dict(format_status=gate.teacher.COMPLETE,
            parsed_content=dict(user_text='different question',assistant_text='answer'))
        with patch.object(gate.teacher,'parsed_response',return_value=parsed):
            with self.assertRaisesRegex(ValueError,'fixed learner question changed'):
                gate.rendered(unit,{})


if __name__=='__main__':unittest.main()
