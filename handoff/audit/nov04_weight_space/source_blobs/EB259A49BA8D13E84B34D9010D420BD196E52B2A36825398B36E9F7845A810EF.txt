#!/usr/bin/env python3
"""P108 supervised local correction: prepare/capture/search/confirm.

Uses an already fully trained, immutable checkpoint. Gold labels supervise the
calibration; optimizer updates are zero. This is not unsupervised discovery or
a new full-training/general-intelligence result.
"""
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import hashlib
import json
import os
import time

from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as surgery
from scripts import p108_balanced_practice as practice
from scripts import p108_local_linear as local
from scripts.p108_signed_control import row_sign_control,control_receipt
from scripts.p106b_shards import ShardWriter,verify as verify_shards

ROOT=common.ROOT
TAG,MODEL='p108j_v1_20261104','new595-broad-q'
BASE=ROOT/'test_result/evidence'/TAG/MODEL
RUNTIME=ROOT/'runs/isolated'/TAG/MODEL
SOURCES=('scripts/p108_weight_space.py','scripts/diag_p108_weight_space.py',
         'scripts/p108_signed_control.py','scripts/p108_balanced_practice.py',
         'scripts/p108_local_linear.py','scripts/diag_p108_local_linear.py',
         'scripts/test_p108_local_linear.py')


def token_contract(tok,question,expected):
    from tinylm.chat.serialize import serialize
    prompt=serialize(dict(messages=manual.prompt_messages(question)),'chatml',add_generation_prompt=True)
    prefix=tok.encode(prompt).ids
    body=tok.encode(expected).ids
    if (not body or any(t in (2,3,4) for t in body)
            or tok.decode(body,skip_special_tokens=False)!=expected or len(prefix)+len(body)>1024):
        raise ValueError('exact gold-body tokenization or context contract differs')
    return prefix+body,list(range(len(prefix)-1,len(prefix)+len(body))),body+[4]


def constant_baseline(rows):
    counts=defaultdict(Counter)
    for row in rows:
        if row['split']=='calib':counts[(row['family'],row['language'])][row['expected']]+=1
    pred={key:sorted(value,key=lambda x:(-value[x],x))[0] for key,value in counts.items()}
    return {split:dict(items=len(group),exact=sum(r['expected']==pred[(r['family'],r['language'])] for r in group))
            for split in ('dev','test') for group in [[r for r in rows if r['split']==split]]}


def prepare():
    if BASE.exists() or RUNTIME.exists():raise FileExistsError('fresh local-repair namespace required')
    rows=practice.make_data()
    data_report=practice.audit_data(rows)
    manifest=manual.verify_manifest()
    tok=manual.local_tokenizer(manifest)
    tokens=0
    for row in rows:
        _,_,targets=token_contract(tok,row['question'],row['expected'])
        if row['split']=='calib':tokens+=len(targets)
    if not 1<=tokens<=1024:raise ValueError('calibration target token count outside declared1..1024 budget')
    for i,q in enumerate(common.OPEN):
        rows.append(dict(id=f'open_seen_{i:03d}',split='open_seen',family='seen_dialogue_regression',
            language='ko' if i<8 else 'en',question=q,expected=None,protected=i==15,
            source_group=f'PREVIOUSLY_SEEN_DIALOGUE_{i}',rule=None))
    reservation=TAG+'/'+MODEL
    baseline=(ROOT/'docs/EXPERIMENT_BASELINES.md').read_text(encoding='utf-8')
    if reservation not in baseline:raise ValueError('tag must be reserved in baselines BEFORE first GPU')
    plan=(ROOT/common.PLAN_PATH).read_bytes()
    if any(s.encode() not in plan for s in ('Stage5aW','Stage5bW','Stage5cW','Stage5dW')):
        raise ValueError('the new stages must exist before execution')
    common.write_json(BASE/'data.json',dict(schema='P108_LOCAL_RULE_DATA_V1',rows=rows,audit=data_report,
        dev_test_baselines=constant_baseline([r for r in rows if r['split']!='open_seen']),
        baseline_privilege='KNOWN_FAMILY_AND_LANGUAGE_NOT_A_FAIR_OFFICIAL_MODEL_RANKING'))
    with (BASE/'initial_plan.md').open('xb') as stream:stream.write(plan)
    sources=manual.required_source_pins()
    sources.update({name:manual.file_sha(ROOT/name) for name in SOURCES})
    profile=dict(schema='P108_LOCAL_LINEAR_V1',authority_directive=107,deadline=common.DEADLINE.isoformat(),
        model=MODEL,tag=TAG,sources=sources,data_sha256=manual.file_sha(BASE/'data.json'),
        initial_plan_sha256=manual.file_sha(BASE/'initial_plan.md'),
        manual_manifest_sha256=manual.canonical_sha(manifest),calibration_rows=128,
        calibration_target_tokens_expected=tokens,layer=13,nominal_rank=16,ridge=.01,
        target_margin=1.,max_margin_gap=10.,relative_caps=[.0025,.01,.04],
        random_seeds=[17,29,43],max_new=96,max_phase_seconds=3600,
        gradient_fd_examples=4,gradient_fd_epsilon=1.,gradient_fd_relative_tolerance=.1,
        supervised_calibration=True,optimizer_updates=0,new_300m_training=False,
        precision='FP32_MATH',cache_generation=True,mtp=False,recurrence='R1',
        score='VERBATIM_EXCEPT_OUTER_SPACE_OR_STRICT_SINGLE_STRING_KEY_JSON',
        original_checkpoint_writes=0,source_reservation=reservation)
    common.write_json(BASE/'profile.json',profile)
    print('[PREPARED] '+json.dumps(dict(rows=len(rows),calibration_target_tokens=tokens,
        data_audit=data_report,profile_sha256=manual.file_sha(BASE/'profile.json')),ensure_ascii=False),flush=True)


def verify():
    profile=common.read_json(BASE/'profile.json')
    if (profile['schema']!='P108_LOCAL_LINEAR_V1' or profile['authority_directive']!=107
            or profile['deadline']!=common.DEADLINE.isoformat() or profile['model']!=MODEL):
        raise ValueError('local repair authority/profile differs')
    for name,sha in profile['sources'].items():
        if manual.file_sha(manual.owned_path(name))!=sha:raise ValueError('source changed: '+name)
    for name,key in (('data.json','data_sha256'),('initial_plan.md','initial_plan_sha256')):
        if manual.file_sha(BASE/name)!=profile[key]:raise ValueError('frozen input changed')
    if manual.canonical_sha(manual.verify_manifest())!=profile['manual_manifest_sha256']:
        raise ValueError('completed checkpoint binding changed')
    return profile


def origin(active):
    return {key:active[key] for key in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256','precision')}


def gold_features(active,row,layer):
    torch=active['torch']
    from torch.nn.attention import sdpa_kernel,SDPBackend
    ids,positions,targets=token_contract(active['tokenizer'],row['question'],row['expected'])
    tensor=torch.tensor([ids],device='cuda',dtype=torch.long)
    at=torch.tensor(positions,device='cuda',dtype=torch.long)
    gold=torch.tensor(targets,device='cuda',dtype=torch.long)
    module=dict(surgery.down_modules(active['model']))[layer]
    captured={}
    def hook(_m,args,out):
        if captured:raise RuntimeError('unexpected second last-down visit')
        captured.update(keys=args[0].detach(),output=out)
    handle=module.register_forward_hook(hook)
    try:
        with torch.enable_grad(),sdpa_kernel(SDPBackend.MATH):
            logits=active['model'](tensor)
            selected=logits[0].index_select(0,at)
            best=selected.detach().topk(2,dim=-1).indices
            other=torch.where(best[:,0]==gold,best[:,1],best[:,0])
            arange=torch.arange(len(targets),device='cuda')
            margins=selected[arange,gold]-selected[arange,other]
            loss=float(torch.nn.functional.cross_entropy(selected.detach(),gold,reduction='sum'))
            gradient=torch.autograd.grad(margins.sum(),captured['output'])[0]
            inactive=torch.ones(len(ids),device='cuda',dtype=torch.bool);inactive[at]=False
            outside=float(gradient[0,inactive].abs().max()) if bool(inactive.any()) else 0.
            if outside!=0:raise RuntimeError('post-last-down margin unexpectedly mixes token positions')
            key=captured['keys'][0].index_select(0,at).detach().float().cpu()
            g=gradient[0].index_select(0,at).detach().float().cpu()
            margin=margins.detach().float().cpu()
            detail=dict(id=row['id'],targets=len(targets),eot_targets=1,xent_sum=loss,
                gold_argmax=int((selected.detach().argmax(-1)==gold).sum()),
                eot_argmax=bool(selected.detach()[-1].argmax()==4),inactive_gradient_max_abs=outside)
            probe=dict(ids=ids,position=positions[0],target=targets[0],other=int(other[0]),
                       direction=g[0],margin=float(margin[0]))
        if any(p.grad is not None for p in active['model'].parameters()):
            raise RuntimeError('calibration unexpectedly accumulated parameter gradients')
        if not torch.isfinite(g).all():raise ValueError('nonfinite activation gradient')
        return key,g,margin,detail,probe
    finally:
        handle.remove()
        captured.clear()


def gradient_probe(active,probe,profile):
    torch=active['torch']
    from torch.nn.attention import sdpa_kernel,SDPBackend
    direction=surgery.unit_direction(probe['direction']).to(device='cuda')
    module=dict(surgery.down_modules(active['model']))[profile['layer']]
    tensor=torch.tensor([probe['ids']],device='cuda',dtype=torch.long)
    epsilon=profile['gradient_fd_epsilon']
    values=[]
    for sign in (1.,-1.):
        def patch(_m,_args,out):
            result=out.clone()
            result[0,probe['position']]+=sign*epsilon*direction
            return result
        handle=module.register_forward_hook(patch)
        try:
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                logits=active['model'](tensor)
                row=logits[0,probe['position']]
                values.append(float(row[probe['target']]-row[probe['other']]))
        finally:handle.remove()
    measured=(values[0]-values[1])/(2*epsilon)
    predicted=float(probe['direction'].norm())
    error=abs(measured-predicted)
    rounding=256*torch.finfo(torch.float32).eps*max(1.,abs(probe['margin']),*map(abs,values))/(2*epsilon)
    relative=error/max(abs(measured),abs(predicted),1e-12)
    valid=measured>0 and (relative<=profile['gradient_fd_relative_tolerance'] or error<=rounding)
    if not valid:raise ValueError('actual activation gradient failed the predeclared finite-difference gate')
    return dict(measured=measured,predicted=predicted,relative_error=relative,
                absolute_error=error,fp32_rounding_allowance=rounding,epsilon=epsilon,valid=valid)


def capture():
    profile=verify();budget=phase_budget(profile,'capture');budget.check()
    directory=BASE/'capture'
    directory.mkdir(exist_ok=False)
    if RUNTIME.exists():raise FileExistsError('runtime feature namespace exists')
    records=[];probes=[];keys=[];gradients=[];margins=[]
    rows=[r for r in common.read_json(BASE/'data.json')['rows'] if r['split']=='calib']
    with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
        torch=active['torch'];torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
        total=torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(min(1.,6*1024**3/total))
        original=origin(active)
        for i,row in enumerate(rows):
            budget.check()
            k,g,m,record,probe=gold_features(active,row,profile['layer'])
            if i<profile['gradient_fd_examples']:probes.append(dict(id=row['id'],**gradient_probe(active,probe,profile)))
            keys.append(k);gradients.append(g);margins.append(m);records.append(record)
            if (i+1)%16==0:print(f'[CAPTURE] {i+1}/{len(rows)} examples',flush=True)
        k=torch.cat(keys);g=torch.cat(gradients);m=torch.cat(margins)
        if k.shape[0]!=profile['calibration_target_tokens_expected']:raise ValueError('supervision token count differs')
        values,target_report=local.margin_targets(g,m,target_margin=profile['target_margin'],max_gap=profile['max_margin_gap'])
        fit_start=time.monotonic()
        factors,fit=local.ridge_factors(k,values,ridge=profile['ridge'],rank=profile['nominal_rank'])
        fit['cpu_seconds']=time.monotonic()-fit_start
        memory=dict(allocated_peak_bytes=torch.cuda.max_memory_allocated(),reserved_peak_bytes=torch.cuda.max_memory_reserved())
        RUNTIME.mkdir(parents=True,exist_ok=False)
        with (RUNTIME/'features_factors.pt').open('xb') as stream:
            torch.save(dict(keys=k,values=values.float(),gradients=g,margins=m,factors=factors),stream)
        if (RUNTIME/'features_factors.pt').stat().st_size>=20_000_000:raise ValueError('feature packet exceeds20MB')
    verify()
    report=dict(schema='P108_LOCAL_CAPTURE_V1',status='TECHNICAL_COMPLETE',origin=original,
        profile_sha256=manual.file_sha(BASE/'profile.json'),supervised_calibration=True,
        optimizer_updates=0,calibration_rows=len(rows),calibration_target_tokens=k.shape[0],
        original_tf_xent_sum=sum(r['xent_sum'] for r in records),gradient_probes=probes,
        rows=records,target_report=target_report,fit=fit,vram=memory,original_core_unchanged=True,
        packet_sha256=manual.file_sha(RUNTIME/'features_factors.pt'),wall_seconds=time.monotonic()-budget.start)
    common.write_json(directory/'report.json',report)
    print('[FINAL] '+json.dumps({key:report[key] for key in ('status','calibration_rows','calibration_target_tokens','fit','vram','wall_seconds')}),flush=True)


def load_packet(torch):
    report=common.read_json(BASE/'capture/report.json')
    path=RUNTIME/'features_factors.pt'
    if (report['status']!='TECHNICAL_COMPLETE' or manual.file_sha(path)!=report['packet_sha256']
            or report['profile_sha256']!=manual.file_sha(BASE/'profile.json')):
        raise ValueError('sealed calibration packet differs')
    with path.open('rb') as stream:packet=torch.load(stream,map_location='cpu',weights_only=True)
    if manual.file_sha(path)!=report['packet_sha256']:raise ValueError('packet changed while loading')
    return packet,report


def teacher_forced(active,rows,profile,budget):
    torch=active['torch']
    from torch.nn.attention import sdpa_kernel,SDPBackend
    result=dict(rows=len(rows),targets=0,xent_sum=0.,argmax=0,eot_targets=0,eot_argmax=0)
    for row in rows:
        budget.check()
        ids,positions,targets=token_contract(active['tokenizer'],row['question'],row['expected'])
        with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            logits=active['model'](torch.tensor([ids],device='cuda',dtype=torch.long))
            selected=logits[0,positions]
            gold=torch.tensor(targets,device='cuda',dtype=torch.long)
            result['xent_sum']+=float(torch.nn.functional.cross_entropy(selected,gold,reduction='sum'))
            result['argmax']+=int((selected.argmax(-1)==gold).sum())
            result['eot_argmax']+=int(selected[-1].argmax()==4)
        result['targets']+=len(targets);result['eot_targets']+=1
    result['mean_xent']=result['xent_sum']/result['targets']
    return result


def score(row):
    return (row['exact'],row['protected_exact'],-row['empty'],-row['question_echoes'],
            -row['loop_indicators'],-row.get('delta_norm',0.))


def execute_evaluation(phase):
    profile=verify();budget=phase_budget(profile,phase);budget.check()
    directory=BASE/phase
    if directory.exists():raise FileExistsError('evaluation phase is write-once')
    raw_writer=ShardWriter(directory,'answers',limit=3_000_000)
    writer=practice.StrictWriter(raw_writer)
    rows=common.read_json(BASE/'data.json')['rows']
    final=dict(schema='P108_LOCAL_EVAL_V1',phase=phase,profile_sha256=manual.file_sha(BASE/'profile.json'),
        supervised_calibration=True,optimizer_updates=0,variants=[],
        scientific_scope='LIMITED_POSTHOC_CORRECTION_NOT_NEW_FULL_TRAINING_OR_OFFICIAL_BENCHMARK')
    with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
        torch=active['torch'];torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
        torch.cuda.set_per_process_memory_fraction(min(1.,6*1024**3/torch.cuda.get_device_properties(0).total_memory))
        packet,capture_report=load_packet(torch)
        if capture_report['origin']!=origin(active):raise ValueError('calibration and current completed model differ')
        final['origin']=origin(active)
        final['calibration_target_tokens']=capture_report['calibration_target_tokens']
        module=dict(surgery.down_modules(active['model']))[profile['layer']]
        if phase=='search':
            selected=[r for r in rows if r['split']=='dev']
            _,summary=common.evaluate(active,selected,writer,'original_dev',budget,profile['max_new'])
            final['variants'].append(dict(name='original_dev',**summary,
                teacher_forced_dev=teacher_forced(active,selected,profile,budget)))
            seen={};candidates=[]
            for cap in profile['relative_caps']:
                delta,details=local.bounded_delta(packet['factors'],module._wq.detach(),cap)
                digest=surgery.tensor_sha(delta)
                if digest in seen:
                    final.setdefault('duplicate_physical_edits_not_executed',[]).append(dict(cap=cap,of=seen[digest]))
                    continue
                name=f'cap_{cap}';seen[digest]=name
                with surgery.edit_weights(active['model'],active['route'],[(profile['layer'],delta)],'effective') as receipts:
                    if receipts[0]['effective_changed']==0:
                        final.setdefault('zero_realized_not_executed',[]).append(dict(cap=cap,receipts=receipts))
                        continue
                    _,summary=common.evaluate(active,selected,writer,name,budget,profile['max_new'])
                    tf=teacher_forced(active,selected,profile,budget)
                row=dict(name=name,**summary,relative_cap=cap,budget=details,receipts=receipts,
                         delta_norm=receipts[0]['effective_delta_norm'],teacher_forced_dev=tf,
                         requested_delta_sha256=digest)
                candidates.append(row);final['variants'].append(row)
                delta=None
            if not candidates:raise ValueError('no nonzero realized edit; no quality comparison')
            winner=max(candidates,key=score)
            final['selected']=dict(name=winner['name'],relative_cap=winner['relative_cap'],
                requested_delta_sha256=winner['requested_delta_sha256'],selection_split='DEV_ONLY',
                criterion='STRICT_EXACT_PROTECTED_EMPTY_ECHO_LOOP_DELTA')
        else:
            search=common.read_json(BASE/'search/report.json')
            if search['status']!='TECHNICAL_COMPLETE':raise ValueError('sealed selection is missing')
            winner=search['selected'];final['selected']=winner
            final['search_sha256']=manual.file_sha(BASE/'search/report.json')
            selected=[r for r in rows if r['split'] in ('test','open_seen')]
            _,summary=common.evaluate(active,selected,writer,'original_test',budget,profile['max_new'])
            final['variants'].append(dict(name='original_test',**summary))
            delta,details=local.bounded_delta(packet['factors'],module._wq.detach(),winner['relative_cap'])
            if surgery.tensor_sha(delta)!=winner['requested_delta_sha256']:raise ValueError('selected physical delta differs')
            before=module._wq.detach().clone()
            with surgery.edit_weights(active['model'],active['route'],[(profile['layer'],delta)],'effective') as receipts:
                _,summary=common.evaluate(active,selected,writer,'targeted_test',budget,profile['max_new'])
                actual=module._wq.detach().clone()-before
            final['variants'].append(dict(name='targeted_test',**summary,budget=details,receipts=receipts))
            for seed in profile['random_seeds']:
                control=row_sign_control(actual,seed)
                matching=control_receipt(actual,control)
                if not matching['same_support'] or not matching['same_absolute_coefficients']:
                    raise RuntimeError('actual-delta control mismatch')
                with surgery.edit_weights(active['model'],active['route'],[(profile['layer'],control)],'effective') as receipts:
                    current=module._wq.detach()-before
                    error=float((current-control).abs().max())
                    bound=2*torch.finfo(control.dtype).eps*float(before.abs().max()+control.abs().max())
                    if error>bound:raise RuntimeError('control realization exceeds FP32 allowance')
                    _,summary=common.evaluate(active,selected,writer,f'row_sign_{seed}_test',budget,profile['max_new'])
                final['variants'].append(dict(name=f'row_sign_{seed}_test',**summary,receipts=receipts,
                    matching=matching,realized_max_abs=error,rounding_bound=bound))
                control=current=None
            actual=before=delta=None
        final['vram']=dict(allocated_peak_bytes=torch.cuda.max_memory_allocated(),reserved_peak_bytes=torch.cuda.max_memory_reserved())
        module=packet=None
    verify()
    manifest=raw_writer.close(lineage=dict(profile_sha256=final['profile_sha256'],
        checkpoint_sha256=final['origin']['checkpoint_sha256'],supervised_calibration=True))
    verify_shards(directory,manifest)
    final.update(status='TECHNICAL_COMPLETE',original_core_unchanged=True,
        answers_manifest_sha256=manual.file_sha(directory/'answers_shards_manifest.json'),
        wall_seconds=time.monotonic()-budget.start)
    common.write_json(directory/'report.json',final)
    print('[FINAL] '+json.dumps(dict(phase=phase,status=final['status'],
        selected=final.get('selected'),variants=[{key:r[key] for key in
        ('name','scored','exact','protected_exact','loop_indicators','question_echoes','empty')} for r in final['variants']],
        wall_seconds=final['wall_seconds']),ensure_ascii=False),flush=True)


def phase_budget(profile,phase):
    seconds={'capture':900,'search':1200,'confirm':2400}[phase]
    if datetime.now(timezone.utc).timestamp()+seconds+180>=common.DEADLINE.timestamp():
        raise TimeoutError('whole phase cap plus cleanup cannot fit authority deadline')
    return common.Budget(dict(profile,max_phase_seconds=seconds))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','capture','search','confirm'))
    phase=parser.parse_args().phase
    if phase=='prepare':prepare()
    elif phase=='capture':capture()
    else:execute_evaluation(phase)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except TimeoutError as exc:
        print('[HOLD] '+str(exc),flush=True);raise SystemExit(8)
    except Exception:
        import traceback
        traceback.print_exc()
        print('[ERROR] supervised local repair stopped; original artifacts retained',flush=True)
        raise SystemExit(9)
