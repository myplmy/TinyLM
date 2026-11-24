"""Use the learned table selector to read a distant observed value."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys

import torch

from scripts import diag_p077_grounded_length_controls as controls


wide = controls.wide
trial = wide.trial
foundation = wide.foundation
TAG = "p077_grounded_value_readout_gpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)
LIMIT = 2048


def observation(tok, prompt):
    text = tok.decode(prompt,skip_special_tokens=False)
    encoding = tok.encode(text)
    values = list(foundation.VALUE.finditer(text))
    if encoding.ids!=prompt or len(values)!=4 or len({match[1] for match in values})!=4:
        raise ValueError("the observed table must contain four different values")
    final_digits = [match.end(1)-1 for match in values]
    sites = [next(i for i,(lo,hi) in enumerate(encoding.offsets) if lo<=digit<hi) for digit in final_digits]
    return sites,[match[1] for match in values]


def prepare():
    base = wide.grounded.prepare()
    _, (tok,special,_,frozen) = controls.prepare()
    source_paths = [foundation.OUT/file for file in ("wide_eval.json","question_switch_eval.json")]
    fixtures = {}
    for task,path in zip(("value","question"),source_paths,strict=True):
        archive = trial.read_json(path)
        if len(archive["rows"])!=64:
            raise ValueError("expected the independent table and question exchanges")
        for kind in ("repeat","diverse"):
            samples = []
            for row in archive["rows"]:
                for side,short in enumerate(row["prompts"]):
                    index = row["other"] if task=="question" and side==1 else row["field"]
                    head,table,query = wide.parts(tok,dict(row,field=index),side)
                    sites,values = observation(tok,short)
                    if sites!=row["slots"][side][1:5] or row["gold"][side] not in values:
                        raise ValueError("observed sites differ from the archived table parse")
                    distance = LIMIT-trial.GENERATION+1-len(short)
                    corpus = {"ko":"kobest_copa","en":"winogrande"}[row["language"]]
                    filler = (wide.choices.filler_tokens(tok,corpus,distance) if kind=="repeat" else
                              controls.diverse_filler(tok,row["language"],distance))
                    prompt = head+table+filler+query
                    if not all(point < len(head)+len(table) for point in sites):
                        raise ValueError("only actual observed table positions can be candidates")
                    samples.append(dict(root=row["root"],side=side,language=row["language"],prompt=prompt,
                                        positions=[len(prompt)-1,*sites],values=values,expected=row["gold"][side]))
            if task=="value":
                prior = "2048_far_interpolated" if kind=="repeat" else "2048_far_diverse"
                if [row["prompt"] for row in samples]!=frozen[prior]:
                    raise ValueError("the archived output is for different inputs")
            fixtures[f"{task}_{kind}"] = samples
    records = [Path(__file__),Path(wide.__file__),Path(controls.__file__),*source_paths,
               wide.OUT/"2048_far.json",controls.OUT/"2048_far_diverse.json"]
    plan = dict(tag=TAG,base=base,sources={str(p.relative_to(trial.ROOT)):trial.file_sha(p) for p in records},
                arms=list(fixtures),fixture_sha256=foundation.data.authored.digest(fixtures))
    return plan,(tok,special,fixtures)


@torch.inference_mode()
def readout(model, selector, tok, end, records):
    answers = []
    for start in range(0,len(records),wide.BATCH):
        rows = records[start:start+wide.BATCH]
        tokens = torch.tensor([row["prompt"] for row in rows],device="cuda")
        sites = torch.tensor([row["positions"] for row in rows],device="cuda")
        with torch.autocast("cuda",dtype=torch.bfloat16):
            hidden = model(tokens,return_hidden=True)
            probability = selector(hidden,sites).float().softmax(dim=-1)
        for row, distribution in zip(rows,probability.tolist(),strict=True):
            idx = max(range(len(distribution)),key=distribution.__getitem__)
            value = row["values"][idx]
            answers.append(dict(answer=value,ids=[*tok.encode(value,add_special_tokens=False).ids,end],
                                choice=idx,probability=distribution,correct=value==row["expected"]))
    return answers


def worker(plan, fraction):
    torch.set_num_threads(1)
    verified,(tok,special,fixtures) = prepare()
    if verified!=plan:
        raise ValueError("the readout data changed after preflight")
    torch.cuda.set_per_process_memory_fraction(fraction)
    base = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(base["model"])!=plan["base"]["state_sha256"]:
        raise ValueError("the original model does not match its state receipt")
    cfg = replace(wide.TMTConfig(**base["config"]),max_seq_len=LIMIT)
    model = wide.TiedMLPTransformer(cfg).to("cuda").eval()
    model.load_state_dict(base["model"])
    head = foundation.ValueLink(cfg.dim).to("cuda").eval()
    head.load_state_dict(base["train_head"])
    totals = {}
    end = special["<|im_end|>"]
    for arm,records in fixtures.items():
        answers = readout(model,head,tok,end,records)
        if arm.startswith("question"):
            defaults = [answer for start in range(0,len(records),wide.BATCH)
                        for answer in wide.cached(model,tok,special,[r["prompt"] for r in records[start:start+wide.BATCH]])]
        else:
            saved = (wide.OUT/"2048_far.json" if arm.endswith("repeat") else controls.OUT/"2048_far_diverse.json")
            defaults = [answer for row in trial.read_json(saved)["rows"] for answer in row["answers"]]
        verified_rows = []
        for item,selected,default in zip(records,answers,defaults,strict=True):
            verified_rows.append(dict(root=item["root"],side=item["side"],language=item["language"],gold=item["expected"],
                                      selected=selected,normal=default,normal_exact=default["eot"] and default["answer"]==item["expected"]))
        counts = {}
        for lang in ("ko","en"):
            pairs = [(a,b) for a,b in zip(verified_rows[::2],verified_rows[1::2],strict=True) if a["language"]==lang]
            counts[lang] = dict(pairs=len(pairs), selected=sum(a["selected"]["correct"] and b["selected"]["correct"] for a,b in pairs),
                                normal=sum(a["normal_exact"] and b["normal_exact"] for a,b in pairs),
                                individual=sum(r["selected"]["correct"] for pair in pairs for r in pair))
        trial.publish(OUT/f"{arm}.json",dict(rows=verified_rows,counts=counts))
        totals[arm] = counts
        print(json.dumps(dict(arm=arm,counts=counts)),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,counts=totals,peak_mib=torch.cuda.max_memory_allocated()/2**20))


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
    if args.receipt is None or trial.read_json(args.receipt)!=plan or args.stop_by is None:
        parser.error("requires a sealed readout experiment and authorized cutoff")
    return wide.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=120)


if __name__=="__main__":
    sys.exit(main())
