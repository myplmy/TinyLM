"""Measure the effect of a lower initial bilingual transfer weight in the original order."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np
import torch

from scripts import run_p109c_bilingual_shuffled_pairs as shuffled


paired = shuffled.previous
trial, data, baseline = paired.trial, paired.data, paired.baseline
TAG = "p109c_bilingual_early_transfer_scale_gpu_v1_20261121"
OUT = paired.OUT.with_name(TAG)
EARLY_STEPS = 256
EARLY_SCALE = .60


def prepare():
    shuffle_plan, _ = shuffled.prepare()
    shuffled_report = trial.read_json(shuffled.OUT / "report.json")
    terminal = trial.read_json(shuffled.OUT / "supervisor.json")
    if (shuffled_report["plan"] != shuffle_plan or terminal["returncode"] != 0
            or terminal["stop_reason"] is not None):
        raise ValueError("requires the completed frozen comparison of both orders")
    return dict(tag=TAG, source=trial.file_sha(Path(__file__)), original=shuffle_plan["original"],
                warm=shuffle_plan["warm"], warm_state=shuffle_plan["warm_proof"],
                first_updates=EARLY_STEPS, loss_multiplier=EARLY_SCALE,
                original_report=shuffle_plan["paired_source"],
                shuffled_report=trial.file_sha(shuffled.OUT / "report.json"))


def worker(plan, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if prepare() != plan or not torch.cuda.is_bf16_supported():
        raise ValueError("the sealed early transfer test or accelerator changed")
    with np.load(paired.PAYLOAD, allow_pickle=False) as arrays:
        tensors = paired.gpu_arrays([arrays[k] for k in ("tokens", "labels", "context", "sites")])
        options = torch.as_tensor(arrays["options"], device="cuda", dtype=torch.long)
        distinct = torch.as_tensor(arrays["unique"], device="cuda")
    holdout, (tok, special, _, translated) = paired.crossed.prepare()
    if holdout != plan["original"]["cross"]:
        raise ValueError("the bilingual holdout changed")
    validation = trial.read_json(baseline.INPUT / "validation.json")
    ordinary = trial.read_json(data.DATA / "evaluation.json")
    model = baseline.TiedMLPTransformer(trial.make_config()).to("cuda")
    selector = baseline.ValueLink(model.cfg.dim).to("cuda")
    optimizer = torch.optim.AdamW([*model.parameters(), *selector.parameters()], lr=.0015,
                                  weight_decay=.01, fused=True)
    shared = torch.load(shuffled.SNAPSHOT, weights_only=True, map_location="cpu")
    model.load_state_dict(shared["model"])
    selector.load_state_dict(shared["selector"])
    optimizer.load_state_dict(shared["optimizer"])
    torch.set_rng_state(shared["cpu_rng"])
    torch.cuda.set_rng_state(shared["cuda_rng"])
    expected = json.dumps(plan["warm_state"], sort_keys=True)
    if json.dumps(paired.fingerprint(model, selector, optimizer), sort_keys=True) != expected:
        raise ValueError("the restored optimizer or model differs")

    started = time.perf_counter()
    selected_transfer = paired.selected_transfer
    update = 0
    early_accepted = torch.zeros((), dtype=torch.long, device="cuda")

    def scale_initial_loss(*args):
        nonlocal update
        loss, eligible = selected_transfer(*args)
        update += 1
        if update <= EARLY_STEPS:
            early_accepted.add_(eligible)
            loss = loss * EARLY_SCALE
        return loss, eligible

    # Scope the change to this owned child and reuse the frozen training loop.
    paired.selected_transfer = scale_initial_loss
    try:
        wide = paired.train_phase(model, selector, optimizer, tensors, plan["original"]["supervised"],
                                  "early_transfer_scale", plan["original"]["warm_updates"], started,
                                  (options, distinct))
    finally:
        paired.selected_transfer = selected_transfer
    if wide["step"] != data.UPDATES or update != data.UPDATES - plan["original"]["warm_updates"]:
        raise ValueError("the intended updates did not all execute")
    assessment = paired.evaluate(model, selector, tok, special, validation, ordinary, translated, OUT)
    with (OUT / "foundation.pt").open("xb") as file:
        torch.save(dict(tag=TAG, step=wide["step"], parent=None, config=asdict(model.cfg),
                        model={k: v.detach().cpu() for k, v in model.state_dict().items()},
                        train_head={k: v.detach().cpu() for k, v in selector.state_dict().items()}), file)
    result = dict(plan=plan, wide=wide, assessment=assessment, updates=update,
                  early_accepted=int(early_accepted.item()), elapsed=time.perf_counter()-started,
                  checkpoint=trial.file_sha(OUT / "foundation.pt"),
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20)
    trial.publish(OUT / "report.json", result)
    print(json.dumps(dict(assessment=assessment, steps=update, early_accepted=result["early_accepted"])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires the sealed early transfer test and cutoff")
    return baseline.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                    authorization_end=paired.bridge.AUTHORIZATION_END, min_seconds=600)


if __name__ == "__main__":
    raise SystemExit(main())
