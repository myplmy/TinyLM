import copy
import unittest
from scripts import p108b_pm_questions as questions


class TestFreshEvaluationContract(unittest.TestCase):
    def test_counts_and_role(self):
        data=questions.build();self.assertTrue(questions.validate(data,[]))
        self.assertEqual(data['role'],'FINAL_ONLY_NEVER_FIT_OR_SELECT')

    def test_old_question_is_rejected(self):
        data=questions.build()
        with self.assertRaises(ValueError):questions.validate(data,[data['rows'][0]['question']])

    def test_duplicate_rejected(self):
        data=questions.build();data['rows'][1]['question']=data['rows'][0]['question']
        with self.assertRaises(ValueError):questions.validate(data,[])

    def test_closed_answers_are_computed(self):
        rows=[r for r in questions.build()['rows'] if r['family']=='other']
        self.assertEqual(len(rows),32)
        for row in rows:
            p=row['proof'];expected=p['left']+p['right'] if p.get('operation')=='add' else p['value']
            self.assertEqual(row['expected'],str(expected))

    def test_requested_repetition_and_missing_answers_differ(self):
        rows=questions.build()['rows'];rep=[r for r in rows if r.get('allow_repeat')]
        missing=[r for r in rows if r.get('requires_clarification')]
        self.assertEqual(len(rep),8);self.assertEqual(len(missing),8)
        self.assertTrue(all(len(r['expected'].split())==3 for r in rep))
        self.assertTrue(all(r['expected'] is None for r in missing))

    def test_unedited_english_fact_groups_are_explicit(self):
        target=[r for r in questions.build()['rows'] if r['family']=='target']
        self.assertEqual(sum(r['same_fact_in_edit_fit'] for r in target),24)
        self.assertEqual(sum(not r['same_fact_in_edit_fit'] for r in target),8)

    def test_followups_never_supply_gold(self):
        data=questions.build();follow=[r for r in data['rows'] if r.get('followups')]
        self.assertEqual(len(follow),16)
        self.assertTrue(all(r['expected'] is None and len(r['followups'])==1 for r in follow))


if __name__=='__main__':unittest.main()
