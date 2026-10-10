"""P093B recovery: dev-only selection and storage round-trip primitives.

CPU operator tests are not a model-training run. Test/CE/real generation are
deliberately owned by the user-run driver, never by the dev optimizer.
"""
from __future__ import annotations
import copy
import time
import torch
from scripts import p093b_native_repair as native

VERSION="P093B_DEV_SELECTION_V1"
CHECKPOINT_STEPS=(0,20,50,100,250)


def snapshot(adapters):
    return [[{k:v.detach().cpu().clone() for k,v in a.state_dict().items()} for a in row] for row in adapters]


def restore(adapters,state):
    if len(adapters)!=len(state): raise ValueError("adapter ownership count changed")
    for row,values in zip(adapters,state):
        if len(row)!=len(values): raise ValueError("projection ownership count changed")
        for adapter,payload in zip(row,values): adapter.load_state_dict(payload,strict=True)


def dev_fit(shared,adapters,x,y,dev_x,dev_y,*,lr,steps=250,points=CHECKPOINT_STEPS,deadline=None):
    if lr not in (1e-3,1e-4) or steps<1 or 0 not in points or steps not in points:
        raise ValueError("preregistered LR/endpoint contract required")
    params=native.parameters_unique([a for row in adapters for a in row])
    if not params: raise ValueError("empty trainable adapter ownership")
    optimizer=torch.optim.AdamW(params,lr=lr,weight_decay=0)
    curve=[]; best=None; state=None; grad_max=0.; begin=time.perf_counter()
    def observe(step):
        nonlocal best,state
        train=native.measure(shared,x,y,adapters)
        dev=native.measure(shared,dev_x,dev_y,adapters)
        record={"step":step,"train_nrms":train["nrms"],"dev_nrms":dev["nrms"]}
        curve.append(record)
        if best is None or dev["nrms"]<best["dev_nrms"]:
            best=record.copy(); state=snapshot(adapters)
    observe(0)
    for step in range(1,steps+1):
        if deadline is not None and time.monotonic()>=deadline: raise TimeoutError("calibration recovery wall budget")
        for row in adapters:
            for adapter in row: adapter.train()
        optimizer.zero_grad(set_to_none=True)
        loss=native.normalized_loss(native.local_predictions(shared,x,adapters),y)
        loss.backward(); grads=[p.grad for p in params if p.grad is not None]
        if not grads or not all(torch.isfinite(g).all() for g in grads):
            raise ValueError("empty/nonfinite residual gradients")
        grad_max=max(grad_max,max(float(g.abs().max()) for g in grads))
        torch.nn.utils.clip_grad_norm_(params,1.); optimizer.step()
        if step in points: observe(step)
    restore(adapters,state)
    return {"lr":lr,"completed_updates":steps,"selected_step":best["step"],"selected_dev_nrms":best["dev_nrms"],
            "curve":curve,"grad_max":grad_max,"wall_sec":time.perf_counter()-begin,
            "trainable_parameters":sum(p.numel() for p in params),"selection_scope":"DEV_ONLY; test not an argument"},state


def select_trial(trials):
    if not trials: raise ValueError("no LR trials")
    return min(range(len(trials)),key=lambda i:(trials[i]["selected_dev_nrms"],trials[i]["selected_step"],i))


def half_storage_roundtrip(adapters):
    result=copy.deepcopy(adapters)
    with torch.no_grad():
        for row in result:
            for a in row:
                a.D.copy_(a.D.half().float()); a.U.copy_(a.U.half().float())
    return result


def byte_account(adapters):
    params=sum(a.D.numel()+a.U.numel() for row in adapters for a in row)
    return {"factor_parameters":params,"fp32_parameter_bytes":params*4,"fp16_storage_bytes":params*2,
            "ideal_ternary2bit_storage_bytes":(params*2+7)//8,
            "native_runtime_dtype":"FP32","fp16_roundtrip_runtime_saving":False,
            "exclusions":"shared core, master/cache copies, scales, metadata, KV, allocator and full model",
            "scope":"factor payload arithmetic, not deployed RSS/32MiB proof"}
