"""CPU structural support-ID, exact-source, masks and shared budget fixtures."""
import unittest
from tinylm.chat.canonical import normalize
from scripts import p106b_visible_source as contract

class SupportTests(unittest.TestCase):
    def source(self):return normalize(dict(messages=[dict(role='user',content='Read this source.'),
        dict(role='assistant',content='Mina is blue. Jin is red.')],meta=dict(source_id='fixture:1',source_sha256='A'*64)))
    def test_exact_unicode_source_slices_and_ids(self):
        source=self.source();spans=contract.source_spans(source)
        for s in spans:
            original=contract.text(source['messages'][s['source_message_index']])
            self.assertEqual(original[s['start']:s['end']],s['text'])
        self.assertEqual(contract.reference_ids('SOURCE_IDS:2,1',spans),[1,2])
    def test_missing_duplicate_outside_ids_fail_closed(self):
        spans=contract.source_spans(self.source())
        for note in ('','SOURCE_IDS:99','SOURCE_IDS:1,1','SOURCE_IDS:1\nSOURCE_IDS:2','SOURCE_IDS:1,2,3,4'):
            with self.assertRaises(ValueError):contract.reference_ids(note,spans)
    def test_selected_source_visible_and_note_not_in_student_answer(self):
        from tinylm.data.prepare import SyntheticTokenizer
        source=self.source();spans=contract.source_spans(source)
        row=contract.wrap(dict(user_text='Mina color?',assistant_text='blue',correction_note='SOURCE_IDS:1'),
            spans,source,'en',SyntheticTokenizer())
        self.assertIn('Mina is blue.',contract.text(row['messages'][0]))
        self.assertNotIn('Jin is red.',contract.text(row['messages'][0]))
        self.assertEqual(contract.text(row['messages'][1]),'blue')
        self.assertTrue(row['meta']['code_wraps_canonical_chatml'])
    def test_three_structural_attempts_include_first(self):
        self.assertEqual(contract.MAX_ATTEMPTS,3)

    def test_real_driver_imports_and_budget_api_with_mock_server(self):
        from scripts import diag_p106b_visible_source16 as driver
        class Session:
            def request(self,route,payload):
                if route=='/apply-template':
                    assert isinstance(payload['messages'],list);return {'prompt':'fixture prompt'}
                assert route=='/tokenize';assert payload['parse_special'] is True
                return {'tokens':[1,2,3]}
        budget=driver.input_budget(Session(),{'messages':[{'role':'user','content':'fixture'}]})
        self.assertEqual(budget['prompt_tokens'],3)
        self.assertEqual(budget['context_tokens'],8192)
        self.assertEqual(budget['maximum_output_tokens'],3072)

if __name__=='__main__':unittest.main(verbosity=2)
