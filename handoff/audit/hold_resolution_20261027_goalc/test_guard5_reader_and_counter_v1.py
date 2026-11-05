"""Run all 21 transport regressions plus exact new guard and metadata negatives."""
from pathlib import Path
from types import SimpleNamespace
import copy
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_lossless_review_packet_v3 as regression
import scoped_lossless_review_entry_v4 as entry
import lossless_review_packet_v3 as core
import active_guard_v5_preflight_v1 as guard


class CurrentTransport(regression.LosslessV3Tests):
    def setUp(self):
        super().setUp()
        current=patch.object(regression.legacy,'entry',entry);current.start();self.addCleanup(current.stop)

    def test_guard4_required_before_core_or_payload_load(self):
        scope={'contract':{'path':entry.CONTRACT[0].replace('_V5.','_V4.'),'sha256':entry.CONTRACT[1]}}
        metadata=SimpleNamespace(pinned=lambda *args:json.dumps(scope).encode())
        with patch.object(entry,'load_module',return_value=metadata) as load,patch.object(sys,'argv',
            ['entry','--cohort','x','--source-id','expanded_train:7','--view','pair']):
            with self.assertRaises(ValueError):entry.cli(Path('/tmp'),'role',{})
            self.assertEqual(load.call_count,1)


class Guard5Cases(unittest.TestCase):
    def test_two_new_ids_denied_before_role_or_payload(self):
        for key in guard.NEW_IDS:
            with self.subTest(key=key):
                scope={'schema':core.previous.base.SCHEMA,'contract':{'path':'guard'},'roles':{}}
                calls=[]
                def metadata(root,pin):
                    calls.append(pin);return json.dumps({'restricted_ids':list(guard.NEW_IDS),'restricted_hashes':[]}).encode()
                with self.assertRaises(ValueError):
                    core.load_pair(Path('/tmp'),scope,'unknown','unknown',key,metadata,
                        lambda *args:self.fail('quarantine payload opened'))
                self.assertEqual(len(calls),1)

    def test_new_original_or_candidate_hash_denied_before_payload(self):
        for label in ['original','candidate']:
            with self.subTest(label=label):
                scope={'schema':core.previous.base.SCHEMA,'contract':{'path':'guard'},
                    'roles':{'role':{'cohort':{'path':core.previous.base.DATA_ROOT+'/cohort/manifest.json'}}}}
                row={'id':'expanded_train:77','role':'role',
                    'original':{'path':core.previous.base.DATA_ROOT+'/source.txt','sha256':'A'*64},
                    'candidate':{'path':core.previous.base.DATA_ROOT+'/candidate.txt','sha256':'B'*64}}
                def metadata(root,pin):
                    return json.dumps({'restricted_ids':[],'restricted_hashes':[row[label]['sha256']]}
                        if pin['path']=='guard' else {'rows':[row]}).encode()
                with self.assertRaises(ValueError):
                    core.load_pair(Path('/tmp'),scope,'role','cohort','expanded_train:77',metadata,
                        lambda *args:self.fail('hash-denied payload opened'))

    def test_counter_body_acceptance_and_wrong_pins_rejected(self):
        source={'id':'expanded_train:32895','role':'context_controls','occurrences':2,
            'original':{'path':'x','sha256':'A'*64},'candidate':{'path':'y','sha256':'B'*64}}
        item=dict(source,derived_candidate=source['candidate'])
        row={'id':source['id'],'decision':'NEEDS_ROOT','body_references':[],'declared_output_cell':'—'}
        with patch.object(guard,'checked_contract',return_value={'newly_quarantined_entries':[item]}):
            self.assertEqual(guard.validate_new_hold(row,source),item)
            for delta in [{'decision':'ACCEPT_CANDIDATE'},{'decision':'EXCLUDE'},
                {'body':'new.txt'},{'clean_text_sha256':'C'*64},{'body_references':['new.txt']},
                {'declared_output_cell':'new.txt'}]:
                with self.subTest(delta=delta),self.assertRaises(AssertionError):
                    guard.validate_new_hold(dict(row,**delta),source)
            changed=copy.deepcopy(source);changed['candidate']['sha256']='C'*64
            with self.assertRaises(AssertionError):guard.validate_new_hold(row,changed)

    def test_actual_guard5_preserves_old_metadata_and_four_parent_aliases(self):
        data=guard.checked_contract()
        self.assertEqual(len(data['trusted_metadata']),19)
        self.assertEqual({key for r in data['newly_quarantined_entries'] for key in r['parent_alias_ids']},
            {'expanded_train:32895','historical_train:32895','expanded_train:74587','historical_train:74587'})


if __name__=='__main__':unittest.main(verbosity=2)
