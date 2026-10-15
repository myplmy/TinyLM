from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import p106b_reference_views as code


def example():
    units=[dict(id=1,role='user',text='first\n  indented\n',source_message_index=0),dict(id=2,role='assistant',text='second',source_message_index=1)]
    text='Quoted reference:\n';spans=[]
    for unit in units:
        text+=code.header(unit,'en');start=len(text);text+=unit['text']
        spans.append(dict(start=start,end=len(text),sha256=code.sha(unit['text']),source_message_index=unit['source_message_index']));text+='\n'
    text+='Question:\nWhich item?'
    return dict(messages=[dict(role='user',content=[dict(type='text',text=text)]),dict(role='assistant',content=[dict(type='text',text='second')])],
        meta=dict(language='en',rubric='CLARIFICATION_POSTHOC',source_reference_trace=units,student_original_message_ranges=spans,teacher_selected_reference_ids=[2]))


class Views(unittest.TestCase):
    def test_exact_full_and_selected_whole_messages(self):
        row=example();before=copy.deepcopy(row);full=code.view(row,'full');selected=code.view(row,'selected')
        self.assertEqual(full['messages'],row['messages']);self.assertEqual(selected['messages'][1],row['messages'][1])
        text=selected['messages'][0]['content'][0]['text'];self.assertNotIn('indented',text);self.assertIn('second',text)
        self.assertTrue(text.endswith('Question:\nWhich item?'));self.assertEqual(selected['meta']['current_reference_ids'],[2])
        self.assertFalse(selected['meta']['student_training_allowed']);self.assertEqual(row,before)
        self.assertEqual(selected['meta']['upstream_meta']['source_reference_trace'][0]['text'],'first\n  indented\n')

    def test_empty_is_explicit_and_unknown_selection_never_guessed(self):
        row=example();empty=code.view(row,'empty');self.assertEqual(empty['meta']['current_reference_ids'],[])
        self.assertNotIn('second',empty['messages'][0]['content'][0]['text'])
        row['meta']['teacher_selected_reference_ids']=[999]
        with self.assertRaises(ValueError):code.view(row,'selected')

    def test_corrupt_original_ranges_rejected(self):
        row=example();row['meta']['student_original_message_ranges'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):code.view(row,'full')


if __name__=='__main__':unittest.main()
