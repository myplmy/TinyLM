"""Counterfactual controller keeps the owner body/state untouched."""
from unittest.mock import patch
import unittest
from scripts import diag_p108b_regularizer as r


class RegularizerTests(unittest.TestCase):
    def test_modes_have_identical_design_other_than_explicit_preservation_origin(self):
        specs=r.specs();self.assertEqual(len(specs),4)
        for suffix in('SAME4','ADAPT_R4'):
            a=next(x for x in specs if x.name=='REGINC_'+suffix)
            b=next(x for x in specs if x.name=='REGTOTAL_'+suffix)
            self.assertEqual({k:v for k,v in vars(a).items()if k!='name'},
                             {k:v for k,v in vars(b).items()if k!='name'})

    def test_private_controller_reuses_body_without_mutating_original_solver(self):
        original=r.owner.propose.__globals__['solver']
        a=r.controller(False);b=r.controller(True)
        self.assertIs(a.__code__,r.owner.run.__code__)
        self.assertIs(b.__globals__['propose'].__code__,r.owner.propose.__code__)
        self.assertFalse(a.__globals__['solver'].solve_increment.keywords['total_preservation'])
        self.assertTrue(b.__globals__['solver'].solve_increment.keywords['total_preservation'])
        self.assertIs(r.owner.propose.__globals__['solver'],original)


if __name__=='__main__':unittest.main()
