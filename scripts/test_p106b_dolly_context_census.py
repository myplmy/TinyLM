from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from scripts import diag_p106b_dolly_context_census as code


class Alignment(unittest.TestCase):
    def test_existing_language_and_missing_language_are_not_duplicate_kwargs(self):
        self.assertEqual(code.declared_language(dict(language='en',path='fixture'),'en')['language'],'en')
        self.assertEqual(code.declared_language(dict(path='fixture'),'ko')['language'],'ko')
        with self.assertRaises(ValueError):code.declared_language(dict(language='en'),'ko')

    def test_literal_span_is_not_a_truth_judge(self):
        q='What color?\nContext:A is blue. B is red.';a='blue';s=code.exact_span(q,a)
        self.assertEqual(s['status'],'UNIQUE_LITERAL_SPAN');self.assertEqual(q[s['answer_start']:s['answer_end']],a)
        self.assertEqual(code.exact_span(q,'unknown')['status'],'NO_UNIQUE_LITERAL_TARGET')

    def test_duplicate_and_missing_context_are_unknown_not_wrong(self):
        self.assertEqual(code.exact_span('Question only','blue')['status'],'NO_UNIQUE_CONTEXT_MARKER')
        self.assertEqual(code.exact_span('Q\nContext:blue blue','blue')['status'],'NO_UNIQUE_LITERAL_TARGET')
        self.assertEqual(code.exact_span('Q\nContext:blue\nContext:blue','blue')['status'],'NO_UNIQUE_CONTEXT_MARKER')

    def test_korean_byte_overlap_uses_last_source_token_and_no_future_answer(self):
        from types import SimpleNamespace
        class Tokens:
            def encode(self,text):return SimpleNamespace(ids=list(range(2*len(text))),offsets=[(i,i+1) for i in range(len(text)) for _ in (0,1)])
        q='어떤 색?\nContext:가방은 파랑입니다.';a='파랑';span=code.exact_span(q,a);tokens=code.token_span(q,a,span,Tokens())
        self.assertIn(tokens['answer_end_token'],tokens['reference_token_positions'])
        self.assertLess(tokens['reference_token_positions'][-1],tokens['assistant_predictor'])
        self.assertFalse(tokens['prefix_has_answer_body'])


if __name__=='__main__':unittest.main()
