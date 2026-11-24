"""Compare content-only title and question pooling on the archived table routing requests."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys

import torch
import torch.nn.functional as F

from scripts import train_p077_grounded_semantic_router as router


TAG = "p077_grounded_content_pooling_gpu_v1_20261121"
OUT = router.OUT.with_name(TAG)
trial,named,separate = router.trial,router.named,router.separate
foundation = router.foundation
PREFIX = named.HEADER + " "


def views(row):
    question = router.QUESTION.search(row["text"])
    tables = list(router.TABLE.finditer(row["text"]))
    if question is None or len(tables)!=2:
        raise ValueError("the archived request lost its two titles or question")
    return (question[1],tables[0][1],tables[1][1])


def content(tok,text):
    encoded = tok.encode(PREFIX+text+named.TAIL)
    lo,hi = len(PREFIX),len(PREFIX)+len(text)
    sites = tuple(i for i,(a,b) in enumerate(encoded.offsets) if a<hi and b>lo and a<b)
    if not sites or len(encoded.ids)-1 in sites or encoded.ids!=router.encode_text(tok,text):
        raise ValueError("content pooling must keep the archived tokens and omit the ChatML suffix")
    return tuple(encoded.ids),sites


def prepare():
    root = router.OUT/"report.json"
    origin = trial.read_json(root)
    end = trial.read_json(router.OUT/"supervisor.json")
    tok,special,_,_,_ = trial.load_cases()
    rows = origin["requests"]
    if end["returncode"] or end["stop_reason"] or router.authored.digest(rows)!=origin["plan"]["test_sha256"]:
        raise ValueError("requires the exact completed held-out requests")
    input_views = [views(row) for row in rows]
    sequences = {view:content(tok,view) for item in input_views for view in item}
    body = foundation.OUT/"foundation.pt"
    plan = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),baseline_sha256=trial.file_sha(root),
                test_sha256=origin["plan"]["test_sha256"],body_sha256=origin["plan"]["body_sha256"],
                body_file_sha256=trial.file_sha(body),input_sha256=router.authored.digest(sequences),rows=len(rows))
    return plan,(special,origin,input_views,sequences)


@torch.no_grad()
def features(model,seqs,pad):
    result = {"last_content":{},"mean_content":{}}
    ready = sorted(seqs)
    with torch.autocast("cuda",dtype=torch.bfloat16):
        for start in range(0,len(ready),8):
            names = ready[start:start+8]
            batch = [seqs[name] for name in names]
            width = max(len(ids) for ids,_ in batch)
            x = torch.tensor([ids+(pad,)*(width-len(ids)) for ids,_ in batch],device="cuda")
            hidden = model(x,return_hidden=True)
            for j,(name,(_,sites)) in enumerate(zip(names,batch,strict=True)):
                result["last_content"][name] = hidden[j,sites[-1]].float()
                result["mean_content"][name] = hidden[j,list(sites)].float().mean(dim=0)
    return result


def summaries(requests,selected,oracle):
    counts = {}
    for family in ("new_phrases","new_categories"):
        counts[family] = {}
        for language in ("ko","en"):
            rows = [(row,index,upper) for row,index,upper in zip(requests,selected,oracle,strict=True)
                    if row["family"]==family and row["language"]==language]
            groups = [rows[i:i+4] for i in range(0,len(rows),4)]
            if not all(len(g)==4 and len({r["root"] for r,_,_ in g})==1 and
                       len({(tuple(r["order"]),r["side"]) for r,_,_ in g})==4 for g in groups):
                raise ValueError("the four variations no longer form the archived groups")
            ok = [r["target"]==pred for r,pred,_ in rows]
            counts[family][language] = dict(
                route_correct=sum(ok),
                route_all_four=sum(all(ok[j:j+4]) for j in range(0,len(ok),4)),
                answer_correct=sum(route and upper["correct"] for route,(_,_,upper) in zip(ok,rows,strict=True)),
            )
    return counts


def worker(plan,fraction):
    torch.set_num_threads(1)
    checked,(special,origin,input_views,sequences) = prepare()
    if checked!=plan:
        raise ValueError("the sealed content comparison changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    data = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(data["model"])!=plan["body_sha256"]:
        raise ValueError("wrong model for the content comparison")
    config = replace(separate.wide.TMTConfig(**data["config"]),max_seq_len=trial.WIDTH)
    model = separate.wide.TiedMLPTransformer(config).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(data["model"])
    model.freeze_quant()
    table = features(model,sequences,special["<pad>"])
    predictions = {"chatml_final":[r["selected"] for r in origin["predictions"]["cosine"]]}
    for arm,bank in table.items():
        x = torch.stack([torch.stack([bank[text] for text in item]) for item in input_views])
        predictions[arm] = F.cosine_similarity(x[:,1:],x[:,:1],dim=-1).argmax(-1).tolist()
    counts = {arm:summaries(origin["requests"],selected,origin["predictions"]["oracle"])
              for arm,selected in predictions.items()}
    trial.publish(OUT/"report.json",dict(plan=plan,counts=counts,predictions=predictions,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
    print(json.dumps(counts),flush=True)


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
        parser.error("requires sealed content inputs and the authorized cutoff")
    return separate.wide.owner.supervise(worker,(plan,),OUT,args.stop_by,
                                         authorization_end=named.AUTHORIZATION_END,min_seconds=180)


if __name__ == "__main__":
    sys.exit(main())
