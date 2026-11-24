"""Apply protected margin-selected shared writes after real optimizer updates."""

import argparse
from copy import deepcopy
from datetime import datetime
from itertools import zip_longest
import json
from pathlib import Path
import sys

import torch

from scripts import probe_p108_overlay_composition as composition


TAG = "p108_periodic_margin_writes_gpu_v1_20261121"
OUT = composition.OUT.with_name(TAG)
solver = composition.added
prior,trial = composition.prior,composition.trial
FRAC_CAP, ATTEMPT_LIMIT = .30, 6


def prepare():
    contract,(data,_,_,_) = composition.prepare()
    source = composition.OUT/"report.json"
    studied = trial.read_json(source)
    terminated = trial.read_json(composition.OUT/"supervisor.json")
    if (studied["plan"]!=contract or terminated["returncode"] or terminated["stop_reason"]
            or not all(row["shared_correct"] and row["shared_protected"] for row in studied["comparisons"].values())
            or not studied["joined"]["same_prior_correct"]):
        raise ValueError("requires the tested shared writes and protected sidecar composition")
    control = trial.read_json(prior.CONTROL)
    if control["epochs"][-1]["steps"]!=464:
        raise ValueError("the archived correction schedule must have 464 updates")
    return dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),comparison_sha256=trial.file_sha(source),
                control_sha256=trial.file_sha(prior.CONTROL),base=contract["overlay"]["reference"]["setup"],
                sites=list(prior.SITES),row_norm_cap=FRAC_CAP,attempt_limit=ATTEMPT_LIMIT),data


def proposals(model,dev,roots,before,protected,end):
    offered = []
    for root in roots:
        keys,scores,labels = prior.projected(model,dev[root]["records"]["correction"])
        response = before["rows"][root]["correction"]
        actual = response["ids"]+([end] if response["eot"] else [])
        diff = next((i for i,(a,b) in enumerate(zip_longest(labels.tolist(),actual)) if a!=b),None)
        if diff is None or diff>=min(len(labels),len(actual)) or int(scores[diff].argmax())!=actual[diff]:
            continue
        wanted,rival = int(labels[diff]),actual[diff]
        norm = float(model.emb.weight[rival if wanted==end else wanted].detach().norm())
        model_rows = solver.candidates(keys[diff].double().cpu(),scores[diff].double().cpu(),wanted,rival,end,
                                       protected,norm,.10)
        for record,delta in model_rows:
            if delta is not None and record["norm_ratio"]<=FRAC_CAP:
                offered.append((root,record,delta))
    return offered


def edit_at_boundary(model,opt,tok,special,dev,guard,seen,archived=None):
    model.eval()
    model.clear_quant()
    panel = dict(dev,**guard)
    baseline = archived if archived is not None else trial.evaluate(model,tok,special,panel)
    kept = prior.existing_answers(baseline)
    wrong = sorted(root for root in dev if not prior.correct(baseline["rows"][root],"correction"))
    guard_scores,missed = solver.observed_guards(model,guard,baseline)
    candidates = sorted(proposals(model,dev,wrong,baseline,guard_scores,special["<|im_end|>"]),
                        key=lambda row:(row[0] in seen,row[1]["norm_ratio"],row[0]))
    attempts = []
    accepted = None
    before_moments = trial.state_sha(opt.state_dict())
    for root,candidate,delta in candidates[:ATTEMPT_LIMIT]:
        ids = candidate["tokens"]
        stored = model.emb.weight[ids].detach().clone()
        retain = False
        try:
            with torch.no_grad():
                model.emb.weight[ids] = stored+delta.to(stored)
            model.clear_quant()
            focused = trial.evaluate(model,tok,special,{root:dev[root]})["rows"][root]
            result = dict(root=root,expected=dev[root]["gold"],before=baseline["rows"][root]["correction"],
                          after=focused["correction"],candidate=candidate)
            if prior.correct(focused,"correction"):
                after = trial.evaluate(model,tok,special,panel)
                retain = solver.identical_sequences(baseline,after,kept)
                result.update(protected=retain)
            attempts.append(result)
            if retain:
                accepted = result
                break
        finally:
            if not retain:
                with torch.no_grad():
                    model.emb.weight[ids] = stored
                model.clear_quant()
    if trial.state_sha(opt.state_dict())!=before_moments:
        raise ValueError("the manual write changed optimizer moments")
    return dict(accepted=accepted,wrong=len(wrong),previous_retention={root:prior.correct(baseline["rows"][root],"correction")
                for root in seen},attempts=attempts,feasible=len(candidates),protected_answers=len(kept),
                protected_positions=len(guard_scores[0]),guard_score_mismatches=missed,optimizer_sha256=before_moments)


def finalize(name,model,tok,special,cases,dev,events,reference):
    model.eval()
    model.clear_quant()
    fingerprint = trial.state_sha(model.state_dict())
    test = reference["test"] if fingerprint==reference["state_sha256"] else trial.evaluate(model,tok,special,cases["test"])
    fit = {event["accepted"]["root"]:dev[event["accepted"]["root"]] for event in events if event["accepted"]}
    final_answers = trial.evaluate(model,tok,special,fit)
    protect = solver.identical_sequences(reference["test"],test,prior.existing_answers(reference["test"]))
    artifact = None
    if fit and protect and any(prior.correct(row,"correction") for row in final_answers["rows"].values()):
        artifact = OUT/f"{name}.pt"
        with artifact.open("xb") as file:
            torch.save(dict(model={key:value.detach().cpu() for key,value in model.state_dict().items()},
                            config=vars(model.cfg),tag=TAG,branch=name),file)
    return dict(state_sha256=fingerprint,reused_test=fingerprint==reference["state_sha256"],
                retained={root:prior.correct(row,"correction") for root,row in final_answers["rows"].items()},
                fit=final_answers,test=test,archived_test=reference["test"]["totals"],protected_test=protect,
                exported_sha256=trial.file_sha(artifact) if artifact else None)


def worker(plan,fraction):
    torch.set_num_threads(1)
    checked,(tok,special,cases,orders,profiles,dev) = prepare()
    if checked!=plan:
        raise ValueError("the periodic edit inputs changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(prior.foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(state["model"])!=plan["base"]["base"]["state_sha256"]:
        raise ValueError("the starting weights differ")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**state["config"])).to("cuda")
    model.load_state_dict(state["model"])
    torch.manual_seed(prior.reference.data.SEED)
    opt = torch.optim.AdamW(model.parameters(),lr=prior.reference.LR,weight_decay=.01,fused=True)
    guard = {root:cases["validation"][root] for root in plan["base"]["guard"]}
    steps = profiles["CORRECTION_ONLY"]["updates"]
    ordered = [[cases["train"][item["case_id"]]["records"][item["view"]] for item in epoch]
               for epoch in orders["CORRECTION_ONLY"]*trial.CYCLES]
    control = trial.read_json(prior.CONTROL)
    step,seen,events,history = 0,set(),[],[]
    for i,batch in enumerate(ordered[:prior.SITES[-1]],1):
        step,metrics = prior.train_epoch(model,opt,batch,special,step,steps)
        history.append(dict(epoch=i,**metrics))
        if not seen and control["epochs"][i-1]["ce"]!=metrics["ce"]:
            raise ValueError("the unedited correction prefix no longer matches")
        if i not in prior.SITES:
            continue
        if i==prior.SITES[-1]:
            scratch = {key:t.detach().cpu().clone() for key,t in model.state_dict().items()}
            moments = deepcopy(opt.state_dict())
            rng = (torch.get_rng_state(),torch.cuda.get_rng_state())
        saved = None if seen else trial.read_json(added_boundary(i))["before"]
        event = edit_at_boundary(model,opt,tok,special,dev,guard,seen,archived=saved)
        event.update(epoch=i,step=step)
        events.append(event)
        if event["accepted"]:
            seen.add(event["accepted"]["root"])
        trial.publish(OUT/f"boundary_{step}.json",event)
        print(json.dumps(dict(step=step,edit=bool(event["accepted"]),attempts=len(event["attempts"]))),flush=True)
    boundary_step = step
    branches = {}
    for branch in (("periodic","first_only") if all(event["accepted"] for event in events) else ("periodic",)):
        step = boundary_step
        if branch=="first_only":
            model.load_state_dict(scratch)
            opt.load_state_dict(moments)
            torch.set_rng_state(rng[0])
            torch.cuda.set_rng_state(rng[1])
        for i,batch in enumerate(ordered[prior.SITES[-1]:],prior.SITES[-1]+1):
            step,metrics = prior.train_epoch(model,opt,batch,special,step,steps)
            history.append(dict(epoch=i,branch=branch,**metrics))
        if step!=steps:
            raise ValueError("the periodic branch did not finish the correction schedule")
        branches[branch] = finalize(branch,model,tok,special,cases,dev,
                                    events if branch=="periodic" else events[:-1],control)
    trial.publish(OUT/"report.json",dict(plan=plan,events=events,branches=branches,history=history,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
    print(json.dumps({key:dict(retained=value["retained"],test=value["test"]["totals"],
                              protected=value["protected_test"]) for key,value in branches.items()}),flush=True)


def added_boundary(epoch):
    return composition.added.first.followup.OUT/f"edit_{epoch}.json"


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
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the protected write receipt and authorized cutoff")
    return prior.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=solver.AUTHORIZATION_END,min_seconds=360)


if __name__ == "__main__":
    sys.exit(main())
