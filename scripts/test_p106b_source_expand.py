from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import unittest
from scripts import diag_p106b_source_expand as code
from tinylm.chat.canonical import normalize,validate


class Tokenizer:
    def encode(self,text):return SimpleNamespace(ids=list(range(len(text))),offsets=[(i,i+1) for i in range(len(text))])


class Contracts(unittest.TestCase):
    def row(self):return validate(normalize(dict(messages=[dict(role='user',content='A is blue. Which color is A?'),
        dict(role='assistant',content='blue')],meta=dict(language='en',parent_concept_id='A'*64,source_group_id='A'*64,
        source_id='fixture',source_license='project_authored',source_family='NQ-Open'))))

    def test_old_root_and_message_are_excluded(self):
        row=self.row();self.assertEqual(code.allowed(row,{'A'*64},set(),Tokenizer()),(False,'old_concept'))
        row['messages'][0]['content'][0]['text']='x'*210
        keys={k.upper() for k in code.source.data.document_keys(row)}
        self.assertEqual(code.allowed(row,set(),keys,Tokenizer()),(False,'old_long_message'))

    def test_actual_token_reserve_not_quality(self):
        row=self.row();row['messages'][0]['content'][0]['text']='x'*600
        self.assertEqual(code.allowed(row,set(),set(),Tokenizer()),(False,'full_reference_token_reserve'))

    def test_full_original_visible_not_only_selected_answer(self):
        row=self.row();spans=code.source.support.source_spans(row)
        content=dict(user_text='Which color is A?',assistant_text='blue',correction_note='SOURCE_IDS:1')
        result=code.full_wrap(content,spans,row,'en',Tokenizer())
        question=code.source.support.text(result['messages'][0])
        self.assertIn('A is blue.',question)
        self.assertEqual(result['meta']['teacher_selected_reference_ids'],[1])
        self.assertEqual(len(result['meta']['source_reference_ids']),len(spans))
        self.assertEqual(code.source.support.text(result['messages'][-1]),'blue')

    def test_original_message_order_is_preserved(self):
        row=self.row();spans=code.source_spans(row)
        self.assertEqual([s['source_message_index'] for s in spans],sorted(s['source_message_index'] for s in spans))
        request=code.payload(list(reversed(spans)),'en',1337)
        supplied=__import__('json').loads(request['messages'][1]['content'])['public_source_spans']
        self.assertEqual(supplied[0]['source_role'],'user')
        content=dict(user_text='Which color is A?',assistant_text='blue',correction_note='SOURCE_IDS:1')
        result=code.full_wrap(content,list(reversed(spans)),row,'en',Tokenizer())
        question=code.source.support.text(result['messages'][0])
        self.assertLess(question.index('A is blue.'),question.index('\nblue'))


if __name__=='__main__':unittest.main()
