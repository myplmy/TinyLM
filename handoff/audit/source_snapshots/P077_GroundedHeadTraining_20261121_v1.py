"""Train only the grounded selector on frozen long-context features."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys

import torch
import torch.nn.functional as F

from scripts import diag_p077_grounded_value_readout as eval_readout
from scripts import run_p077_grounded_context_training as training


wide = eval_readout.wide
trial = wide.trial
foundation = wide.foundation
TAG = "p077_grounded_value_readout_head_train_gpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)
LR = .0015


def prepare():
    control, (tok,special,fixtures) = eval_readout.prepare()
    model, (_,_,_,_,_,training_rows) = training.prepare()
    before = trial.read_json(eval_readout.OUT/"report.json")
    terminal = trial.read_json(eval_readout.OUT/"supervisor.json")
    if before["plan"]!=control or terminal["stop_reason"] or terminal["returncode"]:
        raise ValueError("requires the completed fixed representation readout control")
    if len(training_rows)!=training.STEPS:
        raise ValueError("the paired training sequence is incomplete")
    receipt = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),control=control,training=model,
                   first_readout_sha256=trial.file_sha(eval_readout.OUT/"report.json"),updates=training.STEPS,lr=LR)
    return receipt,(tok,special,fixtures,training_rows)


@torch.no_grad()
def extract(model, tokens, spots):
    with torch.autocast("cuda",dtype=torch.bfloat16):
        hidden = model(tokens,return_hidden=True)
        rows = torch.arange(tokens.shape[0],device=tokens.device)
        points = hidden[rows[:,None],spots[:,:5]].float()
    return points


def worker(plan, fraction):
    torch.set_num_threads(1)
    checked,(tok,special,fixtures,rows) = prepare()
    if checked!=plan:
        raise ValueError("sealed head training changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    state_sha = plan["control"]["base"]["state_sha256"]
    if trial.state_sha(state["model"])!=state_sha:
        raise ValueError("unexpected frozen representation")
    cfg = replace(wide.TMTConfig(**state["config"]),max_seq_len=eval_readout.LIMIT)
    model = wide.TiedMLPTransformer(cfg).to("cuda").eval()
    model.load_state_dict(state["model"])
    model.requires_grad_(False)
    model.freeze_quant()
    head = foundation.ValueLink(cfg.dim).to("cuda")
    head.load_state_dict(state["train_head"])
    optimizer = torch.optim.AdamW(head.parameters(),lr=LR,weight_decay=.01,fused=True)
    locations = torch.arange(5,device="cuda").expand(training.BATCH,-1)
    cross_checks = []
    history = []
    running = torch.zeros((),device="cuda")
    for step,(xs,_,points) in enumerate(rows,1):
        tokens = torch.as_tensor(xs["mixed_positions"].astype("int64"),device="cuda")
        sites = torch.as_tensor(points["mixed_positions"],dtype=torch.long,device="cuda")
        encoded = extract(model,tokens,sites)
        if step in (1,2):
            visible = torch.arange(tokens.shape[1],device="cuda")[None,:] <= sites[:,0,None]
            alternate = extract(model,torch.where(visible,tokens,special["<pad>"]),sites)
            check = torch.equal(encoded,alternate)
            cross_checks.append(dict(step=step,width=tokens.shape[1],identical=check))
            if not check:
                raise ValueError("the evidence selector can see tokens after the question")
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(head(encoded,locations),sites[:,-1])
        loss.backward()
        optimizer.step()
        running += loss.detach()
        if step%48==0:
            item = dict(step=step,mean_ce=running.item()/48)
            history.append(item)
            print(json.dumps(item),flush=True)
            running.zero_()
    if trial.state_sha(model.state_dict())!=state_sha:
        raise ValueError("head-only optimization unexpectedly changed the frozen body")
    head.eval()
    counts = {}
    for arm,records in fixtures.items():
        predictions = eval_readout.readout(model,head,tok,special["<|im_end|>"],records)
        values = [dict(selector=pred,root=item["root"],language=item["language"],side=item["side"],gold=item["expected"])
                  for item,pred in zip(records,predictions,strict=True)]
        arm_count = {}
        for lang in ("ko","en"):
            pairs = [(a,b) for a,b in zip(values[::2],values[1::2],strict=True) if a["language"]==lang]
            arm_count[lang] = dict(both=sum(a["selector"]["correct"] and b["selector"]["correct"] for a,b in pairs),
                                   changed_slot=sum(a["selector"]["choice"]!=b["selector"]["choice"] for a,b in pairs),
                                   individual=sum(r["selector"]["correct"] for p in pairs for r in p))
        counts[arm] = arm_count
        trial.publish(OUT/f"{arm}.json",dict(rows=values,counts=arm_count))
        print(json.dumps(dict(arm=arm,counts=arm_count)),flush=True)
    head_path = OUT/"trained_head.pt"
    with head_path.open("xb") as stream:
        torch.save(dict(train_head={k:v.detach().cpu() for k,v in head.state_dict().items()},body_state_sha256=state_sha,
                        source_checkpoint_sha256=plan["control"]["base"]["checkpoint_sha256"],tag=TAG),stream)
    trial.publish(OUT/"report.json",dict(plan=plan,counts=counts,history=history,post_question_invariance=cross_checks,
                  weights_sha256=trial.file_sha(head_path),body_sha256=state_sha,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or trial.read_json(args.receipt)!=plan or args.stop_by is None:
        parser.error("requires the sealed head experiment and cutoff")
    return wide.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=180)


if __name__=="__main__":
    sys.exit(main())
