"""Materialize every whole-census structure match as an exact source pair."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_policy_v25 as old_policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
PROFILE = BASE / "ordinal_metadata_candidate_census_v26_v1"
OUT = BASE / "ordinal_metadata_counter_v26_v1"
inv.require(not OUT.exists(), "new assignment namespace required")
profile_path = PROFILE / "complete.json"
profile = inv.cache.read(profile_path)
inv.verify(PROFILE / "matches", profile["matches_manifest"])
selected = list(inv.cache.rows(PROFILE / "matches", profile["matches_manifest"]))
inv.require(len(selected) == 27 and len({r["original_text_sha256"] for r in selected}) == 27, "whole-census matches differ")
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695",
              "expanded_train:1216576", "expanded_train:1250821", "expanded_train:20624", "expanded_train:6030"}
inv.require(not {r["id"] for r in selected} & restricted, "restricted parent cannot enter these pairs")
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "structure_counter"]
pins = dict(profile["production_source_pins"])
for name, digest in pins.items():
    inv.require(inv.file_sha(ROOT / name) == digest, "whole-census ordinal proof code changed")
loads, counts = Counter(), Counter()
assignments, rows = {role: [] for role in roles}, []
directory = OUT / "inputs"
directory.mkdir(parents=True)
started = time.monotonic()
with ExitStack() as stack:
    reader = inv.OriginalReader(inv.cache.read(BASE / "scope.json"), stack)
    for source in selected:
        raw, complete, valid = reader.text(source)
        inv.require(complete and valid and inv.sha(raw) == source["original_text_sha256"], "exact original source differs")
        input_row = dict(source, text=raw, complete_eos=complete, valid_utf8=valid)
        before = old_policy.propose(input_row)
        inv.require(before["decision"] == "PENDING"
                    and inv.sha(before.get("candidate", before["text"])) == source["diagnostic_sha256"],
                    "fresh exact original does not reproduce its v25 diagnostic")
        value = policy.propose(input_row)
        clean = value.get("candidate", value["text"])
        role = min(roles, key=lambda name: (loads[name], roles.index(name)))
        loads[role] += len(raw)
        assignments[role].append(source["id"])
        pair = {}
        for kind, text in [("original", raw), ("candidate", clean)]:
            payload = text.encode("utf-8")
            inv.require(0 < len(payload) < 20_000_000, "ordered splitting required")
            path = directory / (source["id"].replace(":", "_") + "_" + kind + ".txt")
            with path.open("xb") as stream:
                stream.write(payload)
            pair[kind] = dict(path=str(path.relative_to(ROOT)), sha256=inv.sha(text))
        rows.append(dict(source, **pair, role=role, raw_original_not_redecoded=False,
                         fresh_exact_original_readback=True,
                         original_native_v25_proposal_reproduced=True,
                         original_source_code_guard=policy.code_preserved(raw, clean),
                         original_source_unicode_guard=policy.unicode_examples_preserved(raw, clean),
                         original_source_style_guard=policy.semantic_style_preserved(raw, clean),
                         ordered_deletion=policy.ordered_deletion(raw, clean),
                         candidate_decision=value["decision"],
                         candidate_reasons=value["reasons"], root_approved=False))
        counts[value["decision"]] += 1
for role in roles:
    destination = BASE / "agents" / role / OUT.name
    destination.mkdir(parents=True, exist_ok=False)
    owned = [r for r in rows if r["role"] == role]
    instructions = ["# " + role + " / " + OUT.name, "",
        "역할은 지정 원문/후보 판독과 새 txt/md 정제·hold/제외 근거뿐이다.",
        "허용 읽기는 이 START/TASK/READING_VIEWS, 지정 원문/후보와 순서 뷰, 자신이 새로 저장한 txt/md다.",
        "허용 쓰기는 이 지정 폴더 안 새 txt/md뿐이다. 기존 파일은 자기 파일도 덮기·삭제·이동·개명하지 않는다.",
        "코드·시험·모델·GPU·Git·규약·공유원장·타역할/세션·보호데이터·웹·설치·다운로드·다른 경로 쓰기는 금지한다.",
        "위키 빈 칸은 명시된 표 축에 따른 공란인지 실제 식·변수·값의 탈락인지 문맥으로 구분한다.",
        "명명 정의 뒤 빈 괄호만 정리할 수 있는 경우에도 뒤의 수식 결손을 통과시키지 않는다.",
        "수식/값을 추정 생성하지 않고 결손 직접 의존부만 exact hold로 분리한다. 독립 유효 내용·참고·분류·강조·코드·조건·숫자는 보존한다.",
        "각 원문/후보의 모든 뷰를 순서대로 EOF/전체 diff까지 실제 판독한다. 읽기뷰 일부를 완성 TXT로 복사하지 않는다.",
        "한 TASK를 마칠 때 즉시 표형 review_NNN.md를 배타적으로 저장한다.",
        "표 열: ID / 판정 / 실제 판독 범위 / 출력 / 구체 근거. 실제 Markdown 표를 쓰고 셀 안의 파이프는 이스케이프한다.",
        "판정은 ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT다. 출력 열에는 최종 본문 TXT 한 개만 지목한다.",
        "후보가 옳으면 candidate 경로 그대로 ACCEPT할 수 있다. 변경 시 전체 본문을 편집 기반으로 새 TXT와 hold를 저장하고 새 EOF/전체 diff를 확인한다.",
        "실제 불법 제조 세부가 나타나면 복제하지 말고 ID/이유만 root에 보고한다. 일반 학술 내용은 이 범주로 자동 제외하지 않는다.",
        "이 27쌍은 전체 v25 미결의 서수 분류 경계 후보 전수계수 결과 전부다. 코퍼스 전체 의미검증·사실검증·캐시 채택 완료가 아니다."]
    instructions += [
        "현재 root_selected_lexical_counter_v1의 기존32TASK 전부를 먼저 마친 뒤 이 묶음을 시작한다.",
        "이 새 묶음은 분류명 내부의 서수 마침표를 지우지 않는 경계 증명이다. 원문 값/분류 순서/참고자료를 보존한다.",
        "일반 마침표를 전부 허용하거나, 처음6000문자만 읽고 완료라 쓰거나, 공통 수식 결손을 무시하면 안 된다.",
        "코드/통계/모델/GPU/Git/웹은 금지한다. 새 TXT/MD 편집용 좁은 파일 API와 nl/sed/diff/tail 읽기 보조만 허용한다.",
        "raw EOF에서 마지막 개행이 없을 수 있으므로 wc-l을 마지막 논리줄로 오인하지 않는다. 마지막 실제 행과 전체 diff를 확인한다."]
    for number, row in enumerate(owned, 1):
        lines = ["# TASK_" + str(number).zfill(3), row["id"],
            "START_HERE와 READING_VIEWS를 따른다.",
            "original: " + str(ROOT / row["original"]["path"]), "original SHA256: " + row["original"]["sha256"],
            "candidate: " + str(ROOT / row["candidate"]["path"]), "candidate SHA256: " + row["candidate"]["sha256"],
            "후보 판정: " + row["candidate_decision"], "사유: " + ", ".join(row["candidate_reasons"]),
            "전량 계수된 실제 서수 분류값: " + ", ".join(row["proof"]["dotted_category_values"])]
        with (destination / ("TASK_" + str(number).zfill(3) + ".md")).open("x", encoding="utf-8") as stream:
            stream.write(chr(10).join(lines) + chr(10))
    with (destination / "START_HERE.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(instructions) + chr(10))
inv.require(pins == {name: inv.file_sha(ROOT / name) for name in pins}, "production code changed")
manifest = dict(status="ALL_27_ORDINAL_CENSUS_MATCHES_HAVE_EXACT_SOURCE_PAIRS_NOT_ADMISSION",
    rows=rows, assignments=assignments, source_characters_by_role=dict(loads), candidate_counts=dict(counts),
    input_pins={str(profile_path.relative_to(ROOT)): inv.file_sha(profile_path),
        str((BASE / "scope.json").relative_to(ROOT)): inv.file_sha(BASE / "scope.json"),
        str(Path(__file__).relative_to(ROOT)): inv.file_sha(Path(__file__))},
    source_code_pins=pins, seconds=time.monotonic() - started,
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", manifest)
views = (AUDIT / "prepare_selected_literal_views_v3.py").read_text(encoding="utf-8")
views = views.replace("root_selected_literal_counter_v3", OUT.name)
with (AUDIT / "prepare_v26_ordinal_views_v1.py").open("x", encoding="utf-8") as stream:
    stream.write(views)
print(json.dumps(dict(rows=len(rows), assignments={r: len(ids) for r, ids in assignments.items()},
    source_characters_by_role=dict(loads), candidate_counts=dict(counts), seconds=manifest["seconds"])))
