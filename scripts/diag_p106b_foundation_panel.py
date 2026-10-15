#!/usr/bin/env python3
"""Inference-only DEV64 on existing students; no old data/weights are mutated."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
import gc
import json
import time
from scripts import diag_p106b_grounded_span as source
from scripts import summarize_p106b_grounded_span as cached
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
TAG='p106b_foundation_reading_dev64_v1_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
REFERENCES={
    'large_binding':('p106b_binding_scale_v1_s1337','auxdense100','1DE63EE5E5682221675AD70B60C603B71DF8CDC93C2A33EDCBB430950E3AD9AE'),
    'state_sft':('p106b_state_update_aux_v1_s1337','aux0','8CBF93D325DBCE09D534CADD49440E606F901BBB2890FC27EF3AFD5898960EAF'),
    'small_binding':('p106b_binding_aux_v1_s1337','auxdense100','B57F863685A5048ACD3EDBF9A76490491137FECD1876E10C17B7228ACDAA235A')}
CODE=(*source.CODE,'scripts/diag_p106b_grounded_span_execution.py','scripts/diag_p106b_foundation_panel.py',
      'scripts/test_p106b_foundation_panel.py','scripts/summarize_p106b_grounded_span.py','scripts/diag_p101a_mtp_parity.py')


def select64(rows):
    result=[]
    for language in ('ko','en'):
        values=sorted([r for r in rows if r['meta']['language']==language],key=lambda r:r['meta']['semantic_root_id'])
        if len(values)!=128 or len({r['meta']['semantic_root_id'] for r in values})!=128:
            raise ValueError('exact128 independent document IDs per language required')
        result.extend(values[::4])
    if len(result)!=64:raise ValueError('balanced64 selection failed')
    return result


def counts(rows):
    totals={}
    for language in ('ko','en'):
        selected=[r for r in rows if r['meta']['language']==language]
        totals[language]=dict(cases=len(selected),literal=sum(r['answer'].strip()==r['gold'].strip() for r in selected),
            mean_lexical_f1=sum(source.method.token_f1(r['answer'],r['gold']) for r in selected)/len(selected),
            max_new=sum(r['generation']['finish_reason'].startswith('MAX_NEW') for r in selected))
    return totals


def verify_same_inputs(selected,answer_rows):
    by=cached.indexed(answer_rows);roots={r['meta']['semantic_root_id'] for r in selected}
    if set(by)!=roots:raise ValueError('same selected64 roots required')
    for row in selected:
        old=by[row['meta']['semantic_root_id']]
        if old['messages']!=row['messages'][:-1] or old['gold']!=source.method.text(row['messages'][-1]):
            raise ValueError('cached question/reference/target differs')
    return by


def input_contract(check_weights=False):
    frozen,rows,_=source.read_course();selected=select64(rows['test'])
    current=source.required(cached.EVIDENCE/'report.json')
    if current['status']!='GROUNDED_SPAN_EVALUATED':raise GateNegative('completed previous source evaluation required')
    for p,sha in current['code_sha256'].items():
        if source.public.digest(ROOT/p)!=sha:raise ValueError('prior cached evaluation code changed')
    references={}
    for name,(tag,arm,sha) in REFERENCES.items():
        rp=ROOT/'test_result/evidence'/tag/arm/'report.json';r=source.required(rp);path=ROOT/r['checkpoint']
        if r['checkpoint_sha256']!=sha or not path.resolve().is_relative_to((ROOT/'runs/ckpt').resolve()):
            raise ValueError('pinned reference differs')
        if check_weights and source.public.digest(path)!=sha:raise ValueError('reference weight bytes changed')
        references[name]=dict(report=str(rp.relative_to(ROOT)),report_sha256=source.public.digest(rp),
            checkpoint=r['checkpoint'],checkpoint_sha256=sha)
    info=dict(schema='P106B_FOUNDATION_READING_DEV64_V1',tag=TAG,
        code_sha256={p:source.public.digest(ROOT/p) for p in sorted(set(CODE))},
        source_report_sha256=source.public.digest(source.CORPUS/'report.json'),
        prior_evaluation_sha256=source.public.digest(cached.EVIDENCE/'report.json'),
        selected_questions_sha256=source.method.sha([r['messages'] for r in selected]),references=references,
        parent_source_model='cached previous parent/span0, no repeat GPU',selection='language/root sorted positions0,4,..124',
        prior_test_reused_as_development=True,cases=64,languages=dict(ko=32,en=32),
        precision='FP32_MATH greedy64, EOT stop',auxiliary_inference=False,mtp=False,
        optimizer_updates=0,checkpoint_saved=False,source_data_changed=False,
        authority_deadline_utc=source.DEADLINE.isoformat(),permitted_claim='DESCRIPTIVE_ONLY',
        world_truth='NOT_RUN',scope='model-specific initializer DEV comparison; not new independent final test')
    return info,selected,current


def execute(args):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    source.deadline();info,rows,current=input_contract(True)
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old foundation output preserved')
    if source.public.digest(source.public.TOKENIZER)!=source.public.TOK_SHA:raise ValueError('tokenizer changed')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);began=time.perf_counter();results={};answer_sets={};error=None
    try:
        with wall_limit(args.max_wall_sec):
            for name in ('parent','span0'):
                root_set={r['meta']['semantic_root_id'] for r in rows}
                originals=cached.load(current['arms'][name]['test'])
                values=[r for r in originals if r['meta']['semantic_root_id'] in root_set]
                verify_same_inputs(rows,values);answer_sets[name]=cached.indexed(values)
                results[name]=dict(counts=counts(values),origin='REUSED_IDENTICAL_RAW_64_OF_PREVIOUS256',
                    source_raw_spec=current['arms'][name]['test'],models_loaded_this_endpoint=0)
            for name,ref in info['references'].items():
                source.deadline();state=torch.load(ROOT/ref['checkpoint'],map_location='cpu',weights_only=True)
                if not isinstance(state['cfg'],dict) or state['tokenizer_sha256']!=source.public.TOK_SHA:
                    raise ValueError('actual saved config and exact tokenizer lineage required')
                cfg=TMTConfig(**state['cfg'])
                if (cfg.n_layers,cfg.dim,cfg.ffn_dim,cfg.emb_rank,cfg.vocab_size,cfg.cla_group,cfg.max_seq_len)!=(14,768,2048,256,32768,2,1024) or cfg.tie_mlp or cfg.mtp_aux:
                    raise ValueError('declared dense14/chat32/CLA2/MTPoff geometry differs')
                torch.manual_seed(1337);model=TiedMLPTransformer(cfg);model.load_state_dict(_strip(state['model']),strict=True);del state
                model.set_anneal(1.);model.eval()
                if list(model.visit_schedule())!=list(range(14)):raise ValueError('R1 logical visits required')
                before=source.training.state_fingerprint(model);model=model.cuda();tok=Tokenizer.from_file(str(source.public.TOKENIZER))
                spec=source.generate(model,cfg,tok,rows,LOCAL/name,'natural_dev64')
                values=[json.loads(line) for s in spec['manifest']['shards'] for line in (LOCAL/name/s['path']).read_text().splitlines()]
                verify_same_inputs(rows,values);answer_sets[name]=cached.indexed(values)
                native=source.training.native_ce(model,source.NATIVE);after=source.training.state_fingerprint(model)
                if before!=after:raise ValueError('inference changed body state')
                results[name]=dict(counts=counts(values),raw_spec=spec,native=native,actual_cfg=asdict(cfg),
                    body_before=before,body_after=after,models_loaded_this_endpoint=1,checkpoint=ref['checkpoint'])
                source.training.write(EVIDENCE/(name+'_report.json'),dict(info,endpoint=name,result=results[name]))
                print('[FOUNDATION_DEV64] '+json.dumps(dict(endpoint=name,counts=results[name]['counts'],native=native['ce'],body_unchanged=True)),flush=True)
                del model;gc.collect();torch.cuda.empty_cache()
            sample=[]
            for language in ('ko','en'):
                keys=sorted(k for k,r in answer_sets['parent'].items() if r['meta']['language']==language)
                for i in (0,8,16,24):
                    key=keys[i];base=answer_sets['parent'][key]
                    sample.append(dict(root=key,language=language,messages=base['messages'],source_gold=base['gold'],
                        answers={name:values[key]['answer'] for name,values in answer_sets.items()},
                        scope='same previous source8, now development-only; semantic reading separate'))
            w=ShardWriter(LOCAL/'sample8','review')
            for row in sample:w.append(row)
            manifest=w.close(lineage=dict(scope='fixed8 source questions, five existing endpoints'))
            info.update(sample8_manifest=manifest,sample8_directory=str((LOCAL/'sample8').relative_to(ROOT)))
    except BaseException as exc:
        error=dict(type=type(exc).__name__,reason=str(exc)[:1200])
        import traceback
        traceback.print_exc()
        print('[FOUNDATION_ERROR] '+json.dumps(error),flush=True)
    result=dict(info,status='FOUNDATION_DEV64_COLLECTED' if error is None else 'FOUNDATION_EXECUTION_ERROR',
        endpoints=results,error=error,whole_sec=time.perf_counter()-began,automatic_parent_selection=False)
    source.training.write(EVIDENCE/'report.json',result)
    print('[FOUNDATION_FINAL] '+json.dumps(dict(status=result['status'],completed_endpoints=list(results),whole_sec=result['whole_sec'])),flush=True)
    return 0 if error is None else 130 if error['type']=='KeyboardInterrupt' else 9


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=1800)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=1800:p.error('bounded60..1800')
    if a.check_only:print('[FOUNDATION_CHECK_ONLY] '+json.dumps(input_contract(False)[0]));return 0
    if not a.execute:p.error('explicit execution required')
    try:
        source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-600)
        if a.max_wall_sec<60:raise GateNegative('authorized deadline margin')
        return execute(a)
    except GateNegative as exc:print('[FOUNDATION_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[FOUNDATION_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
