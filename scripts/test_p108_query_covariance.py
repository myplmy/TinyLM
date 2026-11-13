import copy
import unittest
from scripts import diag_p108_query_covariance as d


class QueryCovariance(unittest.TestCase):
    def source(self):
        return dict(facts=[dict(selected=dict(fact=str(i),layer=8 if i%2 else 11,
            oracle_fit=dict(exact=1),value_delta=[float(i+1)]*768,dev_exact=False)) for i in range(12)])

    def test_frozen_selection_is_not_recomputed_from_other_scores(self):
        source=self.source();before=copy.deepcopy(source);selected=d.frozen_selected(source)
        self.assertEqual(selected,[f['selected'] for f in before['facts']]);self.assertEqual(source,before)

    def test_missing_duplicate_layer_and_value_changes_are_rejected(self):
        variants=[]
        a=self.source();a['facts'].pop();variants.append(a)
        a=self.source();a['facts'][1]['selected']['fact']='0';variants.append(a)
        a=self.source();a['facts'][0]['selected']['layer']=2;variants.append(a)
        a=self.source();a['facts'][0]['selected']['value_delta']=[];variants.append(a)
        for value in variants:
            with self.assertRaises(ValueError):d.frozen_selected(value)

    def test_reference_prefers_covariance_and_names_plain_fallback(self):
        a,b=dict(name='plain'),dict(name='covariance')
        self.assertIs(d.choose_reference([a,b]),b)
        self.assertIs(d.choose_reference([a]),a)
        self.assertIsNone(d.choose_reference([]))


if __name__=='__main__':unittest.main()
