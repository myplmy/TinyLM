import unittest
from scripts import diag_p106b_actd_topk as d
from scripts import p106b_alm_bytes as byte


class ACTDTopKPreparationContracts(unittest.TestCase):
    def test_teacher_stream_uses_exact_byte_pieces_and_literal_added_false(self):
        text='a'+chr(0xAC00)+'<think><|im_end|>'
        inverse={value:key for key,value in byte._BYTELEVEL_INVERSE.items()}
        raw={'model':{'vocab':{'a':0,inverse[234]:1,inverse[176]+inverse[128]:2}},
             'added_tokens':[dict(id=3,content='<think>',special=False),dict(id=4,content='<|im_end|>',special=True)]}
        class Tokenizer:
            def __call__(self,value,**kw):
                if value!=text or kw!={'add_special_tokens':False,'return_offsets_mapping':True}:raise AssertionError('original text/options')
                return dict(input_ids=[0,1,2,3,4],offset_mapping=[(0,1),(1,2),(1,2),(2,9),(9,len(text))])
        packed=dict(text=text,student=dict(loss_spans_chars=[[1,len(text)]]))
        stream,native=d.teacher_stream(packed,Tokenizer(),raw)
        self.assertEqual(b''.join(t.data for t in stream.tokens),text.encode())
        self.assertIsNone(stream.tokens[3].special_kind)
        self.assertEqual(stream.tokens[4].special_kind,'<|im_end|>')
        self.assertEqual(native['ids'],[0,1,2,3,4])
        positions,holds=d.cache.prefix_candidates(stream)
        self.assertEqual(len(holds),1)
        self.assertEqual([p['prefix_raw_index'] for p in positions],[0,2,3])
        self.assertEqual([p['target_raw_index'] for p in positions],[1,3,4])

    def test_source_row_identity_is_checked_before_any_real_encoder(self):
        frozen={'source_row':{'messages':[]},'source_row_sha256':'0'*64}
        with self.assertRaisesRegex(ValueError,'source row changed'):
            d.prepared_row(frozen,0,'root',None,None,None,{})

    def test_metadata_only_added_literal_is_consumed_without_modifying_raw_json(self):
        import copy
        text='<tool_response>'
        raw=dict(model=dict(vocab={}),added_tokens=[]);before=copy.deepcopy(raw)
        metadata=[dict(id=99,content=text,special=False)]
        class Tokenizer:
            def __call__(self,value,**kw):return dict(input_ids=[99],offset_mapping=[(0,len(value))])
        packed=dict(text=text,student=dict(loss_spans_chars=[[0,len(text)]]))
        stream,native=d.teacher_stream(packed,Tokenizer(),raw,added_declarations=metadata)
        self.assertEqual(native['ids'],[99]);self.assertEqual(stream.tokens[0].data,text.encode())
        self.assertIsNone(stream.tokens[0].special_kind);self.assertEqual(raw,before)
        with self.assertRaisesRegex(ValueError,'undeclared native ID'):d.teacher_stream(packed,Tokenizer(),raw)

    def test_budget_rejects_expired_and_unknown_oversized_work(self):
        from unittest.mock import patch
        from datetime import timedelta
        class Late:
            @staticmethod
            def now(zone):return d.DEADLINE+timedelta(seconds=1)
        with patch.object(d,'datetime',Late):
            with self.assertRaises(TimeoutError):d.guard()


if __name__=='__main__':unittest.main()
