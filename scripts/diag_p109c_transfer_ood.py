"""Compare the two bilingual-trained bodies on previously unseen wordings and values."""

import argparse
from datetime import datetime
import json
from pathlib import Path

import torch

from scripts import run_p109c_bilingual_value_transfer as paired
from scripts import train_p109c_selected_value_readout as readout
from tinylm.config import TMTConfig


TAG = "p109c_transfer_ood_gpu_v1_20261121"
OUT = paired.OUT.with_name(TAG)
trial,data,baseline = paired.trial,paired.data,paired.baseline


def prepare():
    reference=readout.OUT/"report.json"
    old,ref_end=(trial.read_json(p) for p in (reference,readout.OUT/"supervisor.json"))
    source=paired.OUT/"report.json"
    training,end=(trial.read_json(p) for p in (source,paired.OUT/"supervisor.json"))
    if ref_end["returncode"] or ref_end["stop_reason"] or end["returncode"] or end["stop_reason"]:
        raise ValueError("requires the completed source queries and both trained arms")
    cases={}
    for name,rows in old["answers"].items():
        grouped={}
        for row in rows:
            if row["target"] is not None:
                grouped.setdefault(row["root"],[]).append(row)
        matching=[]
        for root,(first,second) in grouped.items():
            if (first["kind"],second["kind"]) != ("single","swapped"):
                raise ValueError("each numeric source must be a value exchange pair")
            options=(first,second)
            matching.append(dict(root=root,language=first["language"],
                                 prompts=[r["ids"] for r in options],gold=[r["target"] for r in options],
                                 slots=[[*r["sites"],r["values"].index(r["target"])] for r in options]))
        if len(matching)!=32:
            raise ValueError("the unseen wording group must have 32 matched pairs")
        cases[name]=matching
    if set(cases)!={"test_known_range","test_new_range"}:
        raise ValueError("expected both held-out numeric ranges")
    for arm,proof in training["arms"].items():
        if trial.file_sha(paired.OUT/arm/"foundation.pt")!=proof["checkpoint"]:
            raise ValueError("a completed arm changed")
    tok,special,_,_,_=trial.load_cases()
    return dict(tag=TAG,source=trial.file_sha(Path(__file__)),training=trial.file_sha(source),
                reference=trial.file_sha(reference),requests=data.authored.digest(cases),
                counts={k:len(v)*2 for k,v in cases.items()}),(tok,special,cases,training)


def evaluate(plan,fraction):
    checked,(tok,special,cases,training)=prepare()
    if checked!=plan:
        raise ValueError("the unseen request or paired models changed")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    results={}
    for arm in paired.ARMS:
        saved=torch.load(paired.OUT/arm/"foundation.pt",weights_only=True,map_location="cpu")
        if trial.state_sha(saved["model"])!=training["arms"][arm]["state"]:
            raise ValueError("incorrect trained model state")
        model=baseline.TiedMLPTransformer(TMTConfig(**saved["config"])).to("cuda").eval()
        model.load_state_dict(saved["model"])
        selector=baseline.ValueLink(model.cfg.dim).to("cuda").eval()
        selector.load_state_dict(saved["train_head"])
        arms={}
        for name,rows in cases.items():
            generated=data.evaluate(model,tok,special,rows,paired=True)
            slots=baseline.evaluate_slots(model,selector,rows,special["<pad>"])
            arms[name]=dict(joint=generated["both_correct"],by_language=generated["by_language"],
                            individual=sum(out["answer"]==gold and out["eot"] for row in generated["rows"]
                                           for out,gold in zip(row["outputs"],row["gold"],strict=True)),
                            selected=slots["individual"],output=generated["rows"],slot_rows=slots["rows"])
        results[arm]=arms
        del model,selector
    trial.publish(OUT/"report.json",dict(plan=plan,results=results))
    print(json.dumps({name:{key:{k:v for k,v in value.items() if k not in ("output","slot_rows")}
                            for key,value in arms.items()} for name,arms in results.items()}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    plan,_=prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the exact sealed OOD panel")
    return baseline.owner.supervise(evaluate,(plan,),OUT,args.stop_by,
                                    authorization_end=paired.bridge.AUTHORIZATION_END,min_seconds=180)


if __name__=="__main__":
    raise SystemExit(main())
