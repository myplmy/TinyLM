"""Compare identical initial G4 trits with different latent margins on written inputs."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import random
import re
from statistics import median
import subprocess
from time import perf_counter
import unicodedata

from tokenizers import Tokenizer
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_edit_retention as prior
from scripts import diag_p109_qwen_248k_warm_ce as audit
from tinylm.infer.generate import sample


TAG = "p108_g4_master_margin_authored_v1_20261119"
OUT = prior.OUT.with_name(TAG)
PROFILE = OUT/"profile.json"
DATA = OUT/"data.pt"
SOURCE = prior.OUT/"profile.json"
SELECTION = prior.OUT/"selection.json"
STEPS, BATCH, WIDTH, SEED = 176, 2, 96, 1362026
WATCH = 64
AT = (1,32,88,STEPS)
ARMS = ("base","flip","margin")


def verify(profile):
    assert all(prior.sha(prior.ROOT/p)==h for p,h in profile["pins"].items())
    assert prior.sha(prior.PARENT)==prior.frozen.PARENT_SHA
    assert prior.sha(DATA)==profile["data_sha256"]


def prepare():
    tok = Tokenizer.from_file(str(prior.frozen.TOKENIZER))
    assert tok.get_vocab_size()==32768 and tok.token_to_id("<eos>")==2
    source = prior.read(SOURCE)
    words = prior.read(audit.qwen.AUTHORED)["data"]["documents"]
    assert len(words)==816 and len({d["id"] for d in words})==816
    assert all(name.casefold() not in d["text"].casefold() for name,*_ in prior.FACTS for d in words)
    train = [[i for i,d in enumerate(words) if d["split"]=="train" and d["language"]==lang] for lang in ("en","ko")]
    held = torch.tensor([[i for i,d in enumerate(words) if d["split"]=="held" and d["language"]==lang]
                         for lang in ("en","ko")])
    assert [len(s) for s in train]==[384,384] and held.shape==(2,24)
    inputs = torch.full((len(words),WIDTH),2,dtype=torch.long)
    labels = torch.full_like(inputs,-100)
    for i,encoding in enumerate(tok.encode_batch([d["text"] for d in words],add_special_tokens=False)):
        ids = encoding.ids
        assert 1<len(ids)<=WIDTH and 2 not in ids
        inputs[i,:len(ids)] = torch.tensor(ids)
        labels[i,:len(ids)] = torch.tensor([*ids[1:],2])
    rng = random.Random(SEED)
    draws = torch.tensor(list(zip(*(rng.sample(s,STEPS) for s in train),strict=True)))
    assert draws.shape==(STEPS,BATCH) and len(draws.unique())==draws.numel()
    count = labels[draws].ne(-100).sum((0,2)).tolist()
    pool = int(labels[sum(train,[])].ne(-100).sum())
    assert pool>=2*sum(count)

    questions = source["questions"]
    tokens = [torch.tensor(r["ids"]) for r in questions]
    panel = (torch.nn.utils.rnn.pad_sequence(tokens,batch_first=True,padding_value=tok.token_to_id("<pad>")),
             torch.tensor([len(t)-1 for t in tokens]),torch.tensor([r["correct"] for r in questions]),
             torch.tensor(source["options"]))
    assert len(questions)==36
    prompts = []
    for name,en,ko,correct in prior.FACTS:
        prompts.append(dict(lang="en",fact=name,expected=en[correct],
                            prompt=f"Inventory item for {name}. Give only the item name.\nAnswer:"))
        prompts.append(dict(lang="ko",fact=name,expected=ko[correct],
                            prompt=f"{name}의 물품 이름만 답하세요.\n정답:"))
    paths = [Path(__file__),SOURCE,SELECTION,audit.qwen.AUTHORED,prior.frozen.TOKENIZER,
             *(prior.ROOT/n for n in prior.SOURCES),prior.ROOT/"tinylm/infer/generate.py"]
    pins = {str(p.relative_to(prior.ROOT)):prior.sha(p) for p in paths}
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    with DATA.open("xb") as output:
        torch.save(dict(x=inputs,y=labels,draws=draws,held=held,panel=panel),output)
    profile = dict(tag=TAG,approval="WIP176",pins=pins,pool=pool,train_documents=draws.numel(),targets=count,
                   held_targets=labels[held].ne(-100).sum((1,2)).tolist(), steps=STEPS, seeded=SEED,
                   open_prompts=prompts,data_sha256=prior.sha(DATA))
    prior.write(PROFILE,profile)
    verify(profile)
    print("P108_MARGIN_CPU",pool,count,profile["held_targets"],flush=True)


@torch.no_grad()
def swaps(model,down,edited):
    group = model.cfg.micro_group
    w = down.weight.reshape(-1,group)
    effective = prior.ternary(down.weight,model.cfg).reshape_as(w)
    covered = torch.zeros_like(w,dtype=torch.bool)
    covered.flatten()[edited] = True
    swaps = []
    for idx in edited.tolist():
        g,c = divmod(idx,group)
        row = w[g]
        candidates = torch.where(effective[g].ne(0)&~covered[g]&(row.abs()>row[c].abs()))[0]
        if not len(candidates):
            continue
        donors = candidates[row[candidates].abs().argsort(descending=True,stable=True)]
        choices = row.expand(len(donors),-1).clone()
        choices[:,c] = row[c].sign()*row[donors].abs()
        choices[torch.arange(len(donors),device=w.device),donors] = row[donors].sign()*row[c].abs()
        exact = torch.where(prior.ternary(choices,model.cfg).eq(effective[g]).all(1))[0]
        if len(exact):
            k = int(exact[0])
            d = int(donors[k])
            w[g].copy_(choices[k])
            covered[g,d] = True
            swaps.append((idx,g*group+d))
    assert torch.equal(prior.ternary(down.weight,model.cfg).reshape_as(w),effective)
    return swaps


@torch.no_grad()
def apply_swaps(down,pairs):
    for target,donor in pairs:
        t,d = down.weight.flatten()[[target,donor]].clone().unbind()
        down.weight.flatten()[target] = t.sign()*d.abs()
        down.weight.flatten()[donor] = d.sign()*t.abs()


def logits(model,x,y,amp):
    valid = y>=0
    with torch.autocast("cuda",dtype=torch.bfloat16,enabled=amp):
        h = model(x,return_hidden=True)
        scores = model._head_logits(h[valid])
    return scores.float(),y[valid]


@torch.no_grad()
def inspect(model,data,tok,profile,full):
    model.eval()
    model.freeze_quant()
    try:
        forced = prior.evaluate(model,data["panel"])
        held = {}
        for lang,rows in zip(("en","ko"),data["held"],strict=True):
            total = count = hits = 0
            for ids in rows.split(4):
                scores,y = logits(model,data["x"][ids],data["y"][ids],False)
                total += float(F.cross_entropy(scores,y,reduction="sum"))
                count += len(y)
                hits += int(scores.argmax(1).eq(y).sum())
            held[lang] = dict(targets=count,nll=total/count,correct=hits)
        answers = []
        if full:
            for prompt in profile["open_prompts"]:
                prefix = tok.decode(tok.encode(prompt["prompt"]).ids)
                text,meta = sample(model,model.cfg,tok,prompt["prompt"],max_new=8,temperature=0.,top_k=0,
                                   device="cuda",logits_last_only=True,return_metadata=True)
                assert text.startswith(prefix)
                result = text[len(prefix):]
                norm = unicodedata.normalize("NFC",result.casefold()).lstrip(" \t\r\n\"'(`")
                label = re.escape(unicodedata.normalize("NFC",prompt["expected"].casefold()))
                pattern = r"(?:(?:a|an|the) )?"+label+r"\b" if prompt["lang"]=="en" else label
                answers.append(dict(**prompt,answer=result,correct=bool(re.match(pattern,norm)),finish=meta["finish_reason"]))
        return dict(choices=forced,held=held,open_answers=answers)
    finally:
        model.clear_quant()


def train(arm,data,profile,tok,idx,original,pairs):
    model,down = prior.load_model()
    assert torch.equal(prior.read_edit(model,down,idx)[1],original)
    installed = prior.install(model,down,idx,0 if arm=="base" else WATCH)
    q = prior.ternary(down.weight.detach(),model.cfg)
    if arm=="margin":
        apply_swaps(down,pairs)
        assert torch.equal(prior.ternary(down.weight.detach(),model.cfg),q)
    effective = prior.state_sha(q)
    del q
    donors = torch.tensor([d for _,d in pairs],device=idx.device)
    donor_sign = prior.read_edit(model,down,donors)[1]
    sign = -original
    current,start_trit,margin = prior.read_edit(model,down,idx)
    uninterrupted = start_trit.eq(sign)
    receipt = {"0":inspect(model,data,tok,profile,True)}
    if arm=="margin":
        assert receipt["0"]==prior.read(OUT/"flip.json")["checks"]["0"]
    route = prior.build_experimental_optimizers(model,"muon_matched",lr=prior.LR,matrix_lr_mult=1.)
    optimizers = (route.matrix,route.adamw)
    prior.keep_active_groups(optimizers)
    rates = [[g["lr"] for g in opt.param_groups] for opt in optimizers]
    path = 0.
    movement = []
    torch.cuda.reset_peak_memory_stats()
    for step,rows in enumerate(data["draws"],1):
        free,total = torch.cuda.mem_get_info()
        if total-free>13_000_000_000 or (OUT/"STOP").exists() or datetime.now(prior.CUTOFF.tzinfo)>=prior.CUTOFF:
            raise RuntimeError(f"execution bound before {arm} update {step}")
        start = perf_counter()
        model.train()
        factor = prior.lr_factor(step-1,4,STEPS,"cosine")
        for opt,values in zip(optimizers,rates,strict=True):
            for g,lr in zip(opt.param_groups,values,strict=True):
                g["lr"] = lr*factor
        scores,y = logits(model,data["x"][rows],data["y"][rows],True)
        loss = F.cross_entropy(scores,y)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        after,trits,_ = prior.read_edit(model,down,idx)
        donor_trit = prior.read_edit(model,down,donors)[1]
        uninterrupted &= trits.eq(sign)
        path += float((after-current).norm())
        current = after
        torch.cuda.synchronize()
        movement.append(dict(step=step,match=int(trits.eq(sign).sum()),uninterrupted=int(uninterrupted.sum()),
                             donor_match=int(donor_trit.eq(donor_sign).sum()),path_l2=path,targets=len(y),
                             norm=float(norm),ce=float(loss.detach()),seconds=perf_counter()-start,
                             trits=trits.tolist(),donor_trits=donor_trit.tolist()))
        del scores,loss,norm
        if step in AT:
            receipt[str(step)] = inspect(model,data,tok,profile,step==STEPS)
            print("P108_MARGIN_UPDATE",arm,step,movement[-1]["match"],movement[-1]["donor_match"],flush=True)
    assert sum(v["targets"] for v in movement)==sum(profile["targets"])
    return dict(initial=installed,effective_sha256=effective,initial_margin=margin.tolist(),initial_trits=start_trit.tolist(),
                initial_donors=donor_sign.tolist(),history=movement,checks=receipt,
                peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),
                median_seconds=median(v["seconds"] for v in movement[4:]),checkpoint_writes=0)


def run():
    assert prior.idle()
    profile = prior.read(PROFILE)
    verify(profile)
    raw = torch.load(DATA,map_location="cpu",weights_only=True)
    data = {k:tuple(x.cuda() for x in v) if k=="panel" else v.cuda() for k,v in raw.items()}
    tok = Tokenizer.from_file(str(prior.frozen.TOKENIZER))
    selection = prior.read(SELECTION)
    idx = torch.tensor(selection["indices"][:WATCH],device="cuda")
    original = torch.tensor(selection["original_signs"][:WATCH],dtype=torch.int8,device=idx.device)
    model,down = prior.load_model()
    prior.install(model,down,idx,WATCH)
    pairs = swaps(model,down,idx)
    assert pairs
    prior.write(OUT/"swaps.json",dict(source=str(SELECTION.relative_to(prior.ROOT)),pairs=pairs))
    del model,down
    torch.cuda.empty_cache()
    device = OUT/"device_100ms.csv"
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*audit.DEVICE,f"--loop-ms={audit.INTERVAL_MS}"),stdout=stream)
        results = {}
        try:
            with sdpa_kernel(SDPBackend.MATH):
                for arm in ARMS:
                    result = train(arm,data,profile,tok,idx,original,pairs)
                    prior.write(OUT/f"{arm}.json",result)
                    results[arm] = result
                    torch.cuda.empty_cache()
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    verify(profile)
    ordinary,margin = results["flip"],results["margin"]
    assert ordinary["effective_sha256"]==margin["effective_sha256"]
    assert ordinary["checks"]["0"]==margin["checks"]["0"]
    samples = audit.read_samples(device)
    assert samples
    prior.write(OUT/"report.json",dict(arms=results,swaps=len(pairs),equal_initial_responses=True,
                device_peak=max(samples,key=lambda v:v["occupied_mib"]),device_samples=len(samples),
                profile_sha256=prior.sha(PROFILE),source_preserved=True))
    print("P108_MARGIN_RESULT",len(pairs),[(a,r["history"][-1]["match"],r["history"][-1]["donor_match"])
          for a,r in results.items()],flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase=parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(prior.CUTOFF.tzinfo)+timedelta(seconds=500)<prior.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (prepare if phase=="prepare" else run)()
