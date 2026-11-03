"""Verify every page TASK partition and write explicit last-TASK role indices."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

parser=argparse.ArgumentParser()
parser.add_argument('--phase',choices=['field','other'],required=True)
phase=parser.parse_args().phase
label,total,pages=('FIELD',18237,36) if phase=='field' else ('OTHER_TYPES',50162,98)
folder='remaining_field_title_readers_v1' if phase=='field' else 'remaining_other_types_readers_v1'
source_path=inv.BASE/folder/'complete.json'
source=inv.cache.read(source_path)
assert source['sources']==total and len(source['pages'])==pages
roles=['context_controls','context_hangul','context_latin','historical_review','legacy_review']
indices={role:[] for role in roles}
coverage=set()
for page in source['pages']:
    path=ROOT/page['path']
    assert inv.file_sha(path)==page['sha256']
    manifest=inv.cache.read(path)
    page_ids=set()
    for role,assigned in manifest['assignments'].items():
        expected=set(assigned)
        directory=inv.BASE/'agents'/role/page['group']
        tasks=sorted(directory.glob('TASK_*.md'))
        seen=set()
        for task in tasks:
            ids=safeguards.explicit_task_ids(task.read_text(encoding='utf-8'))
            assert ids and set(ids)<=expected and not (set(ids)&seen)
            seen.update(ids)
        assert seen==expected and len(tasks)==(len(assigned)+4)//5
        assert not (seen&page_ids)
        page_ids.update(seen)
        indices[role].append(dict(page=page['page'],group=page['group'],sources=len(assigned),
            tasks=[str(task.relative_to(ROOT)) for task in tasks],last_task=tasks[-1].name))
    assert len(page_ids)==page['sources'] and not (coverage&page_ids)
    coverage.update(page_ids)
assert len(coverage)==total
pins=[]
for role,items in indices.items():
    lines=['# 全ページの 자기 TASK 전량 목록','',
        '한 page의 TASK001만 처리하고 다음 page로 넘어가지 않는다. 아래 실제 마지막TASK까지 모두 처리한다.',
        '각 TASK의 모든 source ID를 리뷰에 남긴다. 이미 처리한 뒤 page의 일부는 보존하고, 빠진 앞 page를 마친 뒤 그 지점에서 이어간다.',
        '첫TASK/첫page/페이지 수는 작업량 상한이 아니다. 자기 전량은'+str(sum(row['sources'] for row in items))+'고유다.',
        '다른 역할 입력은 열지 않으며 source/body/sidecar/review를 한ID씩 마감한다. 기존 고정reader/보호 경계를 유지한다.','']
    for item in items:
        lines+=['## 페이지'+str(item['page'])+' : '+str(item['sources'])+'고유 / '+str(len(item['tasks']))+'TASK / 마지막 '+item['last_task']]
        lines+=['- '+str(ROOT/name) for name in item['tasks']]
    path=inv.BASE/'agents'/role/('ROOT_ALL_'+label+'_PAGE_TASKS_V1.md')
    data=(chr(10).join(lines)+chr(10)).encode('utf-8')
    assert len(data)<20_000_000
    with path.open('xb') as stream:stream.write(data)
    pins.append(dict(role=role,path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),
        sources=sum(row['sources'] for row in items),tasks=sum(len(row['tasks']) for row in items)))
output=AUDIT/('COMPLETE_'+label+'_PAGE_TASK_INDEX_V1.json')
assert not output.exists()
inv.write_json(output,dict(status='ALL_PAGE_TASK_PARTITIONS_VERIFIED_NOT_CONTENT_READ',
    sources=total,pages=pages,roles=pins,page_assignments=indices,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [source_path,Path(__file__)]},
    goal_complete=False,training_authorized=False))
print(json.dumps(dict(phase=phase,sources=total,pages=pages,
    roles={row['role']:dict(sources=row['sources'],tasks=row['tasks']) for row in pins})))
