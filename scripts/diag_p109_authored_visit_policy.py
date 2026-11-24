"""Compare learned P109 visit policies on a sealed, authored bilingual pool."""

import argparse
from collections import defaultdict
from pathlib import Path
import os
import random
from statistics import median
import subprocess
from time import perf_counter, time

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_frozen_g4_routes as official
from scripts import p109_train_visit_policy as native
from scripts.diag_p102a_g4_joint_ce_kl_batch8 import DEVICE, INTERVAL_MS, read_samples
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.p107_active_optimizer_groups import keep_active_groups
from tinylm.config import build_config
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.experimental_optimizers import build_experimental_optimizers


ROOT = official.ROOT
TAG = "p109_authored_visit_policy_v2_20261119"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
CHOICES = OUT / "official_inputs.json"
AUTHORED = ROOT / "test_result/evidence/p106b_p109_actual_prefix_kd_v1_20261119/profile.json"
PREVIOUS = ROOT / "test_result/evidence/p108_g4_master_margin_authored_v1_20261119"
POLICIES = native.POLICIES
SEEDS = (1092026, 1092027)
STEPS, WIDTH, LR = 160, 96, 3e-5
CUTOFF = official.prior.CUTOFF.timestamp()
MAX_SECONDS = 510
read, write, digest = official.read_json, official.prior.io.write, official.prior.io.digest


def check_window(seconds=0):
    if time() + seconds >= CUTOFF or (OUT / "STOP").exists():
        raise RuntimeError("outside the approved window or the experiment stop marker exists")


def make_draws(train, lengths, seed):
    policy = native.prior.Policy("balanced_count", seed)
    counts = [native.prior.bounded_count(policy, step, STEPS, "train") for step in range(STEPS)]
    rng = random.Random(seed)
    columns = []
    for candidates in train:
        buckets = defaultdict(list)
        for row in candidates:
            buckets[lengths[row]].append(row)
        pairs = []
        for bucket in buckets.values():
            rng.shuffle(bucket)
            pairs.extend(zip(bucket[::2], bucket[1::2]))
        selected = rng.sample(pairs, STEPS // 4)
        paired = {row for pair in selected for row in pair}
        ordinary = iter(rng.sample([i for i in candidates if i not in paired], STEPS // 2))
        column = []
        for block, pair in enumerate(selected):
            edge = iter(pair if rng.randrange(2) else pair[::-1])
            visits = counts[block * 4:(block + 1) * 4]
            column.extend(next(ordinary) if count == 2 else next(edge) for count in visits)
        if len(set(column)) != STEPS:
            raise ValueError("reused training document within a seed")
        columns.append(column)
    draws = list(zip(*columns, strict=True))
    physical = targets = 0
    by_language = [0, 0]
    for step in range(0, STEPS, 4):
        block = draws[step:step + 4]
        visits = [4 + 12 * n for n in counts[step:step + 4]]
        if sorted(visits) != [16, 28, 28, 40]:
            raise ValueError("incorrect visit allocation in a four-update block")
        physical += sum(visits) * WIDTH * 2
        for language in range(2):
            tokens = [lengths[row[language]] for row in block]
            if sum(n * v for n, v in zip(tokens, visits, strict=True)) != 28 * sum(tokens):
                raise ValueError("valid token-visit budget differs within a block and language")
            by_language[language] += sum(tokens)
            targets += 28 * sum(tokens)
    return dict(draws=draws, counts=counts, padded_visits=physical, target_visits=targets,
                language_targets=by_language)


def training_visit(model, arm, seed, index, total):
    return list(native.route_for(model.cfg, model.owner, arm, seed, index, total))


def check_routes(recipes):
    cfg = build_config("m100s12_g4", "tied", WIDTH)
    cfg.train_repeat = 3.
    cfg.infer_repeat = 1.
    cfg.repeat_mode = "uniform"
    cfg.cla_group = 2
    with torch.device("meta"):
        model = official.prior.build_model(cfg)
    for seed, recipe in recipes.items():
        for arm in POLICIES:
            for index in range(STEPS):
                with model.visit(training_visit(model, arm, int(seed), index, STEPS)) as route:
                    expected = (4 + 12 * recipe["counts"][index]) if arm == "balanced_count" else 28
                    if route["visits"] != expected:
                        raise ValueError("CPU route trace differs from the paired visit budget")


def prepare():
    check_window()
    if OUT.exists():
        raise FileExistsError(OUT)
    pins, inputs = official.prepare_inputs()
    previous = read(PREVIOUS / "profile.json")
    pins.add(PREVIOUS / "profile.json")
    pins.add(PREVIOUS / "data.pt", previous["data_sha256"])
    pins.add(AUTHORED, previous["pins"][str(AUTHORED.relative_to(ROOT))])
    for path in {Path(__file__), official.PLAN, *(ROOT / path for path in native.SOURCES),
                 ROOT / "tinylm/train/anneal_schedule.py", ROOT / "tinylm/train/experimental_optimizers.py",
                 ROOT / "tinylm/train/muon.py", ROOT / "scripts/p107_active_optimizer_groups.py",
                 ROOT / "scripts/diag_p102a_g4_joint_ce_kl_batch8.py",
                 ROOT / "scripts/diag_p102a_g4_recompute_shapes.py"}:
        pins.add(path)
    old_profile = official.OUT / "profile.json"
    pins.add(old_profile)
    prepared = {}
    for name, task in inputs.items():
        if task["receipt"] != read(old_profile)["tasks"][name]:
            raise ValueError("sealed official tasks or token batches differ")
        prepared[name] = dict(gold=[row["gold"] for row in task["rows"]], batches=task["batches"])
    data = torch.load(PREVIOUS / "data.pt", map_location="cpu", weights_only=True)
    documents = read(AUTHORED)["data"]["documents"]
    languages = ("en", "ko")
    train = [[i for i, d in enumerate(documents) if (d["split"], d["language"]) == ("train", language)]
             for language in languages]
    held = [[i for i, d in enumerate(documents) if (d["split"], d["language"]) == ("held", language)]
            for language in languages]
    lengths = data["y"].ne(-100).sum(1).tolist()
    pool = sum(lengths[i] for group in train for i in group)
    if (len(documents) != 816 or data["x"].shape != data["y"].shape or data["x"].shape != (816, WIDTH)
            or data["held"].tolist() != held or [len(s) for s in train] != [384, 384]
            or pool != previous["pool"] or torch.cuda.is_initialized()):
        raise ValueError("authored training and held splits differ")
    recipes = {str(seed): make_draws(train, lengths, seed) for seed in SEEDS}
    if any(2 * sum(recipe["language_targets"]) > pool for recipe in recipes.values()):
        raise ValueError("draw exceeds half of the authored token pool")
    check_routes(recipes)
    OUT.mkdir()
    write(CHOICES, prepared)
    pins.add(CHOICES)
    write(PROFILE, dict(tag=TAG, approval="WIP176", files=pins.files, steps=STEPS, width=WIDTH,
                        pool=pool, recipes=recipes, held_tokens=[sum(lengths[i] for i in ids) for ids in held],
                        tasks={name: task["receipt"] for name, task in inputs.items()}))
    print("P109_AUTHORED_READY", pool, [(seed, r["language_targets"], r["target_visits"])
                                     for seed, r in recipes.items()], flush=True)


def load_profile():
    profile = read(PROFILE)
    pins = official.audit.Inputs()
    pins.files = profile["files"]
    pins.unchanged()
    return profile, pins


def scores(model, inputs, labels, amp):
    valid = labels.ge(0)
    with torch.autocast("cuda", dtype=torch.bfloat16, enabled=amp):
        hidden = model(inputs, return_hidden=True)
        logits = model._head_logits(hidden[valid])
    return logits.float(), labels[valid]


def train(model, data, recipe, arm, seed):
    model.train()
    model.set_anneal(1.)
    route = build_experimental_optimizers(model, "muon_matched", lr=LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    keep_active_groups(optimizers)
    rates = [[group["lr"] for group in opt.param_groups] for opt in optimizers]
    draws = torch.tensor(recipe["draws"], dtype=torch.long, device="cuda")
    events = []
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for step, rows in enumerate(draws):
        check_window()
        free, total = torch.cuda.mem_get_info()
        if total - free > 13_000_000_000:
            raise RuntimeError("CUDA device use crossed 13 GB before the next update")
        start = perf_counter()
        visit = training_visit(model, arm, seed, step, STEPS)
        if len(visit) != (4 + 12 * recipe["counts"][step] if arm == "balanced_count" else 28):
            raise ValueError("calculated route differs from the sealed visit budget")
        factor = lr_factor(step, 4, STEPS, "cosine")
        for opt, group_rates in zip(optimizers, rates, strict=True):
            for group, rate in zip(opt.param_groups, group_rates, strict=True):
                group["lr"] = rate * factor
        with model.visit(visit):
            logits, labels = scores(model, data["x"][rows], data["y"][rows], True)
            loss = F.cross_entropy(logits, labels)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            for opt in optimizers:
                opt.step()
                opt.zero_grad(set_to_none=True)
            value = float(loss.detach()), float(norm)
        elapsed = perf_counter() - start
        events.append(dict(ce=value[0], norm=value[1], seconds=elapsed, visits=len(visit),
                           targets=len(labels), route_sha256=model.route_sha256))
        del logits, labels, loss, norm
        if (step + 1) % 40 == 0:
            print("P109_AUTHORED_UPDATE", seed, arm, step + 1, value[0], flush=True)
    if (sum(event["targets"] for event in events) != sum(recipe["language_targets"])
            or sum(event["targets"] * event["visits"] for event in events) != recipe["target_visits"]):
        raise ValueError("actual training target or route count differs")
    return dict(events=events, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved())


def eval_routes(model, arm, seed, index, total):
    fixed = native.cla.schedule(model.cfg, model.owner, "uniform", 2)
    yield "r2", fixed
    if arm == "balanced_count":
        for count in (1, 3):
            yield f"r{count}", native.cla.schedule(model.cfg, model.owner, "uniform", count)
    if arm == "second_shuffle_r2":
        yield "shuffle", training_visit(model, arm, seed + 17729, index, total)


@torch.inference_mode()
def evaluate(model, data, choices, arm, seed):
    model.eval()
    model.freeze_quant()
    held = defaultdict(list)
    for index, rows in enumerate(data["held"].T):
        labels = data["y"][rows]
        counts = labels.ge(0).sum(1).tolist()
        for key, visit in eval_routes(model, arm, seed, index, data["held"].shape[1]):
            model.set_route(visit)
            logits, targets = scores(model, data["x"][rows], labels, False)
            losses = F.cross_entropy(logits, targets, reduction="none").split(counts)
            hits = logits.argmax(1).eq(targets).split(counts)
            held[key].append([dict(loss_sum=float(loss.sum()), hits=int(hit.sum()), targets=len(loss))
                              for loss, hit in zip(losses, hits, strict=True)])
    bridge = official.adapter.TorchLikelihood(dict(torch=torch, model=model, cfg=model.cfg), model)
    tasks = {}
    for name, task in choices.items():
        result = defaultdict(list)
        started = perf_counter()
        for index, batch in enumerate(task["batches"]):
            check_window()
            for key, visit in eval_routes(model, arm, seed, index, len(task["batches"])):
                model.set_route(visit)
                rows = bridge(batch)
                result[key].extend(rows)
        if any(len(values) != 2 * len(task["gold"]) for values in result.values()):
            raise ValueError("incomplete official answer coverage")
        tasks[name] = dict(scores=result, seconds=perf_counter() - started)
        print("P109_AUTHORED_EVAL", seed, arm, name, len(task["gold"]), flush=True)
    bridge.close()
    return dict(held=held, tasks=tasks)


def run(seed):
    check_window(MAX_SECONDS)
    if not idle() or torch.cuda.device_count() != 1:
        raise RuntimeError("one visible idle GPU is required")
    profile, pins = load_profile()
    choices = read(CHOICES)
    raw = torch.load(PREVIOUS / "data.pt", map_location="cpu", weights_only=True)
    cfg, parent, step = official.prior.load_parent(torch)
    if step != 2289:
        raise ValueError("unexpected starting update")
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if torch.cuda.mem_get_info()[0] < 4 * 1024**3:
        raise RuntimeError("fewer than 4 GiB of free device memory")
    data = {key: raw[key].cuda() for key in ("x", "y", "held")}
    directory = OUT / str(seed)
    directory.mkdir()
    device = directory / "device_100ms.csv"
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*DEVICE, f"--loop-ms={INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                for arm in POLICIES:
                    torch.manual_seed(seed)
                    model = official.prior.build_model(cfg)
                    model.load_state_dict(parent, strict=True)
                    model.cuda()
                    training = train(model, data, profile["recipes"][str(seed)], arm, seed)
                    write(directory / f"{arm}_train.json", training)
                    write(directory / f"{arm}_eval.json", evaluate(model, data, choices, arm, seed))
                    del model
                    torch.cuda.empty_cache()
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = read_samples(device)
    if not samples or not pins.unchanged():
        raise RuntimeError("missing device samples or changed inputs")
    peak = max(samples, key=lambda row: row["occupied_mib"])
    write(directory / "complete.json", dict(seed=seed, device=torch.cuda.get_device_name(),
          peak=peak, samples=len(samples), profile_sha256=digest(PROFILE),
          parent_step=step, checkpoint_writes=0, device_samples_sha256=digest(device)))
    print("P109_AUTHORED_DONE", seed, peak, flush=True)


def summarize():
    import numpy as np

    profile, pins = load_profile()
    choices = read(CHOICES)
    report = {}
    for seed in SEEDS:
        directory = OUT / str(seed)
        recorded = read(directory / "complete.json")
        if recorded["profile_sha256"] != digest(PROFILE) or recorded["device_samples_sha256"] != digest(
                directory / "device_100ms.csv"):
            raise ValueError("sealed run receipt differs")
        rows = {}
        reference = {}
        rng = np.random.default_rng(seed)
        for arm in POLICIES:
            evaluated = read(directory / f"{arm}_eval.json")
            training = read(directory / f"{arm}_train.json")
            events = training.pop("events")
            training.update(seconds=sum(event["seconds"] for event in events),
                            median_update_seconds=median(event["seconds"] for event in events))
            held = {}
            for key, batches in evaluated["held"].items():
                held[key] = [dict(nll=sum(row["loss_sum"] for row in cells) / sum(row["targets"] for row in cells),
                                  hits=sum(row["hits"] for row in cells), targets=sum(row["targets"] for row in cells))
                             for cells in zip(*batches, strict=True)]
            if arm == "balanced_count":
                held["matched"] = [{field: (a[field] + 2 * b[field] + c[field]) / 4 for field in a}
                                   for a, b, c in zip(held["r1"], held["r2"], held["r3"], strict=True)]
            tasks = {}
            for name, task in evaluated["tasks"].items():
                gold = np.array(choices[name]["gold"])
                correct = {}
                for key, values in task["scores"].items():
                    raw = np.array([value[0] for value in values]).reshape((-1, 2))
                    if raw.shape[0] != len(gold) or not np.isfinite(raw).all() or (raw > 0).any():
                        raise ValueError("invalid or incomplete official scores")
                    correct[key] = (raw.argmax(1) == gold).astype(np.int8)
                if arm == "uniform_r2":
                    reference[name] = correct["r2"]
                if arm == "balanced_count":
                    correct["matched"] = (correct["r1"] + 2 * correct["r2"] + correct["r3"]) / 4
                if arm == "second_shuffle_r2":
                    correct["matched"] = correct["shuffle"]
                tasks[name] = {key: dict(correct=float(hit.sum()),
                              **official.paired_delta(hit - reference[name], rng)) for key, hit in correct.items()}
            rows[arm] = dict(training=training, held=held, tasks=tasks)
        report[str(seed)] = dict(device=recorded, arms=rows,
                                 language_targets=profile["recipes"][str(seed)]["language_targets"])
    pins.unchanged()
    write(OUT / "report.json", report)
    for seed, rows in report.items():
        print("P109_AUTHORED_RECOUNT", seed, [(arm, round(result["training"]["seconds"], 2),
              [result["tasks"][name]["r2"]["correct"] for name in official.TASKS])
              for arm, result in rows["arms"].items()], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "summarize"))
    parser.add_argument("--seed", type=int, choices=SEEDS)
    args = parser.parse_args()
    if (args.seed is None) == (args.mode == "run"):
        parser.error("run requires one registered seed; CPU modes take no seed")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if args.mode == "run" else ""):
        parser.error("isolate the CPU phase or select exactly GPU 0")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if args.mode == "prepare":
        prepare()
    elif args.mode == "run":
        run(args.seed)
    else:
        summarize()


if __name__ == "__main__":
    main()
