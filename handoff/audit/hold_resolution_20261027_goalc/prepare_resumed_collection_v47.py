"""Extend the saved collector with two exact nine-source review cohorts."""
from pathlib import Path
import json
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

sealed_path = AUDIT / "CURRENT_TWO_ROLE_REVIEW_RECEIPT_V1.json"
sealed = inv.cache.read(sealed_path)
parser, ident, _ = runpy.run_path(str(AUDIT / "seal_current_two_role_review_v1.py"), run_name="checkpoint_reuse")["load_review_parser"]()
selected = {row["id"]: row for row in sealed["rows"]}
old_path = AUDIT / "AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V1.json"
rows = list(inv.cache.read(old_path)["rows"])
for auxiliary in sealed["nonselected_reviews_preserved"]:
    path = ROOT / auxiliary["path"]
    inv.require(inv.file_sha(path) == auxiliary["sha256"], "old review changed")
    parsed = parser(path.read_bytes())
    inv.require(len(parsed) == 1, "nonselected review needs exact one-ID adjudication")
    key = ident(parsed[0]["cells"][0])
    inv.require(key in selected, "nonselected review refers to another source")
    canonical = selected[key]["review"]
    final = parser((ROOT / canonical["path"]).read_bytes())
    inv.require(len(final) == 1 and ident(final[0]["cells"][0]) == key, "canonical review differs")
    inv.require(inv.file_sha(ROOT / canonical["path"]) == canonical["sha256"], "final review changed")
    rows.append(dict(path=auxiliary["path"], sha256=auxiliary["sha256"], canonical_review=canonical["path"],
        canonical_review_sha256=canonical["sha256"], ids=[key], auxiliary_rows={key: parsed[0]["raw"]},
        canonical_matching_rows={key: final[0]["raw"]}, root_approved=True,
        disposition="REJECTED_OR_SUPERSEDED_DRAFT_REVIEW_HISTORY_NOT_FINAL_DECISION",
        reason="同一源" if False else "같은 정확 원문의 최종 리뷰가9건 마감 영수증에 고정됐다. 불완전/잘못된 초안 리뷰는 원형과 SHA로 보존하고 별개 최종 결정으로 사용하지 않는다. 파일시각이나 최대 버전 자동 선택이 아니다.",
        original_auxiliary_preserved=True, root_body_authorship=False, cache_admitted=0))
inv.require(len(rows) == 18, "all17 new nonselected reviews plus prior auxiliary required")
auxiliary_path = AUDIT / "AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V2.json"
inv.require(not auxiliary_path.exists(), "new immutable auxiliary registry required")
inv.write_json(auxiliary_path, dict(schema="EXACT_AUXILIARY_REVIEW_DISPOSITIONS_V2", rows=rows,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [old_path, sealed_path, Path(__file__)]}))


def replace_once(text, old, new):
    inv.require(text.count(old) == 1, "frozen producer splice is not unique: " + old[:70])
    return text.replace(old, new, 1)


groups = ["resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"]
source = (AUDIT / "collect_supplemental_candidates_v46.py").read_text(encoding="utf-8")
source = replace_once(source, '"supplemental_candidates_snapshot_v46.json"', '"supplemental_candidates_snapshot_v47.json"')
source = replace_once(source, '"AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V1.json"', '"AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V2.json"')
anchor = 'groups += ["root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1", "profile_strata_source_counter_v25_v1"]'
source = replace_once(source, anchor, anchor + chr(10) + "groups += " + repr(groups))
view_extension = '''
for resumed_group in ["resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"]:
    resumed_path = BASE / resumed_group / "reading_views_manifest_v1.json"
    resumed_views = inv.cache.read(resumed_path)
    inv.require(inv.file_sha(ROOT / resumed_views["source_manifest"]["path"]) == resumed_views["source_manifest"]["sha256"],
                "resumed views refer to another exact assignment")
    input_pins[str(resumed_path.relative_to(ROOT))] = inv.file_sha(resumed_path)
    views_manifest["rows"].extend(resumed_views["rows"])
strict_task_cohorts.update({"resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"})
'''
source = replace_once(source, "def digest(payload):", view_extension + chr(10) + "def digest(payload):")
anchor = '            output_cell = next((value for label, value in columns.items() if label in {"출력", "정확 출력", "산출물"}), line)'
extension = '''            if directory.name in {"resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"}:
                pattern += r"|" + re.escape(key_id.replace(":", "_")) + r"_(?:reviewed_v[0-9]+|candidate|original)[.]txt"
'''
source = replace_once(source, anchor, extension + anchor)
anchor = "for detail in coverage.values():"
extension = '''for resumed_group in ["resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"]:
    inv.require(coverage[resumed_group]["expected"] == 9, "resumed exact nine-source assignment differs")
'''
source = replace_once(source, anchor, extension + anchor)
with (AUDIT / "collect_supplemental_candidates_v47.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (AUDIT / "materialize_reviewed_selection_plan_v23.py").read_text(encoding="utf-8")
source = replace_once(source, '"reviewed_selection_plan_v23.json"', '"reviewed_selection_plan_v24.json"')
source = replace_once(source, '"supplemental_candidates_snapshot_v46.json"', '"supplemental_candidates_snapshot_v47.json"')
source = replace_once(source, '"profile_strata_source_counter_v25_v1"]]',
    '"profile_strata_source_counter_v25_v1", "resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"]]')
with (AUDIT / "materialize_reviewed_selection_plan_v24.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print(json.dumps(dict(auxiliary_history=len(rows), preserved_new_nonselected=17, new_cohorts=groups), ensure_ascii=False))
