"""Physical budget and actual-history safeguards for the diagnostic replay."""
import unittest
import numpy as np
from scripts import p108e_evaluation as evaluate


class BudgetAndHistory(unittest.TestCase):
    def test_one_budget_is_shared_across_fourteen_owners(self):
        before={i:np.zeros((2,3),np.float32)for i in range(14)}
        after={i:x.copy()for i,x in before.items()}
        after[1][0,0]=3.;after[13][1,2]=4.
        out,receipt=evaluate.match_all(before,after,10.)
        self.assertAlmostEqual(float(out[1][0,0]),6.,places=5)
        self.assertAlmostEqual(float(out[13][1,2]),8.,places=5)
        self.assertAlmostEqual(receipt["actual_norm"],10.,places=5)
        self.assertEqual(sum(np.count_nonzero(v)for v in out.values()),2)

    def test_missing_owner_is_rejected(self):
        with self.assertRaises(ValueError):evaluate.match_all({0:np.zeros((2,3))},{},1.)

    def test_history_keeps_actual_error_not_gold(self):
        row=dict(question="2+3?",expected="5")
        old=[dict(role="user",content="hello")]
        new=evaluate.extend_history(old,row,"6")
        self.assertEqual(new[-1]["content"],"6")
        self.assertEqual(len(old),1)

    def test_cached_guard_answers_are_not_question_fields(self):
        row=dict(id="guard",question="copy",expected="ok",answer="old",generation={"ids":[1]},actual_history=[])
        self.assertEqual(evaluate.question_only(row),dict(id="guard",question="copy",expected="ok"))


if __name__=="__main__":unittest.main()
