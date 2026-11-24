"""Pair edited eager and native-unpack packed CPU jobs using the real sampler."""

import argparse
from contextlib import contextmanager, ExitStack
import ctypes
from datetime import datetime, timedelta
import fcntl
import gc
from importlib import import_module
import json
import os
from pathlib import Path
import resource
from statistics import median
import subprocess
import sys
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_cpu_unpack_speed as unpack
from scripts.diag_p106b_resource_matrix import model_storage
from tinylm.data.prepare import load_tokenizer, tokenizer_path


origin = unpack.origin
packed = origin.packed
sample_module = import_module('tinylm.infer.generate')
TAG = 'p108_g4_cpu_request_v2_20261119'
OUT = unpack.OUT.with_name(TAG)
TOK = origin.ROOT / 'data_cache/tok-ko-en-32768.json'
TOK_SHA = '3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3'
ORDER = ('eager','packed','packed','eager')
GEN, NATURAL, REPEATS = 8, 12, 2
# Linux UAPI, confirmed with the current WSL kernel. The Torch Python omits these names.
F_ADD_SEALS, F_GET_SEALS, SEALS = 1033, 1034, 15
MFD_CLOEXEC, MFD_ALLOW_SEALING = 1, 2
TEXT = (
    ('en_capital','The capital of Finland is'),
    ('en_triangle','A triangle has this many sides:'),
    ('ko_word','고양이는 영어로 무엇인가?\n답:'),
    ('ko_division','12를 4로 나누면 얼마인가?\n답:'),
)
SOURCES = (*unpack.SOURCES, 'scripts/diag_p108_g4_cpu_request.py','scripts/diag_p106b_resource_matrix.py',
           'tinylm/data/prepare.py')


class PreparedPrompt:
    def __init__(self, ids, tokenizer):
        self.ids, self.tokenizer = ids, tokenizer

    def encode(self, _):
        return SimpleNamespace(ids=self.ids)

    def decode(self, ids):
        return self.tokenizer.decode(ids)


def write(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        print(file=stream)


def snapshot():
    values = {}
    for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
        key, _, rest = line.partition(':')
        if key in ('Rss','Pss','Private_Clean','Private_Dirty'):
            amount, unit = rest.split()
            assert unit=='kB'
            values[key] = int(amount)*1024
    return dict(rss=values['Rss'],pss=values['Pss'],
                private=values['Private_Clean']+values['Private_Dirty'])


def contract():
    refs = (unpack.OUT/'report.json',unpack.long_cache.OUT/'report.json',origin.PARENT,TOK)
    latest = unpack.read(refs[0])
    assert latest['library_closed'] and not latest['full_weight_cache']
    assert latest['parent_sha']==origin.PARENT_SHA==origin.digest(origin.PARENT)
    assert tokenizer_path('ko-en',32768)==TOK and origin.digest(TOK)==TOK_SHA
    assert all(origin.digest(origin.ROOT/name)==v for name,v in latest['source_pins'].items())
    return dict(tag=TAG,refs={str(p.relative_to(origin.ROOT)):origin.digest(p) for p in refs},
        sources={name:origin.digest(origin.ROOT/name) for name in SOURCES},worker_order=list(ORDER),text=[list(x) for x in TEXT],
        context=list(unpack.long_cache.CONTEXTS),generated=GEN,text_cap=NATURAL,repeats=REPEATS,approval='WIP176')


@contextmanager
def edited_eager():
    previous = unpack.read(unpack.long_cache.OUT/'report.json')
    model, step = origin.load_model()
    owner = origin.physical_down_owners(model)[2]
    cache = owner.module._wq
    before = origin.tensor_sha(cache)
    packet,_ = origin.edit_packet(cache,model.cfg.micro_group)
    assert packet['target_sha256']==previous['packet_target']
    with origin.apply_shared_down_packets(model,{2:packet},realization='codes') as change:
        assert change[0]['changed_trits']==2
        yield model,step,packet['target_sha256']
    assert owner.module._wq is cache and origin.tensor_sha(cache)==before


@torch.no_grad()
def export(fd):
    with edited_eager() as (model,step,packet):
        payload = packed.export_payload(model,provenance=dict(tag=TAG,parent_sha=origin.PARENT_SHA,step=step,packet=packet))
        with os.fdopen(os.dup(fd),'wb') as handle:
            torch.save(payload,handle)
    write(OUT/'archive.json',dict(storage=packed.payload_storage(payload),parent_step=step,packet=packet,
        serialized_bytes=os.fstat(fd).st_size))


@contextmanager
def native_unpack(model):
    runtime,spec = unpack.native_runtime()
    modules = [m for m in model.modules() if isinstance(m,packed.PackedGroupLinear)]
    assert modules and all(m.packed_codes.device.type=='cpu' and m.tile_rows==128 for m in modules)
    methods = [m.unpack_rows.__func__ for m in modules]
    indices = torch.arange(max(m.out_f for m in modules))
    counts = dict(lookup_calls=0,physical_matrices=len(modules),index_bytes=indices.numel()*indices.element_size(),
                  library=spec)
    try:
        with ExitStack() as stack:
            for m in modules:
                def rows(start,stop,*,module=m):
                    if not 0<=start<stop<=module.out_f or stop-start>module.tile_rows:
                        raise ValueError('bounded CPU packed tile required')
                    counts['lookup_calls']+=1
                    return runtime.lookup(module,indices[start:stop])
                stack.enter_context(patch.object(m,'unpack_rows',rows))
            yield counts
    finally:
        runtime.close()
        counts['restored']=all(m.unpack_rows.__func__ is old for m,old in zip(modules,methods,strict=True))
        counts['runtime_closed']=runtime.closed
        assert counts['restored'] and counts['runtime_closed']


@contextmanager
def loaded(arm,fd):
    if arm=='eager':
        with edited_eager() as (model,step,packet):
            yield model,step,packet,{}
        return
    assert fd is not None and fcntl.fcntl(fd,F_GET_SEALS)==SEALS
    with open(f'/proc/self/fd/{fd}','rb') as stream:
        payload = torch.load(stream,map_location='cpu',weights_only=True)
    meta = payload['provenance']
    archive = unpack.read(OUT/'archive.json')
    assert meta['tag']==TAG and meta['parent_sha']==origin.PARENT_SHA and meta['packet']==archive['packet']
    assert packed.payload_storage(payload)==archive['storage']
    model = packed.load_payload(payload)
    del payload
    with native_unpack(model) as counts:
        yield model,meta['step'],meta['packet'],counts


def requests(tokenizer):
    gen = torch.Generator().manual_seed(84907)
    old = unpack.read(unpack.long_cache.OUT/'report.json')
    result = {}
    for context in unpack.long_cache.CONTEXTS:
        seq = torch.randint(35,32768,(1,context+unpack.long_cache.TAIL),generator=gen)
        assert origin.tensor_sha(seq)==old['contexts'][str(context)]['input_sha256']
        result[str(context)] = PreparedPrompt(seq[0,:context].tolist(),tokenizer)
    return result


def request(model,tokenizer,text,*,max_new,stop,audit):
    times,ids,hashes,kv_sizes,memory = [],[],[],[],[]
    started,call_started,first = 0.,0.,None
    original_pick = sample_module._pick

    def start_call(_model,_args):
        nonlocal call_started
        call_started=perf_counter()

    def end_call(_model,_args,output):
        times.append(perf_counter()-call_started)
        if audit:
            logits,kv=output
            assert len(kv)==14
            hashes.append(origin.tensor_sha(logits))
            tensors = {t.untyped_storage().data_ptr():t.untyped_storage().nbytes() for pair in kv.values() for t in pair}
            kv_sizes.append(sum(tensors.values()))
            memory.append(snapshot())

    def pick(*args,**kwargs):
        nonlocal first
        token=original_pick(*args,**kwargs)
        if first is None:
            first=perf_counter()-started
        ids.append(int(token.item()))
        return token

    with ExitStack() as stack:
        stack.callback(model.register_forward_pre_hook(start_call).remove)
        stack.callback(model.register_forward_hook(end_call).remove)
        stack.enter_context(patch.object(sample_module,'_pick',pick))
        started=perf_counter()
        text,finish=sample_module.sample(model,model.cfg,tokenizer,text,max_new=max_new,temperature=0.,top_k=0,
            device='cpu',use_cache=True,stop_at_eos=stop,eos_id=2,logits_last_only=True,return_metadata=True)
        wall=perf_counter()-started
    assert len(times)==len(ids)==finish['generated_tokens'] and first is not None
    return dict(wall=wall,first_token=first,prefill=times[0],decode=times[1:],ids=ids,
                decoded=text,finish=finish,logits=hashes,kv_sizes=kv_sizes,step_memory=memory)


@torch.no_grad()
def worker(index,fd):
    arm=ORDER[index]
    tokenizer=load_tokenizer('ko-en',32768)
    assert tokenizer.get_vocab_size()==32768 and tokenizer.token_to_id('<eos>')==2
    inputs=requests(tokenizer)
    before=snapshot()
    start=perf_counter()
    with loaded(arm,fd) as (model,step,packet,runtime), sdpa_kernel(SDPBackend.MATH):
        load_time=perf_counter()-start
        gc.collect()
        after=snapshot()
        storage=model_storage(model)
        cases,texts={},{}
        order=tuple(inputs) if index%2==0 else tuple(reversed(inputs))
        for label in order:
            args=(model,inputs[label],'')
            audit=request(*args,max_new=GEN,stop=False,audit=True)
            samples=[request(*args,max_new=GEN,stop=False,audit=False) for _ in range(REPEATS)]
            assert all(s['ids']==audit['ids'] and s['finish']==audit['finish'] for s in samples)
            cases[label]=dict(audit=audit,samples=samples,after_request=snapshot())
            print('P108_CPU_REQUEST',index,arm,label,median(s['wall'] for s in samples),flush=True)
        for name,prompt in TEXT:
            row=request(model,tokenizer,prompt,max_new=NATURAL,stop=True,audit=True)
            row['continuation']=tokenizer.decode(row['ids'])
            texts[name]=row
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    assert not torch.cuda.is_initialized()
    write(OUT/f'worker_{index}.json',dict(index=index,arm=arm,model_step=step,packet=packet,runtime=runtime,
        load_seconds=load_time,baseline=before,loaded=after,model_storage=storage,peak_rss=peak,cases=cases,texts=texts,
        affinity=sorted(os.sched_getaffinity(0)),checkpoint_writes=0))


def child(phase,limit,fd,*args):
    return subprocess.run([sys.executable,'-B','-u','-X','utf8','-m','scripts.diag_p108_g4_cpu_request',
        phase,*(str(x) for x in args),'--fd',str(fd)],cwd=origin.ROOT,timeout=limit,pass_fds=(fd,)).returncode


def run():
    p=contract()
    OUT.mkdir(exist_ok=False)
    write(OUT/'profile.json',p)
    create=ctypes.CDLL(None,use_errno=True).memfd_create
    create.argtypes=[ctypes.c_char_p,ctypes.c_uint]
    create.restype=ctypes.c_int
    fd=create(b'p108_g4_packed_request',MFD_CLOEXEC|MFD_ALLOW_SEALING)
    if fd<0:
        error=ctypes.get_errno()
        raise OSError(error,os.strerror(error))
    exits={}
    try:
        export_exit=child('export',90,fd)
        if export_exit!=0:
            raise RuntimeError(f'packed export exited {export_exit}')
        fcntl.fcntl(fd,F_ADD_SEALS,SEALS)
        for i in range(len(ORDER)):
            try:
                exits[i]=child('worker',75,fd,i)
            except subprocess.TimeoutExpired:
                exits[i]=124
            print('P108_CPU_REQUEST_EXIT',i,ORDER[i],exits[i],flush=True)
    finally:
        os.close(fd)
    if set(exits.values())!={0}:
        write(OUT/'report.json',dict(exits=exits,transport_closed=True))
        return 8
    all_rows=[unpack.read(OUT/f'worker_{i}.json') for i in range(len(ORDER))]
    compare={}
    for label in (*map(str,unpack.long_cache.CONTEXTS),*(name for name,_ in TEXT)):
        cases=[row['cases'][label]['audit'] if label in row['cases'] else row['texts'][label] for row in all_rows]
        compare[label]={key:all(v[key]==cases[0][key] for v in cases) for key in ('ids','decoded','finish','logits','kv_sizes')}
    assert p==contract()
    write(OUT/'report.json',dict(exits=exits,transport_closed=True,comparison=compare,workers=all_rows,
                                archive=unpack.read(OUT/'archive.json')))
    print('P108_CPU_REQUEST_COMPLETE',compare,flush=True)
    return 0 if all(all(q.values()) for q in compare.values()) else 8


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('run','export','worker'))
    parser.add_argument('index',type=int,nargs='?')
    parser.add_argument('--fd',type=int)
    a=parser.parse_args()
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    assert datetime.now(origin.CUTOFF.tzinfo)+timedelta(minutes=8)<origin.CUTOFF
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if a.phase=='run':
        assert a.index is None and a.fd is None
        return run()
    assert a.fd is not None
    if a.phase=='export':
        assert a.index is None
        export(a.fd)
    else:
        assert a.index is not None and 0<=a.index<len(ORDER)
        worker(a.index,a.fd)


if __name__=='__main__':
    sys.exit(main())
