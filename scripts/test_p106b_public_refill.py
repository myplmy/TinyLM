"""CPU fixtures for exact acquisition, immutable old paths and source caps."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import p106b_public_refill as r


class RefillTests(unittest.TestCase):
    def test_exact_train_only_metadata(self):
        specs=r.english_specs()
        self.assertEqual(len(specs),7)
        self.assertEqual(sum(s['bytes'] for s in specs),6321198481)
        self.assertTrue(all(s['remote_file'].startswith('english/train-') for s in specs))
        self.assertTrue(all(len(s['sha256'])==64 and len(s['revision'])==40 for s in specs))
        self.assertEqual(len({s['path'] for s in specs}),7)
    def test_namespace_different(self):
        from scripts import p106b_balanced_public as old
        self.assertNotEqual(old.OUTPUT,r.OUTPUT)
        self.assertNotIn('TinyDataset',str(r.SOURCE))
    def test_missing_source_is_expected_prerequisite(self):
        from scripts.p106b_mixed_scale import TOK_SHA
        with tempfile.TemporaryDirectory(prefix='p106b_refill_test_') as tmp:
            root=Path(tmp)
            with patch.object(r,'ROOT',root),patch.object(r,'OUTPUT',root/'new'), \
                 patch.object(r,'SOURCE',root/'source'), \
                 patch.object(r,'source_specs',return_value=[]), \
                 patch.object(r,'safe_repo_path',side_effect=lambda p:p), \
                 patch.object(r,'digest',return_value=TOK_SHA):
                with self.assertRaises(FileNotFoundError):r.build_check()
    def test_one_download_is_hash_verified_and_idempotent(self):
        payload=b'fixture source'
        with tempfile.TemporaryDirectory(prefix='p106b_refill_test_') as tmp:
            root=Path(tmp)
            spec={'path':'source/train.parquet','repo':'fixture','revision':'0'*40,
                  'remote_file':'english/train.parquet','bytes':len(payload),
                  'sha256':hashlib.sha256(payload).hexdigest().upper()}
            def opener(_url,timeout):return io.BytesIO(payload)
            with patch.object(r,'ROOT',root),patch.object(r,'safe_repo_path',side_effect=lambda p:p):
                self.assertEqual(r.fetch_one(spec,opener),'DOWNLOADED_VERIFIED')
                self.assertEqual(r.fetch_one(spec,opener),'VERIFIED_EXISTING')
            self.assertEqual((root/spec['path']).read_bytes(),payload)
    def test_wrong_hash_preserves_partial(self):
        with tempfile.TemporaryDirectory(prefix='p106b_refill_test_') as tmp:
            root=Path(tmp)
            spec={'path':'source/train.parquet','repo':'fixture','revision':'0'*40,
                  'remote_file':'english/train.parquet','bytes':3,'sha256':'0'*64}
            with patch.object(r,'ROOT',root),patch.object(r,'safe_repo_path',side_effect=lambda p:p):
                with self.assertRaises(ValueError):r.fetch_one(spec,lambda _url,timeout:io.BytesIO(b'abc'))
            self.assertFalse((root/spec['path']).exists())
            self.assertTrue((root/(spec['path']+'.partial')).exists())
    def test_build_reuses_engine_without_leaking_mutation(self):
        from scripts import p106b_balanced_public as b
        before=(b.OUTPUT,b.rows_for)
        with patch.object(b,'execute',return_value=8) as execute:
            self.assertEqual(r.build([]),8)
            execute.assert_called_once_with([])
        self.assertEqual((b.OUTPUT,b.rows_for),before)
    def test_real_english_schema_and_family(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        table=pa.Table.from_pylist([{'id':'id1','inputs':'question','targets':'answer','dataset_name':'SODA-inst'},
                                  {'id':'id2','inputs':'x','targets':'y','dataset_name':'PIQA (T)'}])
        with tempfile.TemporaryDirectory(prefix='p106b_refill_test_') as tmp:
            root=Path(tmp);p=root/'fixture.parquet';pq.write_table(table,p)
            spec=dict(family='aya_collection_en',path='fixture.parquet',repo='fixture',revision='0'*40,
                      sha256='0'*64,license='card')
            with patch.object(r,'ROOT',root):rows=list(r.english_rows(spec))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['meta']['language'],'en')
        self.assertEqual(rows[0]['meta']['source_family'],'SODA-inst')
        self.assertEqual(rows[0]['meta']['source_collection_row_id'],'id1')
    def test_new_student_paths_and_wire_prerequisite(self):
        from scripts import diag_p106b_mixed_repeat4 as e
        with tempfile.TemporaryDirectory(prefix='p106b_refill_test_') as tmp:
            root=Path(tmp);public=root/'public';public.mkdir()
            report=dict(schema='P106B_MIXED_PUBLIC_C_V1',tokenizer_sha256=e.TOK_SHA,
                token_target_ready=True,nonpadding_tokens={'train:ko':e.GOAL,'train:en':e.GOAL},
                rows={'train:ko':128,'train:en':128,'val:ko':16,'val:en':16},
                train_concat_sha256='T',val_concat_sha256='V')
            (public/'report.json').write_text(json.dumps(report))
            for split,sha in [('train','T'),('val','V')]:
                (public/(split+'_shards_manifest.json')).write_text(json.dumps({'concat_sha256':sha}))
            with patch.object(e,'ROOT',root),patch.object(r,'OUTPUT',public), \
                 patch.object(e,'safe_repo_path',side_effect=lambda p:p), \
                 patch.object(e,'digest',side_effect=lambda p:'D' if p.is_file() else (_ for _ in ()).throw(FileNotFoundError(str(p)))), \
                 patch.object(e,'verify'):
                _report,_specs,info=e.check(wire=True,refill=True)
                self.assertIn('v3_en_refill',info['output'])
                self.assertEqual((info['micro'],info['accum'],info['epochs']),(8,16,1))
                with self.assertRaises(FileNotFoundError):e.check(refill=True)
                w=root/'HF/sft_ready/p106b_mixed_student_wire_v3_en_refill';w.mkdir(parents=True)
                wire=dict(status='WIRE_COMPLETE',optimizer_updates=2,processed_train_row_exposures=256,
                    input={'measurement_contract':'MIXED_COUNTS_VALIDATION_V2',
                           'train_concat_sha256':'T','val_concat_sha256':'V'})
                (w/'report.json').write_text(json.dumps(wire))
                _report,_specs,info=e.check(refill=True)
                self.assertIn('refill300m',info['final'])
                self.assertEqual(info['epochs'],4)
                self.assertTrue(info['grad_checkpoint'])
                wire['input']['train_concat_sha256']='wrong';(w/'report.json').write_text(json.dumps(wire))
                with self.assertRaises(ValueError):e.check(refill=True)


if __name__=='__main__':unittest.main()
