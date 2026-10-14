"""Pure authored-case factorial checks; models/source data never read."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import unittest
from collections import Counter,defaultdict
from scripts.diag_p106b_source_binding import cases

class BindingTests(unittest.TestCase):
    def test32_language_position_balance(self):
        rows=cases();self.assertEqual(len(rows),32)
        self.assertEqual(Counter(r['language'] for r in rows),{'ko':16,'en':16})
        self.assertEqual(Counter(r['target_is_first'] for r in rows),{True:16,False:16})
    def test_same_facts_target_flip(self):
        groups=defaultdict(list)
        for r in cases():groups[(r['root'],tuple(r['ordered_entities']))].append(r)
        for pair in groups.values():
            self.assertEqual(len(pair),2);self.assertEqual(pair[0]['same_fact_mapping'],pair[1]['same_fact_mapping'])
            self.assertNotEqual(pair[0]['gold'],pair[1]['gold'])
    def test_order_flip_keeps_target_answer(self):
        groups=defaultdict(list)
        for r in cases():groups[(r['root'],r['requested_entity'])].append(r)
        for pair in groups.values():
            self.assertEqual(pair[0]['gold'],pair[1]['gold']);self.assertNotEqual(pair[0]['target_is_first'],pair[1]['target_is_first'])

if __name__=='__main__':unittest.main()
