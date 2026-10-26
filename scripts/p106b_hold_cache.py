#!/usr/bin/env python3
"""Reuse the frozen corpus engine for a separately verified HOLD recovery cache.

Parent KEEP/EDIT text and EXCLUDE decisions have priority over new recoveries.
Recovered validation text is checked against the preserved training cache before
construction, so a new validation span cannot evict an existing training row.
No parent file, original token stream or training launcher is modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import mmap
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_corpus_cache as cache
from scripts import p106b_corpus_cleanup as corpus
from scripts import p106b_hold_recovery as recovery
from scripts import p106b_hold_policy as policy_v1
from scripts import p106b_hold_policy_v2 as policy
from scripts import p106b_hold_proposals as proposals
from scripts.p106b_native_text_audit import file_sha,write_json
from scripts.p106b_source_cleanup import sha,safe

SCHEMA="P106B_HOLD_RECOVERY_CACHE_V2"
CODE_FILES=["scripts/p106b_hold_cache.py","scripts/p106b_hold_policy_v2.py",
    "scripts/p106b_hold_policy.py","scripts/p106b_hold_proposals.py","scripts/p106b_hold_recovery.py"]
NAMES={1:"KEEP",2:"EDIT",3:"HOLD",4:"EXCLUDE",5:"EXCLUDE"}


def require(value,message):
    if not value:raise ValueError(message)


def code_pins():
    code_root=Path(__file__).resolve().parents[1]
    return {name:file_sha(code_root/name) for name in CODE_FILES}


def revised_census(base,name="proposals_v2",each=6):
    """Call the frozen census with literal-Unicode rules and fresh review texts."""
    original_pin=proposals.pin;original_read=cache.read
    old=original_read(base/"proposals_v1/review_packets/manifest.json")
    old_initial=original_read(base/"packets_initial_v2/manifest.json")
    def identity(target):
        inventory,value=original_pin(target)
        value.update(recovery_revision_source_sha256=code_pins(),
            previous_proposals_sha256=file_sha(base/"proposals_v1/complete.json"))
        return inventory,value
    def read(path):
        if Path(path)==base/"packets_initial_v2/manifest.json":
            return dict(old_initial,rows=old_initial["rows"]+old["rows"])
        return original_read(path)
    with patch.object(proposals,"policy",policy),patch.object(proposals,"pin",identity),patch.object(cache,"read",read):
        return proposals.full(base,name,each)


class ParentIndex:
    def __init__(self,base):
        self.base=base;self.parent=recovery.PARENT;self.old=self.parent/"cache_v1"
        self.scope=cache.read(base/"scope.json");self.report=cache.read(self.old/"built.json")
        require(file_sha(base/"scope.json")==file_sha(self.parent/"scope.json"),"recovery scope differs from frozen parent")
        proof=cache.read(self.old/"verified.json")
        require(proof.get("every_adopted_document_regenerated") is True,"verified parent cache required")
        for name,digest in self.report["source_code_sha256"].items():
            require(file_sha(Path(__file__).resolve().parents[1]/name)==digest,"parent engine source changed")
        cache.verify(self.old/"ledger",self.report["manifests"]["ledger"])
        self.states={s["name"]:bytearray(s["intervals"]) for s in self.scope["inputs"]}
        self.clean={s["name"]:bytearray(s["intervals"]*32) for s in self.scope["inputs"]}
        self.owners={"train":{},"val":{}};self.duplicates={};self.overlaps={};self.counts=Counter()
        for row in cache.rows(self.old/"ledger",self.report["manifests"]["ledger"]):
            source=row["source"];ordinal=int(row["id"].rsplit(":",1)[1]);decision=row["decision"]
            require(self.states[source][ordinal]==0,"parent ledger repeats an ID")
            code={"KEEP":1,"EDIT":2,"HOLD":3,"EXCLUDE":4}[decision]
            if code==4 and row["reasons"]==["TRAIN_VAL_CONTENT_OVERLAP"]:code=5
            self.states[source][ordinal]=code;self.counts.update([decision])
            if code in (1,2):
                digest=bytes.fromhex(row["clean_text_sha256"])
                self.clean[source][ordinal*32:(ordinal+1)*32]=digest
                require(digest not in self.owners[row["split"]],"parent accepted roster has duplicates")
                self.owners[row["split"]][digest]=row["id"]
            if row.get("duplicate_of"):self.duplicates[row["id"]]=row["duplicate_of"]
            if row.get("validation_overlap"):self.overlaps[row["id"]]=row["validation_overlap"]
        require(all(0 not in v for v in self.states.values()),"parent ledger has missing positions")
        require(all(self.counts[k]==self.report["counts"].get(k,0) for k in ["KEEP","EDIT","HOLD","EXCLUDE"]),"parent decision counts differ")

    def state(self,row):
        return self.states[row["source"]][int(row.get("ordinal",row["id"].rsplit(":",1)[1]))]

    def digest(self,row):
        ordinal=int(row.get("ordinal",row["id"].rsplit(":",1)[1]))
        return bytes(self.clean[row["source"]][ordinal*32:(ordinal+1)*32]).hex().upper()


class RecoveryEngine:
    def __init__(self,base,adoptions):
        self.base=base;self.index=ParentIndex(base);self.adoptions=adoptions
        self.old_document,self.old_overrides=cache.manual_overrides(recovery.PARENT,recovery.OLD_ADOPTIONS)
        self.new_document,self.new_overrides=cache.manual_overrides(base,adoptions)
        self.old_choose=cache.choose;self.old_code_guard=cache.code_preserved
        self.current=None;self.extra={};self.val_blocked={};self.baseline_checked=0;self.recovered=Counter()

    def pick(self,row,overrides,known=False):
        state=self.index.state(row);self.current=(row,state);self.extra={}
        if state in (1,2):
            value=self.old_choose(row,self.old_overrides,known)
            require(value[0] in ("KEEP","EDIT") and sha(value[1])==self.index.digest(row),"preserved baseline text changed")
            return value
        if state in (4,5):
            return "EXCLUDE",row["text"],["TRAIN_VAL_CONTENT_OVERLAP" if state==5 else "EXACT_CLEAN_TEXT_DUPLICATE"],None
        if not row["complete_eos"] or not row["valid_utf8"] or row["id"]=="validation:0":
            return "HOLD",row["text"],["SOURCE_BOUNDARY_NOT_RECOVERABLE"],None
        key=row["original_text_sha256"]
        override=overrides.get(key)
        if override:
            require(override.get("recovery_review") is True,"new manual decision needs an explicit recovery review")
            if known:require(override.get("resolves_inherited_hold") is True,"inherited HOLD is not resolved by this review")
            decision=override["decision"]
            text=override["text"] if decision=="EDIT" else row["text"]
            reasons=[override["reason"]]
            manual=dict(input_match_sha256=key,reference=override["review"],recovery_review=True,
                code_exception=override.get("code_exception"))
        else:
            previous=self.old_overrides.get(key) or self.old_overrides.get(row["candidate_text_sha256"])
            event=dict(reasons=["PRESERVED_PREVIOUS_EXPLICIT_HOLD"] if known else [],
                manual_hold=bool(previous and previous["decision"]=="HOLD"))
            value=policy.propose(row,event);decision,text,reasons=value["decision"],value["text"],value["reasons"];manual=None
        if decision in ("KEEP","EDIT"):
            digest=bytes.fromhex(sha(text));split=row["split"]
            owner=self.index.owners[split].get(digest)
            if owner:
                self.extra["duplicate_of"]=owner
                return "EXCLUDE",text,["EXACT_CLEAN_TEXT_DUPLICATE_WITH_PRESERVED_BASELINE"],manual
            if split=="val" and (digest in self.index.owners["train"] or row["id"] in self.val_blocked):
                self.extra["validation_overlap"]=self.val_blocked.get(row["id"],dict(kind="EXACT_PRESERVED_TRAIN_TEXT",id=self.index.owners["train"].get(digest)))
                return "EXCLUDE",text,["RECOVERED_VALIDATION_CONFLICTS_WITH_PRESERVED_TRAIN"],manual
        return decision,text,reasons,manual

    def code_guard(self,original,cleaned,manual=None):
        require(self.current is not None and self.current[0]["text"]==original,"code guard lost its source row")
        if self.current[1] in (1,2):return self.old_code_guard(original,cleaned,manual)
        if not policy.unicode_examples_preserved(original,cleaned):return False
        if policy.code_preserved(original,cleaned):return True
        exception=(manual or {}).get("code_exception")
        if not exception:return False
        if exception.get("kind")!="UNWRAP_EXTRACTED_UNIT_TABLE":return False
        if exception.get("original_text_sha256")!=sha(original):return False
        lo,hi=exception["original_table_characters"]
        literal=original[lo:hi]
        if not literal.startswith("``` "):return False
        if sha(literal)!=exception["original_table_sha256"]:return False
        retained=literal[4:]
        if cleaned.count(retained)!=1:return False
        blocks,opened=policy_v1.real_code_blocks(original)
        if not opened or not blocks or blocks[-1][0]!=lo:return False
        # Exact, root-reviewed non-code table bytes survive; only the malformed
        # opening marker and the separately held advertising tail disappear.
        return policy.code_preserved(original[:lo],cleaned)

    def annotate(self,row,*,ledger=False):
        state=self.index.state(row);result=dict(row,parent_decision=NAMES[state])
        if state in (1,2):
            require(row["decision"] in ("KEEP","EDIT") and row["clean_text_sha256"]==self.index.digest(row),"existing adopted row was lost or changed")
            if ledger:self.baseline_checked+=1
        if state in (4,5):
            require(row["decision"]=="EXCLUDE","old exclusion was silently released")
            if row["id"] in self.index.duplicates:result["duplicate_of"]=self.index.duplicates[row["id"]]
            if row["id"] in self.index.overlaps:result["validation_overlap"]=self.index.overlaps[row["id"]]
        if state==3:
            if self.current and self.current[0]["id"]==row["id"]:result.update(self.extra)
            if ledger:
                self.recovered.update(documents=1,input_ids=row["input_ids"],**{row["decision"]:1})
                self.recovered[row["decision"]+"_input_ids"]+=row["input_ids"]
        return result

    def validation_preflight(self):
        spec=next(s for s in self.index.scope["inputs"] if s["split"]=="val")
        codec=cache.native.ByteCodec(cache.read(ROOT/self.index.scope["tokenizer"]["path"]))
        raw=(ROOT/spec["path"]).read_bytes();candidates={}
        for row in corpus.iter_scan(recovery.PARENT,spec["name"]):
            if self.index.state(row)!=3:continue
            decision,text,_,_=self.pick(row,self.new_overrides,False)
            if decision not in ("KEEP","EDIT"):continue
            lo,hi=row["source_ids"]
            data=raw[lo*2:hi*2] if text==row["text"] else cache.native.ids_bytes(codec.backend.encode(text,add_special_tokens=False).ids+[2])
            for position,digest in cache.span_hashes(data):candidates.setdefault(digest,[]).append(row["id"])
        if not candidates:return
        with ExitStack() as stack:
            banks={}
            for shard in self.index.report["manifests"]["tokens_train"]["shards"]:
                path=self.index.old/"tokens/train"/shard["path"]
                require(file_sha(path)==shard["sha256"],"parent training shard changed")
                stream=stack.enter_context(path.open("rb"));banks[shard["path"]]=stack.enter_context(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
            for row in cache.rows(self.index.old/"ledger",self.index.report["manifests"]["ledger"]):
                if row["split"]!="train" or row["decision"] not in ("KEEP","EDIT"):continue
                loc=row["cache"];data=banks[loc["shard"]][loc["local_id"]*2:(loc["local_id"]+loc["ids"])*2]
                for position,digest in cache.span_hashes(data):
                    for ident in candidates.get(digest,[]):
                        self.val_blocked.setdefault(ident,dict(kind="PRESERVED_TRAIN_256_IDS_STRIDE128",id=row["id"],local_id=position))


def build(base,adoptions,output_name="cache_v2",proposal_name="proposals_v2"):
    base=safe(base);engine=RecoveryEngine(base,adoptions);pins=code_pins()
    require(proposal_name.isascii() and proposal_name.replace("_","").isalnum(),"safe proposal version required")
    census=base/proposal_name/"complete.json";require(census.exists(),"full revised HOLD census is required")
    census_report=cache.read(census)
    require(census_report["unprocessed"]==0 and census_report["pin"]["recovery_revision_source_sha256"]==pins,"revised full census/code identity differs")
    require(census_report["pin"]["parent_built_sha256"]==file_sha(engine.index.old/"built.json") and
        census_report["pin"]["parent_verified_sha256"]==file_sha(engine.index.old/"verified.json") and
        census_report["pin"]["scope_sha256"]==file_sha(base/"scope.json"),"revised census parent identity differs")
    require(census_report["counts"]["documents"]==engine.index.counts["HOLD"] and
        census_report["counts"]["input_ids"]==engine.index.report["counts"]["HOLD_input_ids"],"revised census HOLD scope differs")
    cache.verify(census.parent/"ledger",census_report["manifest"])
    engine.validation_preflight()
    old_iter=corpus.iter_scan;old_coverage=cache.scan_coverage;old_writer=cache.ShardWriter;old_json=cache.write_json
    out=base/output_name
    provenance=dict(parent_built_sha256=file_sha(engine.index.old/"built.json"),parent_verified_sha256=file_sha(engine.index.old/"verified.json"),
        full_proposals_sha256=file_sha(census),full_proposals_path=str(census.relative_to(ROOT)),adoptions=str(adoptions.relative_to(ROOT)),
        adapter_source_sha256=pins,parent_original_adoptions_sha256=file_sha(recovery.OLD_ADOPTIONS),
        validation_conflicts=dict(engine.val_blocked),rules=policy.RULES)
    class Writer:
        def __init__(self,directory,*args,**kwargs):
            self.writer=old_writer(directory,*args,**kwargs)
            self.ledger=Path(directory)==out/"ledger"
            self.annotated=self.ledger or Path(directory) in [out/"hold",out/"text/train",out/"text/val"]
        def append(self,row):self.writer.append(engine.annotate(row,ledger=self.ledger) if self.annotated else row)
        def close(self,**kwargs):return self.writer.close(**kwargs)
    def emit(path,value):
        if Path(path).name in ["started.json","built.json"]:
            require(code_pins()==pins,"recovery code changed during frozen build")
            value=dict(value,recovery=provenance)
            value["source_code_sha256"]=dict(value["source_code_sha256"],**pins)
        if Path(path).name=="built.json":
            require(engine.baseline_checked==engine.index.counts["KEEP"]+engine.index.counts["EDIT"],"baseline preservation coverage incomplete")
            require(engine.recovered["documents"]==engine.index.counts["HOLD"],"recovery decisions do not cover full parent HOLD")
            value.update(recovery_outcomes=dict(engine.recovered),baseline_accepted_preserved=True,
                recovered_validation_exclusions=len(engine.val_blocked))
        old_json(path,value)
    with patch.object(corpus,"iter_scan",lambda _base,source=None:old_iter(recovery.PARENT,source)),\
            patch.object(cache,"scan_coverage",lambda _base,scope:old_coverage(recovery.PARENT,scope)),\
            patch.object(cache,"choose",engine.pick),patch.object(cache,"code_preserved",engine.code_guard),\
            patch.object(cache,"ShardWriter",Writer),patch.object(cache,"write_json",emit),\
            patch.object(corpus,"RULES",policy.RULES):
        cache.build(base,adoptions,output_name)
    return cache.read(out/"built.json")


def verify(base,output_name="cache_v2"):
    out=base/output_name;report=cache.read(out/"built.json");index=ParentIndex(base)
    for name,digest in report["source_code_sha256"].items():
        require(file_sha(Path(__file__).resolve().parents[1]/name)==digest,"frozen source code differs")
    provenance=report["recovery"]
    require(file_sha(index.old/"built.json")==provenance["parent_built_sha256"] and
        file_sha(index.old/"verified.json")==provenance["parent_verified_sha256"],"verified parent provenance differs")
    require(file_sha(ROOT/provenance["adoptions"])==report["lineage"]["adoptions_sha256"],"adoption source differs")
    require(file_sha(ROOT/provenance["full_proposals_path"])==provenance["full_proposals_sha256"],"full HOLD proposal receipt changed")
    for source in index.scope["inputs"]:require(file_sha(ROOT/source["path"])==source["sha256"],"original input changed")
    proof=cache.verify_cache(base,output_name)
    baseline=0;counts=Counter()
    for row in cache.rows(out/"ledger",report["manifests"]["ledger"]):
        state=index.state(row)
        require(row["parent_decision"]==NAMES[state],"parent decision annotation differs")
        if state in (1,2):
            require(row["decision"] in ("KEEP","EDIT") and row["clean_text_sha256"]==index.digest(row),"baseline body not preserved")
            baseline+=1
        elif state in (4,5):require(row["decision"]=="EXCLUDE","parent exclusion changed")
        else:
            counts.update(documents=1,input_ids=row["input_ids"],**{row["decision"]:1})
            counts[row["decision"]+"_input_ids"]+=row["input_ids"]
    require(baseline==index.counts["KEEP"]+index.counts["EDIT"] and dict(counts)==report["recovery_outcomes"],"independent recovery accounting differs")
    result=dict(schema=SCHEMA,status="CPU_FULL_RECOVERY_CACHE_VERIFIED",built_sha256=file_sha(out/"built.json"),
        core_verified_sha256=file_sha(out/"verified.json"),all_previous_adopted_text_preserved=True,
        parent_adopted_documents=baseline,recovery_outcomes=dict(counts),training_authorized=False,
        global_article_leakage="UNVERIFIED_NO_ORIGINAL_ARTICLE_IDS")
    write_json(out/"recovery_verified.json",result)
    return result


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",
        OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["census","build","verify"]);p.add_argument("--base",type=Path,default=recovery.BASE)
    p.add_argument("--adoptions",type=Path);p.add_argument("--output-name",default="cache_v2")
    p.add_argument("--proposal-name",default="proposals_v2");p.add_argument("--each",type=int,default=6)
    a=p.parse_args();base=safe(a.base)
    if a.command=="census":result=revised_census(base,a.proposal_name,a.each)
    elif a.command=="build":
        require(a.adoptions is not None,"exact root adoption manifest required")
        result=build(base,safe(a.adoptions),a.output_name,a.proposal_name)
    else:result=verify(base,a.output_name)
    import json
    print(json.dumps({k:v for k,v in result.items() if k in ["status","counts","recovery_outcomes","baseline_accepted_preserved"]}),flush=True)


if __name__=="__main__":main()
