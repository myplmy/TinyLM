#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_dualqa_checkpoint_choice as c


def report():
    return dict(status='TRAINED_NEW_SOURCE_TEST_PENDING',updates=176,history=[
        dict(epoch=i,updates=44*i,dev=dict(source_ce=v,code_ce=1.),checkpoint='epoch'+str(i),checkpoint_sha256=str(i)*64)
        for i,v in enumerate([2.,1.5,1.8,1.7],1)])


class Choice(unittest.TestCase):
    def test_choose_only_dev_not_latest(self):
        r=c.choose(report());self.assertEqual(r['epoch'],2);self.assertFalse(r['selected_by_test'])
    def test_changing_code_native_or_test_cannot_change_choice(self):
        r=report();r['test']={'accuracy':1};r['native']={'ce':1e-9}
        for h in r['history']:h['dev']['code_ce']=h['epoch']*100
        self.assertEqual(c.choose(r)['epoch'],2)
    def test_equal_loss_chooses_early_epoch(self):
        r=report();r['history'][2]['dev']['source_ce']=1.5;self.assertEqual(c.choose(r)['epoch'],2)
    def test_missing_epoch_or_nonfinite_rejected(self):
        r=report();r['history'].pop()
        with self.assertRaises(ValueError):c.choose(r)
        r=report();r['history'][0]['dev']['source_ce']=float('nan')
        with self.assertRaises(ValueError):c.choose(r)
    def test_read_only_and_no_auto_primary_replacement(self):
        r=report();before=copy.deepcopy(r);out=c.choose(r);self.assertEqual(r,before);self.assertTrue(out['final4epoch_stays_primary'])


if __name__=='__main__':unittest.main()
