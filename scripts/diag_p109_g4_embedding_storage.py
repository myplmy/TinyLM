"""Pair 32K G4 embedding compression quality with realized CPU storage."""

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import math
import os

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_frozen_g4_routes as frozen
from scripts import diag_p108_g4_cpu_request as deploy
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p106b_resource_matrix import model_storage
from tinylm.data.prepare import load_tokenizer
from tinylm.model.ternary import ternary_g


TAG = 'p109_g4_embedding_storage_v1_20261119'
OUT = frozen.OUT.with_name(TAG)
ARMS = ('int8','twn')
HEAD_ROWS, CONTEXT, GENERATED = 1024,512,8
ORIGIN = deploy.origin
PACK = ORIGIN.packed
SOURCES = tuple(dict.fromkeys((*frozen.SOURCES,*deploy.SOURCES,'scripts/diag_p109_g4_embedding_storage.py')))
READ, WRITE, SHA = frozen.read_json, frozen.prior.io.write, frozen.prior.io.digest


def dense_table_digest(table):
    assert table.dtype==torch.float32 and table.shape==(32768,256)
    return sha256(table.contiguous().view(torch.uint8).numpy()).hexdigest().upper()


@torch.no_grad()
def tables(model):
    original = model.emb.weight.detach()
    assert original.device.type=='cpu' and original.shape==(32768,256) and model.embedding_quantized() is None
    twn = ternary_g(original,original.shape[1],model.cfg)
    # The 5-trit payload has one zero code, so match its sign of zero.
    twn.masked_fill_(twn==0,0.)
    model.quantize_embedding('int8')
    int8 = model._emb_rows()
    model.emb.weight.data=original
    model._emb_fmt=None
    del model._emb_code,model._emb_scale,model._emb_g
    return dict(int8=int8,twn=twn)


def check_inputs():
    pins, data = frozen.prepare_inputs()
    old = READ(frozen.OUT/'profile.json')
    raw, report, profile = (frozen.OUT/n for n in ('choice_batches.jsonl','gpu_report.json','profile.json'))
    meta=READ(report)
    assert SHA(raw)==meta['raw_sha256'] and SHA(profile)==meta['profile_sha256']
    assert pins.files==old['files']
    assert {name:d['receipt'] for name,d in data.items()}==old['tasks']
    return pins, data


def pins():
    refs=(frozen.OUT/'profile.json',frozen.OUT/'gpu_report.json',frozen.OUT/'choice_batches.jsonl',
          frozen.OUT/'report.json',deploy.unpack.OUT/'report.json',frozen.prior.PARENT,frozen.TOKENIZER)
    return dict(tag=TAG,requests=READ(frozen.OUT/'profile.json')['tasks'],
        files={str(path.relative_to(frozen.ROOT)):SHA(path) for path in refs},sources={s:SHA(frozen.ROOT/s) for s in SOURCES},
        head_rows=HEAD_ROWS,context=CONTEXT,generated=GENERATED,arms=list(ARMS),approval='WIP176',checkpoint_writes=0)


def prep():
    old,data=check_inputs()
    m,step=ORIGIN.load_model()
    values=tables(m)
    profile=pins()
    profile['table_sha256']={key:dense_table_digest(v) for key,v in values.items()}
    profile['checkpoint_step']=step
    old.unchanged()
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    WRITE(OUT/'profile.json',profile)
    print('P109_EMBEDDING_READY',profile['table_sha256'],{k:p['receipt']['rows'] for k,p in data.items()},flush=True)


def verify():
    p=READ(OUT/'profile.json')
    assert {k:v for k,v in p.items() if k not in ('table_sha256','checkpoint_step')}==pins()
    return p


@torch.no_grad()
def gpu(p):
    from scripts.p070b_cla_routes import schedule

    assert torch.cuda.device_count()==1 and torch.cuda.mem_get_info()[0]>=4*2**30
    torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    verified, data=check_inputs()
    cfg,state,step=frozen.prior.load_parent(torch)
    model=frozen.prior.build_model(cfg).eval()
    model.load_state_dict(state,strict=True)
    del state
    replacements=tables(model)
    assert {k:dense_table_digest(x) for k,x in replacements.items()}==p['table_sha256']
    assert p['checkpoint_step']==step
    model=model.cuda().float()
    model.set_anneal(1.)
    route=schedule(cfg,model.owner,'uniform',2)
    assert len(route)==28 and route==model._repeat_schedule(2.)
    model.set_route(route)
    assert model.route_sha256==READ(frozen.OUT/'gpu_report.json')['route_book']['uniform_r2'][0]
    scorer=frozen.adapter.TorchLikelihood(dict(torch=torch,model=model,cfg=cfg),model)
    body=lambda:state_sha({k:v for k,v in model.state_dict().items() if k!='emb.weight'})
    source=body()
    raw=OUT/'choice_batches.jsonl'
    counters={}
    with raw.open('x',encoding='utf-8') as stream, torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        model.freeze_quant()
        for arm in ARMS:
            model.emb.weight.copy_(replacements[arm])
            scorer(data['winogrande']['batches'][0])
            for task,spec in data.items():
                choices=0
                for i,batch in enumerate(spec['batches']):
                    if (OUT/'STOP').exists() or datetime.now(frozen.prior.CUTOFF.tzinfo)>=frozen.prior.CUTOFF:
                        raise RuntimeError('evaluation window ended or owned stop')
                    values=scorer(batch)
                    assert len(values)==len(batch['input_ids'])
                    choices+=len(values)
                    print(json.dumps(dict(arm=arm,task=task,index=i,scores=values),allow_nan=False),file=stream,flush=True)
                assert choices==2*frozen.TASKS[task]
                counters[f'{arm}_{task}']=choices
                print('P109_EMBEDDING_EVAL',arm,task,choices,flush=True)
    scorer.close()
    assert body()==source and verify()==p
    verified.unchanged()
    WRITE(OUT/'gpu_report.json',dict(raw_sha256=SHA(raw),profile_sha256=SHA(OUT/'profile.json'),
        counts=counters,route_sha256=model.route_sha256,unchanged_body_sha256=source,
        device=torch.cuda.get_device_name(),checkpoint_writes=0,baseline_eval_calls=0))


@torch.no_grad()
def cpu(p):
    assert not torch.cuda.is_initialized()
    tokenizer=load_tokenizer('ko-en',32768)
    token_ids=torch.randint(35,32768,(CONTEXT,),generator=torch.Generator().manual_seed(36971)).tolist()
    prompt=deploy.PreparedPrompt(token_ids,tokenizer)
    source,step=ORIGIN.load_model()
    assert step==p['checkpoint_step']
    rows={}
    for arm in ARMS:
        fmt='fp32_unchanged' if arm=='int8' else 'ternary5_existing_twn'
        payload=PACK.export_payload(source,provenance={'tag':TAG,'arm':arm},embedding_format=fmt,head_rows=HEAD_ROWS)
        model=PACK.load_payload(payload)
        del payload
        if arm=='int8':
            model.quantize_embedding('int8')
            model.cfg.emb_chunk=HEAD_ROWS
            storage=[model._emb_code,model._emb_scale]
        else:
            storage=[model.packed_embedding.packed_codes,model.packed_embedding.group_scales]
        check=sha256()
        for start in range(0,32768,HEAD_ROWS):
            tile=model._emb_rows(slice(start,start+HEAD_ROWS))
            check.update(tile.contiguous().view(torch.uint8).numpy())
        assert check.hexdigest().upper()==p['table_sha256'][arm]
        physical=model_storage(model)['unique_storage_bytes']
        with deploy.native_unpack(model) as receipt, sdpa_kernel(SDPBackend.MATH):
            inference=deploy.request(model,prompt,'',max_new=GENERATED,stop=False,audit=True)
        kv=inference['kv_sizes'][-1]
        rows[arm]=dict(table_bytes=sum(t.untyped_storage().nbytes() for t in storage),
            model_tensor_bytes=physical,kv_bytes=kv,model_and_kv_bytes=physical+kv,
            ids=inference['ids'],kv_context=CONTEXT+GENERATED-1,effective_table_sha256=check.hexdigest().upper(),
            observed_request_seconds=inference['wall'],body_lookup_calls=receipt['lookup_calls'])
        print('P109_EMBEDDING_CPU_STORAGE',arm,physical,kv,flush=True)
        del model,storage
    assert verify()==p and not torch.cuda.is_initialized()
    WRITE(OUT/'cpu_report.json',dict(arms=rows,profile_sha256=SHA(OUT/'profile.json'),checkpoint_writes=0))


def collect(p):
    import numpy as np

    check,data=check_inputs()
    raw=OUT/'choice_batches.jsonl'
    close=READ(OUT/'gpu_report.json')
    cpu_values=READ(OUT/'cpu_report.json')
    assert close['raw_sha256']==SHA(raw)
    assert close['profile_sha256']==cpu_values['profile_sha256']==SHA(OUT/'profile.json')
    old=frozen.OUT/'choice_batches.jsonl'
    with old.open(encoding='utf-8') as stream:
        original={(r['task'],r['index']):r['arms']['uniform_r2']['scores'] for r in map(json.loads,stream)}
    with raw.open(encoding='utf-8') as stream:
        variants={(r['arm'],r['task'],r['index']):r['scores'] for r in map(json.loads,stream)}
    assert len(variants)==len(ARMS)*len(original)
    rand=np.random.default_rng(1337)
    result={}
    for task,spec in data.items():
        scores={'fp32':[],**{arm:[] for arm in ARMS}}
        for i,batch in enumerate(spec['batches']):
            scores['fp32'].extend(original[(task,i)])
            for arm in ARMS:
                values=variants[(arm,task,i)]
                assert len(values)==len(batch['input_ids'])
                scores[arm].extend(values)
        gold=np.asarray([row['gold'] for row in spec['rows']])
        expected=READ(frozen.OUT/'report.json')['tasks'][task]['by_arm']['uniform_r2']['acc']
        picks,accuracy={},{}
        for arm,values in scores.items():
            assert len(values)==2*len(gold) and all(math.isfinite(v) and type(g) is bool for v,g in values)
            picks[arm]=np.asarray([int(y[0]>x[0]) for x,y in zip(values[::2],values[1::2],strict=True)])
            val=[spec['task'].process_results(row['doc'],values[2*i:2*i+2])['acc'] for i,row in enumerate(spec['rows'])]
            assert all(int(o)==int(h) for o,h in zip(val,picks[arm]==gold,strict=True))
            assert len(val)==frozen.TASKS[task]
            accuracy[arm]=float((picks[arm]==gold).mean())
        assert math.isclose(accuracy['fp32'],expected,rel_tol=0,abs_tol=1e-12)
        base=(picks['fp32']==gold).astype(np.int8)
        movements={}
        for arm in ARMS:
            hit=(picks[arm]==gold).astype(np.int8)
            movement=frozen.paired_delta(hit-base,rand)
            movement.update(changed_choices=int((picks[arm]!=picks['fp32']).sum()),
                            retained_correct=int(((hit==1)&(base==1)).sum()))
            movements[arm]=movement
        result[task]=dict(rows=len(gold),accuracy=accuracy,matched=movements)
    check.unchanged()
    assert verify()==p
    WRITE(OUT/'report.json',dict(tasks=result,cpu=cpu_values['arms'],gpu=close,baseline_sha256=SHA(old),
                               bootstrap_replicates=20000))
    print('P109_EMBEDDING_COMPLETE',result,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','gpu','cpu','collect'))
    a=parser.parse_args()
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==('0' if a.phase=='gpu' else '')
    assert datetime.now(frozen.prior.CUTOFF.tzinfo)+timedelta(minutes=4)<frozen.prior.CUTOFF
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if a.phase=='prepare':
        return prep()
    {'gpu':gpu,'cpu':cpu,'collect':collect}[a.phase](verify())


if __name__=='__main__':
    main()
