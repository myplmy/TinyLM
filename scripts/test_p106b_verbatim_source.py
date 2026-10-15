from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
import copy
import json
import unittest
from scripts import diag_p106b_verbatim_source as code


class Tokens:
    def encode(self,text):return SimpleNamespace(ids=list(range(len(text))),offsets=[(i,i+1) for i in range(len(text))])


def example():
    return dict(messages=[dict(role='system',content=[dict(type='text',text='Quoted original system instruction.')]),
        dict(role='user',content=[dict(type='text',text='Example:\r\n```yaml\r\na:\r\n    b: 1\r\n\tc: 2\r\n```\r\n')]),
        dict(role='assistant',content=[dict(type='text',text='The record contains a nested mapping.\n')])],
        meta=dict(language='en',source_group_id='A'*64,source_id='fixture',source_license='project_authored',source_family='fixture'))


class Contracts(unittest.TestCase):
    def test_whole_messages_never_strip_or_split(self):
        row=example();units=code.message_units(row)
        self.assertEqual(len(units),3)
        self.assertIn('    b: 1\r\n\tc: 2',units[1]['text'])
        for index,unit in enumerate(units):
            self.assertEqual(unit['text'],row['messages'][index]['content'][0]['text'])
            self.assertEqual((unit['start'],unit['end']),(0,len(unit['text'])))

    def test_teacher_json_roundtrip_and_original_system_is_quoted(self):
        row=example();request=code.payload(code.message_units(row),'en',13)
        original=json.loads(request['messages'][1]['content'])['public_source_spans']
        self.assertEqual([u['text'] for u in original],[m['content'][0]['text'] for m in row['messages']])
        self.assertEqual(original[0]['source_role'],'system')
        self.assertNotIn('Quoted original system instruction.',request['messages'][0]['content'])

    def test_student_ranges_preserve_indentation_and_roles(self):
        row=example();units=code.message_units(row)
        content=dict(user_text='What value is associated with b?',assistant_text='1',correction_note='SOURCE_IDS:2')
        result=code.wrap(content,units,row,'en',Tokens());question=code.source.support.text(result['messages'][0])
        for unit,span in zip(units,result['meta']['student_original_message_ranges']):
            self.assertEqual(question[span['start']:span['end']],unit['text'])
        self.assertEqual([m['role'] for m in result['messages']],['user','assistant'])
        self.assertIn('[Original message 1 / system]',question)
        self.assertEqual(result['meta']['teacher_visible_original_messages_sha256'],result['meta']['student_visible_original_messages_sha256'])

    def test_changed_indent_cannot_pass_trace(self):
        row=example();units=code.message_units(row);units[1]['text']=units[1]['text'].replace('    ','')
        with self.assertRaises(ValueError):
            code.wrap(dict(user_text='q',assistant_text='a',correction_note='SOURCE_IDS:2'),units,row,'en',Tokens())

    def test_note_is_not_student_target(self):
        row=example();result=code.wrap(dict(user_text='q',assistant_text='one',
            correction_note='SOURCE_IDS:2\nPRIVATE_NOTE'),code.message_units(row),row,'en',Tokens())
        self.assertEqual(code.source.support.text(result['messages'][-1]),'one')
        self.assertFalse(result['meta']['teacher_reasoning_in_student'])

    def test_source_ids_are_message_ids_not_free_text_truth(self):
        row=example()
        with self.assertRaises(ValueError):
            code.wrap(dict(user_text='q',assistant_text='a',correction_note='SOURCE_IDS:99'),code.message_units(row),row,'en',Tokens())

    def test_profile_changes_cli_and_payload_together_then_restores(self):
        original=code.teacher.THINKING;function=code.source.support.wrap
        with code.bindings(256):
            request=code.payload(code.message_units(example()),'en',1)
            command=code.teacher.command(1,'REDACTED',mtp=True)
            self.assertEqual(request['thinking_budget_tokens'],256)
            self.assertEqual(command[command.index('--reasoning-budget')+1],'256')
            self.assertEqual(command[command.index('--spec-type')+1],'draft-mtp')
        self.assertEqual(code.teacher.THINKING,original)
        self.assertIs(code.source.support.wrap,function)

    def test_budget_error_cannot_truncate_original(self):
        row=example();row['messages'][1]['content'][0]['text']+='x'*1200;original=copy.deepcopy(row)
        with self.assertRaises(ValueError):
            code.wrap(dict(user_text='q',assistant_text='a',correction_note='SOURCE_IDS:2'),code.message_units(row),row,'en',Tokens())
        self.assertEqual(row,original)


if __name__=='__main__':unittest.main()
