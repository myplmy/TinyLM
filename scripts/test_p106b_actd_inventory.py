import copy
import unittest
from scripts import diag_p106b_actd_anchor as d


class InventoryContracts(unittest.TestCase):
    def rows(self):
        record=dict(x=[3,10,11],y=[-100,11,4],segments=[0,1,0])
        return [dict(language='ko',record=record,record_sha256=d.object_sha(record),ce_targets=2,
                     chunks=[dict(positions=[1],teacher_logprob=-.1,teacher_target_count=1)])]

    def test_scalar_alm_is_not_a_topk_cache(self):
        source=self.rows();before=copy.deepcopy(source);r=d.inventory(source)
        self.assertFalse(r['actd_cache_ready']);self.assertEqual(r['export_topk_positions'],0)
        self.assertEqual(r['ce_targets'],2);self.assertEqual(r['actual_x_tokens'],3)
        self.assertEqual(source,before)

    def test_malformed_frozen_record_and_count_are_rejected(self):
        for key,value in [('ce_targets',1),('record_sha256','0'*64)]:
            rows=self.rows();rows[0][key]=value
            with self.assertRaises(ValueError):d.inventory(rows)

    def test_sequence_eos_and_chat_end_are_separate_native_ids(self):
        student={'<eos>':2,'<|im_start|>':3,'<|im_end|>':4}
        teacher={'<|endoftext|>':248044,'<|im_start|>':248045,'<|im_end|>':248046}
        result=d.native_special_map(student,teacher,dict(eos_token='<|endoftext|>'))
        self.assertEqual(result,{248044:2,248045:3,248046:4})
        with self.assertRaises(ValueError):d.native_special_map(dict(student,**{'<eos>':4}),teacher,dict(eos_token='<|endoftext|>'))


if __name__=='__main__':unittest.main()
