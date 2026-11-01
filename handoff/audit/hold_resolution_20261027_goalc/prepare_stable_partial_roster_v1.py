"""Plan and materialize a reviewed stable subset without promoting new drafts.

The full original residual is covered. V6/V9 terminal bodies must match exactly;
all authored/individually assigned/new-counterexample sources remain HOLD here.
An explicit root approval of the immutable plan is required for prepare.
"""
from collections import Counter
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_partial_cache as partial

AUDIT=Path(__file__).resolve().parent
BASE=inv.BASE
PLAN=BASE/"stable_partial_plan_v1"
ROSTER=BASE/"roster_stable_partial_v1"
AUDIT_PLAN=AUDIT/"stable_partial_candidate_plan_v1.json"
APPROVAL=AUDIT/"ROOT_STABLE_PARTIAL_ADMISSIONS_V1.json"
CODE_SOURCE=Path(__file__)


def required_input_pins():
    paths=[BASE/"draft_proposals_v6/complete.json",BASE/"draft_proposals_v9/complete.json",
           BASE/"pending_materialized_v6_v1/complete.json",BASE/"legacy_span_review_v2/manifest.json",
           BASE/"policy_counter_review_v1/manifest.json",AUDIT/"authored_candidates_snapshot_v4.json"]
    return {str(path.relative_to(ROOT)):inv.file_sha(path) for path in paths}


def plan():
    inv.require(not PLAN.exists() and not AUDIT_PLAN.exists(),"stable plan version already exists")
    before=required_input_pins()
    old=inv.cache.read(BASE/"draft_proposals_v6/complete.json")
    current=inv.cache.read(BASE/"draft_proposals_v9/complete.json")
    inv.require(old["root_adopted"]==current["root_adopted"]==0 and current["full_residual_scope_covered"],"draft scope differs")
    for receipt in [old,current]:
        for name,digest in receipt["lineage"]["source_code_sha256"].items():
            inv.require(inv.file_sha(ROOT/name)==digest,"a frozen draft source changed")
    integrity=inv.cache.read(BASE/"pending_materialized_v6_v1/complete.json")
    # The complete materialized receipt is pinned as evidence. The root approval
    # independently names its ordered/code/Unicode result after reading it.
    inv.verify(BASE/"draft_proposals_v6/unique",old["unique_manifest"])
    inv.verify(BASE/"draft_proposals_v9/unique",current["unique_manifest"])
    previous={row["original_text_sha256"]:(row["decision"],row.get("clean_text_sha256"))
              for row in inv.cache.rows(BASE/"draft_proposals_v6/unique",old["unique_manifest"])}
    blocked={row["original_text_sha256"] for row in inv.cache.read(BASE/"legacy_span_review_v2/manifest.json")["rows"]}
    blocked.update(row["original_text_sha256"] for row in inv.cache.read(AUDIT/"authored_candidates_snapshot_v4.json")["rows"])
    blocked.update(row["original"]["sha256"] for row in inv.cache.read(BASE/"policy_counter_review_v1/manifest.json")["rows"])
    boundary_ids={"historical_train:709976","validation:0","validation:3759"}
    writer=inv.ShardWriter(PLAN/"records","decisions",limit=19_999_999)
    decisions={}
    groups=Counter()
    counts=Counter()
    terminal_reasons=Counter()
    for row in inv.cache.rows(BASE/"draft_proposals_v9/unique",current["unique_manifest"]):
        key=row["original_text_sha256"]
        inv.require(key in previous and key not in decisions,"stable plan source coverage differs")
        old_decision,old_sha=previous[key]
        stable=(key not in blocked and old_decision in {"KEEP","EDIT"}
                and row["decision"] in {"KEEP","EDIT"} and row["clean_text_sha256"]==old_sha)
        boundary=(row["id"] in boundary_ids and row["decision"]=="EXCLUDE")
        decision=row["decision"] if stable or boundary else "HOLD"
        group="EXACT_STABLE_V6_V9_BODY" if stable else "ORIGINAL_UNRECOVERABLE_SPLIT_BOUNDARY" if boundary else "OUTSIDE_APPROVED_STABLE_SUBSET"
        record={name:row[name] for name in ["id","source","split","source_ids","source_ids_sha256","original_text_sha256","input_ids","language_bucket","occurrences"]}
        record.update(decision=decision,root_approved=False,planned_group=group,
                      reason=group+":"+",".join(row["reasons"]),draft_rules=row["rules"])
        if stable:
            record["clean_text_sha256"]=row["clean_text_sha256"]
            if decision=="EDIT":
                inv.require(inv.sha(row["text"])==row["clean_text_sha256"],"stable edited body changed")
                record["text"]=row["text"]
            terminal_reasons.update(change["reason"] for change in row["changes"])
        elif decision=="HOLD":
            record["review_status"]="UNRESOLVED_NOT_ADMITTED"
        writer.append(record)
        decisions[key]=decision
        counts.update([decision])
        groups.update([group])
    inv.require(set(decisions)==set(previous),"stable plan omits original unique sources")
    manifest=writer.close(lineage=dict(input_pins=before,producer_sha256=inv.file_sha(CODE_SOURCE)))
    weighted=Counter()
    for row in inv.cache.rows(BASE/"draft_proposals_v9/occurrences",current["occurrence_manifest"]):
        decision=decisions[row["original_text_sha256"]]
        weighted.update(documents=1,input_ids=row["input_ids"],**{decision:1})
        weighted[decision+"_input_ids"]+=row["input_ids"]
    inv.require(weighted["documents"]==inv.EXPECTED and weighted["input_ids"]==462874291,"stable occurrence conservation differs")
    inv.require(before==required_input_pins(),"stable inputs changed during planning")
    result=dict(status="STABLE_SUBSET_PLAN_NOT_ADMISSION",root_adopted=0,goal_complete=False,training_authorized=False,
        counts=dict(counts),occurrence_counts=dict(weighted),groups=dict(groups),terminal_change_reasons=dict(terminal_reasons),
        blocked_source_keys=len(blocked),input_pins=before,producer_sha256=inv.file_sha(CODE_SOURCE),
        records_directory="records",manifest=manifest)
    inv.write_json(PLAN/"complete.json",result)
    inv.write_json(AUDIT_PLAN,dict(result,manifest=None,plan_path=str((PLAN/"complete.json").relative_to(ROOT)),
                                 plan_sha256=inv.file_sha(PLAN/"complete.json")))
    print(json.dumps(dict(status=result["status"],counts=result["counts"],occurrence_counts=result["occurrence_counts"],groups=result["groups"])))


def prepare():
    inv.require(not ROSTER.exists(),"stable roster version already exists")
    summary=inv.cache.read(AUDIT_PLAN)
    approval=inv.cache.read(APPROVAL)
    inv.require(approval.get("schema")=="P106B_ROOT_STABLE_SUBSET_ADMISSION_V1"
                and approval.get("root_approved") is True and approval.get("goal_complete") is False
                and approval.get("training_authorized") is False,"explicit root stable-subset approval required")
    inv.require(approval["audit_plan_sha256"]==inv.file_sha(AUDIT_PLAN)
                and summary["plan_sha256"]==inv.file_sha(PLAN/"complete.json"),"approved stable plan changed")
    for name,digest in summary["input_pins"].items():
        inv.require(inv.file_sha(ROOT/name)==digest,"approved stable input changed")
    for evidence in approval["independent_review_pins"]:
        inv.require(inv.file_sha(ROOT/evidence["path"])==evidence["sha256"],"stable independent review changed")
    receipt=inv.cache.read(PLAN/"complete.json")
    inv.verify(PLAN/"records",receipt["manifest"])
    writer=inv.ShardWriter(ROSTER/"records","decisions",limit=19_999_999)
    proof=dict(path=str(APPROVAL.relative_to(ROOT)),sha256=inv.file_sha(APPROVAL))
    for row in inv.cache.rows(PLAN/"records",receipt["manifest"]):
        writer.append(dict(row,root_approved=row["decision"]!="HOLD",evidence=proof))
    manifest=writer.close(lineage=dict(approval=proof,source_plan_sha256=summary["plan_sha256"]))
    counts=summary["occurrence_counts"]
    inv.write_json(ROSTER/"complete.json",dict(schema=partial.SCHEMA,status="ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER",
        goal_complete=False,training_authorized=False,parent_built_sha256=inv.file_sha(inv.PARENT/"built.json"),
        records_directory="records",manifest=manifest,counts={name:counts[name] for name in ["documents","input_ids"]},
        remaining_hold=counts.get("HOLD",0),unprocessed=counts.get("HOLD",0),approval=proof))
    adoptions=BASE/"stable_partial_adoptions_v1.json"
    inv.write_json(adoptions,dict(schema="P106B_ROOT_TEXT_ADOPTIONS_V1",rows=[],reviews=[]))
    old=inv.cache.read(inv.PARENT/"built.json")
    writer=inv.ShardWriter(BASE/"partial_proposals_v1/ledger","proposals",limit=19_999_999)
    census_counts=Counter()
    for row in inv.cache.rows(inv.PARENT/"hold",old["manifests"]["hold"]):
        writer.append(row)
        census_counts.update(documents=1,input_ids=row["input_ids"])
    census_manifest=writer.close(lineage=dict(approval=proof))
    with partial.revision():
        pins=partial.engine.code_pins()
    inv.write_json(BASE/"partial_proposals_v1/complete.json",dict(unprocessed=0,
        meaning="FULL_SOURCE_ENUMERATION_ONLY_NOT_CONTENT_COMPLETION",content_unprocessed=counts.get("HOLD",0),
        counts=dict(census_counts),manifest=census_manifest,pin=dict(recovery_revision_source_sha256=pins,
            parent_built_sha256=inv.file_sha(inv.PARENT/"built.json"),parent_verified_sha256=inv.file_sha(inv.PARENT/"verified.json"),
            scope_sha256=inv.file_sha(BASE/"scope.json"))))
    print(json.dumps(dict(status="PARTIAL_ROSTER_PREPARED_NOT_CACHE_BUILT",remaining_hold=counts.get("HOLD",0),
                         roster=str((ROSTER/"complete.json").relative_to(ROOT)))))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["plan","prepare"])
    args=parser.parse_args()
    (plan if args.command=="plan" else prepare)()
