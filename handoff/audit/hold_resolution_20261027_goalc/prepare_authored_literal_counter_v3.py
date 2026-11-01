"""Pin flagged actual body alternatives for independent text-only decisions."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "authored_literal_counter_v3"
inv.require(not OUT.exists(), "new exact body counter namespace required")
input_path = AUDIT / "reviewed_body_literals_v1.json"
audit = inv.cache.read(input_path)
by_id, flagged = defaultdict(list), defaultdict(set)
for row in audit["records"]:
    by_id[row["id"]].append(row)
    if row["exact_root_selected"] or row["status"] != "ACTUAL_BODY_LITERAL_READBACK_NOT_SEMANTIC_APPROVAL":
        continue
    if not (row["unicode_guard"] and (row["code_guard"] or row["exact_reviewed_literal_exception"])):
        flagged[row["id"]].add("CODE_OR_UNICODE_SIGNAL")
    if not row["semantic_style_guard"]:
        flagged[row["id"]].add("STYLE_VALUE_SIGNAL")
    if row["introduced_numeric_occurrences"]:
        flagged[row["id"]].add("INTRODUCED_NUMERIC_OCCURRENCE_SIGNAL")
    flagged[row["id"]].update(row["literal_hole_signals"])
flagged = {ident: values for ident, values in flagged.items() if values}
flagged.setdefault("expanded_train:842876", set()).add("SOURCE_TITLE_SLOT_AND_ORPHAN_FOOTER")
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:1216576",
              "expanded_train:1250821", "expanded_train:15695", "expanded_train:20624"}
inv.require(not (set(flagged) & restricted), "limited parent cannot enter general full-source counter")
notes = {
    "expanded_train:36329": "root는 새 후보에 2016년 부활 영화 항목이 원문1회에서2회로 복사된 실제 중복을 확인했다. 원래 채워진 항목은1회 보존하고 빈 선택 병기만 정리하며, 제목이 실제 소실된 다른 작품명은 만들지 않는다.",
    "expanded_train:1292041": "root가 원문 전문을 읽었다. JDBC/Class.forName/static-block 기술 문장과 원래 질문의 문맥을 보존한다. 이름/자격증/장식 물결줄·관련없는 격언은 포럼 서명 footer인지 문맥 판독하고, 본문과 분리하면 원문 그대로 MD에 보존한다. 장식 줄을 코드펜스로 오인해 새 코드나 fence를 만들지 않는다. 실제 코드/함수명은 보호한다.",
    "expanded_train:6773": "root는 Earth'nut`의 사전 전사 기호와 실제 식물 정의를 보호해야 함을 확인했다. Search backtick 같은 웹 UI와 사전 발음/전사 기호를 구분한다. 완결된 식물명·정의·12cm 값은 보존하고 실제 끊긴 문장만 분리한다. Found op URL을 다른 정의의 출처로 새로 재배치하지 않으며 원래 연속 구간/순서를 보존하고 귀속이 불확실하면 MD에 표시한다. 임의 외부 사실조회는 하지 않는다.",
    "expanded_train:842876": "root가 원문/새본문 전문을 읽었다. 본문의 빈 《》와 빈 각주는 그대로 두지 않는다. 마지막 문장에서 현가 변경 무산과 앙케이트 선정 결과로 뽑힌 곡이 현민 애창곡으로 지정됐다는 관계는 명시되어 있다. 노래 이름을 새로 만들지 않고 원문의 채워진 명사 곡과 앙케이트 선정 관계로 문장을 보존할 수 있다. 소실된 곡 제목은 MD에 보류하고, 실제 출처/문화·1972 분류는 보존하며 비어 있는 각주 표제만 분리한다.",
}
OUT.mkdir()
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
loads, assignments, rows = Counter(), {role: [] for role in roles}, []
for ident in sorted(flagged, key=lambda key: -by_id[key][0]["source_characters"]):
    options = by_id[ident]
    primary = next((row for row in options if not row["exact_root_selected"] and (
        not (row["unicode_guard"] and (row["code_guard"] or row["exact_reviewed_literal_exception"]))
        or not row["semantic_style_guard"] or row["introduced_numeric_occurrences"] or row["literal_hole_signals"])), options[0])
    prior_authors = set()
    for row in options:
        review = row.get("review")
        if isinstance(review, dict):
            match = re.search(r"/agents/([^/]+)/", review.get("path", ""))
            if match:
                prior_authors.add(match[1])
    eligible = [role for role in roles if role not in prior_authors] or roles
    role = min(eligible, key=lambda value: (loads[value], roles.index(value)))
    loads[role] += primary["source_characters"]
    original = primary["compare_source"]
    inv.require(inv.file_sha(ROOT / original["path"]) == original["sha256"], "counter original pin changed")
    alternatives = [dict(path=row["body"], sha256=row["clean_text_sha256"], cohort=row["cohort"]) for row in options]
    for pin in alternatives:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "counter body pin changed")
    row = dict(id=ident, role=role, original=original,
               candidate=dict(path=primary["body"], sha256=primary["clean_text_sha256"]),
               other_candidates=alternatives, diagnostic_signals=sorted(flagged[ident]),
               root_context=notes.get(ident, ""), source_characters=primary["source_characters"], root_approved=False)
    rows.append(row)
    assignments[role].append(ident)

for role in roles:
    directory = BASE / "agents" / role / OUT.name
    inv.require(not directory.exists(), "new assigned output directory required")
    directory.mkdir()
    owned = [row for row in rows if row["role"] == role]
    start = f'''# 현재 작업 단계 — {role}

현재 새 작업은 authored_literal_counter_v3의 아래 지정 TASK뿐이다.
이전 authored_postsignal435 / exclusion59 / remaining_context70 / automatic_partial194의 자기 배정은 완료되어 새 읽기·재작성 권한을 닫았다. 옛 TASK로 되돌아가지 않는다. 임상/생태/효모 parent 및 미판독 제외 범위도 다시 열지 않는다.
이 START_HERE와 지정 TASK 및 그 안의 exact 원문/후보/대안만 읽는다. 코드·시험·계수·통계·해시·GPU·모델·Git·웹·설치·기존 파일 덮기·삭제는 금지한다. cat/sed/nl 및 exact pair diff -u 판독과 자기 새 TXT/MD만 허용한다.
정확 출력 폴더: `{directory}`. 상위 BASE나 다른 역할 폴더에 저장하지 않는다.
이전 파일이 있으면 더 높은 새 vN을 사용한다. 완료한 TASK는 다시 읽지 말고 다음 미완 TASK로 이동한다. 이 새 묶음을 마치면 최종 파일명/미판독을 보고하고 root의 새 지정까지 추가 파일 작업 없이 final로 끝낸다. 공유 goal 전체를 이 역할이 독자 수행하지 않는다.
'''
    task_names = []
    for offset in range(0, len(owned), 4):
        name = "TASK_" + str(offset // 4 + 1).zfill(3) + ".md"
        task_names.append(name)
        parts = [start, "# 실제 본문 기호·수치·스타일의 독립 대조",
                 "원문과 primary 후보 및 각 대안을 각각 처음부터 EOF까지 읽고 전체 diff를 대조한다. 큰 출력은 작은 줄범위로 나눠 잘린 부분을 실제 판독한다. 신호는 오류 확정이 아니다.",
                 "고립 ]를 일괄 지우지 않는다. 원문이 균형 잡혔는데 후보가 망가뜨렸으면 원문을 복구한다. 역사 전사/인용/발음/수학 기호가 합법적이면 보존하며 실제 추출 잔재임이 확인될 때만 좁게 정리한다.",
                 "색·굵기·스타일이 실제 값/범례의 의미이면 보존한다. 빈 표·그림·CSS와 소속을 잃은 범례/장식만 원문 근거로 MD에 분리한다. HTML 전체를 지우거나 전부 복구하는 방식은 쓰지 않는다.",
                 "원문에 없는 숫자/이름/식/조건/인용자를 만들지 않는다. 학술 용어·서지·부정·조건과 완결 독립 설명은 보존한다. 검수 메모는 TXT가 아닌 MD에만 쓴다.",
                 "새 review_NNN.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. ACCEPT_CANDIDATE는 아래 primary 후보만 뜻한다. 다른 대안을 택하면 실제 새 expanded_train_ID_v2.txt로 저장하고 REVISE_TEXT로 기록한다. KEEP_SOURCE/EXCLUDE/NEEDS_ROOT도 가능하며 실제 결손은 별도 _v2_hold.md에 보존한다.",
                 "코드/Unicode/스타일 신호가 남아도 검사 면제나 정책 변경을 하지 않는다. 구체적 실제 문맥 근거와 정확 본문을 root가 최종 판단한다. 이것은 캐시 채택·학습 승인이 아니다."]
        for row in owned[offset:offset + 4]:
            parts += ["## " + row["id"], "original: `" + str(ROOT / row["original"]["path"]) + "`",
                      "original SHA: `" + row["original"]["sha256"] + "`",
                      "primary candidate: `" + str(ROOT / row["candidate"]["path"]) + "`",
                      "candidate SHA: `" + row["candidate"]["sha256"] + "`",
                      "진단 신호: " + ", ".join(row["diagnostic_signals"]), row["root_context"]]
            for pin in row["other_candidates"]:
                if pin["path"] != row["candidate"]["path"]:
                    parts += ["추가 exact 대안: `" + str(ROOT / pin["path"]) + "` SHA `" + pin["sha256"] + "`"]
        with (directory / name).open("x", encoding="utf-8") as stream:
            stream.write((chr(10) * 2).join(parts) + chr(10))
    with (directory / "START_HERE.md").open("x", encoding="utf-8") as stream:
        stream.write(start + chr(10) + "현재 TASK: " + ", ".join(task_names) + chr(10))
inv.write_json(OUT / "manifest.json", dict(status="ACTUAL_BODY_LITERAL_COUNTER_NOT_ADMISSION", rows=rows,
    assignments=assignments, source_characters_by_role=dict(loads),
    pins={str(input_path.relative_to(ROOT)):inv.file_sha(input_path), str(Path(__file__).relative_to(ROOT)):inv.file_sha(Path(__file__))},
    root_adopted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(cases=len(rows), assignments={role:len(ids) for role,ids in assignments.items()},
    source_characters_by_role=dict(loads)), ensure_ascii=False))
