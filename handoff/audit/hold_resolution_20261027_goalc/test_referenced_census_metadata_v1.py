"""Reference routing rejects changed identity and never routes unrelated checks."""
from pathlib import Path
from types import SimpleNamespace
import copy
import hashlib
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from referenced_census_metadata_v1 import SCHEMA, bind_reference, resolve_reference


class ReferenceCensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hold_reference_fixture_')
        self.root = Path(self.tmp.name)
        self.parent = self.root/'frozen_parent'
        (self.parent/'hold').mkdir(parents=True)
        self.manifest = {'shards': [{'path':'fixture_000000.jsonl','sha256':'A'*64}]}
        (self.parent/'built.json').write_text(json.dumps({'manifests':{'hold':self.manifest}}))
        self.sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()
        self.read = lambda p: json.loads(p.read_bytes())
        digest = self.sha(self.parent/'built.json')
        self.document = dict(metadata_reference_schema=SCHEMA,
            metadata_reference=dict(path='frozen_parent/hold',parent_built_sha256=digest),
            manifest=self.manifest, pin=dict(parent_built_sha256=digest),
            counts=dict(documents=460695,input_ids=462874291),unprocessed=0,body_fields_decoded=0,
            source_metadata_enumeration=dict(every_position_identity_and_input_ids_recounted=True))
        self.census = self.root/'new_census/complete.json'
        self.census.parent.mkdir()
        self.calls = []
        self.cache = SimpleNamespace(read=self.read,verify=lambda p,m:self.calls.append((Path(p),m)))

    def tearDown(self):
        self.tmp.cleanup()

    def resolve(self, document=None):
        return resolve_reference(self.root,self.parent,document or self.document,self.read,self.sha)

    def test_exact_reference_and_no_payload_copy(self):
        with bind_reference(self.cache,self.root,self.parent,self.census,self.document,self.sha):
            self.cache.verify(self.census.parent/'ledger', self.manifest)
        self.assertEqual([p for p,m in self.calls], [self.parent/'hold',self.parent/'hold'])
        self.assertFalse((self.census.parent/'ledger').exists())

    def test_wrong_reference_path_rejected(self):
        doc = copy.deepcopy(self.document);doc['metadata_reference']['path']='elsewhere/hold'
        with self.assertRaises(AssertionError): self.resolve(doc)

    def test_changed_manifest_rejected(self):
        doc = copy.deepcopy(self.document);doc['manifest']['shards'][0]['sha256']='B'*64
        with self.assertRaises(AssertionError): self.resolve(doc)

    def test_changed_parent_receipt_rejected(self):
        (self.parent/'built.json').write_text('{}')
        with self.assertRaises(AssertionError): self.resolve()

    def test_copied_ledger_rejected(self):
        (self.census.parent/'ledger').mkdir()
        with self.assertRaises(AssertionError):
            with bind_reference(self.cache,self.root,self.parent,self.census,self.document,self.sha): pass

    def test_unrelated_verification_stays_at_original_path(self):
        unrelated=self.root/'cache/text'
        with bind_reference(self.cache,self.root,self.parent,self.census,self.document,self.sha):
            self.cache.verify(unrelated, self.manifest)
        self.assertEqual(self.calls[-1][0],unrelated)

    def test_altered_requested_manifest_rejected(self):
        with bind_reference(self.cache,self.root,self.parent,self.census,self.document,self.sha):
            with self.assertRaises(AssertionError):self.cache.verify(self.census.parent/'ledger',{})


if __name__ == '__main__':
    unittest.main(verbosity=2)
