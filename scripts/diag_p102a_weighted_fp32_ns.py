"""Isolate FP32 Newton-Schulz in the measured weighted-head FP32 cases."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p102a_weighted_head_vocab as head
from scripts.diag_p102a_head_muon_trace import FP32NSInput, validate_ns_interface


TAG = "p102a_weighted_fp32_ns_v1_20261118"
BASE = head.OUT
OUT = BASE.parent / TAG
CASES = tuple((n,p) for n,p in head.CASES if p == "fp32")
pins = head.signature
head.TAG,head.OUT,head.PROFILE,head.CASES=TAG,OUT,OUT/"profile.json",CASES


def signature():
    paths = ("scripts/diag_p102a_weighted_fp32_ns.py","scripts/diag_p102a_head_muon_trace.py")
    return {**pins(),**{p:head.io.digest(head.io.ROOT/p) for p in paths}}


head.signature=signature


def prepare():
    old = head.read(BASE/"terminal.json")
    assert old["exit"]==0 and old["complete"]
    for vocab,_ in CASES:
        rows=head.read(BASE/f"{vocab}_fp32.json")["reports"]
        assert all(v["status"]=="COMPLETE" for v in rows.values())
        for arm in head.BACKENDS[1:]:
            assert rows[arm]["first_step"]["projection_after"]["mismatch"] > 0
            assert rows[arm]["first_step"]["projection_grad"]["mismatch"] == 0
    head.prepare()
    head.io.write(OUT/"variation.json",dict(original_terminal_sha256=head.io.digest(BASE/"terminal.json"),
        fixed_fp32_cases=CASES,independent_variable="FP32_CAST_ONLY_INSIDE_ORIGINAL_NEWTON_SCHULZ",
        original_muon_path_changed=False, original_inputs_changed=False))


def worker(vocab):
    import torch
    from tinylm.train import muon

    original=muon._newton_schulz
    validate_ns_interface(original)

    def fp32_ns(matrix,steps=5,eps=1e-7):
        assert matrix.dtype==torch.float32 and matrix.ndim==2
        with torch.autocast(device_type=matrix.device.type,enabled=False):
            return original(FP32NSInput(matrix),steps=steps,eps=eps)

    with patch.object(muon,"_newton_schulz",fp32_ns):
        return head.worker(vocab,"fp32")


def run():
    p=head.verify()
    variation=head.read(OUT/"variation.json")
    assert variation["original_terminal_sha256"]==head.io.digest(BASE/"terminal.json")
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    assert time.time()+len(CASES)*(head.CAP+25)+40 < head.io.CUTOFF
    cases=[]
    for vocab,precision in CASES:
        if (OUT/"STOP").exists():
            break
        head.io.reserve_device()
        command=["timeout","--signal=INT","--kill-after=15s",f"{head.CAP}s",sys.executable,"-B","-u","-m",
                 "scripts.diag_p102a_weighted_fp32_ns","worker",str(vocab)]
        result=subprocess.run(command,cwd=head.io.ROOT)
        cases.append(dict(vocab=vocab,precision=precision,exit=result.returncode,report=f"{vocab}_{precision}.json"))
        print("P102A_FP32_NS_TERMINAL",vocab,result.returncode,flush=True)
    release=head.io.reserve_device()
    complete=len(cases)==len(CASES)
    status=0 if complete and all(c["exit"]==0 for c in cases) else 8
    head.io.write(OUT/"terminal.json",dict(complete=complete,exit=status,cases=cases,release=release,
                  profile_sha256=head.io.digest(head.PROFILE),source_sha=p["source_sha"]))
    return status


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run","worker"))
    p.add_argument("vocab",type=int,nargs="?")
    a=p.parse_args()
    if a.action=="prepare":
        prepare()
    elif a.action=="run":
        raise SystemExit(run())
    else:
        raise SystemExit(worker(a.vocab))
