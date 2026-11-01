"""공식 원형 대조의 CPU 합성 경계 시험."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from scripts.p106b_official_archive import verify_files


class ArchiveContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.runtime = self.root / 'runtime'
        self.archive = self.root / 'package.tar.gz'
        self.name = 'lm_eval/api/metrics.py'
        for root in [self.source, self.runtime]:
            (root / self.name).parent.mkdir(parents=True)
            (root / self.name).write_bytes(b'official')
        with tarfile.open(self.archive, 'w:gz') as package:
            entry = tarfile.TarInfo('source/' + self.name)
            entry.size = 8
            package.addfile(entry, io.BytesIO(b'official'))

    def check(self, names=None):
        return verify_files(names or [self.name], archive=self.archive, source=self.source, runtime=self.runtime)

    def test_source_and_actual_runtime_match_without_writes(self):
        result = self.check()
        self.assertTrue(result['source_matches'] and result['runtime_matches'])
        self.assertEqual((self.source / self.name).read_bytes(), b'official')

    def test_source_mismatch(self):
        (self.source / self.name).write_bytes(b'mutated')
        with self.assertRaises(ValueError): self.check()

    def test_runtime_mismatch(self):
        (self.runtime / self.name).write_bytes(b'mutated')
        with self.assertRaises(ValueError): self.check()

    def test_relative_path_escape(self):
        for name in ['/lm_eval/file.py', '../file.py', 'lm_eval/../file.py', 'other/file.py']:
            with self.subTest(name=name), self.assertRaises(ValueError): self.check([name])

    def test_missing_file(self):
        with self.assertRaises(ValueError): self.check(['lm_eval/missing.py'])

    def test_duplicate_requested_file(self):
        with self.assertRaises(ValueError): self.check([self.name, self.name])

    def test_source_link_refused(self):
        target = self.root / 'other.py'
        target.write_bytes(b'official')
        (self.source / self.name).unlink()
        (self.source / self.name).symlink_to(target)
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__':
    unittest.main()
