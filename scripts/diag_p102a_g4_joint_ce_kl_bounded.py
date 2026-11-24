"""Measure bounded backward against the finished 248K 8x1 CE/KL reference."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timedelta
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_g4_joint_ce_kl_batch8 as reference
from scripts import p102a_joint_ce_kl as loss
from scripts import p102a_joint_ce_kl_bounded as bounded
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


prior, joint = reference.prior, reference.joint
ROOT, read, write, sha = prior.ROOT, reference.read, reference.write, reference.sha
TAG = "p102a_g4_joint_ce_kl_bounded_delta_v1_20261119"
OUT = reference.OUT.with_name(TAG)
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
PLAN = ROOT / "test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md"
ARCHIVED = ROOT / "test_result/evidence/p109_qwen35_248k_warm_kl_v1_20261119/joint_head_before.py"
LIMIT = 120


def gate(seconds):
    if datetime.now(END.tzinfo) + timedelta(seconds=seconds) >= END or (OUT / "STOP").exists():
        raise TimeoutError("Current user 177 execution window")


def inputs():
    bank, provenance = prior.frozen_logits(torch)
    bank = bank.float()
    original = prior.crops()
    groups = reference.batch8(original)
    old_profile, old_result = (reference.OUT / name for name in ("profile.json", "report.json"))
    historical = read(old_profile)
    result = read(old_result)
    pinned = historical["previous"]["base"]
    same = (prior.expected(bank, provenance, original) == pinned["base"]
            and reference.capacity.ordered_tokens_sha(groups) == historical["ordered_tokens_sha256"]
            and prior.state_sha(groups) == historical["grouped_sha256"])
    for name, expected in pinned["pins"].items():
        path = ARCHIVED if name == "scripts/p102a_joint_ce_kl.py" else ROOT / name
        if sha(path) != expected:
            raise ValueError(f"Historical source differs: {name}")
    if not same or result["exit"] != 0 or not result["gpu_returned"] or not result["sources_unchanged"]:
        raise ValueError("Matching closed baseline and token draws required")
    files = (Path(__file__), Path(loss.__file__), Path(bounded.__file__),
             Path(reference.__file__), old_result, old_profile, ARCHIVED, PLAN)
    profile = dict(tag=TAG, user_directive=177, cutoff=END.isoformat(),
                   inputs=pinned["base"], ordered_tokens_sha256=historical["ordered_tokens_sha256"],
                   grouped_sha256=historical["grouped_sha256"], micro_bs=8, accum=1, width=512,
                   teacher_storage="GPU_FP32", steps=prior.UPDATES, backward_rows=bounded.VJP_ROWS,
                   loss_rows=prior.ROWS, dtype="BF16", checkpoints=0,
                   source_pins={p.relative_to(ROOT).as_posix(): sha(p) for p in files})
    return profile, bank, groups, result


def head_gate(device):
    spec = importlib.util.spec_from_file_location("p102a_archived_joint", ARCHIVED)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    torch.manual_seed(553)
    cfg = TMTConfig(vocab_size=521, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=32,
                    n_q_heads=4, n_kv_heads=2, n_prelude=1, n_middle=2, n_coda=1,
                    tie_mlp=True, mlp_group=2, micro_group=8)
    model = TiedMLPTransformer(cfg).to(device)
    h = torch.randn(1, 531, 32, device=device, requires_grad=True)
    targets = torch.randint(0, cfg.vocab_size, h.shape[:2], device=device)
    targets[:, ::11] = -100
    teacher = torch.randn(531, cfg.vocab_size, device=device)
    kwargs = dict(temperature=prior.TEMPERATURE, rows=71, full_sum=False)
    params = (h, model.emb.weight, model.emb_up.weight)
    results = {}
    for precision, threshold in (("fp32", 1e-5), ("bf16", .01)):
        by_objective = {}
        for name, weights in (("ce",(1.,0.)), ("kl",(0.,1.)), ("combined",(.7,.3))):
            amp = torch.autocast(device, dtype=torch.bfloat16) if precision == "bf16" else nullcontext()
            with amp:
                a = old.joint_ce_kl(model,h,targets,teacher,**kwargs)
                b = loss.joint_ce_kl(model,h,targets,teacher,**kwargs)
                with patch.object(loss,"_JointHead",bounded.BoundedJointHead):
                    c = loss.joint_ce_kl(model,h,targets,teacher,**kwargs)
                original, expected, actual = [torch.autograd.grad(pair[0]*weights[0]+pair[1]*weights[1],params)
                                              for pair in (a,b,c)]
            forward_equal = all(torch.equal(x,y) and torch.equal(y,z) for x,y,z in zip(a,b,c,strict=True))
            baseline_equal = all(torch.equal(x,y) for x,y in zip(original,expected,strict=True))
            relative = [float(torch.linalg.vector_norm((x-y).float())
                        /torch.linalg.vector_norm(x.float()).clamp_min(1e-20)) for x,y in zip(expected,actual,strict=True)]
            changed = [int(torch.count_nonzero(x.ne(y))) for x,y in zip(expected,actual,strict=True)]
            if not forward_equal or not baseline_equal or max(relative) > threshold:
                raise ValueError(f"{device} {precision} {name}: {forward_equal=} {baseline_equal=} {relative=}")
            by_objective[name] = dict(loss_same=forward_equal, historical_default_same=baseline_equal,
                                      relative_l2=relative, changed_entries=changed)
        results[precision] = by_objective
    return dict(device=device, positions=531, ignored=int(targets.lt(0).sum()),
                head_order=["pre_head_hidden","shared_table","shared_projection"], cases=results)


def worker(bank, groups):
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    result = head_gate("cuda")
    write(OUT / "cuda_head_gate.json", result)
    cleanup = {}
    close_owned_cuda(torch,cleanup)
    with patch.object(loss,"_JointHead",bounded.BoundedJointHead):
        joint.worker(reference.host.REFERENCE_ARM, bank, groups, out=OUT, teacher_storage="cuda")
    closure = {}
    close_owned_cuda(torch,closure)
    write(OUT / "cuda_cleanup.json", closure)


def run(profile, old):
    if not prior.idle():
        raise RuntimeError("The dedicated CUDA device is busy")
    points = OUT / "device_100ms.csv"
    before = subprocess.check_output(reference.DEVICE, text=True, timeout=8)
    with points.open("xb") as stream:
        sampler = subprocess.Popen((*reference.DEVICE, f"--loop-ms={reference.INTERVAL_MS}"), stdout=stream)
        try:
            command = ["timeout", "--kill-after=5s", "95s", sys.executable, "-B", "-u", "-m",
                       "scripts.diag_p102a_g4_joint_ce_kl_bounded", "worker"]
            done = subprocess.run(command, cwd=ROOT, check=False)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    returned = prior.idle()
    after = subprocess.check_output(reference.DEVICE, text=True, timeout=8)
    samples = reference.read_samples(points)
    actual = read(OUT / "chunk_sum.json") if done.returncode == 0 else None
    preserved = all(sha(ROOT / name) == stamp for name,stamp in profile["source_pins"].items())
    comparisons = {}
    if actual is not None:
        control = old["gpu_8x1"]
        if actual["initial"] != control["initial"] or [r["targets"] for r in actual["history"]] != [4096]*prior.UPDATES:
            raise ValueError("Actual initial state or update target counts differ")
        comparisons = dict(loss_history=all(a["micros"]==b["micros"] for a,b in zip(control["history"],actual["history"],strict=True)),
            first_gradient=actual["first_gradient"]==control["first_gradient"], final=actual["final"]==control["final"],
            peak_saved_bytes=control["peak_allocated"]-actual["peak_allocated"],
            median_time_ratio=actual["median_seconds_after_first"]/control["median_seconds_after_first"])
    write(OUT / "report.json", dict(exit=done.returncode, actual=actual, saved_reference=old["gpu_8x1"],
         comparisons=comparisons, peak=max(samples,key=lambda r:r["occupied_mib"]) if samples else None,
         samples=len(samples), old_peak=old["peak_device"], device_before=before.strip(), device_after=after.strip(),
         gpu_returned=returned, sources_preserved=preserved, profile_sha256=sha(OUT / "profile.json")))
    print("P102A_G4_BOUNDED", done.returncode, comparisons, returned, flush=True)
    return done.returncode if done.returncode else (0 if samples and returned and preserved else 8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare","gpu","worker"))
    args = parser.parse_args()
    cpu = args.phase == "prepare"
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != ("" if cpu else "0")
            or not cpu and (os.environ.get("PYTORCH_CUDA_ALLOC_CONF") != prior.ALLOCATOR
                            or os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8")):
        parser.error("Use CPU-only mode or the authorized CUDA device with the pinned allocator")
    gate(LIMIT)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile, bank, groups, old = inputs()
    if cpu:
        result = head_gate("cpu")
        OUT.mkdir()
        (OUT/"plan_at_execution.md").write_bytes(PLAN.read_bytes())
        write(OUT/"profile.json",profile)
        write(OUT/"cpu_head_gate.json",result)
        print("P102A_G4_BOUNDED_CPU",len(result["cases"]),profile["ordered_tokens_sha256"],flush=True)
        return 0
    if (profile != read(OUT/"profile.json")
            or sha(OUT/"plan_at_execution.md") != profile["source_pins"][PLAN.relative_to(ROOT).as_posix()]):
        raise ValueError("Sealed P102A inputs changed")
    return worker(bank, groups) if args.phase == "worker" else run(profile,old)


if __name__ == "__main__":
    raise SystemExit(main())
