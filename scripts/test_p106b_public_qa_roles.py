#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_public_qa_roles as f
from tinylm.chat.canonical import normalize,validate


def fixture():
    reference='Nora was born in1901. She writes as BlueOak. BlueOak wrote WindRoad. '+('Background sentence for explicit reference. '*6)
    return validate(normalize(dict(messages=[dict(role='user',content=reference+'1. Who wrote WindRoad? 2. What is her pen name? 3. What book did she write? 4. Next question?'),
        dict(role='assistant',content='1. Nora 2. BlueOak 3. WindRoad 4. Later answer')],
        meta=dict(source='p106b_public_direct',selection_family='Flan-Coqa',language='en',parent_concept_id='fixture',
            source_id='fixture_only',source_repo='fixture',source_license='fixture',rights_status='FIXTURE',
            control_output_contract=dict(kind='UNIQUE_JSON',value=44),assistant_targets=999,capability_profile='json'))))


class Roles(unittest.TestCase):
    def test_original_three_roles_and_no_future_answers_in_first_user(self):
        row=fixture();child,p=f.wrap(row);self.assertEqual([m['role'] for m in child['messages']],['user','assistant']*3)
        self.assertEqual([f.source.text(x) for x in child['messages'][1::2]],['Nora','BlueOak','WindRoad'])
        self.assertEqual(f.source.text(child['messages'][2]),'What is her pen name?')
        self.assertNotIn('2. What',f.source.text(child['messages'][0]));self.assertNotIn('Later answer',str(child))

    def test_exact_source_ranges_and_immutable_input(self):
        row=fixture();old=copy.deepcopy(row);child,p=f.wrap(row);texts=[f.source.text(m) for m in row['messages']]
        for item in p['pairs']:
            for j,key in enumerate(('original_question_range','original_answer_range')):
                a,b=item[key];self.assertEqual(texts[j][a:b].strip(),item['question' if j==0 else 'answer'])
        self.assertEqual(row,old);self.assertEqual(child['meta']['original_messages_sha256'],f.source.sha(row['messages']))

    def test_translated_number_units_not_guessed(self):
        row=fixture();row['messages'][0]['content'][0]['text']=f.source.text(row['messages'][0]).replace('3. What','3살 What')
        with self.assertRaisesRegex(ValueError,'boundaries'):f.wrap(row)

    def test_duplicate_or_missing_boundary_rejected(self):
        for replacement in ('2. Another 2. What','What'):
            row=fixture();row['messages'][0]['content'][0]['text']=f.source.text(row['messages'][0]).replace('2. What',replacement)
            with self.assertRaisesRegex(ValueError,'boundaries'):f.wrap(row)

    def test_unregistered_producer_not_guessed(self):
        row=fixture();row['meta']['selection_family']='ordinary_free_text'
        with self.assertRaisesRegex(ValueError,'declared'):f.wrap(row)

    def test_old_json_contract_and_counts_not_inherited(self):
        child,p=f.wrap(fixture());self.assertNotIn('control_output_contract',child['meta']);self.assertNotIn('assistant_targets',child['meta'])
        self.assertEqual(child['meta']['rights_status'],'FIXTURE');self.assertEqual(child['meta']['teacher_calls'],0)
        self.assertEqual(child['meta']['semantic_truth'],'NOT_REVIEWED')


if __name__=='__main__':unittest.main()
