"""Pin excluded authored sources for independent salvage-or-exclude reading.

Known restricted sources stay metadata-only and are not reopened, copied,
hashed or delegated. No excluded proposal is automatically admitted.
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
source = AUDIT / "authored_body_integrity_v2.json"
out = BASE / "exclusion_second_review_v1"
inv.require(not out.exists(), "new immutable exclusion review namespace required")
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:1216576"}
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
assignments, loads = {role: [] for role in roles}, Counter({role: 0 for role in roles})
records, unassigned = [], []
for row in inv.cache.read(source)["records"]:
    if row["decision"] != "EXCLUDE":
        continue
    if row["id"] in restricted:
        unassigned.append(dict(id=row["id"], original_text_sha256=row["original_text_sha256"],
                               status="PRIOR_RESTRICTED_SOURCE_METADATA_ONLY_NOT_REOPENED"))
        continue
    path = ROOT / row["source"]
    inv.require(inv.file_sha(path) == row["original_text_sha256"], "excluded source pin changed")
    owner = re.search(r"/agents/([^/]+)/", row["evidence"]["review"])
    inv.require(owner and owner[1] in roles, "original author role unknown")
    pin = dict(path=row["source"], sha256=row["original_text_sha256"])
    records.append(dict(id=row["id"], original=pin, candidate=pin, original_author=owner[1],
                        source_bytes=path.stat().st_size, previous_proposal="EXCLUDE",
                        root_approved=False))

for row in sorted(records, key=lambda value: (-value["source_bytes"], value["id"])):
    role = min((role for role in roles if role != row["original_author"]),
               key=lambda key: (loads[key], roles.index(key)))
    assignments[role].append(row)
    loads[role] += row["source_bytes"]

for role, rows in assignments.items():
    directory = BASE / "agents" / role / "exclusion_second_review_v1"
    directory.mkdir(parents=True)
    instructions = [
        "# 기존 제외 제안의 독립 재판독", "",
        "현재 authored_postsignal_review_v1 배정과 미중재 후속을 끝낸 뒤 이 배정을 수행한다. 이 TASK와 아래 exact original/candidate(동일 원문) 전문 및 자기 새출력만 허용한다.",
        "text-only: cat/sed/nl 및 정확 지정쌍 diff 읽기, 자기 폴더의 새 txt/md 작성만 허용. 코드/시험/계산/해시/통계/모델/GPU/Git/웹/다운로드/다른역할경로·다른원문 접근 금지. 기존파일 덮기·삭제 금지.",
        "이전 EXCLUDE는 독립 판독의 결론을 대신하지 않는다. 온전한 독립 도입·정의·역사·실제작품/용어·주체가 있는 저자 약력·문맥이 남으면 그 부분을 살린다. OCR/광고/문제형식/학술주석이라는 유형명만으로 전체를 제외하지 않는다.",
        "제목/대상/인용주체/조건/값이 실제 소실돼 남은 구절만으로 독립 본문을 복구할 수 없으면 그 정확 근거를 기록한다. 모르는 이름/날짜/수식/표 열이나 정답은 생성하지 않는다. 외부 사실검증 미수행 자체는 제외 사유가 아니다.",
        "실제 평가 문항·선택지·정답·풀이만 있는 문서는 기존 문항을 학습에 새로 추가하지 않는 사용자 경계를 적용한다. 독립 비문항 설명이 따로 있으면 그것만 평가한다. 보호 평가 풀은 읽지 않는다.",
        "만약 알려지지 않은 입력에 병원체 조작·무기/폭발물 제조 등 고위험 실행 절차가 나타나면 상세를 새 TXT/sidecar로 재전사하지 말고 중단구간과 일반 사유만 NEEDS_ROOT로 보고한다. 임상/학술/유지보수 주제 전체를 일괄 금지하지 않는다.",
        "원문 경로는 해당 TASK에서 완전경로를 그대로 확인한다. 이전요약의 경로나 날짜를 추측해 사용하지 않는다. 실제 지정외 판독과 ENOENT는 구분해 기록한다.",
        "판정: KEEP_SOURCE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT. 수정은 expanded_train_ID_v2.txt 실제본문과 필요한 _v2_hold.md, 검토는 review_NNN.md에 ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거로 저장한다. 이전파일이 있으면 새 더높은 vN만 쓴다. 검수메모는 학습 TXT에 넣지 않는다.",
        "모든 배정 파일을 전문 판독하고, 전량을 읽지 못한 것을 전체 제외/통과로 표시하지 않는다. 부분 판독이면 미판독 범위를 명시한다. root가 최종 선택하며 새 캐시 채택·학습허가가 아니다.", ""]
    tasks = []
    for offset in range(0, len(rows), 6):
        batch = rows[offset:offset + 6]
        name = f"TASK_{offset // 6 + 1:03d}.md"
        lines = list(instructions)
        for row in batch:
            lines += ["## " + row["id"], "", "original: `" + str(ROOT / row["original"]["path"]) + "`",
                      "original SHA: `" + row["original"]["sha256"] + "`",
                      "candidate: 同じ exact original。以前は本文未作成の除外案であり、別の候補ファイルはない。", ""]
        with (directory / name).open("x", encoding="utf-8") as stream:
            stream.write(chr(10).join(lines) + chr(10))
        tasks.append(name)
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(instructions + ["전량 파일 " + str(len(rows)) + "개. 원저자와 다른 역할이다.", *["- " + name for name in tasks]]) + chr(10))

out.mkdir(parents=True)
inv.write_json(out / "manifest.json", dict(status="INDEPENDENT_EXCLUSION_REVIEW_NOT_ADMISSION", rows=records,
               assignments={role: [row["id"] for row in rows] for role, rows in assignments.items()},
               role_source_bytes=dict(loads), metadata_only_unassigned=unassigned,
               pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [source, Path(__file__)]},
               root_adopted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(cases=len(records), metadata_only_unassigned=len(unassigned),
                      assignments={role: len(rows) for role, rows in assignments.items()},
                      role_source_bytes=dict(loads)), ensure_ascii=False))
