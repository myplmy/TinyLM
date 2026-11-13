"""The resumed latest-batch path and iterator version lifetime, CPU only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diag_p106b_nov05_english_resume as resume


class ResumeVersionTests(unittest.TestCase):
    def test_v5_latest_batch_uses_its_declared_view_not_parent_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = root / 'batch_000000'
            batch.mkdir()
            (batch / 'report.json').write_text(json.dumps(dict(
                input=dict(visible_source_contract=resume.view.VIEW))), encoding='utf-8')
            before = resume.supported.VERSION
            with patch.object(resume.view, 'OUTPUT', root):
                iterator = resume.batches(None, root)
                item = next(iterator)
                self.assertEqual(item[1]['input']['visible_source_contract'], resume.view.VIEW)
                self.assertEqual(resume.supported.VERSION, before)
                with self.assertRaises(StopIteration):
                    next(iterator)
            self.assertEqual(resume.supported.VERSION, before)

    def test_a_mixed_v5_batch_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = root / 'batch_000000'
            batch.mkdir()
            (batch / 'report.json').write_text(json.dumps(dict(
                input=dict(visible_source_contract='wrong'))), encoding='utf-8')
            before = resume.supported.VERSION
            with patch.object(resume.view, 'OUTPUT', root):
                with self.assertRaisesRegex(ValueError, 'different generation contract'):
                    list(resume.batches(None, root))
            self.assertEqual(resume.supported.VERSION, before)

    def test_parent_destination_keeps_the_original_v3_reader(self):
        observed = []
        def original(control, destination):
            observed.append(resume.supported.VERSION)
            yield 'parent'
        with patch.object(resume, 'ORIGINAL_BATCHES', original):
            self.assertEqual(list(resume.batches(None, Path('/tmp/other-parent'))), ['parent'])
        self.assertEqual(observed, [resume.supported.VERSION])

    def test_runtime_restores_the_original_reader_after_failure(self):
        original = resume.supported.batches
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with resume.runtime():
                self.assertIs(resume.supported.batches, resume.batches)
                raise RuntimeError('fixture')
        self.assertIs(resume.supported.batches, original)


if __name__ == '__main__':
    unittest.main()
