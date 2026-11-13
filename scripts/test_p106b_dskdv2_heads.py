import unittest
import torch
from scripts.p106b_dskdv2_heads import gather_rows


class Slice:
    def __init__(self,tensor):self.value=tensor;self.requests=[]
    def get_shape(self):return list(self.value.shape)
    def __getitem__(self,key):self.requests.append(key);return self.value[key]


class BoundedHeadRows(unittest.TestCase):
    def test_preserves_arbitrary_native_id_order_across_chunks_without_loading_whole_head(self):
        tensor=torch.arange(80,dtype=torch.float32).reshape(20,4).to(torch.bfloat16);view=Slice(tensor)
        observed=gather_rows(view,[19,0,8,4],rows=20,width=4,chunk=5)
        torch.testing.assert_close(observed,tensor[[19,0,8,4]].float(),rtol=0,atol=0)
        self.assertEqual(len(view.requests),3)
        self.assertTrue(all(key[0].stop-key[0].start<=5 for key in view.requests))
    def test_duplicate_outside_or_shape_mismatch_native_ids_are_rejected(self):
        view=Slice(torch.zeros(5,3))
        for ids,rows,width in [([1,1],5,3),([5],5,3),([1],6,3),([1],5,4)]:
            with self.subTest(ids=ids,rows=rows,width=width),self.assertRaises(ValueError):
                gather_rows(view,ids,rows=rows,width=width)
    def test_nonfinite_original_chunk_is_not_repaired_or_skipped(self):
        tensor=torch.zeros(5,3);tensor[2,1]=float('nan')
        with self.assertRaises(ValueError):gather_rows(Slice(tensor),[2],rows=5,width=3)


if __name__=='__main__':unittest.main()
