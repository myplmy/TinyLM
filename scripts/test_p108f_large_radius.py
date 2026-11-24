"""Genuinely unused blocks, duplicate exclusion and terminal JSON contracts."""
import json
import unittest
from scripts import diag_p108f_large_radius as owner


class LargeRadiusContracts(unittest.TestCase):
    def test_four_unused_block_indices(self):
        questions=[str(i) for i in range(128)];excluded=[0,1,2,3,32,33,64,65,96,97,126,127]
        self.assertEqual(owner.select_cases(questions,excluded),[4,34,66,98])

    def test_duplicate_question_is_not_fresh(self):
        questions=[str(i) for i in range(128)];questions[4]=questions[0];questions[34]=questions[5]
        excluded=[0,1,2,3,32,33,64,65,96,97,126,127]
        self.assertEqual(owner.select_cases(questions,excluded),[5,35,66,98])
        with self.assertRaises(ValueError):owner.select_cases(questions[:32],excluded)

    def test_all_comparisons_and_terminal_summary_are_json_serializable(self):
        metrics=dict(exact_argmax=True,logit_rmse=.5,response_relative_error=.25)
        rows=[dict(baseline_exact=False,comparisons={name:metrics.copy() for name in owner.PREDICTORS})]
        encoded=json.dumps(dict(summary=owner.summarize(rows),status="COMPLETE",error=None))
        result=json.loads(encoded)["summary"]["QUADRATIC_300"]
        self.assertEqual((result["argmax_exact"],result["gained_against_no_change"],result["lost_against_no_change"]),(1,1,0))


if __name__=="__main__":unittest.main()
