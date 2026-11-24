"""Admission failure evidence and native ByteLevel interpretation contracts."""
from pathlib import Path
import tempfile
import unittest

from scripts.diag_p106b_dvlm_pts import AdmissionWriter, native_pieces
from scripts.p106b_dvlm_pts import AdmissionHold


class AdmissionEvidenceTests(unittest.TestCase):
    def test_partial_failure_flushes_rows_without_complete_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = AdmissionWriter(root, 'admission', limit=128)
            writer.append({'row_id': 'first', 'status': 'WHOLE_SAMPLE_HOLD'})
            partial = writer.preserve_partial()
            self.assertEqual(partial['rows'], 1)
            self.assertFalse(partial['complete_manifest'])
            self.assertTrue((root / partial['shards'][0]['path']).read_bytes().endswith(b'\n'))
            self.assertFalse(writer.manifest_path.exists())

    def test_completed_manifest_remains_complete_during_secondary_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = AdmissionWriter(Path(directory), 'admission', limit=128)
            writer.append({'row_id': 'first'})
            manifest = writer.close(lineage={'partial': False})
            partial = writer.preserve_partial()
            self.assertEqual(partial['rows'], manifest['rows'])
            self.assertTrue(partial['complete_manifest'])

    def test_added_literal_token_keeps_its_literal_utf8(self):
        pieces = native_pieces([7, 8], {8: 'hello'}, {7: '<|assistant|>'})
        self.assertEqual(pieces, (b'<|assistant|>', b'hello'))

    def test_undeclared_native_id_is_a_whole_sample_hold(self):
        with self.assertRaisesRegex(AdmissionHold, 'undeclared native token'):
            native_pieces([9], {8: 'hello'}, {})


if __name__ == '__main__':
    unittest.main()
