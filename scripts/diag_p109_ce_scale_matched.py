"""Match CE and KD packed-row calibration budgets and evaluate on held-out tasks."""

import argparse
import os
from pathlib import Path
from statistics import median
import subprocess
from time import perf_counter, time

import numpy as np
from tokenizers import Tokenizer
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_frozen_g4_routes as official
from scripts import diag_p109_qwen35_248k_scale_calibration as scale


ce = scale.ce
ROOT = ce.ROOT
TAG = "p109_qwen_248k_ce_scale_matched_v1_20261119"
OUT = ce.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
CHOICES = OUT / "choices.json"
EXPORT = OUT / "ce_calibrated_5trit.pt"
SOURCE_MODELS = {"ce": ce.EXPORT, "kd": scale.kd.EXPORT, "kd_48": scale.EXPORT}
MODELS = {**SOURCE_MODELS, "ce_48": EXPORT}
BATCH_CHOICES = 16
MAX_BYTES = 13_000_000_000
CUTOFF = ce.parent.CUTOFF.timestamp()
read, write, digest = ce.qwen.load, ce.qwen.write, ce.qwen.digest


def check_window(seconds=0):
    if time() + seconds >= CUTOFF or (OUT / "STOP").exists():
        raise RuntimeError("approved execution window or the experiment stop marker")


def check_device():
    check_window()
    free, total = torch.cuda.mem_get_info()
    if total - free > MAX_BYTES:
        raise RuntimeError("device use crossed the 13 GB operating boundary")


def prepare_choices(pins):
    task_sources, tasks = official.prepare_inputs()
    for path, receipt in task_sources.files.items():
        if path in pins.files and pins.files[path] != receipt:
            raise ValueError("task source changed during preparation")
    pins.files.update(task_sources.files)
    from lm_eval.api.model import TemplateLM

    source = read(ce.qwen.ASSET)["assets"]["qwen35_hf"]
    path = ROOT / source["path"]
    pins.add(ce.qwen.ASSET)
    pins.add(path, source["file_sha256"])
    tokenizer = Tokenizer.from_file(str(path))
    if (tokenizer.get_vocab_size() != ce.ASSIGNED or
            tokenizer.token_to_id("<|endoftext|>") != ce.EOS or source["physical_rows"] != ce.VOCAB):
        raise ValueError("Qwen tokenizer and packed table differ")
    prepared = {}
    receipts = {}
    for name, recorded in tasks.items():
        task, rows = recorded["task"], recorded["rows"]
        requests, batches = [], []
        for row in rows:
            _, _, alternatives = official.task_requests(task, row["doc"], row["index"])
            requests.extend(alternatives)
        request_sha = official.checksum([[req.doc_id, req.idx, req.args] for req in requests])
        if request_sha != recorded["receipt"]["request_sha256"]:
            raise ValueError("official request strings or order differ")

        def capture(batch):
            batches.append(batch)
            return [(-1., False)] * len(batch["input_ids"])

        planner = official.adapter.LikelihoodCore(vocab_size=ce.ASSIGNED, pad_id=ce.EOS,
                                                  score_batch=capture, batch_size=BATCH_CHOICES)
        encoder = official.adapter._adapter_type(TemplateLM)(core=planner, tokenizer=tokenizer,
                        prefix_id=ce.EOS, eos_id=ce.EOS, provenance={"tokenizer_sha256": source["file_sha256"]})
        encoder.loglikelihood(requests, disable_tqdm=True)
        observed = planner.diagnostics()
        encoder.close()
        if (observed["requests_scored"] != 2 * official.TASKS[name]
                or observed["context_truncated_requests"] or len(rows) != official.TASKS[name]):
            raise ValueError("incomplete or truncated official continuations")
        prepared[name] = dict(gold=[row["gold"] for row in rows], batches=batches)
        receipts[name] = dict(request_sha256=request_sha, token_sha256=official.checksum(batches),
                              rows=len(rows), choices=len(requests), batches=len(batches),
                              targets=observed["continuation_tokens_scored"], truncations=0,
                              max_width=max(len(b["input_ids"][0]) for b in batches))
    return prepared, receipts


def prepare():
    check_window()
    if OUT.exists():
        raise FileExistsError(OUT)
    previous = read(scale.PROFILE)
    scale.verify(previous)
    pins = official.audit.Inputs()
    reports = {}
    for name, path in SOURCE_MODELS.items():
        report_path = path.parent / "report.json"
        report = read(report_path)
        pins.add(report_path)
        pins.add(path, report["packed_sha256"])
        reports[name] = report["packed_held"]
    pins.add(scale.PROFILE)
    pins.add(scale.DRAWS, previous["draws_sha256"])
    for path in (Path(__file__), official.PLAN, ce.DATA, ce.PROFILE, Path(scale.__file__),
                 Path(ce.__file__), ROOT / "scripts/p014e_packed_g128.py",
                 ROOT / "tinylm/model/transformer.py", ROOT / "tinylm/model/modules.py"):
        pins.add(path)
    for path in official.SOURCES:
        pins.add(ROOT / path)
    draws = np.load(scale.DRAWS, allow_pickle=False)
    with np.load(ce.DATA, allow_pickle=False) as data:
        labels = data["y"][draws]
        blocked = set(data["draws"].ravel()) | set(data["held"].ravel())
    valid = labels[labels >= 0]
    if (draws.shape != (scale.STEPS, ce.BATCH) or len(np.unique(draws)) != draws.size
            or blocked.intersection(draws.ravel()) or len(valid) != previous["draw_targets"]
            or len(np.unique(valid)) != previous["editable_rows"] or valid.max() >= ce.ASSIGNED):
        raise ValueError("the existing 48-update calibration stream differs")
    choices, task_receipts = prepare_choices(pins)
    if torch.cuda.is_initialized():
        raise ValueError("preparation used CUDA")
    OUT.mkdir()
    write(CHOICES, choices)
    pins.add(CHOICES)
    write(PROFILE, dict(tag=TAG, approval="WIP176", files=pins.files, authored_held=reports,
                        tasks=task_receipts, steps=scale.STEPS, lr=scale.LR,
                        editable_rows=previous["editable_rows"], targets=previous["draw_targets"],
                        remaining_pool=previous["eligible_pool"], draws_sha256=previous["draws_sha256"]))
    print("P109_CE_SCALE_READY", len(valid), previous["editable_rows"],
          {name: t["rows"] for name, t in task_receipts.items()}, flush=True)


def load_profile():
    profile = read(PROFILE)
    pins = official.audit.Inputs()
    pins.files = profile["files"]
    pins.unchanged()
    return profile, pins


def train(profile):
    payload = torch.load(ce.EXPORT, map_location="cpu", weights_only=True)
    model = ce.load_payload(payload, device="cuda", tile_rows=4096)
    with np.load(ce.DATA, allow_pickle=False) as bundle:
        x, y, held = [torch.from_numpy(bundle[k]).cuda() for k in ("x", "y", "held")]
    draws = torch.from_numpy(np.load(scale.DRAWS, allow_pickle=False)).cuda()
    with torch.no_grad():
        first = draws[0]
        original, _ = ce.logits(model, x[first], y[first])
        scale.install_calibration_body(model)
        wrapped, _ = ce.logits(model, x[first], y[first])
        if not torch.equal(original, wrapped):
            raise ValueError("the calibration wrapper changed initial CE logits")
    del original, wrapped
    table = model.packed_embedding
    base = table.group_scales.detach().clone()
    labels = y[draws]
    ids = torch.unique(labels[labels >= 0])
    if len(ids) != profile["editable_rows"] or not bool(torch.all(base[ids] > 0)):
        raise ValueError("the same row IDs require positive CE scales")
    offsets = torch.nn.Parameter(torch.zeros_like(base[ids]))
    optimizer = torch.optim.Adam([offsets], lr=scale.LR)

    def installed():
        return base.index_copy(0, ids, base[ids] * offsets.exp())

    history = []
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for index, rows in enumerate(draws, 1):
        check_device()
        started = perf_counter()
        table.group_scales = installed()
        logits, targets = ce.logits(model, x[rows], y[rows])
        loss = F.cross_entropy(logits, targets)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_([offsets], 1., error_if_nonfinite=True)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        with torch.no_grad():
            offsets.clamp_(-scale.LIMIT, scale.LIMIT)
        torch.cuda.synchronize()
        history.append(dict(step=index, loss=float(loss.detach()), gradient_norm=float(norm),
                            targets=targets.numel(), seconds=perf_counter() - started))
        del logits, targets, loss, norm
        if index % 16 == 0:
            print("P109_CE_SCALE_UPDATE", index, history[-1]["loss"], flush=True)
    if sum(row["targets"] for row in history) != profile["targets"]:
        raise ValueError("actual number of training targets differs from KD calibration")
    with torch.no_grad():
        edited = installed()
        table.group_scales = edited
        changed = torch.where(edited.ne(base).flatten())[0]
        if not bool(torch.isin(changed, ids).all() and torch.isfinite(edited).all()):
            raise ValueError("untargeted rows or nonfinite scales")
        multiplier = offsets.exp()
        limits = [float(multiplier.min()), float(multiplier.max())]
        final = ce.evaluate(model, x, y, held)
        trained = dict(payload, embedding=dict(payload["embedding"], scales=edited.cpu().contiguous()),
                       provenance=dict(payload["provenance"], tag=TAG, calibration_steps=scale.STEPS,
                                       profile_sha256=digest(PROFILE), previous_packed_sha256=digest(ce.EXPORT)))
    del model, table, optimizer, edited
    torch.cuda.empty_cache()
    with EXPORT.open("xb") as stream:
        torch.save(trained, stream)
    reloaded = torch.load(EXPORT, map_location="cpu", weights_only=True)
    if not torch.equal(reloaded["embedding"]["codes"], payload["embedding"]["codes"]):
        raise ValueError("CE embedding codes changed")
    for previous, current in zip(payload["matrices"], reloaded["matrices"], strict=True):
        if previous["paths"] != current["paths"] or any(
                not torch.equal(previous["weight"][key], current["weight"][key]) for key in ("codes", "scales")):
            raise ValueError("CE body matrix changed")
    for previous, current in zip(payload["rest"], reloaded["rest"], strict=True):
        if previous["paths"] != current["paths"] or not torch.equal(previous["tensor"], current["tensor"]):
            raise ValueError("CE body tensor changed")
    candidate = ce.load_payload(reloaded, device="cuda", tile_rows=4096)
    if ce.evaluate(candidate, x, y, held) != final:
        raise ValueError("packed CE reload differs from the evaluation before save")
    return dict(history=history, packed_held=final, packed_sha256=digest(EXPORT), bytes=EXPORT.stat().st_size,
                changed_rows=len(changed), multipliers=limits, checkpoint_writes=0,
                median_update_seconds=median(row["seconds"] for row in history[4:]),
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved())


@torch.inference_mode()
def score_arm(name, path, choices):
    model = ce.load_payload(torch.load(path, map_location="cpu", weights_only=True),
                            device="cuda", tile_rows=4096).eval()
    scores = {}
    for task, inputs in choices.items():
        result = []
        for batch in inputs["batches"]:
            check_device()
            x = torch.tensor(batch["input_ids"], dtype=torch.long, device="cuda")
            y = torch.tensor(batch["labels"], dtype=torch.long, device="cuda")
            lengths = [len(tokens) for tokens in batch["continuation_ids"]]
            logits, gold = ce.logits(model, x, y)
            losses = F.cross_entropy(logits, gold, reduction="none")
            result.extend(-float(row.sum()) for row in losses.split(lengths))
            del logits, gold, losses
        if len(result) != 2 * len(inputs["gold"]) or not np.isfinite(result).all():
            raise ValueError("incomplete or invalid official choice scores")
        scores[task] = result
        print("P109_CE_SCALE_PANEL", name, task, len(inputs["gold"]), flush=True)
    return dict(scores=scores, model_sha256=digest(path), choice_sha256=digest(CHOICES))


def evaluate(profile):
    training = read(OUT / "train.json")
    if training["profile_sha256"] != digest(PROFILE) or training["packed_sha256"] != digest(EXPORT):
        raise ValueError("training receipt or matched CE artifact differs")
    choices = read(CHOICES)
    for name, model in MODELS.items():
        write(OUT / f"{name}_choices.json", score_arm(name, model, choices))
        torch.cuda.empty_cache()
    return dict(arms=list(MODELS), authored=profile["authored_held"])


def gpu(mode):
    check_window(150 if mode == "train" else 385)
    if not ce.idle() or torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 4 * 2**30:
        raise RuntimeError("one idle visible GPU and 4 GiB free required")
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    profile, pins = load_profile()
    device = OUT / f"{mode}_device_100ms.csv"
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*ce.DEVICE, f"--loop-ms={ce.INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                result = (train if mode == "train" else evaluate)(profile)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = ce.read_samples(device)
    if not samples or not pins.unchanged():
        raise RuntimeError("device samples missing or source changed")
    result.update(device_peak=max(samples, key=lambda row: row["occupied_mib"]), samples=len(samples),
                  device_sha256=digest(device), profile_sha256=digest(PROFILE))
    write(OUT / f"{mode}.json", result)
    print("P109_CE_SCALE_DONE", mode, result["device_peak"], flush=True)


def summarize():
    profile, pins = load_profile()
    training, evaluated = [read(OUT / f"{stage}.json") for stage in ("train", "evaluate")]
    for phase, recorded in (("train", training), ("evaluate", evaluated)):
        if (recorded["profile_sha256"] != digest(PROFILE) or
                recorded["device_sha256"] != digest(OUT / f"{phase}_device_100ms.csv")):
            raise ValueError("run bindings differ")
    choice = read(CHOICES)
    pairs = (("ce_48", "ce"), ("kd_48", "kd"), ("kd_48", "ce_48"))
    scored = {arm: read(OUT / f"{arm}_choices.json") for arm in MODELS}
    for arm, recorded in scored.items():
        if recorded["model_sha256"] != digest(MODELS[arm]) or recorded["choice_sha256"] != digest(CHOICES):
            raise ValueError("score bindings differ")
    rng = np.random.default_rng(65312026)
    report = {}
    for name, value in choice.items():
        gold = np.array(value["gold"])
        correct = {}
        for arm, result in scored.items():
            scores = np.array(result["scores"][name]).reshape(-1, 2)
            if len(scores) != len(gold) or not np.isfinite(scores).all() or (scores > 0).any():
                raise ValueError("invalid official scores")
            correct[arm] = (scores.argmax(1) == gold).astype(np.int8)
        contrasts = {}
        for arm, control in pairs:
            delta = correct[arm] - correct[control]
            values, counts = np.unique(delta, return_counts=True)
            drawn = rng.multinomial(len(delta), counts / len(delta), size=20000) @ values / len(delta)
            lo, hi = [float(q) for q in np.quantile(drawn, [0.05 / 12, 1 - 0.05 / 12])]
            contrasts[f"{arm}_minus_{control}"] = dict(delta=float(delta.mean()), ci_99_17=[lo, hi],
                                                      wins=int((delta > 0).sum()), losses=int((delta < 0).sum()))
        report[name] = dict(rows=len(gold), correct={arm: int(hit.sum()) for arm, hit in correct.items()},
                            contrasts=contrasts)
    pins.unchanged()
    write(OUT / "report.json", dict(official=report, authored=dict(profile["authored_held"],
               ce_48=training["packed_held"]), train_peak=training["device_peak"],
               eval_peak=evaluated["device_peak"], train_sha256=digest(OUT / "train.json")))
    print("P109_CE_SCALE_RECOUNT", {name: t["correct"] for name, t in report.items()}, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "train", "evaluate", "summarize"))
    mode = parser.parse_args().mode
    uses_gpu = mode in ("train", "evaluate")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if uses_gpu else ""):
        parser.error("select GPU 0 for execution or isolate preparation and recount")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if uses_gpu:
        gpu(mode)
    elif mode == "prepare":
        prepare()
    else:
        summarize()


if __name__ == "__main__":
    main()
