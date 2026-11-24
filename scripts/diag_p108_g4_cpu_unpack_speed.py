"""Isolate exact CPU tile unpacking costs in the edited G4 cached decoder."""

from datetime import datetime
import json
import os
from statistics import median
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_cache_long_cpu as long_cache
from scripts.p014e_direct_cpu import KernelRuntime, ABI
from tinylm.model.lut import pattern_table


origin = long_cache.prior
packed = origin.packed
TAG = 'p108_g4_packed_cpu_inner_v1_20261119'
OUT = long_cache.OUT.with_name(TAG)
OWNED_RUNTIME = origin.ROOT / 'test_result/evidence/p014e_direct_packed_v1_s1337/cpu_v1'
SOURCES = (*long_cache.SOURCES,'scripts/diag_p108_g4_cpu_unpack_speed.py',
           'scripts/p014e_direct_cpu.py','scripts/p014e_direct_cpu.c')
METHODS = ('reference','numpy_lookup','native_lookup')
ORDER = (*METHODS,*reversed(METHODS))


def read(path):
    return json.loads(path.read_bytes())


def native_runtime():
    p = read(OWNED_RUNTIME/'profile.json')
    spec = p['library']
    assert read(OWNED_RUNTIME/'compiler_report.json')['returncode']==0
    assert spec['ABI']==ABI and p['lookup_bit_exact'] and p['torch_version']==torch.__version__
    for name in ('scripts/p014e_direct_cpu.c','scripts/p014e_direct_cpu.py','scripts/p014e_packed_g128.py'):
        assert p['sources'][name]==origin.digest(origin.ROOT/name),name
    path = origin.ROOT/spec['path']
    assert path.stat().st_size==spec['bytes']
    return KernelRuntime(path,spec['sha256'],workers=1),spec


def alternatives(model,runtime):
    matrix = [m for m in model.modules() if isinstance(m,packed.PackedGroupLinear)]
    row_ids = torch.arange(max(m.out_f for m in matrix))
    digits = pattern_table(5,dtype=torch.int8).numpy()

    def numpy_lookup(m,start,stop):
        codes = m.packed_codes[start:stop].numpy()
        trits = digits[codes].reshape(*codes.shape[:-1],-1)[...,:m.group]
        scales = m.group_scales[start:stop].numpy()[...,None]
        return torch.from_numpy(np.multiply(trits,scales,dtype=np.float32).reshape(stop-start,m.in_f))

    def native_lookup(m,start,stop):
        return runtime.lookup(m,row_ids[start:stop])

    methods = dict(reference=packed.PackedGroupLinear.unpack_rows,
                   numpy_lookup=numpy_lookup,native_lookup=native_lookup)
    scratch = dict(numpy_digit_table_bytes=digits.nbytes,native_id_vector_bytes=row_ids.numel()*row_ids.element_size())
    elements, tiles = 0, 0
    for m in matrix:
        assert m.tile_rows==128 and m.packed_codes.device.type=='cpu'
        for start in range(0,m.out_f,m.tile_rows):
            stop = min(start+m.tile_rows,m.out_f)
            ordinary = methods['reference'](m,start,stop)
            for method in (numpy_lookup,native_lookup):
                candidate = method(m,start,stop)
                assert torch.equal(ordinary.view(torch.int32),candidate.view(torch.int32))
            elements += ordinary.numel()
            tiles += 1
    return methods,dict(physical_matrices=len(matrix),elements=elements,tiles=tiles,**scratch)


def measure(model,decode_ids,kv,unpack):
    base_linear = F.linear
    rows, bytes_per_tile, unpack_seconds, linear_seconds, steps = 0, 0, 0., 0., []
    values = []

    def time_unpack(m,start,stop):
        nonlocal rows,bytes_per_tile,unpack_seconds
        begin = perf_counter()
        w = unpack(m,start,stop)
        unpack_seconds += perf_counter()-begin
        rows += 1
        bytes_per_tile = max(bytes_per_tile,w.numel()*w.element_size())
        return w

    def time_linear(*args,**kwargs):
        nonlocal linear_seconds
        begin = perf_counter()
        result = base_linear(*args,**kwargs)
        linear_seconds += perf_counter()-begin
        return result

    context = next(iter(kv.values()))[0].shape[2]
    keys = set(kv)
    with patch.object(packed.PackedGroupLinear,'unpack_rows',time_unpack),patch.object(F,'linear',time_linear):
        for index,token in enumerate(decode_ids.split(1,dim=1),1):
            start = perf_counter()
            logits,kv = model(token,past_kv=kv,use_cache=True,logits_last_only=True)
            steps.append(perf_counter()-start)
            values.append(logits)
            assert set(kv)==keys and len(kv)==14
            assert all(k.shape[2]==v.shape[2]==context+index for k,v in kv.values())
    unique = {t.untyped_storage().data_ptr():t.untyped_storage().nbytes() for pair in kv.values() for t in pair}
    return torch.cat(values,dim=1),dict(decode_seconds=steps,unpack_seconds=unpack_seconds,
        all_linear_seconds=linear_seconds,unpack_calls=rows,max_fp32_tile_bytes=bytes_per_tile,
        kv_bytes=sum(unique.values()))


def context_bench(model,methods,old,context,tokens):
    assert old['input_sha256']==origin.tensor_sha(tokens)
    prefix,kv = model(tokens[:,:context],use_cache=True,logits_last_only=True)
    original_cache = {key:tuple(origin.tensor_sha(v) for v in pair) for key,pair in kv.items()}
    rows = {name:[] for name in METHODS}
    reference = None
    for name in ORDER:
        out,raw = measure(model,tokens[:,context:],kv,methods[name])
        if reference is None:
            reference = out
            joined = torch.cat((prefix,reference),dim=1)
            assert joined.argmax(dim=-1).tolist()==old['cached_eager_vs_packed']['reference_greedy']
        same = torch.equal(out,reference)
        assert same and raw['kv_bytes']==old['packed']['physical_kv_bytes']
        rows[name].append(dict(**raw,logits_exact=True))
    assert original_cache=={key:tuple(origin.tensor_sha(v) for v in pair) for key,pair in kv.items()}
    results = {name:dict(repetitions=rs,median_decode=median(s for a in rs for s in a['decode_seconds']),
                    median_unpack=median(a['unpack_seconds'] for a in rs),
                    median_all_linear=median(a['all_linear_seconds'] for a in rs)) for name,rs in rows.items()}
    print('P108_UNPACK',context,{name:result['median_decode'] for name,result in results.items()},flush=True)
    return results


@torch.no_grad()
def run():
    old_path = long_cache.OUT/'report.json'
    old = read(old_path)
    pins = {name:origin.digest(origin.ROOT/name) for name in SOURCES}
    assert all(pins[name]==value for name,value in old['source_pins'].items())
    assert origin.digest(origin.PARENT)==old['parent_sha256']==origin.PARENT_SHA
    model,step = origin.load_model()
    owner = origin.physical_down_owners(model)[2]
    codes = owner.module._wq
    initial = origin.tensor_sha(codes)
    edit,_ = origin.edit_packet(codes,model.cfg.micro_group)
    assert edit['target_sha256']==old['packet_target']
    with origin.apply_shared_down_packets(model,{2:edit},realization='codes'):
        payload = packed.export_payload(model,provenance={'source_checkpoint_sha256':origin.PARENT_SHA,'tag':TAG})
    assert owner.module._wq is codes and origin.tensor_sha(codes)==initial
    storage=packed.payload_storage(payload)
    assert storage==old['packed_storage']
    model=packed.load_payload(payload)
    del owner,codes,payload

    runtime,spec=native_runtime()
    try:
        methods,weights=alternatives(model,runtime)
        gen=torch.Generator().manual_seed(84907)
        results={}
        with sdpa_kernel(SDPBackend.MATH):
            for context in long_cache.CONTEXTS:
                tokens=torch.randint(35,model.cfg.vocab_size,(1,context+long_cache.TAIL),generator=gen)
                results[str(context)]=context_bench(model,methods,old['contexts'][str(context)],context,tokens)
    finally:
        runtime.close()
    assert origin.digest(origin.PARENT)==origin.PARENT_SHA and not torch.cuda.is_initialized()
    assert pins=={name:origin.digest(origin.ROOT/name) for name in SOURCES}
    OUT.mkdir(exist_ok=False)
    with (OUT/'report.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(tag=TAG,step=step,source_pins=pins,parent_sha=origin.PARENT_SHA,
            old_result_sha=origin.digest(old_path),prior_local_library=spec,library_closed=runtime.closed,
            cpu_affinity=sorted(os.sched_getaffinity(0)),pack_storage=storage,tile_checks=weights,contexts=results,
            candidate_order=ORDER,checkpoint_writes=0,full_weight_cache=False),stream,ensure_ascii=False,indent=2)
        print(file=stream)


if __name__=='__main__':
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and datetime.now(origin.CUTOFF.tzinfo)<origin.CUTOFF
    assert not OUT.exists()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run()
