from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import diag_p106b_binding_factor_probe as code


class Contracts(unittest.TestCase):
    def test_first_target_balanced_across_four_views(self):
        rows=code.source.course.method.source.binding_rows('train',1)
        labels=[code.labels_for(row) for row in rows]
        self.assertEqual(sum(v['requested_is_first']=='1' for v in labels),len(rows)//2)
        self.assertTrue(all(v['first']!=v['last'] for v in labels))

    def test_wrong_producer_metadata_rejected(self):
        row=code.source.course.method.source.binding_rows('train',1)[0]
        row['meta']['first_value']='wrong'
        with self.assertRaises(ValueError):code.labels_for(row)

    def test_test_labels_cannot_choose_checkpoint(self):
        import torch
        torch.set_num_threads(1)
        x=torch.tensor([[-1.,0.],[1.,0.],[-1.,0.],[1.,0.]])
        data={s:x for s in ('train','dev','test')};y={s:torch.tensor([0,1,0,1]) for s in data}
        meta={s:[dict(root='fixture',label=int(v)) for v in y[s]] for s in data}
        a=code.classifier(data,y,meta,2,steps=20)
        other={s:v.clone() for s,v in y.items()};other['test']=1-other['test']
        second=copy.deepcopy(meta)
        for m,label in zip(second['test'],other['test']):m['label']=int(label)
        b=code.classifier(data,other,second,2,steps=20)
        self.assertEqual((a['selected_step'],a['selected_dev_ce']),(b['selected_step'],b['selected_dev_ce']))
        self.assertEqual(a['classes'],2)


if __name__=='__main__':unittest.main()
