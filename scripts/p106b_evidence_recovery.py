"""Producer-owned evidence dependencies, not a classifier of arbitrary questions."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import random
from scripts import p106b_role_bridge as base
wrap=base.wrap
VERSION='P106B_QUERY_SPECIFIC_EVIDENCE_RECOVERY_V1'

LABELS={
 'ko':dict(boy_name='소년의 이름',girl_name='소녀의 이름',boy_age='소년의 나이',girl_age='소녀의 나이',
    boy_grade='소년의 학년',girl_grade='소녀의 학년',region='구역의 이름',area='구역의 면적',percent='전체에서 차지하는 비율',
    year='구역의 지정 연도',sender='물품을 보낸 사람의 이름',recipient='물품을 받은 사람의 이름',item='전달한 물품',
    place='전달 장소',time='전달 시간대',start='사업 시작 연도',end='사업 종료 연도',duration='사업 기간'),
 'en':dict(boy_name="the boy's name",girl_name="the girl's name",boy_age="the boy's age",girl_age="the girl's age",
    boy_grade="the boy's grade",girl_grade="the girl's grade",region='the region name',area='the area of the region',
    percent='the percentage share',year='the designation year',sender="the sender's name",recipient="the recipient's name",
    item='the delivered item',place='the delivery location',time='the time of delivery',start='the project start year',
    end='the project end year',duration='the elapsed project years')}


def facts(g,language):
    return {k:v for k,v in base.values(g,language).items() if k not in ('replacement','duration')}


def neutral(g):
    # Replacement/update values and rendering order are not new initial facts.
    return wrap.sha(dict(version=VERSION,family=g['family'],facts=facts(g,'en')))


def graphs(count,split='train',exclude=()):
    if count<=0 or count%4:raise ValueError('balanced four-family count required')
    seen=set(exclude);out=[];counts={f:0 for f in base.FAMILIES}
    for i in range(count*100):
        g=base.graph(i,split);key=neutral(g)
        if key in seen or counts[g['family']]>=count//4:continue
        out.append(g);seen.add(key);counts[g['family']]+=1
        if len(out)==count:return out
    raise ValueError('distinct visible fact supply exhausted')


def queries(g):
    if g['family']=='years':return ('duration','region')
    rng=random.Random(int(wrap.sha([VERSION,neutral(g),'queries'])[:16],16))
    return tuple(rng.sample(base.keys(g),2))


def dependencies(key):return {'start','end'} if key=='duration' else {key}


def mask_key(g,key):
    if key=='duration':return ('start','end')[int(neutral(g)[:8],16)%2]
    return key


def statement(key,value,language):
    label=LABELS[language][key]
    if language=='en':
        rendered=(f'{int(value):,} square kilometres' if key=='area' else value+' years' if key in ('boy_age','girl_age') else value)
        return f'{label.capitalize()} is {rendered}.'
    last=label[-1];topic='은' if 0xAC00<=ord(last)<=0xD7A3 and (ord(last)-0xAC00)%28 else '는'
    rendered=(f'{int(value):,}제곱킬로미터' if key=='area' else value+'세' if key in ('boy_age','girl_age') else
        value+'학년' if key in ('boy_grade','girl_grade') else value+'년' if key in ('year','start','end') else value)
    return f'{label}{topic} {rendered}입니다.'


def reference(g,language,omitted=None):
    values=facts(g,language)
    if omitted is not None and omitted not in values:raise ValueError('only actual declared facts may be withheld')
    keys=list(values)
    random.Random(int(wrap.sha([VERSION,neutral(g),'fact-order'])[:16],16)).shuffle(keys)
    prefix=('다음은 가상 기록입니다. 실제 인물이나 지역에 관한 자료가 아닙니다. ' if language=='ko' else
            'This is a fictional record, not a real biography or regional report. ')
    lines=[statement(k,values[k],language) for k in keys if k!=omitted]
    if g['family']=='years':lines.append('사업 기간은 종료 연도에서 시작 연도를 뺀 년수입니다.' if language=='ko' else
        'Elapsed project years are end year minus start year.')
    return prefix+' '.join(lines)


def question(key,language,style=0):
    if key!='region':q=base.question(key,language,style)
    else:
        if style not in (0,1,2,3):raise ValueError('declared question style')
        q=(('기록의 구역 이름만 알려 주세요.','이 기록에 따르면 구역의 이름은 무엇인가요?',
            '자료를 참고해 구역 이름만 짧게 적으세요.','어느 구역의 기록인지 이름만 적어 주세요.')[style] if language=='ko' else
           ('What is the region name? Give only its name.','According to this record, state the region name only.',
            'Please extract the region name from the supplied record.','Which region name is specified in this account?')[style])
    if language=='ko':
        return q+(' 단, 자료만으로 정할 수 없으면 추측하지 말고 필요한 항목을 짧게 물어보세요.' if style in (0,1) else
                  ' 근거가 모자랄 때는 값 대신 어떤 정보를 더 받아야 하는지 질문하세요.')
    return q+(' If the record is insufficient, do not guess; briefly ask for the needed fact.' if style in (0,1) else
              ' When the evidence is incomplete, ask which necessary detail should be supplied instead of guessing.')


def clarification(key,language):
    label=LABELS[language][key]
    return (f'자료에 {label} 정보가 없습니다. {label} 정보를 알려 주세요.' if language=='ko' else
            f'The record does not specify {label}. Please provide that detail.')


def updated(g,language,style):
    values=base.values(g,language)
    key={'people':'boy_age','units':'area','years':'end','transfer':'recipient'}[g['family']]
    if g['family']=='transfer':
        value=values['replacement'];instruction=(f'기록에서 물품을 받은 사람을 {value}로 바꾸었습니다. ' if language=='ko' else
            f'The recorded recipient is now {value}. ');wanted='recipient';answer=value
    else:
        value=str(int(values[key])+g['delta']);label=LABELS[language][key]
        instruction=(f'기록에서 {label} 값을 {g["delta"]}만큼 늘렸습니다. ' if language=='ko' else
                     f'Increase {label} in the record by {g["delta"]}. ')
        wanted='duration' if g['family']=='years' else key
        answer=str(int(value)-int(values['start'])) if wanted=='duration' else value
    return dict(question=instruction+question(wanted,language,style),answer=answer),wanted


def make(g,language,mode,partial,style,tok):
    if type(mode) is not int or mode not in range(4) or type(partial) is not bool:raise ValueError('registered four-way evidence condition')
    a,b=queries(g);wanted=(a,b)[mode//2];designated=mask_key(g,(a,b)[mode%2])
    omitted=designated if partial else None;known=facts(g,language)
    if omitted is not None:del known[omitted]
    enough=dependencies(wanted).issubset(known)
    if not enough and omitted not in dependencies(wanted):raise ValueError('only actually missing query dependency may trigger clarification')
    values=base.values(g,language);value=values[wanted]
    first=dict(question=question(wanted,language,style),answer=value if enough else clarification(omitted,language))
    supplied=statement(designated,facts(g,language)[designated],language)
    follow=(f'추가 확인 정보: {supplied} 앞 질문에 다시 답하세요. ' if language=='ko' else
            f'Additional confirmed fact: {supplied} Answer the earlier question again. ')
    second=dict(question=follow+question(wanted,language,style),answer=value)
    third,last=updated(g,language,style);pairs=[first,second,third]
    root=wrap.sha([VERSION,neutral(g),language,mode,partial,style])
    job=dict(root=root,language=language,reference=reference(g,language,omitted),raw_pairs=pairs,
        provenance=dict(source_license='project_authored_fictional'))
    row=wrap.render(job,pairs,tok,repaired=False)
    row['meta'].update(kind='evidence_recovery',source='project_authored_query_specific_evidence',
        source_split=g['split'],neutral_root=neutral(g),producer_graph=copy.deepcopy(g),family=g['family'],
        condition=mode,withholding=partial,omitted_key=omitted,designated_supply_key=designated,
        requested_fields=[wanted,wanted,last],first_required_keys=sorted(dependencies(wanted)),
        first_available_keys=sorted(known),first_response_intent='ANSWER' if enough else 'ASK_FOR_MISSING_FACT',
        query_sufficient=enough,question_style=style,label_status='CODE_PRODUCER_TARGETS',
        semantic_truth='GIVEN_FICTIONAL_RECORD_AND_EXPLICIT_UPDATE_ONLY',
        known_output_contract='PRODUCER_QUERY_SPECIFIC_DEPENDENCIES',
        first_clarification_semantic_rubric='POSTHOC_REVIEW_NOT_EXACT_TEXT_TRUTH' if not enough else 'NOT_APPLICABLE',
        duplicate_type='KNOWN_PRODUCER_REPEAT_OR_UPDATE_ALLOWED',intentional_duplicate_allowed=True,
        teacher_calls=0,supervised_assistant_turns=[1,2,3],evidence_recovery_version=VERSION)
    return row
