import unittest
from scripts import p108b_eval_data as data
from scripts import p108_value_edit as old
from scripts.diag_p108_value_edit import protected_rows


class EvalDataTests(unittest.TestCase):
    def legacy(self):
        ids={'kr_capital','fr_capital_ko','water_ko','earth_ko'}
        return [r for r in old.facts() if r['fact'] in ids and r['split']!='test']+old.relative_facts()+protected_rows()

    def test_roles_counts_and_real_multiturn_count(self):
        legacy=self.legacy();dev=data.selection(legacy);final=data.final_language()
        proof=data.validate(dev,final,legacy)
        self.assertEqual(proof['final_scenarios'],96)
        self.assertEqual(proof['final_actual_user_turns'],240)

    def test_final_boolean_gold_is_computed_consistently(self):
        for item in data.final_language():
            if item['id'].startswith('final:other:'):
                i=int(item['id'].split(':')[2])
                if 8<=i<16:
                    a,b=bool(i%2),bool((i//2)%2)
                    actual=(a and b) if i<12 else (a or b)
                    expected=('참' if actual else '거짓') if item['language']=='ko' else str(actual).lower()
                    self.assertEqual(item['expected'],expected)

    def test_no_implicit_answers_to_missing_context(self):
        missing=[r for r in data.final_language() if r.get('expected_behavior')=='clarify_missing_referent']
        self.assertEqual(len(missing),16)
        self.assertTrue(all(r['expected'] is None for r in missing))

    def test_final_cannot_be_mixed_into_selector(self):
        legacy=self.legacy();dev=data.selection(legacy);final=data.final_language()
        dev[0]['split']='final_test'
        with self.assertRaises(ValueError):data.validate(dev,final,legacy)


if __name__=='__main__':unittest.main()
