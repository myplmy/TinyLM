"""Actual source roles and wrong-turn masking, without any teacher call."""
import unittest
from tokenizers import Tokenizer
from scripts import p108b_correction as c
from scripts.p106b_mixed_scale import TOKENIZER,TOK_SHA
from scripts import interactive_research_infer as manual


class CorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if manual.file_sha(TOKENIZER)!=TOK_SHA:raise ValueError('original chat32 tokenizer changed')
        cls.tok=Tokenizer.from_file(str(TOKENIZER))

    def test_source_scope_is_all24_fit_failures_and_explicit4_synthetic_controls(self):
        rows=c.cases()
        self.assertEqual(sum(r['original_reply_is_actual']for r in rows),24)
        self.assertEqual(sum(not r['original_reply_is_actual']for r in rows),4)
        self.assertEqual(len({r['source_group_id']for r in rows}),10)
        german=next(r for r in rows if r['id']=='de_capital_en:0')
        self.assertEqual(german['root_issues'],['CORRECT_CONTENT_FORMAT_ONLY'])
        self.assertIn('Berlin',german['actual_reply'])

    def test_wrong_assistant_text_remains_context_but_all_its_targets_are_masked(self):
        case=c.cases()[0];parsed=dict(user_text='질문을 복사하지 말고 도시 이름만 답해주세요.',assistant_text=case['verified_short_answer'],correction_note='')
        single,multi=c.views(case,parsed);s=c.masked_record(single,self.tok);m=c.masked_record(multi,self.tok)
        self.assertEqual(s.targets,m.targets)
        self.assertEqual({owner for owner,label in zip(m.segments,m.y)if label!=-100},{2})
        text=self.tok.decode(m.x,skip_special_tokens=False)
        self.assertIn(case['actual_reply'],text)
        self.assertIn(parsed['user_text'],text)
        self.assertEqual(multi['messages'][1]['content'][0]['text'],case['actual_reply'])

    def test_eval_errors_and_changed_literal_answers_are_rejected(self):
        case=c.cases()[0]
        with self.assertRaises(ValueError):c.payload(dict(case,source_split='final_test'),17)
        with self.assertRaises(ValueError):c.views(case,dict(user_text='again',assistant_text='unverified',correction_note=''))

    def test_correct_answer_controls_keep_answer_and_group_pairing(self):
        controls=[r for r in c.cases()if not r['original_reply_is_actual']]
        for case in controls:
            self.assertEqual(case['actual_reply'],case['verified_short_answer'])
            a,b=c.views(case,dict(user_text='Please verify and retain the correct answer.',assistant_text=case['verified_short_answer'],correction_note=''))
            self.assertEqual(a['meta']['source_group_id'],b['meta']['source_group_id'])
            self.assertFalse(a['meta']['corpus75m_admitted'])


if __name__=='__main__':unittest.main()
