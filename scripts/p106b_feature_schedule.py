"""Bounded Linux feature-window coordination with explicit source-only state.

Lower complete feature events own commit status. Upstream adapters must expose
their declared cursor/RNG; this is not a model/optimizer checkpoint or corpus
admission. Failed external calls can be repeated when no record was committed.
No old window is deleted, renamed, rewritten or appended after it is closed.
"""
from __future__ import annotations

import copy
import fcntl
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid
import json

import numpy as np

from scripts import p106b_feature_producer as producer
from scripts import p106b_feature_window as window

SCHEMA='P106B_FEATURE_SCHEDULE_RECIPE_V1'
EVENT_SCHEMA='P106B_FEATURE_SCHEDULE_EVENT_V1'
SOURCE_SCHEMA='P106B_FEATURE_SOURCE_BOUNDARY_V1'
TRANSITION_SCHEMA='P106B_FEATURE_SOURCE_TRANSITION_V1'
STATE_SCHEMA='P106B_FEATURE_SCHEDULE_CURSOR_V1'
SCOPE='EXPLICIT_UPSTREAM_CURSOR_RNG_AND_FEATURE_RECORDS_NOT_MODEL_OR_OPTIMIZER'
TRANSITION='_feature_source_transition'
HARD_LIMITS=dict(max_windows=16,max_records=16384,max_feature_rows=4194304,
    max_selected_positions=1048576,max_physical_bytes=1073741824,max_files=65536,
    max_journal_metadata_bytes=8388608,max_source_state_bytes=16384,max_event_bytes=131072)
WINDOW_NAME=re.compile(r'window_[0-9a-f]{32}')
EVENT_NAME=re.compile(r'event_[0-9a-f]{32}\.jsonl')
SHA=re.compile(r'[0-9A-F]{64}')

def _sha(value):return window._sha(value)
def _copy(value):return json.loads(window._canonical(value))
def _hex(value):return type(value)is str and SHA.fullmatch(value)is not None
def _int(value,label,minimum=0):window._integer(value,label,minimum)
def _bounded(value,maximum,label):
    try:raw=producer.canonical(value)
    except (TypeError,ValueError,OverflowError,RecursionError)as exc:
        raise ValueError('bounded canonical JSON required: '+label)from exc
    if len(raw)>maximum:raise ValueError('canonical JSON byte quota: '+label)
    return json.loads(raw)

def source_boundary(contract,next_record,source_cursor,rng_state):
    """Create a detached declaration; the adapter owns its actual correctness."""
    _int(next_record,'next_record')
    if type(contract)is not dict or not contract or type(source_cursor)is not dict or type(rng_state)is not dict:
        raise ValueError('explicit source contract/cursor/RNG objects required')
    contract=_bounded(contract,HARD_LIMITS['max_source_state_bytes'],'source contract')
    return _bounded(dict(schema=SOURCE_SCHEMA,source_contract_sha256=_sha(contract),
        next_record=next_record,source_cursor=source_cursor,rng_state=rng_state),
        HARD_LIMITS['max_source_state_bytes'],'source boundary')

class FeatureSchedule:
    """One new bounded root; unchanged FeatureProducer objects own each window.

    source.contract is a bounded JSON object. source.state_dict(),
    source.load_state_dict(state), source.next_feature() implement the explicit
    protocol. next_feature returns (metadata, original C-order FP32 array) or
    raises StopIteration without changing state. A complete record must advance
    next_record exactly once. The caller owns every external/model side effect.
    """
    @classmethod
    def create(cls,root,*,source,identities,split,reader_options=None,producer_limits=None,
               limits=None,session_seconds=28800,clock=time.monotonic):
        path=Path(root).absolute()
        if path.resolve()!=path:raise ValueError('new exact unlinked schedule root required')
        path.mkdir(exist_ok=False)
        self=cls.__new__(cls);self._initialize(path,source,session_seconds,clock)
        try:
            bound=dict(HARD_LIMITS)
            if limits is not None:
                if type(limits)is not dict or not set(limits)<=set(bound):raise ValueError('known schedule limits required')
                bound.update(limits)
            for name,value in bound.items():
                _int(value,name,1)
                if value>HARD_LIMITS[name]:raise ValueError('schedule limits may only tighten hard bounds')
            options={}if reader_options is None else copy.deepcopy(reader_options)
            dummy=dict(row_id='preflight',semantic_root_id='preflight',split=split,
                feature_file='preflight.npy',feature_sha256=producer.ZERO,teacher_tokens=1,
                positions=[dict(teacher_predictor_raw_index=0)])
            contract=window.FeatureWindow([dummy],root=path,identities=identities,split=split,**options).contract
            child_limits=dict(max_physical_bytes=272629760,max_files=4096,max_journal_bytes=3000000)
            if producer_limits is not None:
                if type(producer_limits)is not dict or not set(producer_limits)<=set(child_limits):raise ValueError('known producer limits required')
                child_limits.update(producer_limits)
            for name,value in child_limits.items():_int(value,name,4 if name=='max_files'else 1)
            source_contract=self._source_contract()
            self.recipe=dict(schema=SCHEMA,root=str(path),identities=copy.deepcopy(identities),split=split,
                reader_options=contract['options'],producer_limits=child_limits,limits=bound,
                source_contract=source_contract,source_contract_sha256=_sha(source_contract),
                implementation_sha256=producer.file_digest(Path(__file__)),
                producer_sha256=producer.file_digest(Path(producer.__file__)),
                reader_sha256=producer.file_digest(Path(window.__file__)),
                resume_scope=SCOPE,corpus_admitted=False)
            self.recipe['initial_source_state']=self._source_state()
            raw=producer.canonical(self.recipe)
            if len(raw)>65536 or len(raw)>bound['max_physical_bytes']or bound['max_files']<2:
                raise ValueError('schedule recipe/physical quota exceeded')
            with(path/'coordinator_recipe.json').open('xb')as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self._sync_root();self.recipe_sha256=producer.digest(raw)
            self._reset_history();self._inventory()
            return self
        except BaseException:self.close();raise

    @classmethod
    def resume(cls,root,*,source,recipe_sha256,expected_prefix=None,
               session_seconds=28800,clock=time.monotonic):
        path=Path(root).absolute()
        if not path.is_dir()or path.is_symlink()or path.resolve(strict=True)!=path:
            raise ValueError('existing exact unlinked schedule root required')
        self=cls.__new__(cls);self._initialize(path,source,session_seconds,clock)
        try:
            recipe_path=path/'coordinator_recipe.json';info=recipe_path.lstat()
            if not stat.S_ISREG(info.st_mode)or info.st_nlink!=1 or not 0<info.st_size<=65536:
                raise ValueError('bounded regular schedule recipe required')
            raw=recipe_path.read_bytes();self.recipe=json.loads(raw)
            if(not _hex(recipe_sha256)or producer.digest(raw)!=recipe_sha256
                    or producer.canonical(self.recipe)!=raw or self.recipe.get('schema')!=SCHEMA
                    or self.recipe.get('root')!=str(path)or self.recipe.get('resume_scope')!=SCOPE
                    or self.recipe.get('corpus_admitted')is not False
                    or self.recipe.get('implementation_sha256')!=producer.file_digest(Path(__file__))
                    or self.recipe.get('producer_sha256')!=producer.file_digest(Path(producer.__file__))
                    or self.recipe.get('reader_sha256')!=producer.file_digest(Path(window.__file__))
                    or self._source_contract()!=self.recipe.get('source_contract')):
                raise ValueError('schedule recipe/source/root/implementation identity differs')
            # A fresh adapter is required; do not silently rewind an active caller.
            if self._source_state()!=self.recipe['initial_source_state']:
                raise ValueError('schedule resume requires a fresh initial-state source adapter')
            self.recipe_sha256=recipe_sha256;self._reset_history()
            self._recover(expected_prefix)
            self._restore_source(self._last_state)
            return self
        except BaseException:self.close();raise

    def _initialize(self,path,source,seconds,clock):
        self.root=path;self.source=source;self._lock=self._active=None
        self._closed=self._failed=False;self.pause_reason=None
        if(type(seconds)not in(int,float)or not math.isfinite(seconds)or not 0<=seconds<=28800 or not callable(clock)):
            raise ValueError('bounded per-open acquisition seconds and monotonic clock required')
        self._clock=clock;self._session_seconds=float(seconds)
        self._began=self._last_clock=float(clock())
        if not math.isfinite(self._began):raise ValueError('finite monotonic clock required')
        descriptor=os.open(path/'coordinator.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        self._lock=os.fdopen(descriptor,'r+b')
        try:
            info=os.fstat(self._lock.fileno())
            if not stat.S_ISREG(info.st_mode)or info.st_nlink!=1:raise ValueError('regular unlinked schedule lock required')
            fcntl.flock(self._lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:self._lock.close();self._lock=None;raise

    def _source_contract(self):
        value=self.source.contract
        if type(value)is not dict or not value:raise ValueError('explicit declared source contract required')
        return _bounded(value,HARD_LIMITS['max_source_state_bytes'],'source contract')

    def _boundary(self,value):
        maximum=self.recipe['limits']['max_source_state_bytes']
        value=_bounded(value,maximum,'source boundary')
        fields={'schema','source_contract_sha256','next_record','source_cursor','rng_state'}
        if(type(value)is not dict or set(value)!=fields or value['schema']!=SOURCE_SCHEMA
                or value['source_contract_sha256']!=self.recipe['source_contract_sha256']
                or type(value['source_cursor'])is not dict or type(value['rng_state'])is not dict):
            raise ValueError('exact declared source boundary schema/identity required')
        _int(value['next_record'],'next_record')
        return value

    def _source_state(self):
        if self._source_contract()!=self.recipe['source_contract']:raise ValueError('source contract changed')
        return self._boundary(self.source.state_dict())

    def _restore_source(self,state):
        state=self._boundary(state);self.source.load_state_dict(copy.deepcopy(state))
        if self._source_state()!=state:raise ValueError('source adapter did not restore exact declared cursor/RNG')

    def _reset_history(self):
        self._windows=[];self._head=self.recipe_sha256;self._sequence=0;self._finished=False
        self._journal_bytes=0
        self._last_state=self._boundary(self.recipe['initial_source_state'])
        self._record_count=self._feature_rows=self._positions=0;self._row_ids=set()
        self.partial_tails=[];self.orphan_windows=[];self._heads={}
        self._remember_head()

    def _remember_head(self):
        self._heads[self._head]=dict(windows=[w['name']for w in self._windows],
            closed=[w['closed']for w in self._windows],finished=self._finished)

    def _sync_root(self):
        descriptor=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)

    def _inventory(self):
        total=files=0;directories=[];events=[];limits=self.recipe['limits']
        lower_pattern=re.compile(r'(?:feature_[0-9a-f]{32}\.npy|journal_[0-9a-f]{32}\.jsonl)')
        def regular(path):
            nonlocal total,files
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode)or info.st_nlink!=1:raise ValueError('schedule linked/nonregular file refused')
            total+=info.st_size;files+=1
            if total>limits['max_physical_bytes']or files>limits['max_files']:raise ValueError('schedule physical byte/file quota exceeded')
        for path in self.root.iterdir():
            info=path.lstat()
            if path.name in('coordinator_recipe.json','coordinator.lock')or EVENT_NAME.fullmatch(path.name):
                regular(path)
                if EVENT_NAME.fullmatch(path.name):events.append(path.name)
            elif WINDOW_NAME.fullmatch(path.name)and stat.S_ISDIR(info.st_mode)and not path.is_symlink():
                directories.append(path.name)
                if len(directories)>limits['max_windows']:raise ValueError('schedule physical window quota exceeded')
                for child in path.iterdir():
                    if child.name not in('recipe.json','writer.lock')and not lower_pattern.fullmatch(child.name):
                        raise ValueError('unexpected file in owned feature window')
                    regular(child)
            else:raise ValueError('unexpected/linked schedule root entry')
        self._physical_bytes,self._file_count=total,files
        self._directory_names=directories
        return events

    def _capacity(self,byte_count,file_count):
        self._inventory();limits=self.recipe['limits']
        if self._physical_bytes+byte_count>limits['max_physical_bytes']or self._file_count+file_count>limits['max_files']:
            raise ValueError('schedule physical quota before write')

    def _event(self,kind,**extra):
        value=dict(schema=EVENT_SCHEMA,recipe_sha256=self.recipe_sha256,sequence=self._sequence,
            previous_sha256=self._head,kind=kind,**extra)
        value['event_sha256']=_sha(value)
        return value

    def _publish_event(self,event):
        raw=producer.canonical(event)
        if len(raw)>self.recipe['limits']['max_event_bytes']:raise ValueError('schedule global event byte quota exceeded')
        self._capacity(len(raw),1)
        if self._journal_bytes+len(raw)>self.recipe['limits']['max_journal_metadata_bytes']:
            raise ValueError('schedule global journal metadata quota exceeded')
        path=self.root/('event_'+uuid.uuid4().hex+'.jsonl')
        with path.open('xb')as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        self._sync_root();self._journal_bytes+=len(raw)

    def _apply_event(self,event):
        base={'schema','recipe_sha256','sequence','previous_sha256','kind','event_sha256'}
        if (not isinstance(event,dict)or event.get('schema')!=EVENT_SCHEMA
                or event.get('recipe_sha256')!=self.recipe_sha256 or type(event.get('sequence'))is not int
                or event['sequence']!=self._sequence or event.get('previous_sha256')!=self._head
                or event.get('event_sha256')!=_sha({k:v for k,v in event.items()if k!='event_sha256'})or self._finished):
            raise ValueError('schedule complete event/schema/sequence/chain differs')
        kind=event['kind']
        if kind=='open'and set(event)==base|{'window_name','window_index','window_recipe_sha256','source_start_sha256'}:
            if(self._windows and not self._windows[-1]['closed']or type(event['window_index'])is not int
                    or event['window_index']!=len(self._windows)or not WINDOW_NAME.fullmatch(event['window_name'])
                    or any(w['name']==event['window_name']for w in self._windows)
                    or not _hex(event['window_recipe_sha256'])or not _hex(event['source_start_sha256'])):
                raise ValueError('schedule ordered window open differs')
            self._windows.append(dict(name=event['window_name'],recipe_sha256=event['window_recipe_sha256'],
                start_sha256=event['source_start_sha256'],closed=False,records=[],cursor=None,
                closed_cursor=None,window_sha256=None))
        elif kind=='close'and set(event)==base|{'window_name','producer_cursor','window_sha256'}:
            if(not self._windows or self._windows[-1]['closed']or self._windows[-1]['name']!=event['window_name']
                    or not _hex(event['window_sha256'])):raise ValueError('schedule ordered window close differs')
            self._windows[-1].update(closed=True,closed_cursor=_copy(event['producer_cursor']),window_sha256=event['window_sha256'])
        elif kind=='done'and set(event)==base|{'source_state_sha256'}:
            if(any(not w['closed']for w in self._windows)or not _hex(event['source_state_sha256'])):
                raise ValueError('schedule complete source boundary differs')
            self._finished=True;self._done_state_sha=event['source_state_sha256']
        else:raise ValueError('schedule exact event kind/fields required')
        self._head=event['event_sha256'];self._sequence+=1;self._remember_head()

    def _commit_event(self,kind,**extra):
        event=self._event(kind,**extra);self._publish_event(event);self._apply_event(event)

    def _child_recipe(self,name):
        return dict(schema=producer.SCHEMA,root=str(self.root/name),identities=self.recipe['identities'],
            split=self.recipe['split'],reader_options=self.recipe['reader_options'],limits=self.recipe['producer_limits'],
            reader_sha256=self.recipe['reader_sha256'],producer_sha256=self.recipe['producer_sha256'],
            source_scope=producer.SCOPE,corpus_admitted=False)

    def _accept_record(self,record):
        transition=record.get(TRANSITION)
        if(type(transition)is not dict or set(transition)!={'schema','sequence','before','after'}
                or transition['schema']!=TRANSITION_SCHEMA or type(transition['sequence'])is not int
                or transition['sequence']!=self._record_count):raise ValueError('schedule exact source transition required')
        before=self._boundary(transition['before']);after=self._boundary(transition['after'])
        if before!=self._last_state or after['next_record']!=before['next_record']+1:
            raise ValueError('schedule source cursor/RNG transition chain differs')
        ident=record['row_id']
        if ident in self._row_ids:raise ValueError('schedule duplicate committed row ID across windows')
        self._row_ids.add(ident);self._record_count+=1;self._feature_rows+=record['teacher_tokens']
        self._positions+=len(record['positions']);self._last_state=after
        limits=self.recipe['limits']
        if(self._record_count>limits['max_records']or self._feature_rows>limits['max_feature_rows']
                or self._positions>limits['max_selected_positions']):raise ValueError('schedule committed logical quota exceeded')

    def _recover(self,expected_prefix):
        names=self._inventory();events={};self._journal_bytes=0
        if expected_prefix is not None:self._validate_prefix_schema(expected_prefix)
        for name in names:
            path=self.root/name;size=path.stat().st_size
            if size>self.recipe['limits']['max_event_bytes']:raise ValueError('schedule event file quota exceeded')
            self._journal_bytes+=size
            if self._journal_bytes>self.recipe['limits']['max_journal_metadata_bytes']:raise ValueError('schedule journal quota exceeded')
            raw=path.read_bytes()
            if not raw.endswith(b'\n'):
                self.partial_tails.append(dict(file=name,bytes=len(raw),sha256=producer.digest(raw)));continue
            event=json.loads(raw)
            if(not isinstance(event,dict)or producer.canonical(event)!=raw or type(event.get('sequence'))is not int
                    or event['sequence']in events):raise ValueError('schedule complete event canonical form/sequence differs')
            events[event['sequence']]=event
        for sequence in sorted(events):self._apply_event(events[sequence])
        linked={w['name']for w in self._windows}
        self.orphan_windows=sorted(name for name in self._directory_names if name not in linked)
        expected_windows={}if expected_prefix is None else{w['name']:w['producer_cursor']for w in expected_prefix['windows']}
        for entry in self._windows:
            if entry['start_sha256']!=_sha(self._last_state):raise ValueError('schedule window source-start boundary differs')
            child=producer.FeatureProducer.resume(self.root/entry['name'],recipe_sha256=entry['recipe_sha256'],
                expected_prefix=expected_windows.get(entry['name']))
            try:
                if child.recipe!=self._child_recipe(entry['name']):raise ValueError('schedule lower recipe/options differ')
                cursor=child.checkpoint();records=child.records()
                for record in records:self._accept_record(record)
                entry.update(cursor=cursor,records=records)
                if entry['closed']:
                    if not cursor['sealed']or not records or cursor!=entry['closed_cursor']or child.reader().window_sha256!=entry['window_sha256']:
                        raise ValueError('schedule closed window differs from durable lower commit')
                    child.close()
                else:self._active=child
            except BaseException:child.close();raise
        if self._finished and self._done_state_sha!=_sha(self._last_state):raise ValueError('schedule final source-state hash differs')
        if expected_prefix is not None:self._verify_prefix(expected_prefix)
        # Lower sealing can commit before the caller publishes its global close.
        if self._active is not None and self._active.checkpoint()['sealed']:
            self._finish_window_close()

    def _validate_prefix_schema(self,value):
        fields={'schema','recipe_sha256','global_head_sha256','windows','source_state','committed_records',
            'teacher_feature_rows','selected_positions','finished','resume_scope','corpus_admitted','state_sha256'}
        if(type(value)is not dict or set(value)!=fields or value['schema']!=STATE_SCHEMA
                or value['recipe_sha256']!=self.recipe_sha256 or value['resume_scope']!=SCOPE
                or value['corpus_admitted']is not False or type(value['finished'])is not bool
                or value['state_sha256']!=_sha({k:v for k,v in value.items()if k!='state_sha256'})
                or type(value['windows'])is not list or len(value['windows'])>self.recipe['limits']['max_windows']):
            raise ValueError('schedule exact committed prefix schema/checksum required')
        for key in('committed_records','teacher_feature_rows','selected_positions'):_int(value[key],key)
        self._boundary(value['source_state'])
        for entry in value['windows']:
            if(type(entry)is not dict or set(entry)!={'name','producer_cursor'}or type(entry['name'])is not str
                    or not WINDOW_NAME.fullmatch(entry['name'])or type(entry['producer_cursor'])is not dict):
                raise ValueError('schedule exact window prefix required')

    def _verify_prefix(self,value):
        head=self._heads.get(value['global_head_sha256'])
        if(head is None or head['windows']!=[w['name']for w in value['windows']]or head['finished']!=value['finished']):
            raise ValueError('schedule supplied global prefix is absent')
        rows=[]
        for i,(expected,actual)in enumerate(zip(value['windows'],self._windows)):
            cursor=expected['producer_cursor'];count=cursor.get('committed_records')
            _int(count,'prefix committed records')
            if cursor.get('sealed')is not head['closed'][i]or count>len(actual['records']):raise ValueError('schedule prefix window phase differs')
            rows.extend(actual['records'][:count])
        state=self.recipe['initial_source_state']if not rows else rows[-1][TRANSITION]['after']
        if(value['source_state']!=state or value['committed_records']!=len(rows)
                or value['teacher_feature_rows']!=sum(r['teacher_tokens']for r in rows)
                or value['selected_positions']!=sum(len(r['positions'])for r in rows)):
            raise ValueError('schedule prefix source/counters differ')

    def _healthy(self):
        if self._closed or self._failed:raise RuntimeError('schedule closed/failed; reopen durable records')

    def _now(self):
        value=float(self._clock())
        if not math.isfinite(value)or value<self._last_clock:raise ValueError('monotonic acquisition clock moved backward')
        self._last_clock=value;return value

    def _pause(self,reason,before=None):
        if before is not None:self._restore_source(before)
        self.pause_reason=reason
        return dict(status='PAUSED',reason=reason,checkpoint=self.checkpoint())

    def _preview(self,row):
        value=copy.deepcopy(row);value.update(feature_file='feature_'+('0'*32)+'.npy',
            feature_sha256=producer.ZERO,feature_payload_sha256=producer.ZERO)
        return value

    def _reader(self,records,root=None):
        return window.FeatureWindow(records,root=self.root if root is None else root,
            identities=self.recipe['identities'],split=self.recipe['split'],**self.recipe['reader_options'])

    def _record_cost(self,row,array):
        # These are conservative prewrite bounds, not observed file/RSS sizes.
        return array.nbytes+window.HEADER_CAP+12+len(producer.canonical(self._preview(row)))+2048

    def _new_window(self):
        self._inventory()
        if len(self._directory_names)>=self.recipe['limits']['max_windows']:raise ValueError('schedule physical window quota before create')
        name='window_'+uuid.uuid4().hex
        child=producer.FeatureProducer.create(self.root/name,identities=self.recipe['identities'],split=self.recipe['split'],
            reader_options=self.recipe['reader_options'],**self.recipe['producer_limits'])
        self._active=child
        self._commit_event('open',window_name=name,window_index=len(self._windows),
            window_recipe_sha256=child.recipe_sha256,source_start_sha256=_sha(self._last_state))
        self._windows[-1]['cursor']=child.checkpoint()

    def _finish_window_close(self):
        cursor=self._active.checkpoint()
        if not cursor['sealed']:raise RuntimeError('complete lower seal required')
        self._commit_event('close',window_name=self._windows[-1]['name'],producer_cursor=cursor,
            window_sha256=self._active.reader().window_sha256)
        self._windows[-1]['cursor']=cursor;self._active.close();self._active=None

    def seal_window(self):
        self._healthy()
        if self._active is None:return
        try:
            if not self._active.checkpoint()['committed_records']:raise ValueError('empty active window cannot be sealed')
            self._active.seal();self._finish_window_close()
        except BaseException:self._failed=True;raise

    def advance(self):
        self._healthy()
        try:
            if self._finished:return dict(status='COMPLETE',checkpoint=self.checkpoint())
            if self.pause_reason:return dict(status='PAUSED',reason=self.pause_reason,checkpoint=self.checkpoint())
            limits=self.recipe['limits']
            if self._now()-self._began>=self._session_seconds:return self._pause('SESSION_PREFETCH_DEADLINE')
            if(self._record_count>=limits['max_records']or self._feature_rows>=limits['max_feature_rows']
                    or self._positions>=limits['max_selected_positions']):return self._pause('LOGICAL_FEATURE_BUDGET')
            before=self._source_state()
            if before!=self._last_state:raise ValueError('source advanced outside the committed schedule')
            try:item=self.source.next_feature()
            except StopIteration:
                if self._source_state()!=before:raise ValueError('source exhaustion changed cursor/RNG')
                self.seal_window();self._commit_event('done',source_state_sha256=_sha(before))
                return dict(status='COMPLETE',checkpoint=self.checkpoint())
            if type(item)not in(tuple,list)or len(item)!=2:raise ValueError('source returns one metadata/array pair')
            metadata,array=item;after=self._source_state()
            if after['next_record']!=before['next_record']+1:raise ValueError('source next_record must advance by one')
            if(type(metadata)is not dict or TRANSITION in metadata
                    or {'feature_file','feature_sha256','feature_payload_sha256'}&metadata.keys()):
                raise ValueError('original metadata without reserved producer/schedule fields required')
            row=copy.deepcopy(metadata)
            row[TRANSITION]=dict(schema=TRANSITION_SCHEMA,sequence=self._record_count,before=before,after=after)
            self._reader([self._preview(row)])
            if(not isinstance(array,np.ndarray)or array.dtype!=np.float32 or not array.flags.c_contiguous
                    or array.shape!=(row['teacher_tokens'],self.recipe['reader_options']['hidden_width'])
                    or not bool(np.isfinite(array).all())or not row['positions']):
                raise ValueError('source must return original finite C-order FP32 and a nonempty selection')
            if row['row_id']in self._row_ids:raise ValueError('schedule duplicate source row ID')
            if(self._feature_rows+row['teacher_tokens']>limits['max_feature_rows']
                    or self._positions+len(row['positions'])>limits['max_selected_positions']):
                return self._pause('NEXT_RECORD_FEATURE_BUDGET',before)
            preview=self._preview(row);cost=self._record_cost(row,array)
            child_limits=self.recipe['producer_limits']
            hypothetical=self._child_recipe('window_'+('0'*32))
            if(cost+len(producer.canonical(hypothetical))+2048>child_limits['max_physical_bytes']or child_limits['max_files']<5):
                raise ValueError('source record cannot fit a fresh window with closure reserve')
            if len(producer.canonical(preview))+1024>child_limits['max_journal_bytes']:
                raise ValueError('source record cannot fit lower journal event bound')
            rotate=self._active is None
            if self._active is not None:
                try:
                    self._reader(self._active.records()+[preview],root=self._active.root)
                    self._active._capacity(cost+2048,3)
                except ValueError:rotate=True
            self._inventory()
            if rotate and len(self._directory_names)>=limits['max_windows']:
                return self._pause('PHYSICAL_WINDOW_COUNT_BUDGET',before)
            extra=(len(producer.canonical(hypothetical))+8192)if rotate else 4096
            if self._journal_bytes+(6144 if rotate else 4096)>limits['max_journal_metadata_bytes']:
                return self._pause('GLOBAL_JOURNAL_CLOSURE_RESERVE',before)
            try:self._capacity(cost+extra,8 if rotate else 4)
            except ValueError as exc:
                if str(exc)=='schedule physical quota before write':return self._pause('PHYSICAL_BYTE_OR_FILE_BUDGET',before)
                raise
            if rotate:
                self.seal_window();self._new_window()
            cursor=self._active.append(row,array)
            record=self._active.records()[-1];self._accept_record(record)
            self._windows[-1]['records'].append(record);self._windows[-1]['cursor']=cursor
            return dict(status='COMMITTED',row_id=row['row_id'],checkpoint=self.checkpoint())
        except BaseException:self._failed=True;raise

    def checkpoint(self):
        self._healthy()
        value=dict(schema=STATE_SCHEMA,recipe_sha256=self.recipe_sha256,global_head_sha256=self._head,
            windows=[dict(name=w['name'],producer_cursor=copy.deepcopy(w['cursor']))for w in self._windows],
            source_state=copy.deepcopy(self._last_state),committed_records=self._record_count,
            teacher_feature_rows=self._feature_rows,selected_positions=self._positions,
            finished=self._finished,resume_scope=SCOPE,corpus_admitted=False)
        value['state_sha256']=_sha(value)
        return value

    def sealed_readers(self):
        self._healthy()
        return tuple(self._reader(w['records'],root=self.root/w['name'])for w in self._windows if w['closed'])

    def close(self):
        if self._active is not None:self._active.close();self._active=None
        if self._lock is not None:
            fcntl.flock(self._lock.fileno(),fcntl.LOCK_UN);self._lock.close();self._lock=None
        self._closed=True

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
