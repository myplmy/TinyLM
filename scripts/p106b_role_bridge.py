"""Project-authored, program-proven natural role/unit QA; no teacher calls."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import random
from scripts import p106b_source_repair3 as wrap
from scripts import p106b_binding_auxiliary as binding

VERSION='P106B_CODE_NATURAL_ROLE_BRIDGE_V1'
FAMILIES=('people','units','transfer','years')
NAMES={
 'ko':{'train':['하늘','지우','시온','민서','서우','유진','수현','이든'],
       'dev':['가람','나루','다온','라온','새봄','여울','온유','이레'],
       'test':['노을','단비','바다','솔','연우','우주','지안','해솔']},
 'en':{'train':['Alex','Casey','Drew','Emery','Frankie','Hayden','Jamie','Robin'],
       'dev':['Blair','Devon','Ellis','Finley','Kendall','Lake','Marin','Sky'],
       'test':['Avery','Cameron','Jesse','Morgan','Parker','Quinn','Riley','Taylor']}}
ITEMS={'ko':['책','가방','열쇠','상자','우산','노트','지도','공'],
       'en':['book','bag','key','box','umbrella','notebook','map','ball']}
PLACES={'ko':['도서관','공원','역','학교','박물관','정원','우체국','광장'],
        'en':['library','park','station','school','museum','garden','post office','square']}
TIMES={'ko':['아침','정오','오후','저녁'],'en':['morning','noon','afternoon','evening']}


def graph(index,split='train'):
    if type(index) is not int or index<0 or split not in ('train','dev','test'):raise ValueError('declared split/nonnegative index required')
    rng=random.Random(int(wrap.sha([VERSION,split,index])[:16],16))
    ages=rng.sample(range(7,18),2);start=rng.randint(1810,1990);end=start+rng.randint(2,45)
    g=dict(version=VERSION,index=index,split=split,family=FAMILIES[index%4],name_ids=rng.sample(range(8),3),
        ages=ages,grades=rng.sample(range(1,13),2),area=rng.randint(101,50000),percent=rng.randint(1,50),
        year=rng.randint(1900,2020),start=start,end=end,item=rng.randrange(8),place=rng.randrange(8),time=rng.randrange(4),
        delta=rng.randint(1,3),reverse=bool(rng.randrange(2)))
    fields={'people':('ages','grades'),'units':('area','percent','year'),
        'transfer':('item','place','time'),'years':('start','end')}[g['family']]
    name_count={'people':2,'units':1,'transfer':3,'years':1}[g['family']]
    identity=dict(version=VERSION,split=split,family=g['family'],name_ids=g['name_ids'][:name_count],
        facts={k:g[k] for k in fields})
    g['root']=wrap.sha(identity)
    return g


def graphs(count,split='train'):
    if count%4 or count<=0:raise ValueError('balanced four-family count required')
    out=[];used=set();counts={f:0 for f in FAMILIES};i=0
    while len(out)<count:
        g=graph(i,split);i+=1
        if i>count*100:raise ValueError('unique bridge supply exhausted')
        if counts[g['family']]>=count//4 or g['root'] in used:continue
        out.append(g);used.add(g['root']);counts[g['family']]+=1
    return out


def values(g,language):
    if language not in NAMES or g!=graph(g['index'],g['split']):raise ValueError('exact signed producer graph required')
    a,b,c=[NAMES[language][g['split']][i] for i in g['name_ids']]
    if g['family']=='people':return dict(boy_name=a,girl_name=b,boy_age=str(g['ages'][0]),girl_age=str(g['ages'][1]),boy_grade=str(g['grades'][0]),girl_grade=str(g['grades'][1]))
    if g['family']=='units':return dict(region=a,area=str(g['area']),percent=str(g['percent'])+'%',year=str(g['year']))
    if g['family']=='transfer':return dict(sender=a,recipient=b,replacement=c,item=ITEMS[language][g['item']],place=PLACES[language][g['place']],time=TIMES[language][g['time']])
    return dict(region=a,start=str(g['start']),end=str(g['end']),duration=str(g['end']-g['start']))


def reference(g,language):
    v=values(g,language);family=g['family']
    if language=='ko':
        prefix='다음은 가상 기록입니다. 실제 인물이나 지역의 자료가 아닙니다. '
        if family=='people':
            lines=[f"이름이 {v['boy_name']}인 소년은 {v['boy_age']}세이며 {v['boy_grade']}학년입니다.",
                   f"소녀의 이름은 {v['girl_name']}이고 나이는 {v['girl_age']}세, 학년은 {v['girl_grade']}학년입니다."]
        elif family=='units':
            lines=[f"{v['region']} 구역의 면적은 {g['area']:,}제곱킬로미터입니다.",f"전체에서 차지하는 비율은 {v['percent']}입니다.",f"이 구역은 {v['year']}년에 지정되었습니다."]
        elif family=='transfer':
            particle='을' if (ord(v['item'][-1])-0xAC00)%28 else '를'
            lines=[f"발신자의 이름은 {v['sender']}이며, {v['recipient']}에게 {v['item']}{particle} 전달했습니다.",f"전달 장소는 {v['place']}이고 시간대는 {v['time']}입니다."]
        else:lines=[f"{v['region']} 구역의 사업은 {v['start']}년에 시작해서 {v['end']}년에 종료되었습니다.", '기간은 종료 연도에서 시작 연도를 뺀 년수로 정의합니다.']
    else:
        prefix='This is a fictional record, not a real biography or regional report. '
        if family=='people':
            lines=[f"A boy named {v['boy_name']} is {v['boy_age']} years old and is in grade {v['boy_grade']}.",
                   f"The girl is named {v['girl_name']}; she is {v['girl_age']} years old and is in grade {v['girl_grade']}."]
        elif family=='units':lines=[f"The {v['region']} region has an area of {g['area']:,} square kilometres.",f"Its share of the total is {v['percent']}.",f"It was designated in {v['year']}."]
        elif family=='transfer':lines=[f"The sender named {v['sender']} delivered the {v['item']} to {v['recipient']}.",f"The delivery location was the {v['place']}; the time of day was {v['time']}."]
        else:lines=[f"The project in the {v['region']} region began in {v['start']} and ended in {v['end']}.", 'Elapsed years are defined as end year minus start year.']
    if g['reverse']:lines.reverse()
    return prefix+' '.join(lines)


def keys(g):
    return {'people':['boy_name','girl_name','boy_age','girl_age','boy_grade','girl_grade'],
        'units':['area','percent','year'],'transfer':['sender','recipient','item','place','time'],
        'years':['start','end','duration']}[g['family']]


def question(key,language,style=0):
    if style not in (0,1,2,3):raise ValueError('declared seen/paraphrase/heldout question style')
    if language=='ko':
        labels={'boy_name':'소년의 이름','girl_name':'소녀의 이름','boy_age':'소년의 나이','girl_age':'소녀의 나이',
            'boy_grade':'소년의 학년','girl_grade':'소녀의 학년','area':'구역의 면적','percent':'전체에서 차지하는 비율','year':'구역의 지정 연도',
            'sender':'물품을 보낸 사람의 이름','recipient':'물품을 받은 사람의 이름','item':'전달한 물품','place':'전달 장소','time':'전달 시간대',
            'start':'사업 시작 연도','end':'사업 종료 연도','duration':'사업 기간'}
        label=labels[key];final=0xAC00<=ord(label[-1])<=0xD7A3 and (ord(label[-1])-0xAC00)%28!=0
        obj='을' if final else '를';topic='은' if final else '는'
        q=('기록에서 '+label+obj+' 알려 주세요.' if style==0 else
           '이 기록에 따르면 '+label+topic+' 무엇인가요?' if style==1 else
           label+obj+' 기록을 참고해서 짧게 적으세요.' if style==2 else
           '자료에서 '+label+topic+' 어떤 값인지 적어 주세요.')
        ending=(' % 기호까지 붙여 답하세요.' if key=='percent' else ' 쉼표와 단위 없이 숫자만 답하세요.' if key in ('boy_age','girl_age','boy_grade','girl_grade','area','year','start','end','duration') else ' 요청한 값만 짧게 답하세요.')
    else:
        labels={'boy_name':"the boy's name",'girl_name':"the girl's name",'boy_age':"the boy's age",'girl_age':"the girl's age",
            'boy_grade':"the boy's grade",'girl_grade':"the girl's grade",'area':'the area of the region','percent':'the percentage share','year':'the designation year',
            'sender':"the sender's name",'recipient':"the recipient's name",'item':'the delivered item','place':'the delivery location','time':'the time of delivery',
            'start':'the project start year','end':'the project end year','duration':'the elapsed project years'}
        q=('What is '+labels[key]+'?' if style==0 else 'According to this record, state '+labels[key]+'.' if style==1 else 'Please extract '+labels[key]+' from the supplied facts.' if style==2 else 'Which value in the account corresponds to '+labels[key]+'?')
        ending=(' Include the percent sign.' if key=='percent' else ' Give digits only, without commas or units.' if key in ('boy_age','girl_age','boy_grade','girl_grade','area','year','start','end','duration') else ' Give only the requested short value.')
    return q+ending


def qa_pairs(g,language,view,style=0):
    if view not in range(4):raise ValueError('four registered bridge views')
    v=values(g,language);rng=random.Random(int(wrap.sha([VERSION,g['root'],'queries'])[:16],16));order=rng.sample(keys(g),3)
    if view==3:order[0]={'people':'boy_age','units':'area','transfer':'recipient','years':'end'}[g['family']]
    first=order[0];others=[k for k in order[1:] if k!=first]
    for k in keys(g):
        if k!=first and k not in others:others.append(k)
    second=first if view in (0,1) else others[0];third=first if view==0 else others[0] if view==1 else others[1]
    pairs=[dict(question=question(first,language,style),answer=v[first]),
        dict(question=question(second,language,(1-style if style in (0,1) else 5-style) if view==1 else style),answer=v[second]),
        dict(question=question(third,language,style),answer=v[third])]
    requested=[first,second,third]
    if view==3:
        if g['family']=='transfer':
            after=dict(v,recipient=v['replacement']);instruction=(f"기록의 수신자를 {v['replacement']} 이름으로 바꾸고 다른 항목은 그대로 둡니다. " if language=='ko' else
                f"Change the recorded recipient to {v['replacement']} and leave other fields unchanged. ")
            third='sender'
        else:
            after=dict(v);after[first]=str(int(v[first])+g['delta'])
            instruction=(f"기록의 해당 값을 {g['delta']}만큼 늘린 새 기록을 사용하세요. " if language=='ko' else
                f"Use an updated record with that value increased by {g['delta']}. ")
            if g['family']=='years':after['duration']=str(int(after['end'])-int(v['start']));third='duration'
            else:third=others[0];instruction+=('다른 항목은 바꾸지 않습니다. ' if language=='ko' else 'Leave other fields unchanged. ')
        pairs[1]=dict(question=instruction+question(first,language,style),answer=after[first])
        pairs[2]=dict(question=('갱신된 기록에서 답하세요. ' if language=='ko' else 'Use the updated record. ')+question(third,language,style),answer=after[third])
        requested=[first,first,third]
    return pairs,requested


def make(g,language,view,style=0,tok=None):
    if tok is None:raise ValueError('actual student tokenizer required for complete role record')
    pairs,requested=qa_pairs(g,language,view,style);neutral=g['root'];root=wrap.sha([neutral,language,style])
    job=dict(root=root,language=language,reference=reference(g,language),provenance=dict(source_license='project_authored_fictional'),raw_pairs=pairs)
    row=wrap.render(job,pairs,tok,repaired=False)
    row['meta'].update(kind='role_bridge',source='project_authored_role_bridge',source_split=g['split'],
        neutral_root=neutral,producer_graph=copy.deepcopy(g),bridge_version=VERSION,view=view,question_style=style,
        requested_fields=requested,answer_types=['PERCENT' if k=='percent' else 'INTEGER' if k in ('boy_age','girl_age','boy_grade','girl_grade','area','year','start','end','duration') else 'ATOM' for k in requested],
        known_output_contract='PROGRAM_PROVEN_ROLE_UNIT_THREE_QA',
        label_status='CODE_PRODUCER_TARGETS',semantic_truth='GIVEN_FICTIONAL_RECORD_ONLY',
        duplicate_type='KNOWN_PRODUCER_REPEAT_ALLOWED' if view in (0,1) else 'KNOWN_PRODUCER_FIELD_QUERIES',
        intentional_duplicate_allowed=view in (0,1),supervised_assistant_turns=[1,2,3],teacher_calls=0)
    row['meta']['expected_equal_answer_allowed']=len({p['answer'] for p in pairs})<3
    return row


def repeat_control(original,tok,approved):
    if original['meta']['kind'] not in ('binding_color','binding_department') or len(original['messages'])!=2:
        raise ValueError('existing proven two-message code binding record required')
    if binding.binding_bit(original,approved) is None:raise ValueError('trusted original producer binding required')
    user=wrap.text(original['messages'][0]);reference,question_text=user.rsplit('\n',1);answer=wrap.text(original['messages'][1])
    pairs=[dict(question=question_text,answer=answer) for _ in range(3)]
    job=dict(root=wrap.sha([VERSION,'REPEAT_CONTROL',original['messages']]),language=original['meta']['language'],
        reference=reference,raw_pairs=pairs,provenance=dict(source_license='project_authored_fictional'))
    row=wrap.render(job,pairs,tok,repaired=False)
    row['meta'].update(kind='role_repeat_control',source='existing_proven_code_repeat',source_split='train',bridge_version=VERSION,
        original_code_sha256=wrap.sha(original),known_output_contract='PROGRAM_PROVEN_INTENTIONAL_SAME_QUESTION_REPEAT',
        label_status='CODE_PRODUCER_TARGETS',semantic_truth='GIVEN_FICTIONAL_RECORD_ONLY',
        duplicate_type='KNOWN_PRODUCER_REPEAT_ALLOWED',intentional_duplicate_allowed=True,teacher_calls=0)
    return row
