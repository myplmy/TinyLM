"""Measure periodic restoration of original G4 edits during matched learning."""

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
from time import perf_counter
from types import SimpleNamespace
import unicodedata

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_master_margin_authored as old
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.interactive_research_infer import require_idle_gpu


prior = old.prior
ROOT = prior.ROOT
TAG = "p108_g4_ternary_reapply_v1_20261119"
OUT = old.OUT.with_name(TAG)
PLAN = ROOT / "test_plan/P108_직접가중치-방향수리와-학습개입.md"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
SCHEDULES = {"initial_only": (), "middle": (88,), "quarters": (44, 88, 132)}
MAX_CARD_BYTES = 13_000_000_000
ARCHIVE = {
    "profile.json": "C76D129FCE6A9852F0AB17D5AADC66A12BCCBE47AF55446761C51CD220F1343B",
    "report.json": "04D76DF9FC0DA86363A1EE405A44B308861292B9BB7877F1E375A9320BCA259D",
    "data.pt": "CC0C3CB3205749B46B49F1946206EF2A40AE0F8CF0E784489615D749CCC5B86C",
}
CURRENT_TRANSFORMER = "75F305C23CB7C5E0D03926F8D1B81A06A7FFE7F5738ACF002D24160E76E374A9"
TRACE_FIELDS = ("ce", "norm", "targets", "trits", "path_l2")
PROMPTS = {
    "en": (
        "The storage register lists an item for {name}. Give its item name only.\nItem:",
        "Fill in the missing item in this line of the inventory. Record {name} has:",
    ),
    "ko": (
        "보관 목록에서 {name}에 해당하는 물품을 찾으세요. 물품 이름만 쓰세요.\n이름:",
        "재고 대장의 빈칸에 들어갈 물품명만 답하세요. 기록 {name}의 물품은",
    ),
}


def gate(reserve=0):
    if (OUT / "STOP").exists() or (END - datetime.now(END.tzinfo)).total_seconds() <= reserve:
        raise TimeoutError("User 177 time limit or local stop reached")


def source_pins():
    for name, expected in ARCHIVE.items():
        if prior.sha(old.OUT / name) != expected:
            raise ValueError(f"Archived P108 StageOwnerContinueX {name} differs")
    legacy = prior.read(old.PROFILE)
    pins = legacy["pins"] | {"tinylm/model/transformer.py": CURRENT_TRANSFORMER}
    for name, expected in pins.items():
        if prior.sha(ROOT / name) != expected:
            raise ValueError(f"Unreviewed change in the reference route: {name}")
    if prior.sha(prior.PARENT) != prior.frozen.PARENT_SHA:
        raise ValueError("The original P079 checkpoint differs")
    additions = (
        Path(__file__).resolve(), PLAN, Path(close_owned_cuda.__code__.co_filename).resolve(),
        Path(require_idle_gpu.__code__.co_filename).resolve(),
    )
    pins.update({p.relative_to(ROOT).as_posix(): prior.sha(p) for p in additions})
    return pins


@torch.no_grad()
def restore_codes(weight, cfg, indices, desired):
    raw = weight.flatten()
    before = prior.ternary(weight, cfg).flatten()
    before_sign = before.sign()
    selected = before_sign[indices].ne(desired)
    missing = indices[selected]
    result = dict(restored=missing.tolist(), master_l2=0., effective_l2=0.,
                  other_codes_changed=0, retained_codes_rescaled=0)
    if not missing.numel():
        return result
    width = cfg.micro_group
    groups = missing // width
    start = raw[missing].clone()
    for group in groups.unique().tolist():
        local = groups == group
        positions = missing[local]
        # Solve a >= ratio * (other magnitudes + k*a) / group_width.
        remaining = raw[group * width:(group + 1) * width].abs().sum() - start[local].abs().sum()
        minimum = cfg.twn_thr_ratio * remaining / (width - cfg.twn_thr_ratio * int(local.sum()))
        amplitude = minimum * 1.02 + torch.finfo(raw.dtype).eps
        raw[positions] = desired[selected][local] * amplitude
    after = prior.ternary(weight, cfg).flatten()
    after_sign = after.sign()
    if not torch.equal(after_sign[indices], desired.to(after_sign.dtype)):
        raise ValueError("The grouped threshold repair must restore all designated codes")
    changed = before_sign.ne(after_sign)
    changed[missing] = False
    result.update(master_l2=float((raw[missing] - start).norm()), effective_l2=float((after - before).norm()),
                  other_codes_changed=int(changed.sum()),
                  retained_codes_rescaled=int((before.ne(after) & before_sign.eq(after_sign)).sum()))
    return result


def verify_cpu_contract():
    cfg = SimpleNamespace(micro_group=128, twn_thr_ratio=.7, ste_clip=1.3, sparse34=False)
    weight = torch.ones((1, 128), dtype=torch.float32)
    weight[0, :2] = torch.tensor([.1, -.2])
    indices = torch.tensor([0, 1, 2])
    desired = torch.tensor([-1, 1, 1])
    receipt = restore_codes(weight, cfg, indices, desired)
    assert receipt["restored"] == [0, 1] and receipt["other_codes_changed"] == 0
    assert receipt["master_l2"] > 0 and receipt["effective_l2"] > 0
    assert receipt["retained_codes_rescaled"] == 126
    snapshot = weight.clone()
    assert restore_codes(weight, cfg, indices, desired)["restored"] == [] and torch.equal(weight, snapshot)
    return receipt


def read_cpu_data():
    raw = torch.load(old.DATA, map_location="cpu", weights_only=True)
    draws = raw["draws"]
    supervision = raw["y"][draws].ne(-100)
    if (tuple(draws.shape) != (old.STEPS, old.BATCH) or draws.unique().numel() != 352
            or supervision.sum((0, 2)).tolist() != [5487, 6012] or raw["x"].shape[1] != old.WIDTH):
        raise ValueError("The original authored draw order or observed target counts differ")
    return raw


def prepare():
    gate()
    pins = source_pins()
    receipt = verify_cpu_contract()
    raw = read_cpu_data()
    prior_profile = prior.read(old.PROFILE)
    previous = {entry["prompt"] for entry in prior_profile["open_prompts"]}
    cases = [
        dict(language=lang, fact=name, expected=(en if lang == "en" else ko)[correct],
             text=template.format(name=name))
        for lang, templates in PROMPTS.items()
        for template in templates
        for name, en, ko, correct in prior.FACTS
    ]
    if len({c["text"] for c in cases}) != 24 or previous.intersection(c["text"] for c in cases):
        raise ValueError("The first-answer panel must contain 24 new question surfaces")
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU preparation opened CUDA")
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    prior.write(OUT / "profile.json", dict(tag=TAG, user_directive=177, pins=pins,
                schedules={name:list(schedule) for name,schedule in SCHEDULES.items()}, archive=ARCHIVE,
                cases=cases, draw_sha256=prior.state_sha(raw["draws"]), cpu_fixture=receipt,
                cuda_evidence="ARM_EXECUTION_REQUIRED", checkpoint_writes=0))
    print("P108_REAPPLY_CPU", raw["draws"].shape, len(cases), receipt, flush=True)


def matched_trace(left, right, until):
    return [tuple(r[k] for k in TRACE_FIELDS) for r in left[:until]] == [
        tuple(r[k] for k in TRACE_FIELDS) for r in right[:until]
    ]


@torch.no_grad()
def generate_answers(model, tok, profile):
    model.eval()
    model.freeze_quant()
    answers = []
    try:
        for case in profile["cases"]:
            gate()
            prompt = case["text"]
            prefix = tok.decode(tok.encode(prompt).ids)
            text, meta = old.sample(model, model.cfg, tok, prompt, max_new=16, temperature=0., top_k=0,
                                    device="cuda", logits_last_only=True, return_metadata=True)
            if not text.startswith(prefix):
                raise ValueError("The generation result lost the expected prefix")
            answer = text[len(prefix):]
            normalized = unicodedata.normalize("NFC", answer.casefold()).strip().rstrip(".。").strip()
            answers.append(dict(**case, answer=answer, correct=normalized == case["expected"].casefold(),
                                finish=meta["finish_reason"]))
    finally:
        model.clear_quant()
    return answers


def train(name, schedule, data, tok, profile, indices, original_sign, archive, control):
    model, down = prior.load_model()
    if not torch.equal(prior.read_edit(model, down, indices)[1], original_sign):
        raise ValueError("The original 64 active signs differ")
    initial = prior.install(model, down, indices, old.WATCH)
    if prior.state_sha(prior.ternary(down.weight.detach(), model.cfg)) != archive["effective_sha256"]:
        raise ValueError("The initial installed edit differs from the earlier experiment")
    desired = -original_sign
    previous, codes, _ = prior.read_edit(model, down, indices)
    uninterrupted = codes.eq(desired)
    route = prior.build_experimental_optimizers(model, "muon_matched", lr=prior.LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    prior.keep_active_groups(optimizers)
    rates = [[g["lr"] for g in opt.param_groups] for opt in optimizers]
    path = 0.
    history, events = [], []
    torch.cuda.reset_peak_memory_stats()
    for step, rows in enumerate(data["draws"], 1):
        gate()
        free, total = torch.cuda.mem_get_info()
        if total - free > MAX_CARD_BYTES:
            raise MemoryError("13 GB device occupancy boundary reached")
        start = perf_counter()
        model.train()
        factor = prior.lr_factor(step - 1, 4, old.STEPS, "cosine")
        for opt, values in zip(optimizers, rates, strict=True):
            for group, lr in zip(opt.param_groups, values, strict=True):
                group["lr"] = lr * factor
        scores, target = old.logits(model, data["x"][rows], data["y"][rows], True)
        loss = F.cross_entropy(scores, target)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        value, codes, _ = prior.read_edit(model, down, indices)
        path += float((value - previous).norm())
        uninterrupted &= codes.eq(desired)
        row = dict(step=step, targets=len(target), norm=float(norm), ce=float(loss.detach()),
                   trits=codes.tolist(), before_restore=int(codes.eq(desired).sum()),
                   uninterrupted=int(uninterrupted.sum()), path_l2=path)
        history.append(row)
        if step in schedule:
            if not events and not matched_trace(history, control["history"], step):
                raise ValueError(f"{name}: matched control differs before the first intervention")
            event = restore_codes(down.weight, model.cfg, indices, desired)
            event["step"] = step
            events.append(event)
            value, codes, _ = prior.read_edit(model, down, indices)
        previous = value
        row["after_restore"] = int(codes.eq(desired).sum())
        row["seconds"] = perf_counter() - start
        del scores, loss, norm
        if step in (44, 88, 132, old.STEPS):
            print("P108_REAPPLY_STEP", name, step, row["before_restore"], row["after_restore"], flush=True)
    if sum(row["targets"] for row in history) != 11499:
        raise ValueError("The actual supervised denominator differs")
    replay = name == "initial_only" and matched_trace(history, archive["history"], old.STEPS)
    held = archive["checks"][str(old.STEPS)] if replay else old.inspect(model, data, tok, profile, False)
    held = {key: held[key] for key in ("held", "choices")}
    answers = generate_answers(model, tok, profile)
    return dict(initial=initial, history=history, events=events, held=held, archive_metrics_reused=replay,
                answers=answers, final_state_sha256=prior.state_sha(model.state_dict()),
                master_edit_l2=initial["master_l2"] + sum(event["master_l2"] for event in events),
                master_optimizer_l2=path, peak_allocated=torch.cuda.max_memory_allocated(),
                peak_reserved=torch.cuda.max_memory_reserved(), checkpoint_writes=0)


def run():
    gate(480)
    profile = prior.read(OUT / "profile.json")
    pins = source_pins()
    if (profile["pins"] != pins or profile["archive"] != ARCHIVE
            or prior.sha(OUT / "plan_at_execution.md") != pins[PLAN.relative_to(ROOT).as_posix()]):
        raise ValueError("The sealed runtime, documents or execution plan differ")
    raw = read_cpu_data()
    if prior.state_sha(raw["draws"]) != profile["draw_sha256"]:
        raise ValueError("The sealed draw order differs")
    entry = require_idle_gpu()
    data = {k:tuple(x.cuda() for x in v) if k == "panel" else v.cuda() for k,v in raw.items()}
    tok = old.Tokenizer.from_file(str(prior.frozen.TOKENIZER))
    selection = prior.read(old.SELECTION)
    indices = torch.tensor(selection["indices"][:old.WATCH], device="cuda")
    original_sign = torch.tensor(selection["original_signs"][:old.WATCH], dtype=torch.int8, device="cuda")
    if len(indices.unique()) != old.WATCH or not bool(original_sign.abs().eq(1).all()):
        raise ValueError("Expected 64 unique originally active positions")
    archive = prior.read(old.OUT / "report.json")["arms"]["flip"]
    measurements = {}
    csv = OUT / "device_100ms.csv"
    with csv.open("xb") as stream:
        sampler = subprocess.Popen((*old.audit.DEVICE, f"--loop-ms={old.audit.INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                for name, schedule in SCHEDULES.items():
                    gate(90)
                    result = train(name, schedule, data, tok, profile, indices, original_sign, archive,
                                   measurements.get("initial_only"))
                    prior.write(OUT / f"{name}.json", result)
                    measurements[name] = result
                    torch.cuda.empty_cache()
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = old.audit.read_samples(csv)
    report = dict(tag=TAG, entry=entry, arms=measurements, checkpoint_writes=0, sampled_rows=len(samples),
                  device_peak=max(samples, key=lambda sample: sample["occupied_mib"]),
                  source_preserved=source_pins() == pins, profile_sha256=prior.sha(OUT / "profile.json"))
    if not report["source_preserved"]:
        raise ValueError("Inputs changed during the comparison")
    del data, indices, original_sign
    close_owned_cuda(torch, report)
    prior.write(OUT / "report.json", report)
    print("P108_REAPPLY_RESULT", report["device_peak"],
          {name: (arm["history"][-1]["after_restore"], sum(ans["correct"] for ans in arm["answers"]))
           for name, arm in measurements.items()}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    args = parser.parse_args()
    expected = "0" if args.phase == "run" else ""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use isolated CPU preparation and the authorized CUDA device")
    if expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS is required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (run if expected else prepare)()
