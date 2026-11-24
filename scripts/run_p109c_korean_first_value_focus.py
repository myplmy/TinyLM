"""Focus the full vocabulary loss on failed Korean first numeric tokens."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from scripts import run_p109c_bilingual_value_transfer as paired


TAG = "p109c_korean_first_value_focus_gpu_v2_20261121"
OUT = paired.OUT.with_name(TAG)
WARM = paired.OUT/"shared_wide_start.pt"
trial,data,control,baseline,bridge = paired.trial,paired.data,paired.control,paired.baseline,paired.bridge
WEIGHT = .10


def focus_loss(logits, first, labels, linked):
    candidate = logits[first[::2]]
    target = labels[first[::2]]
    use = linked[::2] & candidate.detach().argmax(dim=1).ne(target)
    pieces = F.cross_entropy(candidate,target,reduction="none")
    return (pieces * use).sum(),use.sum()


def verify_loss():
    values = torch.tensor(((1.,2.),(1.,3.),(3.,1.),(3.,2.)),requires_grad=True)
    loss,hits = focus_loss(values,torch.arange(4),torch.zeros(4,dtype=torch.long),torch.ones(4,dtype=torch.bool))
    grad,=torch.autograd.grad(loss,values)
    if hits.item()!=1 or not grad[0].abs().any() or grad[1:].abs().any():
        raise ValueError("the focus loss must be confined to the failed Korean first token")


def prepare():
    report_path=paired.OUT/"report.json"
    terminal_path=paired.OUT/"supervisor.json"
    previous,terminal=trial.read_json(report_path),trial.read_json(terminal_path)
    archived=trial.read_json(baseline.OUT/"report.json")
    base=bridge.base_contract()
    if (terminal["returncode"] or terminal["stop_reason"] or previous["plan"]["base"]!=base
            or trial.file_sha(WARM)!=previous["warm_checkpoint"]
            or tuple(data.authored.LANGUAGES)!=("ko","en")):
        raise ValueError("requires the completed shared parentless warm comparison")
    expected=archived["stages"][:2]
    actual=previous["warm_phases"]
    warm_losses_match=all(a["losses"][:3]==b["ce"] for a,b in zip(actual,expected,strict=True))
    verify_loss()
    return dict(tag=TAG,source=trial.file_sha(Path(__file__)),prior=trial.file_sha(report_path),
                terminal=trial.file_sha(terminal_path),base=base,warm=previous["warm_checkpoint"],
                warm_state=previous["warm_state"],warm_steps=previous["plan"]["warm_updates"],
                warm_logged_losses_match=warm_losses_match,weight=WEIGHT,cross=previous["plan"]["cross"])


def worker(plan,fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if prepare()!=plan:
        raise ValueError("the sealed focus condition changed")
    tok,special,arrays,phases,_=control.profile()
    phase=phases[-1]
    if phase!=plan["base"]["stages"][-1]:
        raise ValueError("the original wide training phase changed")
    cut=slice(phase["offset"],phase["offset"]+phase["rows"])
    x,y,context=paired.gpu_arrays([a[cut] for a in arrays])
    with np.load(baseline.INPUT/"sites.npz",allow_pickle=False) as f:
        sites=torch.as_tensor(f["sites"][cut],device="cuda",dtype=torch.long)
    snapshot=torch.load(WARM,weights_only=True,map_location="cpu")
    model=baseline.TiedMLPTransformer(trial.make_config()).to("cuda")
    selector=baseline.ValueLink(model.cfg.dim).to("cuda")
    model.load_state_dict(snapshot["model"])
    selector.load_state_dict(snapshot["selector"])
    parameters=[*model.parameters(),*selector.parameters()]
    optimizer=torch.optim.AdamW(parameters,lr=.0015,weight_decay=.01,fused=True)
    optimizer.load_state_dict(snapshot["optimizer"])
    torch.set_rng_state(snapshot["cpu_rng"])
    torch.cuda.set_rng_state(snapshot["cuda_rng"])
    model.clear_quant()
    restored = json.dumps(paired.fingerprint(model,selector,optimizer),sort_keys=True)
    if restored!=json.dumps(plan["warm_state"],sort_keys=True):
        raise ValueError("focus did not restore the identical shared warm state")
    del snapshot
    count=[0,0,0]
    used=torch.zeros((),device="cuda",dtype=torch.long)
    sums=torch.zeros(4,device="cuda")
    step=plan["warm_steps"]
    started=time.perf_counter()
    for offset in range(0,len(x),data.BATCH):
        block=slice(offset,offset+data.BATCH)
        answer,prefix,loc=y[block],context[block],sites[block]
        keep,keep_prefix=answer.ne(baseline.IGNORE),prefix.ne(baseline.IGNORE)
        labels,prompt=answer[keep],prefix[keep_prefix]
        length=keep.sum(dim=1)
        first=length.cumsum(0)-length
        step+=1
        optimizer.param_groups[0]["lr"]=.0015*min(1.,step/64)*(1-.7*(step/data.UPDATES)**2)
        model.set_anneal(min(1.,step/(.6*data.UPDATES)))
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cuda",dtype=torch.bfloat16):
            hidden=model(x[block],return_hidden=True)
            scores=model._head_logits(hidden[keep]).float()
            ce=F.cross_entropy(scores,labels,reduction="sum")
            nll,_=control.target_nll(model,hidden[keep_prefix].unsqueeze(0),prompt.unsqueeze(0),rows=control.CE_ROWS)
            context_ce=nll.sum()
            selection=selector(hidden,loc).float()
            location_ce=F.cross_entropy(selection,loc[:,-1],reduction="sum")
            focus,applied=focus_loss(scores,first,labels,selection.detach().argmax(dim=1)==loc[:,-1])
            loss=(ce/labels.numel()+control.WEIGHT*context_ce/prompt.numel()+baseline.WEIGHT*location_ce/len(answer)
                  +WEIGHT*focus/(len(answer)//2))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True)
        optimizer.step()
        used+=applied
        count[0]+=labels.numel()
        count[1]+=prompt.numel()
        count[2]+=len(answer)
        sums+=torch.stack([v.detach() for v in (ce,context_ce,location_ce,focus)])
        if step%128==0:
            print(json.dumps(dict(step=step,applied=used.item(),seconds=time.perf_counter()-started)),flush=True)
    if step!=data.UPDATES or count!=[phase["targets"],phase["context_targets"],phase["rows"]]:
        raise ValueError("training changed the original supervised inputs")
    cross,(_,_,_,translations)=paired.crossed.prepare()
    if cross!=plan["cross"]:
        raise ValueError("the bilingual test panel changed")
    val=trial.read_json(baseline.INPUT/"validation.json")
    orig=trial.read_json(data.DATA/"evaluation.json")
    report=paired.evaluate(model,selector,tok,special,val,orig,translations,OUT)
    model_state={k:v.detach().cpu() for k,v in model.state_dict().items()}
    final=OUT/"foundation.pt"
    with final.open("xb") as file:
        torch.save(dict(tag=TAG,parent=None,step=step,warm=plan["warm"],config=asdict(model.cfg),model=model_state,
                        train_head={k:v.detach().cpu() for k,v in selector.state_dict().items()}),file)
    result=dict(plan=plan,updates=step-plan["warm_steps"],counts=count,focused_rows=int(used.item()),assessment=report,
                ce=[v/n for v,n in zip(sums.tolist(),(*count,count[2]//2),strict=True)],
                checkpoint=trial.file_sha(final),state=trial.state_sha(model_state),
                peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,elapsed=time.perf_counter()-started)
    trial.publish(OUT/"report.json",result)
    print(json.dumps(dict(assessment=report,focused_rows=result["focused_rows"])),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    plan=prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires an approved deadline and a sealed focus comparison")
    return baseline.owner.supervise(worker,(plan,),OUT,args.stop_by,
                                    authorization_end=bridge.AUTHORIZATION_END,min_seconds=900)


if __name__=="__main__":
    raise SystemExit(main())
