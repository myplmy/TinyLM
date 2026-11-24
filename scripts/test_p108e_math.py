"""Physical-coordinate and local-proposal contracts independent of TinyLM."""
import unittest
import numpy as np
from scripts import p108e_math as study


class LocalWinnerContracts(unittest.TestCase):
    def test_right_basis_preserves_target_and_normal_nullspace(self):
        target=np.array([[1.,2.,0.,0.],[0.,1.,0.,0.]])
        full=np.concatenate([target,np.array([[0.,0.,1.,0.]])])
        basis,record=study.right_basis(target,full,np.array([[0.,0.,0.,1.]]),np.ones(3),prompt_extra=1)
        np.testing.assert_allclose(target@basis.T@basis,target,atol=1e-12)
        np.testing.assert_allclose(basis[:,3],0,atol=1e-12)
        self.assertLess(record["orthogonality_max"],1e-12)

    def test_left_retention_and_cap_are_reported(self):
        planes=np.array([[[3.,0.],[0.,1.]]])
        basis,covariance,record=study.left_basis(planes,np.ones(1),retention=.99,rank_cap=1)
        self.assertTrue(record["rank_cap_hit"])
        self.assertAlmostEqual(record["retained_energy"],.9)

    def test_coefficient_norm_is_physical_before_materialization(self):
        left=np.eye(3)[:,:2];right=np.eye(4)[:2]
        theta=np.array([1.,2.,3.,4.]);matrix=study.reconstruct(theta,left,right)
        self.assertAlmostEqual(np.linalg.norm(theta),np.linalg.norm(matrix))

    def test_single_and_joint_known_qp(self):
        blocks={0:np.ones((1,1)),1:np.ones((1,1))};current={0:np.zeros(1),1:np.zeros(1)}
        single,record=study.proposal(blocks,current,np.array([-1.]),[0],10.,desired=.2)
        joint,record=study.proposal(blocks,current,np.array([-1.]),[0,1],10.,desired=.2)
        self.assertAlmostEqual(single[0][0],1.2,places=7)
        self.assertAlmostEqual(joint[0][0],.6,places=7)
        self.assertAlmostEqual(joint[1][0],.6,places=7)

    def test_repeat_budget_is_original_centred_with_fixed_other_layer(self):
        blocks={0:np.ones((1,1)),1:np.ones((1,1))};current={0:np.array([.6]),1:np.array([.8])}
        result,record=study.proposal(blocks,current,np.array([-5.]),[0],1.)
        self.assertLessEqual(np.sqrt(sum(float(v@v)for v in result.values())),1.)
        np.testing.assert_array_equal(result[1],current[1])

    def test_choice_prioritizes_whole_question_then_hinge(self):
        a=dict(score=dict(questions_all_gold=1,mean_hinge=.4),actual_norm=3.,alpha=1.,layer=13)
        b=dict(score=dict(questions_all_gold=0,mean_hinge=.1),actual_norm=1.,alpha=.5,layer=0)
        self.assertLess(study.rank_key(a),study.rank_key(b))

    def test_question_success_is_content_and_eot_together(self):
        result=study.score(np.array([.3,-.1,.2,.2]),[(0,2),(2,4)])
        self.assertEqual(result["questions_all_gold"],1)
        self.assertEqual(result["positions_gold"],3)


if __name__=="__main__":unittest.main()
