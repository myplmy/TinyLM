"""공식 평가 원문은 바꾸지 않는 CPU 경계 시험."""
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from scripts import prepare_p106b_kobest_official_eval as module


class TestAssets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_docs(self, docs):
        path = self.root / 'test.jsonl'
        path.write_text(chr(10).join(json.dumps(row, ensure_ascii=False) for row in docs) + chr(10))
        return path

    def test_labels_and_order_digest(self):
        docs = [dict(paragraph='문맥', question='질문', label=i) for i in [0, 1]]
        path = self.write_docs(docs)
        result = module.scan_test(path, 'boolq', 2)
        self.assertEqual(result['label_counts'], {0: 1, 1: 1})
        first = result['ordered_json_sha256']
        self.assertNotEqual(first, module.scan_test(self.write_docs(docs[::-1]), 'boolq', 2)['ordered_json_sha256'])

    def test_original_duplicates_are_preserved(self):
        doc = dict(sentence='좋다', label=1)
        result = module.scan_test(self.write_docs([doc, doc]), 'sentineg', 2)
        self.assertEqual((result['rows'], result['duplicate_rows_preserved']), (2, 1))

    def test_wrong_denominator(self):
        with self.assertRaises(ValueError):
            module.scan_test(self.write_docs([dict(sentence='좋다', label=1)]), 'sentineg', 2)

    def test_bool_is_not_an_integer_label(self):
        with self.assertRaises(ValueError):
            module.scan_test(self.write_docs([dict(sentence='좋다', label=True)]), 'sentineg', 1)

    def test_label_out_of_range(self):
        with self.assertRaises(ValueError):
            module.scan_test(self.write_docs([dict(sentence='좋다', label=2)]), 'sentineg', 1)

    def test_missing_or_empty_field(self):
        for value in ['', '  ', None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.scan_test(self.write_docs([dict(sentence=value, label=0)]), 'sentineg', 1)

    def test_duplicate_json_key(self):
        path = self.root / 'bad.jsonl'
        path.write_text('{"sentence":"good","label":0,"label":1}' + chr(10))
        with self.assertRaisesRegex(ValueError, '중복 JSON'):
            module.scan_test(path, 'sentineg', 1)

    def test_copa_connector_contract(self):
        doc = dict(premise='문장', question='기타', alternative_1='하나', alternative_2='둘', label=0)
        with self.assertRaises(ValueError):
            module.scan_test(self.write_docs([doc]), 'copa', 1)

    def repo(self, target):
        repo = self.root / 'repo'
        (repo / 'refs').mkdir(parents=True)
        (repo / 'refs/main').write_text(module.REVISION)
        (repo / 'blobs').mkdir()
        snapshot = repo / 'snapshots' / module.REVISION / 'boolq'
        snapshot.mkdir(parents=True)
        (snapshot / 'test.jsonl').symlink_to(target)
        return repo

    def test_only_exact_hf_blob_is_allowed(self):
        repo = self.repo('../../../blobs/source')
        (repo / 'blobs/source').write_text('data')
        path, blob = module.local_test(repo, module.REVISION, 'boolq')
        self.assertEqual(path.name, 'test.jsonl')
        self.assertEqual(blob, repo / 'blobs/source')

    def test_external_link_is_rejected(self):
        target = self.root / 'external'
        target.write_text('data')
        repo = self.repo(target)
        with self.assertRaises(ValueError):
            module.local_test(repo, module.REVISION, 'boolq')

    def test_exact_snapshot_regular_file_is_allowed(self):
        repo = self.repo('../../../blobs/source')
        path = repo / 'snapshots' / module.REVISION / 'boolq/test.jsonl'
        path.unlink()
        path.write_text('data')
        selected, resolved = module.local_test(repo, module.REVISION, 'boolq')
        self.assertEqual(selected.absolute(), resolved)

    def test_snapshot_parent_symlink_is_rejected(self):
        repo = self.repo('../../../blobs/source')
        parent = repo / 'snapshots' / module.REVISION / 'boolq'
        (parent / 'test.jsonl').unlink()
        parent.rmdir()
        external = self.root / 'outside'
        external.mkdir()
        (external / 'test.jsonl').write_text('data')
        parent.symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            module.local_test(repo, module.REVISION, 'boolq')

    def test_revision_and_family_are_pinned(self):
        for revision, family in [('other', 'boolq'), (module.REVISION, 'other')]:
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                module.local_test(self.root, revision, family)

    def test_official_sources_match_archive_and_reject_tamper(self):
        source = self.root / 'source'
        archive = self.root / 'source.tar.gz'
        relatives = ['lm_eval/tasks/kobest/' + name for name in
                     ['_kobest.yaml', 'utils.py'] + ['kobest_' + x + '.yaml' for x in module.SPECS]]
        with tarfile.open(archive, 'w:gz') as package:
            for relative in relatives:
                body = relative.encode()
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
                info = tarfile.TarInfo('official/' + relative)
                info.size = len(body)
                package.addfile(info, io.BytesIO(body))
        self.assertEqual(len(module.task_sources(source, archive)), 7)
        (source / relatives[0]).write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            module.task_sources(source, archive)

    def test_dependency_probe_does_not_install_or_import_hf(self):
        fake = subprocess.CompletedProcess([], 0, stdout=json.dumps(dict(packages={'evaluate': None, 'numpy': dict(version='1')})))
        with patch.object(module.subprocess, 'run', return_value=fake) as run:
            report = module.dependencies(Path('/approved/python'))
        self.assertEqual(report['missing'], ['evaluate'])
        self.assertFalse(report['installation_performed'])
        self.assertEqual(run.call_args.args[0][:3], ['/approved/python', '-I', '-B'])
        self.assertNotIn('import datasets', run.call_args.args[0][-1])


if __name__ == '__main__':
    unittest.main()
