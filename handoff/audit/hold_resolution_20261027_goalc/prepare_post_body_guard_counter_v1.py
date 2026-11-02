"""Export all11 remaining transforms and four numeric flags for exact text work."""
from collections import Counter
from pathlib import Path
import difflib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

BASE=inv.BASE
GROUP='post_body_guard_counter_v1'
OUT=BASE/GROUP
audit_path=AUDIT/'JOIN_REPEAT_NOMINAL_BODY_AUDIT_V1.json'
snapshot_path=AUDIT/'supplemental_candidates_snapshot_v55.json'
audit,snapshot=map(inv.cache.read,[audit_path,snapshot_path])
inv.require(not OUT.exists(),'new immutable post-body review namespace required')
all_rows={(row['cohort'],row['id']):row for row in snapshot['records']}
selected=[row for row in audit['records'] if row.get('post_policy_would_edit') or row.get('introduced_numeric_occurrences')]
inv.require(len(selected)==14 and len({row['id'] for row in selected})==14,'all14 current guard cases must be visible')
native=inv.cache.read(BASE/'root_join_conflict_counter_v1/manifest.json')
draft_path=BASE/'draft_proposals_v26_delta_v1/complete.json'
source_code_pins=inv.cache.read(draft_path)['lineage']['source_code_sha256']
for name,digest in source_code_pins.items():
    inv.require(inv.file_sha(ROOT/name)==digest,'frozen production code changed')
native_rows={row['id']:row for row in native['rows']}
roles=['context_controls','context_hangul','context_latin','historical_review','legacy_review']
assignments={role:[] for role in roles}
costs=Counter()
instructions={
 'expanded_train:47767':'현재 var() 함수 문장은 실제 스프레드시트 함수의 완결 서술이다. 기계의 문장 전체 삭제 제안은 적용하지 않고 실제 함수 괄호와 설명을 보존한다.',
 'expanded_train:299540':'현재 괄호 속 맨끝에서2번째 샤프/단조 딸림음은 값이 채워진 음악 설명이다. 쉼표가 괄호 앞에 있다는 이유로 문장 전체를 삭제하지 않는다.',
 'expanded_train:157350':'승강인원 링크의 표시문자 승강 인원을 보존하고 위키 링크 마크만 푼다. 수치·비교·연도는 그대로다.',
 'expanded_train:217033':'원작 링크의 실제 표시 제목을 보존하고 위키 링크 마크만 푼다. 영화와 원작 관계를 합치거나 없는 제목을 추가하지 않는다.',
 'expanded_train:1278579':'Charles Mosley의 편집자 병기 ed.를 보존하고 깨진 editor 링크 껍데기만 푼다. 서지·연도·쪽수·ISBN은 그대로다.',
 'expanded_train:1787':'중국 대륙의 채워진 중국 본토 별칭은 유지하고 그 앞의 빈 세미콜론 껍데기만 제거한다. 실제 내용 없는 각주/참고자료 표제만 제거하며 다른 본문은 보존한다.',
 'expanded_train:1034905':'바지르/고관과 수니파/이슬람교도 및 포경 수술의 위키 링크를 원래 표시문자로 푼다. 실제 역사 서술·귀속·대상·조건은 바꾸지 않는다. 링크 메타데이터 원형은 별도 보존한다.',
 'expanded_train:1069370':'구조 및 기관이라는 실제 글자는 보존하고 b id의 HTML 표시 태그만 푼다. 학술 내용·전사 기호를 지우지 않는다.',
 'expanded_train:670165':'튄문 역 링크의 실제 표시문자 튄문을 보존하고 링크 껍데기만 푼다. 다른 역/노선/시설 관계와 순서는 유지한다.',
 'expanded_train:77559':'실제 내용 없는 참조주/내용주 표제만 제거한다. 채워진 본문·인용·참고자료는 그대로 유지한다.',
 'expanded_train:119838':'실제 내용 없는 각주/내용주/참조주 표제만 제거한다. 새 숫자8/21 계수는 원문 날짜 표현·현재 본문에 근거가 있는지 설명하고 원문에 없는 날짜·발매물명은 만들지 않는다. 이미 별도보류된 제목없는 날짜/China를 복원하지 않는다.',
 'expanded_train:291381':'현재 출생1913-05-13과 사망1980-04-12의 근거는 별도 허용된 날짜 증거MD다. 원형의1890·6월12일을 다른 경력·날짜까지 지우는 이유로 쓰지 않는다. 새 나이 계산이나 기타 사실 정정을 하지 않는다.',
 'expanded_train:4482':'같은 원문 저서목록에 명시된 포물선/내접삼각형 넓이비4/3과 실제 서술의 동일 대상을 대조한다. 없는 공비·식·그림·3.1416 직접목적어는 채우지 않는다.',
 'expanded_train:50559':'같은 원문과 별도 허용된 즉위일 증거MD를 대조해11월17일의 좁은 정정을 검토한다. 생년/사망일은 보존하고69세/70살은 원래 보류 경계를 유지하며 나이를 계산하지 않는다.',
}


def save(path,text):
    payload=text.encode('utf-8')
    inv.require(0<len(payload)<20_000_000,'text artifact requires ordered splitting')
    with path.open('xb') as stream:stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))


prepared=[]
for row in selected:
    original_pin=row['original']
    inv.require(inv.file_sha(ROOT/original_pin['path'])==original_pin['sha256'],'original changed')
    inv.require(inv.file_sha(ROOT/row['body'])==row['clean_text_sha256'],'current body changed')
    original=(ROOT/original_pin['path']).read_text(encoding='utf-8')
    body=(ROOT/row['body']).read_text(encoding='utf-8')
    proposed=policy.propose(dict(id=row['id'],text=body,complete_eos=True,valid_utf8=True),False)
    machine=proposed.get('candidate',proposed['text'])
    parent=all_rows[(row['cohort'],row['id'])]
    prepared.append(dict(record=row,parent=parent,original=original,body=body,machine=machine,
        cost=len(original)+len(body)+len(machine)))
for item in sorted(prepared,key=lambda item:(-item['cost'],item['record']['id'])):
    available=[role for role in roles if role!=item['parent']['role']]
    role=min(available,key=lambda value:(costs[value],len(assignments[value]),value))
    item['role']=role
    assignments[role].append(item['record']['id'])
    costs[role]+=item['cost']
(OUT/'inputs').mkdir(parents=True)
(OUT/'reading_packets_v1').mkdir()
extra=[]
for filename in ['EVIDENCE_291381_TOLBERT_DATES_V1.md','EVIDENCE_50559_ACCESSION_DATE_V1.md']:
    p=BASE/'root_join_conflict_counter_v1'/filename
    extra.append(save(OUT/filename,p.read_text(encoding='utf-8')))
rows=[]
for item in prepared:
    row=item['record'];ident=row['id'];stem=ident.replace(':','_')
    original=save(OUT/'inputs'/(stem+'_original.txt'),item['original'])
    candidate=save(OUT/'inputs'/(stem+'_candidate.txt'),item['body'])
    delta=''.join(difflib.unified_diff(item['body'].splitlines(True),item['machine'].splitlines(True),fromfile='current_body',tofile='machine_proposal'))
    sections=[('original',item['original']),('current_candidate',item['body']),
              ('machine_proposal_not_authority',item['machine']),('full_current_to_machine_diff',delta or '기계 제안은 현재 본문과 같다'),
              ('root_instruction',instructions[ident])]
    framed=''
    for label,text in sections:
        framed+='=== BEGIN '+ident+' '+label+' ==='+chr(10)+text+chr(10)+'=== END '+ident+' '+label+' ==='+chr(10)
    parts=[]
    for offset in range(0,len(framed),6000):
        fragment=framed[offset:offset+6000]
        parts.append(dict(**save(OUT/'reading_packets_v1'/(stem+'_'+str(offset//6000+1).zfill(4)+'.txt'),fragment),
            characters=[offset,offset+len(fragment)]))
    source=native_rows[ident]
    record={key:source[key] for key in ['id','source','split','source_ids','source_ids_sha256',
        'original_text_sha256','input_ids','occurrences','language_bucket']}
    record.update(original=original,candidate=candidate,reading_parts=parts,role=item['role'],
        previous_review=item['parent']['review'],previous_body=row['body'],
        candidate_reasons=row['post_policy_reasons'],root_instruction=instructions[ident],
        root_approved=False,cache_admitted=False)
    rows.append(record)
by_id={row['id']:row for row in rows}
for role,ids in assignments.items():
    directory=BASE/'agents'/role/GROUP
    directory.mkdir(parents=True,exist_ok=False)
    start=['# 후속 본문 보존·숫자 경계 판독','',
        '입력은 이START/TASK와 거기 지정한 원문·현재후보·연속패킷 및 아래 정확 날짜증거MD뿐이다.',
        '쓰기는 이 자기 신규폴더의 새TXT/MD뿐이다. 기존원문·캐시·후보·리뷰를 덮거나 삭제하지 않는다.',
        '코드·시험·해시·통계·계산·Python·Git·웹·모델·GPU·타세션·보호자료·목록밖경로는 금지한다.',
        '지정 원문·현재후보·기계제안·전체diff·root지시를 논리END와 실제EOF까지 읽는다.6000문자조각은 연속이다.',
        '기계삭제제안은 정답이 아니다.47767의 실제var()함수와299540의 채워진 음악 설명은 삭제하지 않는다.',
        '나머지 실제 위키/HTML껍데기·빈표제만 root의 정확 범위로 정리한다. 고유명사·숫자·날짜·조건·부정·귀속을 보존한다.',
        '수정필요없으면ACCEPT_CANDIDATE와TASK의정확current candidate경로. 실제수정은자기새전체TXT/sidecar와REVISE_TEXT.',
        '모든review_NNN.md는ID/판정/실제판독범위/정확출력/구체근거5열이다. 상태칸에는상태만,출력칸에는실제TXT절대경로를쓴다.',
        '원문/후보는BASE/'+GROUP+'/inputs,새출력만BASE/agents/역할/'+GROUP+'다.입력경로에agents/역할을덧붙이지않는다.',
        '불명확한숫자·이름·누락공식은생성하지않고좁은질문NEEDS_ROOT를보낸다.다른독립ID는계속한다.검수한국어/원문언어유지.',
        '이14건은478전량검산에서드러난후속전부이며전체goal작업량상한이아니다.캐시채택/품질완료를선언하지않는다.',
        '허용된 추가 날짜증거:']
    start += ['- '+str(ROOT/pin['path']) for pin in extra]
    save(directory/'START_HERE.md',chr(10).join(start)+chr(10))
    for task,offset in enumerate(range(0,len(ids),5),1):
        lines=['# TASK_'+str(task).zfill(3),'START_HERE의권한과root지시를따른다.']
        for ident in sorted(ids)[offset:offset+5]:
            row=by_id[ident]
            lines += ['## '+ident,'original: '+str(ROOT/row['original']['path']),
                      'candidate: '+str(ROOT/row['candidate']['path']),'root지시: '+row['root_instruction'],'연속입력:']
            lines += ['- '+str(ROOT/pin['path']) for pin in row['reading_parts']]
        save(directory/('TASK_'+str(task).zfill(3)+'.md'),chr(10).join(lines)+chr(10))
manifest=dict(status='ALL14_POST_BODY_TRANSFORMS_AND_NUMERIC_FLAGS_REQUIRE_INDEPENDENT_REVIEW',rows=rows,
    assignments=assignments,source_characters_by_role=dict(costs),extra_evidence=extra,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [audit_path,snapshot_path,draft_path,Path(__file__)]},
    source_code_pins=source_code_pins,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(OUT/'manifest.json',manifest)
print(json.dumps(dict(sources=14,assignments={role:len(ids) for role,ids in assignments.items()},
    characters=dict(costs),packet_parts=sum(len(row['reading_parts']) for row in rows)),ensure_ascii=False))
