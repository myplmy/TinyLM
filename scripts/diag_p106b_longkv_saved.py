#!/usr/bin/env python3
"""CPU-only replay of saved benchmark histories; no new sampled answers or training."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1',
    TRANSFORMERS_OFFLINE='1', USE_HUB_KERNELS='0', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2',
    OPENBLAS_NUM_THREADS='2', TOKENIZERS_PARALLELISM='false')
from scripts import interactive_research_infer as manual
from scripts.diag_p106b_resource_matrix import wall as wall_limit

INPUT = ROOT/'test_result/evidence/p106b_gsm8k_nvml_v1_20261101/native595-q/full'
OUTPUT = ROOT/'test_result/evidence/p106b_longkv_cpu_v1_20261101'
DOC_IDS = (0, 149, 509)
POSITIONS = (0, 8, 64, 128, 255)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def selected_inputs():
    report = json.loads((INPUT/'report.json').read_text())
    assert report['final_exit']==0 and report['actual_rows']==1319
    assert report['source_unchanged'] and report['parent_unchanged']
    selected = {}
    bindings = {str((INPUT/'report.json').relative_to(ROOT)):digest(INPUT/'report.json')}
    for spec in report['generation']['shards']:
        path = INPUT/'generation'/spec['path']
        raw = path.read_bytes()
        assert len(raw)==spec['bytes']<4_000_000 and digest(path)==spec['sha256']
        bindings[str(path.relative_to(ROOT))] = spec['sha256']
        for line in raw.splitlines():
            row = json.loads(line)
            if row['doc_id'] in DOC_IDS:
                assert row['doc_id'] not in selected
                assert row['role']=='OFFICIAL_TEST_GENERATION_NEVER_TRAIN'
                ids = row['metadata']['generated_ids']
                prefix = row['metadata']['actual_prefix_ids']
                assert len(ids)==256 and len(prefix)<=768
                assert all(type(i) is int and 0<=i<32768 for i in ids+prefix)
                selected[row['doc_id']] = row
    assert tuple(sorted(selected))==DOC_IDS
    return [selected[i] for i in DOC_IDS], bindings


def compare_logits(left, right, torch):
    assert left.shape==right.shape and left.ndim==2
    delta = (left.float()-right.float()).abs()
    top = left.float().topk(2,dim=-1)
    return dict(max_abs=float(delta.max()),
        float_close=bool(torch.allclose(left,right,atol=1e-4,rtol=1e-4)),
        argmax_equal=bool(left.argmax(-1).eq(right.argmax(-1)).all()),
        incremental_top1=int(top.indices[0,0]), incremental_margin=float(top.values[0,0]-top.values[0,1]),
        rebuilt_top1=int(right.argmax(-1)[0]), atol=1e-4, rtol=1e-4)


def compare_kv(left, right, torch):
    assert set(left)==set(right) and left
    rows = []
    for owner in sorted(left,key=str):
        assert len(left[owner])==len(right[owner])==2
        record = dict(owner=str(owner), tensors=[])
        for a,b in zip(left[owner],right[owner]):
            assert a.shape==b.shape and a.dtype==b.dtype==torch.float32
            record['tensors'].append(dict(shape=list(a.shape),max_abs=float((a-b).abs().max()),
                float_close=bool(torch.allclose(a,b,atol=1e-4,rtol=1e-4))))
        rows.append(record)
    return rows


def execute():
    assert not OUTPUT.exists(), 'Preserve previous output; use a new version.'
    cases, bindings = selected_inputs()
    manifest = manual.verify_manifest()
    spec = manual.resolve_model('native595-q')
    entry = manifest['entries'][spec.name]
    torch,config_type,model_type,method = manual.inference_modules()
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.manual_seed(1337)
    from torch.nn.attention import sdpa_kernel, SDPBackend
    began = time.monotonic()
    sources={name:digest(ROOT/name) for name in ('scripts/diag_p106b_longkv_saved.py',
        'scripts/test_p106b_longkv_saved.py','run_P106B_Stage15aW_gsm8k_longkv_cpu.sh')}
    result = dict(schema='P106B_SAVED_LONG_KV_CPU_V1',status='STARTED',
        doc_ids=list(DOC_IDS),positions=list(POSITIONS),selection='POSTHOC_IMPLEMENTATION_DIAGNOSIS_NOT_RANDOM_QUALITY_SAMPLE',
        selected_before_new_execution=True, device='cpu',threads=2,precision='FP32_MATH',
        atol=1e-4,rtol=1e-4,source_bindings=bindings,own_sources=sources,auditor_sha256=digest(Path(__file__)),
        checkpoint=spec.checkpoint,checkpoint_sha256=entry['checkpoint']['sha256'],
        core_sha256_expected=entry['core_sha256'],cases=[],model_training=0,new_sampled_answers=0,
        checkpoint_writes=0,benchmark_train_or_teacher_reuse=False,
        interpretation='CPU_SAME_SAVED_HISTORY_ONLY_NOT_GPU_EQUIVALENCE_OR_UNIVERSAL_CACHE_SAFETY')
    code,model,payload = 9,None,None
    try:
        with wall_limit(600),sdpa_kernel(SDPBackend.MATH),torch.no_grad():
            payload = manual.read_selected_payload(torch,spec,entry)
            cfg = config_type(**payload['cfg'])
            manual.validate_cfg(cfg,entry['header'])
            with torch.device('cpu'):
                model = model_type(cfg)
            with method.weight_route(model,spec.arm) as route:
                method.load_routed_state(model,payload,spec.arm)
                payload = None
                model.clear_quant();model.eval();model.set_anneal(1.);model.freeze_quant()
                route.assert_active()
                assert manual.state_fingerprint(model)==entry['core_sha256']
                for saved in cases:
                    history = list(saved['metadata']['actual_prefix_ids'])
                    forced = saved['metadata']['generated_ids']
                    past,checks = None,[]
                    for position in range(max(POSITIONS)+1):
                        pending = history if past is None else history[-1:]
                        logits,past = model(torch.tensor([pending],device='cpu'),past_kv=past,use_cache=True)
                        if position in POSITIONS:
                            rebuilt,fresh = model(torch.tensor([history],device='cpu'),use_cache=True)
                            row = dict(position=position,history_tokens=len(history),
                                logits=compare_logits(logits[:,-1],rebuilt[:,-1],torch),
                                kv=compare_kv(past,fresh,torch),saved_next_id=forced[position])
                            row['cpu_argmax_matches_saved_gpu_id']=row['logits']['incremental_top1']==forced[position]
                            row['kv_all_close']=all(t['float_close'] for owner in row['kv'] for t in owner['tensors'])
                            checks.append(row)
                            print(json.dumps(dict(doc_id=saved['doc_id'],position=position,
                                history=len(history),logits_close=row['logits']['float_close'],
                                argmax_equal=row['logits']['argmax_equal'],kv_all_close=row['kv_all_close'])),flush=True)
                            del rebuilt,fresh
                        del logits
                        if position<max(POSITIONS):history.append(forced[position])
                    result['cases'].append(dict(doc_id=saved['doc_id'],checks=checks))
                    del past
                route.assert_active()
                result['core_sha256_after']=manual.state_fingerprint(model)
                assert result['core_sha256_after']==entry['core_sha256']
                checks=[r for c in result['cases'] for r in c['checks']]
                assert len(checks)==len(DOC_IDS)*len(POSITIONS)
                result['all_same_history_logits_close']=all(r['logits']['float_close'] for r in checks)
                result['all_same_history_argmax_equal']=all(r['logits']['argmax_equal'] for r in checks)
                result['all_same_history_kv_close']=all(r['kv_all_close'] for r in checks)
                code=0 if all(result[k] for k in ('all_same_history_logits_close','all_same_history_argmax_equal','all_same_history_kv_close')) else 8
                result['status']='SAVED_CPU_KV_MATCHED' if code==0 else 'SAVED_CPU_KV_NEGATIVE'
    except TimeoutError as exc:
        result.update(status='CPU_TIME_HOLD',error=str(exc));code=8
    except Exception as exc:
        result.update(status='ERROR',error_type=type(exc).__name__,error=str(exc));code=9
    finally:
        if model is not None:model.clear_quant()
        payload=model=None;gc.collect()
        result['input_bindings_unchanged']=all(digest(ROOT/p)==sha for p,sha in bindings.items())
        result['checkpoint_unchanged']=digest(ROOT/spec.checkpoint)==entry['checkpoint']['sha256']
        result['manifest_unchanged']=manual.canonical_sha(manual.verify_manifest())==manual.canonical_sha(manifest)
        result['own_sources_unchanged']=all(digest(ROOT/p)==sha for p,sha in sources.items())
        result['cuda_initialized']=torch.cuda.is_initialized()
        if not all(result[k] for k in ('input_bindings_unchanged','checkpoint_unchanged','manifest_unchanged','own_sources_unchanged')) or result['cuda_initialized']:
            result['status']='FINAL_BINDING_ERROR';code=9
        result.update(final_exit=code,wall_seconds=time.monotonic()-began,
            max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        OUTPUT.mkdir(exist_ok=False)
        with (OUTPUT/'report.json').open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
        print(json.dumps({k:result[k] for k in ('status','final_exit','wall_seconds','cuda_initialized')}),flush=True)
    return code


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only',action='store_true')
    group.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.check_only:
        cases,bindings=selected_inputs()
        print(json.dumps(dict(status='CPU_MODEL_NOT_RUN',doc_ids=[r['doc_id'] for r in cases],positions=POSITIONS,
            input_files=len(bindings),training=0,new_answers=0,gpu=0)))
    else:raise SystemExit(execute())
