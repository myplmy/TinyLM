"""Assign only additional pinned source packets to the existing five authors."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
AUDIT = Path(__file__).resolve().parent
ROLES = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
packets = json.loads((BASE / "pending_profile_v1/review_packets/manifest.json").read_text())
previous = json.loads((AUDIT / "family_assignments_v1.json").read_text())
covered = {i for value in previous.values() for i in value["ids"]}
new = [r for r in packets["rows"] if r["id"] not in covered]
assigned = {role: [] for role in ROLES}
loads = {role: 0 for role in ROLES}
for row in sorted(new, key=lambda r: (-r["input_ids"], r["id"])):
    role = min(ROLES, key=lambda k: (loads[k], k))
    assigned[role].append(row)
    loads[role] += row["input_ids"]
result = {}
for role in ROLES:
    directory = BASE / "agents" / role / "profile_resolution_v1"
    directory.mkdir()
    lines = ["# 추가 원문 문맥 판독과 텍스트 정제", "",
             "역할은 지정 원문 판독과 새 txt/md 작성이다. 총괄은 아래 탐지 사유를 불량 확정으로 보지 않으며 실제 본문으로 반증할 것을 요청한다. 현재 맡은 교정을 먼저 마친 뒤 진행한다.", "",
             "허용 입력은 이 TASK에 나열한 정확 원문 파일뿐이다. 코드·시험·전처리·코퍼스 통계·해시 계산·모델·GPU·Git·웹·설치·삭제·목록 밖 접근 금지. 원문과 이전 저장물 수정 금지. 읽기는 일반 텍스트 도구로 하고 새 작성은 이 디렉터리 안 txt/md만 허용한다.", "",
             "원문을 끝까지 읽고 KEEP/EDIT/EXCLUDE를 제안한다. KEEP은 코드/전사/반복/목록이 문맥에서 유효한 이유를 기록한다. EDIT는 원문 문구·숫자·날짜·부정·조건·주체·순서를 보존하고 빈 표제/별칭 슬롯/UI/완결성이 깨진 구간만 분리한다. 표의 대응이 원문에서 분명하면 그 구조와 값을 보존한다. 이름·수식·값·링크·문장 내용을 만들어 넣거나 새 동의어로 바꾸지 않는다. 코드가 실제 잘려 있고 독립 설명이 남지 않거나 조각 경계를 분리할 수 없으면 구체 소실/종속 참조를 적어 EXCLUDE한다. 탐지 라벨 자체만으로 EXCLUDE하지 않는다. 판정 불명인 경우 정확한 원문 구절과 갈리는 이유를 총괄에게 반환하고 독립 작업을 계속한다.", "",
             "EDIT 본문은 SOURCE_ID.txt, 분리 원문과 사유는 SOURCE_ID_hold.md에 별도 작성한다. KEEP은 원문 재복사 없이 review에 KEEP으로 기록한다. EXCLUDE는 SOURCE_ID_exclude.md에 실제 결손·복원 불가와 안전한 부분 보존 가능성을 판단한 이유를 적는다. 검수 메모를 txt에 넣지 않는다.", "",
             "새 review.md 표 열: ID | KEEP/EDIT/EXCLUDE/NEEDS_ROOT | 실제 원문 판독 범위 | 보존·분리·제외 이유 | 실제 출력 파일명. rules.md에는 이 원문에서 확인한 재사용 가능한 문맥 기준과 반례를 적는다. 전량 사실검증/모델 품질/전체 잔여 완료로 보고하지 않는다.", ""]
    rows = []
    for row in sorted(assigned[role], key=lambda r: r["id"]):
        source = ROOT / row["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == row["sha256"]
        lines += ["## " + row["id"], "", "정확 원문: `" + str(source) + "`", "",
                  "이전 탐지 사유(판독으로 반증 가능): " + ", ".join(row["reasons"]), "",
                  "새 파일 접두사: " + row["id"].replace(":", "_"), ""]
        rows.append({k: row[k] for k in ["id", "path", "sha256", "reasons", "input_ids"]})
    task = directory / "TASK.md"
    with task.open("x", encoding="utf-8") as f:
        f.write(chr(10).join(lines))
    result[role] = dict(rows=rows, task=str(task.relative_to(ROOT)), input_ids=loads[role])
with (AUDIT / "profile_assignments_v1.json").open("x", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write(chr(10))
print(json.dumps({role: dict(documents=len(assigned[role]), input_ids=loads[role]) for role in ROLES}))
