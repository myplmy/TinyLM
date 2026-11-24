"""Exercise the frozen DWA objective and actual Native CUDA optimizer groups."""

import argparse
from contextlib import nullcontext
import json
import math
import os
import random
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as io
from scripts.p107_active_optimizer_groups import keep_active_groups


TAG = "p106b_dwa_native_updates_synthetic_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
FIXTURE = OUT / "fixture.json"
ARMS = ("ce", "dwa")
WIDTH, VOCAB, TEACHER_WIDTH, TEACHER_VOCAB, GROUPS, ROWS, CAP = 64,32768,1024,151936,3,4,420
STUDENT_IDS, TEACHER_IDS, STUDENT_HEAD_SKIP, TEACHER_HEAD_SKIP = 16,19,5,6
CE = ROWS*(STUDENT_IDS-STUDENT_HEAD_SKIP)
TEACHER_TARGETS = ROWS*(TEACHER_IDS-TEACHER_HEAD_SKIP)
BAND = dict(alpha=.7,base=5.,entropy_scale=2.,penalty=1.)
SOURCES = (
    "scripts/diag_p106b_dwa_native_updates.py", "scripts/diag_p013_native_matched_training.py",
    "scripts/p106b_dwa_cma.py", "scripts/p106b_dwa_native.py", "scripts/p106b_softdtw_triton_v2.py",
    "scripts/p107_scaled_optimizer_group.py", "scripts/p107_active_optimizer_groups.py",
    "scripts/interactive_research_infer.py", "tinylm/model/transformer.py", "tinylm/model/ternary.py",
    "tinylm/config.py", "tinylm/train/anneal_schedule.py", "tinylm/train/muon.py",
    "tinylm/train/experimental_optimizers.py",
)


def fixture():
    rng = random.Random(271882)
    return [[dict(row_id=f"{group}:{row}",student=[rng.randrange(35,VOCAB) for _ in range(STUDENT_IDS)],
        teacher=[rng.randrange(35,TEACHER_VOCAB) for _ in range(TEACHER_IDS)]) for row in range(ROWS)]
        for group in range(GROUPS)]


def pins():
    return {name:io.digest(io.ROOT/name) for name in SOURCES}


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    OUT.mkdir(exist_ok=False)
    io.write(FIXTURE,fixture())
    io.write(PROFILE,dict(tag=TAG,sources=pins(),fixture=io.digest(FIXTURE),width=WIDTH,band=BAND,
        full_vocabs=[VOCAB,TEACHER_VOCAB],teacher_width=TEACHER_WIDTH,ce=CE,teacher_targets=TEACHER_TARGETS,
        soft_dtw_gamma=.1,coefficient=.3,native_updates=GROUPS,repeated_evaluations=0))
    verify()
    print("DWA_NATIVE_UPDATE_PREPARED",io.digest(PROFILE),CE,TEACHER_TARGETS,flush=True)


def verify():
    profile = json.loads(PROFILE.read_bytes())
    assert profile["sources"]==pins() and profile["fixture"]==io.digest(FIXTURE)
    data = json.loads(FIXTURE.read_bytes())
    assert data==fixture()
    return data


def worker(arm):
    import torch
    from torch.nn import functional as F
    from scripts.interactive_research_infer import state_fingerprint
    from scripts.p106b_dwa_cma import loss_components
    from scripts.p106b_dwa_native import close_accounting, predictor_view, streaming_share
    from scripts.p106b_softdtw_triton_v2 import soft_dtw
    from scripts.p107_scaled_optimizer_group import ScaleConfig, ScaledOptimizerGroup
    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.anneal_schedule import lr_factor
    from tinylm.train.experimental_optimizers import build_experimental_optimizers

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
    data = verify()
    entry = io.reserve_device()
    out = OUT/arm
    out.mkdir(exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    start = time.monotonic()
    cfg = build_config("m100s10","dense",WIDTH,True)
    model = TiedMLPTransformer(cfg).cuda().train()
    model.set_anneal(1.)
    initial = state_fingerprint(model)
    route = build_experimental_optimizers(model,"muon_matched",lr=.0006,matrix_lr_mult=1.)
    optimizers = [route.matrix,route.adamw]
    assert keep_active_groups(optimizers)==[0,2]
    parameters = [p for p in model.parameters() if p.requires_grad]
    generator = torch.Generator(device="cuda").manual_seed(123001)
    enabled = arm == "dwa"
    projectors = teacher_head = original_projectors = None
    if enabled:
        teacher_head = torch.empty((TEACHER_VOCAB,TEACHER_WIDTH),device="cuda").normal_(0.,.02,generator=generator)
        projectors = torch.nn.ModuleDict({name:torch.nn.Linear(a,b,bias=False) for name,a,b in (
            ("query",2*cfg.dim,2*TEACHER_WIDTH), ("t2s",TEACHER_WIDTH,cfg.dim),
            ("s2t",cfg.dim,TEACHER_WIDTH), ("embedding_t2s",TEACHER_WIDTH,cfg.dim))}).cuda()
        original_projectors = state_fingerprint(projectors)
        parameters.extend(projectors.parameters())
        optimizers.append(torch.optim.AdamW(projectors.parameters(),lr=.0006))
    rates = [[g["lr"] for g in opt.param_groups] for opt in optimizers]
    controller = ScaledOptimizerGroup(parameters,optimizers,run_signature=io.digest(PROFILE),
        expected_backwards=ROWS,config=ScaleConfig(init_scale=128.,growth_interval=2))

    def student_embedding(ids):
        return F.linear(F.embedding(ids,model._emb_w()),model._emb_up_w())

    def align(cost):
        return soft_dtw(cost.double().contiguous(),gamma=.1)

    records = []
    for ordinal, rows in enumerate(data):
        if (OUT/"STOP").exists() or time.monotonic()-start>CAP-25:
            raise TimeoutError("owned CUDA window or STOP")
        for opt,base in zip(optimizers,rates,strict=True):
            for group,lr in zip(opt.param_groups,base,strict=True):
                group["lr"] = lr*lr_factor(ordinal,1,GROUPS,"cosine",.2)
        torch.cuda.synchronize()
        before = time.monotonic()
        decoded = []
        student_head = model._emb_w().detach() @ model._emb_up_w().detach().T if enabled else None
        for row in rows:
            ids = row["student"]
            x = torch.tensor([ids[:-1]+[0]*(WIDTH-len(ids)+1)],device="cuda")
            with torch.autocast("cuda",dtype=torch.bfloat16):
                hidden = model(x,return_hidden=True)[0,:len(ids)-1]
            student = predictor_view(torch,ids,[False]*STUDENT_HEAD_SKIP+[True]*(STUDENT_IDS-STUDENT_HEAD_SKIP),
                hidden.float(),student_embedding)
            sl = model._head_logits(student.hidden)
            if enabled:
                ti = row["teacher"]
                features = torch.randn((len(ti)-1,TEACHER_WIDTH),generator=generator,device="cuda")
                teacher = predictor_view(torch,ti,[False]*TEACHER_HEAD_SKIP+[True]*(TEACHER_IDS-TEACHER_HEAD_SKIP),
                    features,lambda selected:F.embedding(selected,teacher_head))
                packet = loss_components(torch,student,teacher,sl,teacher.hidden@teacher_head.T,**projectors,
                    student_head=student_head,teacher_head=teacher_head,kd_gate_scale=1.,dtw=align,band=BAND)
                loss = streaming_share(packet,global_student_targets=CE,kd_rate=.3,dtw_rate=.3)
                raw = {key:float(value.detach()) for key,value in packet["raw"].items()}
            else:
                ce = F.cross_entropy(sl,student.targets,reduction="sum")
                loss = ce/CE
                raw = {"student_ce":float(ce.detach())}
            controller.backward(loss)
            decoded.append(dict(row_id=row["row_id"],student_count=student.count,
                teacher_count=TEACHER_IDS-TEACHER_HEAD_SKIP,raw=raw))
            del student,hidden,sl,loss
            if enabled:
                del packet,teacher,features
        torch.cuda.synchronize()
        mark = time.monotonic()
        result = controller.finish(clip_norm=1.)
        torch.cuda.synchronize()
        assert result["status"]=="STEPPED_ALL" and result["optimizer_step_calls"]==len(optimizers)
        accounting = close_accounting(decoded,expected_ids=[r["row_id"] for r in rows],student_targets=CE,teacher_targets=TEACHER_TARGETS)
        combined = {key:math.fsum(row["raw"][key] for row in decoded) for key in decoded[0]["raw"]}
        event = dict(group=ordinal,source=accounting,raw_sums=combined,optimizer=result,
            forward_backward_seconds=mark-before,optimizer_seconds=time.monotonic()-mark)
        io.write(out/f"update_{ordinal}.json",event)
        records.append(event)
        print("DWA_NATIVE_UPDATE",arm,ordinal,result["status"],flush=True)
    final = state_fingerprint(model)
    assert initial!=final
    projection = state_fingerprint(projectors) if enabled else None
    assert not enabled or (original_projectors!=projection and teacher_head.grad is None)
    io.write(out/"report.json",dict(arm=arm,initial=initial,final=final,updates=records,
        projector_changed=original_projectors!=projection,teacher_model_calls=0,peak_allocated=torch.cuda.max_memory_allocated(),
        peak_reserved=torch.cuda.max_memory_reserved(),wall_seconds=time.monotonic()-start,entry=entry,checkpoint_writes=0))


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0" and time.time()+2*CAP+120<io.CUTOFF
    verify()
    closed,reports = {},{}
    for arm in ARMS:
        require_idle_gpu()
        env = dict(os.environ,TRITON_CACHE_DIR=str(OUT/"triton_cache"))
        argv = [sys.executable,"-B","-u","-m","scripts.diag_p106b_dwa_native_updates","worker",arm]
        try:
            code = subprocess.run(argv,cwd=io.ROOT,env=env,timeout=CAP).returncode
        except subprocess.TimeoutExpired:
            code = 124
        path = OUT/arm/"report.json"
        closed[arm] = dict(exit=code,after_exit=require_idle_gpu(),sha256=io.digest(path) if path.is_file() else None)
        if code==0 and path.is_file():
            reports[arm] = json.loads(path.read_bytes())
    verify()
    complete = set(reports)==set(ARMS)
    io.write(OUT/"terminal.json",dict(complete_workers=complete,arms=closed))
    if not complete:
        return 8
    a,b = (reports[arm] for arm in ARMS)
    assert a["initial"]==b["initial"] and a["final"]!=b["final"]
    assert a["updates"][0]["raw_sums"]["student_ce"]==b["updates"][0]["raw_sums"]["student_ce"]
    io.write(OUT/"report.json",dict(complete=True,profile_sha256=io.digest(PROFILE),arms=reports))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run","worker"))
    parser.add_argument("arm",nargs="?",choices=ARMS)
    args = parser.parse_args()
    if (args.phase=="worker") != (args.arm is not None):
        parser.error("only a worker gets an arm")
    handlers = {"prepare":prepare,"run":run,"worker":lambda:worker(args.arm)}
    raise SystemExit(handlers[args.phase]())
