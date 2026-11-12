"""Metadata-only guard6 boundaries; no source bodies, tokenizer or cache worker."""
from pathlib import Path
import copy
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch

AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(AUDIT.parents[2])]
import guarded_reviewed_cache_v9 as cache


class Guard6CacheMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=cache.guard.checked_contract()

    def selection(self):
        rows=[dict(id=ident,original_text_sha256='1'*64,
                   selected=dict(decision='EDIT',body='fixture-safe.txt',clean_text_sha256='2'*64))
              for ident in sorted(cache.SAFE_IDS)]
        return dict(rows=rows),dict(rows=copy.deepcopy(rows))

    def restricted_row(self,decision='EDIT'):
        entry=self.contract['actual_filter_metadata_hold']
        choice=dict(decision=decision)
        if decision=='EDIT':
            choice.update(body='must-not-be-opened.txt',clean_text_sha256=entry['original']['sha256'])
        return dict(id=cache.guard.NEW_ID,original_text_sha256=entry['original']['sha256'],selected=choice)

    def test_exact_three_prior_safe_rows_stay_unchanged(self):
        document,prior=self.selection()
        cache.validate_selection(document,prior,self.contract)

    def test_changed_prior_safe_row_is_rejected(self):
        document,prior=self.selection();document['rows'][0]['selected']['body']='changed.txt'
        with self.assertRaises(Exception):cache.validate_selection(document,prior,self.contract)

    def test_actual_filter_body_cannot_be_selected(self):
        document,prior=self.selection();document['rows'].append(self.restricted_row())
        with self.assertRaises(Exception):cache.validate_selection(document,prior,self.contract)

    def test_actual_filter_metadata_hold_is_allowed(self):
        document,prior=self.selection();document['rows'].append(self.restricted_row('HOLD'))
        cache.validate_selection(document,prior,self.contract)

    def test_prior_exact_metadata_exclusion_is_preserved(self):
        document,prior=self.selection()
        key='expanded_train:1216576'
        entry=self.contract['trusted_metadata'][key]
        row=dict(id=key,original_text_sha256=entry['original_text_sha256'],
                 selected=dict(decision='EXCLUDE',body=None,clean_text_sha256=None),root_approved=True)
        document['rows'].append(row);prior['rows'].append(copy.deepcopy(row))
        cache.validate_selection(document,prior,self.contract)

    def test_new_exclusion_of_a_restricted_body_is_rejected(self):
        document,prior=self.selection();document['rows'].append(self.restricted_row('EXCLUDE'))
        with self.assertRaises(Exception):cache.validate_selection(document,prior,self.contract)

    def test_new_filter_cannot_borrow_a_prior_exclude_entry(self):
        document,prior=self.selection();row=dict(self.restricted_row('EXCLUDE'),root_approved=True)
        document['rows'].append(row);prior['rows'].append(copy.deepcopy(row))
        with self.assertRaises(Exception):cache.validate_selection(document,prior,self.contract)

    def test_alias_with_restricted_packet_sha_is_rejected(self):
        document,prior=self.selection();row=self.restricted_row();row['id']='expanded_train:987654320'
        row['original_text_sha256']='3'*64
        row['selected']['clean_text_sha256']=self.contract['actual_filter_metadata_hold']['reading_parts'][0]['sha256']
        document['rows'].append(row)
        with self.assertRaises(Exception):cache.validate_selection(document,prior,self.contract)

    def test_cumulative_six_parent_aliases_match_metadata(self):
        opaque=dict(trusted_hold_metadata=copy.deepcopy(self.contract['trusted_metadata']))
        self.assertEqual(len(cache.validate_new_aliases(opaque,self.contract)),6)

    def test_missing_actual_filter_parent_alias_is_rejected(self):
        opaque=dict(trusted_hold_metadata=copy.deepcopy(self.contract['trusted_metadata']))
        del opaque['trusted_hold_metadata'][cache.guard.NEW_ALIAS]
        with self.assertRaises(Exception):cache.validate_new_aliases(opaque,self.contract)

    def test_changed_actual_filter_interval_is_rejected(self):
        opaque=dict(trusted_hold_metadata=copy.deepcopy(self.contract['trusted_metadata']))
        opaque['trusted_hold_metadata'][cache.guard.NEW_ALIAS]['input_ids']+=1
        with self.assertRaises(Exception):cache.validate_new_aliases(opaque,self.contract)

    def test_active_context_installs_and_restores_guard6(self):
        previous=cache.previous.CONTRACT
        with cache.active_contract() as contract:
            self.assertEqual(cache.previous.CONTRACT,cache.CONTRACT)
            self.assertEqual(cache.opaque_runtime.EXPECTED,cache.EXPECTED)
            self.assertEqual(len(contract['restricted_hashes']),25)
        self.assertEqual(cache.previous.CONTRACT,previous)
        self.assertIsNone(cache.ACTIVE_CONTRACT)

    def test_nested_context_uses_same_checked_metadata(self):
        with cache.active_contract() as outer:
            with cache.active_contract() as inner:
                self.assertIs(outer,inner)
                self.assertEqual(len(cache.checked_contract()['trusted_metadata']),21)

    def test_actual_prior_initializer_never_hashes_or_loads_source_views(self):
        selection=AUDIT/'ROOT_AUTHORED_SELECTIONS_V32.json'
        pin='67A77EA21E4F98FE5FF5F27D906B0C8E08C0B702C2B852750A9C0825281DA5A8'
        with cache.active_contract(),cache.bound_selection_loads([(selection,pin)],directory=AUDIT):
            inputs=SimpleNamespace()
            cache.initialize_prior_body_inputs(inputs,selection)
            self.assertEqual(inputs.safe_texts,{})
            self.assertEqual(len(inputs.safe_clean_texts),3)
            self.assertTrue(all(case['view']['path'] not in inputs.pins for case in inputs.safe.values()))
            cache.inner_runtime.GuardedInputs.check(inputs)
            key,case=next(iter(inputs.safe.items()))
            row=dict(id=case['id'],text='',original_text_sha256=key,restricted_parent_body_not_decoded=True)
            engine=SimpleNamespace(current=(row,3),guard=inputs)
            self.assertTrue(cache.prior_body_code_guard(engine,'',inputs.safe_clean_texts[key]))
            with self.assertRaises(Exception):cache.prior_body_code_guard(engine,'',inputs.safe_clean_texts[key]+'x')
            cache.guard.assert_no_protected_opens()

    def test_ordinary_source_still_uses_original_guard(self):
        engine=SimpleNamespace(current=(dict(id='fixture',text='ordinary'),3))
        original=Mock(return_value=True)
        with patch.object(cache,'BASE_SAFE_CODE_GUARD',original):
            self.assertTrue(cache.prior_body_code_guard(engine,'old','new',{}))
        original.assert_called_once_with(engine,'old','new',{})


if __name__=='__main__':
    unittest.main()
