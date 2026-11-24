"""Stateful synthetic source and new-root failure/recovery controls only."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from scripts import p106b_feature_schedule as core
from scripts import p106b_feature_producer as lower

FIXTURE_BASES=[]
DEFAULT_PROFILE=[]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def fingerprint(root):
    return {str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()and not p.is_symlink()and p.stat().st_nlink==1}
def preserve(root,before):
    for name,expected in before.items():
        assert(root/name).is_file(),name
        assert sha(root/name)==expected,name

class SyntheticSource:
    def __init__(self,*,count=5,width=4,tokens=None,selected=2,seed=1337):
        self.contract=dict(kind='AUTHORED_PCG64_FEATURE_SOURCE',count=count,width=width,
            tokens=tokens,selected=selected,seed=seed,numpy_version=np.__version__)
        self.index=0;self.rng=np.random.Generator(np.random.PCG64(seed));self.calls=0;self.emitted=[]

    def state_dict(self):
        return core.source_boundary(self.contract,self.index,dict(index=self.index),self.rng.bit_generator.state)

    def load_state_dict(self,value):
        if(value['source_contract_sha256']!=core._sha(self.contract)
                or value['next_record']!=value['source_cursor']['index']):raise ValueError('synthetic source state differs')
        self.index=value['next_record'];self.rng.bit_generator.state=copy.deepcopy(value['rng_state'])

    def next_feature(self):
        self.calls+=1
        if self.index==self.contract['count']:raise StopIteration
        index=self.index;tokens=self.contract['tokens']or 5+index%3
        array=self.rng.standard_normal((tokens,self.contract['width'])).astype(np.float32)
        array[0,0]=np.float32(-0.)
        indices=[0]+[int(i)for i in self.rng.permutation(np.arange(1,tokens))[:self.contract['selected']-1]]
        row=dict(row_id='r'+str(index),semantic_root_id='authored'+str(index),split='train',
            teacher_tokens=tokens,positions=[dict(teacher_predictor_raw_index=i,target=index%6)for i in indices])
        self.index+=1;self.emitted.append((copy.deepcopy(row),array.copy()))
        return row,array

class Clock:
    def __init__(self,value=0.):self.value=value
    def __call__(self):return self.value

class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='p106b-feature-schedule-v1-',dir='/tmp'))
        FIXTURE_BASES.append(self.base)
        self.identities={name:letter*64 for name,letter in zip(
            ('teacher_sha256','tokenizer_sha256','mapping_sha256','data_sha256'),'ABCD')}

    def create(self,source=None,name='schedule',**options):
        source=SyntheticSource()if source is None else source
        reader=dict(hidden_width=source.contract['width'],batch_positions=2,max_records=2)
        reader.update(options.pop('reader_options',{}))
        return core.FeatureSchedule.create(self.base/name,source=source,identities=self.identities,
            split='train',reader_options=reader,**options)

    def resume(self,recipe,source=None,name='schedule',**options):
        return core.FeatureSchedule.resume(self.base/name,source=SyntheticSource()if source is None else source,
            recipe_sha256=recipe,**options)

    def drain(self,schedule):
        for _ in range(100):
            result=schedule.advance()
            if result['status']!='COMMITTED':return result
        raise AssertionError('synthetic drain did not stop')

    def selected(self,schedule):
        values=[];order=[]
        for reader in schedule.sealed_readers():
            while True:
                try:batch=reader.prepare()
                except StopIteration:break
                values.append(batch.values.copy());order.extend(zip(batch.row_ids,batch.positions));reader.finish()
        return(np.concatenate(values)if values else np.empty((0,4),dtype=np.float32)),order

    def expected(self,source):
        values=[];order=[]
        for row,array in source.emitted:
            values.append(array[[p['teacher_predictor_raw_index']for p in row['positions']]])
            order.extend((row['row_id'],p)for p in row['positions'])
        return np.concatenate(values),order

    def test_rollover_preserves_original_bytes_positions_order_and_explicit_source_state(self):
        source=SyntheticSource()
        with self.create(source)as schedule:
            result=self.drain(schedule);cp=schedule.checkpoint();values,order=self.selected(schedule)
            expected,expected_order=self.expected(source)
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(len(cp['windows']),3)
            self.assertEqual(cp['source_state'],source.state_dict());self.assertEqual(cp['committed_records'],5)
            self.assertEqual(cp['teacher_feature_rows'],29);self.assertEqual(cp['selected_positions'],10)
            self.assertEqual(values.tobytes(),expected.tobytes());self.assertEqual(order,expected_order)
            self.assertFalse(cp['corpus_admitted']);self.assertIn('NOT_MODEL_OR_OPTIMIZER',cp['resume_scope'])
            for row,_ in source.emitted:self.assertNotIn(core.TRANSITION,row)

    def test_fresh_resume_restores_PCG64_and_exact_future_features(self):
        baseline=SyntheticSource()
        with self.create(baseline,name='baseline')as full:
            self.drain(full);expected_values,expected_order=self.selected(full);expected_state=full.checkpoint()['source_state']
        source=SyntheticSource()
        with self.create(source)as first:
            first.advance();prefix=first.advance()['checkpoint'];recipe=first.recipe_sha256
        before=fingerprint(self.base/'schedule');fresh=SyntheticSource()
        with self.resume(recipe,source=fresh,expected_prefix=prefix)as reopened:
            self.assertEqual(fresh.state_dict(),prefix['source_state'])
            self.drain(reopened);values,order=self.selected(reopened)
            self.assertEqual(values.tobytes(),expected_values.tobytes());self.assertEqual(order,expected_order)
            self.assertEqual(reopened.checkpoint()['source_state'],expected_state)
        preserve(self.base/'schedule',before)

    def test_lagging_prefix_is_verified_without_discarding_later_commits(self):
        with self.create()as first:
            prefix=first.advance()['checkpoint'];recipe=first.recipe_sha256
            for _ in range(3):first.advance()
        before=fingerprint(self.base/'schedule')
        with self.resume(recipe,expected_prefix=prefix)as fresh:
            self.assertEqual(fresh.checkpoint()['committed_records'],4)
            self.assertEqual(fresh.source.index,4);self.drain(fresh)
            self.assertEqual(fresh.checkpoint()['committed_records'],5)
        preserve(self.base/'schedule',before)

    def test_lower_complete_record_before_caller_failure_advances_recovery_once(self):
        original=lower.FeatureProducer.append
        def after_commit(child,*args,**kwargs):
            original(child,*args,**kwargs);raise RuntimeError('injected after lower commit')
        first=self.create();recipe=first.recipe_sha256
        with patch.object(lower.FeatureProducer,'append',after_commit):
            with self.assertRaisesRegex(RuntimeError,'after lower commit'):first.advance()
        with self.assertRaises(RuntimeError):first.checkpoint()
        first.close();before=fingerprint(self.base/'schedule');source=SyntheticSource()
        with self.resume(recipe,source=source)as recovered:
            self.assertEqual(source.index,1);self.assertEqual(recovered.checkpoint()['committed_records'],1)
            self.drain(recovered);self.assertEqual(recovered.checkpoint()['committed_records'],5)
            self.assertEqual(len({r['row_id']for w in recovered._windows for r in w['records']}),5)
        preserve(self.base/'schedule',before)

    def test_uncommitted_payload_is_retained_and_upstream_source_is_replayed(self):
        first=self.create();recipe=first.recipe_sha256
        original=lower.FeatureProducer._publish
        def before_event(child,event):
            if event['kind']=='record':raise RuntimeError('injected before lower record event')
            return original(child,event)
        with patch.object(lower.FeatureProducer,'_publish',before_event):
            with self.assertRaisesRegex(RuntimeError,'before lower'):first.advance()
        first.close();before=fingerprint(self.base/'schedule')
        with self.resume(recipe)as fresh:
            self.assertEqual(fresh.source.index,0);self.assertEqual(len(fresh._active.orphan_features),1)
            self.drain(fresh);self.assertEqual(fresh.checkpoint()['committed_records'],5)
        preserve(self.base/'schedule',before)

    def test_partial_lower_event_does_not_advance_source_and_remains_immutable(self):
        first=self.create();first.advance();recipe=first.recipe_sha256
        def partial(event):
            raw=lower.canonical(event);path=first._active.root/('journal_'+uuid.uuid4().hex+'.jsonl')
            with path.open('xb')as stream:stream.write(raw[:len(raw)//2])
            raise RuntimeError('injected partial lower event')
        with patch.object(first._active,'_publish',partial):
            with self.assertRaisesRegex(RuntimeError,'partial lower'):first.advance()
        first.close();before=fingerprint(self.base/'schedule')
        with self.resume(recipe)as fresh:
            self.assertEqual(fresh.source.index,1);self.assertEqual(len(fresh._active.partial_tails),1)
            self.drain(fresh)
        preserve(self.base/'schedule',before)

    def test_partial_global_open_retains_orphan_directory_and_source_boundary(self):
        first=self.create();recipe=first.recipe_sha256
        def partial(event):
            raw=lower.canonical(event);path=first.root/('event_'+uuid.uuid4().hex+'.jsonl')
            with path.open('xb')as stream:stream.write(raw[:len(raw)//2])
            raise RuntimeError('injected partial global open')
        with patch.object(first,'_publish_event',partial):
            with self.assertRaisesRegex(RuntimeError,'partial global'):first.advance()
        first.close();before=fingerprint(self.base/'schedule')
        with self.resume(recipe)as fresh:
            self.assertEqual(fresh.source.index,0);self.assertEqual(len(fresh.partial_tails),1)
            self.assertEqual(len(fresh.orphan_windows),1);self.drain(fresh)
            self.assertEqual(fresh.checkpoint()['committed_records'],5)
        preserve(self.base/'schedule',before)

    def test_lower_seal_committed_before_global_close_is_recovered(self):
        first=self.create(reader_options=dict(max_records=1));first.advance()
        prefix=first.checkpoint();recipe=first.recipe_sha256;original=first._publish_event
        def missing_close(event):
            if event['kind']=='close':raise RuntimeError('injected missing global close')
            return original(event)
        with patch.object(first,'_publish_event',missing_close):
            with self.assertRaisesRegex(RuntimeError,'missing global close'):first.advance()
        first.close();before=fingerprint(self.base/'schedule')
        with self.resume(recipe,expected_prefix=prefix)as fresh:
            self.assertEqual(fresh.source.index,1);self.assertTrue(fresh._windows[0]['closed'])
            self.drain(fresh);self.assertEqual(fresh.checkpoint()['committed_records'],5)
        preserve(self.base/'schedule',before)

    def test_complete_corrupt_or_gapped_global_events_are_not_partial_tails(self):
        for kind in('checksum','gap'):
            with self.subTest(kind=kind):
                with self.create(name=kind)as first:
                    recipe=first.recipe_sha256;event=first._event('done',source_state_sha256=core._sha(first._last_state))
                    if kind=='checksum':event['event_sha256']='F'*64
                    else:
                        event['sequence']=1;event['event_sha256']=core._sha({k:v for k,v in event.items()if k!='event_sha256'})
                    with(first.root/('event_'+uuid.uuid4().hex+'.jsonl')).open('xb')as stream:stream.write(lower.canonical(event))
                before=fingerprint(self.base/kind)
                with self.assertRaises(ValueError):self.resume(recipe,name=kind)
                preserve(self.base/kind,before)

    def test_source_contract_or_nonfresh_adapter_rejected_without_new_fetch(self):
        with self.create()as first:recipe=first.recipe_sha256
        wrong=SyntheticSource(seed=7)
        with self.assertRaises(ValueError):self.resume(recipe,source=wrong)
        self.assertEqual(wrong.calls,0)
        nonfresh=SyntheticSource();nonfresh.next_feature()
        with self.assertRaises(ValueError):self.resume(recipe,source=nonfresh)
        self.assertEqual(nonfresh.calls,1)

    def test_boolean_boundary_and_inexact_source_restore_are_refused(self):
        class BooleanState(SyntheticSource):
            def state_dict(self):
                value=super().state_dict();value['next_record']=True;return value
        bad=BooleanState()
        with self.assertRaises(ValueError):self.create(bad,name='bad')
        self.assertEqual(bad.calls,0)
        with self.create()as first:
            first.advance();recipe=first.recipe_sha256
        class InexactRestore(SyntheticSource):
            def load_state_dict(self,value):return
        with self.assertRaisesRegex(ValueError,'restore exact'):self.resume(recipe,source=InexactRestore())

    def test_duplicate_row_ids_across_windows_are_refused_before_commit(self):
        class DuplicateSource(SyntheticSource):
            def next_feature(self):
                row,array=super().next_feature();row['row_id']='duplicate';return row,array
        with self.create(DuplicateSource(),reader_options=dict(max_records=1))as schedule:
            schedule.advance();before=fingerprint(schedule.root)
            with self.assertRaisesRegex(ValueError,'duplicate source row'):schedule.advance()
        preserve(self.base/'schedule',before)

    def test_feature_budget_restores_uncommitted_cursor_RNG_and_keeps_units_distinct(self):
        source=SyntheticSource()
        with self.create(source,limits=dict(max_feature_rows=10))as schedule:
            prefix=schedule.advance()['checkpoint'];before=source.state_dict();files=fingerprint(schedule.root)
            result=schedule.advance()
            self.assertEqual(result['status'],'PAUSED');self.assertEqual(source.state_dict(),before)
            self.assertEqual(source.calls,2);self.assertEqual(schedule.checkpoint()['committed_records'],1)
            self.assertEqual(schedule.checkpoint()['teacher_feature_rows'],5)
            self.assertEqual(schedule.checkpoint()['selected_positions'],2)
            self.assertEqual(schedule.checkpoint(),prefix)
            schedule.advance();self.assertEqual(source.calls,2);preserve(schedule.root,files)
            schedule.seal_window();self.assertEqual(len(schedule.sealed_readers()),1)

    def test_window_and_global_physical_budgets_pause_without_consuming_next_source(self):
        for label,limits in[('windows',dict(max_windows=1)),('bytes',dict(max_physical_bytes=8192)),('files',dict(max_files=2))]:
            with self.subTest(label=label):
                source=SyntheticSource()
                with self.create(source,name=label,limits=limits,reader_options=dict(max_records=1))as schedule:
                    if label=='windows':schedule.advance()
                    before=source.state_dict();files=fingerprint(schedule.root)
                    result=schedule.advance();self.assertEqual(result['status'],'PAUSED')
                    self.assertEqual(source.state_dict(),before);preserve(schedule.root,files)

    def test_prefetch_deadline_does_not_claim_hard_callback_cancellation_and_new_open_resumes(self):
        clock=Clock();source=SyntheticSource();original=source.next_feature
        def slow():
            value=original();clock.value=10.;return value
        source.next_feature=slow
        with self.create(source,session_seconds=5,clock=clock)as schedule:
            self.assertEqual(schedule.advance()['status'],'COMMITTED')
            self.assertEqual(schedule.advance()['reason'],'SESSION_PREFETCH_DEADLINE')
            self.assertEqual(source.calls,1);recipe=schedule.recipe_sha256
        with self.resume(recipe,session_seconds=5,clock=Clock())as fresh:
            self.assertEqual(fresh.source.index,1);self.assertEqual(self.drain(fresh)['status'],'COMPLETE')

    def test_persistent_lock_and_linked_or_unexpected_entries_are_refused(self):
        first=self.create();recipe=first.recipe_sha256
        with self.assertRaises(BlockingIOError):self.resume(recipe)
        first.close()
        target=self.base/'owned_external_fixture.bin'
        with target.open('xb')as stream:stream.write(b'owned fixture only')
        link=self.base/'schedule'/('event_'+uuid.uuid4().hex+'.jsonl');link.symlink_to(target)
        with self.assertRaises(ValueError):self.resume(recipe)
        self.assertTrue(link.is_symlink());self.assertEqual(target.read_bytes(),b'owned fixture only')

    def test_valid_lower_commit_with_wrong_source_transition_is_rejected_on_recovery(self):
        source=SyntheticSource();first=self.create(source);first.advance();recipe=first.recipe_sha256
        before=copy.deepcopy(first.recipe['initial_source_state']);row,array=source.next_feature()
        row[core.TRANSITION]=dict(schema=core.TRANSITION_SCHEMA,sequence=1,before=before,after=source.state_dict())
        first._active.append(row,array);first.close();files=fingerprint(self.base/'schedule')
        with self.assertRaisesRegex(ValueError,'transition chain'):self.resume(recipe)
        preserve(self.base/'schedule',files)

    def test_rehashed_prefix_with_changed_counters_or_source_state_is_refused(self):
        with self.create()as first:
            prefix=first.advance()['checkpoint'];recipe=first.recipe_sha256
        for field in('source_state','committed_records'):
            bad=copy.deepcopy(prefix)
            if field=='source_state':bad[field]['next_record']=99
            else:bad[field]=True
            bad['state_sha256']=core._sha({k:v for k,v in bad.items()if k!='state_sha256'})
            with self.subTest(field=field),self.assertRaises(ValueError):self.resume(recipe,expected_prefix=bad)

    def test_1024_width_three4MiB_windows_have_exact_selected_bytes_and_bounded_batches(self):
        source=SyntheticSource(count=3,width=1024,tokens=1024,selected=206)
        with self.create(source,reader_options=dict(hidden_width=1024,batch_positions=128,max_records=1))as schedule:
            self.assertEqual(self.drain(schedule)['status'],'COMPLETE')
            cp=schedule.checkpoint();expected,expected_order=self.expected(source)
            values,order=self.selected(schedule);self.assertEqual(values.tobytes(),expected.tobytes());self.assertEqual(order,expected_order)
            self.assertEqual(len(cp['windows']),3);self.assertEqual(cp['teacher_feature_rows'],3072)
            self.assertEqual(cp['selected_positions'],618)
            readers=schedule.sealed_readers();maximum=0
            for reader in readers:
                while True:
                    try:batch=reader.prepare()
                    except StopIteration:break
                    maximum=max(maximum,batch.values.nbytes);reader.finish()
            self.assertEqual(maximum,524288)
            DEFAULT_PROFILE.append(dict(root=str(schedule.root),windows=3,original_arrays=3,
                original_payload_bytes=3*4194304,teacher_feature_rows=3072,selected_positions=618,
                maximum_batch_bytes=maximum,source_state=cp['source_state'],
                exact_selected_bytes=True,forced_window_max_records=1))

if __name__=='__main__':unittest.main()
