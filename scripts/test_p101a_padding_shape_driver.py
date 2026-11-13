import unittest
from unittest.mock import patch
from scripts import diag_p101a_padding_shapes as driver
from scripts import p101a_sft_mtp_data as data
from tinylm.data.prepare import SyntheticTokenizer
from tinylm.train.mtp_sft import encode_record


class ConsumerContract(unittest.TestCase):
    def test_actual_consumer_preserves_explicit_second_turn_only_supervision(self):
        tok=SyntheticTokenizer(vocab_size=31,span=31)
        row=dict(messages=[dict(role='user',content='first'),dict(role='assistant',content='wrong first answer'),
                           dict(role='user',content='correct it'),dict(role='assistant',content='right')],
                 meta=dict(supervised_assistant_turns=[2]))
        generic=encode_record(row,tok)
        report=dict(manifests=dict(train={},val={}))
        with patch.object(data,'stream_rows',side_effect=lambda *_:[row]):
            actual=driver.read_records(None,report,tok)['train'][0]
        self.assertEqual(actual.x,generic.x)
        self.assertLess(actual.targets,generic.targets)
        self.assertNotIn(1,actual.segments)
        self.assertIn(2,actual.segments)
        self.assertTrue(all(y==-100 for y,s in zip(actual.y,generic.segments) if s==1))


if __name__=='__main__':unittest.main()
