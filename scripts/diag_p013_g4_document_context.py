"""Compare matched document-isolated G4 context schedules on existing authored rows."""

import argparse
from datetime import datetime
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel
from tokenizers import Tokenizer

from scripts import diag_p102a_g4_joint_ce_kl_batch8 as sampling
from scripts import diag_p107_g4_r2_visibility as r2
from scripts import diag_p109_warm_visit_routes as warm
from scripts import interactive_research_infer as manual
from scripts.diag_p106b_gsq_objective import write
from tinylm.model import TiedMLPTransformer, transformer
from tinylm.train.context_curriculum import ContextPlan
from tinylm.train.document_context_curriculum import regroup_document_context
from tinylm.train.hybrid_mntp import IGNORE_INDEX, document_visibility


ROOT = warm.io.ROOT
TAG = "p013_g4_document_context_actual_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
BATCHES = OUT / "draws.npz"
SOURCE = ROOT / "test_result/evidence/p106b_p109_actual_prefix_kd_v1_20261119"
PLAN = ROOT / "test_plan/P013_seq-length-warmup-소규모.md"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768.json"
TOKENIZER_SHA = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
WIDTH, BATCH, ACCUM, STEPS, SEED, LR = 1024, 2, 2, 8, 5711024, 3e-5
FIXED = ContextPlan(((8,1024),), BATCH, ACCUM, WIDTH)
STAGED = ContextPlan(((2,128),(4,256),(6,512),(8,1024)), BATCH, ACCUM, WIDTH)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def gate(reserve=0):
    if (END - datetime.now(END.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 time window or local stop reached")


def sources():
    files = (
        Path(__file__).resolve(), Path(warm.__file__).resolve(), Path(r2.__file__).resolve(),
        Path(sampling.__file__).resolve(), SOURCE / "profile.json", SOURCE / "report.json", PLAN, TOKENIZER,
        ROOT / "tinylm/train/document_context_curriculum.py", ROOT / "tinylm/train/context_curriculum.py",
        ROOT / "tinylm/train/hybrid_mntp.py", ROOT / "tinylm/model/transformer.py",
        ROOT / "tinylm/model/visibility.py", ROOT / "tinylm/model/ternary.py",
        ROOT / "tinylm/model/modules.py", ROOT / "tinylm/config.py",
    )
    return {p.relative_to(ROOT).as_posix():manual.file_sha(p) for p in files}


def make_draws():
    archive = read(SOURCE / "profile.json")
    evidence = read(SOURCE / "report.json")
    if not evidence["source_preserved"] or manual.file_sha(TOKENIZER) != TOKENIZER_SHA:
        raise ValueError("The closed original authored sources and 32K tokenizer are required")
    tok = Tokenizer.from_file(str(TOKENIZER))
    documents = archive["data"]["documents"]
    if len(documents) != 816 or len({doc["id"] for doc in documents}) != 816:
        raise ValueError("Original authored ID coverage differs")
    pools = {key:[] for key in ("train","held")}
    seen_tokens = set()
    for identifier, row in enumerate(documents):
        ids = tuple(tok.encode(row["text"],add_special_tokens=False).ids)
        if len(ids) < 2 or ids in seen_tokens:
            raise ValueError("Authored document tokens are short or duplicate")
        seen_tokens.add(ids)
        pools[row["split"]].append((identifier,ids))
    rng = np.random.default_rng(SEED)
    arrays, receipts = {}, {}
    for split, rows in pools.items():
        if len(rows) != {"train":768,"held":48}[split]:
            raise ValueError("Wrong original authored partition size")
        raw = np.concatenate([np.asarray(ids,dtype=np.int64) for _,ids in rows])
        owners = np.repeat([identifier for identifier,_ in rows], [len(ids) for _,ids in rows])
        steps = STEPS if split == "train" else 1
        offset = rng.integers(0, len(raw)-WIDTH-1, size=(steps,ACCUM,BATCH))
        index = offset[...,None] + np.arange(WIDTH+1)
        arrays[split+"_tokens"], arrays[split+"_doc_ids"], arrays[split+"_starts"] = raw[index], owners[index], offset
        receipts[split] = dict(documents=len(rows), tokens=len(raw), longest=max(len(ids) for _,ids in rows),
                               full_draws=int(offset.size), exact_token_duplicate_documents=0,
                               pool_sha256=sha256(raw.tobytes()+owners.tobytes()).hexdigest().upper())
    return arrays, receipts, archive["sources"]["parent_sha"]


def pair(arrays, split, step):
    return tuple(zip((torch.from_numpy(x) for x in arrays[split+"_tokens"][step]),
                     (torch.from_numpy(x) for x in arrays[split+"_doc_ids"][step]),strict=True))


def audit(arrays):
    summaries = []
    for step in range(STEPS):
        rows = pair(arrays,"train",step)
        valid = sum(int((d[:, :-1] == d[:, 1:]).sum()) for _,d in rows)
        variants = {}
        for n in (128,256,512,1024):
            current = regroup_document_context(rows,FIXED,n,vocab_size=32768)
            if current.target_count != valid or current.input_slots != 4096:
                raise ValueError("CPU counting or original source identity differs")
            for batch,(tokens,owners) in zip(current.batches,rows,strict=True):
                doc = owners[:,:-1].reshape(-1,n)
                allowed = (doc[:,:,None] == doc[:,None,:]).tril()
                if (not torch.equal(batch.inputs,tokens[:,:-1].reshape_as(batch.inputs))
                        or not torch.equal(batch.attention_mask[:,0],allowed)):
                    raise ValueError("Independent chunk input or mask oracle differs")
            variants[str(n)] = current.retained_chunk_final_targets
        summaries.append(dict(step=step+1,targets=valid,ignored=4096-valid,chunk_final=variants))
    # Prevent a bad source from becoming acceptable only because its repeat crosses two chunks.
    tiny = ContextPlan(((1,4),),1,1,4)
    tokens = torch.arange(40,45).reshape(1,5)
    docs = torch.tensor([[0,0,1,1,-1]])
    check = regroup_document_context(((tokens,docs),),tiny,2,vocab_size=32768)
    assert check.target_count == 2 and check.batches[0].targets.tolist() == [[41,-100],[43,-100]]
    try:
        regroup_document_context(((tokens,torch.tensor([[0,0,1,1,0]])),),tiny,2,vocab_size=32768)
    except ValueError:
        pass
    else:
        raise AssertionError("Noncontiguous repeated source document was accepted")
    return summaries


def prepare():
    gate()
    torch.set_num_threads(1)
    arrays, receipts, parent = make_draws()
    summary = audit(arrays)
    if torch.cuda.is_initialized() or manual.file_sha(warm.PARENT) != parent:
        raise ValueError("CPU-only preparation and matching exact G4 parent are required")
    OUT.mkdir()
    with BATCHES.open("xb") as stream:
        np.savez(stream,**arrays)
    (OUT/"plan_at_execution.md").write_bytes(PLAN.read_bytes())
    write(PROFILE,dict(tag=TAG,user_directive=177,end=END.isoformat(),sources=sources(),
                       parent_sha256=parent,draws_sha256=manual.file_sha(BATCHES),pools=receipts,
                       shape=[STEPS,ACCUM,BATCH,WIDTH+1],scheduled=[STAGED.length_at(i) for i in range(STEPS)],
                       audit=summary,lr=LR,official_quality=False))
    print("G4_DOC_CONTEXT_SEAL",receipts,sum(row["targets"] for row in summary),flush=True)


def forward(model,batch):
    inputs, targets, mask = batch.inputs.cuda(), batch.targets.cuda(), batch.attention_mask.cuda()
    with torch.autocast("cuda",dtype=torch.bfloat16):
        logits = model(inputs,attention_mask=mask)
    # Outer FP32 reduction with the original ignore_index and complete group denominator.
    return F.cross_entropy(logits.float().flatten(0,1),targets.flatten(),reduction="sum",ignore_index=-100)


@torch.no_grad()
def held_readback(model,arrays,generate=False):
    model.eval()
    held = pair(arrays,"held",0)
    group = regroup_document_context(held,FIXED,WIDTH,vocab_size=32768)
    total = sum(float(forward(model,batch)) for batch in group.batches)
    answer = []
    if generate:
        tokens, docs = (t[:1,:-1].cuda() for t in held[0])
        for _ in range(2):
            mask = document_visibility(docs,bidirectional=False)
            with torch.autocast("cuda",dtype=torch.bfloat16):
                suffix = model(tokens,attention_mask=mask)[:,-1].argmax(dim=-1,keepdim=True)
            answer.append(int(suffix.item()))
            tokens = torch.cat((tokens[:,1:],suffix),dim=1)
            docs = torch.cat((docs[:,1:],docs[:,-1:]),dim=1)
    return dict(width=WIDTH,targets=group.target_count,nll=total/group.target_count,generated_ids=answer)


def train(name,plan,profile,arrays):
    torch.manual_seed(SEED)
    cfg, state, step = warm.load_parent(torch)
    assert step == 2289 and cfg.max_seq_len >= WIDTH
    cfg.train_repeat = 2.
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(state,strict=True)
    del state
    model.set_anneal(1.)
    model.cuda()
    initial = manual.state_fingerprint(model)
    pre = held_readback(model,arrays)
    model.train()
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters,lr=LR,betas=(.9,.95),weight_decay=0.,foreach=False,fused=False)
    torch.cuda.reset_peak_memory_stats()
    history = []
    for step in range(plan.steps):
        gate(15)
        optimizer.zero_grad(set_to_none=True)
        start = perf_counter()
        batch = regroup_document_context(pair(arrays,"train",step),plan,plan.length_at(step),vocab_size=32768)
        if batch.target_count != profile["audit"][step]["targets"]:
            raise ValueError("Actual update target denominator differs from the CPU readback")
        total = 0.
        for micro in batch.batches:
            loss = forward(model,micro)
            (loss / batch.target_count).backward()
            total += float(loss.detach())
            del loss
        norm = torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True).item()
        if not norm > 0:
            raise ValueError("A real complete optimizer update requires finite nonzero gradients")
        optimizer.step()
        torch.cuda.synchronize()
        row = dict(step=step+1,width=batch.length,targets=batch.target_count,slots=batch.input_slots,
                   ignored=batch.excluded_targets,chunk_final=batch.retained_chunk_final_targets,
                   mask_bytes=sum(m.attention_mask.numel() for m in batch.batches),
                   nll=total/batch.target_count,norm=norm,seconds=perf_counter()-start)
        history.append(row)
        print("G4_DOC_CONTEXT_UPDATE",name,row,flush=True)
    peaks = dict(allocated=torch.cuda.max_memory_allocated(),reserved=torch.cuda.max_memory_reserved())
    final = manual.state_fingerprint(model)
    updates = sorted({int(st["step"].item()) for st in optimizer.state.values()})
    if updates != [STEPS] or initial == final:
        raise ValueError("Observed student and optimizer state did not complete")
    final_view = held_readback(model,arrays,generate=True)
    return dict(initial=initial,final=final,history=history,training_peak=peaks,
                updates=updates,held_before=pre,held_after=final_view)


def actual():
    from scripts.diag_p107_hybrid_mntp import close_owned_cuda

    gate(240)
    profile = read(PROFILE)
    if (profile["sources"] != sources() or profile["draws_sha256"] != manual.file_sha(BATCHES)
            or profile["parent_sha256"] != manual.file_sha(warm.PARENT)):
        raise ValueError("The sealed exact author, parent or draw closure differs")
    entry = manual.require_idle_gpu()
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 10*(1<<30):
        raise MemoryError("The single GPU needs at least 10 GiB free")
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    arms = {}
    with (np.load(BATCHES,allow_pickle=False) as arrays,
          patch.object(transformer,"prepare_visibility",r2.prepare_r2),sdpa_kernel(SDPBackend.MATH)):
        for name,plan in (("fixed",FIXED),("staged",STAGED)):
            csv = OUT / (name+"_device_100ms.csv")
            with csv.open("xb") as stream:
                sampler = subprocess.Popen((*sampling.DEVICE,f"--loop-ms={sampling.INTERVAL_MS}"),stdout=stream)
                try:
                    arms[name] = train(name,plan,profile,arrays)
                finally:
                    if sampler.poll() is None:
                        sampler.terminate()
                    sampler.wait(timeout=8)
            samples = sampling.read_samples(csv)
            arms[name].update(sample_count=len(samples),device_peak=max(samples,key=lambda row:row["occupied_mib"]))
            write(OUT / f"{name}.json",arms[name])
            gc.collect()
            torch.cuda.empty_cache()
    a,b = arms.values()
    if (a["initial"] != b["initial"] or a["held_before"] != b["held_before"]
            or [r["targets"] for r in a["history"]] != [r["targets"] for r in b["history"]]):
        raise ValueError("Same original model, held proof and update-specific target count required")
    result = dict(profile_sha256=manual.file_sha(PROFILE),entry=entry,arms=arms,checkpoint_writes=0)
    close_owned_cuda(torch,result)
    result["source_preserved"] = (
        profile["sources"] == sources() and profile["draws_sha256"] == manual.file_sha(BATCHES)
        and profile["parent_sha256"] == manual.file_sha(warm.PARENT))
    if not result["source_preserved"]:
        raise ValueError("A protected source or checkpoint differs")
    write(OUT/"report.json",result)
    print("G4_DOC_CONTEXT_RESULT",a["updates"],b["updates"],flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","actual"))
    phase = parser.parse_args().phase
    expected = "" if phase=="prepare" else "0"
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use isolated CPU preparation and the authorized CUDA device")
    if expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS is required")
    (prepare if phase=="prepare" else actual)()


if __name__ == "__main__":
    main()
