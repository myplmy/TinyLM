"""Same-domain sufficient/absent/ambiguous fictional records, code-owned truth.

Finite source grammars are producer controls, not an online semantic blacklist.
Old courses and real-world teacher corpora are not mutated or claimed expanded.
"""
from __future__ import annotations
import json
import random
from tinylm.chat.canonical import normalize,validate
from scripts.p106b_context_quality import sha,text,teacher_payload
VERSION='P106B_BROAD_MATCHED_CONTEXT_V2'
KINDS=('building','speech','library','book','item','trpg','boolean','arithmetic')
VALUES={'ko':{
 'building':('해양연구소','천문학과','로봇연구실','문헌보관소','역사학과','생물연구소','음악학과','경제연구소'),
 'speech':('달빛광장','새봄공원','나래강당','한울홀','은하공원','서쪽광장','평화회관','해솔정원'),
 'library':('해솔마을 북쪽','남문광장 서쪽','달빛공원 옆','누리역 남쪽','중앙거리 동쪽','바다마을 입구','나래학교 뒤','동쪽언덕'),
 'book':('겨울항해','작은우주','바람의숲','잊힌지도','별의시간','오늘의노래','마지막편지','희망의봄'),
 'item':('보랏빛','녹색','주황색','은색','노란색','갈색','분홍색','검은색'),
 'trpg':('철검','나무지팡이','푸른망토','가죽방패','불꽃검','은빛활','회복물약','황금반지')},
 'en':{
 'building':('Marine Lab','Astronomy','Robot Lab','Archive Room','History','Biology Lab','Music','Economics'),
 'speech':('Moon Square','Spring Park','Nara Hall','Hanul Hall','Galaxy Park','West Square','Peace Hall','Hae Garden'),
 'library':('north of Hae Village','west of South Square','beside Moon Park','south of Nuri Station','east of Main Road','entrance of Sea Village','behind Nara School','East Hill'),
 'book':('Winter Voyage','Small Universe','Forest Wind','Lost Map','Star Time','Song Today','Last Letter','Spring Hope'),
 'item':('violet','green','orange','silver','yellow','brown','pink','black'),
 'trpg':('iron sword','wood staff','blue cloak','leather shield','fire blade','silver bow','healing potion','gold ring')}}


def make(kind,language,seed,*,novel=False):
    if kind not in KINDS or language not in ('ko','en'):raise ValueError('registered grammar required')
    r=random.Random(seed);ko=language=='ko'
    if kind=='arithmetic':
        from scripts.p106b_context_quality import make as old
        row=old(kind,language,seed,novel=novel)
        row['meta'].update(generation_version=VERSION,turn_rubrics=[row['meta']['rubric']])
        return row
    if kind=='boolean':
        names=r.sample(range(12),3);values=[r.choice((True,False)) for _ in range(3)]
        operations=[r.choice(('AND','OR','XOR')) for _ in range(2)];group=r.randrange(2)
        from scripts.p106b_context_quality import NAMES
        labels=[NAMES[language][i] for i in names]
        def op(a,b,kind):return a and b if kind=='AND' else a or b if kind=='OR' else a!=b
        answer=(op(op(values[0],values[1],operations[0]),values[2],operations[1]) if group==0 else
                op(values[0],op(values[1],values[2],operations[1]),operations[0]))
        expression=(f'({labels[0]} {operations[0]} {labels[1]}) {operations[1]} {labels[2]}' if group==0 else
                    f'{labels[0]} {operations[0]} ({labels[1]} {operations[1]} {labels[2]})')
        facts=', '.join(f'{a}={str(b).lower()}' for a,b in zip(labels,values))
        question=(f'논리 기록: {facts}. {expression}의 값만 true 또는 false로 쓰세요.' if ko else
                  f'Boolean record: {facts}. Give only {expression} as true or false.')
        if novel:question+=( '\n괄호가 지정한 계산 순서를 지켜 주세요.' if ko else
                            '\nRespect the parenthesized evaluation order.')
        root=sha(dict(task='three_variable_boolean',names=names,values=values,operations=operations,group=group))
        return validate(normalize(dict(messages=[dict(role='user',content=question),
            dict(role='assistant',content=str(bool(answer)).lower())],meta=dict(source='p106b_broad_code_reference',
                source_license='project_authored_synthetic',language=language,kind=kind,root_concept_id=root,
                semantic_root_id=root,generation_version=VERSION,rubric='EXACT_BOOLEAN',turn_rubrics=['EXACT_BOOLEAN'],
                source_condition='SUFFICIENT',world_facts='CODE_ONLY',novel_wording=novel))))
    ids=r.sample(range(1,200),3);values=r.sample(range(8),3);year=r.randrange(1900,2100)
    if year==2013:year=2101  # Earlier independent building test never becomes train.
    mode=r.randrange(10);wanted=r.randrange(2);val=VALUES[language][kind]
    prefixes={'ko':{'building':'누리관','speech':'민 대표','library':'나래도서관','book':'윤 작가','item':'상자','trpg':'용사'},
              'en':{'building':'Nuri Hall','speech':'President Min','library':'Nara Library','book':'Author Yun','item':'Box','trpg':'Hero'}}
    names=[prefixes[language][kind]+str(i) for i in ids]
    field={'ko':{'building':'입주 기관','speech':'연설 장소','library':'위치','book':'책 제목','item':'색상','trpg':'장비'},
           'en':{'building':'institution inside','speech':'speech location','library':'location','book':'book title','item':'color','trpg':'equipment'}}[language][kind]
    present=[0,1] if mode not in (4,5,9) else [0]
    qname=names[wanted]
    deictic=mode in (4,5,8,9)
    missing=(mode in (6,7) or mode==9)
    ambiguous=mode==8
    if mode in (6,7):qname=names[2]
    context=[]
    if mode!=9:
        for i in present:
            value=val[values[i]]
            if kind=='building':
                sentence=(f'{year+i}년에 완공된 {names[i]}의 입주 기관은 {value}입니다.' if ko else
                          f'{names[i]}, completed in {year+i}, houses {value}.')
            elif kind=='speech':
                sentence=(f'{names[i]}는 {value}에서 연설했습니다.' if ko else f'{names[i]} gave a speech in {value}.')
            elif kind=='library':
                sentence=(f'{names[i]}는 {value}에 있습니다.' if ko else f'{names[i]} is {value}.')
            elif kind=='book':
                sentence=(f'{names[i]}가 쓴 책의 제목은 {value}입니다.' if ko else f'{names[i]} wrote a book titled {value}.')
            elif kind=='item':
                sentence=(f'{names[i]}의 색상은 {value}입니다.' if ko else f'{names[i]} is {value}.')
            else:sentence=(f'{names[i]}의 장비는 {value}입니다.' if ko else f'{names[i]} has {value}.')
            context.append(sentence)
    if mode in (4,5):wanted=0;qname=names[0]
    noun={'ko':{'building':'그 건물','speech':'그 대표','library':'그 도서관','book':'그 작가','item':'그 상자','trpg':'그 용사'},
          'en':{'building':'that building','speech':'that president','library':'that library','book':'that author','item':'that box','trpg':'that hero'}}[language][kind]
    subject=noun if deictic else qname
    q=(f'{subject}의 {field}만 답하세요.' if ko else f'Give only the {field} of {subject}.')
    if novel:q=(f'기록에서 {subject}에 해당하는 {field}는 무엇인가요? 내용만 쓰세요.' if ko else
                 f'According to the record, what is the {field} for {subject}? Answer content only.')
    answer=val[values[wanted]]
    rubric='EXACT_SCALAR'
    if missing or ambiguous:
        rubric='CLARIFICATION_POSTHOC'
        if ambiguous or mode==9:
            needed={'ko':{'building':'건물 이름이나 주소','speech':'대표 이름과 연설 시점','library':'도서관 이름','book':'작가 이름','item':'상자 이름이나 번호','trpg':'용사 이름'},
                    'en':{'building':'building name or address','speech':'president name and speech date','library':'library name','book':'author name','item':'box name or number','trpg':'hero name'}}[language][kind]
            answer=(f'대상을 구별할 수 있도록 {needed} 정보를 알려 주세요.' if ko else
                    f'Please provide the {needed} so I can identify the subject.')
        else:answer=(f'기록에 {qname}의 {field} 정보가 없습니다. 그 정보를 알려 주세요.' if ko else
                     f'The record does not contain the {field} of {qname}. Please provide that information.')
    prefix=('가상의 기록:\n' if ko else 'Fictional record:\n')+'\n'.join(context)+'\n' if context else ''
    messages=[dict(role='user',content=prefix+q),dict(role='assistant',content=answer)]
    rubrics=[rubric]
    changed=None
    if not(missing or ambiguous) and r.randrange(4)==0:
        changed=val[values[2]]
        follow=(f'앞 대상의 {field}를 {changed}로 수정합니다. 변경된 값만 answer 항목 하나의 JSON으로 쓰세요.' if ko else
                f'Update the previous subject\'s {field} to {changed}. Give only a JSON object with the answer field.')
        messages.extend([dict(role='user',content=follow),dict(role='assistant',content=json.dumps({'answer':changed},ensure_ascii=False))])
        rubrics.append('EXACT_JSON_OBJECT');rubric='EXACT_JSON_OBJECT'
    # Whole visible document, not query wording/target or an unused random field,
    # determines the group. A no-source generic request has one semantic group.
    basis=dict(kind=kind,visible_facts=[(ids[i],values[i],year+i if kind=='building' else None)
        for i in present] if mode!=9 else [],source_absent=mode==9)
    root=sha(basis)
    return validate(normalize(dict(messages=messages,meta=dict(source='p106b_broad_code_reference',source_license='project_authored_synthetic',
        language=language,kind=kind,root_concept_id=root,semantic_root_id=root,generation_version=VERSION,
        rubric=rubric,turn_rubrics=rubrics,source_condition='MISSING' if missing else 'AMBIGUOUS' if ambiguous else 'SUFFICIENT',
        world_facts='FICTIONAL_CODE_REFERENCES_ONLY',novel_wording=novel))))


def build(train_count=8192,val_count=1024):
    if train_count%16 or val_count%16:raise ValueError('balanced counts required')
    out={};roots=set();conversations=set()
    for split,count in (('train',train_count),('val',val_count)):
        rows=[];attempt=0
        while len(rows)<count:
            position=len(rows);language=('ko','en')[position%2];kind=KINDS[(position//2)%8]
            seed=(491337 if split=='train' else 1941337)+attempt;attempt+=1
            if attempt>count*100:raise ValueError('distinct source space insufficient')
            row=make(kind,language,seed,novel=split=='val');root=row['meta']['semantic_root_id'];sig=sha(row['messages'])
            if root in roots or sig in conversations:continue
            roots.add(root);conversations.add(sig);rows.append(row)
        out[split]=rows
    return out
