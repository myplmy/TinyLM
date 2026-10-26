#!/usr/bin/env python3
"""Versioned extension of the frozen HOLD cache adapter; no engine duplication."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_cache as engine
from scripts import p106b_hold_policy_v3 as policy

ORIGINAL_CODE_GUARD=engine.RecoveryEngine.code_guard
EXTRA_CODE=engine.CODE_FILES+["scripts/p106b_hold_policy_v3.py","scripts/p106b_hold_revision.py"]


def reviewed_code_guard(self,original,cleaned,manual=None):
    if ORIGINAL_CODE_GUARD(self,original,cleaned,manual):return True
    if self.current[1] in (1,2):return False
    exception=(manual or {}).get("code_exception") or {}
    if exception.get("kind")!="DECORATIVE_TILDE_MARKERS":return False
    if exception.get("original_text_sha256")!=engine.sha(original):return False
    approved=exception.get("decorative_lines",[])
    if not approved:return False
    for line in approved:
        if original.splitlines().count(line)!=1 or not re.match(r"^~{3,}[^~]",line):return False
    def unmark(text):
        result=[]
        for line in text.splitlines(keepends=True):
            body=line.rstrip("\r\n");ending=line[len(body):]
            if body in approved:body=re.sub(r"~{3,}$","",re.sub(r"^~{3,}","",body))
            result.append(body+ending)
        return "".join(result)
    return (policy.unicode_examples_preserved(original,cleaned)
        and policy.code_preserved(unmark(original),unmark(cleaned)))


@contextmanager
def revision():
    with patch.object(engine,"policy",policy),patch.object(engine,"CODE_FILES",EXTRA_CODE),\
            patch.object(engine.RecoveryEngine,"code_guard",reviewed_code_guard):
        yield


def census(base,name="proposals_v3",each=6):
    original_read=engine.cache.read
    v1=original_read(base/"proposals_v1/review_packets/manifest.json")
    v2=original_read(base/"proposals_v2/review_packets/manifest.json")
    def read(path):
        if Path(path)==base/"proposals_v1/review_packets/manifest.json":
            return dict(v1,rows=v1["rows"]+v2["rows"])
        return original_read(path)
    with revision(),patch.object(engine.cache,"read",read):
        return engine.revised_census(base,name,each)


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",
        OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["census","build","verify"]);p.add_argument("--base",type=Path,default=engine.recovery.BASE)
    p.add_argument("--adoptions",type=Path);p.add_argument("--proposal-name",default="proposals_v3")
    p.add_argument("--output-name",default="cache_v3");p.add_argument("--each",type=int,default=6)
    args=p.parse_args();base=engine.safe(args.base)
    if args.command=="census":result=census(base,args.proposal_name,args.each)
    else:
        with revision():
            if args.command=="build":
                engine.require(args.adoptions is not None,"exact root adoptions required")
                result=engine.build(base,engine.safe(args.adoptions),args.output_name,args.proposal_name)
            else:result=engine.verify(base,args.output_name)
    import json
    print(json.dumps({k:v for k,v in result.items() if k in ["status","counts","recovery_outcomes","baseline_accepted_preserved"]}),flush=True)


if __name__=="__main__":main()
