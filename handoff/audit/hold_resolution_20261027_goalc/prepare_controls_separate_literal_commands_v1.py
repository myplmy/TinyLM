"""Give exact commands for all distinct candidate pairs without changing inputs."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

group='remaining_literal_full_counter_v1'
manifest_path=inv.BASE/group/'manifest.json'
manifest=inv.cache.read(manifest_path)
directory=inv.BASE/'agents/context_controls'/group
reader=AUDIT/'read_context_controls_literal_packet_v1.py'
scope=inv.cache.read(AUDIT/'CONTROLS_LITERAL_AND_GLOSSARY_INPUT_SCOPE_V1.json')
assert inv.file_sha(reader)==scope['literal']['reader']['sha256']
registry_path=ROOT/scope['literal']['registry']['path']
assert inv.file_sha(registry_path)==scope['literal']['registry']['sha256']
registry=inv.cache.read(registry_path)
rows={row['id']:row for row in manifest['rows'] if row['role']=='context_controls'}
assert set(rows)==set(registry['sources'])
result=[]
def save(path,text):
    payload=text.encode('utf-8')
    assert 0<len(payload)<20_000_000
    with path.open('xb') as stream:stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
for task in sorted(directory.glob('TASK_*.md')):
    ids=sorted(safeguards.explicit_task_ids(task.read_text(encoding='utf-8')))
    selected=[ident for ident in ids if rows[ident]['original']['sha256']!=rows[ident]['candidate']['sha256']]
    if not selected:continue
    lines=['# 서로 다른 입력의 정확 고정 읽기 명령: '+task.stem,'',
        '아래 source-id는 원문/후보/diff가 다른 ID가 아니다. 같은 지정 ID의 모든 연속 frame을 뜻한다.',
        '후보가 원문과 다르므로 원문 전문·후보 전문·전체diff를 모든 패킷 순서대로 읽는다. 동일입력 생략 계획을 적용하지 않는다.',
        '2000문자 패킷이므로 piece는1이고 출력예산8000 이상을 쓴다. 실제 논리 END/EOF를 각각 확인한다.',
        '실제 원문 입력은 아래 기존 고정 reader만 허용한다. raw cat/sed/검색/다른Python/코드·registry 열기는 금지다.',
        '이 문서와 자기 정확 TASK/리뷰는 literal cat으로 읽을 수 있다. 자기 새TXT/MD만 작성하며 내용 판독 전 행은 미판독으로 명시한다.','']
    for ident in selected:
        row=rows[ident]
        assert row['reading_parts']==registry['sources'][ident]
        lines+=['## '+ident,'원문SHA: '+row['original']['sha256'],'후보SHA: '+row['candidate']['sha256'],
                '필수 전체 패킷 수: '+str(len(row['reading_parts'])),'```bash']
        lines+=['/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B '+str(reader)
                +' --source-id '+ident+' --packet '+str(number)+' --piece 1'
                for number in range(1,len(row['reading_parts'])+1)]
        lines+=['```','']
    result.append(dict(save(directory/('ROOT_SEPARATE_INPUT_'+task.stem+'_V1.md'),chr(10).join(lines)+chr(10)),ids=selected))
lines=['# 서로 다른 입력: 전체 명령 목록','',
    '이 목록의 정확 자기 TASK 명령 MD만 추가 허용한다. 기존 ROOT_IDENTITY가 nonidentical로 표시한 ID는 이 명령으로 전량 읽는다.',
    '미판독 NEEDS_ROOT 행은 실제 판독 후 정확 새 리뷰로 교체 연결한다. 원문/후보가 다르다는 이유로 HOLD 결론을 만들지 않는다.','']
for item in result:lines+=['- '+str(ROOT/item['path'])+' : '+','.join(item['ids'])]
index=save(directory/'ROOT_SEPARATE_INPUT_COMMANDS_INDEX_V1.md',chr(10).join(lines)+chr(10))
inv.write_json(AUDIT/'CONTROLS_SEPARATE_LITERAL_COMMANDS_V1.json',dict(
    status='EXACT_READING_COMMANDS_ONLY_NOT_CONTENT_REVIEW',plans=result,index=index,
    sources=sum(len(item['ids']) for item in result),input_pins={str(p.relative_to(ROOT)):inv.file_sha(p)
        for p in [manifest_path,reader,registry_path,Path(__file__)]},
    source_or_candidate_changed=False,goal_complete=False,training_authorized=False))
print(json.dumps(dict(plans=len(result),sources=sum(len(item['ids']) for item in result),inputs_changed=0)))
