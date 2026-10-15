#!/usr/bin/env python3
"""Fresh fictional-name scale contrast; dev-only choice and deadline cost gate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from contextlib import ExitStack,contextmanager
import copy
from datetime import datetime,timezone
import json
import math
from unittest.mock import patch
from scripts import diag_p106b_binding_auxiliary as small
from scripts import p106b_binding_auxiliary as method
from scripts.p106b_native_windows import NATIVE_TRAIN
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative

TAG='p106b_binding_scale_v1_s1337'
VERSION='P106B_FICTIONAL_BINDING_SCALE_V1'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
SMALL_EVIDENCE=small.EVIDENCE
CODE=(*small.CODE,'scripts/diag_p106b_binding_scale.py','scripts/test_p106b_binding_scale.py')
ORIGINAL_INFO=small.info
CANDIDATES=('aux03','aux100','auxdense100')
SURNAMES={'ko':{'train':['김','이','박','최','정','강','조','윤'],'dev':['장','임','오','한'],'test':['신','서','권','황']},
          'en':{'train':['Lane','Park','Hill','Reed','Lake','Stone','Wood','Vale'],
                'dev':['Brown','Gray','Moss','Snow'],'test':['Fox','West','Cloud','Marsh']}}


def info():
    value=ORIGINAL_INFO()
    value.update(schema=VERSION,tag=TAG,code_sha256={p:small.base.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        arms={'aux0':dict(weight=0.,root_permuted=False),'development_selected':dict(candidates=list(CANDIDATES))},
        planned_train_rows=67072,planned_updates=2096,native_access='INDEXED_TRAIN_ONLY',
        scope='fictional relation scale diagnostic, not75M world facts/300M actual SFT tokens',
        initializer='same pinned dense chat32 parent',save_epoch_checkpoints=True)
    return value


def names(split,language):
    given=method.prior.source.NAMES[language][split] if split!='test' else method.NAMES[language]
    return [surname+first if language=='ko' else first+' '+surname
        for surname in SURNAMES[language][split] for first in given]


def binding_rows(split,take):
    """Scoped reuse of exact code producer; no previous file/data is edited."""
    declared={language:{s:names(s,language) for s in ('train','dev','test')} for language in ('ko','en')}
    with patch.object(method.prior.source,'NAMES',declared):
        rows=method.prior.source.binding_rows(split,per_family=take)
    result=[]
    for row in rows:
        item=method.prior.correct_own_question(row);meta=item['meta']
        label='가상 기록:\n' if meta['language']=='ko' else 'Fictional record:\n'
        item['messages'][0]['content'][0]['text']=label+item['messages'][0]['content'][0]['text']
        meta.update(semantic_root_id=method.prior.source.sha(dict(task=VERSION,language=meta['language'],
            kind=meta['kind'],mapping=meta['mapping'])),source_split=split,course_version=VERSION,
            named_entities='FICTIONAL_IDENTIFIERS_NOT_REAL_PERSON_FACTS')
        result.append(item)
    return result


def trusted(values):
    return {method.prior.source.sha(row['messages']):copy.deepcopy(row['meta']) for row in values
        if row['meta']['kind'].startswith('binding_')}


def validate_splits(rows):
    roots={s:{r['meta']['semantic_root_id'] for r in v} for s,v in rows.items() if s in ('train','dev','test')}
    for a,b in (('train','dev'),('train','test'),('dev','test')):
        if roots[a]&roots[b]:raise ValueError('semantic root overlap')
    for language in ('ko','en'):
        sets={s:set(names(s,language)) for s in ('train','dev','test')}
        if any(sets[a]&sets[b] for a,b in (('train','dev'),('train','test'),('dev','test'))):
            raise ValueError('full fictional identifier overlap')
    for split,values in rows.items():
        signatures=[method.prior.source.sha(r['messages']) for r in values]
        if len(set(signatures))!=len(signatures):raise ValueError('duplicate conversation in '+split)


def freeze():
    small.base.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('previous scale namespace preserved')
    source=small.required_json(small.supplier.CORPUS/'report.json','lossless supported source512/64')
    if source['status']!='SUPPORTED_SOURCE_CORPUS_FROZEN' or source['code_sha256']!=small.supplier.info()['code_sha256']:
        raise ValueError('completed same-code lossless corpus required')
    for manifest in source['manifests'].values():verify(small.supplier.CORPUS,manifest)
    public={s:small.public_rows(list(small.base.training.data.stream_rows(small.supplier.CORPUS,m)))
        for s,m in source['manifests'].items()}
    original=method.prior.source.code_rows()
    rows={s:binding_rows(s,n)+[copy.deepcopy(r) for r in original[s] if not r['meta']['kind'].startswith('binding_')]
        for s,n in (('train',4096),('dev',64))}
    rows['train']+=public['train'];rows['dev']+=public['val']
    rows['test']=binding_rows('test',32)
    used={r['meta']['semantic_root_id'] for values in original.values() for r in values}
    used.update(r['meta']['semantic_root_id'] for r in method.fresh_test(original))
    index=0
    while len(rows['test'])<640:
        i=len(rows['test'])-512;language=('ko','en')[i%2];kind=('arithmetic','boolean','json','update')[(i//2)%4]
        item=method.prior.source.make(kind,language,23100000+index,novel=True);index+=1
        if item['meta']['semantic_root_id'] in used:continue
        used.add(item['meta']['semantic_root_id']);item['meta'].update(source_split='scale_test',course_version=VERSION)
        rows['test'].append(item)
        if index>100000:raise ValueError('fresh rule supply exhausted')
    rows['public_eval']=small.public_panel(public['val']);validate_splits(rows)
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    from tinylm.chat.serialize import serialize
    tok=Tokenizer.from_file(str(small.base.training.data.TOKENIZER));counts={};labels=[]
    for split,values in rows.items():
        contract=trusted(values);count=Counter()
        for row in values:
            rec=encode_record(row,tok);small.validate_budget([rec],[row]);m=row['meta']
            m.update(actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            count.update(rows=1,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            if split=='train':
                bit=method.binding_bit(row,contract)
                if bit is None:continue
                prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
                first=next(i for i,v in enumerate(rec.y) if v!=-100)
                if first!=len(tok.encode(prompt).ids)-1:raise ValueError('actual prefix/assistant first position mismatch')
                labels.append(dict(signature=method.prior.source.sha(row['messages']),bit=bit,
                    root=m['semantic_root_id'],positions=method.causal_suffix_positions(row,tok,first)))
        counts[split]=dict(count,languages=dict(Counter(r['meta']['language'] for r in values)),
            kinds=dict(Counter(r['meta']['kind'] for r in values)))
    if {s:len(rows[s]) for s in ('train','dev','test')}!=dict(train=67072,dev=1216,test=640) or len(labels)!=65536:
        raise ValueError('scale dataset size differs')
    if any(sum(r['meta']['target_is_first'] for r in rows[s] if r['meta']['kind'].startswith('binding_'))
            !=sum(r['meta']['kind'].startswith('binding_') for r in rows[s])/2 for s in ('train','dev','test')):
        raise ValueError('query first/second imbalance')
    import numpy as np
    train=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r')
    updates=4*(len(rows['train'])//128);offsets=method.prior.source.native_offsets(len(train),updates*8)
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
    writer=ShardWriter(CORPUS,'aux_labels')
    for item in labels:writer.append(item)
    label_manifest=writer.close(lineage=dict(schema=VERSION,scope='exact producer hash and causal prefix positions'))
    verify(CORPUS,label_manifest)
    value=dict(info(),status='BINDING_SCALE_COURSE_FROZEN',counts=counts,manifests=manifests,
        labels_manifest=label_manifest,dev_contracts=trusted(rows['dev']),epochs=4,expected_updates=updates,
        expected_head_position_events=4*sum(len(v['positions']) for v in labels),native_train_file=NATIVE_TRAIN,
        native_train_sha256=small.base.training.data.digest(ROOT/NATIVE_TRAIN),native_train_offsets=offsets,
        native_targets_per_arm=updates*8192,source_root_overlap=0,binding_names_disjoint=True,
        source_corpus_sha256=small.base.training.data.digest(small.supplier.CORPUS/'report.json'),
        teacher_calls=0,auxiliary_labels=len(labels),candidate_choice_scope='small final-epoch dev only; no fresh-test selection')
    small.base.training.write(CORPUS/'report.json',value)
    small.base.training.write(EVIDENCE/'corpus_report.json',{k:v for k,v in value.items() if k!='dev_contracts'})
    print('[BINDING_SCALE_CORPUS] '+json.dumps(dict(counts=counts,updates=updates,auxiliary_labels=len(labels))),flush=True)
    return 0


def score(report):
    last=report['history'][-1];dev=last['dev']
    exact=sum(c['exact'] for key,c in dev['counts'].items() if ':binding_' in key)
    return (dev['all4_exact_roots'],exact,-last['native']['ce'])


def select_candidate(reports):
    control=score(reports['aux0']);candidate=max(CANDIDATES,key=lambda a:(*score(reports[a]),-CANDIDATES.index(a)))
    improved=score(reports[candidate])[:2]>control[:2]
    return candidate if improved else 'auxdense100',improved


def choice():
    target=EVIDENCE/'choice.json'
    if target.exists():raise GateNegative('previous development choice preserved')
    reports={a:small.required_json(SMALL_EVIDENCE/a/'report.json','all completed small arms') for a in method.ARMS}
    if any(r['status']!='TRAINED_FRESH_TEST_PENDING' or r['updates']!=176 for r in reports.values()):
        raise ValueError('small five-arm completion required')
    if len({json.dumps(r['code_sha256'],sort_keys=True) for r in reports.values()})!=1:raise ValueError('small arm code mismatch')
    selected,improved=select_candidate(reports)
    value=dict(info(),status='DEV_SELECTED' if improved else 'UNCONFIRMED_HYPOTHESIS',candidate=selected,
        dev_scores={a:score(r) for a,r in reports.items()},reference_files={a:dict(path=str((SMALL_EVIDENCE/a/'report.json').relative_to(ROOT)),
        sha256=small.base.training.data.digest(SMALL_EVIDENCE/a/'report.json')) for a in reports},
        selection_uses_small_fresh_test=False,default_adopted=False)
    small.base.training.write(target,value);print('[BINDING_SCALE_CHOICE] '+json.dumps(value),flush=True);return 0


def selected():
    r=small.required_json(EVIDENCE/'choice.json','development-only scale candidate')
    if r['code_sha256']!=info()['code_sha256'] or r['candidate'] not in CANDIDATES:raise ValueError('scale choice/code differs')
    return r['candidate']


def read_course():
    r=small.required_json(CORPUS/'report.json','frozen scale corpus')
    if r['status']!='BINDING_SCALE_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:
        raise ValueError('same-code scale corpus required')
    if small.base.training.data.digest(ROOT/r['native_train_file'])!=r['native_train_sha256']:
        raise ValueError('native train source changed')
    for manifest in (*r['manifests'].values(),r['labels_manifest']):verify(CORPUS,manifest)
    labels=list(small.base.training.data.stream_rows(CORPUS,r['labels_manifest']))
    r['labels']={item['signature']:{k:v for k,v in item.items() if k!='signature'} for item in labels}
    if len(r['labels'])!=65536:raise ValueError('auxiliary label count differs')
    r['required_cost_arms']=['aux0',selected()]
    return r,{s:list(small.base.training.data.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}


def forecast(reports,remaining,completed=()):
    estimates={}
    for arm,report in reports.items():
        steady=sorted(report['step_seconds'][1:])
        if len(steady)!=7 or not all(math.isfinite(x) and x>0 for x in steady):raise ValueError('seven finite steady cost steps required')
        p95=steady[math.ceil(.95*len(steady))-1]
        estimates[arm]=dict(steady_p95=p95,train_estimate_sec=p95*2096+600)
    need=sum(v['train_estimate_sec'] for a,v in estimates.items() if a not in completed)+1800+2700
    return dict(arms=estimates,remaining_sec=remaining,needed_sec=need,complete_arms=list(completed),fits=need<remaining,
        eval_margin_sec=1800,closure_margin_sec=2700,scope='forecast only; not completion guarantee')


def budget(record=False):
    candidate=selected();arms=('aux0',candidate);reports={};completed=[]
    for arm in arms:
        reports[arm]=small.required_json(EVIDENCE/('cost_'+arm)/'report.json','two actual scale cost8 reports')
        if reports[arm]['updates']!=8 or reports[arm]['code_sha256']!=info()['code_sha256']:
            raise ValueError('same-code actual cost8 required')
        path=EVIDENCE/arm/'report.json'
        if path.exists():
            actual=json.loads(path.read_text())
            if actual['status']!='TRAINED_FRESH_TEST_PENDING' or actual['updates']!=2096:
                raise ValueError('previous partial scale arm; manual new version required')
            completed.append(arm)
    remaining=(small.base.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    value=dict(info(),status='BUDGET_MEASURED',**forecast(reports,remaining,completed))
    if record:small.base.training.write(EVIDENCE/'budget_report.json',value)
    print('[BINDING_SCALE_BUDGET] '+json.dumps(value),flush=True)
    if not value['fits']:raise GateNegative('measured forecast does not fit before17 including evaluation/closure')
    return 0


@contextmanager
def selected_runtime():
    candidate=selected();arms={a:method.ARMS[a] for a in ('aux0',candidate)}
    with ExitStack() as stack:
        for name,value in dict(TAG=TAG,CORPUS=CORPUS,EVIDENCE=EVIDENCE,LOCAL=LOCAL,CODE=CODE,
                info=info,read_course=read_course).items():stack.enter_context(patch.object(small,name,value))
        stack.enter_context(patch.object(method,'ARMS',arms))
        yield arms


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('freeze','choice','cost','budget','train','evaluate'),required=True)
    parser.add_argument('--arm',choices=('aux0','candidate'),default='aux0')
    parser.add_argument('--max-wall-sec',type=int,default=7200)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if not 60<=args.max_wall_sec<=10800:parser.error('bounded60..10800')
    try:
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info()));return 0
        if not args.execute:parser.error('explicit execution required')
        small.base.deadline()
        if args.mode=='freeze':return freeze()
        if args.mode=='choice':return choice()
        if args.mode=='budget':return budget(record=True)
        args.max_wall_sec=min(args.max_wall_sec,int((small.base.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if args.max_wall_sec<60:raise GateNegative('closure margin before17 required')
        if args.mode=='train':budget()
        candidate=selected();args.arm='aux0' if args.arm=='aux0' else candidate
        with selected_runtime():
            return small.evaluate(args) if args.mode=='evaluate' else small.train(args,cost=args.mode=='cost')
    except GateNegative as exc:print('[BINDING_SCALE_HOLD] '+str(exc),flush=True);return 8
    except KeyboardInterrupt:print('[BINDING_SCALE_INTERRUPTED] preserve partial outputs',flush=True);return 130
    except Exception as exc:print('[BINDING_SCALE_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return 9


if __name__=='__main__':raise SystemExit(main())
