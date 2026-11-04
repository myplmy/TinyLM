"""New, code-verified balanced practice for supervised post-hoc P108 repair.

These are synthetic rule tasks, not an official benchmark or general-language
corpus. All expected answers are code-owned. No external data is read.
"""
from collections import Counter, defaultdict
import json
import random

NAMES={'ko':['민수','영희','지수','준호','수진','현우','서연','지훈'],
       'en':['Alice','Bob','Carol','David','Emma','Frank','Grace','Henry']}
WORDS={'ko':['빨강','파랑','초록','노랑','사과','당근','고양이','강아지'],
       'en':['red','blue','green','yellow','apple','carrot','cat','puppy']}
ROLES={'ko':[('요리합니다','요리합니까'),('운전합니다','운전합니까'),
             ('수영합니다','수영합니까'),('독서합니다','독서합니까')],
       'en':[('cooks','cooks'),('drives','drives'),('swims','swims'),('reads','reads')]}


def make_data():
    rng=random.Random(20261104)
    pairs=[(a,b) for a in range(20) for b in range(a,20)]
    rng.shuffle(pairs)
    repeat_pairs=[(word,count) for word in range(8) for count in range(2,6)]
    rng.shuffle(repeat_pairs)
    result=[]
    for block,(split,n) in enumerate((('calib',16),('dev',16),('test',32))):
        numbers=pairs[70*block:70*(block+1)]
        rep=repeat_pairs[:8] if block==0 else repeat_pairs[8:16] if block==1 else repeat_pairs[16:]
        for family in ('arithmetic','lookup','role','boolean','update','copy','repeat','json'):
            for i in range(n):
                lang='ko' if i%2==0 else 'en'
                ko=lang=='ko'
                within=i//2
                target=within%2
                reverse=(within//2)%2
                a,b=numbers[(within+{'arithmetic':0,'update':20,'copy':40,'json':50}.get(family,0))%70]
                actors=rng.sample(NAMES[lang],2)
                values=[WORDS[lang][(within+3)%8]]*2
                values[target]=WORDS[lang][within%8]
                detail=dict(target_index=target,reverse=bool(reverse))
                source=f'{split}:{family}:{i}'
                if family=='arithmetic':
                    question=f'{a}+{b}는 얼마입니까? 숫자만 쓰세요.' if ko else f'What is {a}+{b}? Write only the number.'
                    expected=str(a+b)
                    detail=dict(a=a,b=b)
                    source=f'number_pair:{a}:{b}'
                elif family=='lookup':
                    distance=block+1 if within<8 else 4
                    actors=[NAMES[lang][(within+block)%8],NAMES[lang][(within+block+distance)%8]]
                    clauses=[f'{actors[j]}의 표시는 {values[j]}입니다' if ko else f'The label for {actors[j]} is {values[j]}' for j in range(2)]
                    if reverse:clauses.reverse()
                    question=('. '.join(clauses)+f'. {actors[target]}의 표시는 무엇입니까? 표시만 쓰세요.' if ko else
                              '. '.join(clauses)+f'. What is the label for {actors[target]}? Write only the label.')
                    expected=values[target]
                    detail.update(actors=actors,values=values)
                    source='lookup_context:'+lang+':'+json.dumps(sorted(zip(actors,values)),ensure_ascii=True)
                elif family=='role':
                    wanted=(within+block+within//8)%4
                    other=(wanted+1)%4
                    distance=block+1 if within<8 else 4
                    actors[target]=NAMES[lang][(within+block*3)%8]
                    actors[1-target]=NAMES[lang][(within+block*3+distance)%8]
                    roles=[other,other];roles[target]=wanted
                    clauses=[f'{actors[j]}는 {ROLES[lang][roles[j]][0]}' if ko else
                             f'{actors[j]} {ROLES[lang][roles[j]][0]}' for j in range(2)]
                    if reverse:clauses.reverse()
                    question=('. '.join(clauses)+f'. 누가 {ROLES[lang][wanted][1]}? 이름만 쓰세요.' if ko else
                              '. '.join(clauses)+f'. Who {ROLES[lang][wanted][1]}? Write only the name.')
                    expected=actors[target]
                    detail.update(actors=actors,roles=roles,wanted=wanted)
                    source='role_context:'+lang+':'+json.dumps(sorted(zip(actors,roles)),ensure_ascii=True)
                elif family=='boolean':
                    op='AND' if within%2==0 else 'OR'
                    va,vb=bool((within//2)%2),bool((within//4)%2)
                    names=[('A','B'),('C','D'),('E','F')][block] if within<8 else ('G','H')
                    render=lambda value:('참' if value else '거짓') if ko else ('true' if value else 'false')
                    clauses=[f'{names[0]}={render(va)}',f'{names[1]}={render(vb)}']
                    if reverse:clauses.reverse()
                    question=(', '.join(clauses)+f'. {names[0]} {op} {names[1]}는? 참 또는 거짓만 쓰세요.' if ko else
                              ', '.join(clauses)+f'. What is {names[0]} {op} {names[1]}? Write true or false.')
                    expected=render(va and vb if op=='AND' else va or vb)
                    detail=dict(operator=op,a=va,b=vb,reverse=bool(reverse))
                elif family=='update':
                    changed=(within//2)%2
                    reverse=(within//4)%2
                    detail['reverse']=bool(reverse)
                    vals=[a,b]
                    replacement=(vals[changed]+3)%20
                    changed_name=('A','B')[changed];asked_name=('A','B')[target]
                    clauses=[f'A={a}',f'B={b}']
                    if reverse:clauses.reverse()
                    question=(', '.join(clauses)+f'입니다. {changed_name}를 {replacement}로 바꿉니다. 지금 {asked_name}의 값만 쓰세요.' if ko else
                              ', '.join(clauses)+f'. Change {changed_name} to {replacement}. Write only the current value of {asked_name}.')
                    vals[changed]=replacement
                    expected=str(vals[target])
                    detail.update(before=[a,b],changed_index=changed,replacement=replacement)
                    source=f'number_pair:{a}:{b}'
                elif family=='copy':
                    expected=f'key-{a}-{b}'
                    question=f'다음 문자열을 그대로 복사하세요: {expected}' if ko else f'Copy this string exactly: {expected}'
                    detail=dict(a=a,b=b)
                    source=f'number_pair:{a}:{b}'
                elif family=='repeat':
                    word,count=rep[within]
                    expected=' '.join([WORDS[lang][word]]*count)
                    question=(f'{WORDS[lang][word]} 단어를 공백으로 구분해 정확히 {count}번 쓰세요.' if ko else
                              f'Write {WORDS[lang][word]} exactly {count} times, separated by spaces.')
                    detail=dict(word=WORDS[lang][word],count=count)
                    source=f'repeat_pair:{word}:{count}'
                else:
                    expected=json.dumps({'answer':str(a+b)},separators=(',',':'))
                    question=(f'{a}+{b}의 값을 문자열로 answer 항목 하나인 JSON으로만 쓰세요.' if ko else
                              f'Write {a}+{b} as JSON with only the key answer and a string value.')
                    detail=dict(a=a,b=b)
                    source=f'number_pair:{a}:{b}'
                result.append(dict(id=f'{split}_{family}_{i:03d}',split=split,family=family,language=lang,
                    question=question,expected=expected,protected=family in ('copy','repeat'),
                    source_group=source,rule=detail))
    audit_data(result)
    return result


def audit_data(rows):
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('duplicate IDs')
    if len({r['question'] for r in rows})!=len(rows):raise ValueError('duplicate question text')
    questions=defaultdict(set)
    sources=defaultdict(set)
    for r in rows:
        questions[r['split']].add(r['question'])
        sources[r['split']].add(r['source_group'])
        if r['family'] in ('arithmetic','json'):
            ans=str(r['rule']['a']+r['rule']['b'])
            if r['expected']!=(json.dumps({'answer':ans},separators=(',',':')) if r['family']=='json' else ans):
                raise ValueError('computed arithmetic/JSON answer differs')
        if r['family']=='boolean':
            rule=r['rule'];truth=rule['a'] and rule['b'] if rule['operator']=='AND' else rule['a'] or rule['b']
            correct=('참' if truth else '거짓') if r['language']=='ko' else ('true' if truth else 'false')
            if r['expected']!=correct:raise ValueError('boolean answer differs')
        rule=r['rule']
        if r['family']=='lookup' and r['expected']!=rule['values'][rule['target_index']]:
            raise ValueError('lookup target answer differs')
        if r['family']=='role':
            matching=[j for j,role in enumerate(rule['roles']) if role==rule['wanted']]
            if len(matching)!=1 or r['expected']!=rule['actors'][matching[0]]:
                raise ValueError('role target answer differs')
        if r['family']=='update':
            now=list(rule['before']);now[rule['changed_index']]=rule['replacement']
            if r['expected']!=str(now[rule['target_index']]):raise ValueError('updated value answer differs')
        if r['family']=='copy' and r['expected']!=f'key-{rule["a"]}-{rule["b"]}':
            raise ValueError('literal copy answer differs')
        if r['family']=='repeat' and r['expected']!=' '.join([rule['word']]*rule['count']):
            raise ValueError('requested repetition answer differs')
    for a,b in (('calib','dev'),('calib','test'),('dev','test')):
        if questions[a]&questions[b] or sources[a]&sources[b]:raise ValueError('cross-split prompt/source overlap')
    for split,n in (('calib',16),('dev',16),('test',32)):
        group=[r for r in rows if r['split']==split]
        if Counter(r['family'] for r in group)!=Counter({f:n for f in ('arithmetic','lookup','role','boolean','update','copy','repeat','json')}):
            raise ValueError('family quota differs')
        bo=[r for r in group if r['family']=='boolean']
        if Counter(r['expected'] for r in bo)!=Counter({'참':n//4,'거짓':n//4,'true':n//4,'false':n//4}):
            raise ValueError('Boolean labels are not balanced')
    return dict(rows=len(rows),counts=dict(Counter(r['split'] for r in rows)),
                prompt_overlap=0,numeric_repeat_source_overlap=0,
                scope='NEW_SYNTHETIC_RULE_PRACTICE_NOT_GENERAL_INTELLIGENCE')


def strict_score(row):
    if row['expected'] is None:return None
    if row['family']=='json':
        try:
            def unique(pairs):
                if len(dict(pairs))!=len(pairs):raise ValueError('duplicate JSON key')
                return dict(pairs)
            parsed=json.loads(row['answer'],object_pairs_hook=unique)
            return (type(parsed) is dict and set(parsed)=={'answer'}
                    and type(parsed['answer']) is str and parsed==json.loads(row['expected']))
        except (ValueError,TypeError):return False
    return row['answer'].strip()==row['expected']


class StrictWriter:
    """Use the existing evaluator; replace scoring BEFORE its row summary."""
    def __init__(self,writer):self.writer=writer
    def append(self,row):
        row['legacy_whitespace_exact']=row['exact']
        row['exact']=strict_score(row)
        self.writer.append(row)
