#!/usr/bin/env python3
"""Materialize ROOT-reviewed TRAIN correction candidates with explicit patches.

The 28 new teacher user turns were all read by ROOT. Four yes/no requests were
ambiguous under the known-city-only answer contract. Original outputs remain
untouched; explicit ROOT rewrites and case-tag corrections retain lineage.
"""
import copy
import json
from scripts import diag_p108b_correction as production
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter,verify
from tokenizers import Tokenizer

PATCHES={
    'fr_capital_ko:1':('이전 답변이 정확한가요?','앞선 답변은 프랑스의 수도를 알려주지 않았습니다. 프랑스의 수도 도시 이름만 다시 답하세요.'),
    'it_capital_ko:1':('답변이 맞나요?','앞선 답에 로마가 반복됐습니다. 반복과 설명을 빼고 이탈리아의 수도 도시 이름만 한 번 답하세요.'),
    'de_capital_en:1':('You stated "German" as the capital city. Is that correct?',"Your previous reply was not a city name. Give only the name of Germany's capital city."),
    'it_capital_en:1':('Is Cologne the capital of Italy?',"Cologne is not Italy's capital. Give only the name of Italy's capital city.")}
TAG_PATCHES={'fr_capital_ko:1':['WRONG_TASK','UNRELATED_NOUN'],
             'earth_ko:0':['QUESTION_ECHO','WRONG_RELATION']}


def text(message):return ''.join(c.get('text','')for c in message['content'])


def run():
    profile,cases=production.verify();source=production.OUT
    report=json.loads((source/'report.json').read_text(encoding='utf-8'))
    if report['accepted_cases']!=28 or report['candidate_rows']!=56 or not report['owned_server_ended']:
        raise ValueError('complete teacher28/paired56 and actual server shutdown required')
    verify(source,report['candidate_manifest']);rows=[]
    for part in report['candidate_manifest']['shards']:
        rows.extend(json.loads(s)for s in(source/part['path']).read_text(encoding='utf-8').splitlines())
    by_case={case['id']:case for case in cases};grouped={};decisions=[];patches=[]
    for case in cases:
        if not {'original_question','actual_reply','case_kind'}.issubset(case):raise ValueError('explicit actual source case schema required before output creation')
    out=production.BASE/'correction_reviewed_v2'
    if out.exists():raise FileExistsError('preserve earlier ROOT correction candidate review')
    out.mkdir();writer=ShardWriter(out,'candidates',limit=3_000_000);tok=Tokenizer.from_file(str(production.TOKENIZER))
    lines=['P108B 교사 교정 대화 총괄 판독본','',
        '실제 TRAIN 오답24건과 명시 합성 정상4건이며 공식/FINAL 오답이 아닙니다.',
        '교사 원본28회·56관점은 보존했습니다. 도시 이름만 답할 계약과 모호한 재확인 질문4개는 ROOT가 명시 수정했습니다.',
        '단일QA28개와 교정멀티턴28개는 의도된 같은 정답의 두 관점이며56개 독립 지식이 아닙니다.',
        '생산75M 편입/학생 학습은 수행하지 않았습니다. 첫 오답 assistant 턴은 손실을 받지 않습니다.','']
    for row in rows:grouped.setdefault(row['meta']['case_id'],{})[row['meta']['view']]=row
    audits=[]
    for identifier,case in by_case.items():
        pair=grouped[identifier]
        if set(pair)!={'single','correction'}:raise ValueError('exact single/correction pair required')
        single=copy.deepcopy(pair['single']);multi=copy.deepcopy(pair['correction'])
        if text(multi['messages'][0])!=case['original_question']or text(multi['messages'][1])!=case['actual_reply']:
            raise ValueError('original actual question/reply was not preserved')
        if identifier in PATCHES:
            old,new=PATCHES[identifier]
            if text(multi['messages'][2])!=old:raise ValueError('explicit ROOT patch does not match exact teacher original')
            multi['messages'][2]['content']=[dict(type='text',text=new)]
            patches.append(dict(case_id=identifier,old_user_turn=old,new_user_turn=new,author='ROOT',teacher_recalled=False,
                reason='teacher confirmation question was ambiguous for the unchanged literal-city-only answer contract'))
        for view in(single,multi):
            view['meta'].update(root_teacher_review='ROOT_ACTUAL_TEXT_REVIEWED',production_admitted=False,
                root_instruction_patch=identifier in PATCHES and view['meta']['view']=='correction',
                reviewed_source_report_sha256=manual.file_sha(source/'report.json'))
            if identifier in TAG_PATCHES:
                view['meta']['prior_root_issues']=list(view['meta']['root_issues']);view['meta']['root_issues']=TAG_PATCHES[identifier]
            writer.append(view)
        audits.append(production.encode_audit(case,[single,multi],tok))
        decisions.append(dict(case_id=identifier,single_original_accepted=True,
            teacher_multi_original_accepted=identifier not in PATCHES,root_patched_multi_accepted=identifier in PATCHES,
            basis='ROOT read actual question, old answer and new teacher request; known facts/literal output contract checked',
            correct_content_format_only=identifier=='de_capital_en:0'))
        lines.extend(['사례> '+identifier+' / '+case['case_kind'],
            '총괄 판독> '+('교사 질문을 명시 수정한 후보'if identifier in PATCHES else '교사 질문 원형을 유지한 후보')])
        if identifier in PATCHES:lines.append('수정 전 교사 질문> '+PATCHES[identifier][0])
        for m in multi['messages']:lines.append(m['role']+'> '+text(m))
        lines.extend(['지도> 마지막 assistant만 학습; 첫 assistant는 원형 문맥으로 보존',''])
    manifest=writer.close(lineage=dict(source_profile_sha256=manual.file_sha(production.BASE/'correction_profile_v1.json'),
        source_report_sha256=manual.file_sha(source/'report.json'),role='ROOT_REVIEWED_RESEARCH_CANDIDATE_NOT_PRODUCTION'))
    verify(out,manifest)
    summary=dict(schema='P108B_CORRECTION_ROOT_READBACK_V1',status='ROOT_REVIEWED_RESEARCH_CANDIDATE',
        source_report_sha256=manual.file_sha(source/'report.json'),original_teacher_cases=28,root_read_cases=28,
        accepted_unmodified_single_views=28,accepted_unmodified_multi_views=24,explicit_root_multi_patches=4,
        final_candidate_views=56,independent_concept_groups=10,decisions=decisions,root_instruction_patches=patches,
        root_case_issue_patches=TAG_PATCHES,token_audits=audits,
        corrected_assistant_target_tokens=sum(a['corrected_targets_each']for a in audits),
        targets_across_intentional_two_views=2*sum(a['corrected_targets_each']for a in audits),
        candidate_manifest=manifest,teacher_new_requests=0,student_training_updates=0,corpus75m_admitted=False,
        source_raw_unchanged=True,semantic_judge='one ROOT reader, not independent human acceptance')
    library.write_new(out/'ROOT_REVIEW_v1.json',summary)
    target=production.atlas.ROOT/'review_request/20261116_P108B_교정대화_ROOT판독_v2.txt'
    with target.open('x',encoding='utf-8')as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps({k:summary[k]for k in('status','root_read_cases','accepted_unmodified_multi_views','explicit_root_multi_patches','final_candidate_views','corrected_assistant_target_tokens','targets_across_intentional_two_views','corpus75m_admitted')},ensure_ascii=False))


if __name__=='__main__':run()
