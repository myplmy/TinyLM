"""Small synthetic metadata rows; no corpus payloads are opened."""
from pathlib import Path
from unittest.mock import patch
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opaque_parent_projection_v1 as projection


class OpaqueParentProjectionTests(unittest.TestCase):
    def row(self, top, nested):
        return (json.dumps(dict(id='expanded_train:1', original_text_sha256=top,
            decision='HOLD', provenance={'original_text_sha256': nested},
            text='opaque body must never be decoded ' + json.dumps(
                {'original_text_sha256': 'C' * 64}))) + chr(10)).encode()

    def test_nested_provenance_does_not_hide_real_top_level_hold(self):
        line = self.row('A' * 64, 'B' * 64)
        with patch.object(projection.metadata, 'FIELDS', projection.metadata.FIELDS | {'decision'}):
            result = projection.matching_parent_metadata(line, {'A' * 64})
        self.assertEqual(result['original_text_sha256'], 'A' * 64)
        self.assertNotIn('text', result)
        self.assertNotIn('provenance', result)

    def test_nested_match_does_not_select_unrelated_top_level(self):
        line = self.row('B' * 64, 'A' * 64)
        self.assertIsNone(projection.matching_parent_metadata(line, {'A' * 64}))

    def test_unrelated_raw_hashes_are_skipped(self):
        self.assertIsNone(projection.matching_parent_metadata(self.row('B' * 64, 'C' * 64), {'A' * 64}))

    def test_escaped_body_hash_is_not_a_metadata_match(self):
        self.assertIsNone(projection.matching_parent_metadata(self.row('B' * 64, 'B' * 64), {'C' * 64}))

    def test_body_and_provenance_values_are_not_json_decoded(self):
        line = self.row('A' * 64, 'B' * 64)
        original = json.loads
        def checked(raw, *args, **kwargs):
            self.assertNotIn(b'opaque body', raw)
            self.assertFalse(raw.startswith(b'{'))
            return original(raw, *args, **kwargs)
        with patch.object(projection.metadata, 'FIELDS', projection.metadata.FIELDS | {'decision'}), \
                patch.object(projection.metadata.json, 'loads', checked):
            result = projection.matching_parent_metadata(line, {'A' * 64})
        self.assertEqual(result['id'], 'expanded_train:1')

    def test_non_hold_parent_is_rejected(self):
        line = self.row('A' * 64, 'B' * 64).replace(b'"HOLD"', b'"KEEP"')
        with patch.object(projection.metadata, 'FIELDS', projection.metadata.FIELDS | {'decision'}):
            with self.assertRaisesRegex(ValueError, 'non-HOLD'):
                projection.matching_parent_metadata(line, {'A' * 64})


if __name__ == '__main__':
    unittest.main(verbosity=2)
