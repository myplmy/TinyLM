"""Explicitly reopen only each role's already assigned pending literal records."""
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

group='remaining_literal_full_counter_v1'
source_path=inv.BASE/group/'manifest.json';source=inv.cache.read(source_path)
by_id={row['id']:row for row in source['rows']}
snapshot_path=inv.BASE/(group+'_snapshots/v9/complete.json');snapshot=inv.cache.read(snapshot_path)
pending=[]
for pin in snapshot['shards']:
    path=ROOT/pin['path'];assert inv.file_sha(path)==pin['sha256']
    pending.extend(row for row in inv.cache.read(path) if row.get('status')=='TEXT_ADJUDICATION_NOT_ADMISSION'
        and row['id']!='expanded_train:1046282')
outputs=[]
for role in source['assignments']:
    directory=inv.BASE/'agents'/role/group
    assigned=sorted(source['assignments'][role])
    lines=['# 자기 이전 literal 미결의 정확 입력 재개 허가','',
        '현재field폴더와 별도로 아래 자기 과거literal입력/리뷰/새출력 범위를 다시 명시 허용한다.',
        '이 MD와 아래 명시한 자기TASK/리뷰/원문/후보/기존자기TXT·MD만 읽는다. 다른역할/다른cohort/코드/JSON·registry 접근 허가는 아니다.',
        '아래 옛 자기폴더에 새TXT/MD/정확TASK번호의새리뷰버전만 작성할 수 있다. 기존파일은 덮거나 삭제하지 않는다.',
        'controls의 실제원문은 여전히 기존literal고정reader를 쓰며 이MD/자기TASK·리뷰는literalcat으로읽는다.',
        '받은root중재/정확primaryMD를 적용해 새리뷰에 연결한다. 답없는 실제애매함은 정확문구로묻고 독립작업을계속한다.',
        '현재literal이아직TASK072까지끝나지않은역할은 과거보완후남은literalTASK를계속하고그전field로뛰지않는다.','']
    rows=[row for row in pending if row['role']==role]
    files=list(directory.glob('*.txt'))+list(directory.glob('*.md'))
    base_dir=directory/'candidate_bases_v1'
    if base_dir.is_dir():files+=list(base_dir.glob('*.txt'))
    for row in rows:
        ident=row['id'];native=by_id[ident]
        assert native['role']==role
        number=assigned.index(ident)//5+1
        task=directory/('TASK_'+str(number).zfill(3)+'.md')
        assert ident in safeguards.explicit_task_ids(task.read_text(encoding='utf-8'))
        review=ROOT/row['review']['path'];assert review.is_relative_to(directory)
        digits=ident.split(':')[1]
        match=re.compile(r'(?<![0-9])'+digits+r'(?![0-9])')
        drafts=sorted(path for path in files if match.search(path.name))
        lines+=['## '+ident,'TASK: '+str(task),'이전리뷰: '+str(review),
            '원문: '+str(ROOT/native['original']['path']),
            '후보: '+str(ROOT/native['candidate']['path']),
            '현재질문: '+row['reason'],'지정된기존자기초안/근거(읽기만허용;선택승인아님):']
        lines+=['- '+str(path) for path in drafts]
        lines+=['새출력허용폴더: '+str(directory),'']
    path=directory/'ROOT_PREVIOUS_PENDING_EXACT_PATHS_V1.md'
    data=(chr(10).join(lines)+chr(10)).encode('utf-8');assert 0<len(data)<20_000_000
    with path.open('xb') as stream:stream.write(data)
    outputs.append(dict(role=role,pending=len(rows),path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path)))
inv.write_json(AUDIT/'LITERAL_PREVIOUS_PENDING_EXACT_PATHS_V1.json',dict(
    status='EXACT_ROLE_REOPENING_ONLY_NOT_NEW_CONTENT_REVIEW',roles=outputs,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [source_path,snapshot_path,Path(__file__)]},
    goal_complete=False,training_authorized=False))
print(json.dumps(dict(roles={row['role']:row['pending'] for row in outputs})))
