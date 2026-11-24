"""Protected direct edits on a tied training weight at two actual update boundaries."""

import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys

import torch
import torch.nn.functional as F

from scripts import p108b_target_protection as protection
from scripts import p109_cuda_owner as owner
from scripts import run_p109c_correction_grounded as reference
from scripts import run_p109c_correction_scratch as trial
from scripts import run_p109c_table_value_link as foundation
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE, pad_records


TAG = "p108_periodic_tied_head_gpu_v1_20261121"
OUT = trial.DATA.parent / TAG
CONTROL = reference.OUT / "correction_only.json"
SITES = (4, 12)
FRACTIONS = (.05, .10, .20, .30)
VIEWS = ("single", "correction")


def prepare():
    terminal = trial.read_json(reference.OUT/"supervisor.json")
    if terminal["returncode"] != 0 or terminal["stop_reason"] is not None:
        raise ValueError("the matched no-edit comparison must be complete")
    base = reference.prepare()
    control = trial.read_json(CONTROL)
    if control["epochs"][-1]["steps"] != base["profile"]["CORRECTION_ONLY"]["updates"]:
        raise ValueError("wrong reference optimizer schedule")
    _, _, cases, _, _ = trial.load_cases()
    val = sorted(cases["validation"])
    check = torch.eye(3,dtype=torch.float64)
    _, fixture = protection.candidate(check[:,:1],torch.ones(1,1),check[1:2],.1,protect=True)
    if fixture["normalized_protection_residual"] > 1e-7:
        raise ValueError("protected-write solver fixture failed")
    paths = [Path(__file__),Path(protection.__file__),Path(protection.existing.__file__)]
    return dict(tag=TAG, base=base, sources={str(p.relative_to(trial.ROOT)):trial.file_sha(p) for p in paths},
                control_sha256=trial.file_sha(CONTROL), fit=val[:16], guard=val[16:40], audit=val[40:],
                boundaries=list(SITES),fractions=list(FRACTIONS))


def correct(row, view):
    return row[view]["answer"] == row["gold"] and row[view]["eot"]


def existing_answers(result):
    return {(root,view) for root,row in result["rows"].items() for view in VIEWS if correct(row,view)}


@torch.inference_mode()
def projected(model, encoded):
    x = torch.tensor([encoded.x],device="cuda")
    y = torch.tensor([encoded.y],device="cuda")
    take = y.ne(IGNORE)
    with torch.autocast("cuda",dtype=torch.bfloat16):
        h = model(x,return_hidden=True)[take]
        keys = F.linear(h,model._emb_up_w().t())
        logits = model._head_logits(h)
    return keys.float(), logits.float(), y[take]


def write_candidates(model, record, end_id):
    keys, logits, labels = projected(model, record)
    target = labels.ne(end_id) & logits.argmax(-1).ne(labels)
    ids = labels[target].unique(sorted=True)
    if not ids.numel():
        return None
    scores = logits.max(-1).values - logits.gather(-1,labels[:,None]).squeeze(-1)
    values = logits.new_zeros((len(ids),len(labels)))
    for index,token in enumerate(ids):
        active = target & labels.eq(token)
        values[index,active] = scores[active]+.2
    return ids, keys.T, values


def attempt_edit(model,optimizer,tok,special,val,plan):
    model.eval()
    model.clear_quant()
    optimizer.zero_grad(set_to_none=True)
    owned = model.emb.weight
    if model.embedding_quantized() is not None or model._emb_w() is not owned:
        raise ValueError("the editable FP32 output table must be tied to the actual input lookup")
    controls = {root:val[root] for root in (*plan["fit"],*plan["guard"])}
    before = trial.evaluate(model,tok,special,controls)
    kept = existing_answers(before)
    moments = trial.state_sha(optimizer.state_dict())
    anchors = [(i,v) for i in plan["guard"] for v in VIEWS if (i,v) in kept][:12]
    if not anchors:
        return dict(applied=False,reason="no correct protected answer",before=before,optimizer_sha256=moments)
    fixed = torch.cat([projected(model,val[root]["records"][view])[0] for root,view in anchors]).cpu()
    attempts = []
    accepted = None
    after = before
    for target in [i for i in plan["fit"] if (i,"correction") not in kept][:4]:
        encoded = val[target]["records"]["correction"]
        frame = write_candidates(model,encoded,special["<|im_end|>"])
        if frame is None:
            attempts.append(dict(target=target,reason="no wrong content position"))
            continue
        ids, keys, values = frame
        keys, values = keys.cpu(), values.cpu()
        pristine = owned[ids].detach().clone()
        for scale in FRACTIONS:
            budget = scale*pristine.double().norm().item()
            try:
                delta,stats = protection.candidate(keys,values,fixed,budget,protect=True)
            except ValueError as error:
                attempts.append(dict(target=target,scale=scale,reason=str(error)))
                break
            accepted_candidate = False
            try:
                with torch.no_grad():
                    owned.index_copy_(0,ids,pristine+delta.to(pristine))
                model.clear_quant()
                measured = trial.evaluate(model,tok,special,controls)
                scored = existing_answers(measured)
                dropped = sorted(kept-scored)
                target_correct = (target,"correction") in scored
                trials = dict(target=target,scale=scale,edited_ids=ids.tolist(),protected_lost=dropped,
                              target_correct=target_correct,stats=stats,
                              actual_change=float((owned.detach()[ids]-pristine).float().norm()),
                              decision_answer=measured["rows"][target]["correction"]["answer"])
                attempts.append(trials)
                if not dropped and target_correct:
                    anchor = next(((r,v) for r,v in anchors if any(i in val[r]["prompts"][v] for i in ids.tolist())),None)
                    if anchor is not None:
                        r,v = anchor
                        original_key = next((index for index,item in enumerate(anchors) if item==anchor))
                        start = sum(val[k]["records"][w].targets for k,w in anchors[:original_key])
                        new_keys = projected(model,val[r]["records"][v])[0].cpu()
                        trials["shared_input_key_l2"] = float((new_keys-fixed[start:start+len(new_keys)]).norm())
                        trials["shared_input_anchor"] = [r,v]
                    trials["row_delta"] = (owned.detach()[ids]-pristine).cpu().tolist()
                    accepted, after = trials, measured
                    accepted_candidate = True
            finally:
                if not accepted_candidate:
                    with torch.no_grad():
                        owned.index_copy_(0,ids,pristine)
                    if not torch.equal(owned[ids],pristine):
                        raise RuntimeError("rejected weight edit did not restore its rows")
                    model.clear_quant()
            if accepted is not None:
                break
        if accepted is not None:
            break
    if moments != trial.state_sha(optimizer.state_dict()):
        raise RuntimeError("a direct edit changed the optimizer state")
    return dict(applied=accepted is not None,accepted=accepted,attempts=attempts,optimizer_sha256=moments,
                anchors=anchors,before=before,after=after)


def train_epoch(model,optimizer,records,special,step,steps):
    model.train()
    model.clear_quant()
    mass = 0
    total = torch.zeros((),device="cuda")
    for index in range(0,len(records),trial.BATCH):
        items = records[index:index+trial.BATCH]
        x,y,_ = pad_records(items,special["<pad>"],"cuda",fixed_width=trial.WIDTH,batch_size=trial.BATCH)
        keep = y.ne(IGNORE)
        target = y[keep]
        step += 1
        optimizer.param_groups[0]["lr"] = reference.LR*min(1.,step/29)*(1-.7*(step/steps)**2)
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cuda",dtype=torch.bfloat16):
            h = model(x,return_hidden=True)
            loss = F.cross_entropy(model._head_logits(h[keep]).float(),target,reduction="sum")
        (loss/target.numel()).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        optimizer.step()
        mass += target.numel()
        total += loss.detach()
    return step, dict(step=step,targets=mass,ce=total.item()/mass)


def finalize(model,tok,special,cases,plan,branch):
    model.eval()
    model.clear_quant()
    state = model.state_dict()
    digest = trial.state_sha(state)
    previous = trial.read_json(CONTROL)
    reused = previous["state_sha256"]==digest
    results = ({name:previous[name] for name in ("validation","test")} if reused else
               {name:trial.evaluate(model,tok,special,cases[name]) for name in ("validation","test")})
    audit_only = {root:results["validation"]["rows"][root] for root in plan["audit"]}
    trial.publish(OUT/f"{branch}.json",dict(state_sha256=digest,reused_archived_responses=reused,
                  independent_audit_correct=len(existing_answers(dict(rows=audit_only))),**results))
    return digest


def worker(plan,fraction):
    if prepare()!=plan:
        raise ValueError("the frozen periodic edit benchmark changed")
    tok,special,cases,orders,profiles = trial.load_cases()
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if state["tag"]!=foundation.TAG or state["parent"] is not None or trial.state_sha(state["model"])!=plan["base"]["state_sha256"]:
        raise ValueError("shared starting weights changed")
    config = TMTConfig(**state["config"])
    if config.quant_anneal!=1.0 or config.train_repeat!=2.0 or not config.emb_rank:
        raise ValueError("fixed R2, final quantization and the factorized shared embedding are required")
    model = TiedMLPTransformer(config).to("cuda")
    model.load_state_dict(state["model"])
    torch.manual_seed(reference.data.SEED)
    optimizer = torch.optim.AdamW(model.parameters(),lr=reference.LR,weight_decay=.01,fused=True)
    steps = profiles["CORRECTION_ONLY"]["updates"]
    blocks = orders["CORRECTION_ONLY"]*trial.CYCLES
    rows = [[cases["train"][p["case_id"]]["records"][p["view"]] for p in epoch] for epoch in blocks]
    step, events, history = 0,[],[]
    control_ce = trial.read_json(CONTROL)["epochs"]
    print(f"START {TAG}",flush=True)
    for i in range(SITES[-1]):
        epoch = i+1
        step,trial_info = train_epoch(model,optimizer,rows[i],special,step,steps)
        history.append(dict(epoch=epoch,**trial_info))
        print(json.dumps(history[-1]),flush=True)
        if not any(event["applied"] for event in events) and trial_info["ce"] != control_ce[i]["ce"]:
            raise RuntimeError("the unedited prefix diverged from the recorded comparison")
        if epoch in SITES:
            if epoch == SITES[-1]:
                scratch = {name:t.detach().cpu().clone() for name,t in model.state_dict().items()}
                moment_snapshot = deepcopy(optimizer.state_dict())
            record = attempt_edit(model,optimizer,tok,special,cases["validation"],plan)
            record.update(epoch=epoch,step=step)
            trial.publish(OUT/f"edit_{epoch}.json",record)
            events.append(dict(epoch=epoch,step=step,applied=record["applied"]))
            print(json.dumps(events[-1]),flush=True)
    branch_step = step
    results = {}
    for branch in (("periodic","first_only") if events[-1]["applied"] else ("shared",)):
        if branch=="first_only":
            model.load_state_dict(scratch)
            optimizer.load_state_dict(moment_snapshot)
        step = branch_step
        for i in range(SITES[-1],len(rows)):
            step,trial_info = train_epoch(model,optimizer,rows[i],special,step,steps)
            history.append(dict(epoch=i+1,branch=branch,**trial_info))
        if step != steps:
            raise RuntimeError("a final branch missed optimizer updates")
        results[branch] = finalize(model,tok,special,cases,plan,branch)
    trial.publish(OUT/"report.json",dict(tag=TAG, events=events, history=history, branches=results,
                  preflight=plan, peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
    print(json.dumps(dict(events=events,branches=results)),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("run requires the matching receipt and stop time")
    return owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=300)


if __name__=="__main__":
    sys.exit(main())
