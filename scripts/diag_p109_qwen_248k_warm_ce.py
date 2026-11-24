"""Train and pack a diagnostic 248K Qwen-tokenized student from the existing G4."""

import argparse
from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
import random
from statistics import median
import subprocess
from time import perf_counter

import numpy as np
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_compact_qwen_tokenizer as qwen
from scripts import diag_p109_warm_visit_routes as parent
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p102a_g4_joint_ce_kl_batch8 import DEVICE, INTERVAL_MS, read_samples
from scripts.p014e_packed_g128 import export_payload, load_payload, payload_storage
from scripts.p106b_alm_bytes import student_piece_bytes
from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer
from scripts.p107_active_optimizer_groups import keep_active_groups
from tinylm.model.transformer import TiedMLPTransformer
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.experimental_optimizers import build_experimental_optimizers


ROOT = qwen.ROOT
TAG = "p109_qwen_248k_warm_ce_v2_20261119"
OUT = qwen.OUT.with_name(TAG)
STUDENT_TOKENIZER = ROOT / "data_cache/tok-ko-en-32768.json"
ASSIGNED, VOCAB, EOS = 248066, 248320, 248044
UPDATES, WIDTH, BATCH, WARMUP, SEED = 88, 96, 4, 4, 24817
LR, MATRIX_MULT = 3e-5, 0.5
PROFILE = OUT / "profile.json"
MAPPING = OUT / "mapping.npz"
DATA = OUT / "tokens.npz"
EXPORT = OUT / "trained_5trit.pt"


def segments(text, source):
    pieces = []
    start = 0
    while start < len(text):
        for stop in range(len(text), start, -1):
            value = text[start:stop]
            if value in source:
                pieces.append((source[value], stop - start))
                start = stop
                break
        else:
            raise ValueError("parent ByteLevel vocabulary cannot cover a byte")
    return pieces


def prepare():
    source = qwen.load(qwen.ASSET)["assets"]["qwen35_hf"]
    source_path = ROOT / source["path"]
    profile = qwen.load(qwen.OUT / "profile.json")
    earlier = qwen.load(qwen.OUT / "report.json")
    assert not earlier["mismatches"] and earlier["full_vocabulary_match"]
    assert source["physical_rows"] == VOCAB and source["id_count"] == ASSIGNED
    assert source["file_sha256"] == qwen.digest(source_path) == profile["original_sha256"]
    compact = qwen.OUT / "qwen.qbpe"
    assert qwen.digest(compact) == profile["compact_sha256"]
    old, new = qwen.load(STUDENT_TOKENIZER), qwen.load(source_path)
    reserved = {row["id"] for row in old["added_tokens"]}
    old_vocab = {student_piece_bytes(piece):idx for piece,idx in old["model"]["vocab"].items() if idx not in reserved}
    assert all(bytes([b]) in old_vocab for b in range(256))
    old_eos = next(row["id"] for row in old["added_tokens"] if row["content"] == "<eos>")
    new_tokens = sorted([(i, student_piece_bytes(piece), "ordinary") for piece,i in new["model"]["vocab"].items()]
        + [(x["id"], x["content"].encode("utf-8"), "added") for x in new["added_tokens"]])
    assert [i for i, _, _ in new_tokens] == list(range(ASSIGNED))
    assert next(x["content"] for x in new["added_tokens"] if x["id"] == EOS) == "<|endoftext|>"
    origins, scales, offsets = [], [], [0]
    mapping_counts = Counter()
    for token, raw, kind in new_tokens:
        if token == EOS:
            bag, route = [(old_eos, len(raw))], "eos_role"
        elif kind == "ordinary" and raw in old_vocab:
            bag, route = [(old_vocab[raw], len(raw))], "exact_bytes"
        else:
            bag, route = segments(raw,old_vocab), "composed_" + kind
        assert sum(span for _,span in bag) == len(raw) > 0
        origins.extend(old_id for old_id,_ in bag)
        scales.extend(span/len(raw) for _,span in bag)
        offsets.append(len(origins))
        mapping_counts[route] += 1
    offsets.extend([len(origins)]*(VOCAB-ASSIGNED))
    mapping_counts["unassigned_zero"] = VOCAB-ASSIGNED

    docs = qwen.load(qwen.AUTHORED)["data"]["documents"]
    assert len(docs)==816 and len({d["id"] for d in docs})==len(docs)
    x = np.full((len(docs),WIDTH),EOS,dtype=np.int64)
    y = np.full_like(x,-100)
    with CompactQwenTokenizer(compact) as splitter:
        for row,doc in enumerate(docs):
            ids = splitter.encode(doc["text"]).ids
            assert 2 <= len(ids) <= WIDTH+1 and all(0 <= i < ASSIGNED for i in ids)
            count = len(ids)-1
            x[row,:count], y[row,:count] = ids[:-1],ids[1:]
    rng = random.Random(SEED)
    train = [[i for i,d in enumerate(docs) if d["split"] == "train" and d["language"] == lang] for lang in ("en","ko")]
    held = [[i for i,d in enumerate(docs) if d["split"] == "held" and d["language"] == lang] for lang in ("en","ko")]
    chosen = [np.asarray(rng.sample(ids,UPDATES*BATCH//2)).reshape(UPDATES,BATCH//2) for ids in train]
    draws = np.concatenate(chosen,axis=1)
    pool = int((y[np.array(sum(train,[]))]>=0).sum())
    visits = int((y[draws]>=0).sum())
    assert pool >= 2*visits and len(np.unique(draws)) == UPDATES*BATCH
    assert all(len(group)==24 for group in held)
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    for path, kwargs in (
        (MAPPING,dict(indices=np.asarray(origins,dtype=np.int64),offsets=np.asarray(offsets,dtype=np.int64),
                      scales=np.asarray(scales,dtype=np.float32))),
        (DATA,dict(x=x,y=y,draws=draws,held=np.asarray(held,dtype=np.int64))),
    ):
        with path.open("xb") as stream:
            np.savez(stream,**kwargs)
    project_files = [source_path,STUDENT_TOKENIZER,compact,qwen.AUTHORED,Path(__file__),Path(parent.__file__),
        ROOT/"tinylm/model/transformer.py",ROOT/"tinylm/model/modules.py",ROOT/"tinylm/model/ternary.py",
        ROOT/"tinylm/train/experimental_optimizers.py",ROOT/"tinylm/train/muon.py",ROOT/"tinylm/train/anneal_schedule.py",
        ROOT/"scripts/p014e_packed_g128.py",ROOT/"scripts/p109_compact_qwen_tokenizer.py"]
    pins = {str(p.relative_to(ROOT)):qwen.digest(p) for p in project_files}
    receipt = dict(tag=TAG,approval="WIP176",scope="AUTHORED_DIAGNOSTIC",pins=pins,
        parent_sha256=qwen.digest(parent.PARENT),mapping_sha256=qwen.digest(MAPPING),tokens_sha256=qwen.digest(DATA),
        mapping_counts=dict(mapping_counts),vocabulary=VOCAB,assigned=ASSIGNED,train_pool=pool,draw_targets=visits,
        step_count=UPDATES,batch=BATCH,width=WIDTH,seed=SEED,lr=LR,matrix_lr_mult=MATRIX_MULT,
        held_targets=[int((y[group]>=0).sum()) for group in held],checkpoint_writes=0,packed_new_artifact=EXPORT.name)
    qwen.write(PROFILE,receipt)
    print("P109_248K_CPU",receipt["mapping_counts"],pool,visits,receipt["held_targets"],flush=True)


def verify(profile):
    assert profile["tag"]==TAG and profile["assigned"]==ASSIGNED
    assert qwen.digest(parent.PARENT)==profile["parent_sha256"]
    assert qwen.digest(MAPPING)==profile["mapping_sha256"] and qwen.digest(DATA)==profile["tokens_sha256"]
    assert all(qwen.digest(ROOT/p)==h for p,h in profile["pins"].items())


def initialize():
    cfg, weights, step = parent.load_parent(torch)
    assert step==2289
    cfg.train_repeat, cfg.infer_repeat = 2.0, 1.0
    cfg.quant_anneal=1.0
    student=TiedMLPTransformer(cfg)
    student.load_state_dict(weights,strict=True)
    del weights
    with np.load(MAPPING,allow_pickle=False) as m, torch.no_grad():
        matrix=F.embedding_bag(torch.from_numpy(m["indices"]),student.emb.weight.detach(),
            torch.from_numpy(m["offsets"]),mode="sum",include_last_offset=True,per_sample_weights=torch.from_numpy(m["scales"]))
    assert matrix.shape==(VOCAB,256) and torch.count_nonzero(matrix[ASSIGNED:])==0
    cfg.vocab_size=student.emb.num_embeddings=VOCAB
    student.emb.weight=torch.nn.Parameter(matrix)
    student.set_anneal(1.0)
    training_route = student.visit_schedule()
    student.eval()
    assert len(training_route) == 28 and student.visit_schedule() == training_route
    student.train()
    return student.cuda()


def logits(model, x, y, amp=False):
    mask=y>=0
    with torch.autocast("cuda",dtype=torch.bfloat16,enabled=amp):
        hidden=model(x,return_hidden=True)
        scores=model._head_logits(hidden[mask])
        assert scores.shape[-1]==VOCAB
    return scores[:,:ASSIGNED].float(),y[mask]


@torch.inference_mode()
def evaluate(model, x, y, held):
    observed={}
    for lang,rows in zip(("en","ko"),held,strict=True):
        n,total,correct=0,0.,0
        for ids in rows.split(BATCH):
            scores,targets=logits(model,x[ids],y[ids])
            n+=targets.numel()
            total+=float(F.cross_entropy(scores,targets,reduction="sum"))
            correct+=int(scores.argmax(-1).eq(targets).sum())
        observed[lang]=dict(targets=n,nll=total/n,correct=correct)
    return observed


def frozen_scores(model,x,y,held):
    model.eval()
    model.freeze_quant()
    try:
        return evaluate(model,x,y,held)
    finally:
        model.clear_quant()
        model.train()


def training(profile):
    model=initialize()
    with np.load(DATA,allow_pickle=False) as bundle:
        x,y,draws,held=[torch.from_numpy(bundle[k]).cuda() for k in ("x","y","draws","held")]
    checks={0:frozen_scores(model,x,y,held)}
    route=build_experimental_optimizers(model,"muon_matched",lr=LR,matrix_lr_mult=MATRIX_MULT)
    optimizers=(route.adamw,route.matrix)
    keep_active_groups(optimizers)
    rates=[[g["lr"] for g in opt.param_groups] for opt in optimizers]
    history=[]
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for index,ids in enumerate(draws,1):
        if (OUT/"STOP").exists() or datetime.now(parent.CUTOFF.tzinfo)>=parent.CUTOFF:
            raise RuntimeError("owned STOP or deadline")
        factor=lr_factor(index-1,WARMUP,UPDATES,"cosine")
        for opt,base in zip(optimizers,rates,strict=True):
            for group,lr in zip(opt.param_groups,base,strict=True):
                group["lr"]=lr*factor
        start=perf_counter()
        scores,targets=logits(model,x[ids],y[ids],amp=True)
        loss=F.cross_entropy(scores,targets)
        loss.backward()
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        torch.cuda.synchronize()
        history.append(dict(step=index,loss=float(loss.detach()),gradient_norm=float(norm),targets=targets.numel(),
                            seconds=perf_counter()-start))
        del scores,targets,loss,norm
        if index in (16,32,64,UPDATES):
            checks[index]=frozen_scores(model,x,y,held)
            print("P109_248K_TRAIN",index,checks[index],flush=True)
    assert sum(row["targets"] for row in history)==profile["draw_targets"]
    assert [checks[0][lang]["targets"] for lang in ("en","ko")]==profile["held_targets"]
    device_peak=torch.cuda.max_memory_allocated()
    del optimizers,route,opt
    model=model.cpu().eval()
    torch.cuda.empty_cache()
    model.freeze_quant()
    data=export_payload(model,provenance=dict(tag=TAG,parent_sha256=profile["parent_sha256"],
        profile_sha256=qwen.digest(PROFILE),training_updates=UPDATES,assigned_rows=ASSIGNED),
        tile_rows=1024,embedding_format="ternary5_existing_twn",head_rows=2048)
    assert len(data["matrices"])==69 and data["embedding"]["out_features"]==VOCAB
    with EXPORT.open("xb") as stream:
        torch.save(data,stream)
    packed_bytes=payload_storage(data)
    del model
    frozen=load_payload(data,device="cuda",tile_rows=4096)
    del data
    after=evaluate(frozen,x,y,held)
    del frozen
    torch.cuda.empty_cache()
    print("P109_248K_PACKED",after,EXPORT.stat().st_size,flush=True)
    return dict(held_by_update=checks,packed_held=after,history=history,gpu_train_peak_allocated=device_peak,
        median_update_seconds=median(v["seconds"] for v in history[WARMUP:]),packed_payload_storage=packed_bytes,
        packed_bytes=EXPORT.stat().st_size,packed_sha256=qwen.digest(EXPORT),checkpoint_writes=0)


def run():
    assert idle() and torch.cuda.device_count()==1
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.set_float32_matmul_precision("highest")
    profile=qwen.load(PROFILE)
    verify(profile)
    device=OUT/"device_100ms.csv"
    qwen.write(OUT/"active.json",dict(tag=TAG,pid=os.getpid()))
    with device.open("xb") as stream:
        monitor=subprocess.Popen((*DEVICE,f"--loop-ms={INTERVAL_MS}"),stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                result=training(profile)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    verify(profile)
    samples=read_samples(device)
    assert samples
    result.update(device_peak=max(samples,key=lambda r:r["occupied_mib"]),device_samples=len(samples),
                  profile_sha256=qwen.digest(PROFILE),source_preserved=True)
    qwen.write(OUT/"report.json",result)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase=parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(parent.CUTOFF.tzinfo)+timedelta(seconds=620)<parent.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if phase=="prepare":
        prepare()
    else:
        assert os.environ.get("CUBLAS_WORKSPACE_CONFIG")==":4096:8"
        run()
