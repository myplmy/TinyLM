"""Code-known curriculum pairing/split/target tests; no model/real data."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import unittest
from collections import Counter,defaultdict
from scripts.diag_p106b_binding_course import build,KO,EN
from scripts.p106b_visible_source import text

class BindingCourseTests(unittest.TestCase):
    def test_counts_and_source_split(self):
        rows=build();self.assertEqual(len(rows['train']),4096);self.assertEqual(len(rows['val']),512)
        a={r['meta']['semantic_root_id'] for r in rows['train']};b={r['meta']['semantic_root_id'] for r in rows['val']};self.assertFalse(a&b)
        self.assertEqual(Counter(r['meta']['language'] for r in rows['train']),{'ko':2048,'en':2048})
    def test_each_root_four_views_balance_and_correct_gold(self):
        groups=defaultdict(list)
        for r in build()['train']:
            m=r['meta'];groups[m['semantic_root_id']].append(r);self.assertEqual(text(r['messages'][-1]),m['same_fact_mapping'][m['requested_entity']])
        for group in groups.values():
            self.assertEqual(len(group),4);self.assertEqual(Counter(r['meta']['target_is_first'] for r in group),{True:2,False:2})
    def test_new_names_do_not_train_on_diagnostic_names(self):
        for tables in (KO,EN):self.assertFalse(set(tables['train'])&set(tables['val']))
        self.assertFalse({'Mina','Noah'}&set(EN['train']+EN['val']))
        self.assertFalse({'가온','나래'}&set(KO['train']+KO['val']))

if __name__=='__main__':unittest.main()
