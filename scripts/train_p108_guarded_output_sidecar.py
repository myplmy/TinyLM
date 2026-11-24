"""Train the existing sparse output sidecar with protected logits and a frozen body."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from unittest.mock import patch

import torch
import torch.nn.functional as F

from scripts import run_p108_counterfactual_write_replay as source


TAG = "p108_guarded_output_sidecar_gpu_v1_20261121"
OUT = source.OUT.with_name(TAG)
replay,trial,composition = source.replay,source.trial,source.composition
solver,prior = replay.solver,replay.prior
INITIAL = composition.OUT/"joined_overlay.pt"
NEW_FORMS = {
    "ko": (
        "답을 고치기 전에 표를 보세요. {field}의 값만 숫자로 적으세요.",
        "앞 답이 아니라 작업표를 근거로 {field} 번호를 다시 알려 주세요.",
        "저장된 작업 기록에서 {field} 항목에 적힌 번호가 무엇인가요?",
        "지금 표의 {field} 줄을 확인했습니다. 그 줄의 번호만 답해 주세요.",
    ),
    "en": (
        "Consult the table before revising your response. Give the value for {field}.",
        "Use the work log instead of the prior reply and report the number for {field}.",
        "What number is stored on the {field} line in the record?",
        "Check the current record and return the number on the {field} line only.",
    ),
}


def prepare():
    current,(tok,special,cases,_,dev,schedule,old_wording) = source.prepare()
    path = source.OUT/"report.json"
    prior_replay = trial.read_json(path)
    terminal = trial.read_json(source.OUT/"supervisor.json")
    combined = trial.read_json(composition.OUT/"report.json")
    if (prior_replay["plan"]!=current or terminal["returncode"] or terminal["stop_reason"]
            or not INITIAL.is_file() or combined["saved_sha256"]!=trial.file_sha(INITIAL)):
        raise ValueError("requires the completed experiments and protected starting sidecar")
    roots = sorted(set(current["targets"].values()))
    with patch.object(composition,"PARAPHRASES",NEW_FORMS):
        new = composition.novel_requests(tok,dev,roots)
    if {tuple(row["ids"]) for row in old_wording}&{tuple(row["ids"]) for row in new}:
        raise ValueError("the new expression cohort overlaps the earlier requests")
    selected = {row["replay"]:schedule[row["epoch"]-1][row["index"]] for row in current["slots"]}
    plan = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),replay_report=trial.file_sha(path),
                start_overlay_sha256=combined["saved_sha256"],new_expressions_sha256=replay.author.digest(new),
                rows=len(selected),targets=roots,base=current["control"]["base"],
                body_state_sha256=combined["plan"]["overlay"]["reference"]["state_sha256"],
                updates=48)
    return plan,(tok,special,cases,dev,new,selected)


def apply_scores(keys,scores,tokens,delta):
    changed = scores.clone()
    changed[:,tokens] += keys@delta.T
    return changed


def train_sidecar(model,initial,training,guard,guard_baseline,updates):
    selected = torch.tensor(initial["ids"],device="cuda")
    starting = initial["delta"].to(device="cuda",dtype=torch.float32)
    delta = torch.nn.Parameter(starting.clone())
    projected = [prior.projected(model,encoded) for encoded in training]
    # Concatenation creates ordinary tensors for the sidecar's backward pass.
    train_keys,scores,labels = [torch.cat(values).clone() for values in zip(*projected,strict=True)]
    protected,_ = solver.observed_guards(model,guard,guard_baseline)
    guard_keys,guard_scores,winners = [tensor.to("cuda") for tensor in protected]
    guard_keys,guard_scores = guard_keys.float(),guard_scores.float()
    _,gap = solver.span_constraints(guard_scores,winners,selected,guard_scores.new_zeros((len(winners),len(selected))))
    mask = torch.isfinite(gap)
    required = torch.minimum(gap.clamp_min(0)*.25,torch.full_like(gap,.025))
    is_own_row = winners[:,None]==selected
    optimizer = torch.optim.AdamW([delta],lr=.004,weight_decay=0.)
    for _ in range(updates):
        shifts = guard_keys@delta.T
        owner = (shifts*is_own_row).sum(-1,keepdim=True)
        others = torch.cat((shifts,torch.zeros_like(owner)),dim=1)
        guard_loss = F.relu(required[mask]-(gap+owner-others)[mask]).square().mean()
        course_loss = F.cross_entropy(apply_scores(train_keys,scores,selected,delta),labels)
        loss = course_loss+40.*guard_loss
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    return starting.cpu(),delta.detach().cpu(),len(winners)


def worker(plan,fraction):
    torch.set_num_threads(1)
    checked,(tok,special,cases,dev,new,selected) = prepare()
    if checked!=plan:
        raise ValueError("the sidecar inputs changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    data = torch.load(solver.first.CHECKPOINT,weights_only=True,map_location="cpu")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**data["config"])).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(data["model"])
    # This is the completed correction checkpoint, which is bound directly in the sidecar.
    initial = torch.load(INITIAL,weights_only=True,map_location="cpu")
    if trial.state_sha(model.state_dict())!=initial["body_sha256"] or initial["body_sha256"]!=plan["body_state_sha256"]:
        raise ValueError("the stored sidecar belongs to another checkpoint")
    snapshot = trial.read_json(prior.CONTROL)
    guard = {root:cases["validation"][root] for root in plan["base"]["guard"]}
    guard_before = dict(rows={root:snapshot["validation"]["rows"][root] for root in guard})
    checked_answers = prior.existing_answers(guard_before)
    start,trained,positions = train_sidecar(model,initial,list(selected.values()),guard,guard_before,plan["updates"])
    fit = {root:dev[root] for root in plan["targets"]}
    option = None
    attempts = []
    for fraction in (1.,.5,.25):
        candidate = (start+(trained-start)*fraction).half().float()
        with solver.overlay(model,initial["ids"],candidate):
            target = trial.evaluate(model,tok,special,fit)
            guards = trial.evaluate(model,tok,special,guard)
        exact = all(prior.correct(row,"correction") for row in target["rows"].values())
        kept = solver.identical_sequences(guard_before,guards,checked_answers)
        attempts.append(dict(fraction=fraction,targets=target["totals"],guard=kept))
        if exact and kept:
            option = candidate
            break
    if option is None:
        transfer = None
    else:
        with solver.overlay(model,initial["ids"],start):
            before = composition.run_wording(model,tok,special,new)
        with solver.overlay(model,initial["ids"],option):
            after = composition.run_wording(model,tok,special,new)
            test = trial.evaluate(model,tok,special,cases["test"])
        protected = solver.identical_sequences(snapshot["test"],test,prior.existing_answers(snapshot["test"]))
        transfer = dict(before=before,after=after,protected=protected,test=test)
        if (protected and sum(row["exact"] for row in after)>sum(row["exact"] for row in before)
                and all(not a["exact"] or b["exact"] for a,b in zip(before,after,strict=True))):
            artifact = OUT/"trained_overlay.pt"
            with artifact.open("xb") as file:
                torch.save(dict(ids=initial["ids"],delta=option.half(),body_sha256=initial["body_sha256"]),file)
            transfer["saved_sha256"] = trial.file_sha(artifact)
    if trial.state_sha(model.state_dict())!=initial["body_sha256"]:
        raise ValueError("the sidecar optimization changed the base")
    trial.publish(OUT/"report.json",dict(plan=plan,attempts=attempts,new_expressions=transfer,
                  requests=new,guard_positions=positions))
    print(json.dumps(dict(attempts=attempts,transfer=dict(before=sum(r["exact"] for r in transfer["before"]),
                                                         after=sum(r["exact"] for r in transfer["after"]),
                                                         protected=transfer["protected"],test=transfer["test"]["totals"])
                                                       if transfer else None)),flush=True)


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
        parser.error("requires a sealed sidecar experiment and authorized cutoff")
    return prior.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=solver.AUTHORIZATION_END,min_seconds=180)


if __name__=="__main__":
    sys.exit(main())
