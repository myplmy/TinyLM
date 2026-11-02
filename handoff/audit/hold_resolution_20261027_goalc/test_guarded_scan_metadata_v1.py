"""Synthetic metadata tests; never open a real protected source body."""
from pathlib import Path
import importlib.util
import json
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('guarded_scan',Path(__file__).with_name('guarded_scan_metadata_v1.py'))
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
KEY='A'*64


def example(ident='expanded_train:7',key=KEY):
    return dict(id=ident,ordinal=int(ident.rsplit(':',1)[1]),source=ident.split(':',1)[0],split='train',
        source_ids=[10,22],source_ids_sha256='B'*64,original_text_sha256=key,input_ids=12,
        complete_eos=True,valid_utf8=True,original_signals={'example_count':2},
        language_proxy={'codepoints':8},text='OPAQUE BODY',candidate='OPAQUE CANDIDATE')


class GuardedMetadata(unittest.TestCase):
    def run_row(self,data,expected=None):
        expected=expected or example()
        return guard.guarded_row(data,restricted_ids={'expanded_train:7'},restricted_hashes={KEY},
            trusted_metadata={expected['id']:expected})

    def test_protected_body_is_not_sent_to_json_decoder(self):
        raw=json.dumps(example()).encode()
        real=json.loads
        def inspect(data,*args,**kwargs):
            self.assertNotIn(b'OPAQUE',data if isinstance(data,bytes) else data.encode())
            return real(data,*args,**kwargs)
        with patch.object(guard.json,'loads',inspect):
            result=self.run_row(raw)
        self.assertEqual(result['text'],'')
        self.assertNotIn('candidate',result)
        self.assertTrue(result['restricted_parent_body_not_decoded'])

    def test_ordinary_document_retains_exact_full_text(self):
        row=example('validation:10','C'*64)
        result=self.run_row(json.dumps(row).encode())
        self.assertEqual(result,row)

    def test_same_protected_hash_at_another_position_is_also_projected(self):
        alias=example('expanded_train:99')
        self.assertTrue(self.run_row(json.dumps(alias).encode(),alias)['restricted_parent_body_not_decoded'])

    def test_an_unknown_protected_alias_cannot_fall_back_to_body_decode(self):
        with self.assertRaises(ValueError):
            self.run_row(json.dumps(example('expanded_train:99')).encode())

    def test_changed_source_interval_is_rejected(self):
        row=example();row['source_ids']=[10,24]
        with self.assertRaises(ValueError):self.run_row(json.dumps(row).encode())

    def test_changed_protected_hash_is_rejected(self):
        row=example();row['original_text_sha256']='D'*64
        with self.assertRaises(ValueError):self.run_row(json.dumps(row).encode())

    def test_body_can_contain_escaped_metadata_lookalikes(self):
        row=example();row['text']='"id": "expanded_train:99", "original_text_sha256": "'+('C'*64)+'"'
        self.assertTrue(self.run_row(json.dumps(row).encode())['restricted_parent_body_not_decoded'])

    def test_duplicate_real_metadata_id_is_rejected(self):
        raw=json.dumps(example()).encode()
        raw=raw[:-1]+b', "id":"expanded_train:99"}'
        with self.assertRaises(ValueError):self.run_row(raw)

    def test_missing_signal_metadata_is_rejected(self):
        row=example();row.pop('original_signals')
        with self.assertRaises(ValueError):self.run_row(json.dumps(row).encode())

    def test_signal_metadata_cannot_smuggle_text(self):
        row=example();row['language_proxy']={'body':'OPAQUE BODY'}
        with self.assertRaises(ValueError):self.run_row(json.dumps(row).encode())

    def test_restricted_body_utf8_is_not_decoded(self):
        raw=json.dumps(example()).encode().replace(b'OPAQUE BODY',b'\xff\xfe')
        self.assertTrue(self.run_row(raw)['restricted_parent_body_not_decoded'])

    def test_escaped_braces_and_quotes_are_opaque(self):
        row=example();row['text']='quoted " } ], \\ end';row['extra']=[{'other':'{}[]'}]
        self.assertEqual(self.run_row(json.dumps(row).encode())['id'],'expanded_train:7')

    def test_truncated_body_string_is_rejected_without_decoding_it(self):
        raw=json.dumps(example()).encode().split(b'OPAQUE BODY')[0]
        with self.assertRaises(ValueError):self.run_row(raw)

    def test_empty_object_does_not_count_as_a_source(self):
        with self.assertRaises(ValueError):self.run_row(b'{}')


if __name__=='__main__':unittest.main()
