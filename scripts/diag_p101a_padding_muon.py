#!/usr/bin/env python3
"""Nov13 PAD-specific gradient recapture using closed PAD/NS primitives.

Old execution authorities are not called or modified. Two temporary updates
are numerical diagnostics of known-defective V3, not new training or quality.
"""
import argparse
import copy
from datetime import datetime, timezone
import gc
import itertools
import json
from pathlib import Path
import subprocess
import time
import traceback
import weakref
from scripts import diag_p101a_padding_gpu as pad
from scripts import diag_p102a_head_muon_trace as trace

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p101a_padding_muon_v1_20261113'
BASE = ROOT/'test_result/evidence'/TAG
DEADLINE = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)
PLAN = 'test_plan/P101A_M0-U2-QK-MTP-기능계약.md'
SOURCES = ('scripts/diag_p101a_padding_muon.py', 'scripts/test_p101a_padding_muon.py')


class Budget:
    def __init__(self, seconds=3600): self.start, self.seconds, self.deadline = time.monotonic(), seconds, DEADLINE
    def check(self, stage=''):
        if time.monotonic()-self.start > self.seconds or (self.deadline-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('Nov13 authority/phase reserve: '+stage)


def validate_policy(policy):
    if policy not in ('fixed1024', 'crop128'): raise ValueError('exact paired PAD policy required')
    return policy


def admission(torch=None):
    from scripts import interactive_research_infer as manual
    point = manual.require_idle_gpu()
    reply = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                           check=True, capture_output=True, text=True, timeout=10)
    if not reply.stdout.strip().isdigit() or int(reply.stdout.strip()) < 8192:
        raise MemoryError('new PAD trace requires at least8192MiB point free')
    if torch is not None and torch.cuda.is_initialized() and torch.cuda.memory_allocated():
        raise RuntimeError('previous owned GPU allocation remains')
    return dict(point, free_mib=int(reply.stdout.strip()), minimum_free_mib=8192,
                basis='prior actual FP32 MATH reserved4110MiB plus separate trace/replay reserve; not old14000 policy')


def source_map():
    values = trace.sources()
    values.update({name: pad.digest(ROOT/name) for name in SOURCES})
    values['scripts/interactive_research_infer.py'] = pad.digest(ROOT/'scripts/interactive_research_infer.py')
    return dict(sorted(values.items()))


def prepare():
    if BASE.exists(): raise FileExistsError('fresh PAD namespace required')
    if datetime.now(timezone.utc) >= DEADLINE: raise TimeoutError('Nov13 authority expired')
    report_path = ROOT/pad.CORPUS/'report.json'
    if pad.digest(report_path) != pad.CORPUS_SHA: raise ValueError('original V3 report changed')
    from scripts import diag_p101a_sft_mtp as engine
    report = engine.corpus_report(ROOT/pad.CORPUS)
    assets = pad.asset_manifest(engine, report)
    sources = source_map(); BASE.mkdir(parents=True)
    (BASE/'initial_plan.txt').write_bytes((ROOT/PLAN).read_bytes())
    pad.write_new(BASE/'profile.json', dict(schema='P101A_PADDING_MUON_V1', tag=TAG, authority_directive=115,
        deadline=DEADLINE.isoformat(), sources=sources, assets=assets,
        plan_snapshot_sha256=pad.digest(BASE/'initial_plan.txt'), policies=list(pad.POLICIES),
        tolerances=pad.literal_tolerances(), previous_correctness_sha256=pad.digest(
            ROOT/'test_result/evidence/p101a_padding_gpu_v1_s1337_workspace_v2/correctness/report.json'),
        original_corpus_quality='KNOWN_V3_SUPERVISION_DEFECTS_NOT_ADMITTED',
        temporary_updates=2, checkpoint_writes=0, quality_claim=False, compiled_cost_not_run=True,
        max_phase_seconds=3600, minimum_free_mib=8192))
    print('[PREPARED] '+TAG, flush=True)


def verify():
    p = json.loads((BASE/'profile.json').read_text())
    if p['schema']!='P101A_PADDING_MUON_V1' or p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat():
        raise ValueError('exact authority mismatch')
    if p['sources']!=source_map() or p['tolerances']!=pad.literal_tolerances():
        raise ValueError('source or original numerical rule changed')
    for name, sha in p['assets'].items():
        if pad.digest(ROOT/name)!=sha: raise ValueError('exact asset changed: '+name)
    if pad.digest(BASE/'initial_plan.txt')!=p['plan_snapshot_sha256']: raise ValueError('frozen plan changed')
    return p


def capture_arm(torch, engine, core, muon, cls, cfg, initial, initial_sha, pad_id, groups, plan, policy, budget, journal):
    validate_policy(policy); model=opts=proxies=capture=observer=parameters=None
    try:
        budget.check('before model'); point=admission(torch)
        torch.manual_seed(1337); model=cls(copy.deepcopy(cfg)); model.load_state_dict(initial, strict=True)
        model.set_anneal(1.)
        if engine.state_fingerprint(model)!=initial_sha: raise ValueError('fresh CPU initial state changed')
        model._padding_pad_id=pad_id; model.train(); model=model.cuda(); opts=engine.optimizers(model)
        for group in opts[0].param_groups: group['lr']=5e-5
        for group in opts[1].param_groups: group['lr']=2e-4
        parameters=dict(model.named_parameters()); names={id(p):n for n,p in parameters.items()}
        owned=[id(p) for opt in opts for group in opt.param_groups for p in group['params']]
        if len(owned)!=len(set(owned)) or set(owned)!={id(p) for p in model.parameters() if p.requires_grad}:
            raise ValueError('complete unique optimizer ownership required')
        options=trace.matrix_options(opts[1],names)
        capture=trace.PostClipCapture(parameters)
        observer=trace.NSObserver(torch,muon._newton_schulz,tuple(options),guard=budget)
        proxies=(trace.OptimizerProxy(opts[0],capture),trace.OptimizerProxy(opts[1],capture,
                    step=trace.private_muon_step(torch,opts[1],observer)))
        torch.manual_seed(1337)
        update, raw=pad.one_update(torch,core,model,proxies,groups,plan,policy,'fp32_math',budget,journal,
                                  0 if policy=='fixed1024' else 1,0,'PAD_specific_actual_trace',capture=True)
        observer.finish()
        if len(raw)!=157 or any(g is None for g in raw.values()) or capture.values is None:
            raise ValueError('all157 actual raw/clipped gradients required')
        updated={name:trace.cpu_clone(parameters[name]) for name in options}
        buffers={names[id(p)]:trace.cpu_clone(opts[1].state[p]['buf']) for group in opts[1].param_groups for p in group['params']}
        if any(not torch.equal(buffers[n],capture.values[n]) for n in options):
            raise ValueError('fresh momentum differs from actual postclip gradient')
        return dict(raw=raw,clipped=capture.values,ns_input=observer.inputs,ns_output=observer.outputs,
            ns_metadata=observer.metadata,updated=updated,buffers=buffers,options=options,
            all_updated=pad.cpu_copy(parameters),optimizer=pad.optimizer_snapshot(torch,model,opts),
            update=update,admission=point,weak_model=weakref.ref(model),
            weak_parameters=[weakref.ref(p) for p in parameters.values()])
    finally:
        if model is not None: model.clear_quant()
        model=opts=proxies=capture=observer=parameters=None


def run():
    p=verify();budget=Budget();budget.check('start');out=BASE/'actual'
    if out.exists():raise FileExistsError('write-once actual output')
    out.mkdir();journal=pad.Journal(out/'events.jsonl')
    report=dict(schema=p['schema'],tag=TAG,status='RUNNING',authority_directive=115,
        checkpoint_writes=0,quality_claim=False,temporary_updates=0,production_adopted=False,
        corpus_quality=p['original_corpus_quality'],old_execution_main_calls=0,arms=[])
    failure=None;torch=None;initial=template=model=a=b=None
    try:
        from scripts import interactive_research_infer as manual
        manual.validate_import_environment();admission()
        import torch
        from scripts import diag_p101a_sft_mtp as engine
        from scripts import diag_p101a_clean_bilingual as clean
        from tinylm.train import mtp_sft as core
        from tinylm.train import muon
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch,template,cfg,tok,initial_sha=engine.load_runtime('parent_ntp')
        if cfg.cla_group!=2 or not cfg.grad_checkpoint or cfg.mtp_aux or cfg.train_repeat!=1.:
            raise ValueError('original CLA2/checkpoint/R1/NTP geometry required')
        report['memory_plan']=trace.memory_plan(template,muon)
        corpus=engine.corpus_report(ROOT/pad.CORPUS); records=clean.encoded(ROOT/pad.CORPUS,corpus,tok)
        if len(records['train'])!=22528 or len(records['val'])!=512:raise ValueError('original full corpus geometry changed')
        groups=next(iter(engine.batches(records['train'],0)));plan=pad.update_plan(groups)
        old=json.loads((ROOT/'test_result/evidence/p101a_padding_gpu_v1_s1337_workspace_v2/correctness/report.json').read_text())
        if initial_sha!=old['initial_core_sha256'] or plan!=old['plans'][0]:raise ValueError('historical exact parent/group changed')
        report.update(initial_core_sha256=initial_sha,input_plan=plan,tolerances=p['tolerances'])
        initial=pad.cpu_copy(template.state_dict());cls=type(template);template=None
        pad_id=tok.token_to_id('<|pad|>')
        if pad_id is None:pad_id=tok.token_to_id('<pad>')
        captures=[]
        for policy in pad.POLICIES:
            capture=capture_arm(torch,engine,core,muon,cls,cfg,initial,initial_sha,pad_id,groups,plan,policy,budget,journal)
            report['arms'].append(dict(policy=policy,update=capture['update'],admission=capture['admission']))
            report['temporary_updates']+=1;gc.collect();trace.release_cuda(torch)
            if capture['weak_model']() is not None or any(ref() is not None for ref in capture['weak_parameters']):
                raise RuntimeError('actual arm objects not released')
            capture.pop('weak_model');capture.pop('weak_parameters');captures.append(capture)
            print('[PAD_CAPTURE] '+policy,flush=True)
        a,b=captures;tol=p['tolerances']['gradients_and_update']
        report['paired']={name:pad.tensor_table(torch,a[left],b[left],tol) for name,left in
            (('raw_gradients','raw'),('clipped_gradients','clipped'),('all_updated_parameters','all_updated'),
             ('optimizer_state','optimizer'),('ns_inputs','ns_input'),('ns_outputs','ns_output'))}
        report['replay']=trace.replay_all(torch,muon,initial,a,b,tol,budget,journal,device='cuda')
        report['replay_axis']='reference=FIXED1024;streaming=CROP128;no head method change'
        report['status']='TECHNICAL_COMPLETE_NUMERICAL_JUDGMENT_SEPARATE'
        captures=capture=a=b=initial=None;gc.collect();trace.release_cuda(torch)
        verify();report['sources_and_assets_unchanged']=True
    except BaseException as exc:
        report['status']='ERROR';report['error']=repr(exc);traceback.print_exc()
        failure=RuntimeError('Original PAD error: '+repr(exc))
    finally:
        captures=capture=a=b=initial=template=model=None;gc.collect()
        if torch is not None and torch.cuda.is_initialized():
            try:
                trace.release_cuda(torch)
                report['final_allocated_bytes']=torch.cuda.memory_allocated();report['final_reserved_bytes']=torch.cuda.memory_reserved()
            except BaseException as exc:
                report['cleanup_error']=repr(exc);report['status']='ERROR'
                if failure is None:failure=RuntimeError('PAD cleanup: '+repr(exc))
        journal.close();report['seconds']=time.monotonic()-budget.start
        pad.write_new(out/'report.json',report)
    if failure is not None:raise failure
    print('[COMPLETE] '+json.dumps(dict(status=report['status'],seconds=report['seconds'],matrices=report['replay']['matrix_count'])),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','run']);args=parser.parse_args()
    (prepare if args.phase=='prepare' else run)()


if __name__=='__main__':main()
