import unittest
from scripts import diag_p108b_geometry as driver


class GeometryTests(unittest.TestCase):
    def test_equal_absolute_budget_is_not_each_layer_five_percent(self):
        norms={i:400.+i for i in range(14)}
        budget,label=driver.common_budget(norms)
        self.assertEqual(budget,driver.ORIGINAL_BUDGET)
        self.assertEqual(label,'LEGACY_EXACT_ABSOLUTE_B0')
        self.assertNotEqual(budget,.05*norms[0])

    def test_incompatible_legacy_budget_is_labelled_as_a_lower_panel(self):
        norms={i:300.+i for i in range(14)}
        budget,label=driver.common_budget(norms)
        self.assertLess(budget,15.)
        self.assertEqual(label,'COMMON_LOWER_5PCT_PANEL_NOT_LEGACY_MATCHED')
        with self.assertRaises(ValueError):driver.common_budget({0:300.})

    def test_dev_is_used_for_lambda_not_per_question_model_switching(self):
        def candidate(layer,ce,kl,exact,correct):
            return dict(layer=layer,objective=dict(fit_ce=ce,preserve_kl=kl),
                dev=dict(target=dict(exact=exact),other=dict(exact=0),
                         all=dict(loop_indicators=0,question_echoes=0,empty=0)),
                dev_protected_correct_ids=correct)
        records=[candidate(0,1.,10.,24,[]),candidate(1,2.,0.,20,['safe'])]
        selected=driver.select_lambda(records,['safe'])
        self.assertEqual(selected['chosen']['layer'],1)
        self.assertEqual(len(selected['fixed_layer_order']),2)


if __name__=='__main__':unittest.main()
