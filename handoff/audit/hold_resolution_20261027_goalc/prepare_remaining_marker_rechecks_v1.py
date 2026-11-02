"""Grant exact rechecks for newly visible unbound geographic claimants."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

cohort='repeat_named_roles_counter_v2'
manifest=inv.cache.read(inv.BASE/cohort/'manifest.json')
sources={r['id']:r for r in manifest['rows']}
diagnostic=inv.cache.read(AUDIT/'EXACT_COHORT_BODY_DIAGNOSTICS_V1.json')
selected={r['id']:r for r in diagnostic['rows'] if r['cohort']==cohort}
rows=[]
for role,ids in {'context_controls':['expanded_train:629354'],
                 'context_latin':['expanded_train:748220','expanded_train:748497']}.items():
    directory=inv.BASE/'agents'/role/cohort
    lines=['# 총괄 정확 재검토 V2: 후속 주체 결손 진단','',
        'V1에 더해 아래 자기 원문만 재개한다. 새 출생 START의 이전 그룹 제한에 대한 명시 예외다.',
        '허용: 아래 원문/후보/전 연속 패킷/정확 선택본문/자기 기존 review 읽기, 자기 폴더 새 버전 전체 TXT·원형 sidecar·정정 review 생성.',
        '금지: 타역할·미지정 탐색·코드·통계·해시·웹·Git·원형 덮기/삭제.',
        '총괄 진단 표시만으로 삭제하지 말고 원문 전문에서 주체가 실제 소실됐는지 확인한다. 명명 지역·직접 거리·목록 순서·완결된 실제 주장은 보존하고, 미상 주체의 관계절만 원형 sidecar로 분리한다.',
        '공유 ROOT_MEDIATION_V1/V2/V3 읽기 허용. 실제 주체가 다른 셀에 채워져 있으면 그 근거를 제시하고 보존한다. 출력 칸은 정확 TXT 하나만 지정한다.','']
    for key in ids:
        source=sources[key]
        inv.require(source['role']==role,'author ownership mismatch')
        matches=[p for p in sorted(directory.glob('TASK_*.md')) if key in safeguards.explicit_task_ids(p.read_text(encoding='utf-8'))]
        inv.require(len(matches)==1,'one task required')
        task=matches[0]
        row=selected[key]
        lines += ['## '+key,'TASK: '+str(task),'original: '+str(ROOT/source['original']['path']),
            'candidate: '+str(ROOT/source['candidate']['path'])]
        lines += ['- '+str(ROOT/p['path']) for p in source['reading_parts']]
        lines += ['수집된 정확 본문: '+str(ROOT/row['body']['path']),
            '정확 자기 review: '+str(ROOT/row['review']['path'])]
        for marker in row['remaining_literal_review_markers']:
            lines += ['진단 '+marker['kind']+' / 본문 '+str(marker['line'])+'행: '+marker['preview']]
        lines.append('')
    out=directory/'ROOT_EXACT_RECHECK_SCOPE_V2.md'
    with out.open('x',encoding='utf-8') as stream:stream.write(chr(10).join(lines)+chr(10))
    rows.append(dict(role=role,path=str(out.relative_to(ROOT)),sha256=inv.file_sha(out),ids=ids))
receipt=AUDIT/'ADDITIONAL_MARKER_RECHECK_SCOPE_V1.json'
with receipt.open('x',encoding='utf-8') as stream:
    json.dump(dict(rows=rows,producer_sha256=inv.file_sha(Path(__file__)),root_adopted=0),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(rows,ensure_ascii=False))
