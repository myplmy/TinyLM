"""Score the fixed validation corpus with the newly reported hold kept out."""

import json
import os
import signal
import time

from scripts import eval_p109b_scratch_pair_20261120 as choice
from scripts import run_p109b_folded_ste_learning_pilot as pilot
from scripts import run_p109b_scratch_pair_20261120 as pair


OUT = pair.ROOT / "test_result/evidence/p109b_firstpass_full_val_20261120"
ACTUAL = pilot.OUT / "report.json"


def await_device():
    while time.time() + 150 < choice.END:
        if (choice.OUT / "report.json").is_file():
            closed = ACTUAL.is_file() and ACTUAL.read_bytes().endswith(bytes([10]))
            no_pilot_time = time.time() >= pilot.END - 1000 + 35 and not pilot.OUT.exists()
            if closed or no_pilot_time:
                try:
                    return pair.idle_gpu()
                except RuntimeError:
                    pass
        time.sleep(10)
    raise TimeoutError("authorized time for full validation or GPU handoff is unavailable")


def scores(model, tokens, starts, torch):
    import numpy as np

    focal = []
    width = pair.SEQ
    model.freeze_quant()
    for begin in range(0, len(starts), pair.MICRO):
        positions = np.asarray(starts[begin:begin+pair.MICRO])[:, None] + np.arange(width+1)
        valid = positions < len(tokens)
        ids = np.where(valid, tokens[np.minimum(positions, len(tokens)-1)], 0).astype(np.int64)
        labels = torch.from_numpy(np.where(valid[:, 1:], ids[:, 1:], -100)).cuda()
        inputs = torch.from_numpy(ids[:, :-1].copy()).cuda()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(inputs, use_cache=False)
        losses = torch.nn.functional.cross_entropy(logits.float().transpose(1, 2), labels,
                                                  reduction="none", ignore_index=-100)
        totals = losses.sum(dim=1, dtype=torch.float64).cpu().tolist()
        counts = valid[:, 1:].sum(axis=1).tolist()
        focal.extend(zip(totals, counts, strict=True))
    return focal


def interval(left, right, np):
    first, second = np.asarray(left), np.asarray(right)
    if not np.array_equal(first[:, 1], second[:, 1]):
        raise ValueError("validation sampling differs")
    blocks = np.arange(0, len(left), 16)
    sums = np.add.reduceat(second[:, 0] - first[:, 0], blocks)
    targets = np.add.reduceat(first[:, 1], blocks)
    rng = np.random.default_rng(1337)
    indices = rng.integers(0, len(blocks), size=(20_000, len(blocks)))
    estimates = sums[indices].sum(axis=1) / targets[indices].sum(axis=1)
    return {"blocks": len(blocks), "blocks_of_windows": 16, "draws": len(indices),
            "ci_95_nats_per_token": np.quantile(estimates, [.025, .975]).tolist()}


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("one explicitly selected GPU is necessary")
    total, used = await_device()
    signal.alarm(int(choice.END - time.time())-3)
    import math
    import numpy as np
    import torch

    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction((pair.CARD_LIMIT_MIB - used - 512) / total)
    queue = pair.OUT / "queue.json"
    reviewed = choice.read(choice.OUT / "report.json")
    if not choice.read(queue)["complete"] or reviewed["queue_sha256"] != pair.file_sha(queue):
        raise ValueError("use only the closed exact native pair")
    pins = choice.frozen.audit.Inputs()
    train_profile = choice.read(pair.OUT / "profile.json")
    cache = pins.add(pair.POOL / "val.bin", train_profile["pins"][str((pair.POOL / "val.bin").relative_to(pair.ROOT))])
    meta = choice.read(pair.POOL / "meta.json")
    tokens = np.memmap(pair.POOL / "val.bin", dtype="<u2", mode="r")
    if len(tokens) != meta["val"] or len(tokens) != 2_738_000:
        raise ValueError("held-out token range differs")
    exclusions = pins.add(pilot.VAL_HOLD)
    hold = choice.read(pilot.VAL_HOLD)
    exclude_lo, exclude_hi = hold["new_safety_hold_val_tokens"]
    exhaustive = range(0, len(tokens)-1, pair.SEQ)
    excluded = [index for index, start in enumerate(exhaustive)
                if start + pair.SEQ + 1 > exclude_lo and start < exclude_hi]
    if not 0 < exclude_lo < exclude_hi < len(tokens) or excluded != hold["full_validation_excluded_windows"]:
        raise ValueError("the validation hold selector no longer matches the admitted window profile")
    starts = [start for index, start in enumerate(exhaustive) if index not in excluded]
    target_count = sum(min(pair.SEQ, len(tokens)-1-start) for start in starts)
    rows, checkpoints = {}, {}
    with torch.inference_mode():
        for policy in pair.ARMS:
            start = time.monotonic()
            model, checkpoints[policy] = choice.load_model(torch, pins, policy)
            if reviewed["checkpoints"][policy] != checkpoints[policy]:
                raise ValueError("full validation must use the same two immutable final checkpoints")
            rows[policy] = scores(model, tokens, starts, torch)
            if sum(count for _, count in rows[policy]) != target_count:
                raise ValueError("validation coverage must close at exactly all admitted shifted tokens")
            print("P109B_FULL_VAL", policy, len(rows[policy]), time.monotonic()-start, flush=True)
            del model
    pins.unchanged()
    summary = {}
    for policy, result in rows.items():
        mean = math.fsum(value for value, count in result) / target_count
        summary[policy] = {"mean_nll": mean, "ppl": math.exp(mean),
                           "bpb": mean / math.log(2) / meta["bytes_per_token"]}
    baseline, comparison = pair.ARMS
    OUT.mkdir(exist_ok=False)
    pair.publish(OUT / "report.json", {"validation_file": cache, "checkpoints": checkpoints, "exclusions": exclusions,
        "coverage": {"targets": target_count, "windows": len(rows[baseline]), "width": pair.SEQ,
                     "held_windows": excluded, "held_token_range": [exclude_lo, exclude_hi]},
        "schedule": "common R2, causal fixed windows, BF16 logits converted to FP32 before CE",
        "by_arm": summary, "delta": {key: summary[comparison][key] - summary[baseline][key] for key in summary[baseline]},
        "paired_block_bootstrap": interval(rows[baseline], rows[comparison], np), "window_nll_sums_and_counts": rows})


if __name__ == "__main__":
    main()
