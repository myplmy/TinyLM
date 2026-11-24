"""Independent counterexamples for edit-policy selection and budget claims."""
import unittest
import torch
from scripts import p108b_policy as p


class PolicyTests(unittest.TestCase):
    def test_path_and_net_budgets_are_distinct(self):
        net=p.Policy('net',4,'same')
        path=p.Policy('path',4,'same',budget_mode='path')
        self.assertEqual([p.budget_limit(net,j,8.)for j in range(1,5)],[2.,4.,6.,8.])
        self.assertEqual([p.budget_limit(path,j,8.)for j in range(1,5)],[2.]*4)
        # Two opposite2-norm edits have path4 and net0; they are not matched.
        a=torch.tensor([2.,0.]);b=-a
        self.assertEqual(float((a+b).norm()),0.)
        self.assertEqual(float(a.norm()+b.norm()),4.)

    def test_normal_requested_repetition_is_preserved(self):
        rows=[dict(protected=True,exact=True,diagnostics=dict(loop_indicator=True)),
              dict(protected=False,exact=False,diagnostics=dict(loop_indicator=True)),
              dict(protected=True,exact=False,diagnostics=dict(loop_indicator=True))]
        self.assertEqual(p.unwanted_loops(rows),2)

    def test_complete_order_and_distinct_vs_revisit(self):
        order=[9]+[i for i in range(14)if i!=9]
        distinct=p.Policy('d',4,'adaptive_distinct')
        revisit=p.Policy('r',4,'adaptive_revisit')
        kw=dict(best_layer=9,fixed_order=order,visited=[9])
        self.assertNotIn(9,p.eligible_layers(distinct,2,**kw))
        self.assertIn(9,p.eligible_layers(revisit,2,**kw))
        with self.assertRaises(ValueError):p.eligible_layers(distinct,1,best_layer=9,fixed_order=[9],visited=[])

    def test_sparse_support_has_equal_count_and_explicit_random_seed(self):
        torch.manual_seed(2)
        delta=torch.randn(4,32);gradient=torch.randn_like(delta);moment=torch.eye(32)
        spec=p.Policy('s',1,'same',support_denominator=8)
        mask,stats=p.support(spec,delta,gradient,moment)
        self.assertTrue(torch.equal(mask.sum(1),torch.tensor([4]*4)))
        self.assertTrue(stats['approximation_ignores_offdiagonal_interactions'])
        random=p.Policy('r',1,'same',support_denominator=8,support_rule='random',random_seed=1337)
        self.assertTrue(torch.equal(p.support(random,delta,gradient,moment)[0],p.support(random,delta,gradient,moment)[0]))

    def test_matrix_is_unique_and_final_budget_common(self):
        specs=p.primary_policies()
        self.assertEqual(len({s.name for s in specs}),18)
        self.assertTrue(all(p.budget_limit(s,s.rounds,13.)==13. for s in specs))
        self.assertEqual(len(p.diagnostic_policies()),6)

    def test_protection_gain_can_break_selection_tie_without_final_answers(self):
        def record(layer,ce,kl,protect,loop):
            return dict(layer=layer,objective=dict(fit_ce=ce,preserve_kl=kl),
                dev_corrected=dict(protected_correct_ids=[],target_exact=0,other_exact=0,
                    protected_exact=protect,unwanted_loops=loop,question_echoes=0,empty=0))
        records=[record(0,1.,10.,0,0),record(1,2.,0.,2,1)]
        self.assertEqual(p.choose_selection(records,[])['chosen']['layer'],1)


if __name__=='__main__':unittest.main()
