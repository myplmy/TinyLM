"""Measure retention with matched replay and protected shared writes."""

import argparse
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from unittest.mock import patch

import torch

from scripts import run_p108_periodic_margin_writes as periodic


TAG = "p108_margin_write_replay_gpu_v1_20261121"
OUT = periodic.OUT.with_name(TAG)
prior,trial,solver = periodic.prior,periodic.trial,periodic.solver
author = periodic.composition.AUTHOR
TRAIN_FORMS = {
    "ko": (
        "기록을 대조한 뒤 {field}에 등록된 숫자를 적어 주세요.",
        "앞선 응답을 수정합니다. 장부의 {field} 번호가 필요합니다.",
        "현재 작업표가 가리키는 {field} 값을 번호로 써 주세요.",
        "작업 기록에서 {field} 줄을 확인하고 번호를 제시해 주세요.",
    ),
    "en": (
        "Review the register and state the number listed for {field}.",
        "Revise the previous reply with the current {field} entry from the log.",
        "Look up the {field} cell and report its number.",
        "The log is the source for this correction. Give the number beside {field}.",
    ),
}


def authored_replay(tok,root,row):
    composition = periodic.composition
    question = tok.decode(row["prompts"]["single"],skip_special_tokens=False)
    correction = tok.decode(row["prompts"]["correction"],skip_special_tokens=False)
    if not question.startswith(composition.TURN) or not question.endswith(composition.ENDING):
        raise ValueError("expected a sealed ChatML request")
    language = row["language"]
    field = [name for i,name in enumerate(author.FIELDS[language])
             if author.field_question(language,i,1) in correction]
    if len(field)!=1:
        raise ValueError("the replay target field must be unique")
    first = question.removeprefix(composition.TURN).removesuffix(composition.ENDING)
    data = prior.foundation.data
    records = []
    for form in TRAIN_FORMS[language]:
        followup = form.format(field=field[0])
        identifier = author.digest([TAG,root,followup])
        record = author.row(identifier,"correction_replay",language,[
            ("user",first),("assistant",row["foil"]),("user",followup),("assistant",row["gold"]),
        ],view="correction")["record"]
        encoded = data.encode_record(record,tok,context=trial.WIDTH)
        prefix = data.generation_prompt(tok,record)
        labels = [token for token in encoded.y if token!=data.IGNORE]
        if (row["gold"] in followup or encoded.x[:len(prefix)]!=prefix or tok.decode(labels[:-1])!=row["gold"]
                or encoded.targets!=row["records"]["correction"].targets):
            raise ValueError("the replay must preserve the answer supervision and leave it out of the question")
        records.append((identifier,encoded,prefix))
    return records


def build_schedule(cases,orders,replay,targets):
    orig = orders["CORRECTION_ONLY"]*trial.CYCLES
    modified = []
    changes = []
    for epoch,ordered in enumerate(orig,1):
        items = [cases["train"][r["case_id"]]["records"][r["view"]] for r in ordered]
        scheduled = [root for site,root in targets.items() if epoch in (site+1,site+2)]
        if scheduled:
            root, = scheduled
            additions = replay[root]
            language = additions[0][3]
            required = additions[0][1].targets
            slots = [i for i,r in enumerate(ordered) if items[i].targets==required
                     and cases["train"][r["case_id"]]["language"]==language]
            if len(slots)<len(additions):
                raise ValueError("requires matching language and exact supervised token counts")
            selected = [slots[((2*j+1)*len(slots))//(2*len(additions))] for j in range(len(additions))]
            for pos,(identifier,record,_,_) in zip(selected,additions,strict=True):
                changes.append(dict(epoch=epoch,index=pos,replaced=ordered[pos]["case_id"],
                                    replay=identifier,targets=record.targets,language=language))
                items[pos] = record
        modified.append(items)
    if len(changes)!=16:
        raise ValueError("the controlled replay requires two windows of eight replacements")
    return modified,changes


def prepare():
    known,(tok,special,cases,orders,profiles,dev) = periodic.prepare()
    baseline = periodic.OUT/"report.json"
    result = trial.read_json(baseline)
    terminal = trial.read_json(periodic.OUT/"supervisor.json")
    if (result["plan"]!=known or terminal["returncode"] or terminal["stop_reason"]
            or len(result["events"])!=2 or not all(e["accepted"] for e in result["events"])):
        raise ValueError("the two completed protected writes must be available")
    targets = {int(event["epoch"]):event["accepted"]["root"] for event in result["events"]}
    if len(set(targets.values()))!=2 or set(targets)!=set(prior.SITES):
        raise ValueError("replay requires two distinct dated development targets")
    target_roots = set(targets.values())
    excluded = {tuple(row["prompts"]["correction"]) for split in (*cases.values(),dev) for row in split.values()}
    transfer = trial.read_json(periodic.composition.OUT/"report.json")["wording"]
    excluded.update(tuple(row["ids"]) for row in transfer)
    replay = {}
    for root in sorted(target_roots):
        replay[root] = [(*row,dev[root]["language"]) for row in authored_replay(tok,root,dev[root])]
    new = [tuple(prefix) for rows in replay.values() for _,_,prefix,_ in rows]
    if len(set(new))!=8 or excluded.intersection(new):
        raise ValueError("the replay training prompts overlap a sealed cohort or each other")
    schedule,changes = build_schedule(cases,orders,replay,targets)
    digest = author.digest([(root,name,record.x,record.y) for root,rows in replay.items() for name,record,_,_ in rows])
    plan = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),control=known,
                boundary_report_sha256=trial.file_sha(baseline),replay_sha256=digest,targets={str(k):v for k,v in targets.items()},
                slots=changes,transfer_sha256=author.digest(transfer))
    return plan,(tok,special,cases,profiles,dev,schedule,transfer)


def protect_and_write(model,opt,tok,special,dev,guard,root):
    model.eval()
    model.clear_quant()
    panel = dict(dev,**guard)
    baseline = trial.evaluate(model,tok,special,panel)
    target = baseline["rows"][root]
    if prior.correct(target,"correction"):
        return dict(root=root,already_correct=True,accepted=False,before=target["correction"])
    kept = prior.existing_answers(baseline)
    observed,_ = solver.observed_guards(model,guard,baseline)
    proposed = periodic.proposals(model,dev,[root],baseline,observed,special["<|im_end|>"])
    choices = sorted(proposed,key=lambda item:item[1]["norm_ratio"])
    before_opt = trial.state_sha(opt.state_dict())
    attempts = []
    accepted = False
    for _,candidate,delta in choices[:periodic.ATTEMPT_LIMIT]:
        ids = candidate["tokens"]
        old = model.emb.weight[ids].detach().clone()
        try:
            with torch.no_grad():
                model.emb.weight[ids] = old+delta.to(old)
            model.clear_quant()
            checked = trial.evaluate(model,tok,special,{root:dev[root]})["rows"][root]
            result = dict(candidate=candidate,after=checked["correction"])
            if prior.correct(checked,"correction"):
                actual = trial.evaluate(model,tok,special,panel)
                accepted = solver.identical_sequences(baseline,actual,kept)
                result["preserved"] = accepted
            attempts.append(result)
            if accepted:
                break
        finally:
            if not accepted:
                with torch.no_grad():
                    model.emb.weight[ids] = old
                model.clear_quant()
    if trial.state_sha(opt.state_dict())!=before_opt:
        raise ValueError("a write changed AdamW moments")
    return dict(root=root,accepted=accepted,before=target["correction"],attempts=attempts,protected=len(kept))


def train_with_batch_receipt(model,optimizer,items,special,step,total,receipts):
    original = prior.pad_records

    def observed(*args,**kwargs):
        batch = original(*args,**kwargs)
        digest = sha256()
        for tensor in batch[:2]:
            digest.update(str(tuple(tensor.shape)).encode("ascii"))
            digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        receipts.append(digest.hexdigest())
        return batch

    with patch.object(prior,"pad_records",observed):
        return prior.train_epoch(model,optimizer,items,special,step,total)


def worker(plan,fraction):
    torch.set_num_threads(1)
    checked,(tok,special,cases,profiles,dev,schedule,transfer) = prepare()
    if checked!=plan:
        raise ValueError("the sealed replay schedule changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    saved = torch.load(prior.foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    expected = plan["control"]["base"]["base"]["state_sha256"]
    if trial.state_sha(saved["model"])!=expected:
        raise ValueError("wrong shared starting state")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**saved["config"])).to("cuda")
    model.load_state_dict(saved["model"])
    torch.manual_seed(prior.reference.data.SEED)
    optimizer = torch.optim.AdamW(model.parameters(),lr=prior.reference.LR,weight_decay=.01,fused=True)
    expected_steps = profiles["CORRECTION_ONLY"]["updates"]
    control = trial.read_json(prior.CONTROL)
    first = prior.SITES[0]
    step,history = 0,[]
    for epoch,items in enumerate(schedule[:first],1):
        step,metrics = prior.train_epoch(model,optimizer,items,special,step,expected_steps)
        if metrics["ce"]!=control["epochs"][epoch-1]["ce"]:
            raise ValueError("the common prefix changed before the replay split")
        history.append(dict(epoch=epoch,**metrics))
    first_step = step
    model_state = {key:t.detach().cpu().clone() for key,t in model.state_dict().items()}
    opt_state = deepcopy(optimizer.state_dict())
    rng = (torch.get_rng_state(),torch.cuda.get_rng_state())
    targets_at_epoch = plan["targets"]
    focused = {root:dev[root] for root in targets_at_epoch.values()}
    guard = {root:cases["validation"][root] for root in plan["control"]["base"]["guard"]}
    branches = {}
    for arm in ("replay_only","write_and_replay"):
        model.load_state_dict(model_state)
        optimizer.load_state_dict(deepcopy(opt_state))
        torch.set_rng_state(rng[0])
        torch.cuda.set_rng_state(rng[1])
        step,writes,batches = first_step,[],[]
        if arm=="write_and_replay":
            writes.append(dict(step=step,**protect_and_write(model,optimizer,tok,special,dev,guard,targets_at_epoch[str(first)])))
            print(json.dumps(dict(arm=arm,step=step,accepted=writes[-1]["accepted"])),flush=True)
        for epoch,items in enumerate(schedule[first:],first+1):
            step,metrics = train_with_batch_receipt(model,optimizer,items,special,step,expected_steps,batches)
            history.append(dict(arm=arm,epoch=epoch,**metrics))
            if arm=="write_and_replay" and str(epoch) in targets_at_epoch:
                writes.append(dict(step=step,**protect_and_write(model,optimizer,tok,special,dev,guard,targets_at_epoch[str(epoch)])))
                print(json.dumps(dict(arm=arm,step=step,accepted=writes[-1]["accepted"])),flush=True)
        if step!=expected_steps:
            raise ValueError(f"{arm} did not finish the fixed schedule")
        if arm=="write_and_replay" and batches!=branches["replay_only"]["batch_sha256"]:
            raise ValueError("the two arms used different actual padded inputs or labels")
        model.eval()
        model.clear_quant()
        targets = trial.evaluate(model,tok,special,focused)
        test = trial.evaluate(model,tok,special,cases["test"])
        novel = periodic.composition.run_wording(model,tok,special,transfer)
        retained = {root:prior.correct(row,"correction") for root,row in targets["rows"].items()}
        protected = solver.identical_sequences(control["test"],test,prior.existing_answers(control["test"]))
        export = None
        if protected and all(retained.values()):
            path = OUT/f"{arm}.pt"
            with path.open("xb") as out:
                torch.save(dict(model={key:value.detach().cpu() for key,value in model.state_dict().items()},
                                config=vars(model.cfg),tag=TAG,branch=arm),out)
            export = trial.file_sha(path)
        branches[arm] = dict(writes=writes,retained=retained,targets=targets,test=test,transfer=novel,batch_sha256=batches,
                            protected=protected,exported_sha256=export,state_sha256=trial.state_sha(model.state_dict()))
        print(json.dumps(dict(arm=arm,retained=retained,independent=test["totals"],protected=protected)),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,branches=branches,history=history,reference_test=control["test"]["totals"],
                  shared_steps=first_step,total_unique_updates=first_step+2*(expected_steps-first_step),
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
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the sealed replay receipt and authorized cutoff")
    return prior.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=solver.AUTHORIZATION_END,min_seconds=420)


if __name__ == "__main__":
    sys.exit(main())
