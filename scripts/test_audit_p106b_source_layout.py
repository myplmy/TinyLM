from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from scripts import audit_p106b_source_layout as audit
from scripts import diag_p106b_verbatim_source as lossless


class Contracts(unittest.TestCase):
    def row(self):return dict(messages=[dict(role='user',content=[dict(type='text',text='a:\n    b: 1\n')])])
    def units(self,spans):return [dict(id=s['id'],text=s['text']) for s in spans]

    def test_old_slice_valid_but_indent_missing(self):
        row=self.row();spans=audit.source.source.support.source_spans(row)
        result=audit.assess(row,spans,self.units(spans),'\n'.join(s['text'] for s in spans))
        self.assertEqual(result['uncovered_nonwhitespace'],0)
        self.assertEqual(result['missing_leading_indent_characters'],4)

    def test_complete_messages_have_no_missing_characters(self):
        row=self.row();spans=lossless.message_units(row);text=row['messages'][0]['content'][0]['text']
        result=audit.assess(row,spans,self.units(spans),text)
        self.assertEqual(result['uncovered_nonwhitespace']+result['uncovered_whitespace'],0)
        self.assertEqual(result['missing_leading_indent_characters'],0)

    def test_payload_disagreement_is_integrity_error(self):
        row=self.row();spans=lossless.message_units(row);units=self.units(spans);units[0]['text']='wrong'
        with self.assertRaises(ValueError):audit.assess(row,spans,units,'text')


if __name__=='__main__':unittest.main()
