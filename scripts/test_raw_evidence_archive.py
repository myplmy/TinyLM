#!/usr/bin/env python3
"""Regression tests for verified and non-overwriting evidence retrieval."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

if __package__:
    from . import raw_evidence_archive as recovery
else:
    import raw_evidence_archive as recovery


class EvidenceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        home = Path(self.workspace.name)
        self.repo = home / "repo"
        self.backup = home / "backup"
        self.restore = home / "restored"
        self.member = "test_result/evidence/fixture/응답.jsonl"
        self.payload = b'{"response":"ok"}\n'
        self.bundle = self.backup / "20261124_fixture" / "one.tar.gz"
        self.bundle.parent.mkdir(parents=True)
        with tarfile.open(self.bundle, "w:gz") as packed:
            item = tarfile.TarInfo(self.member)
            item.size = len(self.payload)
            item.mode = 0o640
            packed.addfile(item, io.BytesIO(self.payload))
        archive = {
            "archive": (recovery.ARCHIVE_DIR / self.bundle.relative_to(self.backup)).as_posix(),
            "archive_bytes": self.bundle.stat().st_size,
            "archive_sha256": hashlib.sha256(self.bundle.read_bytes()).hexdigest(),
            "file_count": 1,
            "files": [{
                "path": self.member,
                "size": len(self.payload),
                "sha256": hashlib.sha256(self.payload).hexdigest(),
            }],
        }
        self.catalog = self.repo / "test_result/20261124_시험_압축보관_목록.json"
        self.catalog.parent.mkdir(parents=True)
        self.manifest = {
            "schema": recovery.SCHEMA, "archive_count": 1, "file_count": 1, "archives": [archive],
        }
        self.write_catalog()

    def write_catalog(self):
        self.catalog.write_text(json.dumps(self.manifest), encoding="utf-8")

    def entry(self):
        return recovery.lookup(recovery.load_index(self.repo), self.member, None)

    def test_restores_original_path_from_backup_with_no_primary_archive(self):
        entry = self.entry()
        self.assertEqual(recovery.lookup(recovery.load_index(self.repo), "응답.jsonl", None), entry)
        with tempfile.TemporaryFile() as stream:
            archive, mode, mtime = recovery._read_member(entry, [self.repo / recovery.ARCHIVE_DIR, self.backup], stream)
            self.assertEqual(archive, self.bundle)
            target, status = recovery._restore(entry, stream, self.restore, mode, mtime)
            self.assertEqual(status, "restored")
            self.assertEqual(target, self.restore / self.member)
            self.assertEqual(target.read_bytes(), self.payload)
            self.assertEqual(recovery._restore(entry, stream, self.restore, mode, mtime)[1], "already_present")

    def test_refuses_to_replace_a_different_original(self):
        target = self.restore / self.member
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing")
        with tempfile.TemporaryFile() as stream:
            entry = self.entry()
            _, mode, mtime = recovery._read_member(entry, [self.backup], stream)
            with self.assertRaises(FileExistsError):
                recovery._restore(entry, stream, self.restore, mode, mtime)
        self.assertEqual(target.read_bytes(), b"existing")

    def test_refuses_tampered_bundle_and_parent_symlink(self):
        entry = self.entry()
        data = self.bundle.read_bytes()
        self.bundle.write_bytes(bytes([data[0] ^ 1]) + data[1:])
        with tempfile.TemporaryFile() as stream:
            with self.assertRaisesRegex(ValueError, "묶음 해시"):
                recovery._read_member(entry, [self.backup], stream)
        self.restore.mkdir()
        (self.restore / "test_result").symlink_to(self.backup, target_is_directory=True)
        with tempfile.TemporaryFile() as stream:
            with self.assertRaisesRegex(ValueError, "심볼릭"):
                recovery._restore(entry, stream, self.restore, 0o640, 0)

    def test_catalog_rejects_noncanonical_or_protected_paths(self):
        for path in ("test_result/../outside.txt", "datasets/TinyDataset/guarded.tsv"):
            with self.subTest(path=path):
                self.manifest["archives"][0]["files"][0]["path"] = path
                self.write_catalog()
                with self.assertRaises(ValueError):
                    recovery.load_index(self.repo)

    def test_explicit_backup_root_is_used_instead_of_local_configuration(self):
        with patch.dict("os.environ", {"TINYLM_EVIDENCE_ARCHIVE_ROOT": str(self.backup)}):
            self.assertEqual(recovery._archive_roots(self.repo, self.restore), [self.restore])
            self.assertEqual(recovery._archive_roots(self.repo, None)[-1], self.backup)


if __name__ == "__main__":
    unittest.main(verbosity=2)
