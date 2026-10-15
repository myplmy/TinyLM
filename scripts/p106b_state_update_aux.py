"""Code-proven two-turn record updates; no inference-time answer replacement."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import defaultdict
import copy
import json
from unittest.mock import patch
from scripts import p106b_binding_auxiliary as earlier
from tinylm.chat.canonical import normalize,validate
source=earlier.prior.source
VERSION='P106B_STATE_UPDATE_AUX_V1'
ORIGINAL_SUFFIX_SUM=earlier.suffix_auxiliary_sum


def fact_key(row):
    m=row['meta'];family=m.get('property_kind',m['kind'].removeprefix('binding_'))
    return source.sha([m['language'],family,sorted(m.get('initial_values',m.get('mapping',{})).items())])


def render_value(value,mode):
    if mode=='scalar':return value
    if mode=='json':return json.dumps(dict(answer=value),ensure_ascii=False,separators=(',',':'))
    raise ValueError('known scalar/answer-object producer only')


def updated_row(original,updated,asked,mode):
    r=copy.deepcopy(original);m=r['meta'];language=m['language'];family=m['kind'].removeprefix('binding_')
    mapping=m['mapping'];available={'color':{'ko':['빨강','파랑','노랑','초록','보라','주황'],
        'en':['red','blue','yellow','green','purple','orange']},'department':{
        'ko':['산수과','문법과','물리학과','역사학과','음악과','미술과'],
        'en':['Physics','History','Music','Art','Math','Grammar']}}[family][language]
    unused=[v for v in available if v not in mapping.values()]
    fresh=unused[int(fact_key(original)[:8],16)%len(unused)];current={**mapping,updated:fresh};value=current[asked]
    if language=='ko':
        subject=f'{asked}의 현재 색상' if family=='color' else f'{asked} 건물의 현재 학과'
        change=f'기록 정정: {updated}의 색상은 이제 {fresh}입니다.' if family=='color' else f'기록 정정: {updated} 건물의 학과는 이제 {fresh}입니다.'
        objective=subject+('을' if family=='color' else '를')
        request=f'수정된 기록을 기준으로 {subject}만 답하세요.' if mode=='scalar' else f'수정된 기록을 기준으로 {objective} answer 항목에 넣은 JSON 객체 하나만 답하세요.'
        r['messages'][0]['content'][0]['text']='가상 기록입니다.\n'+r['messages'][0]['content'][0]['text']
    else:
        subject=f'the current color of {asked}' if family=='color' else f'the current department in the {asked} building'
        change=f'Record update: {updated} is now {fresh}.' if family=='color' else f'Record update: the {updated} building now houses {fresh}.'
        request=f'Give only {subject}, using the updated record.' if mode=='scalar' else f'Return one JSON object with key answer holding {subject}, using the updated record.'
        r['messages'][0]['content'][0]['text']='Fictional record.\n'+r['messages'][0]['content'][0]['text']
    root=source.sha(dict(task=VERSION,language=language,family=family,mapping=mapping,new_value=fresh))
    previous=source.text(r,-1);initial_asked=m['requested_entity']
    r['messages'] += [dict(role='user',content=change+'\n'+request),dict(role='assistant',content=render_value(value,mode))]
    m.update(kind='state_update_'+family,property_kind=family,initial_values=copy.deepcopy(mapping),current_values=current,
        new_value=fresh,updated_entity=updated,initial_requested_entity=initial_asked,final_requested_entity=asked,
        final_format=mode,requested_entity=asked,target_updated=asked==updated,previous_gold_value=previous,
        semantic_root_id=root,base_mapping_signature=fact_key(original),course_version=VERSION,
        rubric='EXACT_SCALAR' if mode=='scalar' else 'EXACT_JSON_OBJECT',
        turn_rubrics=['EXACT_SCALAR','EXACT_SCALAR' if mode=='scalar' else 'EXACT_JSON_OBJECT'],
        previous_value_copy_correct=previous==value,old_lookup_ignoring_update_correct=mapping[asked]==value,
        truth='PRODUCER_CODE_FACT_CONTRACT',named_entities='FICTIONAL_IDENTIFIERS_NOT_REAL_PERSON_FACTS')
    return validate(normalize(r))


def state_views(group,split):
    if len(group)!=4:raise ValueError('four complete base views required')
    output=[]
    for original in group:
        m=original['meta'];entities=list(m['mapping']);order=int(m['ordered_entities']!=entities)
        for updated in entities:
            for index,asked in enumerate(entities):
                changed=int(updated==asked)
                for mode in ('scalar','json'):
                    if split=='test':
                        first=asked if (order^changed)==0 else next(e for e in entities if e!=asked)
                        chosen_format=('scalar','json')[order^index^changed]
                        if m['requested_entity']!=first or mode!=chosen_format:continue
                    output.append(updated_row(original,updated,asked,mode))
    if len(output)!=(8 if split=='test' else 32):raise ValueError('balanced update view size differs')
    return output


def build_rows(existing):
    declared={language:{s:(earlier.NAMES[language] if s=='test' else source.NAMES[language][s])
        for s in ('train','dev','test')} for language in ('ko','en')}
    result={};used_old={fact_key(r) for v in existing.values() for r in v if r['meta']['kind'].startswith('binding_')}
    for split,base_n,state_n in (('train',320,64),('dev',32,8),('test',32,16)):
        with patch.object(source,'NAMES',declared):candidates=source.binding_rows(split,per_family=1024)
        groups=defaultdict(lambda:defaultdict(list))
        for original in candidates:
            row=earlier.prior.correct_own_question(original)
            if fact_key(row) in used_old:continue
            m=row['meta'];groups[(m['language'],m['kind'])][fact_key(row)].append(row)
        basic=[];states=[]
        for lane,by_fact in sorted(groups.items()):
            values=list(by_fact.values())
            if len(values)<base_n+state_n:raise ValueError('fresh fictional fact supply exhausted')
            for group in values[:base_n]:
                for row in group:
                    item=copy.deepcopy(row);item['meta'].update(course_version=VERSION,source_split=split,
                        semantic_root_id=source.sha([VERSION,'basic',fact_key(row)]))
                    basic.append(item)
            for group in values[base_n:base_n+state_n]:states.extend(state_views(group,split))
        result[split]=states+basic
    result['dev'] += [copy.deepcopy(r) for r in existing['dev'] if r['meta']['kind']=='public_qa']
    result['public_eval']=copy.deepcopy(existing['public_eval'])
    return result


def approved(rows):
    return {source.sha(r['messages']):copy.deepcopy(r['meta']) for r in rows if r['meta']['kind'].startswith('state_update_')}


def label(row,contract):
    m=row['meta']
    if not m['kind'].startswith('state_update_'):return None
    signature=source.sha(row['messages']);trusted=contract.get(signature)
    if trusted is None or m.get('course_version')!=VERSION:raise ValueError('exact state producer conversation required')
    for field in ('initial_values','current_values','new_value','updated_entity','initial_requested_entity',
                  'final_requested_entity','final_format','semantic_root_id','ordered_entities'):
        if m[field]!=trusted[field]:raise ValueError('untrusted state metadata: '+field)
    old=m['initial_values'];current=m['current_values'];updated=m['updated_entity'];asked=m['final_requested_entity']
    if (len(row['messages'])!=4 or [v['role'] for v in row['messages']]!=['user','assistant','user','assistant']
            or set(old)!=set(current) or updated not in old or asked not in old or m['new_value'] in old.values()
            or current!={**old,updated:m['new_value']} or source.text(row,1)!=old[m['initial_requested_entity']]
            or source.text(row,-1)!=render_value(current[asked],m['final_format'])):
        raise ValueError('two-turn code state/gold contract differs')
    return int(updated==asked)


def last_predictor(row,record,tok):
    from tinylm.chat.serialize import serialize
    prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
    position=len(tok.encode(prompt).ids)-1
    starts=[i for i,v in enumerate(record.y) if v!=-100 and (i==0 or record.y[i-1]==-100)]
    if len(starts)!=2 or starts[-1]!=position:raise ValueError('last of two assistant predictor boundaries differs')
    return position


def final_auxiliary_sum(head,hidden,y,labels,windows,dense=False):
    """Only auxiliary mask copy changes; word SFT retains both assistant turns."""
    if dense:raise ValueError('last predictor state study only')
    copied=y.clone()
    for index,bit in enumerate(labels):
        if bit is None:continue
        positions=windows[index]
        if not positions or len(positions)!=1:raise ValueError('single final predictor required')
        mask=y[index].ne(-100);starts=(mask & ~mask.roll(1)).nonzero().flatten().tolist()
        if bool(mask[0]):starts=[0]+[p for p in starts if p]
        if len(starts)!=2 or starts[-1]!=positions[0]:raise ValueError('last assistant block boundary required')
        copied[index,:positions[0]]=-100
    return ORIGINAL_SUFFIX_SUM(head,hidden,copied,labels,windows,dense=False)
