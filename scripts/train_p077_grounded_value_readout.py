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
ATTENTION_TAG = "p077_grounded_value_readout_last_attention_gpu_v1_20261121"
ATTENTION_OUT = OUT.with_name(ATTENTION_TAG)
ATTENTION_LR = .0002
ORIGINAL_SOURCE = trial.ROOT/"handoff/audit/source_snapshots/P077_GroundedHeadTraining_20261121_v1.py"


def prepare(attention=False):
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
    if attention:
        reference = OUT/"report.json"
        head_only = trial.read_json(reference)
        terminal = trial.read_json(OUT/"supervisor.json")
        if terminal["returncode"] or terminal["stop_reason"] or head_only["plan"]!=dict(receipt,source_sha256=trial.file_sha(ORIGINAL_SOURCE)):
            raise ValueError("the completed head-only comparator differs from the new experiment")
        receipt.update(tag=ATTENTION_TAG,head_only_sha256=trial.file_sha(reference),attention_lr=ATTENTION_LR)
    return receipt,(tok,special,fixtures,training_rows)


def extract(model, tokens, spots):
    with torch.autocast("cuda",dtype=torch.bfloat16):
        hidden = model(tokens,return_hidden=True)
        rows = torch.arange(tokens.shape[0],device=tokens.device)
        points = hidden[rows[:,None],spots[:,:5]].float()
    return points


def worker(plan, attention, fraction):
    torch.set_num_threads(1)
    checked,(tok,special,fixtures,rows) = prepare(attention)
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
    trainable = {}
    if attention:
        layer = model.layers[-1].attn_mod
        selected = (layer.q_proj.weight,layer.o_proj.weight)
        trainable = {name:p.requires_grad_() for name,p in model.named_parameters() if any(p is x for x in selected)}
        if len(trainable)!=2:
            raise ValueError("expected the two final attention projections")
        route = model.visit_schedule()
        model.train()
        if model.visit_schedule()!=route:
            raise ValueError("changing the final weights must preserve the visit route")
    else:
        model.freeze_quant()
    directory = ATTENTION_OUT if attention else OUT
    head = foundation.ValueLink(cfg.dim).to("cuda")
    head.load_state_dict(state["train_head"])
    groups = [{"params":head.parameters()}]
    if attention:
        groups.append(dict(params=list(trainable.values()),lr=ATTENTION_LR))
    optimizer = torch.optim.AdamW(groups,lr=LR,weight_decay=.01,fused=True)
    locations = torch.arange(5,device="cuda").expand(training.BATCH,-1)
    cross_checks = []
    history = []
    running = torch.zeros((),device="cuda")
    for step,(xs,_,points) in enumerate(rows,1):
        tokens = torch.as_tensor(xs["mixed_positions"].astype("int64"),device="cuda")
        sites = torch.as_tensor(points["mixed_positions"],dtype=torch.long,device="cuda")
        with torch.set_grad_enabled(attention):
            encoded = extract(model,tokens,sites)
        if step in (1,2):
            visible = torch.arange(tokens.shape[1],device="cuda")[None,:] <= sites[:,0,None]
            with torch.no_grad():
                alternate = extract(model,torch.where(visible,tokens,special["<pad>"]),sites)
            check = torch.equal(encoded,alternate)
            cross_checks.append(dict(step=step,width=tokens.shape[1],identical=check))
            if not check:
                raise ValueError("the evidence selector can see tokens after the question")
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(head(encoded,locations),sites[:,-1])
        loss.backward()
        if attention and step==1 and any(p.grad is None or not bool(torch.isfinite(p.grad).all()) or not bool(p.grad.any())
                                        for p in trainable.values()):
            raise RuntimeError("a final attention projection did not receive an effective gradient")
        optimizer.step()
        running += loss.detach()
        if step%48==0:
            item = dict(step=step,mean_ce=running.item()/48)
            history.append(item)
            print(json.dumps(item),flush=True)
            running.zero_()
    final = {name:p.detach().cpu() for name,p in model.state_dict().items()}
    changed = {name:value for name,value in final.items() if not torch.equal(state["model"][name],value)}
    if set(changed)!=set(trainable):
        raise ValueError("weights outside the intended trainable scope changed, or a planned weight was untouched")
    model.eval()
    model.clear_quant()
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
        trial.publish(directory/f"{arm}.json",dict(rows=values,counts=arm_count))
        print(json.dumps(dict(arm=arm,counts=arm_count)),flush=True)
    short = None
    if attention:
        archive = trial.read_json(foundation.OUT/"wide_eval.json")["rows"]
        short = training.score(model,tok,special,archive,[p for row in archive for p in row["prompts"]])
        trial.publish(directory/"short.json",short)
    head_path = directory/"trained_head.pt"
    with head_path.open("xb") as stream:
        torch.save(dict(train_head={k:v.detach().cpu() for k,v in head.state_dict().items()},changed_body=changed,
                        body_state_sha256=trial.state_sha(final),
                        source_checkpoint_sha256=plan["control"]["base"]["checkpoint_sha256"],tag=plan["tag"]),stream)
    trial.publish(directory/"report.json",dict(plan=plan,counts=counts,history=history,post_question_invariance=cross_checks,
                  weights_sha256=trial.file_sha(head_path),body_sha256=trial.state_sha(final),changed_body=list(changed),
                  short_counts=None if short is None else short["counts"],
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--last-attention",action="store_true")
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare(args.last_attention)
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or trial.read_json(args.receipt)!=plan or args.stop_by is None:
        parser.error("requires the sealed head experiment and cutoff")
    output = ATTENTION_OUT if args.last_attention else OUT
    return wide.owner.supervise(worker,(plan,args.last_attention),output,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=180)


if __name__=="__main__":
    sys.exit(main())
