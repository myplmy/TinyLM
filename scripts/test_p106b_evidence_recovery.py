#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from collections import Counter
from tokenizers import Tokenizer
from scripts import p106b_evidence_recovery as f
from scripts import diag_p106b_repair_role_course as old


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tok=Tokenizer.from_file(str(old.training.data.TOKENIZER))

    def test_all_families_counterfactual_query_sufficiency(self):
        for index in range(8):
            g=f.base.graph(index)
            for language in ('ko','en'):
                rows=[f.make(g,language,m,True,0,self.tok) for m in range(4)]
                self.assertEqual([r['meta']['query_sufficient'] for r in rows],[False,True,True,False])
                self.assertEqual(len({r['meta']['semantic_root_id'] for r in rows}),4)
                for mode in range(4):self.assertTrue(f.make(g,language,mode,False,0,self.tok)['meta']['query_sufficient'])

    def test_same_reference_is_both_sufficient_and_insufficient_for_different_queries(self):
        for i in range(4):
            g=f.base.graph(i)
            rows=[f.make(g,'en',m,True,2,self.tok) for m in range(4)]
            for a,b in ((0,2),(1,3)):
                self.assertEqual(rows[a]['meta']['source_reference'],rows[b]['meta']['source_reference'])
                self.assertNotEqual(rows[a]['meta']['query_sufficient'],rows[b]['meta']['query_sufficient'])

    def test_omission_is_a_declared_fact_not_a_number_blacklist(self):
        g=next(f.base.graph(i) for i in range(0,4000,4) if f.base.graph(i)['ages'][0]==f.base.graph(i)['grades'][1])
        v=f.base.values(g,'en');self.assertEqual(v['boy_age'],v['girl_grade'])
        ref=f.reference(g,'en','boy_age')
        self.assertNotIn("The boy's age is",ref);self.assertIn("The girl's grade is "+v['girl_grade'],ref)

    def test_year_duration_is_derived_not_absent_because_no_literal_duration(self):
        g=f.base.graph(3);rows=[f.make(g,'en',m,True,0,self.tok) for m in range(4)]
        self.assertEqual(rows[1]['meta']['first_required_keys'],['end','start'])
        self.assertTrue(rows[1]['meta']['query_sufficient'])
        self.assertEqual(f.wrap.text(rows[1]['messages'][1]),str(g['end']-g['start']))
        self.assertEqual(rows[0]['meta']['first_response_intent'],'ASK_FOR_MISSING_FACT')

    def test_second_supplies_missing_fact_and_all_four_third_updates_are_recomputed(self):
        for i in range(4):
            g=f.base.graph(i);v=f.base.values(g,'en')
            for mode in range(4):
                a=f.make(g,'en',mode,False,0,self.tok);b=f.make(g,'en',mode,True,0,self.tok)
                self.assertEqual(a['messages'][2:],b['messages'][2:])
                field=b['meta']['requested_fields'][1]
                self.assertEqual(f.wrap.text(b['messages'][3]),v[field])
                last=f.wrap.text(b['messages'][5])
                expected=(str(g['ages'][0]+g['delta']) if i==0 else str(g['area']+g['delta']) if i==1 else
                          v['replacement'] if i==2 else str(g['end']+g['delta']-g['start']))
                self.assertEqual(last,expected)

    def test_all_three_assistant_turns_are_positive_in_actual_encoder(self):
        for i in range(4):
            row=f.make(f.base.graph(i),'ko',0,True,0,self.tok);rec,_=old.factory.encode(row,self.tok)
            self.assertLessEqual(rec.x_tokens,1024)
            self.assertEqual({s for y,s in zip(rec.y,rec.segments) if y!=-100},{1,2,3})

    def test_initial_visible_facts_not_unused_updates_determine_neutral_group(self):
        for i in range(4):
            g=f.base.graph(i);rows=[f.make(g,l,m,p,s,self.tok) for l in ('ko','en') for m in range(4)
                for p in (False,True) for s in (0,2)]
            self.assertEqual(len({r['meta']['neutral_root'] for r in rows}),1)

    def test_balanced_graphs_and_exclusion_of_previous_visible_facts(self):
        oldgraphs=f.base.graphs(128,'test');excluded={f.neutral(g) for g in oldgraphs}
        new=f.graphs(128,'test',exclude=excluded)
        self.assertFalse(excluded&{f.neutral(g) for g in new})
        self.assertEqual(Counter(g['family'] for g in new),{k:32 for k in f.base.FAMILIES})

    def test_hidden_availability_labels_and_values_are_not_injected_into_reference(self):
        g=f.base.graph(1);row=f.make(g,'en',0,True,0,self.tok)
        self.assertNotIn('ASK_FOR_MISSING_FACT',row['meta']['source_reference'])
        self.assertNotIn('insufficient',row['meta']['source_reference'])
        self.assertEqual(row['meta']['teacher_calls'],0);self.assertFalse(row['meta']['formal_train_ready'])

    def test_invalid_conditions_and_undeclared_omissions_rejected(self):
        g=f.base.graph(1)
        with self.assertRaises(ValueError):f.make(g,'en',4,True,0,self.tok)
        with self.assertRaises(ValueError):f.reference(g,'en','not_a_field')


if __name__=='__main__':unittest.main()
