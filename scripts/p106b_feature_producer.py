"""Linux, single-window, append-only feature production; no model is loaded.

Every event uses a new file. Complete canonical newline events are committed;
partial final bytes and unreferenced payloads remain immutable orphan evidence.
Source checkpoints do not restore a model, source iterator, RNG or optimizer.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

import numpy as np

from scripts import p106b_feature_window as window

SCHEMA='P106B_FEATURE_PRODUCER_RECIPE_V1'
EVENT_SCHEMA='P106B_FEATURE_PRODUCER_EVENT_V1'
SCOPE='SINGLE_WINDOW_SOURCE_ACCOUNTING_NOT_MODEL_ITERATOR_RNG_OR_OPTIMIZER'
ZERO='0'*64


def canonical(value):return (window._canonical(value)+chr(10)).encode('utf-8')
def digest(raw):return hashlib.sha256(raw).hexdigest().upper()
def file_digest(path):
    result=hashlib.sha256()
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):result.update(block)
    return result.hexdigest().upper()


class FeatureProducer:
    """Own one new flat root, bounded metadata/payload and a persistent flock.

    Caller-owned input arrays must stay immutable during append. Each producer
    record has at least one selected position. Sealed windows can be read by
    FeatureWindow; multi-window scheduling and corpus admission are not supplied.
    No file is deleted, renamed, overwritten or appended after it is closed.
    """
    @classmethod
    def create(cls,root,*,identities,split,reader_options=None,
               max_physical_bytes=272629760,max_files=4096,max_journal_bytes=3000000):
        path=Path(root).absolute()
        if path.resolve()!=path:raise ValueError('feature producer exact unlinked new root required')
        path.mkdir(exist_ok=False)
        self=cls.__new__(cls)
        self._initialize(path)
        try:
            options={}if reader_options is None else copy.deepcopy(reader_options)
            limits=dict(max_physical_bytes=max_physical_bytes,max_files=max_files,max_journal_bytes=max_journal_bytes)
            for name,value in limits.items():window._integer(value,name,4 if name=='max_files'else 1)
            dummy=dict(row_id='preflight',semantic_root_id='preflight',split=split,
                feature_file='preflight.npy',feature_sha256=ZERO,teacher_tokens=1,
                positions=[dict(teacher_predictor_raw_index=0)])
            contract=window.FeatureWindow([dummy],root=path,identities=identities,split=split,**options).contract
            self.recipe=dict(schema=SCHEMA,root=str(path),identities=copy.deepcopy(identities),split=split,
                reader_options=contract['options'],limits=limits,
                reader_sha256=file_digest(Path(window.__file__)),producer_sha256=file_digest(Path(__file__)),
                source_scope=SCOPE,corpus_admitted=False)
            raw=canonical(self.recipe)
            if len(raw)>65536 or len(raw)>max_physical_bytes:
                raise ValueError('feature producer recipe/physical quota exceeded')
            with(path/'recipe.json').open('xb')as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self.recipe_sha256=digest(raw)
            self._head=self.recipe_sha256
            self._physical_bytes=len(raw);self._file_count=2
            self._sync_root()
            return self
        except BaseException:
            self.close();raise

    @classmethod
    def resume(cls,root,*,recipe_sha256,expected_prefix=None):
        path=Path(root).absolute()
        if not path.is_dir()or path.is_symlink()or path.resolve(strict=True)!=path:
            raise ValueError('feature producer existing exact unlinked root required')
        self=cls.__new__(cls)
        self._initialize(path)
        try:
            recipe_path=path/'recipe.json'
            info=recipe_path.lstat()
            if not stat.S_ISREG(info.st_mode)or info.st_nlink!=1 or not 0<info.st_size<=65536:
                raise ValueError('feature producer bounded regular recipe required')
            raw=recipe_path.read_bytes()
            if digest(raw)!=recipe_sha256:raise ValueError('feature producer recipe SHA differs')
            self.recipe=json.loads(raw)
            if (self.recipe.get('schema')!=SCHEMA or self.recipe.get('root')!=str(path)
                    or canonical(self.recipe)!=raw or self.recipe.get('source_scope')!=SCOPE
                    or self.recipe.get('reader_sha256')!=file_digest(Path(window.__file__))
                    or self.recipe.get('producer_sha256')!=file_digest(Path(__file__))):
                raise ValueError('feature producer recipe/source/root identity differs')
            self.recipe_sha256=recipe_sha256
            self._head=recipe_sha256
            self._recover(expected_prefix)
            return self
        except BaseException:
            self.close();raise

    def _initialize(self,path):
        self.root=path
        self._lock=None;self._closed=self._failed=self._sealed=False
        self._records=[];self._sequence=0;self._head=None
        self._physical_bytes=self._file_count=0
        self.partial_tails=[];self.orphan_features=[]
        descriptor=os.open(path/'writer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        self._lock=os.fdopen(descriptor,'r+b')
        try:
            info=os.fstat(self._lock.fileno())
            if not stat.S_ISREG(info.st_mode)or info.st_nlink!=1:
                raise ValueError('feature producer regular unlinked lock file required')
            fcntl.flock(self._lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:self._lock.close();self._lock=None;raise

    def _sync_root(self):
        descriptor=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)

    def _reader(self,records=None):
        return window.FeatureWindow(self._records if records is None else records,root=self.root,
            identities=self.recipe['identities'],split=self.recipe['split'],**self.recipe['reader_options'])

    def _inventory(self):
        names=[];size=0
        for path in self.root.iterdir():
            names.append(path.name)
            if len(names)>self.recipe['limits']['max_files']:
                raise ValueError('feature producer physical file quota exceeded')
            allowed=(path.name in('recipe.json','writer.lock')
                or re.fullmatch(r'feature_[0-9a-f]{32}\.npy',path.name)
                or re.fullmatch(r'journal_[0-9a-f]{32}\.jsonl',path.name))
            info=path.lstat()
            if not allowed or not stat.S_ISREG(info.st_mode)or info.st_nlink!=1:
                raise ValueError('feature producer unexpected/linked/nonregular root file')
            size+=info.st_size
        if size>self.recipe['limits']['max_physical_bytes']:
            raise ValueError('feature producer physical byte quota exceeded')
        self._physical_bytes,self._file_count=size,len(names)
        return names

    def _verify_record(self,record):
        reader=self._reader([record])
        value=reader._read_feature(record)
        if digest(memoryview(value).cast('B'))!=record.get('feature_payload_sha256'):
            raise ValueError('feature producer original payload bytes differ')

    def _recover(self,expected_prefix):
        names=self._inventory();events={};prefixes={self._head:self.checkpoint()}
        metadata_bytes=0
        for name in sorted(n for n in names if n.startswith('journal_')):
            path=self.root/name
            if path.stat().st_size>self.recipe['limits']['max_journal_bytes']:
                raise ValueError('feature producer journal segment quota exceeded')
            for number,line in enumerate(path.read_bytes().splitlines(keepends=True),1):
                if not line.endswith(bytes([10])):
                    self.partial_tails.append(dict(file=name,line=number,bytes=len(line),sha256=digest(line)))
                    continue
                event=json.loads(line)
                if (not isinstance(event,dict)or canonical(event)!=line
                        or event.get('schema')!=EVENT_SCHEMA or event.get('recipe_sha256')!=self.recipe_sha256
                        or type(event.get('sequence'))is not int or event['sequence']<0
                        or event['sequence']in events):
                    raise ValueError('feature producer complete event/schema/sequence differs')
                checksum=event.get('event_sha256')
                if checksum!=window._sha({k:v for k,v in event.items()if k!='event_sha256'}):
                    raise ValueError('feature producer complete event checksum differs')
                metadata_bytes+=len(line)
                if metadata_bytes>self.recipe['reader_options']['max_metadata_bytes']+1048576:
                    raise ValueError('feature producer aggregate journal metadata quota exceeded')
                events[event['sequence']]=event
                if len(events)>self.recipe['reader_options']['max_records']+1:
                    raise ValueError('feature producer committed event count quota exceeded')
        for sequence in sorted(events):
            event=events[sequence]
            if sequence!=self._sequence or event.get('previous_sha256')!=self._head or self._sealed:
                raise ValueError('feature producer complete event chain differs')
            base={'schema','recipe_sha256','sequence','previous_sha256','kind','event_sha256'}
            if event['kind']=='record'and set(event)==base|{'record'}:
                records=self._records+[event['record']]
                self._reader(records)
                self._verify_record(event['record'])
                self._records=records
            elif event['kind']=='seal'and set(event)==base|{'window_sha256'}:
                if self._reader().window_sha256!=event['window_sha256']:
                    raise ValueError('feature producer sealed window identity differs')
                self._sealed=True
            else:raise ValueError('feature producer exact event kind/schema required')
            self._sequence+=1;self._head=event['event_sha256'];prefixes[self._head]=self.checkpoint()
        used={record['feature_file']for record in self._records}
        self.orphan_features=sorted(name for name in names if name.startswith('feature_')and name not in used)
        if expected_prefix is not None:
            if (not isinstance(expected_prefix,dict)or expected_prefix.get('recipe_sha256')!=self.recipe_sha256
                    or expected_prefix.get('source_scope')!=SCOPE
                    or not isinstance(expected_prefix.get('head_sha256'),str)
                    or expected_prefix['head_sha256']not in prefixes
                    or canonical(prefixes[expected_prefix['head_sha256']])!=canonical(expected_prefix)):
                raise ValueError('feature producer supplied source prefix is absent or changed')

    def _capacity(self,byte_count,file_count):
        limits=self.recipe['limits']
        if self._physical_bytes+byte_count>limits['max_physical_bytes']or self._file_count+file_count>limits['max_files']:
            raise ValueError('feature producer physical byte/file quota before write')

    def _event(self,kind,**extra):
        value=dict(schema=EVENT_SCHEMA,recipe_sha256=self.recipe_sha256,sequence=self._sequence,
            previous_sha256=self._head,kind=kind,**extra)
        value['event_sha256']=window._sha(value)
        return value

    def _publish(self,event):
        line=canonical(event)
        if len(line)>self.recipe['limits']['max_journal_bytes']:
            raise ValueError('feature producer one event exceeds journal quota')
        self._capacity(len(line),1)
        path=self.root/('journal_'+uuid.uuid4().hex+'.jsonl')
        with path.open('xb')as stream:
            stream.write(line);stream.flush();os.fsync(stream.fileno())
        self._sync_root()
        self._physical_bytes+=len(line);self._file_count+=1
        self._sequence+=1;self._head=event['event_sha256']

    def _active(self):
        if self._closed or self._failed or self._sealed:
            raise RuntimeError('feature producer closed/failed/sealed; reopen source or create another window')

    def append(self,metadata,array):
        self._active()
        try:
            if not isinstance(metadata,dict)or {'feature_file','feature_sha256','feature_payload_sha256'}&metadata.keys():
                raise ValueError('feature producer original metadata without reserved file fields required')
            row=copy.deepcopy(metadata)
            if (not isinstance(array,np.ndarray)or array.dtype!=np.float32 or not array.flags.c_contiguous
                    or array.shape!=(row.get('teacher_tokens'),self.recipe['reader_options']['hidden_width'])
                    or not bool(np.isfinite(array).all())or not row.get('positions')):
                raise ValueError('feature producer original finite C-order FP32 and nonempty selection required')
            filename='feature_'+uuid.uuid4().hex+'.npy'
            payload_sha=digest(memoryview(array).cast('B'))
            row.update(feature_file=filename,feature_sha256=ZERO,feature_payload_sha256=payload_sha)
            self._reader(self._records+[row])
            preview=canonical(self._event('record',record=row))
            if len(preview)>self.recipe['limits']['max_journal_bytes']:
                raise ValueError('feature producer event/metadata quota before payload write')
            self._capacity(array.nbytes+window.HEADER_CAP+12+len(preview),2)
            path=self.root/filename
            with path.open('xb')as stream:
                np.save(stream,array,allow_pickle=False);stream.flush();os.fsync(stream.fileno())
            row['feature_sha256']=file_digest(path)
            self._verify_record(row)
            self._physical_bytes+=path.stat().st_size;self._file_count+=1
            self._publish(self._event('record',record=row))
            self._records.append(row)
            return self.checkpoint()
        except BaseException:
            self._failed=True;raise

    def checkpoint(self):
        if self._closed or self._failed:
            raise RuntimeError('feature producer healthy open source required')
        return dict(schema='P106B_FEATURE_PRODUCER_CURSOR_V1',recipe_sha256=self.recipe_sha256,
            head_sha256=self._head,committed_records=len(self._records),sealed=self._sealed,
            teacher_feature_rows=sum(r['teacher_tokens']for r in self._records),
            selected_positions=sum(len(r['positions'])for r in self._records),
            source_scope=SCOPE,corpus_admitted=False)

    def seal(self):
        self._active()
        try:
            reader=self._reader()
            self._publish(self._event('seal',window_sha256=reader.window_sha256))
            self._sealed=True
            return self.checkpoint()
        except BaseException:
            self._failed=True;raise

    def reader(self):
        if self._closed or self._failed or not self._sealed:
            raise RuntimeError('feature producer healthy sealed source required for reader export')
        return self._reader()

    def records(self):return copy.deepcopy(self._records)

    def close(self):
        if self._lock is not None:
            fcntl.flock(self._lock.fileno(),fcntl.LOCK_UN)
            self._lock.close();self._lock=None
        self._closed=True

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
