#!/usr/bin/env python3
"""Refine unresolved drafts while reproducing frozen terminal draft bodies.

This only accelerates another complete proposal pass. Every original interval is
still decoded/verified by the existing engine, and every reused terminal body is
checked against its frozen hash. This is never root approval or cache admission.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_proposals as engine
from scripts import p106b_hold_resolution_policy_v6 as guards

IDENTITY=("id","source","split","source_ids","source_ids_sha256","original_text_sha256","input_ids")
ORIGINAL_WRITER=inv.ShardWriter


def ordered_deletion(original,cleaned):
    source=iter(char for char in original if not char.isspace())
    return all(any(a==b for a in source)for b in cleaned if not b.isspace())


class FrozenDraftSelector:
    def __init__(self,records,new_policy):
        self.records={}
        self.new_policy=new_policy
        self.last=None
        for row in records:
            key=row["original_text_sha256"]
            inv.require(key not in self.records,"frozen draft repeats a source")
            inv.require(row["decision"]in{"KEEP","EDIT","EXCLUDE","PENDING"},"unknown frozen outcome")
            if row["decision"]=="EDIT":
                inv.require(isinstance(row.get("text"),str)and inv.sha(row["text"])==row["clean_text_sha256"],
                            "frozen edited body hash differs")
            elif row["decision"]=="KEEP":
                inv.require(row["clean_text_sha256"]==key,"frozen KEEP changes source")
            self.records[key]=row

    def propose(self,row,individual_hold=False):
        key=row["original_text_sha256"]
        inv.require(key in self.records,"source is outside frozen draft")
        frozen=self.records[key]
        inv.require(all(row[name]==frozen[name]for name in IDENTITY),"source identity/interval changed")
        inv.require(inv.sha(row["text"])==key,"source body does not match frozen identity")
        inherited=individual_hold or bool(row.get("previous_holds"))
        if inherited:
            inv.require(frozen["decision"]=="PENDING","individual HOLD cannot reuse terminal draft")
        if frozen["decision"]=="PENDING":
            value=self.new_policy.propose(row,individual_hold)
        else:
            value=dict(decision=frozen["decision"],text=frozen["text"]if frozen["decision"]=="EDIT"else row["text"],
                       reasons=frozen["reasons"],changes=frozen["changes"],rules=self.new_policy.RULES)
        inv.require(value["decision"]in{"KEEP","EDIT","EXCLUDE","PENDING"},"unknown refinement outcome")
        candidate=value.get("candidate",value["text"])
        proof=None
        if value["decision"]in{"KEEP","EDIT"}:
            inv.require(not inherited,"refinement released an individual HOLD")
            inv.require(value["decision"]!="KEEP"or candidate==row["text"],"refined KEEP changes the source")
            proof=dict(ordered_nonwhitespace_deletion_only=ordered_deletion(row["text"],candidate),
                       code_guard=guards.code_preserved(row["text"],candidate),
                       unicode_guard=guards.unicode_examples_preserved(row["text"],candidate),
                       original_text_sha256=key,clean_text_sha256=inv.sha(candidate))
            inv.require(all(proof[name]for name in("ordered_nonwhitespace_deletion_only","code_guard","unicode_guard")),
                        "automatic draft changes literal characters/order/code/Unicode")
        self.last=dict(original_text_sha256=key,candidate=candidate if not inherited else None,
                       decision=value["decision"],integrity=proof,reused=frozen["decision"]!="PENDING")
        return dict(value,rules=self.new_policy.RULES)


@contextmanager
def refinement(base,baseline_name,new_policy,code_files):
    base=inv.safe(base)
    inv.require(baseline_name.isascii()and baseline_name.replace("_","").isalnum(),"safe frozen namespace required")
    source=base/baseline_name
    complete=source/"complete.json"
    report=inv.cache.read(complete)
    inv.require(report.get("full_residual_scope_covered")is True and report.get("root_adopted")==0,
                "a complete non-admitted draft baseline is required")
    inv.verify(source/"unique",report["unique_manifest"])
    input_sha256=inv.file_sha(complete)
    frozen_code=report["lineage"]["source_code_sha256"]
    for name,digest in frozen_code.items():
        inv.require(inv.file_sha(inv.ROOT/name)==digest,"frozen draft code changed")
    selector=FrozenDraftSelector(inv.cache.rows(source/"unique",report["unique_manifest"]),new_policy)
    inv.require(len(selector.records)==297539,"frozen complete unique scope differs")
    lineage=dict(path=str(complete.relative_to(inv.ROOT)),sha256=input_sha256,
                 reuse="TERMINAL_DRAFT_ONLY_WITH_FRESH_SOURCE_ID_HASH_AND_LITERAL_GUARDS",
                 unprocessed_reported_separately=True,root_adopted=0)

    class LineagedWriter(ORIGINAL_WRITER):
        def append(self,row):
            value=dict(row)
            if self.directory.name=="unique":
                last=selector.last
                inv.require(last and last["original_text_sha256"]==value["original_text_sha256"],"refinement output linkage differs")
                value["frozen_draft_input"]=lineage
                value["reused_frozen_terminal_draft"]=last["reused"]
                if value["decision"]=="PENDING":
                    value["diagnostic_candidate"]=last["candidate"]
                elif last["integrity"]:
                    value["refinement_integrity"]=last["integrity"]
            return super().append(value)

        def close(self,*,lineage):
            return super().close(lineage=dict(lineage,frozen_draft_input=self_frozen_lineage))

    self_frozen_lineage=lineage
    bound=SimpleNamespace(RULES=new_policy.RULES,propose=selector.propose)
    with patch.object(engine,"policy",bound),patch.object(engine,"CODE",code_files),\
            patch.object(inv,"ShardWriter",LineagedWriter):
        yield selector
    inv.require(inv.file_sha(complete)==input_sha256,"frozen draft report changed during refinement")
    inv.verify(source/"unique",report["unique_manifest"])
    for name,digest in frozen_code.items():
        inv.require(inv.file_sha(inv.ROOT/name)==digest,"frozen code changed during refinement")
