#!/usr/bin/env python3
"""Full CPU proposal ledger and independent review packets; no cache admission.

The frozen parent scan supplies original text. Every previous HOLD position is
accounted for, even if it duplicates another position. The new ledger omits bulk
text, while deterministic unique-text packets include actual original/proposal
pairs for text-only reviewers. KEEP/EDIT here are proposals, not usable tokens.
"""
from __future__ import annotations

import argparse
from collections import Counter
import heapq
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_recovery as recovery
from scripts import p106b_hold_policy as policy
from scripts import p106b_corpus_cache as cache
from scripts.p106b_native_text_audit import file_sha, write_json
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_source_cleanup import sha, safe

SCHEMA="P106B_FULL_HOLD_PROPOSALS_V1_NOT_ADMISSION"


def require(value,message):
    if not value:raise ValueError(message)


def proposal_event(record):
    return dict(reasons=record["previous_reasons"],previous_holds=record.get("previous_holds",[]),
        manual_hold="PREVIOUS_INDIVIDUAL_HOLD" in record["features"]["flags"])


def signature(result,record):
    if result["decision"]=="HOLD":kind=result["reasons"][0]
    elif result["decision"]=="EDIT":
        kind="+".join(sorted({x["reason"] for x in result["changes"]})) or "NORMALIZATION_OUTSIDE_CODE"
    else:kind="BODY_UNCHANGED"
    return "/".join([result["decision"],kind,record["features"]["language_bucket"]])


def pin(base):
    inventory=cache.read(base/"inventory.json")
    value=dict(parent_built_sha256=file_sha(recovery.OLD_CACHE/"built.json"),
        parent_verified_sha256=file_sha(recovery.OLD_CACHE/"verified.json"),
        inventory_sha256=file_sha(base/"inventory.json"),scope_sha256=file_sha(base/"scope.json"),
        inventory_source_sha256=file_sha(ROOT/"scripts/p106b_hold_recovery.py"),
        policy_source_sha256=file_sha(ROOT/"scripts/p106b_hold_policy.py"),
        proposal_source_sha256=file_sha(Path(__file__)),rules=policy.RULES)
    for key in ["parent_built_sha256","parent_verified_sha256","scope_sha256","inventory_source_sha256"]:
        require(inventory["pin"][key]==value[key],"frozen inventory parent/code differs: "+key)
    return inventory,value


def full(base=recovery.BASE,name="proposals_v1",each=6):
    base=safe(base);inventory,identity=pin(base)
    require(name.isascii() and name.replace("_","").isalnum(),"safe new proposal namespace required")
    require(1<=each<=40,"bounded unique review packet strata required")
    out=base/name;require(not out.exists(),"write-once proposal namespace exists")
    out.mkdir();write_json(out/"started.json",dict(schema=SCHEMA,pin=identity,status="NOT_COMPLETE"))
    writer=ShardWriter(out/"ledger","proposals",limit=recovery.LIMIT)
    counts=Counter();by_reason=Counter();by_stratum=Counter();sources={};samples={};unique=set()
    initial=cache.read(base/"packets_initial_v2/manifest.json")
    previously_read={r["original_text_sha256"] for r in initial["rows"]}
    chosen_hashes=set();started=last=time.monotonic()
    for raw in inventory["units"]:
        stamp_path=ROOT/raw;stamp=cache.read(stamp_path)
        verify(stamp_path.parent/"records",stamp["manifest"])
        records={r["id"]:r for r in cache.rows(stamp_path.parent/"records",stamp["manifest"])}
        require(records,"HOLD inventory unit has no records")
        parent_path=ROOT/next(iter(records.values()))["source_unit"]
        parent=cache.read(parent_path);verify(parent_path.parent/"records",parent["manifest"])
        visited=set()
        for row in cache.rows(parent_path.parent/"records",parent["manifest"]):
            record=records.get(row["id"])
            if record is None:continue
            require(row["source_ids_sha256"]==record["source_ids_sha256"] and
                row["original_text_sha256"]==record["original_text_sha256"],"proposal source linkage differs")
            result=policy.propose(row,proposal_event(record));key=signature(result,record)
            event={k:record[k] for k in ["id","source","split","ordinal","source_ids","source_ids_sha256",
                    "original_text_sha256","input_ids"]}
            event.update(previous_decision="HOLD",proposal=result["decision"],reasons=result["reasons"],
                changes=result["changes"],clean_text_sha256=sha(result["text"]) if row["valid_utf8"] else None,
                family=record["features"]["family"],language_bucket=record["features"]["language_bucket"],
                review_stratum=key,rules=policy.RULES,training_admission="NOT_ADMITTED")
            writer.append(event);visited.add(row["id"]);unique.add(row["original_text_sha256"])
            counts.update(documents=1,input_ids=row["input_ids"],**{result["decision"]:1})
            counts[result["decision"]+"_input_ids"]+=row["input_ids"]
            source=sources.setdefault(row["source"],Counter());source.update(documents=1,**{result["decision"]:1})
            by_reason.update(result["reasons"]);by_stratum.update([key])
            fingerprint=row["original_text_sha256"]
            if fingerprint and fingerprint not in previously_read and fingerprint not in chosen_hashes:
                chosen_hashes.add(fingerprint)
                heap=samples.setdefault(key,[]);score=-int(fingerprint,16)
                entry=(score,row["id"],dict(event,original_text=row["text"],proposed_text=result["text"]))
                if len(heap)<each:heapq.heappush(heap,entry)
                elif entry[:2]>heap[0][:2]:heapq.heapreplace(heap,entry)
        require(len(visited)==len(records),"unprocessed HOLD positions in proposal unit")
        if time.monotonic()-last>=20:
            import json
            print(json.dumps(dict(phase="full_hold_proposals",counts=dict(counts),seconds=round(time.monotonic()-started,1))),flush=True)
            last=time.monotonic()
    require(counts["documents"]==inventory["counts"]["documents"] and
        counts["input_ids"]==inventory["counts"]["input_ids"] and
        sum(counts[k] for k in ["KEEP","EDIT","HOLD"])==counts["documents"],"full HOLD conservation differs")
    manifest=writer.close(lineage=identity);verify(out/"ledger",manifest)
    packet_dir=out/"review_packets";packet_dir.mkdir();catalog=[]
    ordered=sorted((entry[2] for heap in samples.values() for entry in heap),key=lambda r:(r["review_stratum"],r["id"]))
    for i,event in enumerate(ordered):
        stem=event["id"].replace(":","_");paths={}
        for kind in ["original","proposed"]:
            path=packet_dir/(stem+"_"+kind+".txt");body=event.pop(kind+"_text")
            require(len(body.encode("utf-8"))<20_000_000,"single packet exceeds byte contract")
            with path.open("x",encoding="utf-8",newline="") as stream:stream.write(body)
            paths[kind+"_path"]=str(path.relative_to(ROOT))
        catalog.append(dict(**event,**paths,role=recovery.ROLE_NAMES[i%5]))
    packet_report=dict(schema=SCHEMA,purpose="INDEPENDENT_STRATIFIED_PROPOSAL_CONTEXT_NOT_PREVALENCE",
        each=each,rows=catalog,unique_texts=len(catalog),initial_172_excluded=True)
    write_json(packet_dir/"manifest.json",packet_report)
    require(pin(base)[1]==identity,"frozen policy/parent changed during full proposal census")
    report=dict(schema=SCHEMA,pin=identity,counts=dict(counts),unique_original_texts=len(unique),
        sources={k:dict(v) for k,v in sources.items()},reasons=dict(by_reason),reasons_may_overlap=True,
        strata=dict(by_stratum),manifest=manifest,review_packets=len(catalog),unprocessed=0,
        actual_cache_created=False,training_authorized=False,seconds=time.monotonic()-started)
    write_json(out/"complete.json",report)
    import json
    print(json.dumps({k:report[k] for k in ["counts","review_packets","unprocessed","actual_cache_created","seconds"]}),flush=True)
    return report


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",
        OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base",type=Path,default=recovery.BASE);p.add_argument("--name",default="proposals_v1")
    p.add_argument("--each",type=int,default=6);a=p.parse_args();full(a.base,a.name,a.each)


if __name__=="__main__":main()
