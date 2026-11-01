"""Pin tests, actual purpose execution, independent rows and source scope."""
from datetime import datetime
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_revision_v25 as revision
from scripts import p106b_hold_resolution_policy_v25 as policy

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
purpose_path = AUDIT / "policy_v25_purpose_probe_v1.json"
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v37.json"
baseline_path = BASE / "draft_proposals_v21/complete.json"
purpose, snapshot, baseline = [inv.cache.read(p) for p in [purpose_path, snapshot_path, baseline_path]]
inv.require(len(revision.CODE) == len(set(revision.CODE)) == 63, "production source list differs")
for name, sha in purpose["source_code_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == sha, "purposed production source changed")
for name, sha in baseline["lineage"]["source_code_sha256"].items():
    inv.require(inv.file_sha(ROOT / name) == sha, "verified v21 source changed")
inv.require(len(purpose["rows"]) == 987 and purpose["counts"] == dict(PENDING=862, EDIT=98, KEEP=27),
            "actual purpose counts differ")
by_id = {r["id"]: r for r in purpose["rows"]}
inv.require(by_id["expanded_train:897170"]["decision"] == "PENDING"
            and policy.COLUMN_REASON in by_id["expanded_train:897170"]["reasons"], "missing language axis was released")
for ident in ["827", "47955", "183488", "268392", "599416", "885560", "1200497"]:
    row = by_id["expanded_train:" + ident]
    inv.require(row["decision"] == "PENDING" and policy.ALIAS_BODY in row["reasons"], "named alias certified an unchecked body")
groups = ["policy_v23_literal_counter_v1", "policy_v23_structural_counter_v1", "root_selected_literal_counter_v4"]
for group, expected in zip(groups, [9, 33, 2]):
    cover = snapshot["coverage"][group]
    inv.require(cover["saved"] == cover["expected"] == expected and cover["awaiting_review"] == 0, "independent assignment missing")
inv.require(not [r for r in snapshot["errors"] if r.get("group") in groups], "a new source review was rejected")
new_terminal = [r for r in purpose["rows"] if r["previous_decision"] == "PENDING" and r["decision"] in {"KEEP", "EDIT"}]
inv.require(len(new_terminal) == 13, "new purpose terminals differ")
reviews, overrides = [], []
for row in new_terminal:
    inv.require(all(row[k] for k in ["code_guard", "unicode_guard", "semantic_style_guard", "ordered_deletion"]), "terminal preservation flag")
    choices = [r for r in snapshot["records"] if r["id"] == row["id"] and r["cohort"] in groups]
    inv.require(choices and all(r["status"] != "MECHANICAL_REJECTION_NOT_APPLIED" and r["decision"] != "NEEDS_ROOT" for r in choices),
                "new terminal lacks a saved independent source review")
    for review in choices:
        inv.require(review["original"]["sha256"] == row["source"]["sha256"], "independent review has a different original")
        inv.require(inv.file_sha(ROOT / review["review"]["path"]) == review["review"]["sha256"], "independent review changed")
        inv.require(inv.file_sha(ROOT / review["body"]) == review["clean_text_sha256"], "independent body changed")
    unequal = [r for r in choices if r["clean_text_sha256"] != row["clean_text_sha256"]]
    if unequal:
        overrides.append(dict(id=row["id"], automatic_candidate_sha256=row["clean_text_sha256"],
            independent_review_bodies=[dict(body=r["body"], sha256=r["clean_text_sha256"]) for r in unequal],
            disposition="INDIVIDUALLY_REVIEWED_SOURCE_REQUIRES_EXPLICIT_BODY_SELECTION_BEFORE_CACHE"))
    reviews.append(dict(id=row["id"], source=row["source"], saved_reviews=[r["review"] for r in choices]))
tests = [
    ("test_policy_v25_v1.log", "Ran 361 tests", "2529f7"),
    ("test_refinement_v10_current25_v1.log", "Ran 48 tests", "545cb6"),
    ("test_review_safeguards_v3_v1.log", None, "f8daa8")]
for filename, count, observed in tests:
    log = (AUDIT / filename).read_text(encoding="utf-8")
    inv.require(log.rstrip().endswith("OK") and (count is None or count in log), "required test did not pass")
output = AUDIT / "POLICY_V25_FULL_PREFLIGHT_V1.json"
inv.require(not output.exists() and not (BASE / "draft_proposals_v25").exists(), "full v25 already exists")
receipt = dict(status="CPU_FULL_DRAFT_PREFLIGHT_PASSED_NOT_CACHE_ADMISSION",
    observed_exit_zero=dict(regression="2529f7", replay="545cb6", review_guard="f8daa8", purpose="d0d00f",
                            collector37="228f0f", plan14="aade14", preview="72221a"),
    original_scope=dict(unique_original_sha256=297539, occurrences=460695, stored_input_ids=462874291),
    source_code_pins={name: inv.file_sha(ROOT / name) for name in revision.CODE},
    purpose_sources=987, independent_saved_pairs=44, purpose_new_terminal_sources=13,
    independent_source_reviews=reviews, required_manual_body_overrides=overrides,
    automatic_cache_admitted=0, final_admission_must_exempt_every_individually_reviewed_source=True,
    current_root_selection8_sources=3084, new_selection9_unresolved=7,
    cpu_threads=1, estimated_seconds=[3000, 5400], gpu_calls=0, model_loads=0,
    whole_v22_v23_v24_drafts_not_run=True, goal_complete=False, training_authorized=False,
    input_pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [
        purpose_path, snapshot_path, baseline_path, *(AUDIT / t[0] for t in tests),
        AUDIT / "POLICY_V25_CONTEXT_CONTRACT_V1.md", Path(__file__)]})
inv.write_json(output, receipt)
lines = ["", "## " + datetime.now().astimezone().isoformat() + " — v25 전량 CPU 초안 시작 예고", "",
    "선행 회귀361/동결재생48/작업배정검사 및987쌍 목적 검사는 실제0이며 독립9+33+2 전량저장·새기계반려0입니다. 수식 결손과 필수 비교열 전량결손 반례를 보수적으로 반영했고 전량v22/v23/v24는 실행하지 않습니다.",
    "이제 소유63 생산파일을 동결하고 원래297539SHA/460695위치의 새v25 전량 초안을 CPU1로 수행합니다. 예상50–90분, 여유RAM약28GB·디스크약489GiB 확인, GPU/모델/학습0입니다. 다른 세션 경로·원장·프로세스·Git/index를 열거나 바꾸지 않으며 중단/잠금을 요청하지 않습니다.",
    "실행 중 생산파일은 수정하지 않고 자기 저장본문 중재/감사만 진행합니다. 새초안은 캐시채택/goal완료/추가300M승인이 아닙니다. 모든 개별판독 원문은 최종 자동채택에서 제외하고 정확 선택본문을 별도로 연결해야 합니다.", ""]
with (ROOT / "tmp/COORD_HOLD_01a17740.md").open("a", encoding="utf-8") as stream:
    stream.write(chr(10).join(lines))
print(json.dumps(dict(status=receipt["status"], code_files=63, scope=receipt["original_scope"],
    required_manual_overrides=[r["id"] for r in overrides], estimated_seconds=receipt["estimated_seconds"]), ensure_ascii=False))
