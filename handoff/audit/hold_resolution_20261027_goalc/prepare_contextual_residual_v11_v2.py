"""Assign every new pending purpose packet, without reopening reviewed sources.

Five existing text-only roles receive exact original/candidate pins. This is
neither a prevalence estimate nor an admission, and no original is modified.
"""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
GROUP = "contextual_residual_v11_v1"
destination = BASE / GROUP
inv.require(not (destination / "manifest.json").exists(), "new immutable assignment manifest required")
destination.mkdir(exist_ok=True)
prior = AUDIT / "authored_body_integrity_v1.json"
known = {row["id"] for row in inv.cache.read(prior)["records"]}
input_paths = [prior]
for group in ["policy_counter_review_v1", "remaining_structure_context_v1",
              "policy_v10_literal_counter_v1", "policy_v11_literal_counter_v1"]:
    path = BASE / group / "manifest.json"
    known.update(row["id"] for row in inv.cache.read(path)["rows"])
    input_paths.append(path)
known.add("expanded_train:1250821")
source = BASE / "draft_proposals_v11/review_packets/manifest.json"
input_paths.append(source)
rows = [row for row in inv.cache.read(source)["rows"]
        if row["decision"] == "PENDING" and row["id"] not in known]
inv.require(len(rows) == len({row["original_text_sha256"] for row in rows}), "repeated assignment source")
inv.require(all(not any("PRIOR_INDIVIDUAL" in reason for reason in row["reasons"]) for row in rows),
            "prior individual judgments must remain source-specific")
inv.require(all(row["id"] not in {"expanded_train:756966", "expanded_train:14760"} for row in rows),
            "restricted source must not be reopened")
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
assigned, loads = {role: [] for role in roles}, Counter()
for row in sorted(rows, key=lambda item: -(ROOT / item["paths"]["original"]["path"]).stat().st_size):
    for pin in row["paths"].values():
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "purpose packet changed")
    role = min(roles, key=lambda name: (loads[name], roles.index(name)))
    assigned[role].append(row)
    loads[role] += (ROOT / row["paths"]["original"]["path"]).stat().st_size

instructions = """# v11에서 새로 관측한 잔여 문맥 전체 판독

현재 승인: 이 TASK와 자기 TASK_NNN.md에 지정한 original/candidate 전문만 읽고 자기 새 txt/md만 작성한다. 다른 역할/실험/보호자료/작업규약/코드 접근, 원문·기존 결과물 덮기와 삭제는 금지한다.
금지: 코드 작성·실행·시험·통계·해시·모델·GPU·Git·웹. 정확한 지정쌍 diff -u 읽기는 허용한다. diff 종료1은 내용 차이이며 판독 오류가 아니다.

PENDING은 불량 확정이 아니다. 독립 문단과 실제 관계를 처음부터 끝까지 읽어 판단한다. 전체 출력이 잘리면 짧은 구간으로 이어 읽고 실제 EOF를 확인한다. 읽지 않은 구간을 전문 판독이라고 기록하거나, 판독 미완만으로 전체 EXCLUDE하지 않는다.
정상 표제·참고문헌·외부 링크·가족/선수/작품/차례 목록·조건·부정·수량/날짜/단위/귀속·학술용어·프로그램/Unicode 예제·문맥상 반복을 보존한다. 같은 줄 반복만으로 지우지 않는다. 원문에 없는 이름·논리·관계·정답·수식·사실·값을 만들지 않는다.
빈 괄호/제목/통계와 끊긴 수식은 실제로 비어 있는 국소 부분과 직접 의존 부분만 hold로 분리하고, 독립적으로 남는 본문은 과잉 삭제하지 않는다. 뒤 문장에서 대상을 밝히는 정상 대명사를 지우지 않는다. 서로 다른 인물/장/행의 날짜를 충돌로 단정하지 않는다.
일반 의료·생물학·역사·종교·정치 문서와 상품/책의 실제 제목·저자·내용/서지 정보는 주제나 광고 페이지라는 이유만으로 제외하지 않는다. 실제 고위험 생물 조작 절차라면 세부를 재전사하지 말고 NEEDS_ROOT로 경계만 보고한다. 기존 평가문항/정답을 새 본문에 추가하거나 대신 풀지 않는다.

판정은 KEEP_SOURCE / ADOPT_CANDIDATE / EDIT_TEXT / EDIT_RECIPE / EXCLUDE / NEEDS_ROOT이다. KEEP/ADOPT는 선택한 본문이 문맥상 온전할 때만 쓴다. 수정은 실제 새 txt 또는 아래 strict literal edits.md를 작성한다. 검수 메모는 md에만 둔다. 원문 보관은 기존 입력을 참조하면 되며 원문 전체를 메모에 중복할 필요 없다.
각 TASK_NNN의 결과는 새 review_NNN.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. 출력에는 정확 txt/edits.md 버전을 하나만 명시한다. 이미 있는 review나 본문은 덮지 말고 더 높은 vN 파일에 새로 작성한다. 모호한 인접 파일 버전 중 하나를 추측하지 않는다.

짧은 수정에만 사용할 수 있는 strict recipe 형식:

# P106B_LITERAL_TEXT_EDITS_V1
source_id: TASK의 정확한 source:ID
base: original 또는 candidate
base_sha256: 해당 TASK의 정확 SHA
reason: 실제 수정 이유

## Change 1
ORIGINAL
````````text
기존 본문에 정확히 한 번 있는 실제 문자열
````````
REPLACEMENT
````````text
실제 대체 문자열. 삭제는 내용 없는 블록을 쓴다.
````````

ORIGINAL은 선언한 base의 실제 문자열이어야 하고 Change끼리 겹치면 안 된다. 행 앵커가 반복되면 원문 문맥을 포함해 하나로 특정한다. 실제 프로그램/인용의 backtick이나 공백을 추측해 바꾸지 않는다. 삭제 예시 설명을 본문이나 빈 replacement에 넣지 않는다.

전 배정의 실제 판독·필요 본문·저장된 판정까지 수행한다. 이 판독은 root 최종 채택, 외부 사실 검증이나 코드 실행 성공이 아니다.
"""
assignments = {}
for role in roles:
    directory = BASE / "agents" / role / GROUP
    directory.mkdir(parents=True, exist_ok=True)
    ordered = sorted(assigned[role], key=lambda row: row["id"])
    tasks = []
    for start in range(0, len(ordered), 9):
        number = start // 9 + 1
        task = directory / ("TASK_%03d.md" % number)
        lines = ["# 새 잔여 원문 판독 묶음 %d" % number, "", "상위 TASK.md의 권한과 형식을 따른다.", ""]
        for row in ordered[start:start + 9]:
            lines += ["## " + row["id"], "", "검출 사유(불량 확정 아님): " + ", ".join(row["reasons"]), ""]
            for label, pin in row["paths"].items():
                lines += [label + ": `" + str(ROOT / pin["path"]) + "`",
                          label + " base_sha256: `" + pin["sha256"] + "`", ""]
        payload = chr(10).join(lines).encode("utf-8")
        if task.exists():
            inv.require(task.read_bytes() == payload, "preserved assignment task differs")
        else:
            with task.open("xb") as stream:
                stream.write(payload)
        tasks.append(str(task.relative_to(ROOT)))
    task_text = instructions + chr(10) + "배정 파일: " + ", ".join(Path(path).name for path in tasks) + chr(10)
    main_task = directory / "TASK.md"
    if main_task.exists():
        inv.require(main_task.read_bytes() == task_text.encode("utf-8"), "preserved main task differs")
    else:
        with main_task.open("x", encoding="utf-8") as stream:
            stream.write(task_text)
    assignments[role] = dict(ids=[row["id"] for row in ordered], tasks=tasks, original_bytes=loads[role])

inv.write_json(destination / "manifest.json", dict(status="SOURCE_PINNED_TEXT_ONLY_ASSIGNMENT_NOT_ADMISSION",
               rows=rows, assignments=assignments, prior_excluded_from_reassignment=len(known),
               pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in input_paths + [Path(__file__)]},
               root_adopted=0, training_authorized=False))
print(json.dumps(dict(rows=len(rows), assignments={role: dict(count=len(value["ids"]), bytes=value["original_bytes"])
                                                 for role, value in assignments.items()}), ensure_ascii=False))

