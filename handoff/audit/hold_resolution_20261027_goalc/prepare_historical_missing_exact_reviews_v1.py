"""Reopen only ten assigned sources that have no saved review row."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

cohort='repeat_named_roles_counter_v2'
directory=inv.BASE/'agents/historical_review'/cohort
manifest=inv.cache.read(inv.BASE/cohort/'manifest.json')
sources={r['id']:r for r in manifest['rows']}
lines=['# 총괄 정확 재개 허용서 V2: 저장 판독 누락 10건','',
 'V1 허용 범위에 아래 자기 TASK005/007의10건을 추가한다. 새 출생 START의 이전 그룹 제한에 대한 명시 예외다.',
 '허용은 지정 원문/후보/전 연속 패킷/자기 기존 TXT·MD 읽기와 자기 폴더 새 전체 TXT·사유 MD·5열 review_005_vN.md 또는 review_007_vN.md 생성뿐이다.',
 'V1 및 공유 ROOT_MEDIATION_V1/V2/V3도 읽기 허용. 1403490의 ROOT_EVIDENCE_1403490_CREDIT_V1.md도 정확 근거로 읽는다.',
 '현재 수집에는 이10건의 저장된 review행이 없다. 과거에 읽었다는 메시지로 완료 처리하지 않고 원문/후보/기존 실제 수정본과 다시 대조해 저장 판독을 남긴다. 코드/Git/웹/해시/타역할/원형 덮기·삭제 금지.','']
for number in (5,7):
    task=directory/f'TASK_{number:03}.md'
    lines += ['## '+task.name, '정확 TASK: '+str(task)]
    for key in sorted(safeguards.explicit_task_ids(task.read_text(encoding='utf-8'))):
        row=sources[key]
        inv.require(row['role']=='historical_review','unexpected owner')
        lines+=['### '+key,'original: '+str(ROOT/row['original']['path']),
            'candidate: '+str(ROOT/row['candidate']['path'])]
        lines += ['- '+str(ROOT/p['path']) for p in row['reading_parts']]
        prefix=key.replace(':','_')
        lines += ['기존 자기 산출물: '+str(p) for p in sorted(directory.glob(prefix+'*')) if p.suffix in {'.txt','.md'}]
        lines.append('')
out=directory/'ROOT_EXACT_RECHECK_SCOPE_V2.md'
with out.open('x',encoding='utf-8') as stream:stream.write(chr(10).join(lines)+chr(10))
print(json.dumps(dict(path=str(out.relative_to(ROOT)),sha256=inv.file_sha(out),sources=10),ensure_ascii=False))
