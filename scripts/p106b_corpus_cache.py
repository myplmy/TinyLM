#!/usr/bin/env python3
"""Build and independently regenerate sharded native text/token derivatives.

The source inventory and full ordered scan must exist. Manual overrides name
real text artifacts reviewed by the coordinator. Unresolved HOLD never enters
either split. This does not authorize training or claim URL-level decontamination.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import p106b_corpus_cleanup as corpus
from scripts import diag_p106b_native_expansion as native
from scripts import p106b_native_format_pair as pair
from scripts.p106b_native_text_audit import file_sha, signals, write_json
from scripts.p106b_source_cleanup import safe, sha
from scripts.p106b_shards import ShardWriter, verify

SCHEMA="P106B_CLEAN_NATIVE_CACHE_V1"
LIMIT=19_999_999
HOLDS=ROOT/"handoff/audit/oct26_research/native_format_holds.json"
HOLD_SHA="B7F08AB4478118D4BD47539B420372EF0F09742563483CA794D743B8CB4B5478"
SECONDARY_RULES="INDEPENDENT_CONTROL_READBACK_V2"
MISSING_FIELD=re.compile(r"\(\s*\)|《\s*》|\(\s*←\s*[,)]")
PAGE_UI=re.compile(r"(?mi)^\s*(?:subscribe to our newsletter|return to homepage|file last updated\b|this news release is available in\b|go to our previous news item\b|latest posts by\b|leave a comment\b)")


def independent_control_risks(text):
    # Added after text-only independent controls found concrete missed fields
    # and newsletter UI. They are HOLD candidates, never automatic deletions.
    plain="".join(corpus.FENCE.split(text)[::2])
    reasons=[]
    if MISSING_FIELD.search(plain):reasons.append("MISSING_PARENTHETICAL_OR_TITLE_CONTEXT")
    if PAGE_UI.search(plain):reasons.append("PAGE_NAVIGATION_OR_SUBSCRIPTION_CONTEXT")
    if "_x000D_" in plain:reasons.append("ESCAPED_EXTRACTION_NEWLINE_CONTEXT")
    if re.search(r"(?mi)^\s*참조\s*$",plain):reasons.append("REFERENCE_HEADING_CONTEXT")
    return reasons


def protected_code_changed(original,cleaned):
    return corpus.FENCE.findall(original)!=corpus.FENCE.findall(cleaned)


def code_preserved(original,cleaned,manual=None):
    if not protected_code_changed(original,cleaned):return True
    decorative="~~~~~~~~~~ 0 ~~~~~~~~~~"
    if (manual and manual.get("decorative_rule_removed")==decorative
            and original.count(decorative)==1 and decorative not in cleaned):
        return not protected_code_changed(original.replace(decorative,"",1),cleaned)
    return False


def require(ok,message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(directory,manifest):
    for spec in manifest["shards"]:
        with (directory/spec["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                yield json.loads(line)


class TokenWriter:
    """Keep each EOS document in one <=19,999,998 byte little-endian shard."""
    def __init__(self,directory,limit=19_999_998):
        require(type(limit) is int and 2<=limit<20_000_000 and limit%2==0,"uint16 shard limit required")
        self.directory,self.limit=directory,limit
        directory.mkdir(parents=True,exist_ok=False)
        self.stream=None
        self.specs=[]
        self.global_ids=self.local_bytes=0
        self.whole=hashlib.sha256()

    def finish(self):
        if self.stream is not None:
            self.stream.flush();self.stream.close()
            self.specs.append(dict(path=Path(self.stream.name).name,bytes=self.local_bytes,
                ids=self.local_bytes//2,first_id=self.global_ids-self.local_bytes//2,
                sha256=self.digest.hexdigest().upper()))
            self.stream=None

    def append(self,data):
        require(data and len(data)%2==0 and len(data)<=self.limit,"complete bounded uint16 document required")
        if self.stream is not None and self.local_bytes+len(data)>self.limit:
            self.finish()
        if self.stream is None:
            self.stream=(self.directory/f"tokens_{len(self.specs):06d}.bin").open("xb")
            self.local_bytes=0;self.digest=hashlib.sha256()
        result=dict(shard=Path(self.stream.name).name,local_id=self.local_bytes//2,
                    offset_ids=self.global_ids,ids=len(data)//2,ids_sha256=hashlib.sha256(data).hexdigest().upper())
        self.stream.write(data);self.digest.update(data);self.whole.update(data)
        self.local_bytes+=len(data);self.global_ids+=len(data)//2
        return result

    def close(self):
        self.finish()
        require(self.global_ids>0,"empty accepted cache is not success")
        value=dict(schema=SCHEMA,token_dtype="uint16",byte_order="little",eos_id=2,
            ids=self.global_ids,bytes=self.global_ids*2,limit_bytes=self.limit,
            concat_sha256=self.whole.hexdigest().upper(),shards=self.specs)
        write_json(self.directory/"manifest.json",value)
        return value


class ShardedTokens:
    """Read-only global slices for CPU cache consumers; no model integration."""
    def __init__(self,directory,manifest=None):
        import numpy as np
        self.directory=Path(directory)
        self.manifest=manifest or read(self.directory/"manifest.json")
        self.arrays=[np.memmap(self.directory/s["path"],dtype="<u2",mode="r") for s in self.manifest["shards"]]

    def __len__(self):
        return self.manifest["ids"]

    def __getitem__(self,item):
        import numpy as np
        if isinstance(item,int):
            position=item if item>=0 else len(self)+item
            if position<0 or position>=len(self):
                raise IndexError(position)
            return int(self[position:position+1][0])
        start,stop,step=item.indices(len(self))
        require(step==1,"only contiguous cache windows are supported")
        if stop<=start:
            return np.array([],dtype="<u2")
        pieces=[]
        for spec,values in zip(self.manifest["shards"],self.arrays):
            lo,hi=spec["first_id"],spec["first_id"]+spec["ids"]
            if start<hi and stop>lo:
                pieces.append(values[max(0,start-lo):min(len(values),stop-lo)])
        return np.concatenate(pieces)


def scan_coverage(base,scope):
    before=Counter();proxies=Counter();summaries={}
    for source in scope["inputs"]:
        cursor=ordinal=0;counts=Counter();local=Counter()
        for stamp in sorted((base/"scan"/source["name"]).glob("unit_*/complete.json")):
            info=read(stamp)
            require(info["start_ids"]==cursor and info["start_ordinal"]==ordinal
                and info["source_sha256"]==source["sha256"],"full scan chain has a gap or overlap")
            verify(stamp.parent/"records",info["manifest"])
            cursor,ordinal=info["end_ids"],info["end_ordinal"]
            counts.update(info["counts"]);before.update(info["before_signals"])
            local.update(info["before_proxy"]);proxies.update(info["before_proxy"])
        require(cursor==source["ids"] and ordinal==source["intervals"],"full target is not scanned")
        require(counts["KEEP"]+counts["EDIT"]+counts["HOLD"]==ordinal,"initial scan decision conservation failed")
        summaries[source["name"]]=dict(counts=counts,language_proxy=local)
    return dict(sources=summaries,before_signals=dict(before),before_proxy=dict(proxies))


def manual_overrides(base,path):
    document=read(path)
    require(document.get("schema")=="P106B_ROOT_TEXT_ADOPTIONS_V1","root adoptions manifest required")
    result={}
    for row in document["rows"]:
        key=row["input_text_sha256"]
        require(key not in result and row["decision"] in ["KEEP","EDIT","HOLD"]
            and row.get("root_reviewed") is True and row.get("reason"),"unique coordinator-reviewed text decision required")
        value=dict(row)
        if row["decision"]=="EDIT":
            target=safe(ROOT/row["path"])
            require(target.is_relative_to(base/"agents") and target.suffix==".txt"
                and file_sha(target)==row["sha256"],"manual text artifact differs")
            text=target.read_text(encoding="utf-8")
            require(text.strip() and (not corpus.MEMOS.search(text)),"editor memo or empty output in manual training body")
            value["text"]=text
        result[key]=value
    return document,result


def choose(row,overrides,known_hold=False):
    text=row["text"]
    candidate,removed,_,_=corpus.propose(text)
    matched=row["original_text_sha256"] if row["original_text_sha256"] in overrides else row["candidate_text_sha256"]
    override=overrides.get(matched)
    if not row["complete_eos"] or not row["valid_utf8"] or (row["split"]=="val" and row["ordinal"]==0):
        return "HOLD",text,list(row["review_reasons"]),None
    if known_hold and not (override and override.get("resolves_inherited_hold") is True):
        return "HOLD",text,["PRESERVED_PREVIOUS_EXPLICIT_HOLD"],None
    if override:
        decision=override["decision"]
        final=override["text"] if decision=="EDIT" else candidate if decision=="KEEP" else text
        if decision=="KEEP" and final!=text:
            decision="EDIT"
        return decision,final,[override["reason"]],dict(input_match_sha256=matched,reference=override["review"],
            decorative_rule_removed=override.get("decorative_rule_removed"))
    if row["automatic_decision"]=="HOLD":
        return "HOLD",text,row["review_reasons"],None
    secondary=independent_control_risks(text)
    if secondary:
        return "HOLD",text,secondary,None
    return row["automatic_decision"],candidate,["EXISTING_EMPTY_TERMINAL_HEADINGS_OR_NFC"] if candidate!=text else ["NO_REVIEW_RISK_SIGNAL_EXACT_BODY_PRESERVED"],None


def span_hashes(data,*,width=256,stride=128):
    # This explicitly measures token-aligned fixed-stride overlap, not arbitrary
    # near-duplicates, semantic similarity or original URL identity.
    for position in range(0,len(data)-width*2+1,stride*2):
        yield position//2,hashlib.sha256(data[position:position+width*2]).digest()


def build(base,adoptions_path,output_name="cache_v1"):
    base=safe(base);scope=read(base/"scope.json")
    require(output_name.isascii() and output_name.replace("_", "").isalnum(),"safe output version required")
    out=base/output_name
    require(not out.exists(),"cache namespace is write-once; resume from completed scan, choose new cache version")
    code_names=["scripts/p106b_corpus_cache.py","scripts/p106b_corpus_cleanup.py",
        "scripts/p106b_native_format_candidate.py","scripts/p106b_native_text_audit.py",
        "scripts/p106b_source_cleanup.py","scripts/p106b_shards.py",
        "scripts/diag_p106b_native_expansion.py","scripts/p106b_native_format_pair.py"]
    # Synthetic isolated fixtures patch ROOT; their source is still this module's
    # actual repository, while all fixture data remain in their temporary root.
    code_root=Path(__file__).resolve().parents[1]
    code_pin={name:file_sha(code_root/name) for name in code_names}
    adoption_pin=file_sha(adoptions_path)
    preflight=scan_coverage(base,scope)
    for source in scope["inputs"]:
        require(file_sha(ROOT/source["path"])==source["sha256"]
            and file_sha(ROOT/source["metadata"])==source["metadata_sha256"],"input or metadata changed")
    tok=scope["tokenizer"]
    require(file_sha(ROOT/tok["path"])==tok["sha256"],"tokenizer identity changed")
    codec=native.ByteCodec(read(ROOT/tok["path"]))
    adoption_document,overrides=manual_overrides(base,adoptions_path)
    require(file_sha(HOLDS)==HOLD_SHA,"previous explicit HOLD roster changed")
    old=read(HOLDS);inherited=pair.Holds(old,old["source_sha256"])
    held_sha={r.get("original_text_sha256") for r in old["holds"]}
    out.mkdir()
    write_json(out/"started.json",dict(schema=SCHEMA,scope_sha256=file_sha(base/"scope.json"),
        adoptions_sha256=adoption_pin,source_code_sha256=code_pin,status="NOT_COMPLETE",rules=corpus.RULES))
    ledger=ShardWriter(out/"ledger","decisions",limit=LIMIT)
    holds=ShardWriter(out/"hold","positions",limit=LIMIT)
    accepted={split:ShardWriter(out/"text"/split,"documents",limit=LIMIT) for split in ("val","train")}
    tokens={split:TokenWriter(out/"tokens"/split) for split in ("val","train")}
    counts=Counter();sources={s["name"]:Counter() for s in scope["inputs"]}
    body_counts={s:Counter() for s in ("val","train")}
    after={s:Counter() for s in ("val","train")};proxies={s:Counter() for s in ("val","train")}
    same_before={s:Counter() for s in ("val","train")}
    same_before_proxy={s:Counter() for s in ("val","train")}
    same_before_counts={s:Counter() for s in ("val","train")}
    all_signal_documents=Counter();accepted_signal_documents={s:Counter() for s in ("val","train")}
    languages={s:Counter() for s in ("val","train")}
    raw_unique=set();unique_before_ids=0;seen={"val":{},"train":{}}
    val_text=set();val_spans={};adoption_hits=Counter();reason_counts=Counter()
    start_time=last_print=time.monotonic()
    with ExitStack() as stack:
        maps={}
        for source in scope["inputs"]:
            stream=stack.enter_context((ROOT/source["path"]).open("rb"))
            maps[source["name"]]=stack.enter_context(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
        val_source=next(s for s in scope["inputs"] if s["split"]=="val")
        val_raw=maps[val_source["name"]][:]
        raw_values=array("H");raw_values.frombytes(val_raw)
        if sys.byteorder!="little":raw_values.byteswap()
        val_index=native.build_val_index(iter(raw_values),pair.pair_for_val(codec,len(codec.pieces)))
        # Preserve both old validation content and the newly adopted content as
        # exclusion references; excluded validation rows are not promoted to train.
        for row in corpus.iter_scan(base,val_source["name"]):
            if row["original_text_sha256"]:
                val_text.add(bytes.fromhex(row["original_text_sha256"]))
            lo,hi=row["source_ids"]
            for position,digest in span_hashes(val_raw[lo*2:hi*2]):
                val_spans.setdefault(digest,dict(id=row["id"],local_id=position,kind="ORIGINAL_VALIDATION_256_IDS_STRIDE128"))
        source_order=[val_source]+[s for s in scope["inputs"] if s["split"]=="train"]
        for source in source_order:
            cursor=ordinal=0
            for row in corpus.iter_scan(base,source["name"]):
                lo,hi=row["source_ids"]
                require(lo==cursor and row["ordinal"]==ordinal,"scan ledger cursor differs")
                cursor,ordinal=hi,ordinal+1
                raw=maps[source["name"]][lo*2:hi*2]
                require(hashlib.sha256(raw).hexdigest().upper()==row["source_ids_sha256"],"original interval SHA differs")
                key=bytes.fromhex(row["original_text_sha256"]) if row["original_text_sha256"] else None
                original_signals=row.get("original_signals")
                if original_signals is None:original_signals=signals(row["text"])[0]
                all_signal_documents.update(original_signals.keys())
                if key is not None and key not in raw_unique:
                    raw_unique.add(key);unique_before_ids+=row["input_ids"]-int(row["complete_eos"])
                explicit=[]
                if source["name"]=="expanded_train":
                    explicit=inherited.match(dict(eos_segment_index=row["ordinal"],cache_segment_ids=[lo,hi-1],
                                                 original_text_sha256=row["original_text_sha256"]))
                known=bool(explicit) or row["original_text_sha256"] in held_sha
                decision,text,reasons,manual=choose(row,overrides,known)
                data=None;leak=None;duplicate=None
                if decision in ("KEEP","EDIT") and not code_preserved(row["text"],text,manual):
                    decision="HOLD";reasons=["PROTECTED_CODE_BYTES_CHANGED_REVIEW_REQUIRED"]
                if decision in ("KEEP","EDIT"):
                    if text==row["text"]:
                        data=raw;mode="SOURCE_SLICE"
                    else:
                        ids=codec.backend.encode(text,add_special_tokens=False).ids
                        restored,body=codec.text(ids)
                        require(restored==text and body==text.encode("utf-8")
                            and not any(v in codec.specials for v in ids),"modified text serialization changed content or reserved tokens")
                        data=native.ids_bytes(ids+[2]);mode="ENCODE_CLEAN_TEXT"
                    require(data[-2:]==b"\x02\x00","accepted document must end in EOS2")
                    text_key=bytes.fromhex(sha(text))
                    if source["split"]=="train":
                        original_ids=array("H");original_ids.frombytes(raw)
                        final_ids=array("H");final_ids.frombytes(data)
                        if sys.byteorder!="little":original_ids.byteswap();final_ids.byteswap()
                        old_hits,_=val_index.match(list(original_ids))
                        new_hits,_=val_index.match(list(final_ids))
                        if key in val_text or text_key in val_text or old_hits or new_hits:
                            leak=dict(kind="EXACT_VALIDATION_DOCUMENT_OR_NONEMPTY_BOUNDARY_SUBSTRING",
                                      original=old_hits,clean=new_hits)
                        if not leak:
                            for position,digest in span_hashes(data):
                                if digest in val_spans:
                                    leak=dict(kind="VALIDATION_TOKEN_SPAN_256_IDS_STRIDE128",local_id=position,
                                              validation=val_spans[digest]);break
                        if leak:
                            decision="EXCLUDE";reasons=["TRAIN_VAL_CONTENT_OVERLAP"]
                    if decision in ("KEEP","EDIT") and text_key in seen[source["split"]]:
                        decision="EXCLUDE";reasons=["EXACT_CLEAN_TEXT_DUPLICATE"]
                        duplicate=seen[source["split"]][text_key]
                    if decision in ("KEEP","EDIT"):
                        seen[source["split"]][text_key]=row["id"]
                        if source["split"]=="val":
                            val_text.add(text_key)
                            for position,digest in span_hashes(data):
                                val_spans.setdefault(digest,dict(id=row["id"],local_id=position,kind="CLEAN_VALIDATION_256_IDS_STRIDE128"))
                event=dict(id=row["id"],source=row["source"],split=row["split"],source_ids=row["source_ids"],
                    source_ids_sha256=row["source_ids_sha256"],original_text_sha256=row["original_text_sha256"],
                    input_ids=row["input_ids"],decision=decision,reasons=reasons,previous_holds=explicit,
                    clean_text_sha256=sha(text) if decision in ("KEEP","EDIT") else None,
                    rules=corpus.RULES,manual=manual,duplicate_of=duplicate,validation_overlap=leak)
                if decision in ("KEEP","EDIT"):
                    cache=tokens[source["split"]].append(data)
                    event["cache"]=cache;event["serialization_mode"]=mode
                    accepted[source["split"]].append(dict(**event,text=text,source_kind="UNKNOWN_MIXED_NATIVE_CACHE",
                        source_url=None,original_document_id=None,truth="NOT_FACT_CHECKED"))
                    info,_=signals(text)
                    after[source["split"]].update(info);proxies[source["split"]].update(corpus.proxy(text))
                    accepted_signal_documents[source["split"]].update(info.keys())
                    same_before[source["split"]].update(original_signals)
                    same_before_proxy[source["split"]].update(row.get("language_proxy") or corpus.proxy(row["text"]))
                    same_before_counts[source["split"]].update(documents=1,tokens=len(raw)//2,content_ids=len(raw)//2-1)
                    languages[source["split"]].update([corpus.language_bucket(text)])
                    body_counts[source["split"]].update(documents=1,tokens=len(data)//2,content_ids=len(data)//2-1)
                    counts["edited_content_ids_delta"]+=len(data)//2-len(raw)//2
                elif decision=="HOLD":
                    holds.append(event)
                ledger.append(event)
                counts.update(documents=1,input_ids=row["input_ids"],**{decision:1})
                counts[decision+"_input_ids"]+=row["input_ids"]
                sources[source["name"]].update(documents=1,input_ids=row["input_ids"],**{decision:1})
                sources[source["name"]][decision+"_input_ids"]+=row["input_ids"]
                reason_counts.update(reasons)
                if manual:
                    adoption_hits[manual["input_match_sha256"]]+=1
                if time.monotonic()-last_print>=20:
                    print(json.dumps(dict(phase="build",source=source["name"],documents=ordinal,
                        total_processed=counts["documents"],counts=dict(counts),elapsed_seconds=round(time.monotonic()-start_time,1))),flush=True)
                    last_print=time.monotonic()
            require(cursor==source["ids"] and ordinal==source["intervals"],"full input interval conservation differs")
    held_hits=inherited.complete()
    lineage=dict(scope_sha256=file_sha(base/"scope.json"),tokenizer_sha256=tok["sha256"],
                 adoptions_sha256=adoption_pin,rules=corpus.RULES,secondary_rules=SECONDARY_RULES)
    manifests={"ledger":ledger.close(lineage=lineage),"hold":holds.close(lineage=lineage)}
    for split in ("val","train"):
        manifests["text_"+split]=accepted[split].close(lineage=lineage)
        manifests["tokens_"+split]=tokens[split].close()
    report=dict(schema=SCHEMA,lineage=lineage,source_code_sha256=code_pin,input_scope=preflight,
        counts=dict(counts),sources={k:dict(v) for k,v in sources.items()},
        accepted={k:dict(v) for k,v in body_counts.items()},
        exact_unique_original_texts=len(raw_unique),exact_unique_original_content_ids=unique_before_ids,
        original_ids_are_not_training_exposure=True,stored_epochs=None,
        accepted_structure_signals={k:dict(v) for k,v in after.items()},
        original_documents_with_signal=dict(all_signal_documents),
        accepted_documents_with_signal={k:dict(v) for k,v in accepted_signal_documents.items()},
        same_adopted_roster_before=dict(counts={k:dict(v) for k,v in same_before_counts.items()},
            structure_signals={k:dict(v) for k,v in same_before.items()},
            language_proxy={k:dict(v) for k,v in same_before_proxy.items()}),
        accepted_language_proxy={k:dict(v) for k,v in proxies.items()},
        accepted_character_presence_buckets={k:dict(v) for k,v in languages.items()},
        source_kind="UNKNOWN_MIXED_NATIVE_CACHE",mixture_metadata_not_document_labels=True,
        manifests=manifests,previous_explicit_hold_entries_hit=len(held_hits),
        manual_adoption_hits=dict(adoption_hits),manual_reviews=adoption_document.get("reviews",[]),
        unmatched_manual_adoptions=sorted(set(overrides)-set(adoption_hits)),
        decision_reasons=dict(reason_counts),reason_counts_may_overlap=True,
        training_authorized=False,model_loads=0,gpu_calls=0,original_writes=0,
        global_original_article_leakage="UNVERIFIED_NO_ORIGINAL_DOCUMENT_IDS",
        overlap_check="exact text and complete EOS token hash; original validation split edges; 256-token windows at stride128",
        overlap_limit="unaligned shifted spans, near duplicates and source URL identity not established",
        semantic_review="INDEPENDENT_STRATIFIED_CONTEXT_REVIEW_PLUS_RULE_PROCESSING_NOT_ALL_FACT_VERIFICATION",
        full_target_processed=True,seconds=time.monotonic()-start_time)
    require(counts["documents"]==sum(s["intervals"] for s in scope["inputs"])
        and counts["KEEP"]+counts["EDIT"]+counts["HOLD"]+counts["EXCLUDE"]==counts["documents"],"final decision totals differ")
    for source in scope["inputs"]:
        require(file_sha(ROOT/source["path"])==source["sha256"],"original source changed during build")
    require(file_sha(adoptions_path)==adoption_pin and all(file_sha(code_root/name)==value for name,value in code_pin.items()),
        "adoptions or preprocessing source changed during frozen build")
    write_json(out/"built.json",report)
    return report


def verify_cache(base,output_name="cache_v1"):
    """Independent consumer: regenerate every accepted byte and check all rosters."""
    require(output_name.isascii() and output_name.replace("_", "").isalnum(),"safe output version required")
    base=safe(base);out=base/output_name;report=read(out/"built.json");scope=read(base/"scope.json")
    require(file_sha(base/"scope.json")==report["lineage"]["scope_sha256"],"scope changed")
    codec=native.ByteCodec(read(ROOT/scope["tokenizer"]["path"]))
    for key in ("ledger","hold","text_val","text_train"):
        directory=out/("text/"+key[5:] if key.startswith("text_") else key)
        verify(directory,report["manifests"][key])
    counts=Counter();cursor={s["name"]:0 for s in scope["inputs"]}
    for event in rows(out/"ledger",report["manifests"]["ledger"]):
        require(event["source_ids"][0]==cursor[event["source"]],"decision ledger has interval gaps")
        cursor[event["source"]]=event["source_ids"][1]
        counts.update(documents=1,input_ids=event["input_ids"],**{event["decision"]:1})
    for source in scope["inputs"]:
        require(cursor[source["name"]]==source["ids"],"decision ledger is incomplete")
    require(all(counts[k]==report["counts"].get(k,0) for k in ["documents","input_ids","KEEP","EDIT","HOLD","EXCLUDE"]),"decision recount differs")
    summaries={};val_text=set();train_text=set();started=time.monotonic()
    with ExitStack() as stack:
        source_maps={}
        for source in scope["inputs"]:
            stream=stack.enter_context((ROOT/source["path"]).open("rb"))
            source_maps[source["name"]]=stack.enter_context(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
        for split in ("val","train"):
            manifest=report["manifests"]["tokens_"+split]
            banks={};total=0;digest=hashlib.sha256()
            for spec in manifest["shards"]:
                path=out/"tokens"/split/spec["path"]
                require(path.stat().st_size==spec["bytes"] and spec["bytes"]<20_000_000
                    and spec["bytes"]%2==0 and spec["first_id"]==total
                    and file_sha(path)==spec["sha256"],"token shard dimensions/hash/order differ")
                stream=stack.enter_context(path.open("rb"))
                banks[spec["path"]]=stack.enter_context(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
                digest.update(banks[spec["path"]]);total+=spec["ids"]
            require(total==manifest["ids"] and digest.hexdigest().upper()==manifest["concat_sha256"],"logical full token stream differs")
            documents=position=0;regenerated=hashlib.sha256();signal_counts=Counter()
            for row in rows(out/"text"/split,report["manifests"]["text_"+split]):
                text=row["text"];cache=row["cache"]
                require(row["decision"] in ("KEEP","EDIT") and sha(text)==row["clean_text_sha256"]
                    and cache["offset_ids"]==position,"admitted text/hash/global offset differs")
                data=banks[cache["shard"]][cache["local_id"]*2:(cache["local_id"]+cache["ids"])*2]
                values=array("H");values.frombytes(data)
                if sys.byteorder!="little":values.byteswap()
                require(values and values[-1]==2 and values.count(2)==1
                    and not any(v in codec.specials for v in values[:-1]),"EOS/document/reserved boundary differs")
                decoded,body=codec.text(values[:-1])
                require(decoded==text and body==text.encode("utf-8"),"cache decode changes adopted text")
                lo,hi=row["source_ids"]
                original=source_maps[row["source"]][lo*2:hi*2]
                require(hashlib.sha256(original).hexdigest().upper()==row["source_ids_sha256"],"source link changed")
                if row["serialization_mode"]=="SOURCE_SLICE":
                    expected=original
                else:
                    expected=native.ids_bytes(codec.backend.encode(text,add_special_tokens=False).ids+[2])
                require(data==expected and hashlib.sha256(data).hexdigest().upper()==cache["ids_sha256"],"deterministic cache regeneration differs")
                regenerated.update(expected);position+=len(data)//2;documents+=1
                key=bytes.fromhex(sha(text))
                seen=val_text if split=="val" else train_text
                require(key not in seen,"accepted same-split exact text duplicate")
                if split=="train":require(key not in val_text,"accepted train/val exact text duplicate")
                seen.add(key);signal_counts.update(signals(text)[0])
            require(position==manifest["ids"] and regenerated.hexdigest().upper()==manifest["concat_sha256"]
                and documents==report["accepted"][split]["documents"]
                and dict(signal_counts)==report["accepted_structure_signals"][split],"independent full consumer count/hash/measurement differs")
            summaries[split]=dict(documents=documents,ids=position,regenerated_sha256=regenerated.hexdigest().upper(),
                exact_text_duplicates=0,structure_signals=dict(signal_counts))
    oversized=[corpus.relative(p) for p in base.rglob("*") if p.is_file() and p.stat().st_size>=20_000_000]
    require(not oversized,"new artifact at or above20,000,000 bytes")
    result=dict(schema=SCHEMA,status="CPU_FULL_CACHE_VERIFIED",summary=summaries,decisions=dict(counts),
        every_adopted_document_regenerated=True,exact_train_val_text_overlap=0,files_under_20mb=True,
        training_authorized=False,global_url_leakage="UNVERIFIED",seconds=time.monotonic()-started)
    write_json(out/"verified.json",result)
    return result


def main(argv=None):
    os.environ.update(TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",CUDA_VISIBLE_DEVICES="",
                      OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["build","verify"])
    parser.add_argument("--base",type=Path,default=corpus.BASE)
    parser.add_argument("--adoptions",type=Path)
    parser.add_argument("--output-name",default="cache_v1")
    args=parser.parse_args(argv)
    if args.command=="build":
        require(args.adoptions is not None,"exact root text-adoption manifest required")
        value=build(args.base,args.adoptions,args.output_name)
        print(json.dumps(dict(status="FULL_CACHE_BUILT_REQUIRES_INDEPENDENT_VERIFY",counts=value["counts"],accepted=value["accepted"])),flush=True)
    else:
        print(json.dumps(verify_cache(args.base,args.output_name)),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
