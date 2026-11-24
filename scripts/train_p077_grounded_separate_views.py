"""Learn a table selector over separate observed table and query features."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
from random import Random
import sys
from time import perf_counter

import torch
import torch.nn.functional as F

from scripts import diag_p077_grounded_value_readout as previous
from scripts import run_p077_grounded_context_training as training
from scripts import train_p077_grounded_value_readout as head_baseline


wide = previous.wide
trial = previous.trial
foundation = previous.foundation
data = foundation.data
TAG = "p077_grounded_separate_view_head_gpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)


def marker_positions(tokens, marker):
    return [i for i in range(len(tokens)-len(marker)+1) if tokens[i:i+len(marker)]==marker]


def parse_long(row, head, first, last):
    tokens = row["prompt"]
    opening,closing = marker_positions(tokens,first),marker_positions(tokens,last)
    if not opening or not closing:
        raise ValueError("the input lacks an explicit remote table and question boundary")
    table_end, question_start = opening[0],closing[-1]+len(last)
    values = row["positions"][1:]
    if (tokens[:len(head)]!=head or not len(head)<=min(values)<=max(values)<table_end<question_start<len(tokens)
            or row["positions"][0]!=len(tokens)-1):
        raise ValueError("the observed values and question must belong to separate bounded spans")
    return dict(table=tokens[:table_end],query=head+tokens[question_start:],positions=values,values=row["values"],
                root=row["root"],language=row["language"],side=row["side"],gold=row["expected"])


def training_samples(tokenizer, head):
    used,origin_sha = training.old_value_groups(tokenizer)
    rng = Random(training.SEED)
    samples = []
    for i in range(training.STEPS*training.BATCH//2):
        values,order,field,other,language = data.draw(rng,i,11,9980,used)
        swapped = list(values)
        swapped[field],swapped[other] = swapped[other],swapped[field]
        for table in (values,tuple(swapped)):
            record,gold = data.form(table,order,field,language,i%3)
            prompt = data.generation_prompt(tokenizer,record)
            text = tokenizer.decode(prompt,skip_special_tokens=False)
            offset = text.rfind(data.authored.field_question(language,field,i%3))
            cut = wide.choices.token_boundary(tokenizer.encode(text),len(text[:offset].rstrip()))
            cells,choices = previous.observation(tokenizer,prompt)
            if offset<1 or cut is None or max(cells)>=cut or prompt[:len(head)]!=head:
                raise ValueError("the short authoring record does not split at the observed question")
            samples.append(dict(table=prompt[:cut],query=head+prompt[cut:],positions=cells,target=choices.index(gold)))
    return samples,origin_sha


def prepare():
    raw, (tok,special,contexts) = previous.prepare()
    checkpoint = head_baseline.OUT/"trained_head.pt"
    report = trial.read_json(head_baseline.OUT/"report.json")
    terminal = trial.read_json(head_baseline.OUT/"supervisor.json")
    if (terminal["returncode"] or terminal["stop_reason"]
            or trial.file_sha(checkpoint)!=report["weights_sha256"] or report["body_sha256"]!=raw["base"]["state_sha256"]):
        raise ValueError("requires the verified frozen-body selector")
    encode = lambda s:tok.encode(s,add_special_tokens=False).ids
    head,first,last = (encode(t) for t in ("<|im_start|>user\n","\n\n---\n","\n---\n\n"))
    fixtures = {arm:[parse_long(r,head,first,last) for r in rows] for arm,rows in contexts.items()}
    samples,origin_sha = training_samples(tok,head)
    widths = [max(len(r["query"]),len(r["table"])) for rows in (*fixtures.values(),samples) for r in rows]
    if max(widths)>trial.WIDTH or len(samples)!=training.BATCH*training.STEPS:
        raise ValueError("expected complete separate short views and matched updates")
    plan = dict(tag=TAG,source=raw,initial_head_sha256=report["weights_sha256"],historical_table_sha256=origin_sha,
                separate_input_sha256=data.authored.digest(fixtures),separate_training_sha256=data.authored.digest(samples),
                lr=head_baseline.LR,updates=training.STEPS,max_encoder_tokens=max(widths),
                source_sha256=trial.file_sha(Path(__file__)))
    return plan,(tok,special,fixtures,samples)


@torch.no_grad()
def features(model, rows, pad):
    def hidden(key):
        width = max(len(row[key]) for row in rows)
        tokens = torch.tensor([row[key]+[pad]*(width-len(row[key])) for row in rows],device="cuda")
        return model(tokens,return_hidden=True)
    with torch.autocast("cuda",dtype=torch.bfloat16):
        i = torch.arange(len(rows),device="cuda")
        ends = torch.tensor([len(r["query"])-1 for r in rows],device="cuda")
        cells = torch.tensor([r["positions"] for r in rows],device="cuda")
        query = hidden("query")[i,ends]
        keys = hidden("table")[i[:,None],cells]
    return torch.cat((query[:,None],keys),dim=1).float()


@torch.no_grad()
def observe(head, key_values, rows, tok, end):
    loc = torch.arange(5,device="cuda").expand(len(rows),-1)
    positions = head(key_values,loc).argmax(-1).tolist()
    output = []
    for row,slot in zip(rows,positions,strict=True):
        text = row["values"][slot]
        output.append(dict(root=row["root"],side=row["side"],language=row["language"],slot=slot,
                           selected=text,gold=row["gold"],correct=text==row["gold"],
                           ids=[*tok.encode(text,add_special_tokens=False).ids,end]))
    return output


def worker(plan, fraction):
    torch.set_num_threads(1)
    checked,(tok,special,fixtures,samples) = prepare()
    if checked!=plan:
        raise ValueError("separate-view data changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    fingerprint = plan["source"]["base"]["state_sha256"]
    if trial.state_sha(state["model"])!=fingerprint:
        raise ValueError("wrong frozen body")
    cfg = replace(wide.TMTConfig(**state["config"]),max_seq_len=trial.WIDTH)
    model = wide.TiedMLPTransformer(cfg).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(state["model"])
    model.freeze_quant()
    head = foundation.ValueLink(cfg.dim).to("cuda")
    previous_head = torch.load(head_baseline.OUT/"trained_head.pt",weights_only=True,map_location="cpu")
    head.load_state_dict(previous_head["train_head"])
    pad,end = (special[token] for token in ("<pad>","<|im_end|>"))
    cached = {arm:torch.cat([features(model,rows[i:i+training.BATCH],pad) for i in range(0,len(rows),training.BATCH)])
              for arm,rows in fixtures.items()}

    def summarize(name):
        raw = {arm:observe(head,cached[arm],rows,tok,end) for arm,rows in fixtures.items()}
        counts = {}
        for arm,output in raw.items():
            langs = {}
            for lang in ("en","ko"):
                pairs = [(a,b) for a,b in zip(output[::2],output[1::2],strict=True) if a["language"]==lang]
                langs[lang] = dict(both=sum(a["correct"] and b["correct"] for a,b in pairs),
                                   changed=sum(a["slot"]!=b["slot"] for a,b in pairs),
                                   individual=sum(r["correct"] for p in pairs for r in p))
            counts[arm] = langs
        trial.publish(OUT/f"{name}.json",dict(counts=counts,rows=raw))
        print(json.dumps(dict(stage=name,counts=counts)),flush=True)
        return counts

    before = summarize("before_training")
    optimizer = torch.optim.AdamW(head.parameters(),lr=head_baseline.LR,weight_decay=.01,fused=True)
    loc = torch.arange(5,device="cuda").expand(training.BATCH,-1)
    train_start = perf_counter()
    running = torch.zeros((),device="cuda")
    history = []
    for step,offset in enumerate(range(0,len(samples),training.BATCH),1):
        rows = samples[offset:offset+training.BATCH]
        x = features(model,rows,pad)
        y = torch.tensor([r["target"] for r in rows],device="cuda")
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(head(x,loc),y)
        loss.backward()
        optimizer.step()
        running += loss.detach()
        if step%48==0:
            item = dict(step=step,mean_ce=running.item()/48)
            print(json.dumps(item),flush=True)
            history.append(item)
            running.zero_()
    train_seconds = perf_counter()-train_start
    after = summarize("after_training")
    if trial.state_sha(model.state_dict())!=fingerprint:
        raise ValueError("the frozen body changed")
    artifact = OUT/"selector.pt"
    with artifact.open("xb") as stream:
        torch.save(dict(train_head={k:v.detach().cpu() for k,v in head.state_dict().items()},tag=TAG,body_state_sha256=fingerprint),stream)
    trial.publish(OUT/"report.json",dict(plan=plan,before=before,after=after,history=history,training_seconds=train_seconds,
                  head_checkpoint_sha256=trial.file_sha(artifact),peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    plan,_=prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the sealed separate view settings and authorized cutoff")
    return wide.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=180)


if __name__=="__main__":
    sys.exit(main())
