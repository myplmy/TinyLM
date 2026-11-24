#!/usr/bin/env python3
"""Aggregate explicit ROOT text ratings; never infer semantic grades by rules."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import interactive_research_infer as manual

ROOT=atlas.ROOT
DIRECTORY=ROOT/'review_request/20261116_P108B_최종원답_v1'


def summarize(rows):
    return dict(n=len(rows),exact_scored=sum(r['exact']is not None for r in rows),
        exact=sum(r['exact']is True for r in rows),relevant=sum(r['rating']['relevance']==2 for r in rows),
        grammar_valid=sum(r['rating']['grammar']==2 for r in rows),natural_form=sum(r['rating']['naturalness']==2 for r in rows),
        adequate=sum(r['rating']['adequacy']==2 for r in rows),partial=sum(r['rating']['adequacy']==1 for r in rows),
        grammatical_sentence=sum(r['rating']['grammar']==2 and r['rating']['sentence_kind']=='SENTENCE'for r in rows),
        unwanted_repeat=sum(r['rating']['unwanted_repeat']for r in rows),inappropriate_list=sum(r['rating']['inappropriate_list']for r in rows),
        sentence_kinds=dict(Counter(r['rating']['sentence_kind']for r in rows)),
        automatic_loops=sum(r['diagnostics']['loop_indicator']for r in rows),
        automatic_echoes=sum(r['diagnostics']['question_echo']for r in rows))


def input_issues(rows):
    first={r['id']:r for r in rows if r['model']=='original'and r['turn']==1}
    expected={f'final:target:{i}:2:ko':('수도을','수도를')for i in range(4)}
    expected.update({f'final:other:{i}:ko':(old,new)for i,old,new in[
        (0,'13와 7를','13과 7을'),(2,'15와 11를','15와 11을'),(3,'16와 13를','16과 13을'),
        (4,'17와 15를','17과 15를'),(5,'18와 17를','18과 17을'),(7,'20와 21를','20과 21을')]})
    issues=[]
    for identifier,(old,new)in expected.items():
        row=first[identifier];original=row['question']
        if original.count(old)!=1:raise ValueError('root-read morphology issue differs from exact saved question')
        issues.append(dict(id=identifier,original=original,corrected_candidate=original.replace(old,new),
            type='ROOT_AUTHORED_KOREAN_PARTICLE_AGREEMENT',source_group=row['source_group']))
    return issues


def run():
    source=DIRECTORY/'SOURCE_ROWS_v1.json';source_sha=manual.file_sha(source)
    unique=json.loads(source.read_text(encoding='utf-8'))['rows'];ratings={};pins={};bindings={}
    packet_manifest=json.loads((DIRECTORY/'READING_MANIFEST_v1.json').read_text(encoding='utf-8'))
    paths=sorted(DIRECTORY.glob('ROOT_RATINGS_part*_v1.json'))
    if len(unique)!=532 or len(paths)!=27:raise ValueError('all532 full contexts and27 manually authored rating parts required')
    for index,path in enumerate(paths):
        record=json.loads(path.read_text(encoding='utf-8'));pins[path.name]=manual.file_sha(path)
        part=packet_manifest['parts'][index];part_path=ROOT/part['path']
        if manual.file_sha(part_path)!=part['sha256']or {r['review_id']for r in record['ratings']}!=set(part['unique_ids']):
            raise ValueError('exact readable part/coverage differs from preserved manifest')
        if record['source_packet_sha256']not in(source_sha,part['sha256'])or record['read_all_text']is not True:
            raise ValueError('actual ROOT reading/source binding missing')
        bindings[path.name]='FULL_SOURCE_ROWS_JSON'if record['source_packet_sha256']==source_sha else 'EXACT_READABLE_PART_TEXT'
        for rating in record['ratings']:
            identifier=rating['review_id']
            if identifier in ratings:raise ValueError('duplicate semantic rating')
            for key in('relevance','grammar','naturalness','adequacy'):
                if type(rating[key])is not int or rating[key]not in(0,1,2):raise ValueError('explicit ordinal grade required')
            for key in('unwanted_repeat','inappropriate_list'):
                if type(rating[key])is not int or rating[key]not in(0,1):raise ValueError('explicit binary grade required')
            ratings[identifier]=rating
    if set(ratings)!={r['review_id']for r in unique}:raise ValueError('ROOT rating coverage differs from full packet')
    expanded=[];seen=set()
    for row in unique:
        signature=hashlib.sha256(json.dumps({k:row[k]for k in('question','actual_history','answer')},ensure_ascii=False,sort_keys=True).encode()).hexdigest().upper()
        if signature!=row['qa_signature']:raise ValueError('complete Q/history/A binding changed')
        for occurrence in row['occurrences']:
            key=(occurrence['model'],occurrence['id'])
            if key in seen:raise ValueError('duplicate model/question occurrence')
            seen.add(key);expanded.append(dict(row,**{k:v for k,v in occurrence.items()if k!='id'},id=occurrence['id'],rating=ratings[row['review_id']]))
    if len(expanded)!=960:raise ValueError('all960 actual answers must map to manual ratings')
    names=list(dict.fromkeys(r['model']for r in expanded));issues=input_issues(expanded);excluded={r['id']for r in issues}
    models={}
    for name in names:
        rows=[r for r in expanded if r['model']==name]
        if len(rows)!=240:raise ValueError('complete240 actual answers per model required')
        models[name]=dict(all=summarize(rows),languages={})
        for language in('ko','en'):
            selected=[r for r in rows if r['language']==language];opened=[r for r in selected if r['family']=='open']
            models[name]['languages'][language]=dict(all=summarize(selected),open_all=summarize(opened),
                open_initial=summarize([r for r in opened if r['turn']==1]),
                open_followups=summarize([r for r in opened if r['turn']>1]),
                insufficient_information=summarize([r for r in selected if r['family']=='protect'and r['expected']is None]))
        models[name]['posthoc_morphology_sensitivity']=summarize([r for r in rows if r['exact']is not None and r['id']not in excluded])
    result=dict(schema='P108B_ROOT_REVIEW_SUMMARY_V1',status='ALL_ACTUAL_TEXT_ROOT_READ_AND_RATED',
        unique_full_contexts=532,actual_answer_references=960,source_sha256=source_sha,rating_sources=pins,rating_binding_modes=bindings,models=models,
        limitations=['one informed ROOT reader, not independent human blind review','grades are ordinal qualitative judgments, not benchmark confidence estimates',
        'short numeric/name syntax is not free dialogue ability','followup appropriateness is relative to actual prior answer; prior factual error remains',
        'posthoc input sensitivity does not replace primary sealed test or repair its independence'],new_model_runs=False)
    library.write_new(DIRECTORY/'ROOT_REVIEW_SUMMARY_v1.json',result)
    library.write_new(ROOT/'handoff/audit/nov16_p108b/FINAL_INPUT_MORPHOLOGY_ISSUES_v1.json',dict(
        source_sha256=source_sha,issues=issues,excluded_scored_ids=sorted(excluded),primary_unchanged=True,
        future_corrected_version_is_new_independent_test=False))
    lines=['P108B 최종 실제 답변 판독 요약','',
        '총괄이960개 답변에 대응하는532개 고유 질문/전체 실제 이력/답을 전량 읽었습니다.',
        '동일 원답을 중복 채점하지 않고960개 모델별 대응을 복원했습니다. 독립 인간 맹검은 아닙니다.',
        '문법/자연스러움은 정답성과 별개입니다. 짧은 명사·숫자의 문법 점수를 일상 대화 능력으로 쓰지 않습니다.','',
        '| 모델 | 언어 | 설명/대화 답 수 | 문법 문장 | 내용 적합 | 부분 적합 | 불필요 반복 | 부적절 나열 |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for name in names:
        for language in('ko','en'):
            r=models[name]['languages'][language]['open_all']
            lines.append('| '+' | '.join(map(str,[name,language,r['n'],r['grammatical_sentence'],r['adequate'],r['partial'],r['unwanted_repeat'],r['inappropriate_list']]))+' |')
    lines.extend(['','위 수는 최초 설명과 실제 후속 대화를 포함합니다. 같은 시나리오의 답은 독립 표본이 아닙니다.',
        '최초 답이 틀렸어도 후속에서 같은 뜻을 한 문장으로 줄이면 국소 지시 수행은 인정하되, 최초 지식이 옳아졌다고 해석하지 않습니다.',
        '한국어 조사 오류10문항은 원문을 바꾸지 않고 별도 민감도 집계로 남겼습니다. 고친 버전도 새 맹검 평가로 부를 수 없습니다.','',
        '전체 질문-답과 실제 대화 이력: answers_001.txt부터 answers_027.txt까지. 수동 판정 원본: ROOT_RATINGS_part001_v1.json부터027까지.'])
    text='\n'.join(lines)+'\n'
    with(DIRECTORY/'READING_SUMMARY_v1.md').open('x',encoding='utf-8')as f:f.write(text)
    print(text)


if __name__=='__main__':run()
