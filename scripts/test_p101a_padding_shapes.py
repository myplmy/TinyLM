import unittest
import torch
from scripts import p101a_padding_shapes as shapes
from tinylm.train.mtp_sft import Record, pad_records, horizon_targets, count_record


class ShapeContracts(unittest.TestCase):
    def test_real_context_tail_controls_width_not_supervised_end(self):
        r = Record(list(range(969)), [7,8]+[-100]*967, [1,1]+[0]*967)
        self.assertEqual([shapes.width([len(r.x)],q) for q in shapes.POLICIES], [992,1024,1024])
        x,y,s = pad_records([r],0,fixed_width=992,batch_size=8)
        self.assertEqual(x[0,:969].tolist(),r.x)
        self.assertEqual(count_record(r)[1],int(horizon_targets(y,s,1)[1].sum()))

    def test_all_horizon_mass_and_order_preserved_for32_and64(self):
        r = Record(list(range(130)), [-100]*125+[7,8,9,10,4], [0]*125+[1]*5)
        full = pad_records([r],0,fixed_width=1024,batch_size=8)
        for q in (32,64):
            crop=pad_records([r],0,fixed_width=shapes.width([len(r.x)],q),batch_size=8)
            for a,b in zip(full,crop):torch.testing.assert_close(a[:,:len(r.x)],b[:,:len(r.x)])
            for h in (1,2,3,4):
                self.assertEqual(int(horizon_targets(full[1],full[2],h)[1].sum()),
                                 int(horizon_targets(crop[1],crop[2],h)[1].sum()))

    def test_pair_slots_uses_each_width_squared(self):
        s=shapes.histogram_summary({32:1,96:1})
        self.assertEqual(s['pair_slots'],8*(32**2+96**2))
        self.assertNotEqual(s['pair_slots'],8*2*((32+96)//2)**2)

    def test_full_group_greedy_covers_every_actual_shape(self):
        def g(a,b,n):
            return dict(widths={str(q):[a]*8+[b]*8 for q in shapes.POLICIES},
                        max_record=b,denominators={'1':n},actual_x_tokens=200)
        groups=[g(128,256,10),g(384,512,20),g(640,1024,30)]
        picked=shapes.select_groups(groups)
        self.assertEqual(picked['covered'],picked['required'])
        self.assertEqual(set(picked['indices']),{0,1,2})

    def test_invalid_length_policy_and_incomplete_groups_fail(self):
        for lengths,q in (([1025],32),([0],64),([True],128),([],32),([50],16)):
            with self.assertRaises(ValueError):shapes.width(lengths,q)
        with self.assertRaises(ValueError):shapes.select_groups([])


if __name__=='__main__':unittest.main()
