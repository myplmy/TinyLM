"""Independent dialogue-context and prospective-decoder-selection tests."""
import unittest
from scripts import diag_p108b_evaluate as api


class EvaluateTests(unittest.TestCase):
    def test_followup_uses_actual_wrong_answer_and_cases_do_not_share_context(self):
        rows=[dict(id='a',question='first',expected='truth',followups=['follow','third']),
              dict(id='b',question='independent',expected=None)]
        seen=[]
        def emit(row,history):
            seen.append((row['id'],list(history)))
            return dict(row,answer='actual wrong '+row['id'])
        records=list(api.dialogue(rows,emit))
        self.assertEqual(len(records),4)
        self.assertEqual(seen[1][1][1]['content'],'actual wrong a')
        self.assertEqual(seen[2][1][-1]['content'],'actual wrong a:turn2')
        self.assertIsNone(records[1]['expected'])
        self.assertEqual(seen[-1][1],[])
        self.assertNotIn('truth',str(seen))

    def test_question_seed_is_same_across_models_and_distinct_by_question(self):
        self.assertEqual(api.seed_for(17,'a'),api.seed_for(17,'a'))
        self.assertNotEqual(api.seed_for(17,'a'),api.seed_for(17,'b'))

    def test_three_stochastic_seeds_are_required_and_protection_precedes_content(self):
        records=[]
        for spec in api.decode.registered():
            for seed in([17,29,43]if spec.temperature else[17]):
                records.append(dict(decoder=spec.name,seed=seed,summary=dict(
                    lost_protected_ids=[]if spec.name=='GREEDY'else['old_correct'],
                    dev=dict(target_exact=0 if spec.name=='GREEDY' else 20,other_exact=0,protected_exact=0),
                    protected_correct=7,unwanted_loops=3,question_echoes=0,empty=0)))
        self.assertEqual(api.select_decoder(records)['chosen']['decoder']['name'],'GREEDY')
        with self.assertRaises(ValueError):api.select_decoder(records[:-1])


if __name__=='__main__':unittest.main()
