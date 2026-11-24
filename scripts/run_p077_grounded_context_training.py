"""Matched 2,048-token training with fixed or varied evidence positions."""

import argparse
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import sys
from time import perf_counter

import numpy as np
import torch
import torch.nn.functional as F

from scripts import diag_p077_grounded_length_controls as controls


wide = controls.wide
trial = wide.trial
foundation = wide.foundation
data = foundation.data
TAG = "p077_grounded_context_distance_train_gpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)
EXPORT_TAG = "p077_grounded_near_export_gpu_v2_20261121"
EXPORT_OUT = OUT.with_name(EXPORT_TAG)
ORIGINAL_SOURCE = trial.ROOT / "handoff/audit/source_snapshots/P077_GroundedContextTraining_20261121_v1.py"
EXPORT_SEED = 10691
STEPS, BATCH, SEED = 192, 8, 754891
WIDTH = 2048
LR = .00035
ARMS = ("near_only", "mixed_positions")
TRAIN_WORDS = {
    "en": ("teacups", "lanterns", "notebooks", "curtains", "paintbrushes", "umbrellas", "blankets", "baskets"),
    "ko": ("찻잔", "초롱불", "공책", "커튼", "붓", "우산", "담요", "바구니"),
}


def old_value_groups(tokenizer):
    _, _, original_cases, _, _ = trial.load_cases()
    used = data.source_keys(tokenizer, original_cases)
    rng = Random(data.PROFILE_SEED)
    data.eval_pairs(tokenizer,rng,11,100,used)
    data.eval_pairs(tokenizer,rng,11,9980,used)
    digest = sha256()
    for _,low,high,count in data.STAGES:
        for i in range(count):
            values,*_ = data.draw(rng,i,low,high,used)
            digest.update(bytes.fromhex(data.authored.digest(["table_values",sorted(values)])))
    if digest.hexdigest()!=trial.read_json(data.DATA/"preflight.json")["train_values_sha256"]:
        raise ValueError("the previously used table groups were not reconstructed")
    return used, digest.hexdigest()


def training_filler(tokenizer, language):
    words = TRAIN_WORDS[language]
    template = {"en":"During the rehearsal, the crew set aside {a} and carried {b} into another room. "
                     "Music played in the hallway while the scene was being arranged. ",
                "ko":"연습 시간에 준비팀은 {a}을 한쪽에 두고 {b}을 옆방으로 옮겼다. "
                     "장면을 준비하는 동안 복도에서는 음악이 들렸다. "}[language]
    paragraphs = [template.format(a=a,b=b) for a in words for b in words if a!=b]
    return tokenizer.encode("\n\n".join(paragraphs),add_special_tokens=False).ids * 2


def prepare():
    prior, (tokenizer,special,eval_rows,eval_fixture) = controls.prepare()
    baseline = trial.read_json(controls.OUT/"supervisor.json")
    if baseline["returncode"] or baseline["stop_reason"]:
        raise ValueError("previous long-context controls did not finish")
    original, (_,_,_,long_fixture) = wide.prepare()
    used, excluded_sha = old_value_groups(tokenizer)
    pools = {lang:training_filler(tokenizer,lang) for lang in ("ko","en")}
    brk = tokenizer.encode("\n\n---\n\n",add_special_tokens=False).ids
    role_head = tokenizer.encode("<|im_start|>user\n",add_special_tokens=False).ids
    rng = Random(SEED)
    data_batches = []
    hashers = {arm:sha256() for arm in ARMS}
    range_hash = sha256()
    target_total, slots, pair_index = 0,0,0
    for update in range(STEPS):
        length = trial.WIDTH if update%4==0 else WIDTH
        shape = (BATCH,length)
        token_arrays = {arm:np.full(shape,special["<pad>"],dtype=np.uint16) for arm in ARMS}
        indices = {arm:np.zeros((BATCH,6),dtype=np.int32) for arm in ARMS}
        targets = np.full(shape,data.IGNORE,dtype=np.int16)
        for entry in range(0,BATCH,2):
            values,order,field,other,language = data.draw(rng,pair_index,11,9980,used)
            swapped = list(values)
            swapped[field],swapped[other] = swapped[other],swapped[field]
            range_hash.update(bytes.fromhex(data.authored.digest(["table_values",sorted(values)])))
            paired = [data.form(values,order,field,language,pair_index%3),data.form(tuple(swapped),order,field,language,pair_index%3)]
            for offset,(record,gold) in enumerate(paired):
                item = data.encode_record(record,tokenizer,context=trial.WIDTH)
                base = data.generation_prompt(tokenizer,record)
                wanted = [token for token in item.y if token!=data.IGNORE]
                if (item.x!=base+wanted or wanted[-1]!=special["<|im_end|>"] or item.y[-1]!=data.IGNORE):
                    raise ValueError("response mask or shifted label differs")
                lookup = foundation.sites_from_prompt(tokenizer,base,gold)
                count = length-len(item.x) if length==WIDTH else 0
                if count:
                    stream = pools[language]
                    size = count-2*len(brk)
                    if size < 1 or len(stream)<=size:
                        raise ValueError("not enough neutral training text")
                    begin = (pair_index*97)%(len(stream)-size)
                    filler = brk+stream[begin:begin+size]+brk
                    question = data.authored.field_question(language,field,pair_index%3)
                    text = tokenizer.decode(base,skip_special_tokens=False)
                    question_at = text.rfind(question)
                    cut = wide.choices.token_boundary(tokenizer.encode(text),len(text[:question_at].rstrip()))
                    if (question_at < 1 or base[:len(role_head)] != role_head or cut is None
                            or not all(len(role_head) <= pos < cut for pos in lookup[1:5])):
                        raise ValueError("the existing value locations must stay inside the table")
                    head,table,tail = role_head,base[len(role_head):cut],base[cut:]
                else:
                    filler,head,table,tail = [],[],base,[]
                row = entry+offset
                for arm in ARMS:
                    start = count if arm=="near_only" else count*((pair_index//2)%5)//4
                    prompt = head+filler[:start]+table+filler[start:]+tail
                    sequence = prompt+wanted
                    token_arrays[arm][row,:len(sequence)] = sequence
                    indices[arm][row] = (lookup[0]+count,*(i+start for i in lookup[1:5]),lookup[-1])
                target_begin = len(base)+count-1
                targets[row,target_begin:target_begin+len(wanted)] = wanted
                if any(not np.array_equal(x[row,target_begin+1:target_begin+1+len(wanted)], wanted)
                       for x in token_arrays.values()):
                    raise ValueError("a visible shifted target moved between training arms")
                target_total += len(wanted)
            pair_index += 1
        for arm in ARMS:
            for array in (token_arrays[arm],targets,indices[arm]):
                hashers[arm].update(array.tobytes())
        data_batches.append((token_arrays, targets, indices))
        slots += BATCH*length
    plan = dict(tag=TAG, seed=SEED, updates=STEPS, batch=BATCH, lr=LR, slots=slots, paired_train=pair_index,
                targets=target_total, source=original, controls_sha256=trial.file_sha(controls.OUT/"report.json"),
                long_fixtures_sha256=prior["input_sha256"], excluded_sha256=excluded_sha, group_sha256=range_hash.hexdigest(),
                arm_sha256={name:h.hexdigest() for name,h in hashers.items()}, source_sha256=trial.file_sha(Path(__file__)))
    return plan,(tokenizer,special,eval_rows,long_fixture,eval_fixture,data_batches)


def score(model, tokenizer, special, cases, prompts):
    grouped = defaultdict(list)
    for i,p in enumerate(prompts):
        grouped[len(p)].append(i)
    answers = [None]*len(prompts)
    for indices in grouped.values():
        generated = controls.batches(lambda rows:wide.cached(model,tokenizer,special,rows),[prompts[i] for i in indices])
        for i,result in zip(indices,generated,strict=True):
            answers[i] = result
    records = []
    for index,row in enumerate(cases):
        generated = answers[2*index:2*index+2]
        hit = [answer["eot"] and answer["answer"]==gold for answer,gold in zip(generated,row["gold"],strict=True)]
        records.append(dict(root=row["root"],language=row["language"],gold=row["gold"],answers=generated,exact=hit,both=all(hit)))
    counts = {lang:dict(both=sum(r["both"] for r in records if r["language"]==lang),
                        individual=sum(sum(r["exact"]) for r in records if r["language"]==lang)) for lang in ("ko","en")}
    return dict(counts=counts, rows=records)


def export_receipt(profile):
    report_path, final_path = OUT/"report.json", OUT/"supervisor.json"
    report = trial.read_json(report_path)
    final = trial.read_json(final_path)
    archive_sha = trial.file_sha(ORIGINAL_SOURCE)
    if (report["tag"]!=TAG or final["returncode"] or final["stop_reason"]
            or dict(profile,source_sha256=archive_sha)!=report["preflight"]):
        raise ValueError("the archived training experiment differs from the exact replay inputs")
    reference = report["arms"]["near_only"]
    if reference["history"][-1]["step"] != STEPS or reference["checkpoint_sha256"] is not None:
        raise ValueError("the near-only endpoint is already saved or was not completed")
    return dict(tag=EXPORT_TAG,training=profile,archive_sha256=archive_sha,seed=EXPORT_SEED,
                training_report_sha256=trial.file_sha(report_path),training_terminal_sha256=trial.file_sha(final_path),
                arm="near_only",expected_state_sha256=reference["state_sha256"])


def worker(profile, export, fraction):
    torch.set_num_threads(1)
    checked,(tokenizer,special,cases,fixtures,extra,batches) = prepare()
    if checked != profile:
        raise ValueError("long-context training seal changed")
    if export is not None and export_receipt(checked) != export:
        raise ValueError("the near-only export receipt changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    common = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(common["model"])!=profile["source"]["source"]["state_sha256"]:
        raise ValueError("wrong common initial state")
    cfg = replace(wide.TMTConfig(**common["config"]),max_seq_len=WIDTH)
    model = wide.TiedMLPTransformer(cfg).to("cuda")
    link = foundation.ValueLink(cfg.dim).to("cuda")
    parameters = list(model.parameters())+list(link.parameters())
    evaluations = {"short":[p for row in cases for p in row["prompts"]]}
    for key in next(iter(fixtures.values())):
        evaluations[key] = [p for row in cases for p in fixtures[row["root"]][key]]
    evaluations.update({key:extra[key] for key in ("2048_near_diverse","2048_far_diverse")})
    results = {}
    arms = ARMS if export is None else (export["arm"],)
    for arm in arms:
        model.load_state_dict(common["model"])
        link.load_state_dict(common["train_head"])
        model.clear_quant()
        model.train()
        if export is not None:
            torch.manual_seed(export["seed"])
        optimizer = torch.optim.AdamW(parameters,lr=LR,weight_decay=.01,fused=True)
        start = perf_counter()
        torch.cuda.reset_peak_memory_stats()
        history = []
        for step,(xs,ys,locations) in enumerate(batches,1):
            x,y,places = [torch.from_numpy(array).to(device="cuda",dtype=torch.long)
                          for array in (xs[arm].astype(np.int64),ys,locations[arm])]
            keep = y.ne(data.IGNORE)
            optimizer.param_groups[0]["lr"] = LR*min(1.,step/12)*(1.-.7*(step/STEPS)**2)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda",dtype=torch.bfloat16):
                hidden = model(x,return_hidden=True)
                answer = F.cross_entropy(model._head_logits(hidden[keep]).float(),y[keep])
                value = F.cross_entropy(link(hidden,places).float(),places[:,-1])
            (answer+foundation.WEIGHT*value).backward()
            torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True)
            optimizer.step()
            if step%48==0:
                row = dict(arm=arm,step=step,answer_ce=answer.item(),link_ce=value.item(),seconds=perf_counter()-start)
                history.append(row)
                print(json.dumps(row),flush=True)
        train_time = perf_counter()-start
        peak = torch.cuda.max_memory_allocated()/2**20
        if export is not None:
            weights = {name:t.detach().cpu() for name,t in model.state_dict().items()}
            digest = trial.state_sha(weights)
            checked = dict(tag=EXPORT_TAG,arm=arm,updates=STEPS,history=history,train_seconds=train_time,
                           peak_allocated_mib=peak,state_sha256=digest,expected_state_sha256=export["expected_state_sha256"],
                           matches_archived_state=digest==export["expected_state_sha256"],evaluated=0,preflight=export)
            path = EXPORT_OUT/"near_only.pt"
            with path.open("xb") as out:
                torch.save(dict(model=weights,config=vars(cfg),tag=EXPORT_TAG,arm=arm),out)
            trial.publish(EXPORT_OUT/"report.json",dict(checked,checkpoint_sha256=trial.file_sha(path)))
            print(f"FROZEN_DEPLOYMENT_STATE {digest}",flush=True)
            return
        model.eval()
        model.clear_quant()
        raw = {case:score(model,tokenizer,special,cases,prompts) for case,prompts in evaluations.items()}
        counts = {case:value["counts"] for case,value in raw.items()}
        both = lambda name:sum(x["both"] for x in counts[name].values())
        accepted = both("2048_far")>=8 and both("2048_far_diverse")>=4
        weights = {name:t.detach().cpu() for name,t in model.state_dict().items()}
        sha = trial.state_sha(weights)
        saved = None
        if accepted:
            path = OUT/f"{arm}.pt"
            with path.open("xb") as out:
                torch.save(dict(model=weights,config=vars(cfg),tag=TAG,arm=arm),out)
            saved = trial.file_sha(path)
        result = dict(history=history,peak_allocated_mib=peak,train_seconds=train_time,state_sha256=sha,
                      checkpoint_sha256=saved,far_candidate=accepted,counts=counts)
        trial.publish(OUT/f"{arm}.json",dict(result,raw=raw))
        results[arm] = result
        print(json.dumps(dict(arm=arm,counts=counts,far_candidate=accepted)),flush=True)
    trial.publish(OUT/"report.json",dict(tag=TAG, preflight=profile,arms=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run","export-check","export"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    export = export_receipt(plan) if args.mode.startswith("export") else None
    receipt = export if export is not None else plan
    if args.mode in ("check","export-check"):
        print(json.dumps(receipt,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=receipt:
        parser.error("run requires the exact preflight and authorized stop time")
    output, minimum = (OUT,480) if export is None else (EXPORT_OUT,120)
    return wide.owner.supervise(worker,(plan,export),output,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=minimum)


if __name__=="__main__":
    sys.exit(main())
