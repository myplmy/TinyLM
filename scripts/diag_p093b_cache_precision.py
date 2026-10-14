"""Same saved parent/shared/r64 cache x precision; no learning or raw mutation."""
from __future__ import annotations
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p093b_generation_attribution as legacy
from scripts.diag_p101a_mtp_parity import PrecisionForward,CaptureTokens,first_difference
from scripts.p106b_shards import ShardWriter,verify
TARGET=ROOT/'test_result/evidence/p093b_cache_precision_v1_s1337'


def preflight():
    if TARGET.exists() or TARGET.is_symlink():raise FileExistsError('preserve existing precision diagnosis')
    source=legacy.source()
    from scripts.p106b_education_followup import ARMS
    spec=ARMS['a'];tok=ROOT/spec['tokenizer']
    if legacy.old.digest(legacy.old.PARENT)!=legacy.recovery.PARENT_SHA:
        raise ValueError('native parent changed')
    if legacy.old.digest(tok)!=spec['tok_sha']:raise ValueError('legacy tokenizer changed')
    manifests={role:legacy.original_answers(role)[1] for role in ('parent','shared','rank64')}
    return source,tok,dict(schema='P093B_CACHE_PRECISION_PAIR_V1',
        source_report_sha256=legacy.REPORT_SHA,parent_sha256=legacy.recovery.PARENT_SHA,
        tokenizer_sha256=spec['tok_sha'],original_manifests_sha256=manifests,
        source_code_migrations=source['runtime_calibration_code_updates'],
        max_new=96,precisions=['bf16_auto','fp32_math'],cache_modes=[True,False],
        subjects=['parent','shared','rank64'],new_generations=96,
        optimizer_updates=0,checkpoint_writes=0,tf32=False,
        code_sha256={p:legacy.old.digest(ROOT/p) for p in
            ('scripts/diag_p093b_cache_precision.py','scripts/diag_p093b_generation_attribution.py',
             'scripts/test_p093b_generation_probe.py','scripts/diag_p101a_mtp_parity.py',
             'tinylm/infer/generate.py','tinylm/model/transformer.py')})


def execute(args):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model,sample
    from scripts import p093b_native_repair as native
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    source,tokpath,info=preflight();idle_before_gpu()
    TARGET.mkdir(parents=True,exist_ok=False);writer=ShardWriter(TARGET,'answers')
    pairs=[];start=time.perf_counter();rc=9;status='STARTED'
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    try:
        with wall_limit(args.max_wall_sec),torch.no_grad():
            base,cfg,device=load_model('dense',str(legacy.old.PARENT),'cuda')
            if cfg.n_layers!=16 or cfg.tie_mlp or cfg.n_modes!=1:raise ValueError('old parent geometry changed')
            ids=source['input']['group_layers'];originals=[base.layers[i].mlp[0] for i in ids]
            shared=native.shared_native(originals,cfg)
            adapters=legacy.old.load_adapters(legacy.BASE,'rank64',shared,cfg,source['input'])
            tok=Tokenizer.from_file(str(tokpath))
            for role in ('parent','shared','rank64'):
                rows,_=legacy.original_answers(role)
                context=nullcontext() if role=='parent' else native.patched_group(base,ids,shared,
                    adapters if role=='rank64' else None)
                with context:
                    for precision in ('bf16_auto','fp32_math'):
                        model=PrecisionForward(base,precision)
                        for row in rows:
                            results=[];prompt_ids=tok.encode(row['prompt']).ids
                            for cache in (True,False):
                                wrapped=CaptureTokens(tok);torch.cuda.synchronize();tick=time.perf_counter()
                                decoded,meta=sample(model,cfg,wrapped,row['prompt'],max_new=96,
                                    temperature=0.,top_k=1,device=device,use_cache=cache,
                                    logits_last_only=True,return_metadata=True)
                                torch.cuda.synchronize();record=dict(subject=role,id=row['id'],
                                    precision=precision,use_cache=cache,prompt=row['prompt'],
                                    generated_ids=wrapped.decoded_ids[len(prompt_ids):],decoded=decoded,
                                    generation=meta,seconds=time.perf_counter()-tick,semantic_quality='NOT_REVIEWED')
                                writer.append(record);results.append(record)
                                print('[P093B_PRECISION_ANSWER] '+json.dumps(record,ensure_ascii=False),flush=True)
                            left,right=results
                            pair=dict(subject=role,id=row['id'],precision=precision,
                                ids_equal=left['generated_ids']==right['generated_ids'],
                                text_equal=left['decoded']==right['decoded'],
                                finish_equal=left['generation']['finish_reason']==right['generation']['finish_reason'],
                                count_equal=left['generation']['generated_tokens']==right['generation']['generated_tokens'],
                                first_difference=first_difference(left['generated_ids'],right['generated_ids']))
                            pair['parity']=all(pair[k] for k in ('ids_equal','text_equal','finish_equal','count_equal'))
                            pairs.append(pair)
        status='CACHE_PRECISION_COLLECTION_COMPLETE';rc=0
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 9;status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR'
        info['error']=dict(type=type(exc).__name__,reason=str(exc)[:1000])
    finally:
        manifest=writer.close(lineage=info);verify(TARGET,manifest)
        legacy.old.write(TARGET/'report.json',dict(info,status=status,returncode=rc,pairs=pairs,
            answers_manifest=manifest,whole_sec=time.perf_counter()-start,
            quality='NOT_REVIEWED',production_precision_adopted=False,
            scope='collection0 is not all-pair parity or repetition repair; same wrong output can match'))
    return rc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=900:p.error('bounded no-training gate required')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[2]));return 0
    return execute(a)

if __name__=='__main__':raise SystemExit(main())
