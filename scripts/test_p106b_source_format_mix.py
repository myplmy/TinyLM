"""CPU fixtures for format-only manipulation; no model/tokenizer loading."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import unittest
from scripts import diag_p106b_source_format_mix as mix
from tinylm.chat.canonical import normalize

class FormatMixTests(unittest.TestCase):
    def rows(self):
        value=normalize(dict(messages=[dict(role='user',content='Reference'),dict(role='assistant',content='blue')],
            meta=dict(language='en',parent_concept_id='A'*64,course_family='AYA',
                      source_reference_trace=[dict(text='Mina is blue.',id=1)])))
        return mix.course.data.views(value,'Which one?', 'train')
    def test_natural_preserves_exact_reference_and_answer(self):
        original=self.rows()[0];edited=mix.transform(original,'Which one?',True)
        self.assertEqual(mix.course.support.text(edited['messages'][0]),original['meta']['reference_text']+'\n\nWhich one?')
        self.assertEqual(edited['messages'][-1],original['messages'][-1])
        self.assertEqual(edited['meta']['reference_text'],'')
    def test_missing_contract_is_unchanged(self):
        original=self.rows()[1];edited=mix.transform(original,'Which one?',False)
        self.assertEqual(original['messages'],edited['messages'])
        with self.assertRaises(ValueError):mix.transform(original,'Which one?',True)
    def test_half_per_language_family_and_deterministic(self):
        rows=[]
        for i in range(8):
            value=self.rows()[0];value['meta']['parent_concept_id']=str(i)*64
            rows.append(value)
        self.assertEqual(len(mix.natural_selection(rows)),4)
        self.assertEqual(mix.natural_selection(rows),mix.natural_selection(list(reversed(rows))))
    def test_no_source_or_input_mutation(self):
        original=self.rows()[0];edited=mix.transform(original,'Which one?',True)
        self.assertNotEqual(original['messages'][0],edited['messages'][0])
        self.assertTrue(original['meta']['reference_text'])

if __name__=='__main__':unittest.main()
