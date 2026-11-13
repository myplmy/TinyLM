import unittest
from scripts import diag_p108_nullspace_write as d


class DriverContracts(unittest.TestCase):
    def test_fit_only_gate_ignores_dev_test_and_collapses_fact(self):
        def row(fact,layer,oracle,nll):
            return dict(fact=fact,layer=layer,oracle_fit=dict(exact=oracle),optimization=dict(trace=[dict(nll=nll)]),write=dict(delta_norm=1.),dev_exact=layer==99)
        selected,skipped=d.pick_candidates([row('a',99,0,.01),row('a',5,1,3.),row('a',8,2,5.),row('b',2,0,1.)])
        self.assertEqual([(r['fact'],r['layer']) for r in selected],[('a',8)])
        self.assertEqual(skipped,[dict(fact='b',reason='ORACLE_GATE_NEGATIVE_NOT_RUN')])

    def test_primary_and_large_diagnostic_caps_are_separate(self):
        self.assertEqual(d.cap_status(.05),'PRIMARY_CAP5')
        self.assertEqual(d.cap_status(.050001),'LARGE_EDIT_DIAGNOSTIC_ONLY')
        self.assertEqual(d.cap_status(.20),'LARGE_EDIT_DIAGNOSTIC_ONLY')
        for value in (0.,-.1,.200001,float('nan')):self.assertEqual(d.cap_status(value),'CAP20_REJECTED')


if __name__=='__main__':unittest.main()
