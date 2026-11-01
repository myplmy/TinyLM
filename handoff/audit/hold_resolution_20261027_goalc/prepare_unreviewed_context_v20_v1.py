"""Make every new census representative an exact source/candidate assignment."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "remaining_unreviewed_context_v20_v1"
inv.require(not OUT.exists(), "new source assignment namespace required")
profile_path = BASE / "remaining_unreviewed_candidate_profile_v20_v1/review_packets/manifest.json"
report_path = BASE / "remaining_unreviewed_candidate_profile_v20_v1/complete.json"
known_paths = [AUDIT / "reviewed_selection_plan_v9.json", BASE / "root_selected_signal_counter_v2/manifest.json",
               BASE / "policy_v21_literal_counter_v1/manifest.json"]
inputs = [profile_path, report_path, *known_paths, BASE / "scope.json", Path(__file__)]
profile = inv.cache.read(profile_path)
known = set()
for path in known_paths:
    value = inv.cache.read(path)
    known.update(row["id"] for row in value.get("records", value.get("rows", [])))
selected = profile["rows"]
inv.require(len(selected) == 233 and not ({row["id"] for row in selected} & known), "new census is not disjoint from prior assignments")
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695", "expanded_train:1216576",
              "expanded_train:1250821", "expanded_train:20624", "expanded_train:6030"}
inv.require(not ({row["id"] for row in selected} & restricted), "restricted parent cannot enter general text packets")
pins = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in inputs}
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "structure_counter"]
assignments, loads, rows = {role: [] for role in roles}, Counter(), []
directory = OUT / "originals"
directory.mkdir(parents=True)
started = time.monotonic()
with ExitStack() as stack:
    reader = inv.OriginalReader(inv.cache.read(BASE / "scope.json"), stack)
    for source in selected:
        inv.require(inv.file_sha(ROOT / source["candidate"]["path"]) == source["candidate"]["sha256"], "candidate pin differs")
        raw, complete, valid = reader.text(source)
        inv.require(complete and valid and inv.sha(raw) == source["original_text_sha256"], "source is not a complete exact original")
        payload = raw.encode("utf-8")
        inv.require(0 < len(payload) < 20_000_000, "source requires ordered splitting")
        path = directory / (source["id"].replace(":", "_") + "_original.txt")
        with path.open("xb") as out:
            out.write(payload)
        if source["language_bucket"] == "NO_HANGUL":
            eligible = ["context_latin", "historical_review", "structure_counter"]
        elif any(any(term in reason for term in ["FORMAL", "CODE", "DECLARATION"]) for reason in source["reasons"]):
            eligible = ["context_controls", "structure_counter"]
        else:
            eligible = roles
        role = min(eligible, key=lambda value: (loads[value], roles.index(value)))
        loads[role] += len(raw)
        assignments[role].append(source["id"])
        rows.append(dict(source, role=role, original=dict(path=str(path.relative_to(ROOT)), sha256=inv.sha(raw)),
                         original_characters=len(raw), source_identity_decode_verified=True, root_approved=False))

for role in roles:
    destination = BASE / "agents" / role / OUT.name
    destination.mkdir(parents=True, exist_ok=False)
    owned = [row for row in rows if row["role"] == role]
    instructions = ["# " + OUT.name + " / " + role, "",
        "총괄의 시작 메시지를 받은 뒤 이 폴더의 전체 TASK를 판독한다. 기존 root_selected_signal_counter_v2 미완 TASK가 있으면 그것을 먼저 전량 마친다.",
        "허용 읽기: 이 START/TASK/READING_VIEWS와 각 TASK가 정확히 지정한 원문/후보, 자신이 새로 저장한 txt/md.",
        "허용 쓰기: `" + str(destination) + "` 안의 새 txt/md만. 기존 자기 파일도 덮기·삭제·이동·개명하지 않는다.",
        "금지: 코드/시험/규약/모델/GPU/Git/설치/다운로드/웹, 다른 역할·세션·보호데이터 읽기, /tmp 포함 다른 경로 쓰기.",
        "보고·검토 사유는 한국어로 쓴다. 실제 원문의 언어·명칭·코드·수식·인용문은 번역하거나 바꾸지 않는다.",
        "원문/후보의 모든 읽기뷰를 순서대로 연결해 EOF/전체 diff까지 실제 읽는다. 잘린 출력을 완료로 세지 않는다. 읽기뷰는 편집 기반이나 새 학습 문서가 아니다.",
        "수정할 때 전체 candidate 또는 정확 original 전체를 편집 기반으로 사용하고 새 TXT도 전량 EOF/전체 차이를 확인한다.",
        "유효한 이름/숫자/단위/부정/조건/인용 주체/불확실성/채워진 표/실제 코드·강조/참고/분류를 보호한다. 빈 표제·UI·빈 선택병기·근거 없는 수식/관계 조각은 분리한다.",
        "편집 설명·검수 메모·미상 표시·행수·버전·보존했습니다 등은 본문에 넣지 않고 hold/review MD에 둔다. 새 사실/변수/기호/동의어/날짜를 만들지 않는다.",
        "출생연도만 충돌하면 충돌 없는 월일·사람·장소·가족까지 함께 버리지 않는다. 서로 귀속된 복수설은 불확실성과 귀속을 보존하며 어느 설도 선택하지 않는다.",
        "각 TASK를 마치면 즉시 canonical 표형 review_NNN.md를 저장한다. ID는 해당 TASK 목록과 정확히 같아야 하며 과거 다른 TASK ID를 복사해 완료로 세지 않는다.",
        "표 열: | ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |. 판정: ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT.",
        "출력 열에는 최종 본문 TXT 한 개만 지목한다. 실패/중간본은 사유/hold에 기록하고 그대로 보존한다. ACCEPT는 지정 candidate 자체를 정확히 명시할 수 있다.",
        "정정 시 review_NNN_v2.md 등 새 버전을 만든다. 원문 결손·직접 의존 조각과 정확 사유는 ID_vN_hold.md에 원형으로 둔다.",
        "실제 불법 제조 세부가 나타나면 기술 내용은 복제하지 않고 ID/이유만 root에 보고한다. 일반 역사·과학을 이 범주로 자동 제외하지 않는다.",
        "총괄이 중재할 좁은 질문은 정확 원문/후보/전후 문맥과 함께 보내고 다른 독립 TASK를 계속한다. 실제 캐시 채택·전량 사실검증·모델 개선은 주장하지 않는다.",
        "이 묶음은 전량 미결 계수에서 이전 배정 ID를 제외한 모든 새 유형 대표233쌍이다. 작업량 상한이나 코퍼스 전체 의미검증의 대체물이 아니다."]
    names = []
    for offset in range(0, len(owned), 4):
        name = "TASK_" + str(offset // 4 + 1).zfill(3) + ".md"
        names.append(name)
        text = ["# " + name, "지정 폴더 START_HERE.md와 READING_VIEWS.md의 권한·전체 판독 규칙을 따른다.",
                "후보는 v20 diagnostic candidate이며 원문과 다를 수 있다. 오삭제된 독립 내용도 원문에서 복구한다."]
        for row in owned[offset:offset + 4]:
            text += ["## " + row["id"], "original: `" + str(ROOT / row["original"]["path"]) + "`",
                     "original SHA256: " + row["original"]["sha256"], "candidate: `" + str(ROOT / row["candidate"]["path"]) + "`",
                     "candidate SHA256: " + row["candidate"]["sha256"], "사유: " + ", ".join(row["reasons"]),
                     "유형: " + ", ".join(row["profile_kinds"])]
        with (destination / name).open("x", encoding="utf-8") as out:
            out.write((chr(10) * 2).join(text) + chr(10))
    with (destination / "START_HERE.md").open("x", encoding="utf-8") as out:
        out.write(chr(10).join(instructions + ["", "전체 TASK: " + ", ".join(names)]) + chr(10))
for name, key in pins.items():
    inv.require(inv.file_sha(ROOT / name) == key, "assignment input changed")
result = dict(status="ALL_UNASSIGNED_STRATA_REPRESENTATIVES_HAVE_EXACT_SOURCE_PAIRS_NOT_ADMISSION", rows=rows,
              assignments=assignments, source_characters_by_role=dict(loads), input_pins=pins,
              reused_previously_assigned_ids=[], seconds=time.monotonic() - started,
              cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(rows=len(rows), assignments={role: len(ids) for role, ids in assignments.items()},
                      source_characters_by_role=dict(loads), seconds=result["seconds"]), ensure_ascii=False))
