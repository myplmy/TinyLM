"""Fit the packed EOS row on actual authored document boundaries."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path
import random
import subprocess
from time import perf_counter

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_qwen35_248k_scale_calibration as calibrated
from scripts.p014e_packed_g128 import pack_weight
from tinylm.model.ternary import ternary_g


ce = calibrated.ce
TAG = "p109_qwen35_248k_eos_row_v2_20261119"
OUT = ce.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
EXPORT = OUT / "eos_5trit.pt"
FIT_DOCS_PER_LANG, STEPS, LR, SEED = 48, 128, .005, 65248044


def verify(profile):
    assert all(ce.qwen.digest(ce.ROOT/p)==s for p,s in profile["pins"].items())
    report = ce.qwen.load(calibrated.OUT/"report.json")
    assert report["recovery_gate"] and report["packed_sha256"]==ce.qwen.digest(calibrated.EXPORT)
    return report


def prepare():
    docs = ce.qwen.load(ce.qwen.AUTHORED)["data"]["documents"]
    with np.load(ce.DATA,allow_pickle=False) as original:
        x,y,held,previous = [original[k] for k in ("x","y","held","draws")]
    seen = set(previous.ravel()) | set(np.load(calibrated.DRAWS,allow_pickle=False).ravel())
    available = [[i for i,d in enumerate(docs) if d["split"]=="train" and d["language"]==lang and i not in seen]
                 for lang in ("en","ko")]
    rng = random.Random(SEED)
    selected = [rng.sample(group,FIT_DOCS_PER_LANG) for group in available]
    fit = [group[:40] for group in selected]
    development = [group[40:] for group in selected]
    lengths = (y>=0).sum(1)
    assert np.array_equal(y>=0,np.arange(ce.WIDTH)[None,:]<lengths[:,None])
    assert (x[np.arange(len(x)),lengths]==ce.EOS).all() and not (x[y>=0]==ce.EOS).any()
    all_fit = sum(selected,[])
    assert len(set(all_fit))==96 and not (set(all_fit)&set(held.ravel()))
    pool = int(sum(lengths[group].sum()+len(group) for group in available))
    train = int(lengths[all_fit].sum()+len(all_fit))
    assert pool>=2*train
    files = [Path(__file__),ce.DATA,ce.qwen.AUTHORED,calibrated.DRAWS,calibrated.EXPORT,
             calibrated.OUT/"report.json",ce.ROOT/"scripts/p014e_packed_g128.py",
             ce.ROOT/"tinylm/model/ternary.py",ce.ROOT/"tinylm/model/transformer.py"]
    profile = dict(tag=TAG,approval="WIP176",row=ce.EOS,fit=fit,development=development,
                   held=held.tolist(),pool=pool,draw=train,
                   steps=STEPS,lr=LR,pins={str(p.relative_to(ce.ROOT)):ce.qwen.digest(p) for p in files})
    verify(profile)
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    ce.qwen.write(PROFILE,profile)
    print("P109_EOS_ROW_CPU",len(all_fit),len(held.ravel()),train,pool,flush=True)


@dataclass
class Panel:
    position: torch.Tensor
    other_max: torch.Tensor
    other_choice: torch.Tensor
    other_logmass: torch.Tensor
    target_logit: torch.Tensor
    target: torch.Tensor
    document: torch.Tensor
    baseline_eos: torch.Tensor


@torch.no_grad()
def collect(model,x,y,rows):
    values = [[] for _ in range(8)]
    for block in rows.split(ce.BATCH):
        xb,yb = x[block].clone(),y[block].clone()
        lengths = yb.ge(0).sum(1)
        doc = torch.arange(len(block),device=xb.device)
        xb[doc,lengths] = yb[doc,lengths-1]
        yb[doc,lengths] = ce.EOS
        mask = yb>=0
        hidden = model(xb,return_hidden=True)[mask]
        projected = F.linear(hidden,model._emb_up_w().t())
        scores = model._head_logits(hidden)[:,:ce.ASSIGNED].contiguous()
        target = yb[mask]
        eos_before = scores[:,ce.EOS].clone()
        target_logit = scores.gather(1,target[:,None]).flatten()
        scores[:,ce.EOS] = -torch.inf
        other,other_id = scores.max(1)
        batch_values = (projected,other,other_id,scores.logsumexp(1),target_logit,
                        target,block[:,None].expand_as(yb)[mask],eos_before)
        for out,value in zip(values,batch_values,strict=True):
            out.append(value)
    return Panel(*(torch.cat(out) for out in values))


def choose_eos(panel,eos):
    return (eos>panel.other_max)|((eos==panel.other_max)&(panel.other_choice>ce.EOS))


def select_multiplier(panel,row):
    multipliers = torch.arange(65,116,device=row.device,dtype=row.dtype)/100
    scores = multipliers[:,None]*F.linear(panel.position,row).flatten()[None,:]
    selection = choose_eos(panel,scores)
    ends = panel.target==ce.EOS
    correct = selection[:,ends].sum(1).tolist()
    premature = selection[:,~ends].sum(1).tolist()
    index = max(range(len(correct)),key=lambda i:(-premature[i],correct[i],-abs(i-35)))
    return multipliers[index], dict(end_correct=correct[index],premature=premature[index],
        ends=int(ends.sum()),ordinary=int((~ends).sum()),multiplier=float(multipliers[index]))


def summarize(panel, eos):
    ends = panel.target==ce.EOS
    picked = choose_eos(panel,eos)
    correct = panel.other_choice.eq(panel.target)&~picked&~ends
    nll = (torch.logaddexp(panel.other_logmass,eos)-panel.target_logit)[~ends]
    return dict(ends=int(ends.sum()),end_correct=int((picked&ends).sum()),
                premature=int((picked&~ends).sum()),ordinary_targets=int((~ends).sum()),
                ordinary_correct=int(correct.sum()),ordinary_nll=float(nll.mean()),
                end_documents=panel.document[picked&ends].tolist())


def learn(profile, initial):
    payload = torch.load(calibrated.EXPORT,map_location="cpu",weights_only=True)
    model = ce.load_payload(payload,device="cuda",tile_rows=4096)
    with np.load(ce.DATA,allow_pickle=False) as arrays:
        x,y = [torch.from_numpy(arrays[k]).cuda() for k in ("x","y")]
    fit = torch.tensor(sum(profile["fit"],[]),device=x.device)
    dev = torch.tensor(sum(profile["development"],[]),device=x.device)
    held = torch.tensor(profile["held"],device=x.device)
    start = perf_counter()
    train = collect(model,x,y,fit)
    control = collect(model,x,y,dev)
    assert len(train.target)+len(control.target)==profile["draw"]
    evaluation = {lang:collect(model,x,y,rows) for lang,rows in zip(("en","ko"),held,strict=True)}
    torch.cuda.synchronize()
    features_seconds = perf_counter()-start
    row = torch.tensor([ce.EOS],device=x.device)
    start_weight = model.packed_embedding.rows(row).detach()
    norm = start_weight.square().sum().clamp_min(1e-8)
    before = {lang:summarize(panel,panel.baseline_eos) for lang,panel in evaluation.items()}
    assert all(before[lang]["ordinary_correct"]==initial["packed_held"][lang]["correct"] for lang in before)
    for panel in (train,control,*evaluation.values()):
        assert (F.linear(panel.position,start_weight).flatten()-panel.baseline_eos).abs().max()<.001
    master = torch.nn.Parameter(start_weight.clone())
    optimizer = torch.optim.Adam([master],lr=LR)
    mask = train.target==ce.EOS
    history = []
    started = perf_counter()
    for step in range(1,STEPS+1):
        if (OUT/"STOP").exists() or datetime.now(ce.parent.CUTOFF.tzinfo)>=ce.parent.CUTOFF:
            raise RuntimeError("owned STOP or deadline")
        q = ternary_g(master,master.size(1),model.cfg)
        margin = F.linear(train.position,q).flatten()-train.other_max
        negatives = margin[~mask]
        pos,neg = F.softplus(1-margin[mask]).mean(),F.softplus(1+negatives).mean()
        hardest = F.softplus(2+negatives.topk(32).values).mean()
        loss = (pos+neg)/2+.75*hardest+.01*(master-start_weight).square().sum()/norm
        loss.backward()
        grad = torch.nn.utils.clip_grad_norm_([master],1.,error_if_nonfinite=True)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        history.append(dict(step=step,loss=float(loss.detach()),grad=float(grad)))
    optimizer_seconds = perf_counter()-started
    with torch.no_grad():
        changed_row = ternary_g(master,master.size(1),model.cfg)
        multiplier, selection = select_multiplier(control,changed_row)
        changed_row = changed_row*multiplier
        final = {lang:summarize(panel,F.linear(panel.position,changed_row).flatten())
                 for lang,panel in evaluation.items()}
    end = sum(r["end_correct"] for r in final.values())
    early = sum(r["premature"] for r in final.values())
    missed = sum(before[lang]["ordinary_correct"]-v["ordinary_correct"] for lang,v in final.items())
    passed = end>=24 and min(r["end_correct"] for r in final.values())>=8 and early<=3 and missed<=2
    entry = pack_weight(changed_row,changed_row.size(1),tile_rows=1)
    result = dict(baseline=before,held=final,end_correct=end,premature=early,lost_ordinary=missed,
                  candidate=passed,features_seconds=features_seconds,optimizer_seconds=optimizer_seconds,
                  history=history,development=selection,checkpoint_writes=0,
                  row_record=dict(codes=entry["codes"].flatten().tolist(),scale=float(entry["scales"].item())))
    if passed:
        table = payload["embedding"]
        codes,scales = table["codes"].clone(),table["scales"].clone()
        codes[ce.EOS:ce.EOS+1] = entry["codes"]
        scales[ce.EOS:ce.EOS+1] = entry["scales"]
        assert torch.equal(codes[:ce.EOS],table["codes"][:ce.EOS])
        assert torch.equal(codes[ce.EOS+1:],table["codes"][ce.EOS+1:])
        new = dict(payload,embedding=dict(table,codes=codes,scales=scales),provenance=dict(
            payload["provenance"],tag=TAG,profile_sha256=ce.qwen.digest(PROFILE),eos_row_steps=STEPS))
        with EXPORT.open("xb") as stream:
            torch.save(new,stream)
        restored = ce.load_payload(torch.load(EXPORT,map_location="cpu",weights_only=True),device="cuda",tile_rows=4096)
        with torch.no_grad():
            for lang,rows in zip(("en","ko"),held,strict=True):
                panel = collect(restored,x,y,rows)
                actual = summarize(panel,panel.baseline_eos)
                assert all(actual[k]==final[lang][k] for k in ("end_correct","premature","ordinary_correct","end_documents"))
                assert torch.equal(panel.other_choice,evaluation[lang].other_choice)
                final[lang]["ordinary_nll_reloaded"] = actual["ordinary_nll"]
        result.update(packed_sha256=ce.qwen.digest(EXPORT),packed_bytes=EXPORT.stat().st_size)
    return result


def run():
    assert ce.idle() and torch.cuda.device_count()==1
    assert torch.cuda.mem_get_info()[0]>=13_000*2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.set_float32_matmul_precision("highest")
    profile = ce.qwen.load(PROFILE)
    initial = verify(profile)
    device = OUT/"device_100ms.csv"
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*ce.DEVICE,f"--loop-ms={ce.INTERVAL_MS}"),stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                result = learn(profile,initial)
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
    print("P109_EOS_ROW_RESULT",result["end_correct"],result["premature"],result["lost_ordinary"],
          result["candidate"],result["device_peak"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(ce.parent.CUTOFF.tzinfo)+timedelta(seconds=180)<ce.parent.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (prepare if phase=="prepare" else run)()
