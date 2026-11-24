"""Compare actual CE and ACTD optimizer updates on a new numeric fixture."""

import argparse
from contextlib import nullcontext
import json
import math
import os
import random
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as training


ROOT = training.ROOT
TAG = "p106b_actd_native_updates_synthetic_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
FIXTURE = OUT / "fixture.json"
CPU_RESULT = OUT / "cpu" / "report.json"
WIDTH, ROWS, BATCH, UPDATES, VOCAB = 128, 7, 4, 3, 257
CE_TARGETS = ROWS * (WIDTH - 9)
SELECTED_ROWS = (0, 2, 4, 6)
POSITIONS = (15, 31, 63, 126)
KD_TARGETS = len(SELECTED_ROWS) * len(POSITIONS)
ARMS = ("ce", "actd")
CAP = 420
SOURCES = (
    "scripts/diag_p106b_actd_native_updates.py", "scripts/diag_p013_native_matched_training.py",
    "scripts/p106b_actd_consumer.py", "scripts/p106b_actd_anchor.py",
    "scripts/p107_scaled_optimizer_group.py", "scripts/interactive_research_infer.py",
    "tinylm/train/mtp_sft.py", "tinylm/train/experimental_optimizers.py", "tinylm/train/muon.py",
    "tinylm/train/anneal_schedule.py", "tinylm/config.py", "tinylm/model/transformer.py",
    "tinylm/model/modules.py", "tinylm/model/ternary.py",
)


def pins():
    return {path: training.digest(ROOT / path) for path in SOURCES}


def make_fixture():
    rng = random.Random(246681)
    groups = []
    for _ in range(UPDATES):
        rows = []
        for i in range(ROWS):
            ids = [rng.randrange(3, VOCAB) for _ in range(WIDTH)]
            positions = []
            if i in SELECTED_ROWS:
                for j in POSITIONS:
                    target = ids[j + 1]
                    ordinary = [token for token in range(3, VOCAB) if token != target]
                    anchors = [target, target, *rng.sample(ordinary, 126)]
                    positions.append(dict(student_prefix_raw_index=j, student_target_raw_index=j+1,
                        student_target_id=target, owner=1, distribution=dict(accepted=True,
                            anchor_ids=anchors,native_logits=[-k / 16 for k in range(128)])))
            rows.append(dict(ids=ids, positions=positions))
        groups.append(rows)
    return groups


def verify():
    profile = json.loads(PROFILE.read_bytes())
    assert profile["sources"] == pins() and profile["fixture_sha256"] == training.digest(FIXTURE)
    data = json.loads(FIXTURE.read_bytes())
    assert data == make_fixture()
    return data


def prepare_cpu():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    OUT.mkdir(exist_ok=False)
    training.write(FIXTURE, make_fixture())
    training.write(PROFILE, dict(tag=TAG,sources=pins(),fixture_sha256=training.digest(FIXTURE),
        shape=dict(width=WIDTH,real_rows=ROWS,batch=BATCH,ce_per_group=CE_TARGETS,kd_per_group=KD_TARGETS),
        weight=.3,updates_per_arm=UPDATES,data_type="NEW_SYNTHETIC_NUMERIC_IDS",gpu_child_cap=CAP,
        old_evaluations=0,old_checkpoint_loads=0))
    folder = CPU_RESULT.parent
    folder.mkdir(exist_ok=False)
    data = verify()
    results = {arm: train_arm(arm, data, "cpu", folder / arm, None) for arm in ARMS}
    compare(results)
    verify()
    training.write(CPU_RESULT, dict(complete=True,arms=results,profile_sha256=training.digest(PROFILE)))
    print("ACTD_UPDATE_CPU", training.digest(PROFILE), CE_TARGETS, KD_TARGETS, flush=True)


def compare(results):
    a,b = (results[name] for name in ARMS)
    assert a["initial_core_sha256"] == b["initial_core_sha256"]
    assert a["final_core_sha256"] != b["final_core_sha256"]
    assert a["groups"][0]["ce_sum"] == b["groups"][0]["ce_sum"]
    assert all(row["actd_positions"] == 0 for row in a["groups"])
    assert all(row["actd_positions"] == KD_TARGETS for row in b["groups"])


def train_arm(arm, data, device, folder, gpu_entry):
    import torch
    from scripts.interactive_research_infer import state_fingerprint
    from scripts.p106b_actd_consumer import components
    from scripts.p107_scaled_optimizer_group import ScaleConfig, ScaledOptimizerGroup
    from tinylm.config import TMTConfig, build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.anneal_schedule import lr_factor
    from tinylm.train.experimental_optimizers import build_experimental_optimizers
    from tinylm.train.mtp_sft import Record, pad_records

    folder.mkdir(exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    gpu = device == "cuda"
    synchronize = torch.cuda.synchronize if gpu else lambda: None
    if gpu:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.reset_peak_memory_stats()
        cfg = build_config("m100s10", "dense", WIDTH, True)
        assert (cfg.dim,cfg.n_layers,cfg.vocab_size) == (768,14,32768)
    else:
        assert not torch.cuda.is_initialized()
        cfg = TMTConfig(vocab_size=VOCAB,dim=32,ffn_dim=64,n_q_heads=4,n_kv_heads=2,
            emb_rank=8,n_prelude=1,n_middle=2,n_coda=1,mlp_group=1,tie_mlp=False,
            micro_group=8,max_seq_len=WIDTH,grad_checkpoint=False,quantize_embedding=False,quant_anneal=1.)
    model = TiedMLPTransformer(cfg).to(device).train()
    model.set_anneal(1.0)
    initial = state_fingerprint(model)
    parameters = [p for p in model.parameters() if p.requires_grad]
    if gpu:
        route = build_experimental_optimizers(model,"muon_matched",lr=6e-4,matrix_lr_mult=1.)
        optimizers = (route.matrix, route.adamw)
    else:
        optimizers = (torch.optim.AdamW(parameters,lr=6e-4,foreach=False,fused=False),)
    rates = [[g["lr"] for g in optimizer.param_groups] for optimizer in optimizers]
    scaler = ScaledOptimizerGroup(parameters,optimizers,run_signature=training.digest(PROFILE),
        expected_backwards=2,config=ScaleConfig(init_scale=128.,growth_interval=2))

    summary = []
    started = time.monotonic()
    for ordinal, group in enumerate(data):
        if gpu and (time.monotonic()-started>CAP-30 or (OUT/"STOP").exists()):
            raise TimeoutError("ACTD owned budget or stop")
        count = dict(ce_sum=0.,anchor_sum=0.,residual_sum=0.,ce_targets=0,actd_positions=0,loss=0.)
        factor = lr_factor(ordinal,1,UPDATES,"cosine",.2)
        for optimizer,base in zip(optimizers,rates,strict=True):
            for g,lr in zip(optimizer.param_groups,base,strict=True):
                g["lr"] = factor * lr
        synchronize()
        begin = time.monotonic()
        for i in range(0, ROWS, BATCH):
            rows = group[i:i+BATCH]
            records = [Record(r["ids"][:-1],[-100]*8+r["ids"][9:],[0]*8+[1]*(WIDTH-9)) for r in rows]
            x,y,segments = pad_records(records,0,device,fixed_width=WIDTH,batch_size=BATCH)
            positions = [dict(p,batch_row=k) for k,row in enumerate(rows) for p in row["positions"]]
            precision = torch.autocast("cuda",dtype=torch.bfloat16) if gpu else nullcontext()
            with precision:
                hidden = model(x,return_hidden=True)
                terms = components(model,hidden,y,segments,positions,ce_denominator=CE_TARGETS,
                    actd_denominator=KD_TARGETS,enable_actd=arm=="actd",chunk=64,checkpoint_heads=True)
                loss = terms["ce_sum"] / CE_TARGETS
                if arm == "actd":
                    loss = loss + .3 * (terms["anchor_sum"] + terms["residual_sum"]) / KD_TARGETS
            scaler.backward(loss)
            for key in ("ce_sum","anchor_sum","residual_sum"):
                count[key] += float(terms[key].detach())
            for key in ("ce_targets","actd_positions"):
                count[key] += terms[key]
            count["loss"] += float(loss.detach())
            del x,y,segments,hidden,terms,loss
        synchronize()
        after_gradients = time.monotonic()
        status = scaler.finish(clip_norm=1.)
        synchronize()
        assert count["ce_targets"] == CE_TARGETS and count["actd_positions"] == (KD_TARGETS if arm=="actd" else 0)
        expected = count["ce_sum"]/CE_TARGETS + .3*(count["anchor_sum"]+count["residual_sum"])/KD_TARGETS
        assert math.isclose(expected,count["loss"],rel_tol=2e-6) and status["status"] == "STEPPED_ALL"
        assert status["backward_calls"] == 2 and status["optimizer_step_calls"] == len(optimizers)
        event = dict(ordinal=ordinal,lr_factor=factor,forward_backward_seconds=after_gradients-begin,
            optimizer_seconds=time.monotonic()-after_gradients,update=status,**count)
        training.write(folder / f"update_{ordinal}.json", event)
        summary.append(event)
        print("ACTD_UPDATE",device,arm,ordinal,count["ce_targets"],count["actd_positions"],flush=True)
    final = state_fingerprint(model)
    assert final != initial and len(summary) == UPDATES
    result = dict(arm=arm,device=device,initial_core_sha256=initial,final_core_sha256=final,groups=summary,
        parameters=sum(p.numel() for p in model.parameters()),profile_sha256=training.digest(PROFILE),
        wall_seconds=time.monotonic()-started,peak_allocated_bytes=torch.cuda.max_memory_allocated() if gpu else 0,
        peak_reserved_bytes=torch.cuda.max_memory_reserved() if gpu else 0,gpu_entry=gpu_entry,
        teacher_model_loads=0,checkpoints_written=0)
    training.write(folder / "report.json",result)
    return result


def read_cpu():
    cpu = json.loads(CPU_RESULT.read_bytes())
    assert cpu["complete"] is True and cpu["profile_sha256"] == training.digest(PROFILE)
    compare(cpu["arms"])
    return training.digest(CPU_RESULT)


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0" and time.time()+2*CAP+120<training.CUTOFF
    verify()
    cpu_sha = read_cpu()
    folder = OUT / "cuda"
    folder.mkdir(exist_ok=False)
    terminal, reports = {}, {}
    for arm in ARMS:
        require_idle_gpu()
        argv = [sys.executable,"-B","-u","-m","scripts.diag_p106b_actd_native_updates","worker",arm]
        try:
            code = subprocess.run(argv,cwd=ROOT,timeout=CAP).returncode
        except subprocess.TimeoutExpired:
            code = 124
        vm = require_idle_gpu()
        path = folder / arm / "report.json"
        terminal[arm] = dict(exit=code,after_child_exit=vm,report_sha256=training.digest(path) if path.is_file() else None)
        if code == 0 and path.is_file():
            reports[arm] = json.loads(path.read_bytes())
    complete = set(reports) == set(ARMS)
    training.write(folder / "terminal.json",dict(arms=terminal,cpu_report_sha256=cpu_sha,all_reports=complete))
    verify()
    if not complete:
        return 8
    compare(reports)
    training.write(folder / "report.json",dict(complete=True,profile_sha256=training.digest(PROFILE),arms=reports))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare-cpu","check","run","worker"))
    parser.add_argument("arm",nargs="?",choices=ARMS)
    args = parser.parse_args()
    if (args.phase=="worker") != (args.arm is not None):
        parser.error("only a worker accepts an arm")
    if args.phase=="prepare-cpu":
        prepare_cpu()
    elif args.phase=="check":
        verify()
        print("ACTD_UPDATE_CHECK",training.digest(PROFILE),read_cpu(),flush=True)
    elif args.phase=="worker":
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
        train_arm(args.arm,verify(),"cuda",OUT/"cuda"/args.arm,training.reserve_device())
    else:
        raise SystemExit(run())


if __name__=="__main__":
    main()
