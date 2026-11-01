#!/usr/bin/env python3
"""An explicitly incomplete recovery cache; never a zero-HOLD goal receipt.

Reuse the frozen builder, baseline priority and independent full consumer.
Only root-approved terminal bodies enter training text. Unresolved sources stay
HOLD with their actual occurrence counts; no placeholder exclusions are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_cache as final
from scripts import p106b_hold_resolution_revision_v9 as context_revision

engine=final.engine
cache=engine.cache
require=engine.require
BASE=final.BASE
SCHEMA="P106B_PARTIAL_RESIDUAL_RECOVERY_ROSTER_V1"
RULES="PARTIAL_RESIDUAL_RECOVERY_GOAL_INCOMPLETE_V1"
EXTRA_CODE=list(dict.fromkeys(final.EXTRA_CODE+context_revision.CODE+
                             ["scripts/p106b_hold_resolution_partial_cache.py"]))


def load_roster(path,index):
    document=cache.read(path)
    require(document.get("schema")==SCHEMA and document.get("status")=="ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER",
            "explicit partial roster is required")
    require(document.get("goal_complete") is False and document.get("training_authorized") is False,
            "partial roster cannot assert goal or training authorization")
    require(document["parent_built_sha256"]==engine.file_sha(index.old/"built.json"),"partial parent differs")
    directory=path.parent/document["records_directory"]
    require(directory.resolve().is_relative_to(path.parent.resolve()),"partial roster records escape their version")
    cache.verify(directory,document["manifest"])
    result={}
    evidence_pins={}
    for row in cache.rows(directory,document["manifest"]):
        key=row["original_text_sha256"]
        decision=row["decision"]
        require(key not in result and decision in {"KEEP","EDIT","EXCLUDE","HOLD"},"duplicate or unknown partial outcome")
        require(row.get("reason") and isinstance(row.get("evidence"),dict),"partial outcome lacks evidence")
        evidence=row["evidence"]
        evidence_path=ROOT/evidence["path"]
        allowed=[index.base/"agents",ROOT/"handoff/audit/hold_resolution_20261027_goalc"]
        require(any(evidence_path.resolve().is_relative_to(folder.resolve()) for folder in allowed),"partial evidence escapes review paths")
        if evidence["path"] not in evidence_pins:
            evidence_pins[evidence["path"]]=engine.file_sha(evidence_path)
        require(evidence_pins[evidence["path"]]==evidence["sha256"],"partial review evidence changed")
        if decision=="HOLD":
            require(row.get("root_approved") is False and row.get("review_status")=="UNRESOLVED_NOT_ADMITTED",
                    "unresolved text cannot be labeled root-approved")
            require(not row.get("text") and not row.get("clean_text_sha256"),"unresolved candidate must stay out of admitted bodies")
        else:
            require(row.get("root_approved") is True,"terminal partial proposal is not root-approved")
            if decision=="KEEP":
                require(row["clean_text_sha256"]==key,"partial KEEP changes the source")
            elif decision=="EDIT":
                require(isinstance(row.get("text"),str) and row["text"].strip()
                        and engine.sha(row["text"])==row["clean_text_sha256"]
                        and not engine.corpus.MEMOS.search(row["text"]),"partial edited body differs or contains a memo")
        result[key]=row
    counts=Counter()
    keys=set()
    remaining=0
    cache.verify(index.old/"hold",index.report["manifests"]["hold"])
    for row in cache.rows(index.old/"hold",index.report["manifests"]["hold"]):
        key=row["original_text_sha256"]
        require(key in result,"partial roster omits a residual source")
        keys.add(key)
        counts.update(documents=1,input_ids=row["input_ids"])
        remaining+=result[key]["decision"]=="HOLD"
    require(keys==set(result) and dict(counts)==document["counts"]
            and counts["documents"]==index.counts["HOLD"],"partial full-source coverage differs")
    require(document.get("remaining_hold")==remaining and document.get("unprocessed")==remaining,
            "partial remaining-HOLD occurrence count differs")
    return document,result


@contextmanager
def revision(prepared=None):
    with patch.object(final,"load_roster",load_roster),patch.object(final,"EXTRA_CODE",EXTRA_CODE), \
            patch.object(final,"RULES",RULES):
        with final.revision(prepared):
            yield


def build(base,adoptions,roster,output_name="cache_partial_v1",proposal_name="partial_proposals_v1"):
    require(not (base/output_name).exists(),"partial cache version already exists")
    # Baseline construction must precede public ParentIndex replacement. Its
    # original reproducer owns the older parent, not the current cache's index.
    with patch.object(final,"load_roster",load_roster):
        prepared=final.ResolutionEngine(base,adoptions,roster)
    with revision(prepared):
        report=engine.build(base,adoptions,output_name,proposal_name)
    require(report["counts"].get("HOLD",0)==prepared.roster_document["remaining_hold"],
            "a terminal body failed a guard; partial count is not the approved count")
    return report


def verify(base,roster,output_name="cache_partial_v1"):
    with revision():
        result=engine.verify(base,output_name)
    index=final.LatestIndex(base)
    document,proposals=load_roster(roster,index)
    report=cache.read(base/output_name/"built.json")
    require(report["counts"].get("HOLD",0)==document["remaining_hold"],"actual partial HOLD count differs")
    checked=Counter()
    outcomes=Counter()
    roster_sha=engine.file_sha(roster)
    for row in cache.rows(base/output_name/"ledger",report["manifests"]["ledger"]):
        if index.state(row)!=3:
            continue
        expected=proposals[row["original_text_sha256"]]
        if expected["decision"]=="HOLD":
            require(row["decision"]=="HOLD","unresolved source was promoted or discarded")
        elif expected["decision"]=="EXCLUDE":
            require(row["decision"]=="EXCLUDE","excluded partial source was admitted")
        elif row["decision"] in {"KEEP","EDIT"}:
            require(row["clean_text_sha256"]==expected["clean_text_sha256"],"partial admitted text differs")
        else:
            require(row["decision"]=="EXCLUDE" and (row.get("duplicate_of") or row.get("validation_overlap")),
                    "approved partial body was lost without duplicate/split evidence")
        require(row.get("resolution_roster_sha256")==roster_sha,"partial ledger roster differs")
        checked.update(documents=1,input_ids=row["input_ids"])
        outcomes.update([row["decision"]])
    require(dict(checked)==document["counts"],"independent partial residual coverage differs")
    proof=dict(schema=SCHEMA,status="CPU_PARTIAL_RECOVERY_CACHE_VERIFIED_GOAL_INCOMPLETE",
               roster_sha256=roster_sha,checked=dict(checked),outcomes=dict(outcomes),
               remaining_hold=document["remaining_hold"],unprocessed=document["remaining_hold"],
               all_previous_adopted_text_preserved=True,goal_complete=False,training_authorized=False,
               core_recovery_verified_sha256=engine.file_sha(base/output_name/"recovery_verified.json"))
    engine.write_json(base/output_name/"partial_resolution_verified.json",proof)
    return dict(result,partial_resolution=proof)


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["build","verify"])
    parser.add_argument("--base",type=Path,default=BASE)
    parser.add_argument("--adoptions",type=Path)
    parser.add_argument("--roster",type=Path,required=True)
    parser.add_argument("--output-name",default="cache_partial_v1")
    parser.add_argument("--proposal-name",default="partial_proposals_v1")
    args=parser.parse_args()
    base=engine.safe(args.base)
    roster=engine.safe(args.roster)
    if args.command=="build":
        require(args.adoptions is not None,"partial root adoption file required")
        result=build(base,engine.safe(args.adoptions),roster,args.output_name,args.proposal_name)
    else:
        result=verify(base,roster,args.output_name)
    print(json.dumps({key:value for key,value in result.items()
                      if key in {"status","counts","recovery_outcomes","partial_resolution"}}),flush=True)


if __name__=="__main__":
    main()
