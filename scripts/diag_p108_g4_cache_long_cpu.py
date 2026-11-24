"""Measure long cached CPU outputs across the proven edited G4 packed transfer."""

from datetime import datetime
import json
import os
from pathlib import Path
from time import perf_counter

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_shared_pack as prior


TAG = 'p108_g4_cache_long_cpu_v1_20261119'
OUT = prior.OUT.parent.with_name(TAG)
CONTEXTS, TAIL = (128,512), 4
SOURCES = (*prior.SOURCES,'scripts/diag_p108_g4_cache_long_cpu.py')


def measure(model,tokens,context):
    t = perf_counter()
    full = model(tokens)[:,context-1:].clone()
    full_seconds = perf_counter()-t
    t = perf_counter()
    last, cache = model(tokens[:,:context],use_cache=True,logits_last_only=True)
    prefill_seconds = perf_counter()-t
    keys = set(cache)
    outputs, timing = [last], []
    for index in range(context,context+TAIL):
        t = perf_counter()
        last,cache = model(tokens[:,index:index+1],past_kv=cache,use_cache=True,logits_last_only=True)
        timing.append(perf_counter()-t)
        outputs.append(last)
        assert set(cache)==keys and len(cache)==14
        assert all(k.shape[2]==v.shape[2]==index+1 for k,v in cache.values())
    resident = {}
    for tensors in cache.values():
        for x in tensors:
            storage=x.untyped_storage()
            resident[storage.data_ptr()]=storage.nbytes()
    return full,torch.cat(outputs,dim=1),dict(full_seconds=full_seconds,prefill_seconds=prefill_seconds,
        decode_seconds=timing,kv_entries=len(keys),kv_length=context+TAIL,physical_kv_bytes=sum(resident.values()))


@torch.no_grad()
def run():
    raw = json.loads(prior.OUT.read_bytes())
    assert prior.digest(prior.PARENT)==raw['checkpoint_sha256']==prior.PARENT_SHA
    assert raw['refreeze_restored'] and raw['master_unchanged']
    pins = {name:prior.digest(prior.ROOT/name) for name in SOURCES}
    model,step = prior.load_model()
    owner = prior.physical_down_owners(model)[2]
    matrix = owner.module._wq
    initial = prior.tensor_sha(matrix)
    editing,_ = prior.edit_packet(matrix,model.cfg.micro_group)
    assert editing['target_sha256']==raw['packet']['target_sha256']
    gen = torch.Generator().manual_seed(84907)
    out = {}
    with prior.apply_shared_down_packets(model,{2:editing},realization='codes') as edit, sdpa_kernel(SDPBackend.MATH):
        assert edit[0]['changed_trits']==2
        payload = prior.packed.export_payload(model,provenance={'source_checkpoint_sha256':prior.PARENT_SHA,'tag':TAG})
        loaded = prior.packed.load_payload(payload)
        physical = loaded.layers[2].mlp[0].down_proj
        assert isinstance(physical,prior.packed.PackedGroupLinear)
        assert all(loaded.layers[i].mlp[0].down_proj is physical for i in owner.layers)
        for start in range(0,physical.out_f,physical.tile_rows):
            stop = min(start+physical.tile_rows,physical.out_f)
            assert torch.equal(physical.unpack_rows(start,stop),owner.module._wq[start:stop])
        storage = prior.packed.payload_storage(payload)
        del payload
        for context in CONTEXTS:
            tokens = torch.randint(35,model.cfg.vocab_size,(1,context+TAIL),generator=gen)
            ef,ec,eager = measure(model,tokens,context)
            pf,pc,packed = measure(loaded,tokens,context)
            out[str(context)] = dict(input_sha256=prior.tensor_sha(tokens),eager=eager,packed=packed,
                full_eager_vs_packed=prior.compare(ef,pf),cached_eager_vs_packed=prior.compare(ec,pc),
                eager_full_vs_cached=prior.compare(ef,ec),packed_full_vs_cached=prior.compare(pf,pc))
            cached = out[str(context)]['cached_eager_vs_packed']
            print('P108_G4_LONG_CACHE_CPU',context,packed['kv_entries'],packed['physical_kv_bytes'],
                  cached['max_abs'],cached['outside_tolerance'],flush=True)
    assert owner.module._wq is matrix and prior.tensor_sha(matrix)==initial
    assert pins=={name:prior.digest(prior.ROOT/name) for name in SOURCES}
    assert prior.digest(prior.PARENT)==prior.PARENT_SHA and not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    with (OUT/'report.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(tag=TAG,checkpoint_step=step,parent_sha256=prior.PARENT_SHA,source_pins=pins,
            packed_storage=storage,packet_target=editing['target_sha256'],contexts=out,
            forced_decode_tokens=TAIL,optimizer_updates=0,checkpoint_writes=0),stream,ensure_ascii=False,indent=2)
        print(file=stream)


if __name__=='__main__':
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and datetime.now(prior.CUTOFF.tzinfo)<prior.CUTOFF
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run()
