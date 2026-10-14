"""Independent code-known balanced lookup curriculum; four passes, no teacher."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
import hashlib
import json
import random
from unittest.mock import patch
from tinylm.chat.canonical import normalize,validate
from scripts import diag_p106b_context_quality as prior
from scripts import diag_p101a_sft_mtp as training
from scripts.p106b_shards import ShardWriter,verify
TAG='p106b_binding_course_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
KO={'train':['민수','지수','진우','예린','태호','소희','하준','은서','도윤','유진','서준','수빈'],
    'val':['지후','서연','현우','채원','정우','하린','시우','예나','수호','윤아','건우','소율']}
EN={'train':['Alice','Brian','Claire','Daniel','Eva','Frank','Grace','Henry','Iris','Jack','Kate','Leon'],
    'val':['Lina','Theo','Rose','Owen','Ruby','Paul','Jade','Kyle','Tina','Ivan','Hugo','Emma']}
CODE=('scripts/diag_p106b_binding_course.py','scripts/test_p106b_binding_course.py',*prior.CODE)


def info():
    return dict(schema='P106B_CODE_KNOWN_BINDING_COURSE_V1',tag=TAG,parent_sha256=training.PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,seed=1337,micro_bs=8,accum=16,seq=1024,grad_checkpoint=True,
        compile='default',epochs=4,expected_updates=128,train_rows=4096,val_rows=512,lr=5e-5,muon_lr=2e-4,
        teacher='NONE_PROJECT_AUTHORED_CODE',mtp=False,formal_train_ready=False,world_knowledge_claim=False,
        code_sha256={p:training.data.digest(ROOT/p) for p in CODE})


def build():
    rows={};roots={}
    for split in ('train','val'):
        result=[];roots[split]=set();target=256 if split=='train' else 32
        for language in ('ko','en'):
            names=(KO if language=='ko' else EN)[split]
            for family in ('color','department'):
                values=(['빨강','파랑','노랑','초록','보라','주황'] if family=='color' else
                        ['산수과','문법과','물리학과','역사학과','음악과','미술과']) if language=='ko' else (
                        ['red','blue','yellow','green','purple','orange'] if family=='color' else
                        ['Physics','History','Music','Art','Math','Grammar'])
                # Canonical unordered entity pair prevents (a,b,x,y)/(b,a,y,x)
                # from counting the same fact mapping as two independent roots.
                combos=[(a,b,x,y) for a in names for b in names if a<b for x in values for y in values if x!=y]
                rng=random.Random(str((1337,split,language,family)));rng.shuffle(combos)
                for a,b,x,y in combos[:target]:
                    mapping={a:x,b:y};root=hashlib.sha256(json.dumps([language,family,mapping],sort_keys=True).encode()).hexdigest().upper();roots[split].add(root)
                    for order in (0,1):
                        ordered=(a,b) if not order else (b,a)
                        if language=='ko':sentences=[f'{n}의 색상은 {mapping[n]}입니다.' if family=='color' else f'{n} 건물에는 {mapping[n]}가 있습니다.' for n in ordered]
                        else:sentences=[f'{n} is {mapping[n]}.' if family=='color' else f'The {n} building houses {mapping[n]}.' for n in ordered]
                        for asked in (a,b):
                            q=(f'{asked}의 색상은 무엇입니까? 색상 단어만 답하세요.' if family=='color' else f'{asked} 건물에는 어느 학과가 있습니까? 학과 이름만 답하세요.') if language=='ko' else (
                               f'What color is {asked}? Reply with only the color word.' if family=='color' else f'What department is in the {asked} building? Reply with only the department name.')
                            prefix=('제시된 자료만 근거로 답하세요. 자료가 주어지지 않으면 자료를 요청하세요.\n자료:\n' if language=='ko' else
                                    'Answer using only the supplied reference. If it is not supplied, request the reference.\nReference:\n')
                            user=prefix+' '.join(sentences)+('\n질문:\n' if language=='ko' else '\nQuestion:\n')+q
                            result.append(validate(normalize(dict(messages=[dict(role='user',content=user),dict(role='assistant',content=mapping[asked])],meta=dict(
                                source='PROJECT_AUTHORED_CODE',source_license='project_authored_fictional',language=language,
                                kind='code_binding',rubric='EXACT_SCALAR',semantic_root_id=root,parent_concept_id=root,
                                source_split=split,same_fact_mapping=mapping,requested_entity=asked,ordered_entities=list(ordered),
                                target_is_first=asked==ordered[0],reasoning_in_student=False,semantic_truth='PRODUCER_CODE_FACT_CONTRACT')))))
        # Interleave language/family while preserving all four views of each root.
        result.sort(key=lambda r:(r['meta']['semantic_root_id'],r['meta']['requested_entity'],tuple(r['meta']['ordered_entities'])))
        rows[split]=result
    if roots['train']&roots['val']:raise ValueError('root overlap')
    return rows


def freeze():
    if CORPUS.parent.exists():raise FileExistsError('preserve prior curriculum')
    from tokenizers import Tokenizer
    from tinylm.train import mtp_sft as core
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('tokenizer changed')
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));rows=build();planned={};counts={}
    for split,values in rows.items():
        c=Counter()
        for row in values:
            r=core.encode_record(row,tok)
            if r.x_tokens>1024:raise ValueError('bounded without truncation')
            c.update(rows=1,actual_x_tokens=r.x_tokens,assistant_targets=r.targets)
            c[row['meta']['language']]+=1
        counts[split]=dict(c)
    CORPUS.mkdir(parents=True,exist_ok=False)
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        planned[split]=writer.close(lineage=info());verify(CORPUS,planned[split])
    report=dict(info(),status='COURSE_FROZEN',counts=counts,manifests=planned,semantic_root_overlap=0,
        scope='finite code-known factual mappings; not new world knowledge/75M; dev old32 names excluded from train/val')
    training.write(CORPUS/'report.json',report);training.write(EVIDENCE/'corpus_report.json',report)
    print('[BINDING_CORPUS] '+json.dumps(counts));return 0


def read_course():
    r=json.loads((CORPUS/'report.json').read_text())
    if r['status']!='COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('same frozen code required')
    for m in r['manifests'].values():verify(CORPUS,m)
    return r,{s:list(training.data.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}


def train(args):
    args.arm='lookup_balanced'
    with patch.object(prior,'TAG',TAG),patch.object(prior,'CORPUS',CORPUS),patch.object(prior,'EVIDENCE',EVIDENCE), \
         patch.object(prior,'read_course',read_course),patch.object(prior,'info',info),patch.object(prior,'ARMS',{'lookup_balanced':('parent_ntp',5e-5)}):
        return prior.train(args)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('corpus','train'),required=True);p.add_argument('--max-wall-sec',type=int,default=1200)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=1200:p.error('bounded60..1200')
    if args.check_only:
        if args.mode=='train':read_course()
        print('[CHECK_ONLY] '+json.dumps(info()));return 0
    if args.execute:return freeze() if args.mode=='corpus' else train(args)
    p.error('explicit mode required')

if __name__=='__main__':raise SystemExit(main())
