"""Keep the widened bilingual course and move its old-range rows to the final segment."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np
import torch

from scripts import run_p109c_bilingual_range_extension as widened


paired, trial, data, baseline = widened.paired, widened.trial, widened.data, widened.baseline
TAG = "p109c_bilingual_range_replay_gpu_v1_20261121"
OUT = paired.OUT.with_name(TAG)
TAIL_UPDATES = 512
SEED = 2026112119


def prepare():
    input_plan, _ = widened.prepare()
    report = trial.read_json(widened.OUT / "report.json")
    terminal = trial.read_json(widened.OUT / "supervisor.json")
    if report["plan"] != input_plan or terminal["returncode"] or terminal["stop_reason"]:
        raise ValueError("requires the completed comparison from the same bilingual tables")
    pairs = input_plan["supervised"][-1] // 2
    tail = pairs - TAIL_UPDATES * data.BATCH // 2
    with np.load(widened.PAYLOAD, allow_pickle=False) as arrays:
        new_range = arrays["indices"]
    move = new_range[new_range >= tail]
    eligible = np.setdiff1d(np.arange(tail), new_range, assume_unique=True)
    chosen = np.sort(np.random.default_rng(SEED).choice(eligible, len(move), replace=False))
    order = np.arange(pairs)
    order[chosen], order[move] = move, chosen
    if (not len(move) or not np.array_equal(np.sort(order), np.arange(pairs))
            or np.intersect1d(order[tail:], new_range).size):
        raise ValueError("the new order must preserve every table and keep new-range pairs out of the tail")
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), input=input_plan,
                prior_report=trial.file_sha(widened.OUT / "report.json"), tail_updates=TAIL_UPDATES,
                tail_pair_count=pairs-tail, swaps=len(move), seed=SEED,
                order=data.authored.digest(order.tolist()))
    return plan, order


def worker(plan, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    checked, order = prepare()
    if checked != plan or not torch.cuda.is_bf16_supported():
        raise ValueError("the course order or accelerator changed")
    rows = np.column_stack((2*order, 2*order+1)).reshape(-1)
    with np.load(widened.PAYLOAD, allow_pickle=False) as arrays:
        tensors = paired.gpu_arrays([arrays[k][rows] for k in widened.ARRAYS[:4]])
        options = torch.as_tensor(arrays["options"][order], device="cuda", dtype=torch.long)
        unique = torch.as_tensor(arrays["unique"][order], device="cuda")
    input_plan, (tok, special, ood_cases, _) = widened.prepare()
    source = input_plan["contract"]
    translation_plan, (_, _, _, translated) = paired.crossed.prepare()
    if translation_plan != source["base"]["cross"]:
        raise ValueError("the original translated assessments changed")
    validation = trial.read_json(baseline.INPUT / "validation.json")
    ordinary = trial.read_json(data.DATA / "evaluation.json")
    model = baseline.TiedMLPTransformer(trial.make_config()).to("cuda")
    selector = baseline.ValueLink(model.cfg.dim).to("cuda")
    optimizer = torch.optim.AdamW([*model.parameters(), *selector.parameters()], lr=.0015,
                                  weight_decay=.01, fused=True)
    shared = torch.load(paired.OUT / "shared_wide_start.pt", weights_only=True, map_location="cpu")
    model.load_state_dict(shared["model"])
    selector.load_state_dict(shared["selector"])
    optimizer.load_state_dict(shared["optimizer"])
    torch.set_rng_state(shared["cpu_rng"])
    torch.cuda.set_rng_state(shared["cuda_rng"])
    if json.dumps(paired.fingerprint(model, selector, optimizer), sort_keys=True) != json.dumps(source["warm_state"], sort_keys=True):
        raise ValueError("the common starting state differs")
    started = time.perf_counter()
    warm_updates = source["base"]["warm_updates"]
    wide = paired.train_phase(model, selector, optimizer, tensors, input_plan["supervised"], "range_replay",
                              warm_updates, started, (options, unique))
    if wide["step"] != data.UPDATES or not wide["transfer_pairs"]:
        raise ValueError("the reordered course did not complete")
    assessment = paired.evaluate(model, selector, tok, special, validation, ordinary, translated, OUT)
    ood = {}
    for name, cases in ood_cases.items():
        generated = data.evaluate(model, tok, special, cases, paired=True)
        slots = baseline.evaluate_slots(model, selector, cases, special["<pad>"])
        count = sum(out["answer"] == gold and out["eot"] for row in generated["rows"]
                    for out, gold in zip(row["outputs"], row["gold"], strict=True))
        ood[name] = dict(individual=count, joint=generated["both_correct"],
                         by_language=generated["by_language"], selected=slots["individual"])
        trial.publish(OUT / f"{name}.json", dict(generated=generated, selected=slots))
    with (OUT / "foundation.pt").open("xb") as file:
        torch.save(dict(tag=TAG, step=wide["step"], parent=None, config=asdict(model.cfg),
                        model={k: v.detach().cpu() for k, v in model.state_dict().items()},
                        train_head={k: v.detach().cpu() for k, v in selector.state_dict().items()}), file)
    report = dict(plan=plan, wide=wide, assessment=assessment, ood=ood, updates=wide["step"]-warm_updates,
                  checkpoint=trial.file_sha(OUT / "foundation.pt"), elapsed=time.perf_counter()-started,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20)
    trial.publish(OUT / "report.json", report)
    print(json.dumps(dict(assessment=assessment, ood=ood), ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires the sealed row order and a cutoff")
    return baseline.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                    authorization_end=paired.bridge.AUTHORIZATION_END, min_seconds=600)


if __name__ == "__main__":
    raise SystemExit(main())
