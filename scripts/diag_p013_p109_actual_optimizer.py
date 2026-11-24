"""Compare three matrix optimizers on paired warm G4 Korean and English CE."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
from statistics import median
import subprocess
from time import perf_counter

from tokenizers import Tokenizer
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_p109_actual_prefix_kd as prior


TAG = "p013_p109_actual_optimizer_v1_20261119"
OUT = prior.OUT.with_name(TAG)
base, read, write, sha = prior.base, prior.read, prior.write, prior.sha
UPDATES, WARMUP = 88, 4
STAMPS = (0, 8, 16, 24, 32, 48, 64, UPDATES)
MUON, NOR, ADA = "muon_matched", "normuon_author_fp32", "adamuon_author_bf16"
ORDER = {2027: (MUON, NOR, ADA), 2039: (ADA, NOR, MUON)}
SOURCES = (*prior.SOURCES, "tinylm/train/normuon_author.py", "tinylm/train/adamuon_author.py",
           Path(__file__).relative_to(base.ROOT).as_posix())


def prepared():
    profile_path, result_path = prior.OUT / "profile.json", prior.OUT / "report.json"
    previous, report = read(profile_path), read(result_path)
    assert report["source_preserved"]
    baseline = report["arms"]["ce"]
    docs = list(prior.documents())
    assert docs == [{k: v for k, v in doc.items() if k != "teacher_ids"}
                    for doc in previous["data"]["documents"]]
    tokenizer = Tokenizer.from_file(str(base.STUDENT))
    xs = torch.zeros((len(docs), prior.WIDTH), dtype=torch.long)
    ys = torch.full_like(xs, -100)
    for row, doc in enumerate(docs):
        tokens = base.encode(tokenizer, doc["text"])
        count = len(tokens) - 1
        assert 0 < count <= prior.WIDTH
        xs[row, :count] = torch.tensor(tokens[:-1])
        ys[row, :count] = torch.tensor(tokens[1:])
    groups = {lang: torch.tensor([i for i, doc in enumerate(docs)
                                if doc["split"] == "train" and doc["language"] == lang])
              for lang in ("en", "ko")}
    held = torch.tensor([i for i, doc in enumerate(docs) if doc["split"] == "held"])
    train_pool = int(ys[torch.cat(tuple(groups.values()))].ne(-100).sum())
    assert train_pool == previous["data"]["train_ce_pool"]
    draws, draw_receipts = {}, {}
    for seed, order in ORDER.items():
        rng = torch.Generator().manual_seed(seed)
        chosen = [pool[torch.randint(len(pool), (UPDATES, prior.BATCH // 2), generator=rng)]
                  for pool in groups.values()]
        draws[seed] = torch.cat(chosen, dim=1)
        active = int(ys[draws[seed]].ne(-100).sum())
        assert train_pool >= 2 * active
        draw_receipts[str(seed)] = dict(order=list(order), supervised_targets=active,
            distinct_documents=int(draws[seed].unique().numel()), draw_sha256=base.state_sha(draws[seed]))
    assert not torch.equal(*draws.values())
    profile = dict(tag=TAG, approval="WIP176", source_sha256={s: sha(base.ROOT / s) for s in SOURCES},
        parent_sha256=sha(prior.frozen.prior.PARENT), tokenizer_sha256=sha(base.STUDENT),
        prior_profile_sha256=sha(profile_path), prior_report_sha256=sha(result_path),
        common_arrays_sha256=base.state_sha((xs, ys, held)),
        initial_model_sha256=baseline["initial"], initial_held=baseline["held"]["0"]["summary"],
        target_held=baseline["held"]["64"]["summary"], train_pool=train_pool, draws=draw_receipts,
        updates=UPDATES, warmup=WARMUP, base_lr=prior.LR, matrix_lr_mult=1.,
        context=prior.WIDTH, micro_bs=prior.BATCH, accum=1, held_steps=list(STAMPS),
        max_worker_seconds=400, checkpoint_writes=0)
    assert profile["parent_sha256"] == prior.frozen.PARENT_SHA == previous["sources"]["parent_sha"]
    return profile, docs, xs, ys, held, draws


def state_storage_bytes(optimizer):
    storages = {}
    for state in optimizer.state.values():
        for value in state.values():
            if isinstance(value, torch.Tensor):
                storage = value.untyped_storage()
                storages[str(value.device), storage.data_ptr()] = storage.nbytes()
    return sum(storages.values())


def train(method, seed, docs, xs, ys, held, draw_ids, contract):
    arm_start = perf_counter()
    model = prior.initialize()
    initial = base.state_sha(model.state_dict())
    assert initial == contract["initial_model_sha256"]
    route = prior.build_experimental_optimizers(model, method, lr=prior.LR, matrix_lr_mult=1.)
    optimizers = (route.adamw, route.matrix)
    prior.keep_active_groups(optimizers)
    rates = [[g["lr"] for g in opt.param_groups] for opt in optimizers]
    initial_score = prior.evaluate(model, xs, ys, docs, held)
    assert initial_score["summary"] == contract["initial_held"]
    history, scores = [], {"0": dict(**initial_score, training_seconds=0., elapsed_seconds=0.)}
    first_reach = None
    peak_allocated = peak_reserved = 0
    torch.cuda.synchronize()
    started = perf_counter()
    for step, ids in enumerate(draw_ids, 1):
        if (OUT / "STOP").exists() or datetime.now(base.CUTOFF.tzinfo) >= base.CUTOFF:
            raise RuntimeError("owned STOP or deadline")
        scale = prior.lr_factor(step - 1, WARMUP, UPDATES, "cosine")
        for optimizer, rate in zip(optimizers, rates, strict=True):
            for group, lr in zip(optimizer.param_groups, rate, strict=True):
                group["lr"] = lr * scale
        torch.cuda.reset_peak_memory_stats()
        update_start = perf_counter()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(xs[ids])
            targets = ys[ids]
            loss = F.cross_entropy(logits.flatten(0, 1), targets.flatten())
        loss.backward()
        grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        route.validate_before_step()
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        torch.cuda.synchronize()
        seconds = perf_counter() - update_start
        history.append(dict(step=step, loss=float(loss.detach()), gradient_norm=float(grad),
                            supervised_targets=int(targets.ne(-100).sum()), seconds=seconds))
        peak_allocated = max(peak_allocated, torch.cuda.max_memory_allocated())
        peak_reserved = max(peak_reserved, torch.cuda.max_memory_reserved())
        del logits, loss, grad, targets
        if step in STAMPS:
            score = prior.evaluate(model, xs, ys, docs, held)
            score.update(training_seconds=sum(row["seconds"] for row in history),
                         elapsed_seconds=perf_counter() - started)
            scores[str(step)] = score
            languages = score["summary"]
            if first_reach is None and all(languages[k]["nll"] <= v["nll"]
                                           for k, v in contract["target_held"].items()):
                first_reach = dict(step=step, training_seconds=score["training_seconds"],
                                   elapsed_seconds=score["elapsed_seconds"])
            print("P109_OPTIMIZER_STEP", seed, method, step,
                  f"{languages['en']['nll']:.5f}", f"{languages['ko']['nll']:.5f}", flush=True)
    assert sum(row["supervised_targets"] for row in history) == contract["draws"][str(seed)]["supervised_targets"]
    return dict(seed=seed, method=method, initialized_sha256=initial,
        final_sha256=base.state_sha(model.state_dict()), roles_sha256=base.state_sha(route.manifest["parameters"]),
        optimizer_contract_sha256=route.manifest["contract_sha256"],
        optimizer_state_storage_bytes={"matrix": state_storage_bytes(route.matrix),
                                       "adamw": state_storage_bytes(route.adamw)},
        peak_allocated_bytes=peak_allocated, peak_reserved_bytes=peak_reserved, history=history,
        median_update_seconds=median(row["seconds"] for row in history[WARMUP:]),
        arm_wall_seconds=perf_counter() - arm_start, held=scores, first_reach=first_reach)


def execute(profile, docs, xs, ys, held, draws):
    assert base.idle() and torch.cuda.device_count() == 1
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    write(OUT / "active.json", dict(pid=os.getpid(), tag=TAG))
    xs, ys, held = (tensor.cuda() for tensor in (xs, ys, held))
    device = OUT / "device_100ms.csv"
    arms = []
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*base.DEVICE, f"--loop-ms={base.INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                for seed, order in ORDER.items():
                    order_ids = draws[seed].cuda()
                    for method in order:
                        arm = train(method, seed, docs, xs, ys, held, order_ids, profile)
                        write(OUT / f"seed_{seed}_{method}.json", arm)
                        arms.append(arm)
                        torch.cuda.empty_cache()
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = base.read_samples(device)
    source_same = all(sha(base.ROOT / s) == v for s, v in profile["source_sha256"].items())
    parent_same = sha(prior.frozen.prior.PARENT) == profile["parent_sha256"]
    tokenizer_same = sha(base.STUDENT) == profile["tokenizer_sha256"]
    assert source_same and parent_same and tokenizer_same and samples
    assert len({arm["roles_sha256"] for arm in arms}) == 1
    for seed in ORDER:
        assert len({a["history"][0]["loss"] for a in arms if a["seed"] == seed}) == 1
    write(OUT / "report.json", dict(arms=arms, source_preserved=True, checkpoint_writes=0,
        profile_sha256=sha(OUT / "profile.json"), device_sha256=sha(device), device_samples=len(samples),
        device_peak=max(samples, key=lambda row: row["occupied_mib"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    assert datetime.now(base.CUTOFF.tzinfo) + timedelta(seconds=420) < base.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    profile, *arrays = prepared()
    if phase == "prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT / "profile.json", profile)
        print("P109_OPTIMIZER_CPU", profile["train_pool"], profile["draws"], flush=True)
    else:
        assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
        assert profile == read(OUT / "profile.json")
        execute(profile, *arrays)


if __name__ == "__main__":
    main()
