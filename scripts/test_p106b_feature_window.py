"""Synthetic CPU NPY/source contracts; never open an existing user cache."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import weakref

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from scripts import p106b_feature_window as core


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class WindowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise ValueError('CPU window tests cannot initialize CUDA')
    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():raise ValueError('CPU window tests initialized CUDA')
    def setUp(self):
        # Retain all new scratch files instead of deleting any file.
        self.root=Path(tempfile.mkdtemp(prefix='tinylm-feature-window-v1-',dir='/tmp'))
        self.arrays=[np.arange(20,dtype=np.float32).reshape(5,4),
            (np.arange(28,dtype=np.float32)*-.125).reshape(7,4),np.ones((3,4),dtype=np.float32)]
        self.arrays[0][0,0]=np.float32(-0.)
        self.records=[]
        for i,(array,indices)in enumerate(zip(self.arrays,([0,4,2],[1,3,6,2],[]))):
            path=self.root/('r'+str(i)+'.npy')
            with path.open('xb')as stream:np.save(stream,array,allow_pickle=False)
            self.records.append(dict(row_id='r'+str(i),semantic_root_id='source'+str(i),split='train',
                feature_file=path.name,feature_sha256=digest(path),teacher_tokens=len(array),language=('ko'if i==0 else'en'),
                positions=[dict(teacher_predictor_raw_index=index,target=(index+i)%6,
                    student_target_raw_index=index+1,accepted=True,mapping_mode=1)for index in indices]))
        self.identities={name:letter*64 for name,letter in zip(
            ('teacher_sha256','tokenizer_sha256','mapping_sha256','data_sha256'),'ABCD')}
    def reader(self,records=None,**options):
        return core.FeatureWindow(self.records if records is None else records,root=self.root,
            identities=self.identities,split='train',hidden_width=4,batch_positions=options.pop('batch_positions',3),**options)
    def all_batches(self,reader):
        result=[]
        while True:
            try:batch=reader.prepare()
            except StopIteration:break
            result.append(batch);reader.finish()
        return result
    def expected(self):
        return np.stack([self.arrays[i][position['teacher_predictor_raw_index']]
            for i,row in enumerate(self.records)for position in row['positions']])
    def byte_equal(self,a,b):
        self.assertEqual(a.shape,b.shape);self.assertEqual(a.dtype,b.dtype)
        self.assertTrue(np.array_equal(a.view(np.uint8),b.view(np.uint8)))
    def replacement(self,name,array,**save_options):
        path=self.root/name
        with path.open('xb')as stream:np.save(stream,array,**save_options)
        record=copy.deepcopy(self.records[0]);record.update(feature_file=name,feature_sha256=digest(path))
        return [record]

    def test_every_original_FP32_byte_position_metadata_and_file_is_preserved(self):
        before={r['feature_file']:digest(self.root/r['feature_file'])for r in self.records}
        reader=self.reader();batches=self.all_batches(reader)
        self.byte_equal(np.concatenate([b.values for b in batches]),self.expected())
        self.assertEqual([len(b.values)for b in batches],[3,3,1])
        expected=[(r['row_id'],p)for r in self.records for p in r['positions']]
        actual=[(name,p)for b in batches for name,p in zip(b.row_ids,b.positions)]
        self.assertEqual(actual,expected)
        for batch in batches:
            self.assertTrue(batch.values.flags.owndata);self.assertIsNone(batch.values.base)
            self.assertFalse(batch.values.flags.writeable)
            for row_id,metadata in batch.rows.items():
                row=next(r for r in self.records if r['row_id']==row_id)
                self.assertEqual(metadata,{k:v for k,v in row.items()if k!='positions'})
        self.assertEqual(before,{r['feature_file']:digest(self.root/r['feature_file'])for r in self.records})
        self.assertEqual(reader.stats['files_opened'],2)

    def test_previous_full_array_is_released_before_next_file_payload_allocation(self):
        reader=self.reader(batch_positions=4)
        old_read=reader._read_feature;old_fromfile=core.np.fromfile;references=[]
        def observe(row):
            value=old_read(row);references.append(weakref.ref(value));return value
        def allocate(*args,**kwargs):
            self.assertFalse(any(ref()is not None for ref in references))
            return old_fromfile(*args,**kwargs)
        with patch.object(reader,'_read_feature',side_effect=observe),patch.object(core.np,'fromfile',side_effect=allocate):
            batches=self.all_batches(reader)
        self.assertEqual(reader.stats['maximum_feature_array_bytes'],112)
        self.assertEqual(reader.stats['maximum_prepared_batch_bytes'],64)
        self.assertEqual(len({id(ref())for ref in references if ref()is not None}),1)
        self.byte_equal(np.concatenate([b.values for b in batches]),self.expected())

    def test_JSON_source_resume_matches_next_batch_without_mutating_saved_cursor(self):
        first=self.reader();first.prepare();first.finish()
        saved=json.loads(json.dumps(first.state_dict()));untouched=copy.deepcopy(saved)
        expected=first.prepare()
        second=self.reader();second.load_state_dict(saved)
        self.assertEqual(second.stats['files_opened'],0)
        actual=second.prepare();self.byte_equal(expected.values,actual.values)
        self.assertEqual(expected.row_ids,actual.row_ids);self.assertEqual(expected.positions,actual.positions)
        self.assertEqual(expected.rows,actual.rows)
        first.finish();second.finish();self.assertEqual(first.state_dict(),second.state_dict())
        self.assertEqual(saved,untouched)
        self.assertIn('NOT_MODEL_OPTIMIZER_OR_RNG',saved['resume_scope'])

    def test_pending_and_invalid_finish_are_not_resumable_boundaries(self):
        reader=self.reader()
        with self.assertRaises(RuntimeError):reader.finish()
        reader.prepare()
        with self.assertRaises(RuntimeError):reader.prepare()
        with self.assertRaises(RuntimeError):reader.state_dict()
        with self.assertRaises(RuntimeError):reader.load_state_dict(self.reader().state_dict())
        reader.finish();self.assertEqual(reader.state_dict()['next_position'],3)

    def test_wrong_window_checksum_boolean_and_midbatch_cursor_are_rejected_before_IO(self):
        initial=self.reader();initial.prepare();initial.finish();saved=initial.state_dict()
        bad=[]
        value=copy.deepcopy(saved);value['state_sha256']='0'*64;bad.append(value)
        for key,value in(('next_position',True),('committed_batches',True),('next_position',1),('committed_batches',999)):
            item=copy.deepcopy(saved);item[key]=value
            item['state_sha256']=core._sha({k:v for k,v in item.items()if k!='state_sha256'});bad.append(item)
        for value in bad:
            reader=self.reader()
            with patch.object(core.os,'open',side_effect=AssertionError('feature IO forbidden')):
                with self.assertRaises(ValueError):reader.load_state_dict(value)
            self.assertEqual(reader.state_dict()['next_position'],0)
        other=self.reader(batch_positions=2)
        with self.assertRaises(ValueError):other.load_state_dict(saved)
        identities=copy.deepcopy(self.identities);identities['teacher_sha256']='F'*64
        other=core.FeatureWindow(self.records,root=self.root,identities=identities,split='train',hidden_width=4,batch_positions=3)
        with self.assertRaises(ValueError):other.load_state_dict(saved)

    def test_declared_metadata_and_output_metadata_have_no_mutable_alias_to_source(self):
        reader=self.reader();before=reader.contract
        self.records[0]['positions'][0]['target']=999
        self.identities['teacher_sha256']='F'*64
        batch=reader.prepare()
        self.assertNotEqual(batch.positions[0]['target'],999)
        batch.positions[0]['target']=888
        batch.rows['r0']['language']='changed'
        self.assertEqual(reader.contract,before)
        with self.assertRaises(ValueError):batch.values[0,0]=123

    def test_all_payload_metadata_record_and_position_quotas_precede_feature_IO(self):
        values=[dict(max_feature_bytes=79),dict(max_window_payload_bytes=239),dict(max_batch_bytes=47),
            dict(max_metadata_bytes=1),dict(max_records=2),dict(max_positions=6)]
        with patch.object(core.os,'open',side_effect=AssertionError('quota must precede feature IO')):
            for options in values:
                with self.subTest(options=options),self.assertRaises(ValueError):self.reader(**options)

    def test_bad_records_split_paths_duplicate_ID_and_predictor_indices_are_rejected(self):
        versions=[]
        for key,value in(('split','dev'),('feature_file','../outside.npy'),('feature_file','/tmp/outside.npy'),
            ('feature_file','sub/part.npy'),('feature_sha256','bad'),('teacher_tokens',True)):
            rows=copy.deepcopy(self.records);rows[0][key]=value;versions.append(rows)
        rows=copy.deepcopy(self.records);rows[1]['row_id']=rows[0]['row_id'];versions.append(rows)
        for index in(True,-1,5):
            rows=copy.deepcopy(self.records);rows[0]['positions'][0]['teacher_predictor_raw_index']=index;versions.append(rows)
        with patch.object(core.os,'open',side_effect=AssertionError('invalid metadata cannot open features')):
            for rows in versions:
                with self.assertRaises(ValueError):self.reader(rows)

    def test_NPY_shape_dtype_Fortran_and_object_headers_reject_before_array_allocation(self):
        versions=[('bad_f64.npy',np.ones((5,4),dtype=np.float64),False),
            ('bad_fortran.npy',np.asfortranarray(np.ones((5,4),dtype=np.float32)),False),
            ('bad_shape.npy',np.ones((6,4),dtype=np.float32),False),
            ('bad_object.npy',np.full((5,4),None,dtype=object),True)]
        for name,array,pickled in versions:
            rows=self.replacement(name,array,allow_pickle=pickled)
            reader=self.reader(rows)
            with (patch.object(core.np,'fromfile',side_effect=AssertionError('invalid header cannot allocate array')),
                patch.object(core.np,'load',side_effect=AssertionError('np.load/pickle forbidden'))):
                with self.assertRaises(ValueError):reader.prepare()

    def test_header_length_version_and_literal_are_bounded_before_payload_allocation(self):
        variants=[('bad_long.npy',b'\x93NUMPY\x01\x00'+struct.pack('<H',65535)+bytes(80)),
            ('bad_version.npy',b'\x93NUMPY\x03\x00'+bytes(80)),
            ('bad_literal.npy',b'\x93NUMPY\x01\x00'+struct.pack('<H',4)+b'123\n'+bytes(80))]
        for name,content in variants:
            path=self.root/name
            with path.open('xb')as stream:stream.write(content)
            record=copy.deepcopy(self.records[0]);record.update(feature_file=name,feature_sha256=digest(path))
            reader=self.reader([record])
            with patch.object(core.np,'fromfile',side_effect=AssertionError('header must fail before allocation')):
                with self.assertRaises(ValueError):reader.prepare()

    def test_exact_payload_length_and_whole_SHA_are_required_and_faults_break_cursor(self):
        original=(self.root/'r0.npy').read_bytes()
        for name,content in(('short.npy',original[:-4]),('tail.npy',original+b'EXTRA')):
            path=self.root/name
            with path.open('xb')as stream:stream.write(content)
            record=copy.deepcopy(self.records[0]);record.update(feature_file=name,feature_sha256=digest(path))
            reader=self.reader([record])
            with patch.object(core.np,'fromfile',side_effect=AssertionError('size must fail before array allocation')):
                with self.assertRaises(ValueError):reader.prepare()
        rows=copy.deepcopy(self.records);rows[0]['feature_sha256']='0'*64
        reader=self.reader(rows)
        with patch.object(core.np,'fromfile',side_effect=AssertionError('SHA must fail before array allocation')):
            with self.assertRaisesRegex(ValueError,'SHA differs'):reader.prepare()
        with self.assertRaises(RuntimeError):reader.state_dict()
        with self.assertRaises(RuntimeError):reader.prepare()
        with self.assertRaises(RuntimeError):reader.finish()

    def test_nonfinite_feature_is_not_silently_removed_or_changed(self):
        array=self.arrays[0].copy();array[4,0]=float('nan')
        rows=self.replacement('bad_finite.npy',array,allow_pickle=False)
        reader=self.reader(rows)
        with self.assertRaisesRegex(ValueError,'finite'):reader.prepare()
        with self.assertRaises(RuntimeError):reader.state_dict()
        self.assertTrue(np.isnan(array[4,0]))

    def test_symlink_hardlink_and_linked_root_are_rejected_without_following(self):
        alias=self.root/'link.npy';alias.symlink_to(self.root/'r0.npy')
        record=copy.deepcopy(self.records[0]);record['feature_file']=alias.name
        with self.assertRaises(ValueError):self.reader([record]).prepare()
        directory=self.root/'root_alias';directory.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):
            core.FeatureWindow(self.records,root=directory,identities=self.identities,split='train',hidden_width=4,batch_positions=3)
        hard=self.root/'hard.npy';os.link(self.root/'r0.npy',hard)
        record=copy.deepcopy(self.records[0]);record['feature_file']=hard.name
        with self.assertRaises(ValueError):self.reader([record]).prepare()

    def test_cached_file_metadata_change_is_detected_without_returning_stale_rows(self):
        reader=self.reader(batch_positions=1);reader.prepare();reader.finish()
        path=self.root/'r0.npy';info=path.stat()
        os.utime(path,ns=(info.st_atime_ns,info.st_mtime_ns+1000000))
        with self.assertRaisesRegex(ValueError,'cached source file changed'):reader.prepare()
        with self.assertRaises(RuntimeError):reader.state_dict()

    def test_global_position_denominator_matches_independent_double_CE_and_gradient(self):
        values=torch.tensor(self.expected(),dtype=torch.float64)
        targets=torch.tensor([p['target']for r in self.records for p in r['positions']],dtype=torch.long)
        weight=torch.linspace(-.05,.07,24,dtype=torch.float64).reshape(4,6).requires_grad_()
        expected=torch.nn.functional.cross_entropy(values@weight,targets)
        gradient=torch.autograd.grad(expected,weight)[0]
        other=weight.detach().clone().requires_grad_();pieces=[]
        reader=self.reader()
        for batch in self.all_batches(reader):
            x=torch.tensor(batch.values,dtype=torch.float64)
            y=torch.tensor([p['target']for p in batch.positions],dtype=torch.long)
            loss=torch.nn.functional.cross_entropy(x@other,y,reduction='sum')/len(values)
            pieces.append(float(loss.detach()));loss.backward()
        self.assertAlmostEqual(math.fsum(pieces),float(expected.detach()),delta=1e-12)
        torch.testing.assert_close(other.grad,gradient,atol=1e-12,rtol=1e-12)

    def test_completed_source_cursor_restores_end_without_any_feature_IO(self):
        reader=self.reader();self.all_batches(reader);saved=reader.state_dict()
        self.assertEqual((saved['next_position'],saved['committed_batches']),(7,3))
        other=self.reader();other.load_state_dict(saved)
        with patch.object(core.os,'open',side_effect=AssertionError('completed cursor cannot read features')):
            with self.assertRaises(StopIteration):other.prepare()
        self.assertEqual(other.stats['files_opened'],0)

    def test_default1024_width_4MiB_sources_keep_all412_positions_and512KiB_batches(self):
        arrays=[np.arange(1024**2,dtype=np.float32).reshape(1024,1024)/4096,
            -np.arange(1024**2,dtype=np.float32).reshape(1024,1024)/8192]
        indices=[list(range(0,1024,5))+[1023],list(range(1023,-1,-5))+[0]]
        records=[]
        for i,(array,selected)in enumerate(zip(arrays,indices)):
            path=self.root/('standard'+str(i)+'.npy')
            with path.open('xb')as stream:np.save(stream,array,allow_pickle=False)
            records.append(dict(row_id='standard'+str(i),semantic_root_id='standard_root'+str(i),split='train',
                feature_file=path.name,feature_sha256=digest(path),teacher_tokens=1024,
                positions=[dict(teacher_predictor_raw_index=index,target=index%6)for index in selected]))
        reader=core.FeatureWindow(records,root=self.root,identities=self.identities,split='train')
        batches=self.all_batches(reader)
        expected=np.concatenate([array[selected]for array,selected in zip(arrays,indices)])
        self.assertEqual(expected.shape,(412,1024))
        self.byte_equal(np.concatenate([batch.values for batch in batches]),expected)
        self.assertEqual([len(batch.values)for batch in batches],[128,128,128,28])
        self.assertEqual(reader.stats['maximum_feature_array_bytes'],4*1024**2)
        self.assertEqual(reader.stats['maximum_prepared_batch_bytes'],512*1024)
        self.assertEqual(reader.stats['files_opened'],2)
        self.assertEqual(reader.stats['payload_bytes_read'],8*1024**2)
        self.assertEqual(reader.state_dict()['next_position'],412)


if __name__=='__main__':unittest.main()
