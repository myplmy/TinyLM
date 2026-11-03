"""Authorize exact existing phase queues, without changing their source ownership."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
proof_path = AUDIT / 'REMAINING_OTHER_TYPES_READER_PREPARATION_VERIFIED_V1.json'
proof = inv.cache.read(proof_path)
assert proof['unique_sources'] == 50162 and proof['pages'] == 98
assert proof['new_file_size_check']['files'] == 396944
role_counts = {'context_controls': (9694,1988), 'context_hangul': (10074,2064),
               'context_latin': (10119,2067), 'historical_review': (10133,2067), 'legacy_review': (10142,2069)}
rows=[]
for role,(sources,tasks) in role_counts.items():
    directory=inv.BASE/'agents'/role
    queue=directory/'REMAINING_OTHER_TYPES_QUEUE_V1.md'
    index=directory/'ROOT_ALL_OTHER_TYPES_PAGE_TASKS_V1.md'
    assert queue.is_file() and index.is_file()
    text=chr(10).join(['# 나머지 유형98페이지의 정확 후속 판독 권한','',
        '역할='+role+'; 자기배정 '+str(sources)+'고유/'+str(tasks)+'TASK; 총98페이지.',
        '선결은 현재literal72개TASK와옛미결/지시된보완, 그뒤field36페이지의각자모든TASK다. 그선결전에는other로뛰지않는다.',
        '모두마친뒤아래자기큐와전체TASK색인을따라other001–098의각TASK전부를계속한다. 각페이지첫TASK만처리하고다음페이지로뛰지않는다.',
        '큐/색인: '+str(queue)+' / '+str(index),
        '각페이지자기START_HERE/TASK/READING_VIEWS/ROOT_IDENTITY와그들이정확명시한입력만읽고,자기배정ID만새TXT/MD/review로정제한다.',
        '기존입력/본문/캐시/리뷰는덮거나삭제하지않는다. 기존선택본을고칠때는새버전으로만만든다.',
        'controls는각페이지ROOT_SCOPED_INPUT_READER_V1.md에적힌고정readonly reader만예외로실행한다. 임의Python/코드/registry/원문raw직독은금지다.' if role=='context_controls' else
        '자기TASK의정확native original/candidate전문과전체diff를EOF까지직접읽는것도packet전체판독과동등하게허용한다. 동일proof가있으면원문실제전문+동일후보연결+마지막diff만읽을수있다. 도구잘림은전문이아니다.',
        '다른역할/보호ID및동일SHA/보호TinyDataset/타세션자료·코드/시험/통계/해시/웹/Git/모델/GPU는금지다.',
        '없는수식/이름/값을만들지않고실제결손과직접종속최소구간만원형sidecarHOLD한다. 완결한목록/질문/부분코드/조건·숫자·귀속·불확실성을보존한다.',
        '주어생략/미응답/원저자버그/다른언어/보안주제만으로삭제하지않는다. 보통의명확한경계는이미승인된원칙으로닫고고유하게애매한문맥만총괄에게질문한다.',
        '이준비/배정은내용검토완료나캐시채택이아니다. 현재과업/페이지/단계의끝은전체goal의정지사유가아니다.',''])
    target=directory/'ROOT_OTHER_TYPES_PHASE_AUTHORIZATION_V1.md'
    with target.open('x',encoding='utf-8') as stream:stream.write(text)
    rows.append({'role':role,'sources':sources,'tasks':tasks,'scope':str(target.relative_to(ROOT)),
                 'sha256':inv.file_sha(target),'queue_sha256':inv.file_sha(queue),'task_index_sha256':inv.file_sha(index)})
inv.write_json(AUDIT/'OTHER_TYPES_PHASE_EXACT_AUTHORIZATION_V1.json',{
    'status':'EXACT_SEQUENTIAL_PHASE_AUTHORIZATION_NOT_CONTENT_REVIEW','rows':rows,
    'input_pins':{str(path.relative_to(ROOT)):inv.file_sha(path) for path in (proof_path,Path(__file__))},
    'source_or_candidate_changed':False,'cleaned_prose_authored_by_root':0,'goal_complete':False,'training_authorized':False})
print(json.dumps({'roles':len(rows),'sources':sum(r['sources'] for r in rows),'tasks':sum(r['tasks'] for r in rows)}))
