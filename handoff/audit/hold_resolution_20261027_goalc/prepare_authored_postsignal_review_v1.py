"""Review every remaining authored-body signal with a different text reader.

Previously repaired source IDs are excluded by explicit pinned receipts. Signal
presence is not an error verdict, and no approval/cache admission is produced.
"""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
GROUP = 'authored_postsignal_review_v1'
out = BASE / GROUP
inv.require(not out.exists(), 'new immutable post-signal assignment required')
integrity = AUDIT / 'authored_body_integrity_v2.json'
supplemental = AUDIT / 'supplemental_candidates_snapshot_v5.json'
selections = AUDIT / 'ROOT_READBACK_BODY_SELECTIONS_V1.json'
excluded = {row['id'] for row in inv.cache.read(supplemental)['records']}
excluded.update(row['id'] for row in inv.cache.read(selections)['rows'])
rows = [row for row in inv.cache.read(integrity)['records']
        if row.get('post_body_policy_decision') == 'PENDING' and row['id'] not in excluded]
inv.require(len(rows) == len({row['original_text_sha256'] for row in rows}), 'duplicate signal source')
roles = ['context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review']
assigned, loads = {role: [] for role in roles}, Counter({role: 0 for role in roles})
records = []
for row in rows:
    source, body = ROOT / row['source'], ROOT / row['body']
    inv.require(inv.file_sha(source) == row['original_text_sha256'] and inv.file_sha(body) == row['clean_text_sha256'],
                'post-signal original or body changed')
    inv.require(row['id'] not in {'expanded_train:756966', 'expanded_train:14760'}, 'restricted source cannot enter text review')
    match = re.search(r'/agents/([^/]+)/', row['evidence'].get('review', ''))
    author = match[1] if match else None
    records.append(dict(id=row['id'], original=dict(path=row['source'], sha256=row['original_text_sha256']),
                        candidate=dict(path=row['body'], sha256=row['clean_text_sha256']),
                        reasons=row['post_body_policy_reasons'], original_author=author,
                        pair_bytes=source.stat().st_size + body.stat().st_size, root_approved=False))
for row in sorted(records, key=lambda item: (-item['pair_bytes'], item['id'])):
    available = [role for role in roles if role != row['original_author']]
    role = min(available, key=lambda name: (loads[name], roles.index(name)))
    assigned[role].append(row)
    loads[role] += row['pair_bytes']
instructions = '''# 회수 본문에 남은 모든 형식 신호의 독립 판독

권한은 이 TASK, 자기 TASK_NNN에 지정한 정확 original/candidate 전문, 자기 새 txt/md만이다. 기존 역할의 본문도 정확히 지정한 이 파일만 읽을 수 있다. 원문·기존 결과물 덮기/삭제와 다른 경로 접근은 금지한다.
코드 작성·실행·시험·계산·통계·해시·모델·GPU·Git·웹은 금지한다. 정확 지정쌍 diff -u 읽기는 허용한다. 원문 코드/수식/Unicode의 실제 전사는 가능하지만 새 구현·값·공식·조건을 만들지 않는다.

아래 사유는 탐지 신호이지 불량 확정이 아니다. 원문과 이미 회수된 본문을 모두 처음부터 끝까지 읽고 실제 의미 보존과 잔여 손상을 판단한다. 출력이 잘리면 짧은 구간으로 이어 EOF를 확인한다. 읽지 않은 구간을 전문 판독으로 보고하거나 판독 미완만으로 전체 EXCLUDE하지 않는다.
- 반복은 서로 다른 표/절/함수/자료 항목의 같은 값·제목·서지·후렴일 수 있다. 문맥상 정상 반복은 그대로 유지하고 구체 관계를 근거에 쓴다. 무조건 중복 삭제하지 않는다.
- 빈 괄호는 함수 호출·튜플·문자열·문법 예제일 수 있다. 실제 수식/인구/단위/매개변수 결손은 복원하지 않고 결손과 직접 의존 부분만 분리하며, 같은 문단의 완결 문장을 함께 지우지 않는다.
- ‘생년월일은 미상’은 빈 날짜가 아니다. 원문에 귀속된 호적/묘비/추정/여러 설과 양력/음력, 서로 양립하는 범위·다른 정밀도는 보존한다. 같은 대상의 무귀속 양립 불가능한 단정 필드만 좁게 분리하고 어느 값을 사실로 선택하지 않는다.
- 정상 목차/내용 목록/서지/URL/외부 자료명은 실제 값이 있으면 보존한다. 신호가 HTML/위키/표라고 실제 정보가 없는 것은 아니다. 실제 색상·강조·행/열·수량/조건과 소속을 잃지 않는다.
- 필드가 채워진 인포박스는 실제 이름표와 값을 그대로 갖는 문장/목록으로 옮길 수 있다. 병렬 배열의 매칭이 불명확하면 각 원래 필드별 값 목록과 순서를 유지하고 새 연결을 추정하지 않는다. 빈 값/레이아웃 껍데기만 분리한다.
- 일반 의료/과학/역사/종교/정치/상품 문서를 주제·평판만으로 버리지 않는다. 위험 조작 절차가 실제 발견되면 세부를 재전사하지 않고 NEEDS_ROOT로 경계만 보고한다. 새 평가 문항·정답이나 대신 푼 답안을 만들지 않는다.

판정은 ACCEPT_CANDIDATE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT. 수정이 필요하면 실제 새 source_ID_v2.txt 및 필요한 hold.md를 작성한다. 이번에는 새 recipe 대신 실제 TXT로 회수한다. 자기 새 파일로 정확 base를 안전하게 복사한 뒤 좁은 텍스트 패치도 허용하지만 기존 파일이 있으면 더 높은 새 버전을 쓴다. 검수·보관 메모는 md에만 둔다.
각 TASK_NNN의 결과는 새 review_NNN.md 표: ID | 판정 | 실제 판독 범위 | 정확 출력 | 구체 근거. 이미 있는 review는 덮지 않고 새 vN을 쓴다. 수정 출력에는 실제 TXT 하나의 정확 이름만 명시한다.
묶음별 결과를 저장하고 전 배정을 계속한다. 이것은 root 최종 채택/캐시 생성/외부 사실 확인/코드 실행 성공이 아니다.
'''
assignment_map = {}
for role, assigned_rows in assigned.items():
    directory = BASE / 'agents' / role / GROUP
    directory.mkdir(parents=True)
    ordered = sorted(assigned_rows, key=lambda item: item['id'])
    tasks = []
    for start in range(0, len(ordered), 8):
        number = start // 8 + 1
        path = directory / ('TASK_%03d.md' % number)
        lines = ['# 회수 본문 독립 판독 묶음 %d' % number, '', '상위 TASK.md의 정확 권한과 형식을 따른다.', '']
        for row in ordered[start:start + 8]:
            lines += ['## ' + row['id'], '', '남은 신호(오류 확정 아님): ' + ', '.join(row['reasons']), '']
            for label in ['original', 'candidate']:
                pin = row[label]
                lines += [label + ': `' + str(ROOT / pin['path']) + '`', label + ' SHA: `' + pin['sha256'] + '`', '']
        with path.open('x', encoding='utf-8') as stream:
            stream.write(chr(10).join(lines) + chr(10))
        tasks.append(str(path.relative_to(ROOT)))
    with (directory / 'TASK.md').open('x', encoding='utf-8') as stream:
        stream.write(instructions + chr(10) + '배정 파일: ' + ', '.join(Path(path).name for path in tasks) + chr(10))
    assignment_map[role] = dict(ids=[row['id'] for row in ordered], tasks=tasks, pair_bytes=loads[role])
out.mkdir()
inv.write_json(out / 'manifest.json', dict(status='ALL_REMAINING_AUTHORED_SIGNALS_INDEPENDENT_TEXT_REVIEW_NOT_ADMISSION',
               rows=records, assignments=assignment_map,
               pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [integrity, supplemental, selections, Path(__file__)]},
               root_adopted=0, training_authorized=False, goal_complete=False))
print(json.dumps(dict(cases=len(records), assignments={role: len(value['ids']) for role, value in assignment_map.items()},
                      pair_bytes=dict(loads)), ensure_ascii=False))
