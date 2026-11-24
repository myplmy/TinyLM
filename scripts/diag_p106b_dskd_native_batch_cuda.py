"""Exercise the actual Native BF16 batch/CE/KD and CUDA optimizer boundary."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from scripts import diag_p013_native_matched_training as training
from scripts.p106b_official_lm_adapter import canonical


ROOT = training.ROOT
TAG = "p106b_dskd_native_batch_cuda_synthetic_v2_20261118"
OUT = ROOT/"test_result/evidence"/TAG
PROFILE = OUT/"profile.json"
DATA = OUT/"fixture.json"
WIDTH, ROWS, UPDATES, BATCH, VOCAB = 1024, 17, 4, 8, 32768
TEACHER_WIDTH, TEACHER_VOCAB = 1024, 151936
TARGET_POSITIONS = (0,255,511,767,1022)
FEATURE_ROWS = (0,7,8,16)
TEACHER_TOP = (19,101,220,301,574)
ARMS = ("ce","feature_kd")
SOURCE_PINS = (
    "scripts/diag_p106b_dskd_native_batch_cuda.py", "scripts/diag_p013_native_matched_training.py",
    "scripts/p106b_dskdv2_microbatch.py","scripts/p106b_dskdv2_training.py","scripts/p106b_dskdv2_window.py",
    "scripts/p106b_dskdv2_contract.py","scripts/p106b_feature_window.py","scripts/p107_scaled_optimizer_group.py",
    "tinylm/train/experimental_optimizers.py","tinylm/train/anneal_schedule.py",
    "tinylm/config.py","tinylm/model/transformer.py","tinylm/model/ternary.py",
)


def source_pins():
    return {name:training.digest(ROOT/name) for name in SOURCE_PINS}


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==""
    OUT.mkdir(exist_ok=False)
    features = OUT/"features"
    features.mkdir()
    rng = np.random.default_rng(1337)
    feature = np.zeros((len(TARGET_POSITIONS)+1,TEACHER_WIDTH),dtype="<f4")
    feature[:len(TARGET_POSITIONS),:len(TARGET_POSITIONS)] = np.eye(len(TARGET_POSITIONS))
    groups, pins = [], {}
    for ordinal in range(UPDATES):
        meta, packed, kd = [], [], []
        for i in range(ROWS):
            ids = rng.integers(3,VOCAB,size=WIDTH).tolist()
            item = dict(ids=ids,labels=[-100]+ids[1:],turn_ids=[0]+[1]*(WIDTH-1))
            fingerprint = canonical(item)
            row = dict(row_id=f"u{ordinal}_r{i}",semantic_root_id=f"root_u{ordinal}_r{i}",
                record_sha256=hashlib.sha256(b"synthetic_record"+fingerprint).hexdigest().upper(),
                source_row_sha256=hashlib.sha256(b"synthetic_source"+fingerprint).hexdigest().upper(),
                student_tokens=WIDTH,split="train",ce_targets=WIDTH-1)
            meta.append(row)
            packed.append(item)
            if i in FEATURE_ROWS:
                path = features/(row["row_id"]+".npy")
                with path.open("xb") as stream:
                    np.save(stream,feature,allow_pickle=False)
                sha = pins[path.name] = training.digest(path)
                aligned = [dict(student_predictor_raw_index=si,student_target_raw_index=si+1,
                    teacher_predictor_raw_index=ti,teacher_target_raw_index=ti+1,student_target_id=ids[si+1],
                    teacher_native_argmax=top,mapped_student_argmax=top,mapping_mode=1,
                    accepted=True,lookahead_bytes=0,owner=1) for ti,(si,top) in enumerate(zip(TARGET_POSITIONS,TEACHER_TOP,strict=True))]
                kd.append(dict(**row,teacher_tokens=len(feature),feature_file=path.name,feature_sha256=sha,positions=aligned))
        groups.append(dict(ce=meta,packed=packed,kd=kd))
    training.write(DATA,groups)
    recipe = dict(teacher_vocab=TEACHER_VOCAB,teacher_width=TEACHER_WIDTH,top_ids=TEACHER_TOP,
        uniform_seed=153737,alignment="IDENTITY_MOD_STUDENT_VOCAB",student_vocab=VOCAB)
    design_sha = hashlib.sha256(canonical(recipe)).hexdigest().upper()
    ids = dict(teacher_sha256=design_sha,tokenizer_sha256=hashlib.sha256(b"synthetic numeric token ids").hexdigest().upper(),
        mapping_sha256=design_sha,data_sha256=training.digest(DATA))
    previous = ROOT/"test_result/evidence/p106b_dskd_native_batch_cuda_synthetic_v1_20261118/profile.json"
    original = json.loads(previous.read_bytes())
    assert original["fixture_sha256"]==training.digest(DATA) and original["features"]==pins
    training.write(PROFILE,dict(schema="DSKD_NATIVE_CUDA_SYNTHETIC_PROFILE_V2",tag=TAG,sources=source_pins(),
        fixture_sha256=training.digest(DATA),features=pins,existing_checkpoints=0,model_calls=0,
        declared_synthetic_identities=ids,synthetic_recipe=recipe,
        previous_fixture_byte_exact=True,previous_profile_sha256=training.digest(previous),
        native_shape=dict(batch=BATCH,width=WIDTH,rows=ROWS,vocab=VOCAB,teacher_width=TEACHER_WIDTH,teacher_vocab=TEACHER_VOCAB)))
    print("DSKD_NATIVE_CUDA_PREPARED",training.digest(PROFILE),len(pins),flush=True)


def verify():
    profile = json.loads(PROFILE.read_bytes())
    assert profile["sources"]==source_pins() and profile["fixture_sha256"]==training.digest(DATA)
    assert len(profile["features"])==len(FEATURE_ROWS)*UPDATES
    assert all(training.digest(OUT/"features"/name)==sha for name,sha in profile["features"].items())
    return profile


def teacher_parameters(torch, student_dim):
    generator = torch.Generator(device="cuda").manual_seed(153737)
    head = torch.empty((TEACHER_VOCAB,TEACHER_WIDTH),device="cuda").uniform_(-.02,.02,generator=generator)
    for i, top in enumerate(TEACHER_TOP):
        head[top,i] = 1.
    assert head[:,:len(TEACHER_TOP)].argmax(dim=0).tolist()==list(TEACHER_TOP)
    def normal(shape):
        return torch.empty(shape,device="cuda").normal_(0.,.025,generator=generator)
    return head, torch.nn.Parameter(normal((TEACHER_WIDTH,student_dim))), normal((student_dim,TEACHER_WIDTH))


def worker(name):
    profile = verify()
    device = training.reserve_device()
    import torch
    from scripts.interactive_research_infer import state_fingerprint
    from scripts.p106b_dskdv2_microbatch import CausalMicrobatchFrames
    from scripts.p106b_dskdv2_training import CEKDGroup
    from scripts.p106b_feature_window import FeatureWindow
    from scripts.p107_scaled_optimizer_group import ScaledOptimizerGroup, ScaleConfig
    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.anneal_schedule import lr_factor
    from tinylm.train.experimental_optimizers import build_experimental_optimizers

    target = OUT/name
    target.mkdir(exist_ok=False)
    started = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()
    cfg = build_config("m100s10","dense",WIDTH,True)
    assert cfg.dim==768 and cfg.n_layers==14 and cfg.vocab_size==VOCAB
    student = TiedMLPTransformer(cfg).cuda().train()
    student.set_anneal(1.)
    init = state_fingerprint(student)
    route = build_experimental_optimizers(student,"muon_matched",lr=6e-4,matrix_lr_mult=1.)
    optimizers = [route.matrix,route.adamw]
    params = [p for p in student.parameters() if p.requires_grad]
    head = t2s = s2t = mapping = modes = None
    if name=="feature_kd":
        head,t2s,s2t = teacher_parameters(torch,cfg.dim)
        mapping = [i%VOCAB for i in range(TEACHER_VOCAB)]
        modes = [1]*TEACHER_VOCAB
        optimizers.append(torch.optim.AdamW([t2s],lr=6e-4))
        params.append(t2s)
    base_rates = [[group["lr"] for group in optimizer.param_groups] for optimizer in optimizers]
    controller = None
    summary = []
    for ordinal,fixture in enumerate(json.loads(DATA.read_bytes())):
        if time.monotonic()-started>840 or (OUT/"STOP").exists():
            raise TimeoutError("declared run time or owned STOP")
        stage = time.monotonic()
        reader = None
        if name=="feature_kd":
            reader = FeatureWindow(fixture["kd"],root=OUT/"features",identities=profile["declared_synthetic_identities"],split="train",
                hidden_width=TEACHER_WIDTH,batch_positions=7)
        group = CEKDGroup(student,fixture["ce"],up=student._emb_up_w(),embedding=student._emb_w(),
            student_width=WIDTH,reader=reader,teacher_head=head,t2s=t2s,s2t=s2t,teacher_width=WIDTH,
            mapping=mapping,mapping_modes=modes,chunk_positions=4,ce_chunk=64,kd_rate=.3,parameters=params)
        frames = CausalMicrobatchFrames(student,fixture["ce"],fixture["packed"],student_width=WIDTH,batch_size=BATCH,
            pad_id=0,autocast_dtype=torch.bfloat16)
        if controller is None:
            controller = ScaledOptimizerGroup(params,optimizers,run_signature=training.digest(PROFILE),
                expected_backwards=group.expected_backward_calls,config=ScaleConfig(init_scale=128.,growth_interval=2))
        assert controller.expected_backwards==group.expected_backward_calls
        factor = lr_factor(ordinal,1,UPDATES,"cosine",.2)
        for optimizer,rates in zip(optimizers,base_rates,strict=True):
            for param_group,rate in zip(optimizer.param_groups,rates,strict=True):
                param_group["lr"] = factor*rate
        torch.cuda.synchronize()
        start_train = time.monotonic()
        complete = frames.consume(group,lambda loss,ctx:controller.backward(loss,retain_graph=ctx["retain_graph"]))
        torch.cuda.synchronize()
        optim_start = time.monotonic()
        update = controller.finish(clip_norm=1.)
        torch.cuda.synchronize()
        assert complete["forward_calls"]==3 and complete["group"]["global_ce_denominator"]==ROWS*(WIDTH-1)
        assert complete["group"]["global_kd_denominator"]==(len(FEATURE_ROWS)*len(TARGET_POSITIONS) if reader else 0)
        result = dict(ordinal=ordinal,lr_factor=factor,prepare_seconds=start_train-stage,
            forward_backward_seconds=optim_start-start_train,optimizer_seconds=time.monotonic()-optim_start,
            frame_group=complete,update=update)
        training.write(target/f"update_{ordinal}.json",result)
        summary.append(result)
        print("DSKD_NATIVE_CUDA_UPDATE",name,ordinal,update["status"],flush=True)
        if update["status"]!="STEPPED_ALL":
            raise RuntimeError("actual optimizer group did not update all roles")
        if ordinal==0 and time.monotonic()-started+3*(time.monotonic()-stage)*1.5+60>900:
            raise TimeoutError("remaining updates exceed measured budget")
    final = state_fingerprint(student)
    assert init!=final and len(summary)==UPDATES
    training.write(target/"report.json",dict(model_parameters=sum(p.numel() for p in student.parameters()),
        mode=name,initial_core_sha256=init,final_core_sha256=final,actual_groups=len(summary),status="COMPLETE",
        allocated_peak_bytes=torch.cuda.max_memory_allocated(),reserved_peak_bytes=torch.cuda.max_memory_reserved(),
        process_GPU_scope="TORCH_ALLOCATOR_DURING_THIS_CHILD",wall_seconds=time.monotonic()-started,gpu_entry=device,
        checkpoint_writes=0,existing_pretrained_loads=0,profile_sha256=training.digest(PROFILE)))


def run():
    verify()
    assert time.time()+1920<training.CUTOFF
    receipts = {}
    for name in ARMS:
        try:
            child = subprocess.run([sys.executable,"-B","-u","-m","scripts.diag_p106b_dskd_native_batch_cuda","worker",name],
                cwd=ROOT,timeout=900)
            result = child.returncode
        except subprocess.TimeoutExpired:
            result = 124
        receipts[name] = dict(exit=result,report=(OUT/name/"report.json").is_file())
    verify()
    complete = all(state["exit"]==0 and state["report"] for state in receipts.values())
    training.write(OUT/"actual.json",dict(tag=TAG,complete=complete,arms=receipts,
        ended_UTC=datetime.now(timezone.utc).isoformat()))
    return 0 if complete else 8


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","check","run","worker"))
    parser.add_argument("arm",nargs="?",choices=ARMS)
    args = parser.parse_args()
    if args.stage=="prepare":
        prepare()
    elif args.stage=="check":
        print("DSKD_NATIVE_CUDA_CHECK",len(verify()["features"]),training.digest(PROFILE),flush=True)
    elif args.stage=="worker":
        worker(args.arm)
    else:
        raise SystemExit(run())
