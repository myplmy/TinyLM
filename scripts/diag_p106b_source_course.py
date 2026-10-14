"""Independent source course; old/public inputs read-only, no models in check-only."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import ExitStack
import copy
import json
import math
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import p106b_source_course as data
from scripts import p101a_sft_mtp_data as public
from scripts import diag_p101a_sft_mtp as training
from scripts import diag_p106b_context_quality as prior
from scripts import p106b_gemma_labels as teacher
from scripts import p106b_visible_source as support
from scripts import diag_p106b_gemma_telemetry_resume as telemetry
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.diag_p106b_gemma_ac import count_prompt
from scripts.p106b_shards import ShardWriter,verify
TAG='p106b_source_course_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
CORPUS=OUTPUT/'corpus'
CODE=('scripts/p106b_source_course.py','scripts/diag_p106b_source_course.py','scripts/test_p106b_source_course.py',
      'scripts/p106b_visible_source.py','scripts/p106b_gemma_labels.py','scripts/p106b_gemma_teacher.py',
      'scripts/p106b_memory_stream.py','scripts/diag_p106b_gemma_ac.py','scripts/diag_p106b_context_quality.py',
      'scripts/diag_p101a_sft_mtp.py','tinylm/train/mtp_sft.py')
FAMILIES={'ko':('NQ','COQA','ADVERSARIAL','AYA'),'en':('NQ','COQA','AYA','OASST')}


def existing_sources(manifests):
    # Public format/multiturn views retain original concepts. These instructions
    # remain quoted data, never the teacher's task. New split is explicit below.
    for original_split in ('val','train'):
        for row in public.stream_rows(public.PUBLIC,manifests[original_split]):
            if row['meta'].get('source')=='p106b_public_direct':yield row,original_split
    identities=[]
    for directory in [public.TEACHER/('batch_'+f'{i:06d}') for i in range(4)]+[
            ROOT/'HF/sft_ready/p106b_gemma_deficit_mtp_v4'/('batch_'+f'{i:06d}') for i in (4,5)]:
        rp=directory/'report.json';r=json.loads(rp.read_text());identities.append(dict(path=str(rp.relative_to(ROOT)),sha256=public.digest(rp)))
        for record in public.stream_rows(directory,r['raw_manifest']):
            row=record.get('source')
            if isinstance(row,dict) and data.family(row)=='ADVERSARIAL':yield row,row['meta'].get('source_split','UNSPECIFIED')


def source_root(row):
    value=row['meta'].get('parent_concept_id') or row['meta'].get('source_group_id')
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdefABCDEF' for c in value):
        value=support.sha(row['messages'])
    return value


def info():
    return dict(schema=data.VERSION,tag=TAG,parent_sha256=training.PARENT_SHA,tokenizer_sha256=public.TOK_SHA,
        micro_bs=8,accum=16,seq=1024,grad_checkpoint=True,compile='default',seed=1337,epochs=4,
        expected_updates=32,train_rows=1024,val_rows=128,lr=5e-5,muon_lr=2e-4,
        teacher_mtp=True,teacher_sampler=teacher.SAMPLER,teacher_context=teacher.CONTEXT,
        teacher_output=teacher.MAX_OUTPUT,teacher_thinking=teacher.THINKING,
        source_train=512,source_val=64,views_per_source=2,reference_weight_options=[0.,.1],
        formal_train_ready=False,world_knowledge_claim=False,code_sha256={p:public.digest(ROOT/p) for p in CODE})


def deck():
    if public.digest(public.PUBLIC/'report.json')!=public.PUBLIC_SHA:raise ValueError('pinned public changed')
    manifests={s:json.loads((public.PUBLIC/(s+'_shards_manifest.json')).read_text()) for s in ('train','val')}
    pools={};rejected=Counter();duplicates=set()
    for original,original_split in existing_sources(manifests):
        row=copy.deepcopy(original);meta=row['meta'];lang=meta.get('language');fam=data.family(row)
        if fam not in FAMILIES.get(lang,()):continue
        root=source_root(row)
        if (root,lang) in duplicates:continue
        duplicates.add((root,lang))
        split='val' if int(root[:8],16)%5==0 else 'train'
        row['meta'].update(parent_concept_id=root,original_source_split=original_split)
        try:support.source_spans(row)
        except ValueError:rejected['bounded_source_spans']+=1;continue
        lane=(split,lang,fam);pools.setdefault(lane,[]).append(row)
    chosen=[];seen=set();family_counts=Counter()
    for split in ('val','train'):
        target=64 if split=='train' else 8;reserve=16 if split=='train' else 4
        for lang in ('ko','en'):
            for fam in FAMILIES[lang]:
                rows=sorted(pools.get((split,lang,fam),[]),key=lambda row:support.sha(row['messages']))
                accepted=[]
                for row in rows:
                    keys=data.document_keys(row)
                    if keys&seen:continue
                    seen.update(keys);accepted.append(row)
                    if len(accepted)==target+reserve:break
                if len(accepted)<target:raise ValueError('source lane short: '+str((split,lang,fam,len(accepted),target)))
                for n,row in enumerate(accepted):chosen.append(dict(split=split,language=lang,family=fam,
                    target_per_lane=target,source=row,root=row['meta']['parent_concept_id'],reserve_order=n))
                family_counts[split+':'+lang+':'+fam]=len(accepted)
    # Interleave languages/families rather than processing a whole KO prefix.
    chosen.sort(key=lambda x:(x['reserve_order'],x['split'],x['family'],x['language']))
    return chosen,dict(public_sha256=public.PUBLIC_SHA,source_manifests=manifests,
        selected=support.sha(chosen),family_counts=dict(family_counts),rejections=dict(rejected),
        source_cap='one quarter of source groups per language; not claim of token balance',
        split_policy='new original-concept SHA20percent val; preserve original source split; selected exact long-message keys also disjoint',
        past_pretraining_or_translation_overlap='NOT_ESTABLISHED; only new SFT source-group disjointness verified')


def freeze():
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('fresh namespace only')
    selected,identity=deck();OUTPUT.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(OUTPUT,'sources')
    for row in selected:writer.append(row)
    report=dict(info(),status='SOURCE_DECK_FROZEN',identity=identity,manifest=writer.close(lineage=info()))
    verify(OUTPUT,report['manifest']);training.write(OUTPUT/'sources_report.json',report)
    training.write(EVIDENCE/'source_deck.json',dict(info(),status='SOURCE_DECK_FROZEN',identity=identity,
        source_manifest=report['manifest'],raw_sources='LOCAL_ONLY_IGNORED_HF'))
    print('[SOURCE_DECK] '+json.dumps(identity['family_counts']));return 0


def read_deck():
    report=json.loads((OUTPUT/'sources_report.json').read_text())
    if report['code_sha256']!=info()['code_sha256']:raise ValueError('frozen source/code controls changed')
    return list(public.stream_rows(OUTPUT,report['manifest'])),report


def generate(args):
    from tokenizers import Tokenizer
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    selected,report=read_deck();target=OUTPUT/'teacher'
    if target.exists():raise FileExistsError('preserve previous teacher run; no implicit reset')
    idle_before_gpu();target.mkdir(exist_ok=False);tok=Tokenizer.from_file(str(public.TOKENIZER))
    raw=ShardWriter(target,'raw');canon=ShardWriter(target,'candidates');counts=Counter();results=[];began=time.perf_counter();rc=9;status='STARTED';metrics={}
    try:
        with wall_limit(args.max_wall_sec),PersistentMemory() as source:
            reader=telemetry.RetryingMemoryReader(source,emit=lambda x:print(x,flush=True))
            with stream_session_scope(reader),teacher.GemmaSession(True) as session:
                for item in selected:
                    lane=item['split']+':'+item['language']+':'+item['family']
                    if counts[lane]>=item['target_per_lane']:continue
                    spans=support.source_spans(item['source']);feedback='';candidate=None
                    for attempt in range(1,4):
                        session.check();seed=int(support.sha([TAG,item['root'],attempt])[:12],16)%(2**31-1)
                        payload=support.payload(spans,item['language'],seed,feedback)
                        payload['messages'][0]['content']+=' Selected SOURCE_IDS must cover the entity, relation, conditions and answer, not merely an isolated answer word. For a short original QA select BOTH its question and answer spans if needed. Software will explicitly require the supplied reference.'
                        budget=count_prompt(session,payload['messages'],teacher.CONTEXT,teacher.MAX_OUTPUT)
                        tick=time.perf_counter();reply=session.request('/v1/chat/completions',payload,timeout=180)
                        parsed=teacher.parsed_response(reply,item['language']);reason='';candidate=None
                        try:
                            if parsed['format_status']!=teacher.COMPLETE:raise ValueError(parsed.get('parse_error') or parsed['format_status'])
                            candidate=support.wrap(parsed['parsed_content'],spans,item['source'],item['language'],tok)
                            candidate['meta'].update(parent_concept_id=item['root'],source_split=item['split'],course_family=item['family'])
                            pair=data.views(candidate,parsed['parsed_content']['user_text'],item['split'])
                            for row in pair:data.record(row,tok)
                        except ValueError as exc:reason=str(exc);candidate=None
                        raw.append(dict(item=item,payload=payload,reply=reply,parsed=parsed,candidate=candidate,
                            structural_reason=reason,attempt=attempt,seconds=time.perf_counter()-tick,budget=budget))
                        print('[SOURCE_COURSE_PROGRESS] '+json.dumps(dict(lane=lane,root=item['root'][:12],attempt=attempt,
                            accepted=candidate is not None,structural_reason=reason,confirmed_sources=sum(counts.values())),ensure_ascii=False),flush=True)
                        if candidate is not None:
                            canon.append(dict(item=item,candidate=candidate,question=parsed['parsed_content']['user_text']));counts[lane]+=1;break
                        feedback=reason
                    results.append(dict(root=item['root'],lane=lane,attempts=attempt,accepted=candidate is not None))
                metrics=dict(memory=session.memory(),telemetry=reader.snapshot(),persistent=source.snapshot())
        complete=sum(counts.values())==576;rc=0 if complete else 8;status='TEACHER_COURSE_COMPLETE' if complete else 'SOURCE_ACCEPTANCE_SHORT'
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 9;status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR';metrics['error']=dict(type=type(exc).__name__,reason=str(exc)[:1200])
    finally:
        result=dict(info(),source_deck_sha256=public.digest(OUTPUT/'sources_report.json'),status=status,returncode=rc,
            counts=dict(counts),confirmed_sources=sum(counts.values()),results=results,metrics=metrics,
            raw_manifest=raw.close(lineage=info()),candidate_manifest=canon.close(lineage=info()),whole_sec=time.perf_counter()-began,
            semantic_truth='PSEUDO_UNVERIFIED; no online meaning/word blacklist',source_raw='IGNORED_HF')
        training.write(target/'report.json',result);training.write(EVIDENCE/'teacher_report.json',result)
    return rc


def corpus():
    from tokenizers import Tokenizer
    report=json.loads((OUTPUT/'teacher/report.json').read_text())
    if report['status']!='TEACHER_COURSE_COMPLETE' or report['code_sha256']!=info()['code_sha256']:raise FileNotFoundError('same-code complete576 sources required')
    if CORPUS.exists():raise FileExistsError('frozen corpus preserved')
    tok=Tokenizer.from_file(str(public.TOKENIZER));CORPUS.mkdir();writers={s:ShardWriter(CORPUS,s) for s in ('train','val')};counts={s:Counter() for s in writers};roots={s:set() for s in writers}
    for item in public.stream_rows(OUTPUT/'teacher',report['candidate_manifest']):
        split=item['item']['split'];candidate=item['candidate'];roots[split].add(item['item']['root'])
        for row in data.views(candidate,item['question'],split):
            r=data.record(row,tok);counts[split].update(rows=1,actual_x_tokens=r.x_tokens,assistant_targets=r.targets,reference_targets=data.native_count(r))
            writers[split].append(row)
    if roots['train']&roots['val'] or len(roots['train'])!=512 or len(roots['val'])!=64:raise ValueError('source group counts/overlap differs')
    manifests={s:w.close(lineage=info()) for s,w in writers.items()}
    value=dict(info(),status='COURSE_FROZEN',manifests=manifests,counts={s:dict(c) for s,c in counts.items()},
        source_root_overlap=0,teacher_report_sha256=public.digest(OUTPUT/'teacher/report.json'),unique_source_groups={'train':512,'val':64},
        scope='source-required QA/absence contrast; not universal missing-intent classifier or75M corpus')
    training.write(CORPUS/'report.json',value);training.write(EVIDENCE/'corpus_report.json',value)
    print('[SOURCE_COURSE_CORPUS] '+json.dumps(value['counts']));return 0


def read_course():
    r=json.loads((CORPUS/'report.json').read_text())
    if r['code_sha256']!=info()['code_sha256']:raise ValueError('same frozen code required')
    return r,{s:list(public.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}


def train(args):
    weight=0. if args.arm=='sft_only' else .1
    def metadata():return dict(info(),reference_weight=weight)
    with ExitStack() as scope:
        for name,value in [('TAG',TAG),('CORPUS',CORPUS),('EVIDENCE',LOCAL),('read_course',read_course),('info',metadata),
                           ('ARMS',{'sft_only':('parent_ntp',5e-5),'reference_lm':('parent_ntp',5e-5)})]:scope.enter_context(patch.object(prior,name,value))
        with data.ReferenceObjective(weight) as objective:
            rc=prior.train(args)
            r=json.loads((LOCAL/args.arm/'report.json').read_text())
            r.update(reference_target_events=objective.executed_targets,reference_weight=weight,
                extra_input_tokens=0,teacher_answer_exact_agreement_not_truth=True,
                raw_answers='LOCAL_ONLY_MAY_CONTAIN_THIRD_PARTY_SOURCE',formal_train_ready=False)
            training.write(EVIDENCE/(args.arm+'_report.json'),r)
            return rc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','generate','corpus','train'),required=True)
    p.add_argument('--arm',choices=('sft_only','reference_lm'),default='sft_only');p.add_argument('--max-wall-sec',type=int,default=7200)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=9000:p.error('bounded experiment window60..9000')
    try:
        if a.check_only:
            if a.mode=='train':read_course()
            elif a.mode=='generate':read_deck()
            print('[CHECK_ONLY] '+json.dumps(info()));return 0
        return {'freeze':freeze,'generate':lambda:generate(a),'corpus':corpus,'train':lambda:train(a)}[a.mode]()
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc));return 8
    except KeyboardInterrupt:return 130
    except Exception as exc:print('[SOURCE_COURSE_ERROR] '+type(exc).__name__+': '+str(exc));return 9

if __name__=='__main__':raise SystemExit(main())
