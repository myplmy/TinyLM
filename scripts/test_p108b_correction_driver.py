"""Contract failures, limited retries and actual wrong-turn masking."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from scripts import diag_p108b_correction as d


class Budget:
    def check(self):pass


class CorrectionDriverTests(unittest.TestCase):
    def case(self):return next(r for r in d.contract.cases()if r['id']=='kr_capital:0')

    def response(self,case,answer):
        return dict(choices=[dict(finish_reason='stop',message=dict(
            content='QUESTION:\nPlease answer only with the city name.\nANSWER:\n'+answer+'\nNOTE:',reasoning_content='retained sidecar'))],usage=dict(completion_tokens=20))

    def test_literal_copy_rejection_recovers_with_original_source_unchanged(self):
        case=self.case();bad=self.response(case,'wrong literal');good=self.response(case,case['verified_short_answer']);raw=[]
        session=SimpleNamespace(check=lambda:None)
        with patch.object(d,'request_with_evidence',side_effect=[bad,good])as request:
            result=d.generate_case(session,case,raw.append,Budget(),0)
        self.assertEqual(result['attempts'],2);self.assertEqual(result['status'],'CANDIDATE_STRUCTURE_COMPLETE')
        self.assertEqual(len(raw),2);self.assertFalse(raw[0]['accepted_structure']);self.assertTrue(raw[1]['accepted_structure'])
        self.assertEqual(raw[1]['metrics']['reasoning_text'],'retained sidecar')
        import json
        body=json.loads(request.call_args.args[1]['messages'][1]['content'])
        self.assertEqual(body['original_question'],case['original_question'])
        self.assertEqual(body['verified_short_answer'],case['verified_short_answer'])

    def test_three_failures_are_preserved_and_never_wrapped_as_accepted(self):
        case=self.case();raw=[];bad=self.response(case,'wrong literal')
        with patch.object(d,'request_with_evidence',return_value=bad):
            result=d.generate_case(SimpleNamespace(check=lambda:None),case,raw.append,Budget(),0)
        self.assertEqual(len(raw),3);self.assertEqual(result['status'],'REJECTED_STRUCTURE_AFTER3');self.assertFalse(result['views'])


if __name__=='__main__':unittest.main()
