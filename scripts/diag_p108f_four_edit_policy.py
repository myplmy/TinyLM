"""Complete the four-write arms in the already measured Gemma18 panel."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p108f_matched_policies as prior


TAG = "p108f_gemma18_matched_policy_four_v1_20261119"
BASE = prior.OUT
OUT = BASE.with_name(TAG)
SOURCE_PINS = prior.pins
INPUTS = ("profile.json","search.json","ORIGINAL.json","SINGLE1.json","report.json")


def pins():
    earlier = prior.READ(BASE/"profile.json")
    support = SOURCE_PINS()
    assert earlier["original_core_sha256"]==support["original_core_sha256"]
    assert earlier["native_model_sha256"]==support["native_model_sha256"]
    assert earlier["source_pins"]==support["source_pins"]
    p = Path(__file__)
    return dict(**{k:v for k,v in support.items() if k!="tag"},tag=TAG,
                new_script_sha256=prior.HASH(p),
                previous={name:prior.HASH(BASE/name) for name in INPUTS})


def four_rounds(body,downs,fit,target,counts):
    order = prior.READ(BASE/"search.json")["order"]
    assert sorted(order)==list(downs)
    best = order[0]
    parameters = tuple(m.weight for m in downs.values())
    flags = tuple((p,p.requires_grad) for p in body.parameters())
    try:
        body.requires_grad_(False)
        for p in parameters:
            p.requires_grad_(True)
        initial = {i:m.weight.detach().double().clone() for i,m in downs.items()}
        start = fit.directions(parameters)
        first,row = prior.trial(downs,initial,best,start[best],target/4,0.,fit)
        del start
        paths = {}
        searches = {}
        for name in ("SAME4","SEQ4","ADAPT_D4"):
            state = {best:row}
            steps = [first]
            traces = []
            for count in range(2,5):
                with prior.applied(downs,state):
                    directions = fit.directions(parameters)
                    if name=="ADAPT_D4":
                        candidates = [i for i in downs if i not in state]
                    else:
                        candidates = [best if name=="SAME4" else order[count-1]]
                    trials = [prior.trial(downs,initial,i,directions[i],target*count/4,steps[-1]["net"],fit)
                              for i in candidates]
                selected,update = min(trials,key=lambda r:(r[0]["fit_nll"],r[0]["layer"]))
                assert abs(selected["net"]-target*count/4)<1e-6
                state[selected["layer"]] = update
                steps.append(selected)
                traces.append([c for c,_ in trials])
            paths[name] = (steps,state,steps[-1]["fit_nll"])
            searches[name] = traces
        info = dict(order=order,first=first,stages=searches,
                    reused_original=prior.HASH(BASE/"ORIGINAL.json"),
                    reused_single=prior.HASH(BASE/"SINGLE1.json"),gradient_passes=counts["fit_backwards"])
        return paths,info
    finally:
        for p,old_flag in flags:
            p.requires_grad_(old_flag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","actual"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(prior.DEADLINE.tzinfo)+timedelta(seconds=400)<prior.DEADLINE
    with (
        patch.object(prior,"OUT",OUT),patch.object(prior,"pins",pins),
        patch.object(prior,"experiments",four_rounds),patch.object(prior,"START_LIMIT",360),
    ):
        if phase=="prepare":
            prior.prepare()
            old,new = [prior.READ(p/"profile.json") for p in (BASE,OUT)]
            assert all(old[k]==new[k] for k in ("fit","evaluation","edit_budget"))
        else:
            prior.actual()


if __name__ == "__main__":
    main()
