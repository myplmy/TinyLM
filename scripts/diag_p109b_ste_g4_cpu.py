"""Test update-level STE reuse with the actual tied G4 and Muon RMS4 on CPU."""

import os
from statistics import median
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109_train_visit_policy as route
from scripts import run_p109b_scratch_pair_20261120 as pair
from tinylm.config import build_config
from tinylm.train import trainer
from tinylm.train.muon import Muon, split_params


OUT = pair.ROOT / "test_result/evidence/p109b_g4_ste_reuse_exact_update_cpu_v2_20261120"
LEARNING_RATE = 1e-3
ANNEAL = 0.60


def sample():
    data = np.memmap(pair.PILOT / "train.bin", dtype="<u2", mode="r")
    starts = np.random.default_rng(1234).integers(0, len(data) - 65, (4, 2))
    tokens = data[starts[:, :, None] + np.arange(65)].astype(np.int64)
    return [(torch.from_numpy(row[:, :-1].copy()), torch.from_numpy(row[:, 1:].copy())) for row in tokens]


def optimizers(model):
    matrices, _ = split_params(model)
    matrix_ids = {id(parameter) for parameter in matrices}
    groups = []
    for group in model.param_groups(LEARNING_RATE, weight_decay=0.1):
        others = [parameter for parameter in group["params"] if id(parameter) not in matrix_ids]
        if others:
            groups.append(dict(group, params=others))
    return (torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8),
            Muon(matrices, lr=LEARNING_RATE * 4, scale_mode="rms", weight_decay=0.0), matrix_ids)


def update(model, initial, batches, *, cached, bf16, ce_rows=32):
    model.load_state_dict(initial, strict=True)
    model.zero_grad(set_to_none=True)
    model.clear_quant()
    model.training_forwards = 0
    adamw, muon, matrices = optimizers(model)
    device = next(model.parameters()).device
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        torch.cuda.reset_peak_memory_stats(device)
    losses = []
    begin = time.perf_counter()
    with patch.object(model, "refresh_quant", wraps=model.refresh_quant) as refresh:
        if cached:
            model.begin_quant_update_cache()
        for x, y in batches:
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=bf16):
                loss = trainer._ce_recomputed(model, x, y, ce_rows) / len(batches)
            losses.append(float(loss.detach()))
            loss.backward()
        if cached:
            model.finish_quant_update_cache()
        refreshes = refresh.call_count
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    seconds = time.perf_counter() - begin
    snapshot = lambda value: value.detach().to(device="cpu", copy=True)
    gradients = {name: snapshot(parameter.grad) for name, parameter in model.named_parameters() if parameter.grad is not None}
    norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0))
    adamw.step()
    muon.step()
    weights = {name: snapshot(parameter) for name, parameter in model.named_parameters() if name in gradients}
    if model.training_forwards != len(batches) or model._p102a_quant_update is not None:
        raise ValueError("actual visits or STE cache release differs")
    return {"seconds": seconds, "losses": losses, "gradient": gradients, "weights": weights,
            "norm": norm, "refreshes": refreshes,
            "peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 2**20 if device.type == "cuda" else None,
            "peak_reserved_mib": torch.cuda.max_memory_reserved(device) / 2**20 if device.type == "cuda" else None,
            "muon_names": {name for name, parameter in model.named_parameters() if id(parameter) in matrices}}


def peak_delta(left, right, field, names):
    return max((float((left[field][name] - right[field][name]).abs().amax()), name) for name in names)


def compare(model, initial, batches, bf16):
    by_kind = {False: [], True: []}
    retain = {}
    for cached in (False, True, True, False):
        result = update(model, initial, batches, cached=cached, bf16=bf16)
        by_kind[cached].append(result["seconds"])
        if cached in retain:
            prior = retain[cached]
            if (prior["losses"] != result["losses"]
                    or any(peak_delta(prior, result, field, prior[field])[0] for field in ("gradient", "weights"))):
                raise ValueError("same-arm fresh repeats must reproduce loss, gradients, and weights")
        retain.setdefault(cached, result)
    reference, candidate = retain[False], retain[True]
    names = set(reference["gradient"])
    if names != set(candidate["gradient"]) or (reference["refreshes"], candidate["refreshes"]) != (4, 1):
        raise ValueError("same gradients and exact 4-to-1 refresh coverage required")
    return {"ordinary_seconds_abba": by_kind[False], "cached_seconds_abba": by_kind[True],
            "cache_minus_ordinary_median_pct": 100 * (median(by_kind[True]) / median(by_kind[False]) - 1),
            "loss_max_abs": max(abs(a - b) for a, b in zip(reference["losses"], candidate["losses"])),
            "gradient_max_abs_and_parameter": peak_delta(reference, candidate, "gradient", names),
            "muon_weight_max_abs_and_parameter": peak_delta(reference, candidate, "weights", reference["muon_names"]),
            "adamw_weight_max_abs_and_parameter": peak_delta(reference, candidate, "weights", names-reference["muon_names"]),
            "clip_norm_delta": abs(reference["norm"] - candidate["norm"]), "parameters_with_gradient": len(names),
            "refresh_counts": [reference["refreshes"], candidate["refreshes"]]}


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("explicit CPU-only execution required")
    torch.set_num_threads(2)
    torch.manual_seed(1337)
    cfg = build_config("m100s12_g4", "tied", 64, ckpt=False)
    cfg.train_repeat = 2.0
    model = route.RoutedG4(cfg).train()
    model.set_anneal(ANNEAL)
    model.training_route = route.route_for(cfg, model.owner, "second_shuffle_r2", 1337, 19, pair.STEPS)
    initial = {key: value.detach().clone() for key, value in model.state_dict().items()}
    batches = sample()
    reports = {}
    for name, bf16 in (("fp32", False), ("autocast_bf16", True)):
        reports[name] = compare(model, initial, batches, bf16)
        print(name, reports[name], flush=True)
    result = dict(results=reports, sample_shape={"micro": 2, "accum": 4, "sequence": 64},
                  model="G4 tied CLA2 R2 second traversal shuffle", seed=1337, target_tokens=512,
                  clip_norm=1, ce_recompute_rows=32, anneal=ANNEAL, adamw_lr=LEARNING_RATE,
                  muon_lr=LEARNING_RATE * 4, muon_scale="rms", cuda=False,
                  core_training_calls=8, saved_checkpoints=0, actual_quality="NOT_RUN")
    OUT.mkdir(exist_ok=False)
    pair.publish(OUT / "report.json", result)


if __name__ == "__main__":
    main()
