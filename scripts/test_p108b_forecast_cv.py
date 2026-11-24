"""Independent synthetic calibration/fold/ranking checks, no TinyLM or files."""
import unittest
import numpy as np
from scripts import p108b_forecast_cv as c


class ForecastContracts(unittest.TestCase):
    def test_cross_language_same_fact_has_one_group(self):
        self.assertEqual(c.semantic_group("de_capital_ko"),c.semantic_group("de_capital_en"))
        self.assertNotEqual(c.semantic_group("de_capital_ko"),c.semantic_group("it_capital_en"))

    def test_fold_excludes_both_held_layer_and_held_concept(self):
        layers=np.array([0,0,1,1,2,2]);groups=np.array(["a","b","a","b","a","b"])
        train,test=c.fold_indices(layers,groups,1,"a")
        self.assertEqual(np.where(train)[0].tolist(),[1,5]);self.assertEqual(np.where(test)[0].tolist(),[2])

    def test_affine_recovers_known_law_on_unseen_predictors(self):
        p=np.array([-2.,-1.,1.,2.]);y=2*p+3
        actual,_=c.predict("AFFINE",p,p*0,y,np.ones(4),np.array([0.,4.]),np.zeros(2))
        np.testing.assert_allclose(actual,[3.,11.],atol=1e-12)

    def test_held_labels_cannot_change_a_fitted_prediction(self):
        p=np.arange(6,dtype=float);layers=np.array([0,0,1,1,2,2]);groups=np.array(["a","b"]*3)
        train,test=c.fold_indices(layers,groups,1,"a");y=p*2+3
        first,_=c.predict("AFFINE",p[train],layers[train],y[train],np.ones(train.sum()),p[test],layers[test])
        y[~train]=1e9
        second,_=c.predict("AFFINE",p[train],layers[train],y[train],np.ones(train.sum()),p[test],layers[test])
        np.testing.assert_array_equal(first,second)

    def test_group_weights_balance_repeated_language_variants(self):
        w=c.group_weights(["a","a","a","b"])
        self.assertAlmostEqual(w[:3].sum(),.5);self.assertAlmostEqual(w[3],.5)

    def test_auc_ties_and_perfect_reversed_rank(self):
        self.assertEqual(c.auc([1,1],[True,False]),.5)
        self.assertEqual(c.auc([2,1],[True,False]),1.)
        self.assertEqual(c.auc([1,2],[True,False]),0.)


if __name__=="__main__":unittest.main()
