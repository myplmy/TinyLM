"""Exercise the current consumed-group scaler and three masking modes on CUDA."""

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as training
from scripts.p107_active_optimizer_groups import keep_active_groups


TAG = "p107_native_scaled_uniform_observe_adaptive_v1_20261118"
OUT = training.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
MODES = ("uniform", "observe", "adaptive")
BATCH, WIDTH, MICROS, UPDATES, VOCAB = 4, 128, 4, 6, 32768
CAP = 300
SOURCES = (
    "scripts/diag_p107_native_scaled_training.py", "scripts/diag_p013_native_matched_training.py",
    "scripts/p107_active_optimizer_groups.py", "scripts/p107_scaled_optimizer_group.py",
    "scripts/interactive_research_infer.py", "scripts/p108_weight_space.py", "tinylm/train/document_source.py",
    "tinylm/train/hybrid_mntp.py", "tinylm/train/adaptive_masking.py", "tinylm/train/adaptive_training.py",
    "tinylm/train/hybrid_session.py", "tinylm/train/anneal_schedule.py", "tinylm/train/experimental_optimizers.py",
    "tinylm/train/muon.py", "tinylm/config.py", "tinylm/model/transformer.py", "tinylm/model/ternary.py",
)


def pins():
    return {name: training.digest(training.ROOT / name) for name in SOURCES}


def documents():
    import torch

    def generated(count, seed):
        rng = torch.Generator(device="cpu").manual_seed(seed)
        base = torch.randint(0,128,(count,129),generator=rng)
        companion = (base * 29 + 17) % 128 + 128
        return torch.stack((base,companion),dim=2).reshape(count,-1)[:, :257] + 35
    return generated(64,27819),generated(4,19673)


def make_source(data):
    from tinylm.train.document_source import ExplicitDocumentSource

    return ExplicitDocumentSource(list(data),[f"authored-{i:02d}" for i in range(len(data))],
        batch=BATCH,length=WIDTH,micros=MICROS,vocab=VOCAB,seed=1337)


def fixture_proof():
    import torch
    from scripts.p108_weight_space import tensor_sha
    from tinylm.train.hybrid_mntp import causal_batch

    data, validation = documents()
    assert len({tensor_sha(t) for t in (*data,*validation)}) == len(data)+len(validation)
    source = make_source(data)
    updates = []
    for _ in range(UPDATES):
        pairs = source.next_update()
        causal_targets = sum(causal_batch(x,docs,vocab_size=VOCAB).target_count for x,docs in pairs[:MICROS//2])
        assert causal_targets == (MICROS//2)*BATCH*WIDTH
        updates.append(dict(causal_targets=causal_targets,source_rng=tensor_sha(source.rng.get_state()),
            inputs=[tensor_sha(torch.stack((x,docs))) for x,docs in pairs]))
    return dict(source=source.contract,validation_sha256=tensor_sha(validation),updates=updates)


def prepare():
    import torch

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    proof = fixture_proof()
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    training.write(PROFILE,dict(tag=TAG,sources=pins(),inputs=proof,modes=MODES,arm_cap=CAP,updates=UPDATES))
    print("P107_NATIVE_SCALED_PREPARED",training.digest(PROFILE),len(proof["updates"]),flush=True)


def verify():
    profile = json.loads(PROFILE.read_bytes())
    assert profile["sources"] == pins() and profile["modes"] == list(MODES) and profile["updates"] == UPDATES
    return profile


def worker(mode):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.interactive_research_infer import state_fingerprint
    from scripts.p107_scaled_optimizer_group import ScaleConfig, ScaledOptimizerGroup
    from scripts.p108_weight_space import tensor_sha
    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.adaptive_masking import PolicyConfig
    from tinylm.train.adaptive_training import AdaptiveMNTPTrainer, CONSUME_SCALED_GROUP
    from tinylm.train.experimental_optimizers import build_experimental_optimizers
    from tinylm.train.hybrid_mntp import causal_batch, objective_mean
    from tinylm.train.hybrid_session import HybridTrainingSession

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
    entry = training.reserve_device()
    profile = verify()
    assert fixture_proof() == profile["inputs"]
    started = time.monotonic()
    folder = OUT / mode
    folder.mkdir(exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    cfg = build_config("m100s10","dense",WIDTH,True)
    model = TiedMLPTransformer(cfg).cuda().train()
    model.set_anneal(1.)
    initial = state_fingerprint(model)
    route = build_experimental_optimizers(model,"muon_matched",lr=6e-4,matrix_lr_mult=1.)
    optimizers = (route.matrix,route.adamw)
    assert keep_active_groups(optimizers) == [0,2]
    train, validation = documents()
    source = make_source(train)
    assert source.contract == profile["inputs"]["source"]
    signature = training.digest(PROFILE)
    policy = PolicyConfig(VOCAB,.15,.2,2,"keep",1337,34,13,source.corpus_sha256,signature)
    def scaler():
        return ScaledOptimizerGroup([p for p in model.parameters() if p.requires_grad],optimizers,
            run_signature=signature,expected_backwards=MICROS,config=ScaleConfig(init_scale=128.,growth_interval=2))
    trainer = AdaptiveMNTPTrainer(model,optimizers,source,policy_config=policy,mode=mode,masked_micros=MICROS//2,
        signature=signature,collect_ids=lambda logits,_:logits.argmax(-1).detach().cpu(),
        autocast_dtype=torch.bfloat16,scaled_group_factory=scaler,overflow_policy=CONSUME_SCALED_GROUP)
    session = HybridTrainingSession(trainer,total_updates=UPDATES,warmup_updates=1,schedule="cosine")
    ids = validation[:, :WIDTH+1].contiguous()
    val_batch = causal_batch(ids,torch.arange(BATCH)[:,None].expand_as(ids).contiguous(),vocab_size=VOCAB)

    def val():
        model.eval()
        model.clear_quant()
        with torch.no_grad(),torch.autocast("cuda",dtype=torch.bfloat16):
            logits = model(val_batch.inputs.cuda(),attention_mask=val_batch.attention_mask.cuda())
            ce,count = objective_mean(logits,val_batch.targets.cuda())
        model.train()
        model.clear_quant()
        return dict(ce=float(ce),targets=count,synthetic_only=True)

    records = []
    with sdpa_kernel(SDPBackend.MATH):
        before = val()
        for ordinal, expected in enumerate(profile["inputs"]["updates"]):
            if (OUT / "STOP").exists() or time.monotonic()-started>CAP-25:
                raise TimeoutError("owned stop or CUDA time limit")
            row = session.update()
            assert row["update"] == ordinal and row["causal_targets"] == expected["causal_targets"]
            assert row["masked_targets"] > 0 and math.isfinite(row["loss"])
            assert row["optimizer_applied"] and row["optimizer_groups_applied"] == ordinal+1
            assert source.cursor == ordinal+1 and tensor_sha(source.rng.get_state()) == expected["source_rng"]
            assert row["scaled_optimizer_group"]["backward_calls"] == MICROS and row["optimizer_groups_skipped"] == 0
            training.write(folder / f"update_{ordinal}.json",row)
            records.append(row)
            print("P107_NATIVE_SCALED_UPDATE",mode,ordinal,row["masked_targets"],flush=True)
        after = val()
    assert before["targets"] == after["targets"] == BATCH*WIDTH
    final = state_fingerprint(model)
    assert initial != final
    training.write(folder / "report.json",dict(mode=mode,initial_sha256=initial,final_sha256=final,
        parameters=sum(p.numel() for p in model.parameters()),validation_before=before,validation_after=after,
        total_groups=source.cursor,updates=records,entry=entry,wall_seconds=time.monotonic()-started,
        max_allocated_bytes=torch.cuda.max_memory_allocated(),max_reserved_bytes=torch.cuda.max_memory_reserved(),
        old_checkpoint_reads=0,checkpoint_writes=0,profile_sha256=signature))


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    assert time.time()+len(MODES)*CAP+120<training.CUTOFF and os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
    verify()
    finished, reports = {},{}
    for mode in MODES:
        require_idle_gpu()
        argv = [sys.executable,"-B","-u","-m","scripts.diag_p107_native_scaled_training","worker",mode]
        try:
            code = subprocess.run(argv,cwd=training.ROOT,timeout=CAP).returncode
        except subprocess.TimeoutExpired:
            code = 124
        path = OUT / mode / "report.json"
        finished[mode] = dict(exit=code,after_exit=require_idle_gpu(),report_sha256=training.digest(path) if path.is_file() else None)
        if code == 0 and path.is_file():
            reports[mode] = json.loads(path.read_bytes())
    verify()
    complete = set(reports) == set(MODES)
    training.write(OUT / "terminal.json",dict(complete_workers=complete,arms=finished))
    if not complete:
        return 8
    assert len({r["initial_sha256"] for r in reports.values()}) == 1
    assert max(r["validation_before"]["ce"] for r in reports.values())-min(r["validation_before"]["ce"] for r in reports.values())<1e-6
    training.write(OUT / "report.json",dict(complete=True,arms=reports,
        uniform_observe_final_exact=reports["uniform"]["final_sha256"]==reports["observe"]["final_sha256"],
        controlled_validation_sha256=verify()["inputs"]["validation_sha256"]))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","run","worker"))
    parser.add_argument("mode",nargs="?",choices=MODES)
    args = parser.parse_args()
    if (args.stage=="worker") != (args.mode is not None):
        parser.error("only workers receive a masking mode")
    handlers = {"prepare":prepare,"run":run,"worker":lambda:worker(args.mode)}
    raise SystemExit(handlers[args.stage]())
