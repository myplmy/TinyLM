#!/usr/bin/env python3
"""Opt-in four-update diagnostic; no CP save, teacher or default-route changes."""
from __future__ import annotations

import argparse
import copy
import gc
import itertools
import json
from pathlib import Path
import sys
import time
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_padding_gpu as old

TAG = 'p102a_streaming_head_v1_s1337'
NEW_SOURCES = ('scripts/diag_p102a_streaming_head.py', 'scripts/test_p102a_streaming_head.py',
               'tinylm/train/streaming_head.py', 'tinylm/train/alm.py')


def sources():
    return dict(sorted({**old.source_manifest(), **{p: old.digest(old.safe_path(p)) for p in NEW_SOURCES}}.items()))


class HeadCore:
    """Existing update loop seam. No optimizer/padding/normalization reimplementation."""
    def __init__(self, variant):
        if variant not in ('reference', 'streaming'):
            raise ValueError('registered head required')
        from tinylm.train import mtp_sft
        self.variant = variant
        self.pad_records = mtp_sft.pad_records
        self.normalized_loss = mtp_sft.normalized_loss

    def components(self, model, hidden, y, segments, *, horizons):
        if horizons:
            raise ValueError('main-head-only numerical gate')
        from tinylm.train import alm, streaming_head
        if self.variant == 'reference':
            nll, mask = alm.target_nll(model, hidden, y, chunk=64, checkpoint_head=True)
        else:
            nll, mask = streaming_head.target_nll(model, hidden, y, chunk=64, tile=4096)
        return {1: nll.sum()}, {1: int(mask.sum())}


def fresh_optimizers(engine, model):
    """Keep parameter-group loop references out of the long-lived run frame."""
    opts = engine.optimizers(model)
    for group in opts[0].param_groups:
        group['lr'] = 5e-5
    for group in opts[1].param_groups:
        group['lr'] = 2e-4
    return opts


def checked_cuda(model, guard):
    guard.check('immediately before CUDA model admission')
    return model.cuda()


def run(args, source_map):
    deadline = old.aware(args.deadline)
    if not old.utc_now() < deadline <= old.HARD_STOP or (deadline-old.utc_now()).total_seconds() < args.max_wall_sec:
        raise ValueError('explicit wall reservation must fit before16:30KST')
    if args.source_sha256 != old.identity(source_map):
        raise ValueError('source-only receipt changed')
    target = old.safe_path('test_result/evidence/' + TAG)
    if target.exists():
        raise ValueError('existing evidence namespace refused')
    # Refuse foreign processes BEFORE creating an execution receipt.
    admission = old.gpu_admission()
    target.mkdir()
    journal = old.Journal(target/'events.jsonl')
    began = time.perf_counter()
    guard = old.Guard(deadline, args.max_wall_sec)
    result = dict(schema='P102A_STREAMING_HEAD_GPU_V1', tag=TAG, sources=source_map,
        source_sha256=old.identity(source_map), started_at=old.utc_now().isoformat(),
        deadline=deadline.isoformat(), max_wall_sec=args.max_wall_sec, checkpoint_writes=0,
        production_adopted=False, official_cce_or_liger_kernel=False, quality_claim=False,
        tolerances=old.literal_tolerances(), gpu_admission=admission,
        status='STARTED', returncode=9, pairs={}, updates=[], assets_before=None,
        dataset_quality='KNOWN_V3_SUPERVISION_DEFECTS_NUMERICAL_CONTROL_ONLY_NOT_ADMITTED',
        timing_scope='ONE_UPDATE_PER_ARM_WITH_CPU_GRADIENT_CAPTURE_NOT_STEADY_STATE_SPEED')
    old.write_new(target/'admission.json', result)
    assets = None
    model = opts = template = None
    torch = None
    try:
        with old.wall_limit(args.max_wall_sec):
            from scripts import diag_p101a_sft_mtp as engine
            from scripts import diag_p101a_clean_bilingual as clean
            report = engine.corpus_report(old.safe_path(old.CORPUS))
            assets = old.asset_manifest(engine, report)
            result['assets_before'] = assets
            guard.check('before parent load')
            torch, template, cfg, tok, initial_sha = engine.load_runtime('parent_ntp')
            if cfg.cla_group != 2 or not cfg.grad_checkpoint or cfg.mtp_aux or cfg.train_repeat != 1.:
                raise ValueError('original parent CLA2/ckptON/R1/MTPoff required')
            if any(isinstance(m, torch.nn.Dropout) and m.p for m in template.modules()):
                raise ValueError('dropout0 required')
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            records = clean.encoded(old.safe_path(old.CORPUS), report, tok)
            if len(records['train']) != 22528 or len(records['val']) != 512:
                raise ValueError('full frozen corpus row identity required')
            groups = next(iter(engine.batches(records['train'], 0)))
            plan = old.update_plan(groups)
            initial = old.cpu_copy(template.state_dict())
            cls = type(template)
            pad = tok.token_to_id('<|pad|>')
            if pad is None: pad = tok.token_to_id('<pad>')
            if type(pad) is not int or not 0 <= pad < 32768:
                raise ValueError('original PAD ID required')
            result.update(initial_core_sha256=initial_sha, plan=plan,
                precision_policies=['fp32_math', 'bf16_eager'], seed=1337,
                optimizer=dict(factory='diag_p101a_sft_mtp.optimizers', adam_lr=5e-5,
                               muon_lr=2e-4,clip=1.,fresh_each_arm=True),
                parent_sha256=old.PARENT_SHA, tokenizer_sha256=old.TOKENIZER_SHA)
            del template
            template = None
            for precision in ('fp32_math', 'bf16_eager'):
                captures=[]
                for variant in ('reference', 'streaming'):
                    guard.check('before fresh model')
                    old.gpu_admission(torch)
                    guard.check('after external GPU admission query')
                    torch.manual_seed(1337)
                    model=cls(copy.deepcopy(cfg))
                    model.load_state_dict(initial, strict=True)
                    model.set_anneal(1.)
                    if engine.state_fingerprint(model) != initial_sha:
                        raise ValueError('fresh core changed')
                    model._padding_pad_id=pad
                    model.train(); model=checked_cuda(model,guard)
                    opts=fresh_optimizers(engine,model)
                    ids=[id(p) for o in opts for g in o.param_groups for p in g['params']]
                    if len(ids)!=len(set(ids)) or set(ids)!={id(p) for p in model.parameters() if p.requires_grad}:
                        raise ValueError('optimizer coverage/alias changed')
                    if any(o.state for o in opts): raise ValueError('fresh empty optimizer required')
                    torch.manual_seed(1337)
                    rng=old.rng_identity(torch)
                    update,gradients=old.one_update(torch,HeadCore(variant),model,opts,groups,plan,
                        'fixed1024',precision,guard,journal,len(result['updates']),0,'correctness',capture=True)
                    result['updates'].append(dict(update,head_policy=variant))
                    if (update['all_parameter_count'] != 157 or update['non_none_gradient_count'] != 157
                            or update['none_gradient_names'] or len(gradients) != 157
                            or any(g is None for g in gradients.values())):
                        raise ValueError('all157 actual gradients required; shared missing gradients cannot pass')
                    captures.append(dict(gradients=gradients,parameters=old.cpu_copy(dict(model.named_parameters())),
                        optimizer=old.optimizer_snapshot(torch,model,opts),initial_rng=rng,final_rng=old.rng_identity(torch)))
                    model_reference=weakref.ref(model)
                    parameter_references=[weakref.ref(p) for p in model.parameters()]
                    model.clear_quant()
                    del opts,model
                    opts=model=None
                    gc.collect()
                    if model_reference() is not None or any(ref() is not None for ref in parameter_references):
                        raise ValueError('prior model/parameters still referenced; no next model admission')
                    old.clear_runtime_workspace(torch)
                    torch.cuda.empty_cache(); torch.cuda.synchronize()
                    if torch.cuda.memory_allocated(): raise ValueError('live prior CUDA tensors; no co-residency')
                a,b=captures
                if a['initial_rng']!=b['initial_rng'] or a['final_rng']!=b['final_rng']:
                    raise ValueError('paired initial/final RNG differs')
                updates=result['updates'][-2:];t=result['tolerances']
                comparisons=dict(
                    loss=old.scalar_difference(updates[0]['loss'],updates[1]['loss'],t['loss_and_norm']),
                    preclip_norm=old.scalar_difference(updates[0]['preclip_norm'],updates[1]['preclip_norm'],t['loss_and_norm']),
                    gradients=old.tensor_table(torch,a['gradients'],b['gradients'],t['gradients_and_update']),
                    updated_parameters=old.tensor_table(torch,a['parameters'],b['parameters'],t['gradients_and_update']),
                    optimizer_state=old.tensor_table(torch,a['optimizer'],b['optimizer'],t['gradients_and_update']))
                result['pairs'][precision]=dict(comparisons=comparisons,
                    close=all(x['close'] for x in comparisons.values()),initial_rng=a['initial_rng'],final_rng=a['final_rng'],
                    tied_scope='ALL_PARAMETERS_INCLUDE_SUMMED_INPUT_AND_OUTPUT_EMB_AND_PROJECTION_GRADIENTS')
                del captures,a,b
            result['all_pairs_close']=all(x['close'] for x in result['pairs'].values())
            result['status']='NUMERICAL_PASS_NOT_ADOPTED' if result['all_pairs_close'] else 'VALID_NUMERICAL_NEGATIVE_NOT_ADOPTED'
            result['returncode']=0 if result['all_pairs_close'] else 8
    except Exception as error:
        result.update(status='ERROR_PARTIAL_EVIDENCE',returncode=9,error_type=type(error).__name__,error=str(error))
    finally:
        cleanup_errors=[]
        try:
            if model is not None: model.clear_quant()
        except Exception as error:
            cleanup_errors.append('model clear: '+repr(error))
        model=opts=template=None
        gc.collect()
        if torch is not None and torch.cuda.is_initialized():
            try:
                torch.cuda.synchronize(); old.clear_runtime_workspace(torch); torch.cuda.empty_cache()
                result['final_allocated_bytes']=torch.cuda.memory_allocated()
                if result['final_allocated_bytes']: cleanup_errors.append('live CUDA allocation at final close')
            except Exception as error:
                cleanup_errors.append('CUDA cleanup: '+repr(error))
        try:
            result['sources_unchanged']=sources()==source_map
        except Exception as error:
            result['sources_unchanged']=None
            cleanup_errors.append('source reread: '+repr(error))
        if assets is not None:
            try:
                result['assets_after']={p:old.digest(old.safe_path(p)) for p in assets}
                result['assets_unchanged']=result['assets_after']==assets
            except Exception as error:
                result['assets_unchanged']=None
                cleanup_errors.append('asset reread: '+repr(error))
        if cleanup_errors:
            result.update(cleanup_errors=cleanup_errors,status='ERROR_CLEANUP_OR_FINAL_AUDIT',returncode=9)
        elif not result['sources_unchanged'] or (assets is not None and not result['assets_unchanged']):
            result.update(status='ERROR_SOURCE_OR_ASSET_MUTATION',returncode=9)
        result.update(finished_at=old.utc_now().isoformat(),wall_seconds=time.perf_counter()-began)
        journal.close()
        old.write_new(target/'report.json',result)
    print(json.dumps({k:result[k] for k in ('schema','status','returncode','wall_seconds','checkpoint_writes','sources_unchanged')},ensure_ascii=False))
    return result['returncode']


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--execute',action='store_true')
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--source-sha256')
    p.add_argument('--deadline',default='2026-10-23T16:30:00+09:00')
    p.add_argument('--max-wall-sec',type=int,default=600)
    a=p.parse_args(argv)
    if not 60<=a.max_wall_sec<=1200: p.error('wall bound must be60..1200')
    s=sources()
    if a.check_only:
        print(json.dumps(dict(tag=TAG,source_sha256=old.identity(s),source_count=len(s),model_calls=0)));return 0
    if not a.execute: p.error('explicit --execute or source-only --check-only required')
    return run(a,s)


if __name__=='__main__':
    raise SystemExit(main())
