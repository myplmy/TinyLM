#!/usr/bin/env python3
"""User-only public QA-candidate/JSON/explicit-memory-turn corpus and300M path.

Source task routing is metadata, never a blacklist of allegedly wrong phrases.
JSON and memory follow-ups are code-authored wrappers of original content, not
new verified knowledge or natural-human conversations. One variant per source
first-question group; shortages are not filled by repetition. No downloads.
"""
from __future__ import annotations
import argparse
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_balanced_public as engine
from scripts.p106b_mixed_scale import digest,safe_repo_path,TOKENIZER,TOK_SHA,GOAL
from scripts.p106b_public_refill import english_rows
from tinylm.chat.canonical import normalize,validate
from tinylm.data.sft import conversation_split_key,encode_conversation,sft_targets

UPSTREAM=ROOT/'HF/sft_ready/p106b_mixed_public_v3_en_refill/report.json'
UPSTREAM_SHA='5035CAD5B9B357AB63B8C69F3C73E2D9BAE5E4A76179ECB32EFE2AE4C1A9D005'
PUBLIC=ROOT/'HF/sft_ready/p106b_capability_public_v1'
VERSION='CAPABILITY_QA_FORMAT_MULTITURN_V1'
# Explicit upstream task-family identifiers, not an answer-content classifier.
QA_FAMILIES={'aya_dataset','Aya-Dataset','oasst1','oasst2','openassistant',
             'Flan-Coqa','NQ-Open','MLQA-inst','SQuAD-inst','TyDiQA-inst','Dolly-15k-inst'}
PROFILES=('qa','json','multiturn')
_TOK=None
_ROUTE_COUNTS=Counter()


class CapabilitySelector(engine.Selector):
    def __init__(self,tok,*,goal=GOAL,probe_keys=()):
        from scripts.p106b_refill_eval_panel import panel
        p=panel();cases=p['singles']+[t for e in p['episodes'] for t in e['turns']]
        extra=[conversation_split_key(normalize(dict(messages=[dict(role='user',content=c['question']),
                                                              dict(role='assistant',content='probe')]))) for c in cases]
        super().__init__(tok,goal=goal,probe_keys=[*probe_keys,*extra])

    def consider(self,row):
        users=[m for m in row['messages'] if m['role']=='user']
        for message in users[1:]:
            key=conversation_split_key(normalize(dict(messages=[message,dict(role='assistant',content='probe')])))
            if key in self.probes:
                self.rejections['fixed_eval_followup_question']+=1;return None
        return super().consider(row)


def text(message):
    blocks=message.get('content',[])
    if isinstance(blocks,str):return blocks
    if any(b.get('type')!='text' for b in blocks):raise ValueError('nontext source needs a separate adapter')
    return ''.join(b['text'] for b in blocks)


def derive(row):
    """Preserve the first user question, so all variants share a split/dedup key."""
    row=validate(normalize(copy.deepcopy(row)))
    msgs=row['messages'];body=msgs[1:] if msgs[0]['role']=='system' else msgs
    if len(body)<2 or any(m['role']!=('user' if i%2==0 else 'assistant') for i,m in enumerate(body)):
        return None
    if body[-1]['role']!='assistant':return None
    language=row['meta'].get('language')
    if language not in ('ko','en'):return None
    family=engine.family_bucket(row['meta']['source_family'])
    source_id=conversation_split_key(row).hex().upper()
    if len(body)>=4:
        profile,nature='multiturn','source_role_sequence'
    else:
        if family not in QA_FAMILIES:return None
        h=int(hashlib.sha256(('CAPABILITY_TASK_V1:'+source_id).encode()).hexdigest()[:8],16)%4
        profile='qa' if h<2 else 'json' if h==2 else 'multiturn'
        nature='not_multiturn' if profile!='multiturn' else 'code_authored_memory_followup'
        answer=text(body[-1])
        if profile=='json':
            # A separate finite value range in val exposes template/value memorization.
            split_value=int.from_bytes(bytes.fromhex(source_id)[:4],'big')%20
            is_val=split_value==0
            n=(80+int(source_id[:8],16)%19) if is_val else (2+int(source_id[:8],16)%78)
            key=('result','count','value','number')[int(source_id[8:10],16)%4]
            question=(f'출력 형식 연습: 키 {key}, 정수 값 {n}인 JSON 객체 한 개만 작성하세요.' if language=='ko'
                      else f'Output-format exercise: return only one JSON object with key {key} and integer value {n}.')
            row['messages']=msgs+[dict(role='user',content=question),
                                  dict(role='assistant',content=json.dumps({key:n}))]
            nature='code_authored_format_followup'
            row['meta']['control_output_contract']=dict(kind='UNIQUE_JSON',key=key,value=n,
                producer='code',truth_scope='explicit requested format/value, not source factual truth')
        elif profile=='multiturn':
            # Deterministic grounding/role-memory task, explicitly not a new fact.
            q2='다음 요청을 위해 준비만 해 주세요. 준비 한 단어만 쓰세요.' if language=='ko' else 'Get ready for my next request. Reply only READY.'
            a2='준비' if language=='ko' else 'READY'
            q3='첫 질문에 했던 답변 전체를 answer 키 하나의 JSON으로만 다시 쓰세요.' if language=='ko' else 'Return your complete answer to my first question as JSON with exactly one key: answer.'
            row['messages']=msgs+[dict(role='user',content=q2),dict(role='assistant',content=a2),
                                  dict(role='user',content=q3),dict(role='assistant',content=json.dumps({'answer':answer},ensure_ascii=False))]
    row=validate(normalize(row))
    if conversation_split_key(row).hex().upper()!=source_id:raise ValueError('source question group changed')
    row['meta'].update(capability_profile=profile,multiturn_kind=nature,source_group_id=source_id,
        capability_derivation=VERSION,semantic_truth='NOT_REVIEWED',
        knowledge_claim='original source content, no claim of new unique facts')
    return row


def transformed_rows(spec):
    from tokenizers import Tokenizer
    global _TOK
    if _TOK is None:_TOK=Tokenizer.from_file(str(TOKENIZER))
    for row in english_rows(spec):
        _ROUTE_COUNTS['original_rows']+=1
        item=derive(row)
        if item is None:
            _ROUTE_COUNTS['unassigned_source_task_or_role']+=1;continue
        original_ids,_,_=encode_conversation(row,_TOK)
        item['meta']['original_source_x_tokens']=max(0,len(original_ids)-1)
        _ROUTE_COUNTS[item['meta']['capability_profile']]+=1
        yield item


_INITIALIZE=engine.initialize_index
_INDEX=engine.index_row


def initialize(connection):
    _INITIALIZE(connection)
    connection.execute('CREATE TABLE capability(prompt TEXT PRIMARY KEY,profile TEXT,nature TEXT,source_tokens INTEGER)')


def index(connection,row,source,ordinal):
    _INDEX(connection,row,source,ordinal)
    key=row['meta']['parent_concept_id']
    owner=connection.execute('SELECT source,ordinal,choice FROM candidates WHERE prompt=?',(key,)).fetchone()
    payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    choice=hashlib.sha256(payload.encode()).hexdigest()
    if owner==(source,ordinal,choice):
        m=row['meta'];connection.execute('INSERT OR REPLACE INTO capability VALUES(?,?,?,?)',
             (key,m['capability_profile'],m['multiturn_kind'],m['original_source_x_tokens']))


def select(connection,goal=GOAL):
    connection.execute('CREATE INDEX rank_order ON candidates(rank,prompt)')
    tokens=Counter();targets=Counter();rows=Counter();families=Counter();task=Counter();kinds=Counter();source_tokens=Counter();rejected=Counter()
    # Intended50/25/25, >=90percent of each target share, <=104percent.
    weights={'qa':.50,'json':.25,'multiturn':.25}
    query='SELECT c.prompt,c.split,c.language,c.family,c.tokens,c.targets,p.profile,p.nature,p.source_tokens FROM candidates c JOIN capability p USING(prompt) ORDER BY c.rank,c.prompt'
    for key,split,lang,family,size,sup,profile,nature,original in connection.execute(query):
        quota=goal if split=='train' else max(1,goal//19)
        lane=split+':'+lang;fam=lane+':'+family;tk=lane+':'+profile
        if tokens[lane]>=quota:rejected['language_full']+=1;continue
        if tokens[lane]+size>=quota+1024:rejected['language_overshoot']+=1;continue
        if families[fam]+size>max(1,quota//4):rejected['source_cap']+=1;continue
        if task[tk]+size>int(quota*weights[profile]*1.04)+1023:rejected['task_cap']+=1;continue
        connection.execute('UPDATE candidates SET selected=1 WHERE prompt=?',(key,))
        tokens[lane]+=size;targets[lane]+=sup;rows[lane]+=1;families[fam]+=size;task[tk]+=size
        kinds[lane+':'+nature]+=1;source_tokens[lane]+=original
    connection.commit()
    deficit={lang:max(0,goal-tokens['train:'+lang]) for lang in ('ko','en')}
    task_deficit={lang+':'+p:max(0,int(goal*weights[p]*.90)-task['train:'+lang+':'+p]) for lang in ('ko','en') for p in PROFILES}
    shares={k:v/tokens[':'.join(k.split(':')[:2])] for k,v in families.items()}
    ready=not any(deficit.values()) and not any(task_deficit.values())
    return dict(rows=dict(rows),nonpadding_tokens=dict(tokens),assistant_targets=dict(targets),
        family_tokens=dict(families),actual_selected_family_shares=shares,selection_rejected=dict(rejected),
        partial_source_balance_warning=any(v>.25 for v in shares.values()),source_cap_tokens_train=goal//4,
        teacher_deficit_tokens=deficit,task_deficit_tokens=task_deficit,token_target_ready=ready,
        unique_prompt_groups=connection.execute('SELECT COUNT(*) FROM candidates').fetchone()[0],
        capability_selection_version=VERSION,task_tokens=dict(task),multiturn_kind_rows=dict(kinds),
        original_source_x_tokens=dict(source_tokens),intended_task_share=weights,
        minimum_task_share_multiplier=.90,maximum_task_share_multiplier=1.04,
        cap_basis='target tokens, not a semantic quality score',
        source_task_assignment='explicit metadata family candidates; no per-row truth claim',
        natural_dialogue_claim='source_role_sequence and code_authored_memory_followup reported separately',
        controlled_format_value_ranges=dict(train=[2,79],val=[80,98]),
        source_routing_counts=dict(_ROUTE_COUNTS),
        fixed_question_exclusion='old8 and additional36 first-question hashes; semantic contamination NOT_RUN')


def sources():
    safe_repo_path(UPSTREAM)
    if digest(UPSTREAM)!=UPSTREAM_SHA:raise ValueError('pinned public source report changed')
    specs=json.loads(UPSTREAM.read_text(encoding='utf-8'))['sources']
    for spec in specs:
        path=ROOT/spec['path'];safe_repo_path(path)
        if path.parts[len(ROOT.parts):len(ROOT.parts)+2]!=('HF','sft_sources'):
            raise ValueError('only exact public sft_sources permitted')
        if not path.is_file():raise FileNotFoundError('public source missing: '+spec['path'])
    return specs


def build(execute=False):
    safe_repo_path(PUBLIC)
    if PUBLIC.exists() or PUBLIC.is_symlink():raise FileExistsError('new version required; old/partial output preserved')
    specs=sources()
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('tokenizer differs')
    if not execute:
        print('[CAPABILITY_PREFLIGHT] '+json.dumps(dict(sources=specs,output=str(PUBLIC.relative_to(ROOT)),
              version=VERSION,full_source_content_hash='USER_BUILD_ONLY',data_created=False,model_loading='NOT_RUN'),ensure_ascii=False));return 0
    # Full content verification and two source passes are user CPU/disk work.
    for spec in specs:
        if digest(ROOT/spec['path'])!=spec['sha256']:raise ValueError('source content changed')
    engine.OUTPUT=PUBLIC;engine.rows_for=transformed_rows;engine.initialize_index=initialize
    engine.index_row=index;engine.select_index=select;engine.Selector=CapabilitySelector
    rc=engine.execute(specs)
    report=json.loads((PUBLIC/'report.json').read_text(encoding='utf-8'))
    print('[CAPABILITY_FINAL] '+json.dumps(dict(token_target_ready=report['token_target_ready'],
        language_deficit=report['teacher_deficit_tokens'],task_deficit=report['task_deficit_tokens'],
        original_source_x_tokens=report['original_source_x_tokens'],multiturn_kind_rows=report['multiturn_kind_rows'],
        semantic_quality='NOT_REVIEWED'),ensure_ascii=False),flush=True)
    return 0 if rc==0 and report['token_target_ready'] else 8


def learner(mode,execute=False):
    from scripts import diag_p106b_mixed_repeat4 as learning
    source=PUBLIC/'report.json';safe_repo_path(source)
    if not source.is_file():raise FileNotFoundError('new capability corpus not built')
    contract=json.loads(source.read_text(encoding='utf-8'))
    required={lang+':'+task for lang in ('ko','en') for task in PROFILES}
    if (contract.get('token_target_ready') is not True
        or set(contract.get('task_deficit_tokens',{}))!=required
        or any(contract['task_deficit_tokens'].values())):
        raise FileNotFoundError('language/task quota incomplete; preserve deficit report before any model loading')
    wire=mode=='wire'
    corpus,specs,info=learning.check(wire=wire,capability=True)
    if not execute:print('[CAPABILITY_LEARNER_PREFLIGHT] '+json.dumps(info));return 0
    return learning.execute(corpus,specs,info,wire=wire)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('build','wire','train'),required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    try:return build(a.execute) if a.mode=='build' else learner(a.mode,a.execute)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except KeyboardInterrupt:print('[INTERRUPTED] new partial output preserved',file=sys.stderr);return 130
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
