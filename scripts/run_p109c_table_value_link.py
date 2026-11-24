"""Train a value-position selector alongside the unchanged P109C language path."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from scripts import p109_cuda_owner as owner
from scripts import run_p109c_correction_scratch as trial
from scripts import run_p109c_table_context_ntp as control
from scripts import run_p109c_table_grounding as data
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE


TAG = "p109c_table_value_link_gpu_v1_20261121"
INPUT = trial.DATA.parent / (TAG + "_inputs")
OUT = trial.DATA.parent / TAG
CONTROL_RECEIPT = trial.ROOT / "test_result/109_log_20261121_P109C_TableContextNTP_CPU.txt"
WEIGHT, PROJECTION = 0.25, 64
VALUE = re.compile(r": ([0-9]+)")


class ValueLink(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.query = nn.Linear(dim, PROJECTION, bias=False)
        self.key = nn.Linear(dim, PROJECTION, bias=False)

    def forward(self, hidden, sites):
        rows = torch.arange(len(sites), device=hidden.device)
        query = self.query(hidden[rows, sites[:, 0]])
        values = self.key(hidden[rows[:, None], sites[:, 1:5]])
        return (values @ query.unsqueeze(-1)).squeeze(-1) / PROJECTION**0.5


def source_pins():
    files = Path(__file__), Path(owner.__file__)
    return {**control.sources(), **{str(p.relative_to(trial.ROOT)): trial.file_sha(p) for p in files}}


def sites_from_prompt(tokenizer, prompt, gold):
    text = tokenizer.decode(prompt, skip_special_tokens=False)
    encoded = tokenizer.encode(text)
    entries = list(VALUE.finditer(text))
    values = [entry.group(1) for entry in entries]
    if encoded.ids != prompt or len(set(values)) != 4 or len(values) != 4 or gold not in values:
        raise ValueError("cannot identify four candidate values in the exact input")
    positions = []
    for match in entries:
        final_digit = match.end(1)-1
        location = [i for i, (start,end) in enumerate(encoded.offsets) if start <= final_digit < end]
        if len(location) != 1:
            raise ValueError("the last digit needs one token position")
        positions.append(location[0])
    query = len(prompt)-1
    if positions != sorted(set(positions)) or positions[-1] >= query:
        raise ValueError("value locations must precede the query, without overlap")
    return query, *positions, values.index(gold)


def compile_metadata():
    if INPUT.exists() or OUT.exists():
        raise FileExistsError(INPUT)
    frozen = control.read_receipt(CONTROL_RECEIPT)
    tok, special, (x, y, _), stages, _ = control.profile()
    metadata = np.empty((len(x),6), dtype=np.int16)
    for i, (tokens, targets) in enumerate(zip(x, y, strict=True)):
        match = np.flatnonzero(targets != IGNORE)
        labels = targets[match].tolist()
        if len(labels) < 2 or labels[-1] != special["<|im_end|>"]:
            raise ValueError("control supervision must end with the answer delimiter")
        first = int(match[0])
        if int(tokens[first+1]) != labels[0]:
            raise ValueError("the answer prediction and the next input token are misaligned")
        gold = tok.decode(labels[:-1], skip_special_tokens=False)
        metadata[i] = sites_from_prompt(tok, tokens[:first+1].tolist(), gold)

    val = trial.read_json(data.DATA / "evaluation.json")
    targets = []
    for row in val["wide"]:
        other, gold = data.form(row["values"], row["order"], row["other"], row["language"], 2)
        alternate = data.generation_prompt(tok, other)
        if gold == row["gold"][0]:
            raise ValueError("query switch needs a different correct field")
        targets.append({**row, "prompts": [row["prompts"][0], alternate], "gold": [row["gold"][0], gold]})
    validation = {"exchange": val["wide"], "question_switch": targets, "short": val["two_digit"]}
    for mode, pairs in validation.items():
        for pair in pairs:
            info = [sites_from_prompt(tok, ids, gold) for ids,gold in zip(pair["prompts"],pair["gold"],strict=True)]
            pair["slots"] = info
            if (info[0][-1] == info[1][-1]) != (mode != "question_switch"):
                raise ValueError("the validation switch does not match the field position contract")

    INPUT.mkdir()
    with (INPUT / "sites.npz").open("xb") as stream:
        np.savez_compressed(stream, sites=metadata)
    trial.publish(INPUT / "validation.json", validation)
    return dict(tag=TAG, sources=source_pins(), weight=WEIGHT, projection=PROJECTION, initial=frozen["initial_sha256"],
                control_receipt=trial.file_sha(CONTROL_RECEIPT), rows=len(metadata), positions=metadata.size,
                training_by_slot=np.bincount(metadata[:, -1]).tolist(), stages=stages,
                inputs={name: trial.file_sha(INPUT/name) for name in ("sites.npz", "validation.json")})


def load_receipt(path):
    sealed = trial.read_json(path)
    if (sealed["tag"] != TAG or sealed["sources"] != source_pins() or sealed["weight"] != WEIGHT
            or sealed["projection"] != PROJECTION or sealed["control_receipt"] != trial.file_sha(CONTROL_RECEIPT)):
        raise ValueError("the value-link preflight changed")
    if any(trial.file_sha(INPUT/name) != sealed["inputs"][name] for name in ("sites.npz", "validation.json")):
        raise ValueError("the prepared value locations changed")
    return sealed


@torch.inference_mode()
def evaluate_slots(model, selector, pairs, pad):
    inputs = [(p,s) for row in pairs for p,s in zip(row["prompts"],row["slots"],strict=True)]
    predicted = []
    for start in range(0, len(inputs), data.BATCH):
        batch = inputs[start:start+data.BATCH]
        length = max(len(prompt) for prompt,_ in batch)
        ids = torch.tensor([prompt+[pad]*(length-len(prompt)) for prompt,_ in batch], device="cuda")
        sites = torch.tensor([info for _,info in batch], device="cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            values = selector(model(ids, return_hidden=True), sites)
        predicted.extend(values.argmax(-1).tolist())
    rows = []
    for index, pair in enumerate(pairs):
        guess = predicted[2*index:2*index+2]
        gold = [item[-1] for item in pair["slots"]]
        rows.append(dict(root=pair["root"], language=pair["language"], guess=guess, gold=gold,
                         exact=[a==b for a,b in zip(guess,gold)]))
    return dict(individual=sum(sum(r["exact"]) for r in rows), joint=sum(all(r["exact"]) for r in rows), rows=rows)


def worker(path, fraction):
    receipt = load_receipt(path)
    tok, special, arrays, stages, _ = control.profile()
    if stages != receipt["stages"]:
        raise ValueError("the control data schedule changed")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 required")
    x, y, context = [torch.from_numpy(v).to("cuda", dtype=torch.long) for v in arrays]
    with np.load(INPUT/"sites.npz", allow_pickle=False) as located:
        sites = torch.from_numpy(located["sites"]).to("cuda", dtype=torch.long)
    if sites.shape != (len(x),6):
        raise ValueError("the slot metadata shape changed")
    validation = trial.read_json(INPUT/"validation.json")
    evaluation = trial.read_json(data.DATA/"evaluation.json")
    torch.manual_seed(data.SEED)
    model = TiedMLPTransformer(trial.make_config())
    initial = trial.state_sha(model.state_dict())
    if initial != receipt["initial"] or len(model.visit_schedule()) != 28:
        raise ValueError("initial state or recursive route differs")
    selector = ValueLink(model.cfg.dim)
    model.to("cuda")
    selector.to("cuda")
    parameters = [*model.parameters(), *selector.parameters()]
    optimizer = torch.optim.AdamW(parameters, lr=.0015, weight_decay=.01, fused=True)
    step, stage_reports = 0, []
    started = time.perf_counter()
    print(f"START {TAG}", flush=True)
    for phase in stages:
        offset = phase["offset"]
        sums = torch.zeros(3, device="cuda")
        answer_count, prefix_count, slot_count = 0, 0, 0
        for start in range(offset, offset+phase["rows"], data.BATCH):
            block = slice(start,start+data.BATCH)
            tokens, answer, prefix, places = x[block], y[block], context[block], sites[block]
            keep, keep_prefix = answer.ne(IGNORE), prefix.ne(IGNORE)
            gold, prompt = answer[keep], prefix[keep_prefix]
            step += 1
            optimizer.param_groups[0]["lr"] = .0015 * min(1., step/64) * (1-.7*(step/data.UPDATES)**2)
            model.set_anneal(min(1., step/(.6*data.UPDATES)))
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                h = model(tokens, return_hidden=True)
                answer_sum = F.cross_entropy(model._head_logits(h[keep]).float(), gold, reduction="sum")
                nll, _ = control.target_nll(model,h[keep_prefix].unsqueeze(0),prompt.unsqueeze(0),rows=control.CE_ROWS)
                prefix_sum = nll.sum()
                link_sum = F.cross_entropy(selector(h, places).float(), places[:, -1], reduction="sum")
                loss = answer_sum/gold.numel() + control.WEIGHT*prefix_sum/prompt.numel() + WEIGHT*link_sum/len(places)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
            optimizer.step()
            answer_count += gold.numel()
            prefix_count += prompt.numel()
            slot_count += len(places)
            sums += torch.stack([answer_sum.detach(),prefix_sum.detach(),link_sum.detach()])
            if step % 128 == 0:
                print(json.dumps(dict(stage=phase["stage"], step=step, wall=time.perf_counter()-started,
                                     ce=[v/n for v,n in zip(sums.tolist(),(answer_count,prefix_count,slot_count))])),flush=True)
        counts = answer_count,prefix_count,slot_count
        if counts != (phase["targets"],phase["context_targets"],phase["rows"]):
            raise RuntimeError("the controlled training counts changed")
        model.eval()
        selector.eval()
        model.clear_quant()
        pairs = validation["short" if phase["stage"]=="two_digit" else "exchange"]
        greedy = data.evaluate(model,tok,special,pairs,paired=True)
        slots = evaluate_slots(model,selector,pairs,special["<pad>"])
        label = phase["stage"]
        trial.publish(OUT/f"{label}_eval.json",greedy)
        trial.publish(OUT/f"{label}_slots.json",slots)
        info = dict(stage=label,step=step,counts=counts,ce=[v/n for v,n in zip(sums.tolist(),counts)],
                    greedy_joint=greedy["both_correct"],nonempty=greedy["nonempty_answers"],
                    by_language=greedy["by_language"],select_joint=slots["joint"],select_individual=slots["individual"])
        stage_reports.append(info)
        print(json.dumps(info),flush=True)
        model.train()
        selector.train()
        model.clear_quant()
    if step!=data.UPDATES:
        raise RuntimeError("converter lost optimizer updates")
    model.eval()
    selector.eval()
    switch = data.evaluate(model,tok,special,validation["question_switch"],paired=True)
    switch_slots = evaluate_slots(model,selector,validation["question_switch"],special["<pad>"])
    val = data.evaluate(model,tok,special,evaluation["original"],paired=False)
    trial.publish(OUT/"question_switch_eval.json",switch)
    trial.publish(OUT/"question_switch_slots.json",switch_slots)
    trial.publish(OUT/"original_eval.json",val)
    last = stage_reports[-1]
    gate = (last["greedy_joint"] >= data.GATE["wide_pairs"] and min(last["by_language"].values()) >= data.GATE["language_pairs"]
            and val["exact_with_eot"] >= data.GATE["original_single"])
    state = {name: value.detach().cpu() for name,value in model.state_dict().items()}
    checkpoint = OUT/"foundation.pt"
    with checkpoint.open("xb") as stream:
        torch.save(dict(model=state,config=asdict(model.cfg),parent=None,step=step,tag=TAG,
                        train_head={name:t.detach().cpu() for name,t in selector.state_dict().items()}),stream)
    if receipt != load_receipt(path):
        raise RuntimeError("the preflight receipt changed during the run")
    trial.publish(OUT/"report.json",dict(tag=TAG,parent=None,initial_sha256=initial,updates=step,stages=stage_reports,
                  gate=gate,original=val["exact_with_eot"],switch_greedy_joint=switch["both_correct"],
                  switch_select_joint=switch_slots["joint"],switch_select_individual=switch_slots["individual"],
                  checkpoint_sha256=trial.file_sha(checkpoint),state_sha256=trial.state_sha(state),
                  preflight_sha256=trial.file_sha(path),wall=time.perf_counter()-started,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                  peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))
    print(f"FINISH {TAG} gate={gate} exchange={last['greedy_joint']}/64 original={val['exact_with_eot']}/64",flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(json.dumps(compile_metadata(),indent=2))
        return 0
    if args.receipt is None or args.stop_by is None:
        parser.error("run requires --receipt and --stop-by")
    load_receipt(args.receipt)
    return owner.supervise(worker,(args.receipt,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=1200)


if __name__ == "__main__":
    sys.exit(main())
