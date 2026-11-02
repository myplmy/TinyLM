"""Invalid names stay rejected except the exact pinned historical source pair."""
from pathlib import Path
import hashlib
import importlib.util
import re
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rank_alias', HERE/'exact_review_rank_alias_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def normal_rank(path):
    match = re.fullmatch(r'review_([0-9]+)_v([0-9]+)\.md', path.name)
    if not match:
        raise ValueError('unrecognized review name')
    return int(match[1]), False, int(match[2])


class AliasTests(unittest.TestCase):
    def fixture(self, root):
        old = root/'review_049_v10_v2.md'
        new = root/'review_049_v11.md'
        old.write_text('source:one source:two')
        new.write_text('source:one source:two')
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()
        record = dict(path=old.name, canonical_review=new.name, sha256=sha(old),
            canonical_review_sha256=sha(new), ids=['source:one','source:two'],
            legacy_rank=[49,False,10], root_approved=True)
        return old, new, record

    def test_exact_legacy_history_orders_before_real_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old,new,r=self.fixture(root)
            rank=module.install_rank_aliases(root,[r],normal_rank,lambda b:set(b.decode().split()))
            self.assertLess(rank(old),rank(new))

    def test_unregistered_nested_name_remains_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old,new,r=self.fixture(root)
            rank=module.install_rank_aliases(root,[r],normal_rank,lambda b:set(b.decode().split()))
            with self.assertRaises(ValueError):rank(root/'review_049_v10_v3.md')

    def test_changed_historical_bytes_are_rejected_at_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old,new,r=self.fixture(root)
            rank=module.install_rank_aliases(root,[r],normal_rank,lambda b:set(b.decode().split()))
            old.write_text('changed')
            with self.assertRaises(AssertionError):rank(old)

    def test_different_source_ids_cannot_be_superseded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old,new,r=self.fixture(root)
            r['ids']=['source:one']
            with self.assertRaises(AssertionError):
                module.install_rank_aliases(root,[r],normal_rank,lambda b:set(b.decode().split()))

    def test_canonical_revision_must_be_newer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old,new,r=self.fixture(root)
            r['legacy_rank']=[49,False,12]
            with self.assertRaises(AssertionError):
                module.install_rank_aliases(root,[r],normal_rank,lambda b:set(b.decode().split()))


if __name__ == '__main__':
    unittest.main()
