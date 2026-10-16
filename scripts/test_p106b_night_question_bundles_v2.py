from pathlib import Path
import copy
import tempfile
import unittest
from unittest.mock import patch
from scripts import diag_p106b_night_question_bundles_v2 as d
from scripts.test_p106b_night_question_bundles import distinct,case


class ShardedCensusTests(unittest.TestCase):
    def test_roundtrip_multiple_small_shards_with_no_aliases_in_summary(self):
        rows=[]
        for n in range(8):rows.extend(distinct(suffix=str(n)))
        census=d.method.census(rows)
        with tempfile.TemporaryDirectory(prefix='p106b_bundle_') as folder,patch.object(d,'FROZEN',Path(folder)):
            storage=d.save_census('train',census,limit=1800)
            manifest=d.qa.required(Path(folder)/'train_shards_manifest.json')
            self.assertGreater(len(manifest['shards']),1)
            self.assertTrue(all(s['bytes']<=1800 for s in manifest['shards']))
            self.assertEqual(d.restore_census('train',storage),census)
            self.assertNotIn('bundles',d.qa.required(Path(folder)/'train_summary.json'))
            with self.assertRaises(FileExistsError):d.save_census('train',census,limit=1800)

    def test_empty_bundle_population_is_not_a_fake_shard(self):
        census=d.method.census([case('a','무엇?','빨강')])
        with tempfile.TemporaryDirectory(prefix='p106b_bundle_') as folder,patch.object(d,'FROZEN',Path(folder)):
            storage=d.save_census('test',census)
            self.assertIsNone(storage['manifest_sha256'])
            self.assertEqual(d.restore_census('test',storage),census)

    def test_modified_shard_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p106b_bundle_') as folder,patch.object(d,'FROZEN',Path(folder)):
            storage=d.save_census('test',d.method.census(distinct()))
            path=next(Path(folder).glob('test_*.jsonl'))
            # Controlled temporary fixture corruption, never a real source file.
            with path.open('ab') as stream:stream.write(b'{}\n')
            with self.assertRaises(ValueError):d.restore_census('test',storage)

    def test_wrong_reconstruction_digest_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='p106b_bundle_') as folder,patch.object(d,'FROZEN',Path(folder)):
            storage=d.save_census('test',d.method.census(distinct()))
            bad=copy.deepcopy(storage);bad['full_census_sha256']='B'*64
            with self.assertRaises(ValueError):d.restore_census('test',bad)

    def test_v1_failure_namespace_not_reused(self):
        self.assertNotEqual(d.FROZEN,d.old.FROZEN)
        self.assertNotEqual(d.EVIDENCE,d.old.EVIDENCE)
        self.assertNotEqual(d.TAG,d.old.TAG)


if __name__=='__main__':unittest.main()
