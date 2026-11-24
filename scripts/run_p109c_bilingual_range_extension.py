"""Replace a quarter of the bilingual training pairs with unseen five-digit tables."""

import argparse
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import time

import numpy as np
import torch

from scripts import diag_p109c_transfer_ood as holdout
from scripts import run_p109c_bilingual_value_transfer as paired


TAG = "p109c_bilingual_range_extension_gpu_v1_20261121"
OUT = paired.OUT.with_name(TAG)
INPUT = paired.OUT.with_name("p109c_bilingual_range_extension_cpu_v1_20261121")
PAYLOAD = INPUT / "wide_pairs.npz"
SEED = 2026112111
REPLACED = 8192
trial, data, baseline, control = paired.trial, paired.data, paired.baseline, paired.control
ARRAYS = ("tokens", "labels", "context", "sites", "options", "unique", "targets")


def references():
    paired_plan = paired.prepare()
    paired_path = paired.OUT / "report.json"
    terminal_path = paired.OUT / "supervisor.json"
    warm = paired.OUT / "shared_wide_start.pt"
    previous = trial.read_json(paired_path)
    terminal = trial.read_json(terminal_path)
    ood_plan, ood_data = holdout.prepare()
    ood_path = holdout.OUT / "report.json"
    ood = trial.read_json(ood_path)
    ood_terminal = trial.read_json(holdout.OUT / "supervisor.json")
    if (previous["plan"] != paired_plan or terminal["returncode"] or terminal["stop_reason"]
            or trial.file_sha(warm) != previous["warm_checkpoint"] or ood["plan"] != ood_plan
            or ood_terminal["returncode"] or ood_terminal["stop_reason"]):
        raise ValueError("requires completed, unchanged paired training and OOD evaluation")
    source = holdout.readout.OUT / "report.json"
    excluded = {
        int(value)
        for rows in trial.read_json(source)["answers"].values()
        for row in rows
        for value in row["values"]
        if 10000 <= int(value) < 99999
    }
    contract = dict(tag=TAG, source=trial.file_sha(Path(__file__)), base=paired_plan,
                    paired_report=trial.file_sha(paired_path), preceding_ood=trial.file_sha(ood_path),
                    ood_plan=ood_plan, warm=previous["warm_checkpoint"], warm_state=previous["warm_state"],
                    seed=SEED, replaced=REPLACED, exclusion_count=len(excluded),
                    exclusion_sha256=data.authored.digest(sorted(excluded)))
    return contract, ood_data, excluded


def prepare_input(deadline):
    if (INPUT.exists() or not deadline.tzinfo or deadline > paired.bridge.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 60):
        raise ValueError("requires a fresh authored CPU preparation within authorization")
    contract, (tok, special, _, _), excluded = references()
    pad = special["<pad>"]
    with np.load(paired.PAYLOAD, allow_pickle=False) as source:
        arrays = {name: source[name] for name in ARRAYS}
    rows = len(arrays["tokens"])
    if rows % data.BATCH or data.BATCH % 2 or tuple(data.authored.LANGUAGES) != ("ko", "en"):
        raise ValueError("expected a paired source and even batches")
    rng = np.random.default_rng(SEED)
    indices = np.sort(rng.choice(rows // 2, REPLACED, replace=False))
    allowed = np.array(sorted(set(range(10000, 99999)) - excluded), dtype=np.int32)
    replacement_values = {}
    unique_groups = set()
    for pair in indices:
        values = rng.choice(allowed, 4, replace=False).tolist()
        group = tuple(sorted(values))
        if group in unique_groups:
            raise ValueError("the augmentation repeated a numeric table")
        unique_groups.add(group)
        replacement_values[int(pair)] = values

    _, _, cases, _, _ = trial.load_cases()
    known = data.source_keys(tok, cases)
    lineage = Random(data.PROFILE_SEED)
    data.eval_pairs(tok, lineage, 11, 100, known)
    data.eval_pairs(tok, lineage, 11, 9980, known)
    original_digest = sha256()
    new_digest = sha256()
    changed = 0

    @lru_cache(maxsize=None)
    def first_piece(value):
        return tok.encode(str(value), add_special_tokens=False).ids[0]

    for phase, lo, hi, count in data.STAGES:
        for i in range(count):
            old, order, field, _, language = data.draw(lineage, i, lo, hi, known)
            fingerprint = bytes.fromhex(data.authored.digest(["table_values", sorted(old)]))
            original_digest.update(fingerprint)
            if phase != "wide" or language != "en":
                continue
            pair = i // 2
            if pair not in replacement_values:
                continue
            values = replacement_values[pair]
            new_digest.update(bytes.fromhex(data.authored.digest(["table_values", sorted(values)])))
            candidates = [first_piece(values[slot]) for slot in order]
            for row, lang in ((i-1, "ko"), (i, "en")):
                record, gold = data.form(values, order, field, lang, (i//32) % 2)
                tokens, labels = paired.preparation.encode_row(record, tok, pad)
                prompt = data.generation_prompt(tok, record)
                locations = baseline.sites_from_prompt(tok, prompt, gold)
                if (locations[-1] != arrays["sites"][row, -1]
                        or labels[locations[0]] != candidates[locations[-1]]
                        or int((labels == special["<|im_end|>"]).sum()) != 1):
                    raise ValueError(f"changed table selection or invalid answer on row {row}")
                arrays["tokens"][row] = tokens
                arrays["labels"][row] = labels
                arrays["sites"][row] = locations
            arrays["options"][pair] = candidates
            arrays["unique"][pair] = [piece not in candidates[:slot] for slot, piece in enumerate(candidates)]
            arrays["targets"][pair] = candidates.index(first_piece(values[field]))
            changed += 1

    archived = trial.read_json(data.DATA / "preflight.json")["train_values_sha256"]
    if original_digest.hexdigest() != archived or changed != REPLACED:
        raise ValueError("could not reconstruct the exact original rows")
    arrays["context"] = control.prefix_labels(arrays["tokens"], arrays["labels"], pad)
    count_labels = lambda key: int(np.count_nonzero(arrays[key] != baseline.IGNORE))
    supervised = [count_labels("labels"), count_labels("context"), rows]
    INPUT.mkdir()
    with PAYLOAD.open("xb") as file:
        np.savez_compressed(file, **arrays, indices=indices, values=list(replacement_values.values()))
    trial.publish(INPUT / "report.json", dict(contract=contract, supervised=supervised,
                  input_slots=int(arrays["tokens"].size), payload=trial.file_sha(PAYLOAD),
                  old_order=archived, new_values_sha256=new_digest.hexdigest()))
    print(json.dumps(dict(replaced=changed, excluded=len(excluded), supervised=supervised)), flush=True)


def prepare():
    contract, ood_data, excluded = references()
    saved = trial.read_json(INPUT / "report.json")
    if saved["contract"] != contract or saved["payload"] != trial.file_sha(PAYLOAD):
        raise ValueError("the prepared augmentation or its source changed")
    with np.load(PAYLOAD, allow_pickle=False) as arrays:
        values = arrays["values"]
        rows = contract["base"]["supervised"][-1]
        if (values.shape != (REPLACED, 4) or set(values.flat) & excluded
                or not np.all((10000 <= values) & (values < 99999))
                or arrays["tokens"].shape != (rows, data.WIDTH)
                or len(np.unique(arrays["indices"])) != REPLACED):
            raise ValueError("the protected five-digit holdout or batch shape is invalid")
    return saved, ood_data


def worker(plan, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    checked, (tok, special, ood_cases, _) = prepare()
    if checked != plan or not torch.cuda.is_bf16_supported():
        raise ValueError("the sealed augmentation or accelerator changed")
    with np.load(PAYLOAD, allow_pickle=False) as arrays:
        tensors = paired.gpu_arrays([arrays[name] for name in ARRAYS[:4]])
        options = torch.as_tensor(arrays["options"], device="cuda", dtype=torch.long)
        unique = torch.as_tensor(arrays["unique"], device="cuda")
    base = plan["contract"]["base"]
    assessment_plan, (_, _, _, translated) = paired.crossed.prepare()
    if assessment_plan != base["cross"]:
        raise ValueError("the original evaluation changed")
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
    warm = json.dumps(paired.fingerprint(model, selector, optimizer), sort_keys=True)
    if warm != json.dumps(plan["contract"]["warm_state"], sort_keys=True):
        raise ValueError("the common starting state differs")
    started = time.perf_counter()
    wide = paired.train_phase(model, selector, optimizer, tensors, plan["supervised"], "transfer_range",
                              base["warm_updates"], started, (options, unique))
    if wide["step"] != data.UPDATES or wide["transfer_pairs"] == 0:
        raise ValueError("the five-digit augmentation did not complete")
    assessment = paired.evaluate(model, selector, tok, special, validation, ordinary, translated, OUT)
    ood_results = {}
    for name, rows in ood_cases.items():
        generated = data.evaluate(model, tok, special, rows, paired=True)
        slots = baseline.evaluate_slots(model, selector, rows, special["<pad>"])
        individual = sum(out["answer"] == gold and out["eot"] for row in generated["rows"]
                         for out, gold in zip(row["outputs"], row["gold"], strict=True))
        ood_results[name] = dict(joint=generated["both_correct"], by_language=generated["by_language"],
                                 individual=individual, selected=slots["individual"])
        trial.publish(OUT / f"{name}.json", dict(generated=generated, selected=slots))
    with (OUT / "foundation.pt").open("xb") as file:
        torch.save(dict(tag=TAG, parent=None, step=wide["step"], config=asdict(model.cfg),
                        model={k: v.detach().cpu() for k, v in model.state_dict().items()},
                        train_head={k: v.detach().cpu() for k, v in selector.state_dict().items()}), file)
    result = dict(plan=plan, wide=wide, assessment=assessment, ood=ood_results,
                  checkpoint=trial.file_sha(OUT / "foundation.pt"), elapsed=time.perf_counter()-started,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20)
    trial.publish(OUT / "report.json", result)
    print(json.dumps(dict(assessment=assessment, ood=ood_results), ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        if args.stop_by is None:
            parser.error("requires a CPU preparation cutoff")
        prepare_input(args.stop_by)
        return 0
    plan, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires the sealed augmentation and a GPU cutoff")
    return baseline.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                    authorization_end=paired.bridge.AUTHORIZATION_END, min_seconds=600)


if __name__ == "__main__":
    raise SystemExit(main())
