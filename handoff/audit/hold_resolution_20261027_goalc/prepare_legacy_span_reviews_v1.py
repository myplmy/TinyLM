"""Materialize every additional inherited source for exact text-only review.

The source is not adopted. Frozen v4 candidates help readers avoid copying
large unchanged bodies; actual remaining edits are authored as txt/md data.
"""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inventory
from scripts import p106b_hold_resolution_policy_v4 as policy
from scripts import p106b_hold_resolution_revision_v4 as revision

BASE = inventory.BASE
AUDIT = Path(__file__).resolve().parent
OUT = BASE / "legacy_span_review_v2"
ROLES = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
require = inventory.require
require(not OUT.exists(), "new immutable legacy review namespace required")
started = time.monotonic()
snapshot = json.loads((AUDIT / "authored_candidates_snapshot_v1.json").read_text())
handled = {row["original_text_sha256"] for row in snapshot["rows"]}
profile = json.loads((BASE / "pending_profile_v1/review_packets/manifest.json").read_text())
profile_ids = {row["id"] for group in json.loads((AUDIT / "profile_assignments_v1.json").read_text()).values() for row in group["rows"]}
handled.update(row["original_text_sha256"] for row in profile["rows"] if row["id"] in profile_ids)
previous_manual = json.loads((ROOT / "handoff/audit/hold_recovery_20261026_goalc/root_adoptions_v3.json").read_text())
# Includes the previously adjudicated unsafe source and the three boundaries.
# Do not decode/reproduce those raw sources again in this new text docket.
handled.update(row["input_text_sha256"] for row in previous_manual["rows"] if row["decision"] == "HOLD")
report = inventory.cache.read(BASE / "draft_proposals_v3/complete.json")
inventory.verify(BASE / "draft_proposals_v3/unique", report["unique_manifest"])
rows = [row for row in inventory.cache.rows(BASE / "draft_proposals_v3/unique", report["unique_manifest"])
        if "PRIOR_INDIVIDUAL_OR_SPAN_REVIEW_REQUIRES_ROOT_ADOPTION" in row["reasons"]
        and row["original_text_sha256"] not in handled]
keys = {row["original_text_sha256"] for row in rows}
original_inventory = inventory.cache.read(BASE / "inventory_v1/complete.json")
links = {row["original_text_sha256"]: row.get("previous_holds", [])
         for row in inventory.cache.rows(BASE / "inventory_v1/unique", original_inventory["unique_manifest"])
         if row["original_text_sha256"] in keys}
require(set(links) == keys, "inherited source disappeared from original inventory")
rows = [dict(row, previous_holds=links[row["original_text_sha256"]]) for row in rows]
pins = {name: inventory.file_sha(ROOT / name) for name in revision.CODE}
OUT.mkdir()
packets = OUT / "packets"
packets.mkdir()
prepared = []
counts = Counter()
with ExitStack() as stack:
    reader = inventory.OriginalReader(inventory.cache.read(BASE / "scope.json"), stack)
    for number, row in enumerate(rows, 1):
        original, complete, valid = reader.text(row)
        result = policy.draft_without_inherited_release(dict(row, text=original, complete_eos=complete, valid_utf8=valid))
        proposed = result.get("candidate", result["text"])
        prefix = row["id"].replace(":", "_")
        paths = {}
        for kind, text in [("original", original), ("candidate", proposed)]:
            if kind == "candidate" and proposed == original:
                paths[kind] = paths["original"]
                continue
            payload = text.encode("utf-8")
            require(len(payload) < 20_000_000, "ordered per-source text split required")
            path = packets / (prefix + "_" + kind + ".txt")
            with path.open("xb") as f:
                f.write(payload)
            paths[kind] = dict(path=str(path.relative_to(ROOT)), sha256=inventory.file_sha(path))
        prepared.append(dict(row, paths=paths, draft_decision=result["decision"], draft_reasons=result["reasons"],
                             raw_bytes=len(original.encode("utf-8")), root_approved=False))
        counts.update([result["decision"]])
        if number % 200 == 0:
            print(json.dumps(dict(phase="legacy_source_candidate_preparation", done=number, total=len(rows), seconds=round(time.monotonic()-started,1))), flush=True)
require({name: inventory.file_sha(ROOT / name) for name in revision.CODE} == pins, "draft code changed during preparation")
assigned = {role: [] for role in ROLES}
loads = {role: 0 for role in ROLES}
for row in sorted(prepared, key=lambda r: (-r["input_ids"], r["id"])):
    role = min(ROLES, key=lambda key: (loads[key], key))
    assigned[role].append(row)
    loads[role] += row["input_ids"]
results = {}
for role in ROLES:
    directory = BASE / "agents" / role / "legacy_span_review_v2"
    directory.mkdir()
    ordered = sorted(assigned[role], key=lambda r: r["id"])
    pages = []
    for index in range(0, len(ordered), 32):
        number = index // 32 + 1
        task = directory / ("TASK_" + str(number).zfill(3) + ".md")
        lines = ["# 이전 HOLD 원문 전수 판독 묶음 " + str(number), "",
                 "상위 TASK.md의 권한·출력 형식을 따른다. 아래 정확 입력만 읽고 이 묶음의 review_" + str(number).zfill(3) + ".md 및 필요한 새 txt/edits.md/exclude.md만 작성한다.", ""]
        for row in ordered[index:index + 32]:
            lines += ["## " + row["id"], "", "이전 보류 연결: " + ", ".join(row["previous_holds"]),
                      "", "초안 판정(채택 아님): " + row["draft_decision"] + " / " + ", ".join(row["draft_reasons"]), ""]
            for kind in ["original", "candidate"]:
                lines += [kind + ": `" + str(ROOT / row["paths"][kind]["path"]) + "`",
                          kind + " base_sha256: `" + row["paths"][kind]["sha256"] + "`", ""]
        with task.open("x", encoding="utf-8") as f:
            f.write(chr(10).join(lines))
        pages.append(str(task.relative_to(ROOT)))
    lines = ["# 이전 개별·구간 HOLD의 추가 원문 전체 대조", "",
             "역할은 지정 원문·후보의 실제 판독과 새 텍스트 작성이다. 코드·시험·전처리·코퍼스 통계·해시 계산·모델·GPU·Git·웹·설치·삭제·목록 밖 접근 금지. 원문/후보/다른 작성자의 저장물을 수정하지 않는다. 아래 모든 묶음이 배정 범위이며 첫32건을 작업량 상한으로 삼지 않는다. 묶음별 저장해 재개 가능하게 한다.", "",
             "이전 HOLD와 새 초안은 그대로 유지돼 있다. 이 작업은 원문을 다시 읽고 의미 보존 가능한 유지/수정/제외를 제안하는 단계다. 원문과 후보를 끝까지 직접 읽으며 잘린 출력은 작은 구간으로 재확인한다. 날짜·단위·수치·학술 용어·부정·조건·주체·인용·불확실성·원문 순서를 보존한다. 단순 반복/표/코드/전사라는 이유로 제외하지 않는다. 내용 없는 절·UI·실제로 소실된 식/값과 이에 의존하는 구간만 분리하고 가능한 독립 본문을 남긴다. 형식 정의를 완결 문장으로 추정해 재서술하지 않는다.", "",
             "일반 교육/역사/생물학이라는 주제명 자체는 형식 대조 중단 사유가 아니다. 새 실험·유전자/병원체 설계·위험한 활용 방법을 생성·최적화·요약하지 않는다. 실제로 유해한 작동 세부가 있는 경우 그 세부는 새 파일에 재전사하지 않고 정확한 경계와 제외 사유만 총괄에게 반환한다.", "",
             "각 묶음의 review_NNN.md 표: ID | KEEP_SOURCE/ADOPT_CANDIDATE/EDIT_TEXT/EDIT_RECIPE/EXCLUDE/NEEDS_ROOT | 실제 읽은 원문·후보 범위 | 구체 보존·분리·제외 이유 | 실제 새 출력 파일. KEEP_SOURCE는 원문 그대로, ADOPT_CANDIDATE는 지정 후보 그대로 승인 제안이므로 불필요한 본문 복사는 하지 않는다. 초안이 PENDING이어도 실제 함수 호출/유효 반복 등으로 반증되면 이유를 적고 유지 가능하다. 반대로 초안 KEEP이어도 실제 손상/고아 참조가 있으면 그대로 승인하지 않는다.", "",
             "EDIT_TEXT는 작은 완결 정제본을 SOURCE_ID.txt로 직접 쓰고 분리 원문/사유를 SOURCE_ID_hold.md에 적는다. 큰 본문에 소수 수정이면 EDIT_RECIPE로 SOURCE_ID.edits.md만 작성해 정확한 원문 구절/새 구절을 제시할 수 있다. 실제 적용/유일성/해시는 총괄이 계산한다. 각 original anchor는 같은 base에서 정확히 한 번 나오는 충분한 문맥이고 서로 겹치면 안 된다. 생략부호로 줄이거나 정규식/코드 명령을 쓰지 않는다. 원문이 보존돼 있으므로 큰 제외 구간을 sidecar에 재복사할 필요 없이 구간 시작/끝과 이유를 기록할 수 있다.", "",
             "EXCLUDE는 실제 결손·주체/조건/문서 경계 소실과 독립 본문이 남지 않는 이유를 SOURCE_ID_exclude.md에 적는다. 과거 HOLD라는 이유만으로 제외하지 않는다. 판단 갈림은 정확 구절로 총괄에게 반환하고 다른 묶음을 계속한다. 검수 메모는 학습 txt에 넣지 않는다. 사실 검증/모델 품질/전량 최종 채택으로 보고하지 않는다.", "",
             "## EDIT_RECIPE 형식", "", "다음 고정8개 backtick 울타리는 데이터 구분자다. 실제 source_id/base/hash는 개별 TASK에서 그대로 복사하며 계산하지 않는다. ORIGINAL과 REPLACEMENT 안에는 실제 텍스트만 쓴다. 완전 삭제는 REPLACEMENT 내용을 빈 줄로 둔다.", "",
             "# P106B_LITERAL_TEXT_EDITS_V1", "source_id: expanded_train:번호", "base: original", "base_sha256: TASK에 적힌 해당 base 해시", "reason: 구체 한국어 사유", "", "## Change 1", "ORIGINAL", "````````text", "실제 원문 구절", "````````", "REPLACEMENT", "````````text", "실제 새 구절", "````````", "", "## 배정된 모든 묶음", ""]
    lines += ["- `" + str(ROOT / page) + "`" for page in pages]
    with (directory / "TASK.md").open("x", encoding="utf-8") as f:
        f.write(chr(10).join(lines))
    results[role] = dict(ids=[row["id"] for row in ordered], pages=pages, input_ids=loads[role],
                        task=str((directory / "TASK.md").relative_to(ROOT)))
value = dict(schema="P106B_ADDITIONAL_INHERITED_SOURCE_REVIEW_V1", status="TEXT_REVIEW_NOT_ADOPTION",
             code_sha256=pins, rows=prepared, assignments=results, counts=dict(counts),
             documents=len(prepared), input_ids=sum(row["input_ids"] for row in prepared),
             seconds=time.monotonic()-started)
inventory.write_json(OUT / "manifest.json", value)
inventory.write_json(AUDIT / "legacy_span_assignments_v2.json", dict(assignments=results, documents=len(prepared), code_sha256=pins))
print(json.dumps(dict(documents=len(prepared), input_ids=value["input_ids"], draft_counts=dict(counts), seconds=value["seconds"],
                      assignments={role:len(rows) for role,rows in assigned.items()})), flush=True)
