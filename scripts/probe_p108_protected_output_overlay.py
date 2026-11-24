"""Check a sparse output-only edit under actual greedy-response protection."""

import argparse
from datetime import datetime
from itertools import zip_longest
import json
from pathlib import Path
import sys
from unittest.mock import patch

import torch
import torch.nn.functional as F

from scripts import probe_p108_tied_head_first_margin as first


TAG = "p108_protected_output_overlay_gpu_v1_20261121"
OUT = first.OUT.with_name(TAG)
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")
prior,trial = first.prior,first.trial
NORM_MULTIPLIERS = (.30,1.25)


def prepare():
    reference,data = first.prepare()
    last_path = first.OUT/"report.json"
    last = trial.read_json(last_path)
    terminal = trial.read_json(first.OUT/"supervisor.json")
    if last["plan"]!=reference or not last["weights_restored"] or terminal["returncode"] or terminal["stop_reason"]:
        raise ValueError("requires the completed first-divergence evidence")
    chosen = {}
    for row in last["comparisons"]:
        if row.get("method") and row.get("before"):
            chosen.setdefault(row["root"],row["before"])
    if set(chosen)!=set(reference["targets"]):
        raise ValueError("the three development failures must have original responses")
    plan = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),first_margin_sha256=trial.file_sha(last_path),
                reference=reference,norm_multipliers=list(NORM_MULTIPLIERS),target_margin=.10,
                solver_contract=check_solver())
    return plan,data,chosen


def span_constraints(scores,labels,tokens,coefficients):
    winner = scores.gather(-1,labels[:,None])
    changed = scores.index_select(-1,tokens)
    for_unchanged = scores.clone()
    for_unchanged[:,tokens] = -torch.inf
    for_unchanged.scatter_(-1,labels[:,None],-torch.inf)
    competitor = torch.cat((changed,for_unchanged.max(-1,keepdim=True).values),dim=-1)
    winner_coefficient = (coefficients*(labels[:,None]==tokens)).sum(-1,keepdim=True)
    competitor_coefficient = torch.cat((coefficients,torch.zeros_like(winner_coefficient)),dim=-1)
    gap = winner-competitor
    gap[:,:len(tokens)].masked_fill_(labels[:,None]==tokens,torch.inf)
    return competitor_coefficient-winner_coefficient,gap


def interval(slope,rhs):
    rising = slope>1e-12
    falling = slope< -1e-12
    if ((~(rising|falling)) & (rhs<0)).any():
        return None
    low = max(0.,float((rhs[falling]/slope[falling]).max())) if falling.any() else 0.
    high = float((rhs[rising]/slope[rising]).min()) if rising.any() else None
    return (low,high) if high is None or low<=high else None


def check_solver():
    scores = torch.tensor([[1.,1.0078125,.5]],dtype=torch.float64)
    change = torch.tensor([[1.]],dtype=torch.float64)
    slope,gap = span_constraints(scores,torch.tensor([1]),torch.tensor([0]),change)
    limit = interval(slope,gap)
    shifted = scores+scores.new_tensor([[.005,0.,0.]])
    fp32,bf16 = int(shifted.float().argmax()),int(shifted.bfloat16().argmax())
    slope,gap = span_constraints(scores,torch.tensor([0]),torch.tensor([0]),change)
    required = interval(slope,gap-.1)
    if limit!=(0.,.0078125) or required!=(.1078125,None) or (fp32,bf16)!=(1,0):
        raise ValueError("the interval or argmax rounding contract failed")
    return dict(protection_upper=limit[1],target_lower=required[0],fp32_winner=fp32,bf16_winner=bf16)


def observed_guards(model,guard,baseline):
    observed = []
    unavailable = 0
    for root in sorted(guard):
        for view in prior.VIEWS:
            if not prior.correct(baseline["rows"][root],view):
                continue
            keys,scores,labels = prior.projected(model,guard[root]["records"][view])
            consistent = scores.argmax(-1)==labels
            unavailable += int((~consistent).sum().item())
            if consistent.any():
                observed.append((keys[consistent].double().cpu(),scores[consistent].double().cpu(),labels[consistent].cpu()))
    if not observed:
        raise ValueError("no protected greedy score positions")
    return tuple(torch.cat(rows) for rows in zip(*observed,strict=True)),unavailable


def directions(key,guards):
    covariance = guards.T @ guards / len(guards)
    regularization = max(float(covariance.diag().mean())*.10,1e-10)
    adjusted = torch.linalg.solve(covariance+torch.eye(len(key),dtype=key.dtype)*regularization,key)
    return {"target":F.normalize(key,dim=0),"guard_whitened":F.normalize(adjusted,dim=0)}


def candidates(key,scores,wanted,rival,end,guard,budget,margin):
    keys,protected,labels = guard
    if wanted==end:
        patterns = {"lower_extra":([rival],[-1.])}
    else:
        patterns = {"raise_wanted":([wanted],[1.])}
        if rival!=end:
            patterns["raise_and_lower"] = ([wanted,rival],[1.,-1.])
    proposals = []
    for geometry,direction in directions(key,keys).items():
        for name,(tokens,signs) in patterns.items():
            ids = torch.tensor(tokens)
            template = torch.tensor(signs,dtype=direction.dtype)[:,None]*direction
            a,b = span_constraints(scores[None,:],torch.tensor([wanted]),ids,(key@template.T)[None,:])
            required = interval(a,b-margin)
            a,b = span_constraints(protected,labels,ids,keys@template.T)
            reserve = torch.minimum(.025*torch.ones_like(b),b.clamp_min(0)*.25)
            allowed = interval(a,b-reserve)
            data = dict(pattern=name,geometry=geometry,tokens=tokens,required=required,protected=allowed)
            if required is not None and allowed is not None:
                lower = max(required[0],allowed[0])
                ceilings = [value for value in (required[1],allowed[1],budget*NORM_MULTIPLIERS[-1]/float(template.norm()))
                            if value is not None]
                upper = min(ceilings)
                if lower<=upper:
                    delta = (template*(lower+min(.01,(upper-lower)/2))).half().float()
                    actual = float(delta.norm())
                    a,b = span_constraints(protected,labels,ids,keys@delta.double().T)
                    if ((a<=b).all() and actual<=budget*NORM_MULTIPLIERS[-1]):
                        updated = scores.clone()
                        updated[ids] += (key@delta.double().T)
                        if int(updated.argmax())==wanted:
                            data.update(norm=actual,norm_ratio=actual/budget,
                                        predicted_margin=first.margin(updated,wanted),half_bytes=delta.numel()*2)
                            proposals.append((data,delta))
                            continue
            proposals.append((data,None))
    return proposals


def overlay(model,ids,delta):
    original = model._head_logits
    index = torch.tensor(ids,device="cuda")
    matrix = delta.to(device="cuda",dtype=torch.float32)

    def head(hidden):
        scores = original(hidden).float()
        keys = F.linear(hidden,model._emb_up_w().t()).float()
        with torch.autocast("cuda",enabled=False):
            scores[...,index] += keys@matrix.T
        return scores

    return patch.object(model,"_head_logits",head)


def identical_sequences(reference,now,kept):
    return all(reference["rows"][root][view]["ids"]==now["rows"][root][view]["ids"]
               and reference["rows"][root][view]["eot"]==now["rows"][root][view]["eot"] for root,view in kept)


def worker(plan,fraction):
    torch.set_num_threads(1)
    checked,(tok,special,cases,_,_,dev),old_answers = prepare()
    if checked!=plan:
        raise ValueError("the protected edit setup changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(first.CHECKPOINT,weights_only=True,map_location="cpu")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**state["config"])).to("cuda").eval()
    model.load_state_dict(state["model"])
    state_sha = plan["reference"]["state_sha256"]
    if trial.state_sha(model.state_dict())!=state_sha:
        raise ValueError("wrong unchanged checkpoint")
    control = trial.read_json(prior.CONTROL)
    setup = plan["reference"]["setup"]
    guard = {root:cases["validation"][root] for root in setup["guard"]}
    guard_baseline = dict(rows={root:control["validation"]["rows"][root] for root in guard})
    kept = prior.existing_answers(guard_baseline)
    protect,unavailable = observed_guards(model,guard,guard_baseline)
    end = special["<|im_end|>"]
    attempts = []
    admissible = []
    dev_baseline = None
    dev_kept = None
    for root in sorted(old_answers):
        before = old_answers[root]
        keys,logits,labels = prior.projected(model,dev[root]["records"]["correction"])
        recorded = before["ids"]+([end] if before["eot"] else [])
        mismatch = next((i for i,(a,b) in enumerate(zip_longest(labels.tolist(),recorded)) if a!=b),None)
        if mismatch is None or mismatch>=min(len(labels),len(recorded)) or int(logits[mismatch].argmax())!=recorded[mismatch]:
            raise ValueError("the archived development error does not align with the current head")
        wanted,rival = int(labels[mismatch]),recorded[mismatch]
        row_budget = float(model.emb.weight[rival if wanted==end else wanted].detach().norm())
        feature,scores = keys[mismatch].double().cpu(),logits[mismatch].double().cpu()
        choices = candidates(feature,scores,wanted,rival,end,protect,row_budget,plan["target_margin"])
        info = dict(root=root,wanted=wanted,rival=rival,before=before,before_margin=first.margin(scores,wanted),
                    gold=dev[root]["gold"],proposals=[row for row,_ in choices],runs=[])
        possible = sorted(((row,delta) for row,delta in choices if delta is not None),key=lambda item:item[0]["norm"])
        for row,delta in possible[:2]:
            protected = False
            with overlay(model,row["tokens"],delta):
                out = trial.evaluate(model,tok,special,{root:dev[root]})["rows"][root]
                repaired = prior.correct(out,"correction")
                measured = dict(candidate=row,after=out["correction"],repaired=repaired)
                if repaired:
                    after = trial.evaluate(model,tok,special,guard)
                    protected = identical_sequences(guard_baseline,after,kept)
                    measured["protected_sequences_unchanged"] = protected
            if repaired and protected:
                if dev_baseline is None:
                    dev_baseline = trial.evaluate(model,tok,special,dev)
                    dev_kept = prior.existing_answers(dev_baseline)
                with overlay(model,row["tokens"],delta):
                    after = trial.evaluate(model,tok,special,dev)
                measured["development_sequences_unchanged"] = identical_sequences(dev_baseline,after,dev_kept)
                if measured["development_sequences_unchanged"]:
                    admissible.append((row,delta,root))
            info["runs"].append(measured)
        attempts.append(info)
    final = None
    if admissible:
        chosen,delta,root = min(admissible,key=lambda entry:entry[0]["norm_ratio"])
        validation = {key:cases["validation"][key] for key in setup["audit"]}
        before_audit = dict(rows={key:control["validation"]["rows"][key] for key in validation})
        with overlay(model,chosen["tokens"],delta):
            got = trial.evaluate(model,tok,special,validation)
            final = dict(target=root,overlay=chosen,protected_audit=identical_sequences(before_audit,got,prior.existing_answers(before_audit)),
                         audit=got)
            if final["protected_audit"]:
                test = trial.evaluate(model,tok,special,cases["test"])
                final.update(test=test,reference_test=control["test"]["totals"],
                             same_prior_correct=identical_sequences(control["test"],test,prior.existing_answers(control["test"])))
        if final.get("same_prior_correct"):
            with (OUT/"output_overlay.pt").open("xb") as stream:
                torch.save(dict(ids=chosen["tokens"],delta=delta.half(),body_sha256=state_sha),stream)
    if trial.state_sha(model.state_dict())!=state_sha:
        raise ValueError("the overlay modified the original tensor state")
    trial.publish(OUT/"report.json",dict(plan=plan,protected_answers=len(kept),protected_positions=len(protect[0]),
                  projected_path_mismatches=unavailable,attempts=attempts,admissible=len(admissible),final=final))
    print(json.dumps(dict(guard=len(kept),candidates=[len(row["runs"]) for row in attempts],
                          repaired=[sum(x["repaired"] for x in row["runs"]) for row in attempts],
                          admissible=len(admissible),independent=final is not None)),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the sealed protected edit and authorized cutoff")
    return prior.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=AUTHORIZATION_END,min_seconds=180)


if __name__ == "__main__":
    sys.exit(main())
