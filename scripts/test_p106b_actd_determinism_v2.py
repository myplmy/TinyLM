import hashlib
import json
from pathlib import Path
import unittest
from scripts import diag_p106b_actd_determinism_v2 as d


class MirrorContracts(unittest.TestCase):
    def test_exact_complete_teacher_provenance_required_not_just_a_matching_path(self):
        raw=json.dumps(dict(status='ACTD_NATIVE_TOP128_COMPLETE',returncode=0,rows_completed=128)).encode()
        sha=hashlib.sha256(raw).hexdigest().upper();self.assertEqual(d.teacher_reference(raw,sha),sha)
        with self.assertRaises(ValueError):d.teacher_reference(raw+b' ',sha)
        broken=json.dumps(dict(status='ERROR',returncode=9,rows_completed=127)).encode()
        with self.assertRaises(ValueError):d.teacher_reference(broken,hashlib.sha256(broken).hexdigest().upper())
    def test_v2_reader_tag_and_destination_are_local_while_original_loss_and_cache_are_unchanged(self):
        before=d.first.old.run.__globals__['d'];runner=d.build_runner(Path('/tmp/actd_v2_unused_contract'))
        self.assertIs(runner.__code__,d.first.old.run.__code__)
        self.assertIs(runner.__globals__['read_cache'],d.first.old.read_cache)
        self.assertIs(d.first.old.run.__globals__['d'],before)
        self.assertEqual(runner.__globals__['d'].TAG,d.TAG)
        self.assertEqual(runner.__globals__['d'].BASE,Path('/tmp/actd_v2_unused_contract'))


if __name__=='__main__':unittest.main()
