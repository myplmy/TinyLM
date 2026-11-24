"""Isolate matched author-optimizer costs using one reproduced P109 G4 gradient."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p013_p109_actual_optimizer as training
from scripts.diag_p107_hybrid_mntp import close_owned_cuda


base, student = training.base, training.prior
ROOT, read, write, sha = base.ROOT, training.read, training.write, training.sha
TAG = "p005b_g4_author_optimizer_step_cost_v1_20261119"
OUT = training.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
PLAN = ROOT / "test_plan/P005b_Muon-레시피-정렬과-QK-norm-상한.md"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
LIMIT, STEPS, SEED = 100, 6, 2027
METHODS = (training.MUON, training.NOR, training.ADA)


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(END.tzinfo) + timedelta(seconds=reserve) >= END:
        raise RuntimeError("owned STOP or deadline")


def guard():
    gate()
    free, total = torch.cuda.mem_get_info()
    if total - free > 13_000_000_000:
        raise RuntimeError("card occupancy exceeded the 13 GB ceiling")


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == 177
    assert all(sha(ROOT / name) == digest for name, digest in profile["pins"].items())


def prepare():
    old_profile, _, xs, ys, _, draws = training.prepared()
    paths = [training.OUT / f"seed_{SEED}_{method}.json" for method in METHODS]
    past = [read(path) for path in paths]
    reference = read(training.OUT / "profile.json")
    for key in ("parent_sha256", "tokenizer_sha256", "common_arrays_sha256", "initial_model_sha256", "draws"):
        assert old_profile[key] == reference[key], key
    values = [row["history"][0] for row in past]
    assert len({(row["loss"], row["gradient_norm"], row["supervised_targets"]) for row in values}) == 1
    assert len({row["roles_sha256"] for row in past}) == 1
    ids = draws[SEED][0]
    assert int(ys[ids].ne(-100).sum()) == values[0]["supervised_targets"] == 124
    OUT.mkdir()
    sealed = OUT / "plan_at_execution.md"
    _, section = PLAN.read_text(encoding="utf8").split("## 18. ", 1)
    assert TAG in section
    sealed.write_text("## 18. " + section, encoding="utf8")
    pins = dict(old_profile["source_sha256"])
    sources = (Path(__file__).resolve(), sealed, base.STUDENT, student.frozen.prior.PARENT,
               training.OUT / "profile.json", training.OUT / "report.json", *paths)
    pins.update({str(path.relative_to(ROOT)): sha(path) for path in sources})
    profile = dict(tag=TAG, approval=177, pins=pins, steps=STEPS, seed=SEED, ids=ids.tolist(),
                   inputs_sha256=base.state_sha((xs[ids], ys[ids])), first=values[0],
                   initial=reference["initial_model_sha256"], roles=past[0]["roles_sha256"],
                   states={row["method"]: row["optimizer_state_storage_bytes"] for row in past})
    verify(profile)
    write(PROFILE, profile)
    print("G4_AUTHOR_COST_PREPARE", profile["ids"], profile["inputs_sha256"], profile["first"]["supervised_targets"], flush=True)


def capture(profile):
    _, _, xs, ys, _, draws = training.prepared()
    ids = draws[SEED][0]
    assert ids.tolist() == profile["ids"] and base.state_sha((xs[ids], ys[ids])) == profile["inputs_sha256"]
    model = student.initialize()
    assert base.state_sha(model.state_dict()) == profile["initial"]
    labels, inputs = ys[ids].cuda(), xs[ids].cuda()
    with sdpa_kernel(SDPBackend.MATH):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(inputs)
            loss = F.cross_entropy(logits.flatten(0, 1), labels.flatten())
        loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
    assert float(loss.detach()) == profile["first"]["loss"] and float(norm) == profile["first"]["gradient_norm"]
    gradients = {name: value.grad.detach().clone() for name, value in model.named_parameters() if value.grad is not None}
    return gradients


def matrix_fields(optimizer):
    amounts = {}
    for fields in optimizer.state.values():
        for name, tensor in fields.items():
            if isinstance(tensor, torch.Tensor):
                key = f"{name}:{tensor.dtype}"
                amounts[key] = amounts.get(key, 0) + tensor.numel() * tensor.element_size()
    return amounts


def measure(method, gradients, profile):
    model = student.initialize()
    assert base.state_sha(model.state_dict()) == profile["initial"]
    route = student.build_experimental_optimizers(model, method, lr=student.LR, matrix_lr_mult=1.)
    student.keep_active_groups((route.adamw, route.matrix))
    assert base.state_sha(route.manifest["parameters"]) == profile["roles"]
    by_name = dict(model.named_parameters())
    timings = []
    torch.cuda.reset_peak_memory_stats()
    for _ in range(STEPS):
        guard()
        for name, value in gradients.items():
            by_name[name].grad = value.clone()
        torch.cuda.synchronize()
        start = perf_counter()
        route.validate_before_step()
        torch.cuda.synchronize()
        checked = perf_counter()
        route.adamw.step()
        torch.cuda.synchronize()
        auxiliary = perf_counter()
        route.matrix.step()
        torch.cuda.synchronize()
        end = perf_counter()
        timings.append(dict(validate=checked-start, adamw=auxiliary-checked, matrix=end-auxiliary, total=end-start))
        guard()
    state = {key: training.state_storage_bytes(value) for key, value in (("matrix", route.matrix), ("adamw", route.adamw))}
    assert state == profile["states"][method]
    fields = matrix_fields(route.matrix)
    assert sum(fields.values()) == state["matrix"]
    final = base.state_sha(model.state_dict())
    assert final != profile["initial"]
    return dict(method=method, timings=timings, steady_median={key: median(t[key] for t in timings[1:]) for key in timings[0]},
                state=state, matrix_fields=fields, final_weights_sha256=final,
                allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())


def worker(profile):
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12500 * 2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    gradients = capture(profile)
    original = base.state_sha(gradients)
    rows = []
    for method in (*METHODS, *reversed(METHODS)):
        torch.cuda.empty_cache()
        result = measure(method, gradients, profile)
        rows.append(result)
        print("G4_AUTHOR_COST_STEP", method, result["steady_median"], result["matrix_fields"], flush=True)
    assert base.state_sha(gradients) == original
    assert all(rows[i]["final_weights_sha256"] == rows[5-i]["final_weights_sha256"] for i in range(3))
    del gradients
    report = dict(gradient_sha256=original, methods=rows, optimizer_only_steps=STEPS*len(rows),
                  forward_backward_calls=1, training_updates=0, evaluations=0, checkpoint_writes=0)
    close_owned_cuda(torch, report)
    write(OUT / "steps.json", report)


def run(profile):
    assert base.idle(), "GPU has another compute process"
    before = subprocess.check_output(base.DEVICE, text=True, timeout=8).strip()
    raw = OUT / "device_100ms.csv"
    with raw.open("xb") as stream:
        sampler = subprocess.Popen((*base.DEVICE, f"--loop-ms={base.INTERVAL_MS}"), stdout=stream)
        try:
            cmd = ["timeout", "--kill-after=5s", f"{LIMIT}s", sys.executable, "-B", "-m", __spec__.name, "worker"]
            code = subprocess.run(cmd, cwd=ROOT).returncode
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    returned = base.idle()
    after = subprocess.check_output(base.DEVICE, text=True, timeout=8).strip()
    verify(profile)
    samples = base.read_samples(raw)
    report = dict(exit=code, before=before, after=after, returned=returned, sources_preserved=True,
                  peak=max(samples, key=lambda row: row["occupied_mib"]), samples=len(samples))
    write(OUT / "report.json", report)
    print("G4_AUTHOR_COST_RELEASE", report, flush=True)
    if code or not returned:
        raise SystemExit(code or 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    gate(LIMIT + 10 if phase == "run" else 0)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if phase == "prepare":
        prepare()
    elif phase == "run":
        profile = read(PROFILE)
        verify(profile)
        run(profile)
    else:
        worker(read(PROFILE))


if __name__ == "__main__":
    main()
