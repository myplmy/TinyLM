"""Train a frozen-body router for two tables referred to by description."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
from random import Random
import re
import sys
from time import perf_counter

import torch
import torch.nn.functional as F

from scripts import diag_p077_grounded_two_tables as named


TAG = "p077_grounded_semantic_router_gpu_v1_20261121"
OUT = named.OUT.with_name(TAG)
trial = named.trial
foundation = named.foundation
separate = named.separate
authored = named.authored
STEPS, BATCH = 192, 8
TABLE = re.compile(r"\[table\]\n([^\n]+)\n([^\n]+)\n\[/table\]")
QUESTION = re.compile(r"\[question\]\n([^\n]+)\n([^\n]+)$")

# Each row gives two training titles, two training descriptions, and one held-out pair.
LEXICON = {
    "ko": (
        (("출고 부서", "물류 발송반"), ("물건을 외부에 보내는 팀", "배송을 맡는 쪽"), ("배송 처리 기록", "꾸러미를 내보내는 곳")),
        (("반품 담당", "회수반"), ("돌려보낸 물품을 받는 팀", "회수 업무를 맡는 쪽"), ("반환 접수 기록", "되가져온 물건을 처리하는 곳")),
        (("재고 창고", "보관 담당"), ("물건을 쌓아 두는 팀", "창고를 관리하는 쪽"), ("재고 정리 기록", "물품을 간직하는 곳")),
        (("정비 작업반", "장비 수선팀"), ("고장 난 물건을 고치는 팀", "정비를 맡는 쪽"), ("수리실 기록", "망가진 기기를 바로잡는 곳")),
        ((), (), ("급여 계산부 기록", "직원의 월급을 정산하는 곳")),
        ((), (), ("구매 조달부 기록", "필요한 장비를 사들이는 곳")),
    ),
    "en": (
        (("outbound dispatch office", "shipping desk"), ("the team that sends packages out", "the group responsible for deliveries"), ("delivery operations record", "the office moving parcels to customers")),
        (("return intake desk", "returns department"), ("the team that receives returned goods", "the group responsible for recovery"), ("refund intake record", "the office taking goods customers send back")),
        (("inventory warehouse", "storage group"), ("the team that keeps goods in stock", "the group responsible for the warehouse"), ("storehouse record", "the office putting materials aside for later")),
        (("equipment maintenance office", "repair workshop"), ("the team that fixes broken machines", "the group responsible for maintenance"), ("servicing record", "the office getting damaged devices working again")),
        ((), (), ("payroll calculation record", "the office issuing employee pay")),
        ((), (), ("purchase procurement record", "the office acquiring new equipment")),
    ),
}


def encode_text(tok, text):
    return tok.encode(named.HEADER + " " + text + named.TAIL).ids


def parse_request(tok, text):
    tables = list(TABLE.finditer(text))
    question = QUESTION.search(text)
    if question is None or len(tables)!=2 or tables[1].end()>=question.start():
        raise ValueError("expected two unlabeled source tables and one description question")
    titles = [encode_text(tok, row[1]) for row in tables]
    field = encode_text(tok, question[2])
    spans = []
    for row in tables:
        ids = tok.encode(named.HEADER + row[2]).ids
        positions,values = separate.previous.observation(tok,ids)
        spans.append(dict(table=ids,query=field,positions=positions,values=values))
    return [encode_text(tok,question[1]), *titles],spans


def training(tok):
    rng = Random(78813)
    result = []
    for i in range(STEPS*BATCH):
        lang = "ko" if i%2==0 else "en"
        target = (i//2)%4
        other = rng.choice([j for j in range(4) if j!=target])
        order = (target,other) if (i//2+i//8)%2==0 else (other,target)
        title = [rng.choice(LEXICON[lang][category][0]) for category in order]
        question = rng.choice(LEXICON[lang][target][1])
        result.append(dict(route=[encode_text(tok,x) for x in (question,*title)], target=order.index(target)))
    return result


def fixtures(tok, used):
    rng = Random(602355)
    cases,raw = [],[]
    for family in ("new_phrases", "new_categories"):
        for group in range(48):
            lang = "ko" if group%2==0 else "en"
            field = (group//2)%4
            pair = tuple(rng.sample(range(4),2)) if family=="new_phrases" else (4,5)
            while True:
                values = rng.sample(range(1000,9999),8)
                keys = [tuple(sorted(values[i:i+4])) for i in (0,4)]
                if used.isdisjoint(keys):
                    used.update(keys)
                    break
            tables = [authored.values_text(lang, values[i:i+4],rng.sample(range(4),4)) for i in (0,4)]
            descriptions = [LEXICON[lang][category][2] for category in pair]
            blocks = [f"[table]\n{title}\n{text}\n[/table]" for (title,_),text in zip(descriptions,tables,strict=True)]
            filler = named.FILLER[lang]
            gap = filler*(860//len(tok.encode(filler).ids))
            ask = authored.field_question(lang,field,(group//8)%3)
            root = authored.digest([family,lang,pair,values,tables])
            for order in ((0,1),(1,0)):
                for requested in (0,1):
                    description = descriptions[requested][1]
                    text = f"{blocks[order[0]]}\n{gap}\n{blocks[order[1]]}\n{gap}\n[question]\n{description}\n{ask}"
                    width = len(tok.encode(named.HEADER+text+named.TAIL).ids)
                    context,spans = parse_request(tok,text)
                    target = order.index(requested)
                    gold = str(values[requested*4+field])
                    if not 1650<=width<=2048 or gold not in spans[target]["values"] or gold in spans[1-target]["values"]:
                        raise ValueError("a semantic routing group does not have distinct answer evidence")
                    item = dict(family=family,root=root,language=lang,side=requested,order=order,target=target,gold=gold,width=width)
                    raw.append(dict(item,text=text))
                    cases.append(dict(item,route=context,spans=[dict(span,root=root,side=requested,language=lang,gold=gold)
                                                               for span in spans]))
    return cases,raw


def prepare():
    tok,special,_,_,_ = trial.load_cases()
    baseline = trial.read_json(named.OUT/"report.json")
    terminal = trial.read_json(named.OUT/"supervisor.json")
    head_sha = trial.file_sha(separate.OUT/"selector.pt")
    if terminal["returncode"] or terminal["stop_reason"] or head_sha!=baseline["plan"]["head_sha256"]:
        raise ValueError("requires the previous selection head and completed source routing")
    used,_ = separate.training.old_value_groups(tok)
    for row in baseline["inputs"]:
        for match in named.TABLE.finditer(row["text"]):
            used.add(tuple(sorted(int(v) for v in foundation.VALUE.findall(match[2]))))
    corpus,_ = separate.training_samples(tok,tok.encode(named.HEADER,add_special_tokens=False).ids)
    for row in corpus:
        used.add(tuple(sorted(int(v) for v in foundation.VALUE.findall(tok.decode(row["table"])))))
    fit = training(tok)
    check,raw = fixtures(tok,used)
    family = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),selector_sha256=head_sha,
                  body_sha256=baseline["plan"]["body_state_sha256"],fit_sha256=authored.digest(fit),
                  test_sha256=authored.digest(raw),runtime_input_sha256=authored.digest(check),
                  updates=STEPS,request_count=len(check),width_min=min(r["width"] for r in raw),
                  width_max=max(r["width"] for r in raw))
    return family,(tok,special,fit,check,raw)


@torch.no_grad()
def route_features(model, datasets, pad):
    sequences = {tuple(view) for rows in datasets for row in rows for view in row["route"]}
    features = {}
    with torch.autocast("cuda",dtype=torch.bfloat16):
        seqs = sorted(sequences)
        for start in range(0,len(seqs),BATCH):
            batch = seqs[start:start+BATCH]
            width = max(map(len,batch))
            tokens = torch.tensor([row+(pad,)*(width-len(row)) for row in batch],device="cuda")
            ends = torch.tensor([len(row)-1 for row in batch],device="cuda")
            states = model(tokens,return_hidden=True)[torch.arange(len(batch),device="cuda"),ends].float()
            features.update(zip(batch,states,strict=True))
    return [torch.stack([torch.stack([features[tuple(view)] for view in row["route"]]) for row in dataset])
            for dataset in datasets]


def worker(plan,fraction):
    torch.set_num_threads(1)
    torch.manual_seed(18761)
    checked,(tok,special,training,tests,raw) = prepare()
    if checked!=plan:
        raise ValueError("semantic examples changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    saved = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    body = saved["model"]
    initial = torch.load(separate.OUT/"selector.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(body)!=plan["body_sha256"] or initial["body_state_sha256"]!=plan["body_sha256"]:
        raise ValueError("the router and answer head need the same frozen body")
    config = replace(separate.wide.TMTConfig(**saved["config"]),max_seq_len=trial.WIDTH)
    model = separate.wide.TiedMLPTransformer(config).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(body)
    model.freeze_quant()
    answer = foundation.ValueLink(config.dim).to("cuda").eval()
    answer.load_state_dict(initial["train_head"])
    head = foundation.ValueLink(config.dim).to("cuda")
    pad,end = (special[key] for key in ("<pad>","<|im_end|>"))
    fit,test = route_features(model,(training,tests),pad)
    y = torch.tensor([row["target"] for row in training],device="cuda")
    sites = torch.arange(3,device="cuda").expand(BATCH,-1)
    optim = torch.optim.AdamW(head.parameters(),lr=.002,weight_decay=.01,fused=True)
    begin = perf_counter()
    for i in range(0,len(training),BATCH):
        logits = head(fit[i:i+BATCH],sites)
        optim.zero_grad(set_to_none=True)
        F.cross_entropy(logits,y[i:i+BATCH]).backward()
        optim.step()
    torch.cuda.synchronize()
    elapsed = perf_counter()-begin
    with torch.no_grad():
        head_scores = head(test,torch.arange(3,device="cuda").expand(len(tests),-1))
        cosine = F.cosine_similarity(test[:,1:],test[:,:1],dim=-1).argmax(-1).tolist()
        learned = head_scores.argmax(-1).tolist()
    by_method = {name:[] for name in ("first","cosine","learned","oracle")}
    for start in range(0,len(tests),4):
        subset = tests[start:start+4]
        spans = [span for row in subset for span in row["spans"]]
        outputs = separate.observe(answer,separate.features(model,spans,pad),spans,tok,end)
        for i,row in enumerate(subset):
            options = {"first":0,"cosine":cosine[start+i],"learned":learned[start+i],"oracle":row["target"]}
            for name,selected in options.items():
                prediction = outputs[2*i+selected]
                by_method[name].append(dict(value=prediction["selected"],correct=prediction["correct"],
                                           selected=selected,route_ok=selected==row["target"]))
    counts = {}
    for name,predictions in by_method.items():
        counts[name] = {}
        for cohort in ("new_phrases","new_categories"):
            subset = [p for p,row in zip(predictions,tests,strict=True) if row["family"]==cohort]
            groups = [subset[i:i+4] for i in range(0,len(subset),4)]
            counts[name][cohort] = dict(route=sum(p["route_ok"] for p in subset),answer=sum(p["correct"] for p in subset),
                                        all_four=sum(all(p["correct"] for p in group) for group in groups))
    if trial.state_sha(model.state_dict())!=plan["body_sha256"]:
        raise ValueError("the frozen model changed during router training")
    artifact = OUT/"router.pt"
    with artifact.open("xb") as sink:
        torch.save(dict(state={k:v.detach().cpu() for k,v in head.state_dict().items()},body_sha256=plan["body_sha256"]),sink)
    trial.publish(OUT/"report.json",dict(plan=plan,counts=counts,predictions=by_method,requests=raw,
                  router_sha256=trial.file_sha(artifact),seconds=elapsed,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
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
        parser.error("requires sealed semantic routing inputs and the authorized cutoff")
    return separate.wide.owner.supervise(worker,(plan,),OUT,args.stop_by,
                                         authorization_end=named.AUTHORIZATION_END,min_seconds=180)


if __name__=="__main__":
    sys.exit(main())
