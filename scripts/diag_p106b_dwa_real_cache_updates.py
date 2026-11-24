"""Apply the existing per-document DWA objective to matched batched Native updates."""

import argparse
from collections import Counter
from datetime import datetime
import gc
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from scripts import diag_p106b_dskdv2_real_cache_updates as dskd
from scripts import interactive_research_infer as manual
from scripts.p106b_dskdv2_recovery import feature_contract


actd, sampling = dskd.actd, dskd.sampling
ROOT, EVIDENCE = dskd.ROOT, dskd.EVIDENCE
TAG = "p106b_dwa_real_cache_updates_v1_20261119"
OUT = EVIDENCE / TAG
PROFILE = OUT / "profile.json"
PAST = EVIDENCE / "p106b_dwa_native_v3_20261117_s1337"
SHAPES = ROOT / "handoff/audit/research_20261118_01a1e647/DWA_REAL128_GROUP_SHAPE_READBACK_v1.json"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
SEED, RATE, LR = 1337, .15, 1e-5
SOURCE_LOG = ROOT / "test_result/101_log_20261117_P106B_Stage7dwa1Wd1_native_detail_v3.txt"


def gate(reserve=0):
    if (END - datetime.now(END.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 time window or local stop reached")


def projectors(torch):
    widths = (("query", 1536, 2048), ("t2s", 1024, 768), ("s2t", 768, 1024), ("embedding_t2s", 1024, 768))
    with torch.device("cpu"), torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(SEED)
        return torch.nn.ModuleDict({name: torch.nn.Linear(dim_in, dim_out, bias=False)
                                    for name, dim_in, dim_out in widths})


def collect():
    earlier = actd.read(dskd.PROFILE)
    previous = actd.read(dskd.OUT / "report.json")
    base = previous["arms"]["ce"]
    source = earlier["inputs"]
    if (previous["profile_sha256"] != manual.file_sha(dskd.PROFILE)
            or not previous["source_preserved"] or base["optimizer_steps"] != [4]
            or (source["batch"], source["accum"], source["width"], source["lr"]) != (8, 4, 1024, LR)):
        raise ValueError("A closed CE-only result at the matched configuration is required")
    actd.verify_selected_checkpoint(source["student"])
    if dskd.file_stamp(Path(source["teacher_head"])) != source["teacher_asset_stamp"]:
        raise ValueError("Original full teacher asset is different from the previous verified instance")
    prior_policy = actd.read(PAST / "profile.json")
    prior_report = actd.read(PAST / "actual/report.json")
    shapes = actd.read(SHAPES)
    if (prior_report["returncode"] != 0 or len(prior_report["blocks"]) != 1
            or not prior_report["blocks"][0]["repeat_gradient_exact"]
            or not prior_report["sources_assets_inputs_unchanged"] or prior_report["closure_errors"]
            or shapes["source_report_sha256"] != manual.file_sha(PAST / "actual/report.json")
            or prior_report["student_initial_core_sha256"] != base["initial"]):
        raise ValueError("Original completed DWA details and matched student are required")
    prepared_path = actd.SOURCE / "profile.json"
    prepared = actd.read(prepared_path)
    rows = list(actd.read_shards(actd.SOURCE, prepared["prepared_manifest"]))
    if [row["row_id"] for row in rows] != prior_policy["row_ids"] or len(rows) != 128:
        raise ValueError("Exact original ordered 128 rows are required")
    feature_path = dskd.RECOVERY / "features_manifest.json"
    features = {entry["row_id"]: entry for entry in actd.read(feature_path)["features"]}
    groups = []
    for row in rows:
        path = ROOT / features[row["row_id"]]["path"]
        if path != dskd.FEATURES / (row["row_id"] + ".npy") or path.is_symlink():
            raise ValueError("Exact recovered native feature path required")
        array = np.load(path, allow_pickle=False, mmap_mode="r")
        teacher = row["teacher"]
        feature_contract(array, tokens=len(teacher["ids"])-1)
        native = row["packed"]["student"]
        if any((label != -100) != keep or (keep and label != token)
               for label, keep, token in zip(native["labels"], native["supervised"], native["ids"], strict=True)):
            raise ValueError("Original student target mask and labels differ")
        groups.append((native, teacher, array))
    groups = [groups[begin:begin+32] for begin in range(0, 128, 32)]
    groups_counts = [dict(student=sum(sum(native["supervised"][1:]) for native, _, _ in group),
                          teacher=sum(sum(teacher["supervised"][1:]) for _, teacher, _ in group))
                     for group in groups]
    if groups_counts != [{name: entry[name] for name in ("student", "teacher")}
                         for entry in shapes["grouped_in_original_order"]]:
        raise ValueError("Per-group original predictor counts differ from the independent CPU audit")

    pins = dict(source["source_pins"])
    files = [Path(__file__).resolve(), dskd.PROFILE, dskd.OUT / "report.json", SHAPES, SOURCE_LOG,
             PAST / "profile.json", PAST / "actual/report.json"]
    files.extend(ROOT / name for name in ("scripts/p106b_dwa_cma.py", "scripts/p106b_dwa_native.py",
                                         "scripts/p106b_softdtw_triton_v2.py"))
    pins.update({path.relative_to(ROOT).as_posix(): manual.file_sha(path) for path in files})
    if any(manual.file_sha(ROOT / path) != digest for path, digest in pins.items()):
        raise ValueError("Previously verified feature, code or initial student proof differs")
    policy = prior_policy["policy"]
    profile = dict(tag=TAG, user_directive=177, end=END.isoformat(), sources=pins,
                   plan_sha256=manual.file_sha(actd.PLAN), teacher_head=source["teacher_head"],
                   teacher_head_key=source["teacher_head_key"], teacher_asset_stamp=source["teacher_asset_stamp"],
                   teacher_asset_sha256=source["teacher_asset_sha256"], student=source["student"],
                   projector_initial=prior_report["projector_initial_state_sha256"],
                   previous_ce_first=base["history"][0]["ce_sum"], previous_ce_final=base["final"],
                   counts=groups_counts, gamma=policy["gamma"], band=policy["band"],
                   confidence=policy["confidence_gate_scale"], rate=RATE, lr=LR,
                   batch=8, accum=4, width=1024, updates=4, corpus_admitted=False)
    return profile, groups


def prepare():
    import torch

    gate()
    profile, _ = collect()
    bank = projectors(torch)
    if manual.state_fingerprint(bank) != profile["projector_initial"] or torch.cuda.is_initialized():
        raise ValueError("Initial projector CPU state differs from the established original")
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(actd.PLAN.read_bytes())
    actd.native.write(PROFILE, profile)
    verify()
    print("DWA_REAL_PREFLIGHT", profile["counts"], profile["projector_initial"][:12], flush=True)


def verify():
    sealed = actd.read(PROFILE)
    now, groups = collect()
    if sealed != now:
        raise ValueError("The sealed exact inputs or model changed")
    return now, groups


def train(profile, groups):
    import torch
    from torch.nn import functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.p106b_actd_consumer import components
    from scripts.p106b_dskdv2_bridge import teacher_logits
    from scripts.p106b_dwa_cma import loss_components
    from scripts.p106b_dwa_native import predictor_view, streaming_share
    from scripts.p106b_softdtw_triton_v2 import soft_dtw
    from tinylm.train.mtp_sft import Record, pad_records

    model = actd.load_student(profile["student"])
    initial = manual.state_fingerprint(model)
    model.cfg.grad_checkpoint = True
    model.cuda().train()
    torch.manual_seed(SEED)
    bank = projectors(torch)
    if manual.state_fingerprint(bank) != profile["projector_initial"] or initial != profile["student"]["core_sha256"]:
        raise ValueError("Initial student and DWA projectors do not match")
    bank.cuda()
    head = dskd.load_head(profile).cuda()
    parameters = [p for p in model.parameters() if p.requires_grad] + list(bank.parameters())
    opt = torch.optim.AdamW(parameters, lr=LR, betas=(.9, .95), weight_decay=0., foreach=False, fused=False)
    torch.cuda.reset_peak_memory_stats()
    history = []

    def embed(ids):
        return F.linear(F.embedding(ids, model._emb_w()), model._emb_up_w())

    def align(cost):
        return soft_dtw(cost.double().contiguous(), gamma=profile["gamma"])

    for step, (group, counts) in enumerate(zip(groups, profile["counts"], strict=True), 1):
        gate(15)
        opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        start = time.perf_counter()
        observed = Counter()
        student_head = model._emb_w().detach() @ model._emb_up_w().detach().T
        for i in range(0, len(group), profile["batch"]):
            rows = group[i:i+profile["batch"]]
            records = [Record(native["ids"][:-1], native["labels"][1:], native["turn_ids"][1:])
                       for native, _, _ in rows]
            x, y, segment = pad_records(records, 0, "cuda", fixed_width=profile["width"], batch_size=profile["batch"])
            with sdpa_kernel(SDPBackend.MATH):
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    hidden = model(x, return_hidden=True)
                    ce = components(model, hidden, y, segment, [], ce_denominator=counts["student"],
                                    actd_denominator=counts["teacher"], enable_actd=False)
                loss = ce["loss"]
                observed.update(ce=ce["ce_targets"], ce_sum=ce["ce_sum"].detach().item())
                for j, (native, old_teacher, array) in enumerate(rows):
                    sv = predictor_view(torch, native["ids"], native["supervised"],
                                        hidden[j, :len(native["ids"])-1].float(), embed)
                    with torch.no_grad():
                        tv = predictor_view(torch, old_teacher["ids"], old_teacher["supervised"],
                                            torch.from_numpy(array.copy()).cuda(),
                                            lambda ids: F.embedding(ids, head))
                        tl = teacher_logits(tv.hidden, head)
                    sl = model._head_logits(sv.hidden)
                    packet = loss_components(torch, sv, tv, sl, tl, **bank, student_head=student_head,
                                             teacher_head=head, kd_gate_scale=profile["confidence"],
                                             dtw=align, band=profile["band"])
                    loss = loss + streaming_share(packet, global_student_targets=counts["student"],
                                                  ce_rate=0., kd_rate=RATE, dtw_rate=RATE)
                    observed.update(student=sv.count, teacher=tv.count, cross_cells=sv.count*tv.count)
                    observed.update({k: v.detach().item() for k, v in packet["raw"].items()})
                    del sv, tv, sl, tl, packet
                loss.backward()
            del x, y, segment, hidden, ce, loss
        if (observed["ce"], observed["student"], observed["teacher"]) != (
                counts["student"], counts["student"], counts["teacher"]):
            raise ValueError("DWA and the matched CE did not preserve the exact original positions")
        if step == 1 and observed["ce_sum"] != profile["previous_ce_first"]:
            raise ValueError("Prior matched CE result cannot be reused with this body/label path")
        gradients = [p.grad.detach() for p in parameters if p.grad is not None]
        grad_max = torch.stack(torch._foreach_norm(gradients, float("inf"))).max().item()
        norm = torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True).item()
        if not norm > 0 or head.grad is not None or any(w.grad is None for w in bank.parameters()):
            raise ValueError("Gradient ownership differs from the intended four-projector objective")
        opt.step()
        torch.cuda.synchronize()
        row = dict(observed, step=step, norm=norm, grad_max=grad_max, seconds=time.perf_counter()-start)
        history.append(row)
        print("DWA_REAL_UPDATE", step, observed["ce"], observed["teacher"], norm, row["seconds"], flush=True)
    final, projector = manual.state_fingerprint(model), manual.state_fingerprint(bank)
    steps = sorted({int(state["step"].item()) for state in opt.state.values()})
    if (final in (initial, profile["previous_ce_final"]) or projector == profile["projector_initial"]
            or steps != [4] or sum(row["cross_cells"] for row in history) != 6823):
        raise ValueError("Actual optimizer updates and nonpadded cross geometry must be observed")
    return dict(initial=initial, final=final, initial_projector=profile["projector_initial"],
                final_projector=projector, projector_parameters=sum(p.numel() for p in bank.parameters()),
                optimizer_steps=steps, history=history, training_peak=dict(
                    allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved()))


def run():
    import torch
    from scripts.diag_p107_hybrid_mntp import close_owned_cuda

    gate(180)
    profile, groups = verify()
    point = manual.require_idle_gpu()
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 10 * (1 << 30):
        raise MemoryError("A single device with at least 10 GiB free is required")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    physical = OUT / "device_100ms.csv"
    with physical.open("xb") as stream:
        monitor = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=stream)
        try:
            result = train(profile, groups)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    samples = sampling.read_samples(physical)
    gc.collect()
    close_owned_cuda(torch, result)
    checkpoint = ROOT / profile["student"]["checkpoint"]["path"]
    immutable = (all(manual.file_sha(ROOT / path) == digest for path, digest in profile["sources"].items())
                 and manual.file_sha(checkpoint) == profile["student"]["checkpoint"]["sha256"]
                 and dskd.file_stamp(Path(profile["teacher_head"])) == profile["teacher_asset_stamp"])
    if not immutable:
        raise ValueError("Immutable teacher or student provenance changed")
    result.update(profile_sha256=manual.file_sha(PROFILE), entry_device=point,
                  source_preserved=True, checkpoint_writes=0, teacher_body_calls=0,
                  ce_replayed_updates=0, device_samples=len(samples),
                  device_peak=max(samples, key=lambda row: row["occupied_mib"]))
    actd.native.write(OUT / "report.json", result)
    print("DWA_REAL_RESULT", result["optimizer_steps"], result["projector_parameters"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual"))
    phase = parser.parse_args().phase
    expected = "" if phase == "prepare" else "0"
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use the isolated CPU or the authorized single GPU")
    if expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS is required")
    (prepare if phase == "prepare" else run)()


if __name__ == "__main__":
    main()
