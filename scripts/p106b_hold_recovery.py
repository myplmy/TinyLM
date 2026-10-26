#!/usr/bin/env python3
"""CPU-only, source-linked review and recovery of the previous HOLD roster.

Inventory labels are review families, never automatic admission or false-fact
judgments. Previous text, caches, source code and decisions remain immutable.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
import hashlib
import heapq
import json
import mmap
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_corpus_cleanup as corpus
from scripts import p106b_corpus_cache as cache
from scripts import p106b_native_format_candidate as fmt
from scripts.p106b_native_text_audit import HEADINGS, normalize_heading, signals, write_json, file_sha
from scripts.p106b_source_cleanup import FENCE, safe, sha
from scripts.p106b_shards import ShardWriter, verify

BASE=ROOT/"data_cache/p106b_hold_recovery_v1_20261026_goalc"
PARENT=corpus.BASE
OLD_CACHE=PARENT/"cache_v1"
OLD_ADOPTIONS=ROOT/"handoff/audit/source_cleanup_20261026_goalc/root_adoptions_v1.json"
SCHEMA="P106B_HOLD_RECOVERY_V1"
INVENTORY_RULES="HOLD_FAMILY_INVENTORY_V1_NOT_ADMISSION"
LIMIT=19_999_999
EXTRA_SECTIONS={"사진","갤러리","기후","인구","통계","인접역","인접 역","승강장",
    "수상 경력","수상경력","타격 성적","수비 성적","참가팀","순위","대진표","경기 결과",
    "선수 명단","선수단","연기한 배우","통산 기록","통산기록"}
SECTION_NAMES={normalize_heading(x) for x in HEADINGS|fmt.OUTLINE|EXTRA_SECTIONS}
FORMAT_HEADINGS={normalize_heading(x) for x in HEADINGS}
OUTLINE_NAMES={normalize_heading(x) for x in fmt.OUTLINE}
MISSING_AFTER_OPEN=re.compile(r"[（(]\s*[,，;]")
ROLE_NAMES=["context_hangul","context_latin","historical_review","legacy_review","context_controls"]


def require(ok,message):
    if not ok:raise ValueError(message)


def family_features(row,event,manual_holds):
    text=row["text"]
    plain="".join(FENCE.split(text)[::2])
    lines=[x.strip() for x in plain.splitlines() if x.strip()]
    reasons=event["reasons"]
    flags=[]
    if not row["complete_eos"] or not row["valid_utf8"] or row["id"]=="validation:0":
        flags.append("INCOMPLETE_OR_UNKNOWN_BOUNDARY")
    if row["original_text_sha256"] in manual_holds or row["candidate_text_sha256"] in manual_holds:
        flags.append("PREVIOUS_INDIVIDUAL_HOLD")
    if event.get("previous_holds") or "PRESERVED_PREVIOUS_EXPLICIT_HOLD" in reasons:
        flags.append("PREVIOUS_EXPLICIT_HOLD")
    flags.extend(cache.independent_control_risks(text))
    if MISSING_AFTER_OPEN.search(plain):flags.append("MISSING_OPENING_NAME_OR_TERM")
    if corpus.open_fence(text):flags.append("OPEN_CODE_FENCE")
    if corpus.BROKEN.search(plain) or "[[" in plain or "{{" in plain:
        flags.append("BROKEN_TABLE_OR_WIKI_MARKUP")
    if corpus.UI.search(plain):flags.append("COMMERCIAL_UI")
    labels=[normalize_heading(x) for x in lines]
    empty=[]
    for i,label in enumerate(labels):
        if label not in SECTION_NAMES:continue
        if i+1==len(labels) or labels[i+1] in SECTION_NAMES:
            # Already-authorized empty terminal format labels are described
            # separately, not mistaken for missing internal table content.
            suffix=all(x in FORMAT_HEADINGS for x in labels[i:])
            if not suffix:empty.append(lines[i])
    if empty:flags.append("EMPTY_INTERNAL_OR_STRUCTURED_SECTION")
    info=row["original_signals"]
    if flags:
        if "INCOMPLETE_OR_UNKNOWN_BOUNDARY" in flags:family="BOUNDARY_FRAGMENT"
        elif any(x.startswith("PREVIOUS_") for x in flags):family="PREVIOUS_INDIVIDUAL_OR_EXPLICIT"
        elif any(x.startswith("MISSING_") or x=="EMPTY_INTERNAL_OR_STRUCTURED_SECTION" for x in flags):family="MISSING_FIELDS_OR_SECTIONS"
        else:family="MARKUP_UI_OR_CODE_REVIEW"
    elif info.get("html_tag_occurrences") or info.get("html_comment_openers"):
        family="MARKUP_OR_TRANSCRIPTION"
    elif info.get("within_doc_repeated_line_extras"):family="REPETITION_WITH_CONTEXT"
    elif any(x in OUTLINE_NAMES for x in labels) or info.get("explicit_category_lines"):
        family="LIST_OR_CATEGORY_WITH_CONTEXT"
    elif info.get("standalone_heading_lines"):family="REFERENCE_OR_APPENDIX_WITH_CONTENT"
    else:family="OTHER_CONTEXT"
    return dict(family=family,flags=sorted(set(flags)),empty_sections=empty,
        nonempty_lines=len(lines),characters=len(text),original_signals=info,
        language_bucket=row["language_bucket"],language_proxy=row["language_proxy"])


def inventory(base=BASE):
    base=safe(base);base.mkdir(parents=True,exist_ok=True)
    require(not (base/"inventory.json").exists(),"inventory complete already; use its manifest")
    parent=cache.read(OLD_CACHE/"built.json");proven=cache.read(OLD_CACHE/"verified.json")
    require(proven.get("every_adopted_document_regenerated") is True,"verified parent required")
    scope=cache.read(PARENT/"scope.json")
    pin=dict(parent_built_sha256=file_sha(OLD_CACHE/"built.json"),
        parent_verified_sha256=file_sha(OLD_CACHE/"verified.json"),scope_sha256=file_sha(PARENT/"scope.json"),
        old_adoptions_sha256=file_sha(OLD_ADOPTIONS),inventory_source_sha256=file_sha(Path(__file__)))
    verify(OLD_CACHE/"hold",parent["manifests"]["hold"])
    holds={}
    for event in cache.rows(OLD_CACHE/"hold",parent["manifests"]["hold"]):
        require(event["decision"]=="HOLD" and event["id"] not in holds,"parent HOLD IDs differ")
        holds[event["id"]]=event
    require(len(holds)==parent["counts"]["HOLD"],"parent HOLD count differs")
    manual={x["input_text_sha256"] for x in cache.read(OLD_ADOPTIONS)["rows"] if x["decision"]=="HOLD"}
    if not (base/"scope.json").exists():write_json(base/"scope.json",scope)
    totals=Counter();families=Counter();flags=Counter();sources={};unique=set();units=[]
    start=last=time.monotonic()
    for source in scope["inputs"]:
        source_counts=Counter();cursor=ordinal=0
        for stamp in sorted((PARENT/"scan"/source["name"]).glob("unit_*/complete.json")):
            old=cache.read(stamp);directory=base/"inventory"/source["name"]/stamp.parent.name
            require(old["start_ids"]==cursor and old["start_ordinal"]==ordinal,"parent scan has gaps")
            cursor,ordinal=old["end_ids"],old["end_ordinal"]
            if (directory/"complete.json").exists():
                complete=cache.read(directory/"complete.json")
                require(complete["pin"]==pin,"resumed inventory source differs")
                verify(directory/"records",complete["manifest"])
            else:
                verify(stamp.parent/"records",old["manifest"])
                writer=ShardWriter(directory/"records","holds",limit=LIMIT)
                local=Counter();by_family=Counter();by_flag=Counter()
                for row in cache.rows(stamp.parent/"records",old["manifest"]):
                    event=holds.get(row["id"])
                    if event is None:continue
                    require(row["original_text_sha256"]==event["original_text_sha256"]
                        and row["source_ids_sha256"]==event["source_ids_sha256"],"parent HOLD/source link differs")
                    features=family_features(row,event,manual)
                    record={k:row[k] for k in ["id","source","split","ordinal","source_ids",
                        "source_ids_sha256","original_text_sha256","candidate_text_sha256","input_ids","complete_eos","valid_utf8"]}
                    record.update(previous_decision="HOLD",previous_reasons=event["reasons"],
                        previous_holds=event.get("previous_holds",[]),features=features,
                        rules=INVENTORY_RULES,source_unit=str(stamp.relative_to(ROOT)),recovery_decision="NOT_REVIEWED")
                    writer.append(record);local.update(documents=1,input_ids=row["input_ids"])
                    by_family.update([features["family"]+"/"+features["language_bucket"]]);by_flag.update(features["flags"])
                require(local["documents"]>0,"empty parent HOLD unit unexpected")
                manifest=writer.close(lineage=pin)
                complete=dict(pin=pin,manifest=manifest,counts=dict(local),families=dict(by_family),flags=dict(by_flag))
                write_json(directory/"complete.json",complete)
            units.append(str((directory/"complete.json").relative_to(ROOT)))
            totals.update(complete["counts"]);source_counts.update(complete["counts"])
            families.update(complete["families"]);flags.update(complete["flags"])
            for record in cache.rows(directory/"records",complete["manifest"]):unique.add(record["original_text_sha256"])
            if time.monotonic()-last>=20:
                print(json.dumps(dict(phase="hold_inventory",counts=dict(totals),source=source["name"],seconds=round(time.monotonic()-start,1))),flush=True);last=time.monotonic()
        require(cursor==source["ids"] and ordinal==source["intervals"],"full parent scan missing")
        sources[source["name"]]=dict(source_counts)
    require(totals["documents"]==parent["counts"]["HOLD"] and totals["input_ids"]==parent["counts"]["HOLD_input_ids"],"full HOLD conservation differs")
    require(file_sha(Path(__file__))==pin["inventory_source_sha256"],"inventory code changed during execution")
    report=dict(schema=SCHEMA,pin=pin,counts=dict(totals),unique_original_texts=len(unique),
        sources=sources,families=dict(families),flags=dict(flags),flag_counts_may_overlap=True,
        units=units,full_parent_hold_coverage=True,unprocessed=0,admission="NOT_REVIEWED",
        training_authorized=False,seconds=time.monotonic()-start)
    write_json(base/"inventory.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ["units","pin"]},ensure_ascii=False),flush=True)
    return report


def inventory_rows(base=BASE):
    report=cache.read(base/"inventory.json")
    for raw in report["units"]:
        p=ROOT/raw;stamp=cache.read(p)
        yield from cache.rows(p.parent/"records",stamp["manifest"])


def packets(base=BASE,each=8,name="packets_initial"):
    base=safe(base);out=base/name
    require(name.isascii() and name.replace("_", "").isalnum() and not out.exists(),"new safe packet namespace required")
    samples={};seen=set()
    for row in inventory_rows(base):
        key=row["features"]["family"]+"/"+row["features"]["language_bucket"]
        fingerprint=(key,row["original_text_sha256"])
        if fingerprint in seen:continue
        seen.add(fingerprint)
        heap=samples.setdefault(key,[])
        number=int(row["original_text_sha256"],16)
        entry=(-number,row["id"],row)
        if len(heap)<each:heapq.heappush(heap,entry)
        elif entry[:2]>heap[0][:2]:heapq.heapreplace(heap,entry)
    chosen={}
    for heap in samples.values():
        for _,_,row in heap:chosen[row["original_text_sha256"]]=row
    out.mkdir()
    scope=cache.read(PARENT/"scope.json");codec=cache.native.ByteCodec(cache.read(ROOT/scope["tokenizer"]["path"]))
    catalog=[]
    for index,row in enumerate(sorted(chosen.values(),key=lambda r:(r["features"]["family"],r["id"]))):
        spec=next(s for s in scope["inputs"] if s["name"]==row["source"])
        lo,hi=row["source_ids"]
        with (ROOT/spec["path"]).open("rb") as stream:
            stream.seek(lo*2);raw=stream.read((hi-lo)*2)
        require(hashlib.sha256(raw).hexdigest().upper()==row["source_ids_sha256"],"packet source interval SHA differs")
        values=array("H");values.frombytes(raw)
        if sys.byteorder!="little":values.byteswap()
        text,_=codec.text(values[:-1] if row["complete_eos"] else values)
        require(sha(text)==row["original_text_sha256"],"packet original text SHA differs")
        filename=row["id"].replace(":","_")+".txt";path=out/filename
        with path.open("x",encoding="utf-8",newline="") as stream:stream.write(text)
        catalog.append(dict(**row,path=str(path.relative_to(ROOT)),sha256=file_sha(path),role=ROLE_NAMES[index%5]))
    manifest=dict(schema=SCHEMA,purpose="STRATIFIED_CONTEXT_REVIEW_NOT_PREVALENCE",rows=catalog,
                  unique_texts=len(catalog),each_stratum=each,training_authorized=False)
    write_json(out/"manifest.json",manifest)
    print(json.dumps(dict(packets=len(catalog),roles=dict(Counter(x["role"] for x in catalog)))),flush=True)
    return manifest


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["inventory","packets"])
    p.add_argument("--base",type=Path,default=BASE)
    p.add_argument("--each",type=int,default=8)
    p.add_argument("--name",default="packets_initial")
    a=p.parse_args()
    if a.command=="inventory":inventory(a.base)
    else:
        require(1<=a.each<=100,"packet stratum request out of bounds")
        packets(a.base,a.each,a.name)
    return 0


if __name__=="__main__":raise SystemExit(main())
