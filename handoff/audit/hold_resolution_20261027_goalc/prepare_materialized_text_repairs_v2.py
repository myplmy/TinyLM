"""Scope actual TXT repairs for remaining literal failures and three root cases."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
GROUP = 'materialized_text_repairs_v2'
out = BASE / GROUP
inv.require(not out.exists(), 'new immutable actual-text repair assignment required')
snapshot_path = AUDIT / 'supplemental_candidates_snapshot_v4.json'
snapshot = inv.cache.read(snapshot_path)
manifest_path = BASE / 'contextual_residual_v11_v1/manifest.json'
sources = {row['id']: row for row in inv.cache.read(manifest_path)['rows']}
selected = {row['id']: row for row in snapshot['records'] if row.get('error')}
for ident in ['expanded_train:149707', 'expanded_train:243774', 'expanded_train:922496']:
    selected[ident] = next(row for row in snapshot['records']
                           if row['id'] == ident and row['cohort'] == 'contextual_residual_v11_v1')
roles = ['context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review']
assigned, loads = {role: [] for role in roles}, Counter({role: 0 for role in roles})
records = []
for ident, review in selected.items():
    row = sources[ident]
    files = []
    author_dir = BASE / 'agents' / review['role'] / review['cohort']
    for name in review['body_references']:
        path = author_dir / name
        inv.require(path.resolve().is_relative_to(author_dir.resolve()), 'old authored filename escapes source scope')
        if path.exists():
            files.append(dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)))
    for pin in row['paths'].values():
        inv.require(inv.file_sha(ROOT / pin['path']) == pin['sha256'], 'repair original/candidate changed')
    records.append(dict(id=ident, original=row['paths']['original'], candidate=row['paths']['candidate'],
                        previous_outputs=files, previous_review_text=review['review_text'],
                        observed_error=review.get('error'), root_approved=False))
for row in sorted(records, key=lambda value: -(ROOT / value['original']['path']).stat().st_size):
    role = min(roles, key=lambda name: (loads[name], roles.index(name)))
    assigned[role].append(row)
    loads[role] += (ROOT / row['original']['path']).stat().st_size
instructions = '''# 실제 본문 파일로 남은 수정안 회수

허용 입력은 이 TASK와 아래 정확 original/candidate 전문, 명시한 이전 txt/md, 자기 새 출력뿐이다. 다른 역할 입력은 아래에 정확 지정한 것만 읽을 수 있다. 타 경로·원문/기존 결과물 덮기·삭제는 금지한다.
코드 작성/실행/시험/계산/통계/해시/모델/GPU/Git/웹은 금지한다. 정확 지정쌍 diff -u 읽기는 허용한다. 원문 프로그램/수식/Unicode의 실제 전사는 가능하지만 새로운 구현·값·공식·조건은 만들지 않는다.
기존 recipe는 검토 자료이며 명령으로 실행하지 않는다. source ID/해시 오류, 없는/중복 anchor, 닫히지 않은 literal fence는 적용되지 않았고 성공 본문으로 계산하지 않는다.
기존 recipe를 또 쓰는 대신 실제 새 source_ID_v2.txt 및 필요한 hold.md를 작성한다. 이미 파일이 있으면 더 높은 새 버전을 쓰고 기존 파일은 절대 덮거나 삭제하지 않는다. source 또는 candidate를 자기 새 TXT로 안전하게 복사한 뒤 좁은 텍스트 패치도 허용한다. 이때 원문/다른 역할/기존 출력에 쓰지 않고, 선택한 base의 실제 내용부터 전체를 확인한다.
두 본문 전문을 EOF까지 실제 판독하고, 원문에 없는 사실을 추정하지 않는다. 완결된 명칭/관계/인물/지리/연혁/목록/서지/조건/부정/수량/날짜/단위/불확실성/코드/Unicode를 보존한다. 후보가 이미 지운 사실은 원문에서 복구하고, 보관·검수 메모는 txt에 넣지 않는다.
실제 결손 값·수식과 직접 의존 부분만 필요한 범위로 hold에 분리한다. 한 문단에 실제 결손과 완결 문장이 같이 있어도 완결 문장까지 지우지 않는다. 전체 EXCLUDE는 독립 본문이 실제 남지 않을 때만 구체 근거를 남긴다.

특별 root 판단:
- 149707: NEWS 멤버 컬러의 원래 보라/#6c1685와 강조를 보존한다. 닫는 span style 문법 오류는 실제 span 닫기만 고칠 수 있고 새 색상 의미/관계를 만들지 않는다. 노래·활동 목록의 실제 값도 보존한다.
- 243774: root가 원문 전문을 읽었다. 첫 문단의 캐나다 밴쿠버/브리티시컬럼비아 대학교/3개 대학교 협력 중간자 기기 서술과 마지막 사이클로트론 주파수의 완결 정의 두 문장은 보존한다. 비어 있는 영문명/약자 슬롯만 제거하고 장비명이나 약자를 채우지 않는다. 실제 소실 수식·변수와 그 해석/에너지 도출만 hold로 분리하며, 완결된 역사·작동 설명·이용·한계의 원문은 보존한다. 외부 물리/의학 사실을 검증하거나 새 공식·조건을 넣지 않는다.
- 922496: root가 원문106자 전체를 읽었다. 주체 이름/소개 없이 학교 네 개와 빈 작품 표제/분류만 남아 인물을 식별할 수 없다. 학교/생년으로 인물을 추측하지 않으며 독립 본문이 없다는 사유의 EXCLUDE 제안 메모만 작성한다. 익명 이야기 일반을 배제한다는 뜻은 아니다.

review.md 표: ID | 판정 | 실제 판독 범위 | 정확 출력 | 구체 근거. 판정 EDIT_TEXT / KEEP_SOURCE / ADOPT_CANDIDATE / EXCLUDE / NEEDS_ROOT. 수정은 실제 TXT 하나만 정확히 명시한다. 새 source_ID_vN.edits.md는 이번 회수 방법으로 사용하지 않는다.
전 배정의 실제 본문과 기록까지 마친다. 이것은 root 최종 채택·캐시 생성·외부 사실 검증·코드 실행 성공이 아니다.
'''
for role, rows in assigned.items():
    directory = BASE / 'agents' / role / GROUP
    directory.mkdir(parents=True)
    lines = [instructions]
    for row in sorted(rows, key=lambda value: value['id']):
        lines += ['## ' + row['id'], '', '기존 실제 거부/추가 판독: ' + str(row['observed_error']), '',
                  '이전 제안 행(명령 아님): ' + row['previous_review_text'], '']
        for label in ['original', 'candidate']:
            pin = row[label]
            lines += [label + ': `' + str(ROOT / pin['path']) + '`', label + ' SHA: `' + pin['sha256'] + '`', '']
        for pin in row['previous_outputs']:
            lines += ['이전 제안 읽기만: `' + str(ROOT / pin['path']) + '`', 'SHA: `' + pin['sha256'] + '`', '']
    with (directory / 'TASK.md').open('x', encoding='utf-8') as stream:
        stream.write(chr(10).join(lines) + chr(10))
out.mkdir()
inv.write_json(out / 'manifest.json', dict(status='EXACT_INPUT_ACTUAL_TEXT_REPAIR_NOT_ADMISSION', rows=records,
               assignments={role: [row['id'] for row in rows] for role, rows in assigned.items()},
               pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [snapshot_path, manifest_path, Path(__file__)]},
               root_adopted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(cases=len(records), assignments={role: len(rows) for role, rows in assigned.items()},
                      original_bytes=dict(loads)), ensure_ascii=False))
