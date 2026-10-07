"""Quota controller for public C plus source-grounded Gemma B.

Pure admission state, immutable source lineage and bounded learner adapters.
The producer never treats a teacher answer as a verified gold label.
"""
from __future__ import annotations
from collections import Counter
import copy
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_capability_corpus as capability
from scripts.p106b_mixed_scale import ROOT, GOAL, TOK_SHA, digest, safe_repo_path
from scripts.p106b_shards import ShardWriter, verify
from tinylm.data.sft import conversation_split_key

BASE_SHA='774E2CBA5DAD402C24F9A70555D0F5ACC1F660BF83BAFE793BC7E4BED9727814'
OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_deficit_v1'
CORPUS=ROOT/'HF/sft_ready/p106b_capability_gemma_v2'
WIRE=ROOT/'HF/sft_ready/p106b_capability_gemma_wire_v2'
STUDENT=ROOT/'HF/sft_ready/p106b_capability_gemma_student_v2'
TAG='p106b_s4_gemma_capability300m_chat32_s1337'
WEIGHTS={'qa':.5,'json':.25,'multiturn':.25}


def rows(directory,manifest):
    verify(directory,manifest)
    for spec in manifest['shards']:
        with (directory/spec['path']).open(encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)


class Quotas:
    def __init__(self,tok,*,goal=GOAL):
        self.goal=goal;self.validation=capability.CapabilitySelector(tok,goal=2**60)
        self.tokens=Counter();self.targets=Counter();self.counts=Counter();self.family=Counter();self.task=Counter()
        self.seen=set();self.questions=set();self.rejections=Counter()

    def quota(self,split):return self.goal if split=='train' else max(1,self.goal//19)

    def source_split(self,key):return 'val' if int.from_bytes(bytes.fromhex(key)[:4],'big')%20==0 else 'train'

    def profile(self,split,language,family,key):
        lane=split+':'+language;quota=self.quota(split)
        if ((key,language) in self.seen or bytes.fromhex(key) in self.validation.probes or self.tokens[lane]>=quota
                or max(1,quota//4)-self.family[lane+':'+family]<16):
            return None
        return max(WEIGHTS,key=lambda p:quota*WEIGHTS[p]-self.task[lane+':'+p])

    def admit(self,row,*,base=False):
        row=copy.deepcopy(row);meta=row['meta'];key=meta['parent_concept_id'];lang=meta['language']
        split=self.source_split(key);profile=meta.get('capability_profile',meta.get('task_profile'))
        if profile not in WEIGHTS or lang not in ('ko','en'):
            raise ValueError('language/task provenance incomplete')
        if (key,lang) in self.seen: self.rejections['same_source_concept_language']+=1;return None
        question=conversation_split_key(row).hex().upper()
        if question in self.questions:self.rejections['same_learner_question']+=1;return None
        self.validation.seen.clear()
        checked=self.validation.consider(row)
        if checked is None:self.rejections['technical_mask_context_or_probe']+=1;return None
        _,row=checked;meta=row['meta'];size,sup=meta['processed_x_tokens'],meta['assistant_targets']
        quota=self.quota(split);lane=split+':'+lang;family=capability.engine.family_bucket(meta['source_family'])
        if (self.tokens[lane]>=quota or self.tokens[lane]+size>=quota+1024
                or self.family[lane+':'+family]+size>max(1,quota//4)
                or self.task[lane+':'+profile]+size>int(quota*WEIGHTS[profile]*1.04)+1023):
            if base:raise ValueError('pinned base row exceeds original quota contract')
            self.rejections['quantity_family_task_cap']+=1;return None
        # The generated question must not move the ORIGINAL concept to another split.
        meta.update(parent_concept_id=key,source_group_id=key,source_split=split,
                    capability_profile=profile,selection_family=family,
                    capability_derivation=capability.VERSION,semantic_truth='NOT_REVIEWED')
        self.seen.add((key,lang));self.questions.add(question)
        self.tokens[lane]+=size;self.targets[lane]+=sup;self.counts[lane]+=1
        self.family[lane+':'+family]+=size;self.task[lane+':'+profile]+=size
        return row

    def report(self):
        deficit={lang:max(0,self.goal-self.tokens['train:'+lang]) for lang in ('ko','en')}
        task_deficit={lang+':'+p:max(0,int(self.goal*WEIGHTS[p]*.9)-self.task['train:'+lang+':'+p])
                      for lang in ('ko','en') for p in WEIGHTS}
        val_deficit={lang:max(0,self.quota('val')-self.tokens['val:'+lang]) for lang in ('ko','en')}
        ready=not any(deficit.values()) and not any(task_deficit.values()) and not any(val_deficit.values())
        return dict(nonpadding_tokens=dict(self.tokens),assistant_targets=dict(self.targets),rows=dict(self.counts),
            family_tokens=dict(self.family),task_tokens=dict(self.task),teacher_deficit_tokens=deficit,
            task_deficit_tokens=task_deficit,validation_deficit_tokens=val_deficit,token_target_ready=ready,
            intended_task_share=WEIGHTS,source_cap_tokens_train=self.goal//4,selection_rejected=dict(self.rejections),
            capability_selection_version=capability.VERSION,production_version='GEMMA_DEFICIT_ORIGINAL_CONCEPT_V1',
            split='original concept hash modulo20; generated variants retain original split',
            formal_train_ready=False,semantic_quality='NOT_REVIEWED',student_training='NOT_RUN')


def base_report():
    path=safe_repo_path(capability.PUBLIC/'report.json')
    if digest(path)!=BASE_SHA:raise ValueError('original partial C report changed')
    report=json.loads(path.read_text(encoding='utf-8'))
    if report.get('tokenizer_sha256')!=TOK_SHA:raise ValueError('base tokenizer mismatch')
    return report


def base_rows(report):
    for split in ('train','val'):
        manifest=json.loads(safe_repo_path(capability.PUBLIC/(split+'_shards_manifest.json')).read_text(encoding='utf-8'))
        if manifest['concat_sha256']!=report[split+'_concat_sha256']:raise ValueError('base concat differs')
        yield from rows(capability.PUBLIC,manifest)


def batch_reports():
    reports=sorted(OUTPUT.glob('batch_*/report.json'))
    directories=sorted(p for p in OUTPUT.glob('batch_*') if p.is_dir())
    if len(reports)!=len(directories):raise FileExistsError('unfinished batch preserved; inspect before resuming')
    for index,path in enumerate(reports):
        if path.parent.name!='batch_'+str(index).zfill(6):raise ValueError('batch sequence gap')
        safe_repo_path(path);yield path.parent,json.loads(path.read_text(encoding='utf-8'))


def generated_rows():
    for directory,report in batch_reports():
        if report.get('base_report_sha256')!=BASE_SHA:raise ValueError('batch base lineage differs')
        if 'candidate_manifest' in report:yield from rows(directory,report['candidate_manifest'])


def finalize(tok):
    safe_repo_path(CORPUS)
    if CORPUS.exists():raise FileExistsError('completed/partial merged corpus preserved')
    base=base_report();state=Quotas(tok)
    for row in base_rows(base):
        if state.admit(row,base=True) is None:raise ValueError('base dedup/count changed')
    for row in generated_rows():
        if state.admit(row) is None:raise ValueError('saved teacher admission cannot be replayed')
    report=state.report()
    if not report['token_target_ready']:raise FileNotFoundError('train/task/val quantity still short: '+json.dumps(report['teacher_deficit_tokens']))
    CORPUS.mkdir(exist_ok=False);writers={s:ShardWriter(CORPUS,s) for s in ('train','val')}
    # A read-only post-training exact-question audit uses actual learner hashes,
    # while original-concept hashes still own dedup and train/val lineage.
    connection=sqlite3.connect(CORPUS/'candidate_index.sqlite')
    try:
        connection.execute('CREATE TABLE candidates(prompt TEXT PRIMARY KEY,split TEXT,selected INTEGER,original_concept TEXT)')
        for stream in (base_rows(base),generated_rows()):
            for row in stream:
                from tinylm.data.sft import encode_conversation,sft_targets
                row=copy.deepcopy(row);ids,labels,_=encode_conversation(row,tok);x,y=sft_targets(ids,labels)
                row['meta'].update(processed_x_tokens=len(x),assistant_targets=sum(v>=0 for v in y))
                split=row['meta']['source_split'];writers[split].append(row)
                connection.execute('INSERT INTO candidates VALUES(?,?,1,?)',
                    (conversation_split_key(row).hex().upper(),split,row['meta']['parent_concept_id']))
        connection.commit()
    finally:connection.close()
    report.update(schema='P106B_MIXED_PUBLIC_C_V1',sources=base['sources'],tokenizer_sha256=TOK_SHA,
        base_report_sha256=BASE_SHA,student_micro=8,student_accum=16,checkpoint_on=True,epochs=4,
        status='PUBLIC_C_TOKEN_TARGET_READY',target_processed_tokens=300_000_000)
    for split,writer in writers.items():
        manifest=writer.close(lineage=dict(base_report_sha256=BASE_SHA,production_version=report['production_version']))
        verify(CORPUS,manifest);report[split+'_concat_sha256']=manifest['concat_sha256']
    with (CORPUS/'report.json').open('x',encoding='utf-8') as file:
        json.dump(report,file,ensure_ascii=False,indent=2);file.write('\n')
    return report


def learner(wire,*,execute=False):
    from scripts import diag_p106b_mixed_repeat4 as learning
    p=safe_repo_path(CORPUS/'report.json');digest(p);report=json.loads(p.read_text(encoding='utf-8'))
    if (report.get('production_version')!='GEMMA_DEFICIT_ORIGINAL_CONCEPT_V1'
            or report.get('base_report_sha256')!=BASE_SHA or report.get('token_target_ready') is not True
            or set(report.get('task_deficit_tokens',{}))!={l+':'+t for l in ('ko','en') for t in WEIGHTS}
            or any(report['task_deficit_tokens'].values())):
        raise FileNotFoundError('completed Gemma75M corpus required; no student started')
    output=WIRE if wire else STUDENT
    final=output/'student.pt' if wire else ROOT/('runs/ckpt/m100s10_ko-en_300M_'+TAG+'.pt')
    log=output/'student.json' if wire else ROOT/('runs/logs/m100s10_ko-en_300M_'+TAG+'.json')
    with patch.object(learning,'PUBLIC',CORPUS),patch.object(learning,'OUTPUT',output),\
         patch.object(learning,'FINAL',final),patch.object(learning,'LOG',log):
        corpus,specs,info=learning.check(wire=False)
    if not wire:
        saved=json.loads(safe_repo_path(WIRE/'report.json').read_text(encoding='utf-8'))
        learning.require_wire_report(saved,specs['train']['concat_sha256'],specs['val']['concat_sha256'])
    info.update(scope='WIRE_TWO_UPDATES_NOT_300M' if wire else 'FOUR_REAL_EPOCHS',epochs=1 if wire else 4)
    if not execute:return info
    with patch.object(learning,'TAG',TAG):
        return learning.execute(corpus,specs,info,wire=wire)


def evaluate(*,execute=False):
    from scripts import diag_p106b_refill_multiaxis as evaluation
    corpus_sha=digest(safe_repo_path(CORPUS/'report.json'))
    output=ROOT/'HF/sft_ready/p106b_gemma_capability_multiaxis_v2'
    child=ROOT/('runs/ckpt/m100s10_ko-en_300M_'+TAG+'.pt')
    log=ROOT/('runs/logs/m100s10_ko-en_300M_'+TAG+'.json')
    with patch.object(evaluation,'CORPUS',CORPUS),patch.object(evaluation,'CORPUS_SHA',corpus_sha),\
         patch.object(evaluation,'OUTPUT',output),patch.object(evaluation,'CHILD',child),patch.object(evaluation,'CHILD_LOG',log):
        info=evaluation.check()
        if not execute:return info
        return evaluation.execute(info)
