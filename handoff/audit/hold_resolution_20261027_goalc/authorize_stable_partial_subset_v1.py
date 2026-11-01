"""Record the root's bounded stable-body decision, not a goal completion."""
from datetime import datetime,timezone
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT=Path(__file__).resolve().parent
BASE=inv.BASE
plan_path=AUDIT/"stable_partial_candidate_plan_v1.json"
plan=inv.cache.read(plan_path)
integrity_path=BASE/"pending_materialized_v6_v1/complete.json"
integrity=inv.cache.read(integrity_path)
inv.require(integrity["terminal_integrity_flags"]==[] and integrity["terminal_integrity_manifest"]["rows"]==199109,
            "the full stable-source preservation receipt differs")
allowed={"EMPTY_FOOTER_BEFORE_PROVEN_METADATA_START_PRESERVE_ALL_NOMINAL_SUFFIX_WORDS",
         "IDENTIFIED_NOMINAL_CONTEXT_REMOVE_ONLY_EMPTY_OPTIONAL_FIELDS",
         "EMPTY_SECTION_PROVEN_BY_APPENDIX_OR_EOF_PRESERVE_POPULATED_CHILD",
         "EMPTY_WEB_CONTENTS_MARKER_OR_EXPLICIT_PAGE_NAVIGATION",
         "EMPTY_FOOTER_BEFORE_EXPLICIT_SOURCE_METADATA_ANCHOR",
         "EMPTY_WIKI_FOOTER_BEFORE_EXPLICIT_CATEGORY_LINES",
         "EMPTY_REFERENCE_RECORD_WITH_NO_NAME_OR_VALUE"}
inv.require(set(plan["terminal_change_reasons"])<=allowed,"stable subset contains an unreviewed change family")
inv.require(plan["counts"]==dict(EXCLUDE=3,EDIT=168392,KEEP=27724,HOLD=101420),"root-reviewed plan counts changed")
inv.require(plan["occurrence_counts"]["HOLD"]==160219 and plan["blocked_source_keys"]==2175,
            "root-reviewed pending/exemption scope changed")
reviews=[]
for role in ["context_controls","context_hangul","context_latin","historical_review","legacy_review"]:
    directory=BASE/"agents"/role
    for pattern in ["counter_manual_v1/counter*.md","counter_family_v1/counter*.md","counter_family_v2/counter*.md",
                    "counter_family_hangul_v1/counter*.md","counter_profile_v1/counter*.md",
                    "counter_followup_v2/counter*.md","integrity_followup_v3/counter*.md"]:
        for path in directory.glob(pattern):
            reviews.append(dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path)))
inv.require(len(reviews)>=15,"independent context review evidence is missing")
decision=dict(schema="P106B_ROOT_STABLE_SUBSET_ADMISSION_V1",root_approved=True,reviewed_by="/root",
    reviewed_at=datetime.now(timezone.utc).isoformat(),goal_complete=False,training_authorized=False,
    audit_plan_sha256=inv.file_sha(plan_path),plan_sha256=plan["plan_sha256"],
    admitted_unique_bodies=196116,proposed_admitted_occurrences=300473,remaining_hold_occurrences=160219,
    independent_review_pins=reviews,preservation_receipt=dict(path=str(integrity_path.relative_to(ROOT)),sha256=inv.file_sha(integrity_path)),
    approved_change_families=sorted(allowed),
    basis=["v6/v9 actual full-source draft receipts and exact source/body SHA agreement",
           "all 199109 v6 terminal sources passed full ordered-nonwhitespace/code/Unicode preservation replay",
           "independent text review of the recovery patterns with root adjudication and corrected negative cases",
           "all 2175 individually authored, prior span-review and new counterexample source keys excluded from this automatic subset"],
    limits=["this is format/context recovery, not full factual validation or model quality evidence",
            "unreviewed newer bodies and unresolved sources stay HOLD; this does not complete the 460695-source goal",
            "baseline accepted bodies and exclusions must remain unchanged in the actual build and full consumer",
            "exact new duplicates and train/validation overlaps may reduce the actual new admission count"],
    producer_sha256=inv.file_sha(Path(__file__)))
out=AUDIT/"ROOT_STABLE_PARTIAL_ADMISSIONS_V1.json"
inv.write_json(out,decision)
print(json.dumps(dict(path=str(out.relative_to(ROOT)),sha256=inv.file_sha(out),review_pins=len(reviews),
                     proposed_admitted_occurrences=300473,remaining_hold=160219,goal_complete=False)))
