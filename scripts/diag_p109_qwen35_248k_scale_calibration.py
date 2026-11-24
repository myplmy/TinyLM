"""Calibrate shared per-token scales in the published five-trit G4 student."""

import argparse
from datetime import datetime, timedelta
from math import log
import os
from pathlib import Path
import random
from statistics import median
import subprocess
from time import perf_counter

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_qwen_248k_warm_ce as ce
from scripts import diag_p109_qwen35_248k_cached_kl as kd
from scripts.p014e_packed_g128 import PackedGroupLinear


TAG = "p109_qwen35_248k_scale_calibration_v2_20261119"
OUT = ce.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
DRAWS = OUT / "draws.npy"
EXPORT = OUT / "calibrated_5trit.pt"
STEPS, SEED, LR = 48, 65312026, .008
LIMIT = log(1.25)


def source_report():
    r = ce.qwen.load(kd.OUT/"report.json")
    assert r["source_preserved"] and ce.qwen.digest(kd.EXPORT)==r["packed_sha256"]
    return r


def verify(profile):
    assert all(ce.qwen.digest(ce.ROOT/p)==h for p,h in profile["pins"].items())
    assert ce.qwen.digest(DRAWS)==profile["draws_sha256"]
    return source_report()


def prepare():
    source_report()
    docs = ce.qwen.load(ce.qwen.AUTHORED)["data"]["documents"]
    with np.load(ce.DATA,allow_pickle=False) as arrays:
        previous = set(arrays["draws"].ravel())
        held = set(arrays["held"].ravel())
        y = arrays["y"]
    choices = [[i for i,d in enumerate(docs) if d["split"]=="train" and d["language"]==lang and i not in previous]
               for lang in ("en","ko")]
    assert [len(group) for group in choices]==[208,208]
    rng = random.Random(SEED)
    selected = [np.asarray(rng.sample(group, STEPS*ce.BATCH//2)).reshape(STEPS,ce.BATCH//2) for group in choices]
    draws = np.concatenate(selected,axis=1)
    assert len(np.unique(draws))==draws.size and not set(draws.ravel()).intersection(previous|held)
    unused_pool = int(sum((y[group]>=0).sum() for group in choices))
    targets = y[draws]
    valid = targets[targets>=0]
    assert unused_pool >= 2*len(valid) and valid.max()<ce.ASSIGNED
    files = [Path(__file__),Path(ce.__file__),ce.DATA,ce.PROFILE,ce.qwen.AUTHORED,kd.EXPORT,
             kd.OUT/"report.json",ce.OUT/"report.json",ce.ROOT/"scripts/p014e_packed_g128.py",
             ce.ROOT/"tinylm/model/transformer.py",ce.ROOT/"tinylm/model/modules.py"]
    pins = {str(p.relative_to(ce.ROOT)):ce.qwen.digest(p) for p in files}
    probe = verify_body_cpu(draws[0,0])
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    with DRAWS.open("xb") as stream:
        np.save(stream,draws)
    profile = dict(tag=TAG, approval="WIP176", steps=STEPS, seed=SEED, lr=LR, scale_limit=[.8,1.25], pins=pins,
                   remaining_docs=sum(map(len,choices)), eligible_pool=unused_pool, draw_targets=len(valid),
                   editable_rows=int(len(np.unique(valid))), draws_sha256=ce.qwen.digest(DRAWS), cpu_probe=probe)
    ce.qwen.write(PROFILE,profile)
    print("P109_SCALE_CPU",draws.size,len(valid),unused_pool,profile["editable_rows"],flush=True)


class FrozenCalibrationLinear(torch.nn.Module):
    """One immutable dense operand for differentiating its input in this experiment."""

    def __init__(self, layer):
        super().__init__()
        assert layer.out_f <= layer.tile_rows
        self.cfg = layer.cfg
        assert not self.cfg.x2_active_tiles
        self.register_buffer("weight",layer.unpack_rows(0,layer.out_f).detach())

    def forward(self,x,mode_p=None):
        assert mode_p is None and x.dtype==torch.float32
        return F.linear(x,self.weight)


@torch.no_grad()
def install_calibration_body(model):
    paths = [(name,module) for name,module in model.named_modules(remove_duplicate=False)
             if isinstance(module,PackedGroupLinear)]
    installed = {}
    for name,module in paths:
        if id(module) not in installed:
            installed[id(module)] = FrozenCalibrationLinear(module)
        parent,_,leaf = name.rpartition(".")
        model.get_submodule(parent)._modules[leaf] = installed[id(module)]
    assert len(installed)==69 and all(not p.requires_grad for p in model.parameters())


def verify_body_cpu(row):
    payload = torch.load(kd.EXPORT,map_location="cpu",weights_only=True)
    model = ce.load_payload(payload,device="cpu",tile_rows=4096)
    with np.load(ce.DATA,allow_pickle=False) as data:
        x,y = [torch.from_numpy(data[k][row:row+1,:16]) for k in ("x","y")]
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
        before,valid = ce.logits(model,x,y)
        install_calibration_body(model)
        after,_ = ce.logits(model,x,y)
    assert torch.equal(before,after)
    table = model.packed_embedding
    target = valid[:1]
    offset = torch.zeros_like(table.group_scales[target],requires_grad=True)
    table.group_scales = table.group_scales.index_copy(0,target,table.group_scales[target]*offset.exp())
    with sdpa_kernel(SDPBackend.MATH):
        scores,labels = ce.logits(model,x,y)
        derivative = torch.autograd.grad(F.cross_entropy(scores,labels),offset)[0]
    assert torch.isfinite(derivative).all() and torch.count_nonzero(derivative)
    result = dict(tokens=labels.numel(),logits_equal=True,scale_gradient=float(derivative.item()))
    print("P109_SCALE_CPU_PROBE",result,flush=True)
    return result


def learn(profile, initial, payload):
    model = ce.load_payload(payload,device="cuda",tile_rows=4096)
    with np.load(ce.DATA,allow_pickle=False) as bundle:
        x,y,held = [torch.from_numpy(bundle[k]).cuda() for k in ("x","y","held")]
    draws = torch.from_numpy(np.load(DRAWS,allow_pickle=False)).cuda()
    first = draws[0]
    with torch.no_grad():
        before,_ = ce.logits(model,x[first],y[first])
    install_calibration_body(model)
    with torch.no_grad():
        after,_ = ce.logits(model,x[first],y[first])
        assert torch.equal(before,after), "calibration-body logits differ before the edit"
    del before,after
    base_held = ce.evaluate(model,x,y,held)
    assert base_held==initial["packed_held"]

    table = model.packed_embedding
    base = table.group_scales.detach().clone()
    labels = y[draws]
    ids = torch.unique(labels[labels>=0])
    assert ids.numel()==profile["editable_rows"]
    assert torch.all(base[ids]>0)
    offsets = torch.nn.Parameter(torch.zeros_like(base[ids]))
    optimizer = torch.optim.Adam([offsets],lr=LR)
    checks = {"0":base_held}
    history = []

    def scales():
        return base.index_copy(0,ids,base[ids]*offsets.exp())

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for step, rows in enumerate(draws,1):
        free,total = torch.cuda.mem_get_info()
        if total-free>kd.online.DEVICE_BUDGET or (OUT/"STOP").exists() or datetime.now(ce.parent.CUTOFF.tzinfo)>=ce.parent.CUTOFF:
            raise RuntimeError(f"execution bound before scale update {step}")
        start = perf_counter()
        table.group_scales = scales()
        scores,targets = ce.logits(model,x[rows],y[rows])
        loss = F.cross_entropy(scores,targets)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_([offsets],1.,error_if_nonfinite=True)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        with torch.no_grad():
            offsets.clamp_(-LIMIT,LIMIT)
        torch.cuda.synchronize()
        history.append(dict(step=step,loss=float(loss.detach()),gradient_norm=float(norm),targets=targets.numel(),
                            seconds=perf_counter()-start))
        del scores,targets,loss,norm
        if step in (16,32,STEPS):
            with torch.no_grad():
                table.group_scales = scales()
            checks[str(step)] = ce.evaluate(model,x,y,held)
            print("P109_SCALE_TRAIN",step,checks[str(step)],flush=True)
    assert sum(r["targets"] for r in history)==profile["draw_targets"]
    final = checks[str(STEPS)]
    total_top = sum(v["correct"] for v in final.values())
    old_top = sum(v["correct"] for v in base_held.values())
    nll = {lang:final[lang]["nll"]-base_held[lang]["nll"] for lang in final}
    improves = max(nll.values())<=0 and total_top>old_top
    result = dict(held_by_update=checks,history=history,held_nll_delta=nll,top1=total_top,base_top1=old_top,
                  recovery_gate=improves and total_top>=201 and all(final[k]["correct"]>=base_held[k]["correct"] for k in final),
                  improves=improves,training_peak_allocated=torch.cuda.max_memory_allocated(),
                  training_peak_reserved=torch.cuda.max_memory_reserved(),
                  median_update_seconds=median(r["seconds"] for r in history[4:]),checkpoint_writes=0)
    with torch.no_grad():
        edited = scales()
        changed = torch.where(edited.ne(base).flatten())[0]
        assert torch.isin(changed,ids).all() and torch.isfinite(edited).all()
        multiplier = offsets.exp()
        result.update(changed_rows=len(changed),multiplier=[float(multiplier.min()),float(multiplier.max())])
    if improves:
        new = dict(payload, embedding=dict(payload["embedding"],scales=edited.cpu().contiguous()),
                   provenance=dict(payload["provenance"], tag=TAG, calibration_steps=STEPS,
                                   profile_sha256=ce.qwen.digest(PROFILE), previous_packed_sha256=initial["packed_sha256"]))
        with EXPORT.open("xb") as stream:
            torch.save(new,stream)
        reread = torch.load(EXPORT,map_location="cpu",weights_only=True)
        assert all(reread[k]==payload[k] for k in ("schema","cfg","embedding_format","arithmetic"))
        assert torch.equal(reread["embedding"]["codes"],payload["embedding"]["codes"])
        assert all(a["paths"]==b["paths"] and all(torch.equal(a["weight"][k],b["weight"][k]) for k in ("codes","scales"))
                   for a,b in zip(reread["matrices"],payload["matrices"],strict=True))
        assert all(a["paths"]==b["paths"] and torch.equal(a["tensor"],b["tensor"])
                   for a,b in zip(reread["rest"],payload["rest"],strict=True))
        packed = ce.load_payload(reread,device="cuda",tile_rows=4096)
        restored = ce.evaluate(packed,x,y,held)
        assert restored==final
        result.update(packed_held=restored,packed_bytes=EXPORT.stat().st_size,packed_sha256=ce.qwen.digest(EXPORT))
    return result


def run():
    assert ce.idle() and torch.cuda.device_count()==1 and torch.cuda.mem_get_info()[0]>=13_000*2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.set_float32_matmul_precision("highest")
    profile = ce.qwen.load(PROFILE)
    initial = verify(profile)
    payload = torch.load(kd.EXPORT,map_location="cpu",weights_only=True)
    device = OUT/"device_100ms.csv"
    ce.qwen.write(OUT/"active.json",dict(tag=TAG,pid=os.getpid()))
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*ce.DEVICE,f"--loop-ms={ce.INTERVAL_MS}"),stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                result = learn(profile,initial,payload)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    verify(profile)
    samples = ce.read_samples(device)
    assert samples
    result.update(device_peak=max(samples,key=lambda v:v["occupied_mib"]),device_samples=len(samples),
                  profile_sha256=ce.qwen.digest(PROFILE),source_preserved=True)
    ce.qwen.write(OUT/"report.json",result)
    print("P109_SCALE_RESULT",result["held_nll_delta"],result["top1"],result["recovery_gate"],result["device_peak"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(ce.parent.CUTOFF.tzinfo)+timedelta(seconds=400)<ce.parent.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (prepare if phase=="prepare" else run)()
