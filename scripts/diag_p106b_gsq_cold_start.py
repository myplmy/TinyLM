"""Native hard-ternary training from scratch with a synthetic causal teacher."""

import argparse
import os
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as io


TAG = "p106b_gsq_ste_cold_start_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
CASES = (("ste","ce"),("gsq","ce"),("ste","ce_kd"),("gsq","ce_kd"))
VOCAB, SEQ, BATCH, UPDATES = 32768, 64, 4, 24
CAP = 390
SOURCES = (
    "scripts/diag_p106b_gsq_cold_start.py","scripts/diag_p013_native_matched_training.py",
    "scripts/p106b_gsq_objective.py","scripts/p093b_native_repair.py","tinylm/config.py",
    "tinylm/model/transformer.py","tinylm/model/ternary.py","tinylm/model/modules.py",
)


def pins():
    return {p:io.digest(io.ROOT/p) for p in SOURCES}


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"]==""
    OUT.mkdir()
    io.write(PROFILE,dict(tag=TAG, cases=CASES, sources=pins(), work="generated causal token law",
        student="m100s10/dense/R1", vocab=VOCAB, seq=SEQ, batch=BATCH, updates=UPDATES,
        target_count=BATCH*SEQ*UPDATES, eval_seed=56565, train_seed=21212,
        optimizer="AdamW same LR and clip", teacher="fixed 8-entry full-support vector per position",
        group_dropout=False, model_initialization_seed=1337,kd_weight=.3,stage_cap_seconds=CAP,
        original_model_loads=0,original_corpus_reads=0,checkpoint_writes=0,gpu_calls=0))
    print("GSQ_COLD_READY",io.digest(PROFILE),len(CASES),flush=True)


def verify():
    import json
    p=json.loads(PROFILE.read_bytes())
    assert p["sources"]==pins() and p["cases"]==[list(x) for x in CASES]
    assert p["target_count"]==BATCH*SEQ*UPDATES and p["eval_seed"]!=p["train_seed"]
    return p


def data(torch,seed):
    gen=torch.Generator().manual_seed(seed)
    x=torch.empty((BATCH,SEQ+1),dtype=torch.long)
    x[:,0]=torch.randint(40,520,(BATCH,),generator=gen)
    probability=torch.tensor([.58,.12,.08,.07,.05,.04,.03,.03],dtype=torch.float32)
    for index in range(SEQ):
        head=(x[:,index]*17+19)%480+40
        choice=torch.multinomial(probability.expand(BATCH,-1),1,generator=gen).squeeze(1)
        x[:,index+1]=(head-40+choice*7)%480+40
    return x.cuda(),probability.cuda()


def objective(torch,logits,sequence,probs,kind):
    import torch.nn.functional as F

    labels=sequence[:,1:]
    current=sequence[:,:-1]
    expected=(current*17+19)%480
    support=(expected[...,None]+7*torch.arange(8,device="cuda"))%480+40
    nll=F.log_softmax(logits.float(),dim=-1)
    ce=-nll.gather(-1,labels.unsqueeze(-1)).mean()
    soft=(-nll.gather(-1,support)*probs).sum(-1).mean()
    soft_kl=soft+(probs*probs.log()).sum()
    loss=ce+(0.3*soft_kl if kind=="ce_kd" else 0.)
    return loss,ce,soft_kl,labels


def worker(arm,kind):
    import torch
    from torch.nn.attention import SDPBackend,sdpa_kernel
    from scripts.p106b_gsq_objective import ObjectiveBridge
    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer

    p=verify()
    assert (arm,kind) in CASES and os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    entry=io.reserve_device()
    print(f"GSQ_COLD_WORKER {arm}/{kind} pid={os.getpid()}",flush=True)
    torch.set_num_threads(1)
    torch.manual_seed(p["model_initialization_seed"])
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    cfg=build_config("m100s10","dense",SEQ,True)
    assert cfg.vocab_size==VOCAB and cfg.n_layers==14
    model=TiedMLPTransformer(cfg).cuda().train()
    model.set_anneal(1.)
    bridge=ObjectiveBridge(model,arm,logit_strength=4.6)
    original=tuple((id(t),t.requires_grad) for t in bridge.masters.values())
    parameters=bridge.parameters_for_optimizer()
    optimizer=torch.optim.AdamW(parameters,lr=2e-4,weight_decay=0.,foreach=False)
    started=time.monotonic()
    held=[]
    loss_rows=[]

    def validation():
        model.eval()
        out=[]
        try:
            with torch.no_grad(),bridge.realization(p["eval_seed"],backward_expected=False):
                for i in range(4):
                    x,probs=data(torch,p["eval_seed"]+i)
                    with torch.autocast("cuda",dtype=torch.bfloat16),sdpa_kernel(SDPBackend.MATH):
                        logits=model(x[:,:-1].contiguous())
                    _,ce,kl,y=objective(torch,logits,x,probs,kind)
                    out.append(dict(ce=float(ce),kl=float(kl),
                        correct=int((logits.argmax(-1)==y).sum()),targets=y.numel()))
        finally:
            model.train()
        return out

    with bridge.installed():
        held.append(validation())
        for step in range(UPDATES):
            if (OUT/"STOP").exists() or time.monotonic()-started>CAP-40:
                raise TimeoutError("owned STOP or child compute budget")
            x,probs=data(torch,p["train_seed"]+step)
            optimizer.zero_grad(set_to_none=True)
            start=time.monotonic()
            with bridge.realization(7331+step):
                with torch.autocast("cuda",dtype=torch.bfloat16),sdpa_kernel(SDPBackend.MATH):
                    logits=model(x[:,:-1].contiguous())
                loss,ce,kl,y=objective(torch,logits,x,probs,kind)
                bridge.backward(loss)
            norm=torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True)
            optimizer.step()
            bridge.project()
            torch.cuda.synchronize()
            loss_rows.append(dict(step=step+1,loss=float(loss.detach()),ce=float(ce.detach()),teacher_kl=float(kl.detach()),
                targets=y.numel(),gradient_norm=float(norm),seconds=time.monotonic()-start))
            del logits,loss,ce,kl
            if step%6==5:
                print("GSQ_COLD_UPDATE",arm,kind,step+1,loss_rows[-1]["ce"],flush=True)
        held.append(validation())
    assert tuple((id(t),t.requires_grad) for t in bridge.masters.values())==original
    model.eval()
    torch.cuda.synchronize()
    io.write(OUT/f"{arm}_{kind}.json",dict(arm=arm,objective=kind,rows=loss_rows,validation=held,
        exact_model_parameter_count=sum(t.numel() for t in model.parameters()),
        optimizer_owned_parameter_count=sum(t.numel() for t in parameters),
        tied_quantization_inventory=bridge.inventory(),gpu_entry=entry,
        peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),
        seconds=time.monotonic()-started,profile_sha256=io.digest(PROFILE),exit=0))


def run():
    verify()
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    assert time.time()+len(CASES)*(CAP+28)+40 < io.CUTOFF
    results=[]
    for arm,kind in CASES:
        if (OUT/"STOP").exists():
            break
        io.reserve_device()
        command=["timeout","--signal=INT","--kill-after=15s",f"{CAP}s",sys.executable,"-B","-u","-m",
                 "scripts.diag_p106b_gsq_cold_start","worker",arm,kind]
        proc=subprocess.run(command,cwd=io.ROOT)
        results.append(dict(arm=arm,objective=kind,exit=proc.returncode))
        print("GSQ_COLD_TERMINAL",arm,kind,proc.returncode,flush=True)
    release=io.reserve_device()
    done=len(results)==len(CASES) and all(x["exit"]==0 for x in results)
    io.write(OUT/"terminal.json",dict(complete=done,exit=0 if done else 8,results=results,
        profile_sha256=io.digest(PROFILE),release=release,checkpoints=0))
    return 0 if done else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run","worker"))
    parser.add_argument("arm",nargs="?")
    parser.add_argument("kind",nargs="?")
    args=parser.parse_args()
    if args.action=="prepare":
        prepare()
    elif args.action=="worker":
        worker(args.arm,args.kind)
    else:
        raise SystemExit(run())
