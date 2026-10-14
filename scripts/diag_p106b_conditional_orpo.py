#!/usr/bin/env python3
"""Same frozen SFT/native input, code-proven conditional ORPO-style contrast."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from dataclasses import asdict
import json
import os
import tempfile
import time
from scripts import p106b_conditional_orpo as method
from scripts import diag_p106b_retention_course as base
from scripts.p106b_shards import ShardWriter,verify
TAG='p106b_context_orpo_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
CODE=('scripts/p106b_conditional_orpo.py','scripts/diag_p106b_conditional_orpo.py',
      'scripts/test_p106b_conditional_orpo.py',*base.CODE)


def info():
    result=base.info()
    result.update(schema=method.VERSION,tag=TAG,orpo_betas=method.BETAS,
        code_sha256={p:base.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        preference_pairs_per_update=16,source_method='ORPO equations3-7; native replay and token-normalized SFT are project adaptations',
        rejected_scope='only byte-verified code one-value tasks; wrong other entity or unrequested duplicate within one answer',
        no_word_blacklist=True,online_regeneration=False,actual_student_rollout='NOT_RUN')
    return result


def checkpoint(arm):
    return ROOT/'runs/ckpt'/f'm100s10_ko-en_context_orpo_dense_chat32_{TAG}_{arm}.pt'


def freeze(args):
    base.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise FileExistsError('fresh ORPO namespace required')
    sealed=json.loads((base.EVIDENCE/'sealed_test/report.json').read_text())
    if sealed['status']!='SEALED_CODE_TEST_COLLECTED':raise ValueError('original three-arm test prerequisite')
    original,rows=base.read_course()
    rows={s:[method.correct_own_question(row) for row in values] for s,values in rows.items()}
    chosen=json.loads((base.EVIDENCE/args.replay_source/'report.json').read_text())
    if chosen['status']!='TRAINED_SEALED_TEST_PENDING':raise ValueError('completed source arm required')
    legal={method.source.sha(method.correct_own_question(r)['messages']) for r in method.source.binding_rows('train')}
    pairs=[method.make_pair(r,legal) for r in rows['train'] if r['meta']['kind'].startswith('binding_')]
    if len(pairs)!=4096:raise ValueError('all known conditional rows required')
    test=method.fresh_test(rows)
    CORPUS.mkdir(parents=True,exist_ok=False)
    manifests={}
    for label,values in (('train',rows['train']),('dev',rows['dev']),('pairs',pairs),('test',test)):
        writer=ShardWriter(CORPUS,label)
        for row in values:writer.append(row)
        manifests[label]=writer.close(lineage=info());verify(CORPUS,manifests[label])
    from tokenizers import Tokenizer
    from tinylm.train import mtp_sft as core
    tok=Tokenizer.from_file(str(base.training.data.TOKENIZER))
    encoded=[core.encode_record(row,tok) for row in rows['train']]
    output=dict(info(),status='PAIRS_FROZEN',manifests=manifests,native_weight=chosen['weight'],
        replay_source=args.replay_source,selection_note=args.decision_note,
        original_corpus_sha256=base.training.data.digest(base.CORPUS/'report.json'),
        original_test_report_sha256=base.training.data.digest(base.EVIDENCE/'sealed_test/report.json'),
        counts=dict(train_sft=5632,train_sft_x=sum(x.x_tokens for x in encoded),assistant_targets=sum(x.targets for x in encoded),
                    pairs=len(pairs),test=len(test),modes=dict(Counter(p['mode'] for p in pairs))),
        source_data_revision='own Korean color particle join corrected; public QA unchanged; compare new beta0, not old recipe',
        prior_test_scope='now development for choosing follow-up, not the new final test',
        expected_updates=original['expected_updates'])
    base.training.write(CORPUS/'report.json',output);base.training.write(EVIDENCE/'corpus_report.json',output)
    print('[CONDITIONAL_PAIRS] '+json.dumps(output['counts']));return 0


def read_course():
    r=json.loads((CORPUS/'report.json').read_text())
    if r['status']!='PAIRS_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('same frozen code required')
    original,rows=base.read_course()
    if base.training.data.digest(base.CORPUS/'report.json')!=r['original_corpus_sha256']:raise ValueError('original input changed')
    for m in r['manifests'].values():verify(CORPUS,m)
    rows={s:list(base.training.data.stream_rows(CORPUS,r['manifests'][s])) for s in ('train','dev')}
    pairs=list(base.training.data.stream_rows(CORPUS,r['manifests']['pairs']))
    test=list(base.training.data.stream_rows(CORPUS,r['manifests']['test']))
    return r,original,rows,pairs,test


def train(args,cost=False):
    base.deadline();r,original,rows,pairs,test=read_course()
    arm=args.arm;beta=method.BETAS[arm];native_weight=r['native_weight']
    target=EVIDENCE/(('cost_' if cost else '')+arm);local=LOCAL/(('cost_' if cost else '')+arm)
    out=checkpoint(arm)
    if target.exists() or local.exists() or (not cost and out.exists()):raise FileExistsError('preserve previous ORPO arm')
    if not cost:
        calibration=json.loads((EVIDENCE/'cost_pair_zero/report.json').read_text())
        if calibration['code_sha256']!=info()['code_sha256'] or calibration['updates']!=8:raise ValueError('same cost8 required')
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.train import mtp_sft as core
    import numpy as np
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=base.training.load_runtime('parent_ntp')
        records=[core.encode_record(row,tok) for row in rows['train']]
        signatures={id(rec):method.source.sha(row['messages']) for rec,row in zip(records,rows['train'])}
        encoded_pairs={p['source_signature']:(core.encode_record(p['chosen'],tok),
            core.encode_record(p['rejected'],tok),p['mode']) for p in pairs}
        dev_records=[core.encode_record(row,tok) for row in rows['dev']]
        native=np.memmap(base.CORPUS/'native_train.bin',dtype=np.uint16,mode='r').reshape(-1,1025)
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_orpo_')
        model=model.cuda();model.train();pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('missing pad')
        torch.cuda.reset_peak_memory_stats();before=None if cost else base.training.native_ce(model,base.NATIVE)
        compiled=torch.compile(model,mode='default');adam,muon=base.training.optimizers(model)
        for opt in (adam,muon):
            for group in opt.param_groups:group['lr']*=.5
        steps=sft_x=assistant_y=native_x=pair_x=pair_y=pair_count=0
        grad_max=0.;seconds=[];history=[];modes=Counter();probability_clamps=0
        for epoch in range(4):
            for groups in base.training.batches(records,epoch):
                base.deadline();tick=time.perf_counter();denominator=sum(x.targets for g in groups for x in g)
                adam.zero_grad(set_to_none=True);muon.zero_grad(set_to_none=True)
                for micro in groups:
                    x,y,segments=core.pad_records(micro,pad,'cuda',fixed_width=1024,batch_size=8)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True);sums,counts=core.components(model,hidden,y,segments,horizons=())
                        loss=sums[1]/denominator
                    if not torch.isfinite(loss):raise ValueError('nonfinite SFT objective')
                    loss.backward();sft_x+=sum(rec.x_tokens for rec in micro);assistant_y+=sum(rec.targets for rec in micro)
                native_records=[core.Record(a[:-1].astype('int64').tolist(),a[1:].astype('int64').tolist(),[1]*1024)
                                for a in native[steps*8:(steps+1)*8]]
                x,y,segments=core.pad_records(native_records,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=compiled(x,return_hidden=True);sums,counts=core.components(model,hidden,y,segments,horizons=())
                    loss=native_weight*sums[1]/8192
                loss.backward();native_x+=8192
                selected=[encoded_pairs[signatures[id(rec)]] for micro in groups for rec in micro if signatures[id(rec)] in encoded_pairs][:16]
                if len(selected)!=16:raise ValueError('sixteen deterministic pairs required')
                for start in range(0,16,4):
                    chunk=selected[start:start+4]
                    values=[p[0] for p in chunk]+[p[1] for p in chunk]
                    x,y,segments=core.pad_records(values,pad,'cuda',fixed_width=1024,batch_size=8)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True)
                        logps=method.sequence_logps(model,hidden,y)
                    preference=method.extra_loss(arm,logps[:4],logps[4:])
                    loss=beta*preference.sum()/16
                    if not torch.isfinite(loss):raise ValueError('nonfinite preference objective')
                    loss.backward();pair_x+=sum(rec.x_tokens for rec in values);pair_y+=sum(rec.targets for rec in values)
                    pair_count+=4;modes.update(p[2] for p in chunk);probability_clamps+=int(logps.ge(-1e-6).sum())
                gradient=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                if not torch.isfinite(gradient):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(gradient));adam.step();muon.step();steps+=1
                torch.cuda.synchronize();seconds.append(time.perf_counter()-tick)
                if steps==1 or steps%16==0:print('[CONDITIONAL_UPDATE] '+json.dumps(dict(arm=arm,steps=steps,sft_x=sft_x,
                    native_x=native_x,pairs=pair_count,last_sec=seconds[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            val=base.training.evaluate(model,dev_records,pad)
            native_eval=base.training.native_ce(model,base.NATIVE)
            generations=base.generate(model,cfg,tok,base.dev_sample(rows['dev']),local,f'dev_epoch{epoch+1}')
            history.append(dict(epoch=epoch+1,updates=steps,val=val,native=native_eval,dev=generations))
        if not cost and (steps!=176 or sft_x!=4*r['counts']['train_sft_x']):raise ValueError('planned exposure mismatch')
        result=dict(info(),status='COST_MEASURED' if cost else 'TRAINED_FRESH_TEST_PENDING',arm=arm,beta=beta,
            native_weight=native_weight,updates=steps,initial_core_sha256=initial,
            extra_objective='CHOSEN_ONLY_NLL' if arm=='positive030' else 'CONDITIONAL_LOG_ODDS',
            rejected_objective_active=bool(beta and arm!='positive030'),
            corpus_sha256=base.training.data.digest(CORPUS/'report.json'),sft_x_tokens=sft_x,assistant_targets=assistant_y,
            native_x_tokens=native_x,pair_x_tokens=pair_x,pair_scored_tokens=pair_y,contrast_pairs=pair_count,
            contrast_modes=dict(modes),probability_floor_clamps=probability_clamps,grad_max=grad_max,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,step_seconds=seconds,
            native_before=before,history=history,whole_sec=time.perf_counter()-began,
            comparison_scope='only beta differs; all arms calculate same chosen/rejected/native input',
            general_intelligence='NOT_ESTABLISHED',actual_student_rollout='NOT_RUN')
        if not cost:
            with out.open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,
                tokenizer_sha256=base.training.data.TOK_SHA,tokenizer_lineage='chat32',conditional_orpo=dict(tag=TAG,arm=arm)),stream)
            result.update(checkpoint=str(out.relative_to(ROOT)),checkpoint_sha256=base.training.data.digest(out),optimizer_saved=False)
        base.training.write(target/'report.json',result)
    print('[CONDITIONAL_FINAL] '+json.dumps({k:result[k] for k in ('arm','status','updates','whole_sec')}),flush=True);return 0


def evaluate(args):
    base.deadline();report,original,rows,pairs,test=read_course();target=EVIDENCE/'fresh_test'
    if target.exists():raise FileExistsError('fresh test preserved')
    trained={arm:json.loads((EVIDENCE/arm/'report.json').read_text()) for arm in method.BETAS}
    for arm,r in trained.items():
        if r['status']!='TRAINED_FRESH_TEST_PENDING' or r['code_sha256']!=info()['code_sha256']:
            raise ValueError('same completed three arms required')
        if base.training.data.digest(ROOT/r['checkpoint'])!=r['checkpoint_sha256']:raise ValueError('checkpoint changed')
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.infer.generate import _strip
    import gc
    idle_before_gpu();began=time.perf_counter();summaries={}
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*method.BETAS):
            base.deadline();torch,model,cfg,tok,initial=base.training.load_runtime('parent_ntp')
            if arm!='parent':
                state=torch.load(ROOT/trained[arm]['checkpoint'],map_location='cpu',weights_only=True)
                model.load_state_dict(_strip(state['model']),strict=True);del state
            model=model.cuda();summaries[arm]=base.generate(model,cfg,tok,test,LOCAL/'fresh_test'/arm,'fresh')
            summaries[arm]['native']=base.training.native_ce(model,base.NATIVE)
            del model;gc.collect();torch.cuda.empty_cache()
    result=dict(info(),status='FRESH_CODE_TEST_COLLECTED',arms=summaries,cases_per_arm=len(test),
        whole_sec=time.perf_counter()-began,checkpoint_saved=False,model_training=False,
        scope='fresh fictional fact associations relative to current SFT; not a world benchmark')
    base.training.write(target/'report.json',result);return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('freeze','cost','train','evaluate'),required=True)
    parser.add_argument('--arm',choices=tuple(method.BETAS),default='pair_zero')
    parser.add_argument('--replay-source',choices=('replay025','replay100'),default='replay100')
    parser.add_argument('--decision-note',default='')
    parser.add_argument('--max-wall-sec',type=int,default=3600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if not 60<=args.max_wall_sec<=21600:parser.error('bounded60..21600')
    if args.check_only:
        if args.mode!='freeze':read_course()
        print('[CHECK_ONLY] '+json.dumps(info()));return 0
    base.deadline()
    if args.mode=='freeze':
        if not args.decision_note:parser.error('explicit development-based choice note required')
        return freeze(args)
    if args.mode in ('cost','train'):return train(args,cost=args.mode=='cost')
    return evaluate(args)


if __name__=='__main__':raise SystemExit(main())
