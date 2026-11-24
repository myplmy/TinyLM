"""Owned observations and physical-coordinate replay for the all-layer study."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from scripts import diag_p108c_scope as io
from scripts import diag_p108d_winner as origin
from scripts import p108c_limits as time_owner
from scripts import p108d_winner as margins_owner
from scripts import p108e_math as calculations
from scripts import p108_wsp_attention as editor

ROOT=io.ROOT
BASE=ROOT/"test_result/evidence/p108e_margin_sqp_v1_s1337"
PROFILE=BASE/"profile.json"
GEOMETRY=BASE/"geometry"
COMMON_BUDGET=origin.COMMON_BUDGET


class Budget(time_owner.Budget):
    def __init__(self,seconds=1800):
        super().__init__(seconds);self.last_disk=0.

    def check(self,**kwargs):
        remaining=super().check(**kwargs)
        now=time.monotonic()
        if now-self.last_disk>5:
            self.last_disk=now
            if shutil.disk_usage(ROOT).free<5_000_000_000:
                raise RuntimeError("less than5GB filesystem space; no cleanup authorized")
            size=sum(p.stat().st_size for p in BASE.rglob("*")if p.is_file())if BASE.exists()else 0
            if size>=1_900_000_000:raise RuntimeError("owned diagnostic disk cap reached")
        return remaining


def source():
    parent,fits,packed,guards,dev,baseline,refs=origin.source()
    guard_packed=origin.margin_owner.packed_inputs(guards,baseline)
    if sum(len(r["ids"])for r in guard_packed)!=239:
        raise ValueError("same239 complete original normal-prefix positions required")
    return parent,fits,packed,guards,guard_packed,dev,baseline,refs


def modules(active):
    origin.module_and_structure(active)
    model=active["model"]
    if any(layer.has_lora or layer.has_lrm or layer.has_film for layer in model.layers):
        raise ValueError("plain residual down branches without local transformations required")
    found=editor.outputs(model)
    return {layer:found["mlp:"+str(layer)]for layer in range(14)}


def native_forward(active,physical,row,*,features=None):
    captured={};handles=[];start=row["start"];count=len(row["targets"])
    if features not in (None,"full","targets"):raise ValueError("explicit observation mode required")
    if features is not None:
        for layer,module in physical.items():
            def retain(_module,args,output,layer=layer):
                if layer in captured:raise RuntimeError("repeated physical down visit")
                keys=args[0][0]if features=="full"else args[0][0,start:]
                captured[layer]=dict(keys=keys.detach().cpu().numpy().copy(),
                    values=output[0,start:].detach().cpu().numpy().copy())
            handles.append(module.register_forward_hook(retain))
        def endpoint(_module,args):captured["endpoint"]=args[0][0,start:].detach().cpu().numpy().copy()
        handles.append(active["model"].norm_f.register_forward_pre_hook(endpoint))
    try:
        device=next(iter(physical.values())).weight.device
        ids=torch.tensor([row["ids"]],device=device)
        hidden=active["model"](ids,return_hidden=True)
        logits=origin.canonical_head_logits(active["model"],hidden,start,count)[0]
    finally:
        for handle in reversed(handles):handle.remove()
    if features is not None and set(captured)!={*range(14),"endpoint"}:
        raise RuntimeError("incomplete all-layer feature observation")
    return logits,captured


def collect(active,physical,rows,budget,*,features="targets"):
    arrays=[];observations={layer:dict(keys=[],values=[])for layer in physical};endpoints=[]
    with torch.no_grad():
        for row in rows:
            budget.check();logits,saved=native_forward(active,physical,row,features=features)
            arrays.append(logits.detach().cpu().numpy().copy())
            if features is not None:
                for layer in physical:
                    for key in ("keys","values"):observations[layer][key].append(saved[layer][key])
                endpoints.append(saved["endpoint"])
            logits=None
    if features is not None:
        observations={layer:{key:np.concatenate(values)for key,values in items.items()}
                      for layer,items in observations.items()}
        observations["endpoint"]=np.concatenate(endpoints)
    else:observations={}
    return np.concatenate(arrays),observations


def target_indices(rows):
    offsets=[];gold=[];full_indices=[];length_weights=[];target_weights=[];cursor=0;full_cursor=0
    for row in rows:
        size=len(row["targets"]);offsets.append((cursor,cursor+size));cursor+=size
        gold.extend(row["targets"])
        full_indices.extend(range(full_cursor+row["start"],full_cursor+len(row["ids"])))
        length_weights.extend([1./len(row["ids"])]*len(row["ids"]))
        target_weights.extend([1./size]*size);full_cursor+=len(row["ids"])
    return dict(offsets=offsets,gold=np.asarray(gold,dtype=np.int64),
        target_from_full=np.asarray(full_indices,dtype=np.int64),
        full_weights=np.asarray(length_weights),target_weights=np.asarray(target_weights))


def load_bases(report):
    result={}
    for item in report["layers"]:
        spec=item["basis"]
        if io.sha(ROOT/spec["path"])!=spec["sha256"]:raise ValueError("frozen basis changed")
        result[item["layer"]]=io.load_arrays(ROOT/spec["path"])
    return result


def materialized(original,coordinates,bases):
    requested={};after={};stats=[]
    for layer in range(14):
        basis=bases[layer];theta=coordinates[layer]
        delta=(np.zeros_like(original[layer],dtype=np.float64)if not theta.size else
               calculations.reconstruct(theta,basis["left"],basis["right"]))
        request=delta.astype(np.float32)
        new=original[layer]+request
        actual=new.astype(np.float64)-original[layer].astype(np.float64)
        requested[layer]=request;after[layer]=new
        stats.append(dict(layer=layer,norm=float(np.linalg.norm(actual)),
            coefficient_norm=float(np.linalg.norm(theta)),changed=int(np.sum(new!=original[layer])),
            outside_requested=int(np.sum((actual!=0)&(request==0))),
            maximum_rounding_error=float(np.max(np.abs(actual-delta)))))
    total=float(np.sqrt(sum(item["norm"]**2 for item in stats)))
    return requested,after,dict(actual_norm=total,layers=stats)


@contextmanager
def install(active,physical,requested):
    native=[("mlp:"+str(layer),torch.from_numpy(requested[layer]).to(physical[layer].weight))for layer in range(14)]
    try:
        with editor.edit(active["model"],active["route"],native)as receipt:yield receipt
    finally:native.clear()


def score_logits(logits,rows):
    layout=target_indices(rows);gold=layout["gold"]
    margin,rivals=margins_owner.winner_margins(logits,gold)
    result=calculations.score(margin,layout["offsets"])
    return result,margin,rivals,logits.argmax(axis=1)


def save_array_chunks(directory,stem,array,*,rows=16):
    pins=[]
    for start in range(0,len(array),rows):
        pins.append(dict(start=start,stop=min(start+rows,len(array)),
            packet=io.save_arrays(directory/(stem+"_"+str(start).zfill(3)+".npz"),values=array[start:start+rows])))
    return pins


def read_array_chunks(pins):
    values=[];cursor=0
    for item in pins:
        if item["start"]!=cursor:raise ValueError("contiguous complete matrix chunks required")
        packet=item["packet"]
        if io.sha(ROOT/packet["path"])!=packet["sha256"]:raise ValueError("numeric chunk changed")
        array=io.load_arrays(ROOT/packet["path"])["values"]
        if len(array)!=item["stop"]-cursor:raise ValueError("numeric chunk length differs")
        values.append(array);cursor=item["stop"]
    return np.concatenate(values)
