#!/usr/bin/env python3
"""CPU source-inventory fixtures; no source files, tokenizer files or models."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.diag_p106b_source_inventory import Inventory,PER_GROUP,token_sample
from scripts.test_p106b_capability_prepare import row
from tinylm.data.prepare import SyntheticTokenizer


class InventoryTests(unittest.TestCase):
    def test_unassigned_source_is_not_labeled_bad_content(self):
        inventory=Inventory();inventory.add(row(family='SODA'))
        report=inventory.summary()
        self.assertEqual(report['original_rows'],1)
        self.assertEqual(report['current_builder_unassigned_rows'],1)
        self.assertEqual(report['quality'],'NOT_REVIEWED')
        self.assertFalse(report['new75M_ready'])
        self.assertEqual(report['full_usable_tokens'],'NOT_MEASURED')

    def test_source_roles_and_code_followups_are_not_conflated(self):
        one=row();multi=copy.deepcopy(row(1));multi['messages']+=copy.deepcopy(one['messages'])
        inventory=Inventory();inventory.add(one);inventory.add(multi)
        self.assertEqual(inventory.summary()['groups'][0]['role_sequence_rows'],1)
        self.assertEqual(inventory.summary()['groups'][0]['normalized_user_turns'],{'1':1,'2':1})

    def test_hash_sample_order_independent_and_bounded(self):
        rows=[row(i) for i in range(60)]
        for i,r in enumerate(rows):r['meta']['source_id']=str(i)
        forward=Inventory();reverse=Inventory()
        for r in rows:forward.add(r)
        for r in reversed(rows):reverse.add(r)
        self.assertEqual(list(forward.rows()),list(reverse.rows()))
        self.assertEqual(len(list(forward.rows())),PER_GROUP)

    def test_original_row_and_provenance_not_mutated(self):
        r=row();before=copy.deepcopy(r);inventory=Inventory();inventory.add(r)
        sample=list(inventory.rows())[0]
        self.assertEqual(r,before);self.assertEqual(sample['original'],before)
        self.assertEqual(sample['quality'],'NOT_REVIEWED')

    def test_tokens_are_sampled_not_measured_inventory(self):
        inventory=Inventory();inventory.add(row())
        result=token_sample(list(inventory.rows())[0],SyntheticTokenizer())
        self.assertGreater(result['original_nonpadding_tokens'],0)
        self.assertGreater(result['derived_targets'],0)
        self.assertEqual(inventory.summary()['full_usable_tokens'],'NOT_MEASURED')


if __name__=='__main__':unittest.main()
