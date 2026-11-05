"""Check scope/link/race refusal using preserved synthetic fixtures only."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import delete_approved_payloads_20261105_v1 as cleanup


class CleanupScopeTests(unittest.TestCase):
    def fixture(self):
        base=Path(tempfile.mkdtemp(prefix='approved_payload_scope_fixture_'))
        target=base/cleanup.TARGETS[0];target.mkdir(parents=True)
        (target/'synthetic.bin').write_bytes(b'fixture')
        (base/'protected.json').write_bytes(b'{}')
        return base,target

    def test_exact46_roots_exclude_official_cache_and_sources(self):
        self.assertEqual(len(cleanup.TARGETS),46)
        self.assertEqual(len(set(cleanup.TARGETS)),46)
        for name in ['cache_reviewed_partial_v11/tokens','agents/file.txt',
                     'roster_reviewed_partial_v20/records','guarded_partial_proposals_v18/ledger']:
            with self.assertRaises(ValueError):cleanup.allowed(name)

    def test_absolute_and_parent_paths_are_denied(self):
        for name in ['/tmp/file','cache_partial_v1/tokens/../original','cache_partial_v1//tokens']:
            with self.assertRaises(ValueError):cleanup.allowed(name)

    def test_unapproved_collect_root_is_denied(self):
        base,target=self.fixture()
        with self.assertRaises(ValueError):cleanup.collect(base,['agents'])
        self.assertTrue((base/'protected.json').exists())

    def test_symbolic_link_inside_target_is_denied(self):
        base,target=self.fixture();(target/'symlink.bin').symlink_to(base/'protected.json')
        with self.assertRaises(ValueError):cleanup.collect(base,[cleanup.TARGETS[0]])

    def test_outside_hardlink_is_denied(self):
        base,target=self.fixture();os.link(target/'synthetic.bin',base/'outside-link.bin')
        with self.assertRaises(ValueError):cleanup.collect(base,[cleanup.TARGETS[0]])

    def test_changed_file_is_not_unlinked(self):
        base,target=self.fixture();files,dirs=cleanup.collect(base,[cleanup.TARGETS[0]])
        (target/'synthetic.bin').write_bytes(b'changed fixture bytes')
        fd=os.open(base,cleanup.FLAGS)
        try:
            with patch.object(cleanup.os,'unlink') as unlink:
                with self.assertRaises(ValueError):cleanup.unlink_one(fd,files[0],{row['path']:row for row in dirs})
                unlink.assert_not_called()
        finally:os.close(fd)

    def test_symlink_parent_swap_is_not_followed(self):
        base,target=self.fixture();files,dirs=cleanup.collect(base,[cleanup.TARGETS[0]])
        target.rename(target.with_name('preserved-fixture'))
        target.symlink_to(target.with_name('preserved-fixture'),target_is_directory=True)
        fd=os.open(base,cleanup.FLAGS)
        try:
            with patch.object(cleanup.os,'unlink') as unlink:
                with self.assertRaises(OSError):cleanup.unlink_one(fd,files[0],{row['path']:row for row in dirs})
                unlink.assert_not_called()
        finally:os.close(fd)

    def test_retained_fingerprint_ignores_only_approved_payload(self):
        base,target=self.fixture();before=cleanup.retained_snapshot(base)
        (target/'synthetic.bin').write_bytes(b'different synthetic payload')
        self.assertEqual(before,cleanup.retained_snapshot(base))
        (base/'protected.json').write_bytes(b'{"changed":true}')
        self.assertNotEqual(before,cleanup.retained_snapshot(base))


if __name__=='__main__':unittest.main(verbosity=2)
