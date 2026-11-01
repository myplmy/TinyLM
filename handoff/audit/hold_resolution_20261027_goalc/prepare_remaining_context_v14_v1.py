"""Assign previously unreviewed remaining source shapes to text-only authors.

Existing original packets and policy are reused. The generated candidate is
only a draft; every role must compare the complete pinned original and body.
"""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v15 as policy
from scripts import p106b_hold_resolution_revision_v14 as revision

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "remaining_context_v14_v1"
inv.require(not OUT.exists(), "immutable new context assignment required")
inputs = [BASE / "remaining_profile_v14_v1/review_packets/manifest.json",
          AUDIT / "authored_body_integrity_v2.json",
          AUDIT / "supplemental_candidates_snapshot_v11.json",
          BASE / "policy_v15_literal_counter_v1/manifest.json"]
profile, core, supplemental, recent = [inv.cache.read(path) for path in inputs]
covered = {row["id"] for row in core["records"] + supplemental["records"] + recent["rows"]}
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:1250821",
              "expanded_train:15695", "expanded_train:1216576"}
selected = [row for row in profile["rows"] if row["id"] not in covered]
inv.require(not (restricted & {row["id"] for row in selected}), "restricted source cannot enter general review")
OUT.mkdir()
(OUT / "candidates").mkdir()
started = time.monotonic()
rows, loads = [], Counter()
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
assignments = {role: [] for role in roles}
for source_row in sorted(selected, key=lambda row: -len(row.get("diagnostic_candidate", ""))):
    source = dict(path=source_row["path"], sha256=source_row["sha256"])
    path = ROOT / source["path"]
    inv.require(inv.file_sha(path) == source["sha256"], "original review packet changed")
    raw = path.read_bytes().decode("utf-8")
    value = policy.propose(dict(source_row, text=raw, complete_eos=True, valid_utf8=True))
    clean = value.get("candidate", value["text"])
    candidate_path = OUT / "candidates" / (source_row["id"].replace(":", "_") + ".txt")
    payload = clean.encode("utf-8")
    inv.require(payload.strip() and len(payload) < 20_000_000, "candidate must be nonempty and independently sharded")
    with candidate_path.open("xb") as stream:
        stream.write(payload)
    if source_row["language_bucket"] == "NO_HANGUL":
        eligible = ["context_latin", "historical_review", "legacy_review"]
    elif any("FORMAL" in reason or "DECLARATION" in reason or "CODE" in reason for reason in source_row["reasons"]):
        eligible = ["context_controls", "legacy_review"]
    else:
        eligible = ["context_controls", "context_hangul", "historical_review", "legacy_review"]
    role = min(eligible, key=lambda name: (loads[name], roles.index(name)))
    loads[role] += len(raw)
    row = dict(id=source_row["id"], original=source,
               candidate=dict(path=str(candidate_path.relative_to(ROOT)), sha256=inv.sha(clean)),
               prior_reasons=source_row["reasons"], decision=value["decision"], reasons=value["reasons"],
               profile_kinds=source_row["profile_kinds"], language_bucket=source_row["language_bucket"],
               original_characters=len(raw), changes=value["changes"], role=role, root_approved=False)
    rows.append(row)
    assignments[role].append(row["id"])

contract = """# 잔여 원문 유형의 전문 독립 판독과 실제 새 본문

앞선 지정 작업을 마친 뒤 이 TASK의 exact original/candidate만 읽는다. 허용은 이 TASK, 정확 지정쌍, 자기 새 TXT/MD뿐이다.
text-only: cat/sed/nl 및 exact pair diff -u 판독, 새 TXT/MD 저장만 허용한다. 코드·시험·계수·통계·해시·모델·GPU·Git·웹·설치·다른 원문 접근·기존 파일 덮기·삭제는 금지한다.
원문과 후보를 각각 처음부터 EOF까지 읽고 전체 diff를 대조한다. 큰 출력이 잘리면 작은 줄구간으로 이어 실제 읽은 범위를 기록하며 미판독을 전문 대조로 쓰지 않는다.
후보는 승인되지 않은 자동 초안이다. 정상 코드·규격 문법·Unicode·색/굵기 정보·역사 전사·채워진 표/목록/서지·서로 다른 문맥의 반복을 보존한다. 빈 수식·값·이름·날짜·조건을 추정해 채우지 않는다.
실제 결손과 그 값을 전제로 한 직접 의존 구간만 별도 hold에 남기고, 같은 문단의 독립된 완결 정의·경력·역사·정성 설명을 함께 지우지 않는다. 소속 표의 실제 행/수치가 없는 범례와 빈 표제는 본문에서 분리한다.
분류·연도·배우/선수/작품 목록을 짧거나 목록이라는 이유로 지우지 않는다. 귀속·관계가 원문에서 확인되면 원래 구조/순서로 보호한다. 출처·인용자·추측/부정/조건을 바꾸지 않으며 전량 외부 사실검증을 주장하지 않는다.
병원체 조작·제조·무기화의 실행 방법이 실제 등장하면 그 구간을 재전사/정리하지 말고 구간과 미판독을 root에 보고한다. 일반 과학·질환·정치·역사라는 주제만으로 보류/제외하지 않는다.
판정은 ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT다. 수정은 레시피 대신 실제 expanded_train_ID_v2.txt와 필요한 _v2_hold.md를 새로 저장한다. 메모는 MD에만 기록하고 TXT에 넣지 않는다.
새 review_NNN.md에 ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 표를 쓴다. 출력은 정확 파일명 하나를 적고 hold는 근거 칸에 쓴다. 이전 산출물은 보존한다. 이것은 root 최종 선택·캐시 검증·학습 승인이 아니다.
"""
for role in roles:
    directory = BASE / "agents" / role / OUT.name
    inv.require(not directory.exists(), "role output namespace must be new")
    directory.mkdir()
    owned = [row for row in rows if row["role"] == role]
    for offset in range(0, len(owned), 4):
        section = [contract]
        for row in owned[offset:offset + 4]:
            section.append("## " + row["id"])
            section.append("original: `" + str(ROOT / row["original"]["path"]) + "`")
            section.append("original SHA: `" + row["original"]["sha256"] + "`")
            section.append("candidate: `" + str(ROOT / row["candidate"]["path"]) + "`")
            section.append("candidate SHA: `" + row["candidate"]["sha256"] + "`")
            section.append("미확정 사유: " + ", ".join(row["reasons"]))
        with (directory / ("TASK_" + str(offset // 4 + 1).zfill(3) + ".md")).open("x", encoding="utf-8") as stream:
            stream.write((chr(10) * 2).join(section) + chr(10))

pins = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in inputs}
code = revision.CODE + ["scripts/p106b_hold_resolution_policy_v15.py", str(Path(__file__).relative_to(ROOT))]
result = dict(status="NEW_REMAINING_SOURCE_CONTEXT_NOT_ADMISSION", rows=rows, assignments=assignments,
              source_characters_by_role=dict(loads), excluded_previously_assigned_ids=sorted(covered),
              input_pins=pins, code_pins={name: inv.file_sha(ROOT / name) for name in code},
              root_adopted=0, seconds=time.monotonic() - started, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(rows=len(rows), assignments={key: len(value) for key, value in assignments.items()},
                      source_characters_by_role=dict(loads), seconds=result["seconds"]), ensure_ascii=False))
