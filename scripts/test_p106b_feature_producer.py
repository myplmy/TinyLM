"""Synthetic new-root recovery contracts; preserve every created file."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from scripts import p106b_feature_producer as core


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class ProducerContracts(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='tinylm-feature-producer-v1-',dir='/tmp'))
        self.root=self.base/'window'
        self.arrays=[np.arange(20,dtype=np.float32).reshape(5,4)/8,
                     np.arange(28,dtype=np.float32).reshape(7,4)/-16]
        self.arrays[0][0,0]=np.float32(-0.)
        self.rows=[dict(row_id='r'+str(i),semantic_root_id='source'+str(i),split='train',teacher_tokens=len(array),
            positions=[dict(teacher_predictor_raw_index=j,target=(i+j)%6)for j in indices])
            for i,(array,indices)in enumerate(zip(self.arrays,([4,0,2],[2,6,1,3])))]
        self.identities={name:letter*64 for name,letter in zip(
            ('teacher_sha256','tokenizer_sha256','mapping_sha256','data_sha256'),'ABCD')}

    def create(self,**options):
        return core.FeatureProducer.create(self.root,identities=self.identities,split='train',
            reader_options=dict(hidden_width=4,batch_positions=2),**options)

    def resume(self,recipe,**options):
        return core.FeatureProducer.resume(self.root,recipe_sha256=recipe,**options)

    def files(self):return {p.name:sha(p)for p in self.root.iterdir()}

    def new_journal(self,event=None,raw=None):
        path=self.root/('journal_'+uuid.uuid4().hex+'.jsonl')
        with path.open('xb')as stream:stream.write(core.canonical(event)if raw is None else raw)
        return path

    def selected(self,reader):
        result=[];order=[]
        while True:
            try:batch=reader.prepare()
            except StopIteration:break
            result.append(batch.values.copy());order.extend(zip(batch.row_ids,batch.positions));reader.finish()
        return np.concatenate(result),order

    def expected(self):
        return np.concatenate([a[[p['teacher_predictor_raw_index']for p in row['positions']]]
                               for row,a in zip(self.rows,self.arrays)])

    def test_sealed_production_preserves_all_original_bytes_metadata_order_and_source_counts(self):
        with self.create()as producer:
            for row,array in zip(self.rows,self.arrays):producer.append(row,array)
            before=producer.checkpoint()
            self.assertEqual((before['committed_records'],before['teacher_feature_rows'],before['selected_positions']),(2,12,7))
            with self.assertRaises(RuntimeError):producer.reader()
            sealed=producer.seal();reader=producer.reader();values,order=self.selected(reader)
            self.assertEqual(values.tobytes(),self.expected().tobytes())
            self.assertEqual(order,[(row['row_id'],p)for row in self.rows for p in row['positions']])
            for original,record in zip(self.rows,producer.records()):
                self.assertEqual(original,{k:v for k,v in record.items()if not k.startswith('feature_')})
                self.assertEqual(record['feature_sha256'],sha(self.root/record['feature_file']))
            self.assertTrue(sealed['sealed']);self.assertFalse(sealed['corpus_admitted'])
            self.assertIn('NOT_MODEL_ITERATOR_RNG_OR_OPTIMIZER',sealed['source_scope'])
        self.assertTrue((self.root/'writer.lock').exists())

    def test_new_segment_resume_extends_exact_prefix_without_changing_any_previous_file(self):
        with self.create()as first:
            checkpoint=first.append(self.rows[0],self.arrays[0]);recipe=first.recipe_sha256
        before=self.files()
        with self.resume(recipe,expected_prefix=checkpoint)as second:
            self.assertEqual(second.checkpoint(),checkpoint)
            second.append(self.rows[1],self.arrays[1]);second.seal()
            values,_=self.selected(second.reader())
            self.assertEqual(values.tobytes(),self.expected().tobytes())
        for name,value in before.items():self.assertEqual(sha(self.root/name),value)

    def test_interruption_after_payload_retains_orphan_and_does_not_duplicate_committed_rows(self):
        first=self.create();first.append(self.rows[0],self.arrays[0]);recipe=first.recipe_sha256
        with patch.object(first,'_publish',side_effect=RuntimeError('injected post-payload interruption')):
            with self.assertRaisesRegex(RuntimeError,'post-payload'):first.append(self.rows[1],self.arrays[1])
        with self.assertRaises(RuntimeError):first.checkpoint()
        first.close();before=self.files()
        with self.resume(recipe)as second:
            self.assertEqual(second.checkpoint()['committed_records'],1)
            self.assertEqual(len(second.orphan_features),1)
            second.append(self.rows[1],self.arrays[1]);second.seal()
            values,_=self.selected(second.reader());self.assertEqual(values.tobytes(),self.expected().tobytes())
        for name,value in before.items():self.assertEqual(sha(self.root/name),value)
        self.assertEqual(len([p for p in self.root.iterdir()if p.suffix=='.npy']),3)

    def test_torn_final_event_bytes_are_recorded_and_preserved_in_a_new_segment_recovery(self):
        first=self.create();first.append(self.rows[0],self.arrays[0]);recipe=first.recipe_sha256
        tails=[]
        def interrupt(event):
            raw=core.canonical(event)
            tails.append(self.new_journal(raw=raw[:len(raw)//2]))
            raise RuntimeError('injected partial event')
        with patch.object(first,'_publish',side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,'partial event'):first.append(self.rows[1],self.arrays[1])
        first.close();before=self.files()
        with self.resume(recipe)as second:
            self.assertEqual(second.checkpoint()['committed_records'],1)
            self.assertEqual(len(second.partial_tails),1)
            self.assertEqual(second.partial_tails[0]['sha256'],sha(tails[0]))
            second.append(self.rows[1],self.arrays[1]);second.seal()
            values,_=self.selected(second.reader());self.assertEqual(values.tobytes(),self.expected().tobytes())
        for name,value in before.items():self.assertEqual(sha(self.root/name),value)

    def test_malformed_complete_event_is_not_hidden_as_an_incomplete_tail(self):
        with self.create()as producer:recipe=producer.recipe_sha256
        bad=self.new_journal(raw=b'not canonical JSON'+bytes([10]))
        before=sha(bad)
        with self.assertRaises((ValueError,json.JSONDecodeError)):self.resume(recipe)
        self.assertEqual(sha(bad),before)

    def test_complete_event_bad_checksum_or_chain_and_sequence_gaps_fail_closed(self):
        for kind in('checksum','chain','gap'):
            self.root=self.base/kind
            with self.create()as producer:
                producer.append(self.rows[0],self.arrays[0]);recipe=producer.recipe_sha256
                event=producer._event('seal',window_sha256='F'*64)
            if kind=='checksum':event['event_sha256']='F'*64
            if kind=='chain':event['previous_sha256']='F'*64
            if kind=='gap':event['sequence']+=1
            if kind!='checksum':event['event_sha256']=core.window._sha({k:v for k,v in event.items()if k!='event_sha256'})
            self.new_journal(event=event);before=self.files()
            with self.assertRaises(ValueError):self.resume(recipe)
            self.assertEqual(self.files(),before)

    def test_concurrent_writer_lock_is_rejected_and_persistent_lock_is_not_deleted(self):
        with self.create()as first:
            before=self.files()
            with self.assertRaises(BlockingIOError):self.resume(first.recipe_sha256)
            self.assertEqual(self.files(),before)
        self.assertTrue((self.root/'writer.lock').exists())

    def test_wrong_recipe_source_version_and_strict_cursor_schema_are_rejected(self):
        with self.create()as first:
            checkpoint=first.append(self.rows[0],self.arrays[0]);recipe=first.recipe_sha256
        with self.assertRaisesRegex(ValueError,'recipe SHA'):self.resume('F'*64)
        original=core.file_digest
        def changed(path):
            if path==Path(core.window.__file__):return 'F'*64
            return original(path)
        with patch.object(core,'file_digest',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'recipe/source/root'):self.resume(recipe)
        for key,value in(('committed_records',True),('teacher_feature_rows',999),('schema','wrong'),('sealed',True)):
            invalid=copy.deepcopy(checkpoint);invalid[key]=value
            with self.assertRaisesRegex(ValueError,'source prefix'):self.resume(recipe,expected_prefix=invalid)

    def test_payload_and_journal_quotas_precede_any_new_payload_file(self):
        for name,options in(('physical',dict(max_physical_bytes=4000)),('journal',dict(max_journal_bytes=64))):
            self.root=self.base/name
            with self.create(**options)as producer:
                before=self.files()
                with self.assertRaisesRegex(ValueError,'quota'):producer.append(self.rows[0],self.arrays[0])
                self.assertEqual(self.files(),before)

    def test_orphan_bytes_count_against_recovery_physical_budget_before_array_IO(self):
        with self.create(max_physical_bytes=10000)as first:recipe=first.recipe_sha256
        path=self.root/('feature_'+uuid.uuid4().hex+'.npy')
        with path.open('xb')as stream:stream.write(bytes(10001))
        with patch.object(core.window.np,'fromfile',side_effect=AssertionError('quota must precede array IO')):
            with self.assertRaisesRegex(ValueError,'physical byte quota'):self.resume(recipe)
        self.assertEqual(path.stat().st_size,10001)

    def test_file_count_quota_blocks_seal_without_changing_prior_files(self):
        with self.create(max_files=4)as producer:
            producer.append(self.rows[0],self.arrays[0]);before=self.files()
            with self.assertRaisesRegex(ValueError,'physical byte/file quota'):producer.seal()
            self.assertEqual(self.files(),before)

    def test_invalid_array_split_reserved_path_and_empty_selection_fail_before_payload_write(self):
        for kind in('dtype','finite','split','reserved','empty'):
            self.root=self.base/kind
            with self.create()as producer:
                row=copy.deepcopy(self.rows[0]);array=self.arrays[0].copy()
                if kind=='dtype':array=array.astype(np.float64)
                if kind=='finite':array[0,0]=float('nan')
                if kind=='split':row['split']='dev'
                if kind=='reserved':row['feature_file']='../outside.npy'
                if kind=='empty':row['positions']=[]
                before=self.files()
                with self.assertRaises(ValueError):producer.append(row,array)
                self.assertEqual(self.files(),before)

    def test_duplicate_row_is_not_recomputed_or_silently_overwritten(self):
        with self.create()as producer:
            producer.append(self.rows[0],self.arrays[0]);before=self.files()
            with self.assertRaisesRegex(ValueError,'duplicate row'):producer.append(self.rows[0],self.arrays[0])
            self.assertEqual(self.files(),before)

    def test_bad_committed_payload_hash_is_rejected_without_rewriting_any_file(self):
        with self.create()as producer:
            producer.append(self.rows[0],self.arrays[0]);recipe=producer.recipe_sha256
            record=copy.deepcopy(self.rows[1]);path=self.root/('feature_'+uuid.uuid4().hex+'.npy')
            with path.open('xb')as stream:np.save(stream,self.arrays[1],allow_pickle=False)
            record.update(feature_file=path.name,feature_sha256=sha(path),feature_payload_sha256='F'*64)
            event=producer._event('record',record=record)
        self.new_journal(event=event);before=self.files()
        with self.assertRaisesRegex(ValueError,'original payload bytes'):self.resume(recipe)
        self.assertEqual(self.files(),before)

    def test_root_symlink_or_hardlinked_file_is_rejected_without_following_external_sources(self):
        with self.create()as producer:
            producer.append(self.rows[0],self.arrays[0]);recipe=producer.recipe_sha256
        alias=self.base/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'unlinked root'):
            core.FeatureProducer.resume(alias,recipe_sha256=recipe)
        payload=next(p for p in self.root.iterdir()if p.suffix=='.npy')
        other=self.root/('feature_'+uuid.uuid4().hex+'.npy')
        import os
        os.link(payload,other)
        with self.assertRaisesRegex(ValueError,'linked/nonregular'):self.resume(recipe)

    def test_sealed_recovery_accepts_a_prior_prefix_but_forbids_new_appends(self):
        with self.create()as producer:
            prefix=producer.append(self.rows[0],self.arrays[0]);recipe=producer.recipe_sha256
            producer.seal();sealed=producer.checkpoint()
        before=self.files()
        with self.resume(recipe,expected_prefix=prefix)as other:
            self.assertEqual(other.checkpoint(),sealed)
            with self.assertRaises(RuntimeError):other.append(self.rows[1],self.arrays[1])
            self.assertEqual(self.files(),before)

    def test_empty_source_cannot_be_sealed_as_an_admitted_window(self):
        with self.create()as producer:
            with self.assertRaises(ValueError):producer.seal()
            with self.assertRaises(RuntimeError):producer.reader()
            self.assertFalse(any(p.suffix=='.npy'for p in self.root.iterdir()))

    def test_published_event_before_caller_failure_is_recovered_as_committed_exactly_once(self):
        first=self.create();prefix=first.checkpoint();recipe=first.recipe_sha256
        original=first._publish
        def interrupt(event):
            original(event)
            raise RuntimeError('injected after durable complete event')
        with patch.object(first,'_publish',side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,'durable complete'):first.append(self.rows[0],self.arrays[0])
        first.close();before=self.files()
        with self.resume(recipe,expected_prefix=prefix)as second:
            self.assertEqual(second.checkpoint()['committed_records'],1)
            self.assertFalse(second.orphan_features)
            second.append(self.rows[1],self.arrays[1]);second.seal()
            values,_=self.selected(second.reader());self.assertEqual(values.tobytes(),self.expected().tobytes())
        for name,value in before.items():self.assertEqual(sha(self.root/name),value)

    def test_partial_seal_can_be_retried_in_a_new_segment_without_mutating_old_tail(self):
        first=self.create();prefix=first.append(self.rows[0],self.arrays[0]);recipe=first.recipe_sha256
        def interrupt(event):
            raw=core.canonical(event);self.new_journal(raw=raw[:len(raw)//2])
            raise RuntimeError('injected partial seal')
        with patch.object(first,'_publish',side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,'partial seal'):first.seal()
        first.close();before=self.files()
        with self.resume(recipe,expected_prefix=prefix)as second:
            self.assertFalse(second.checkpoint()['sealed'])
            self.assertEqual(len(second.partial_tails),1)
            second.seal();values,_=self.selected(second.reader())
            wanted=self.arrays[0][[p['teacher_predictor_raw_index']for p in self.rows[0]['positions']]]
            self.assertEqual(values.tobytes(),wanted.tobytes())
        for name,value in before.items():self.assertEqual(sha(self.root/name),value)

    def test_default1024_width_two4MiB_files_resume_and_preserve_all412_selected_rows(self):
        arrays=[np.arange(1024**2,dtype=np.float32).reshape(1024,1024)/4096,
                -np.arange(1024**2,dtype=np.float32).reshape(1024,1024)/8192]
        indices=[list(range(0,1024,5))+[1023],list(range(1023,-1,-5))+[0]]
        records=[dict(row_id='standard'+str(i),semantic_root_id='standard_root'+str(i),split='train',
            teacher_tokens=1024,positions=[dict(teacher_predictor_raw_index=j)for j in selected])
            for i,selected in enumerate(indices)]
        with core.FeatureProducer.create(self.root,identities=self.identities,split='train')as first:
            prefix=first.append(records[0],arrays[0]);recipe=first.recipe_sha256
        before=self.files()
        with self.resume(recipe,expected_prefix=prefix)as second:
            second.append(records[1],arrays[1]);state=second.seal();reader=second.reader()
            batches=[]
            while True:
                try:batch=reader.prepare()
                except StopIteration:break
                batches.append(batch.values.copy());reader.finish()
            expected=np.concatenate([array[selected]for array,selected in zip(arrays,indices)])
            self.assertEqual(expected.shape,(412,1024))
            self.assertEqual(np.concatenate(batches).tobytes(),expected.tobytes())
            self.assertEqual([len(batch)for batch in batches],[128,128,128,28])
            self.assertEqual(reader.stats['maximum_feature_array_bytes'],4*1024**2)
            self.assertEqual(reader.stats['maximum_prepared_batch_bytes'],512*1024)
            self.assertEqual((state['teacher_feature_rows'],state['selected_positions']),(2048,412))
        for name,value in before.items():self.assertEqual(sha(self.root/name),value)

    def test_produced_sealed_source_feeds_original_frame_consumer_with_independent_gradients(self):
        import torch
        from scripts.test_p106b_dskdv2_window import NativeWindowContracts
        fixture=NativeWindowContracts();fixture.setUpClass();fixture.setUp()
        with self.create()as producer:
            for row,array in zip(fixture.records,fixture.arrays):
                metadata={k:v for k,v in row.items()if k not in('feature_file','feature_sha256')}
                producer.append(metadata,array)
            producer.seal();reader=producer.reader()
            params,frames,bases=fixture.tensors()
            expected,_=fixture.independent(params,frames,rate=.3)
            gradients=torch.autograd.grad(expected,[params[0],params[1],params[3]])
            actual,other_frames,other_bases=fixture.tensors()
            report=fixture.run_update(fixture.consumer(reader,kd_rate=.3),actual,other_frames)
            self.assertAlmostEqual(report['normalized_loss'],float(expected.detach()),delta=1e-10)
            for tensor,gradient in zip((actual[0],actual[1],actual[3]),gradients):
                torch.testing.assert_close(tensor.grad,gradient,atol=1e-10,rtol=1e-10)
            self.assertFalse(report['full_training_checkpoint_or_resume'])
            self.assertFalse(torch.cuda.is_initialized())


if __name__=='__main__':unittest.main()
