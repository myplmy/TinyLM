"""Compare paired bilingual training with selective English-to-Korean value transfer."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from scripts import diag_p109c_bilingual_same_table as crossed
from scripts import prepare_p109c_bilingual_value_transfer as preparation


TAG = "p109c_bilingual_value_transfer_gpu_v1_20261121"
OUT = preparation.OUT.with_name(TAG)
bridge, trial, data, control, baseline = (preparation.bridge, preparation.trial, preparation.data,
                                          preparation.control, preparation.baseline)
PAYLOAD = preparation.OUT / "wide_pairs.npz"
PAIR_WEIGHT, TEMPERATURE = .10, 2.
ARMS = ("paired", "transfer")


def selected_transfer(first_logits, choices, unique, gold, site_correct):
    english_correct = first_logits[1::2].detach().argmax(dim=1).eq(gold)
    korean_wrong = first_logits[::2].detach().argmax(dim=1).ne(gold)
    gate = english_correct & korean_wrong & site_correct.reshape(-1,2).all(1) & (unique.sum(dim=1) > 1)
    teacher = first_logits[1::2].detach().gather(1, choices) / TEMPERATURE
    student = first_logits[::2].gather(1, choices) / TEMPERATURE
    teacher_probs = F.softmax(teacher.masked_fill(~unique, -10000.),dim=1)
    student_log = F.log_softmax(student.masked_fill(~unique, -10000.),dim=1)
    row_cost = F.kl_div(student_log,teacher_probs,reduction="none").sum(dim=1) * TEMPERATURE**2
    return (row_cost * gate).sum(), gate.sum()


def verify_loss():
    logits = torch.tensor(((1.,3.,2.,0.), (4.,0.,2.,1.), (3.,0.,1.,2.), (0.,3.,2.,1.)),requires_grad=True)
    choices = torch.tensor(((0,1,1,2), (0,1,1,2)))
    unique = torch.tensor(((True,True,False,True), (True,True,False,True)))
    gold = torch.tensor((0,1))
    loss, hits = selected_transfer(logits, choices, unique, gold, torch.tensor((True,True,False,True)))
    grad, = torch.autograd.grad(loss,logits)
    if hits.item()!=1 or not torch.isfinite(grad).all() or not grad[0].abs().any() or grad[1:].abs().any():
        raise ValueError("the non-selected or teacher row received the transfer gradient")


def prepare():
    report_path = preparation.OUT / "report.json"
    saved = trial.read_json(report_path)
    base = bridge.base_contract()
    if (saved["source"] != trial.file_sha(Path(preparation.__file__)) or saved["base"] != base
            or saved["inputs"] != trial.file_sha(PAYLOAD)):
        raise ValueError("requires the frozen bilingual source pairs")
    phases = base["stages"]
    n = phases[-1]["rows"]
    with np.load(PAYLOAD, allow_pickle=False) as f:
        if (f["tokens"].shape != (n,data.WIDTH) or f["tokens"].shape != f["labels"].shape
                or f["tokens"].shape != f["context"].shape or f["sites"].shape != (n,6)
                or f["options"].shape != (n//2,4) or f["unique"].shape != (n//2,4)):
            raise ValueError("the paired payload has a different shape")
        paired_gold = np.take_along_axis(f["labels"],f["sites"][:,:1],axis=1).ravel()
        grouped = f["options"][np.arange(n//2),f["targets"]]
        if (not np.array_equal(paired_gold[::2],grouped) or not np.array_equal(paired_gold[1::2],grouped)
                or not np.array_equal(f["sites"][::2,-1],f["sites"][1::2,-1])):
            raise ValueError("paired questions must preserve the same actual first token and row choice")
    verify_loss()
    cross, _ = crossed.prepare()
    return dict(tag=TAG, source=trial.file_sha(Path(__file__)), input_report=trial.file_sha(report_path), base=base,
                payload=saved["inputs"], cross=cross, weight=PAIR_WEIGHT, temperature=TEMPERATURE,
                phases=phases, supervised=[saved["answer_labels"],saved["context_labels"],n],
                warm_updates=sum(phase["rows"]//data.BATCH for phase in phases[:-1]), arms=list(ARMS))


def gpu_arrays(arrays):
    return tuple(torch.as_tensor(v,device="cuda",dtype=torch.long) for v in arrays)


def train_phase(model, selector, optimizer, tensors, expected, stage, step, start, meta=None):
    tokens,labels,context,sites = tensors
    counts = [0,0,0]
    sums = torch.zeros(4,device="cuda")
    routed = torch.zeros((),device="cuda",dtype=torch.long)
    parameters = [*model.parameters(),*selector.parameters()]
    for offset in range(0,len(tokens),data.BATCH):
        batch = slice(offset,offset+data.BATCH)
        ans, pre, loc = labels[batch],context[batch],sites[batch]
        keep, keep_prefix = ans.ne(baseline.IGNORE),pre.ne(baseline.IGNORE)
        answers,prefix = ans[keep],pre[keep_prefix]
        step += 1
        optimizer.param_groups[0]["lr"] = .0015 * min(1.,step/64) * (1-.7*(step/data.UPDATES)**2)
        model.set_anneal(min(1.,step/(.6*data.UPDATES)))
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cuda",dtype=torch.bfloat16):
            hidden = model(tokens[batch],return_hidden=True)
            logits = model._head_logits(hidden[keep]).float()
            answer_loss = F.cross_entropy(logits,answers,reduction="sum")
            nll,_ = control.target_nll(model,hidden[keep_prefix].unsqueeze(0),prefix.unsqueeze(0),rows=control.CE_ROWS)
            context_loss = nll.sum()
            link_logits = selector(hidden,loc).float()
            link_loss = F.cross_entropy(link_logits,loc[:,-1],reduction="sum")
            extra = torch.zeros_like(link_loss)
            if meta is not None:
                candidates, unique = meta
                pair = slice(offset//2,(offset+len(ans))//2)
                per_row = keep.sum(dim=1)
                first = per_row.cumsum(0)-per_row
                extra, accepted = selected_transfer(logits[first],candidates[pair],unique[pair],answers[first][::2],
                                                     link_logits.detach().argmax(dim=1)==loc[:,-1])
                routed += accepted
            loss = (answer_loss/answers.numel() + control.WEIGHT*context_loss/prefix.numel()
                    + baseline.WEIGHT*link_loss/len(ans) + PAIR_WEIGHT*extra/(len(ans)//2))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True)
        optimizer.step()
        counts[0] += answers.numel()
        counts[1] += prefix.numel()
        counts[2] += len(ans)
        sums += torch.stack([v.detach() for v in (answer_loss,context_loss,link_loss,extra)])
        if step % 128 == 0:
            print(json.dumps(dict(stage=stage,step=step,wall=time.perf_counter()-start,
                                  transfer_pairs=int(routed.item()))),flush=True)
    if counts != expected:
        raise ValueError("answer, context or table count differs from the sealed phase")
    means = [v/n for v,n in zip(sums.tolist(),(*counts,counts[-1]//2),strict=True)]
    return dict(stage=stage,step=step,counts=counts,losses=means,transfer_pairs=int(routed.item()))


def fingerprint(model, selector, optimizer):
    state = optimizer.state_dict()
    tensor_state = {f"{p}.{k}":v for p,attrs in state["state"].items() for k,v in attrs.items()}
    if not all(torch.is_tensor(v) for v in tensor_state.values()):
        raise ValueError("unexpected AdamW state representation")
    return dict(model=trial.state_sha(model.state_dict()),selector=trial.state_sha(selector.state_dict()),
                optimizer=trial.state_sha(tensor_state),groups=state["param_groups"])


def evaluate(model, selector, tokenizer, special, tables, basic, translations, directory):
    model.eval()
    selector.eval()
    model.clear_quant()
    exchange = data.evaluate(model,tokenizer,special,tables["exchange"],paired=True)
    switch = data.evaluate(model,tokenizer,special,tables["question_switch"],paired=True)
    original = data.evaluate(model,tokenizer,special,basic["original"],paired=False)
    other_language = data.evaluate(model,tokenizer,special,translations,paired=True)
    translated_slots = baseline.evaluate_slots(model,selector,translations,special["<pad>"])
    for name,result in (("wide_eval",exchange),("question_switch_eval",switch),("original_eval",original),
                        ("translated_eval",other_language),("translated_slots",translated_slots)):
        trial.publish(directory/f"{name}.json",result)
    return dict(exchange=exchange["both_correct"],exchange_language=exchange["by_language"],
                switch=switch["both_correct"],switch_language=switch["by_language"],
                original=original["exact_with_eot"],cross=crossed.compare(exchange["rows"],other_language["rows"]),
                translated_slots=translated_slots["individual"])


def worker(plan, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if not torch.cuda.is_bf16_supported() or prepare()!=plan:
        raise ValueError("the accelerator or sealed paired contract changed")
    tokenizer,special,arrays,phases,_ = control.profile()
    if phases != plan["phases"]:
        raise ValueError("the common warm phases changed")
    x,y,ctx = arrays
    with np.load(baseline.INPUT/"sites.npz",allow_pickle=False) as f:
        loc = f["sites"]
    with np.load(PAYLOAD,allow_pickle=False) as f:
        paired = gpu_arrays([f[k] for k in ("tokens","labels","context","sites")])
        candidates, unique = torch.as_tensor(f["options"],device="cuda",dtype=torch.long),torch.as_tensor(f["unique"],device="cuda")
    tags = trial.read_json(baseline.INPUT/"validation.json")
    basic = trial.read_json(data.DATA/"evaluation.json")
    _,(_,_,_,translations) = crossed.prepare()
    torch.manual_seed(data.SEED)
    model = baseline.TiedMLPTransformer(trial.make_config())
    if trial.state_sha(model.state_dict()) != plan["base"]["initial"] or len(model.visit_schedule())!=28:
        raise ValueError("the unparented initial model or route differs")
    selector = baseline.ValueLink(model.cfg.dim)
    model.to("cuda")
    selector.to("cuda")
    optimizer = torch.optim.AdamW([*model.parameters(),*selector.parameters()],lr=.0015,weight_decay=.01,fused=True)
    start = time.perf_counter()
    warm_steps = 0
    warm_phases = []
    print(f"START {TAG}",flush=True)
    for phase in phases[:-1]:
        cut = slice(phase["offset"],phase["offset"]+phase["rows"])
        warm = train_phase(model,selector,optimizer,gpu_arrays([a[cut] for a in (x,y,ctx,loc)]),
                           [phase["targets"],phase["context_targets"],phase["rows"]],
                           phase["stage"],warm_steps,start)
        warm_steps = warm["step"]
        warm_phases.append(warm)
    if warm_steps != plan["warm_updates"]:
        raise ValueError("the common starting steps changed")
    proof = fingerprint(model,selector,optimizer)
    snapshot = OUT/"shared_wide_start.pt"
    with snapshot.open("xb") as handle:
        torch.save(dict(model=model.state_dict(),selector=selector.state_dict(),optimizer=optimizer.state_dict(),
                        cpu_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state()),handle)
    state = torch.load(snapshot,weights_only=True,map_location="cpu")
    results = {}
    for arm in ARMS:
        model.load_state_dict(state["model"])
        selector.load_state_dict(state["selector"])
        # Loading from fresh serialized tensors avoids sharing CPU optimizer storage between arms.
        fresh_optimizer = torch.load(snapshot,weights_only=True,map_location="cpu")["optimizer"]
        optimizer.load_state_dict(fresh_optimizer)
        torch.set_rng_state(state["cpu_rng"])
        torch.cuda.set_rng_state(state["cuda_rng"])
        model.train()
        selector.train()
        model.clear_quant()
        if fingerprint(model,selector,optimizer) != proof:
            raise ValueError("an arm did not resume the exact shared model, selector and optimizer state")
        extra = (candidates,unique) if arm=="transfer" else None
        wide = train_phase(model,selector,optimizer,paired,plan["supervised"],arm,warm_steps,start,extra)
        if wide["step"] != data.UPDATES or (extra is not None and not wide["transfer_pairs"]):
            raise ValueError("an arm did not finish training or execute the transfer")
        directory = OUT/arm
        directory.mkdir()
        result = evaluate(model,selector,tokenizer,special,tags,basic,translations,directory)
        final = directory/"foundation.pt"
        with final.open("xb") as handle:
            torch.save(dict(tag=TAG,arm=arm,step=data.UPDATES,parent=None,config=asdict(model.cfg),
                            model={k:v.detach().cpu() for k,v in model.state_dict().items()},
                            train_head={k:v.detach().cpu() for k,v in selector.state_dict().items()}),handle)
        results[arm] = dict(wide=wide,assessment=result,checkpoint=trial.file_sha(final),
                            state=trial.state_sha(model.state_dict()))
        trial.publish(directory/"report.json",results[arm])
        print(json.dumps(dict(arm=arm,result=result),ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,warm_phases=warm_phases,warm_state=proof,
                                        warm_checkpoint=trial.file_sha(snapshot),arms=results,
                                        updates=warm_steps+len(ARMS)*(data.UPDATES-warm_steps),
                                        elapsed=time.perf_counter()-start,
                                        peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                                        peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))


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
        parser.error("requires the sealed paired experiment and approved deadline")
    return baseline.owner.supervise(worker,(plan,),OUT,args.stop_by,
                                    authorization_end=bridge.AUTHORIZATION_END,min_seconds=1500)


if __name__ == "__main__":
    raise SystemExit(main())
