"""Name every path for three still-unclosed birth review rows."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

cohort='remaining_birth_full_counter_v1'
manifest=inv.cache.read(inv.BASE/cohort/'manifest.json')
sources={r['id']:r for r in manifest['rows']}
rows=[]
for key in ('expanded_train:1045101','expanded_train:155479','expanded_train:11036'):
    source=sources[key]
    directory=inv.BASE/'agents'/source['role']/cohort
    tasks=[p for p in sorted(directory.glob('TASK_*.md')) if key in safeguards.explicit_task_ids(p.read_text(encoding='utf-8'))]
    inv.require(len(tasks)==1,'one exact TASK required')
    task=tasks[0]
    lines=['# 총괄 정확 재개 V4: '+key,'',
        '이 ID는 현재와 같은 remaining_birth_full_counter_v1의 자기 배정이다. 아래 정확 입력/자기 기존 출력/새 버전 쓰기를 재허용한다.',
        '원문/후보/전 연속패킷과 자기 기존 TXT·MD 읽기, 자기 폴더 새 전체 TXT·원형 sidecar·같은 TASK번호 정정 review만 생성한다. 모든 쓰기에 set -C를 적용하며 기존 파일 덮기·삭제·코드/Git/웹/타역할 접근 금지.',
        '공유 ROOT_MEDIATION_V1/V2/V3 읽기 허용. 새 리뷰의 출력 칸은 정확 TXT 하나만, sidecar는 근거 칸에 적는다.',
        'TASK: '+str(task),'original: '+str(ROOT/source['original']['path']),
        'candidate: '+str(ROOT/source['candidate']['path']),'전문 연속 패킷:']
    lines+=['- '+str(ROOT/p['path']) for p in source['reading_parts']]
    number=task.stem.split('_')[1]
    lines+=['기존 자기 리뷰: '+str(p) for p in sorted(directory.glob('review_'+number+'*.md'))]
    if key.endswith(':1045101'):
        lines+=['경계: 형 이름이 소실된 `형 와 도 음악가이다.`만 보류, 명시 레바논 출생·실명/직업·BBC/1958/2500곡·가수명·사망일/코로나 합병증은 보존. 사망문의 대상없는 `에서`만 분리. 새 형 이름/도시 생성 금지.']
    elif key.endswith(':155479'):
        lines+=['경계: 출생연도 상충 1376/1375만 분리하고 원문18세/74세/두 노장60세 넘김/7년 및 다른 최윤덕 나이 등 독립 관계는 전부 보존한다. 생년에서 역산해 지우거나 새 계산을 하지 않는다.']
    else:
        lines+=['경계: 같은 인물의 무조건적 완전 출생일1769-08-15/1771-12-31 전체 두 주장을 원형sidecar에 분리한다. 월일만 남겨 두 생일을 새로 만들지 않으며 독립 이름·사망일·생애는 보존. 본문에 검수 설명을 넣지 않는다.']
    out=directory/'ROOT_EXACT_RECHECK_SCOPE_V4.md'
    with out.open('x',encoding='utf-8') as stream:stream.write(chr(10).join(lines)+chr(10))
    rows.append(dict(id=key,role=source['role'],path=str(out.relative_to(ROOT)),sha256=inv.file_sha(out)))
with (AUDIT/'BIRTH_UNCLOSED_EXACT_RECHECKS_V1.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(rows=rows,producer_sha256=inv.file_sha(Path(__file__))),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(rows,ensure_ascii=False))
