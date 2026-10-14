"""Bounded CPU contracts; no checkpoint, cache, teacher or GPU reads."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from collections import defaultdict
from scripts import p106b_retention_course as data


class Contracts(unittest.TestCase):
    def test_quadruples_and_first_value_baseline(self):
        rows = data.binding_rows('test', per_family=2)
        groups = defaultdict(list)
        for row in rows:
            meta = row['meta']; groups[meta['semantic_root_id']].append(row)
            self.assertEqual(data.text(row,-1), meta['mapping'][meta['requested_entity']])
        self.assertEqual(len(rows),32)
        self.assertTrue(all(len(v)==4 for v in groups.values()))
        self.assertEqual(sum(data.text(r,-1)==r['meta']['first_value'] for r in rows),16)

    def test_counts_and_disjoint_splits(self):
        rows=data.code_rows(); counts=data.validate_splits(rows)
        self.assertEqual({s:len(v) for s,v in rows.items()},dict(train=5120,dev=640,test=640))
        self.assertEqual(counts['train']['binding_color'],2048)
        self.assertEqual(counts['train']['update'],256)

    def test_unordered_mapping_unique(self):
        rows=data.binding_rows('train',per_family=32)
        mappings=defaultdict(set)
        for r in rows:
            m=r['meta']; key=(m['language'],m['kind'],tuple(sorted(m['mapping'].items())))
            mappings[key].add(m['semantic_root_id'])
        self.assertTrue(all(len(v)==1 for v in mappings.values()))

    def test_native_windows_disjoint(self):
        offsets=data.native_offsets(100000,32)
        self.assertEqual(offsets,data.native_offsets(100000,32))
        ordered=sorted(offsets)
        self.assertTrue(all(b-a>=1025 for a,b in zip(ordered,ordered[1:])))
        with self.assertRaises(ValueError):data.native_offsets(1024,1)

    def test_code_judges_not_word_blacklists(self):
        self.assertTrue(data.exact('{"answer": "red"}','{"answer":"red"}','EXACT_JSON_OBJECT'))
        self.assertFalse(data.exact('A is red','red','EXACT_SCALAR'))
        self.assertIsNone(data.exact('anything','teacher','UNSCORED_PUBLIC_QA'))
        self.assertFalse(data.exact('3+2=5','5','EXACT_INTEGER'))

    def test_global_normalization_and_zero_replay(self):
        import torch
        x=torch.tensor([.2,.7],requires_grad=True)
        sft=(x**2).sum(); native=(3*x).sum()
        total=data.combined_loss(sft,11,native,7,0.)
        g=torch.autograd.grad(total,x,retain_graph=True)[0]
        self.assertTrue(torch.equal(g,torch.autograd.grad(sft/11,x,retain_graph=True)[0]))
        a=data.combined_loss(sft,11,native,7,.25)
        self.assertTrue(torch.allclose(torch.autograd.grad(a,x)[0],2*x.detach()/11+.25*3/7))

    def test_masks_and_padding(self):
        import torch
        from tinylm.train.mtp_sft import Record,pad_records
        from tinylm.data.sft import IGNORE
        r=Record([3,4,5],[IGNORE,5,6],[0,1,1])
        x,y,segments=pad_records([r],0,fixed_width=8,batch_size=2)
        self.assertEqual(int(y.ne(IGNORE).sum()),2)
        self.assertEqual(int(segments.gt(0).sum()),2)
        self.assertTrue(torch.all(y[1]==IGNORE))


if __name__=='__main__':unittest.main()
