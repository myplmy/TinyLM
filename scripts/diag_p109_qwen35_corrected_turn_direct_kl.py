"""Run matched CE and same-token KL on authored G4 correction dialogues."""

import argparse
from datetime import datetime
import gc
import os
from pathlib import Path
from statistics import median
import subprocess
from time import perf_counter

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel
from tokenizers import Tokenizer

from scripts import diag_p106b_direct_kl_leading_newline as boundary
from scripts import diag_p109_qwen35_248k_warm_kl as warm
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
from tinylm.data.sft import encode_conversation, sft_targets


CE = warm.ce
ROOT = CE.ROOT
TAG = "p109_qwen35_248k_corrected_turn_direct_kl_v1_20261120"
OUT = CE.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
PLAN = ROOT / "test_plan/P109_16층-공유-재귀-프리셋-통합.md"
CUTOFF = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
WIDTH, STEPS, WARMUP, EOT = 128, 32, 4, 248046
ITEMS = (
    ("sapphire", "사파이어"), ("chalk", "분필"), ("silver", "은"), ("umbrella", "우산"),
    ("cotton", "면"), ("quartz", "석영"), ("map", "지도"), ("glass", "유리"),
)


def authored(index, language):
    tag = f"R{index + 123}"
    if index % 2 == 0:
        initial, removed = index + 52, index % 13 + 3
        en = (f"Shelf {tag} had {initial} boxes. We removed {removed}. How many boxes remain?",
              "That was the initial count. Subtract the removed boxes and write the remaining count.")
        ko = (f"{tag} 선반에 상자가 {initial}개 있었고 {removed}개를 꺼냈습니다. 몇 개 남았습니까?",
              "그 수는 처음 개수입니다. 꺼낸 수를 빼고 남은 개수만 쓰세요.")
        wrong, right = str(initial), str(initial - removed)
    else:
        left = (index // 2) % len(ITEMS)
        right_index = (left + 1 + (index // 16) % (len(ITEMS) - 1)) % len(ITEMS)
        en = (f"Box {tag} has {ITEMS[left][0]} on the left and {ITEMS[right_index][0]} on the right. Name the item on the right.",
              "Your answer names the left item. Look at the right side and give only that item.")
        ko = (f"{tag} 상자의 왼쪽에는 {ITEMS[left][1]}, 오른쪽에는 {ITEMS[right_index][1]}가 있습니다. 오른쪽 물건은 무엇입니까?",
              "왼쪽 물건을 답했습니다. 오른쪽에서 찾은 물건만 쓰세요.")
        offset = int(language == "ko")
        wrong, right = ITEMS[left][offset], ITEMS[right_index][offset]
    first, follow = en if language == "en" else ko
    answer = "\n\n" + right if index % 3 == 0 else right
    return [("user", first), ("assistant", wrong), ("user", follow), ("assistant", answer)]


def encode(index, lang, tokenizer, compact):
    messages = authored(index, lang)
    canonical = {"messages": [{"role": role, "content": text} for role, text in messages],
                 "meta": {"supervised_assistant_turns": [2]}}
    ids, labels, body = encode_conversation(canonical, tokenizer)
    rendered, spans = boundary.original.render(messages)
    encoded = tokenizer.encode(rendered, add_special_tokens=False)
    if rendered != body or list(encoded.ids) != ids or list(compact.encode(body).ids) != ids:
        raise ValueError("The canonical, teacher and compact input differ")
    alignment = boundary.mask_without_shared_lf(rendered, encoded, spans, EOT)
    expected = alignment["masks"][1]
    original_wrong = alignment["masks"][0]
    shifted = [tuple(pair) for pair in expected["content"] + expected["stop"]]
    missed = [item["token_index"] - 1 for item in alignment["skipped"]]
    x, y = sft_targets(ids, labels)
    if (len(x) > WIDTH or min(ids) < 0 or max(ids) >= CE.ASSIGNED or len(set(ids)) <= 4
            or [(i, v) for i, v in enumerate(y) if v != -100] != shifted
            or any(y[i] != -100 for i, _ in original_wrong["content"] + original_wrong["stop"])
            or any(y[i] != -100 for i in missed)
            or len(missed) != int(index % 3 == 0) or y.count(EOT) != 1):
        raise ValueError(f"Incorrect train/hold labels for R{index + 123} {lang}")
    return dict(group=index, language=lang, messages=[list(pair) for pair in messages],
                x=x, y=y, missing_lf_positions=missed)


def compile_inputs(teacher):
    tokenizer = Tokenizer.from_file(str(teacher / "tokenizer.json"))
    compact_path = CE.qwen.OUT / "qwen.qbpe"
    compact_config = CE.qwen.load(CE.qwen.OUT / "profile.json")
    if (CE.qwen.digest(teacher / "tokenizer.json") != compact_config["original_sha256"]
            or CE.qwen.digest(compact_path) != compact_config["compact_sha256"]):
        raise ValueError("The previously verified teacher/compact tokenizer changed")
    with CE.CompactQwenTokenizer(compact_path) as compact:
        pairs = [[encode(i, lang, tokenizer, compact) for lang in ("en", "ko")] for i in range(128)]
    pool, held = pairs[:-16], pairs[-16:]
    draws = pool[:STEPS]
    rows = [r for pair in draws for r in pair]
    total_pool = sum(len(r["x"]) for pair in pool for r in pair)
    real = sum(len(r["x"]) for r in rows)
    if total_pool < 2 * real or len({tuple(r["x"]) for pair in pairs for r in pair}) != 256:
        raise ValueError("Insufficient or duplicate authored dialogues")
    counts = {lang: sum(sum(v >= 0 for v in r["y"]) for r in rows if r["language"] == lang)
              for lang in ("en", "ko")}
    return dict(draws=draws, held=held, pool_tokens=total_pool, real_input_tokens=real,
                padded_input_tokens=len(rows) * WIDTH, target_by_language=counts,
                shared_lf_train=sum(len(r["missing_lf_positions"]) for r in rows))


def source_pins(teacher):
    involved = (
        Path(__file__), PLAN, Path(warm.__file__), Path(warm.joint.__file__), Path(CE.__file__),
        Path(CE.parent.__file__), Path(boundary.__file__), Path(boundary.original.__file__),
        ROOT / "tinylm/data/sft.py", ROOT / "tinylm/chat/serialize.py", CE.MAPPING, CE.PROFILE,
        CE.parent.PARENT, CE.qwen.OUT / "qwen.qbpe", teacher / "tokenizer.json",
        teacher / "model.safetensors.index.json", teacher / "config.json",
    )
    pins = {str(p.relative_to(ROOT)): CE.qwen.digest(p) for p in involved}
    index = CE.qwen.load(teacher / "model.safetensors.index.json")
    shards = sorted(set(index["weight_map"].values()))
    if not shards or any(Path(s).name != s for s in shards):
        raise ValueError("Resolve only the declared local teacher shards")
    pins.update({str((teacher / name).relative_to(ROOT)): CE.qwen.digest(teacher / name) for name in shards})
    return pins


def gate(reserve=0, *, device=False):
    if (CUTOFF - datetime.now(CUTOFF.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 time or stop marker")
    if device:
        free, total = torch.cuda.mem_get_info()
        if total - free > warm.DEVICE_BUDGET:
            raise RuntimeError("13 GB configured device occupancy reached")


def prepare():
    gate(900)
    teacher = warm.teacher_folder()
    inputs = compile_inputs(teacher)
    assert not torch.cuda.is_initialized()
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    CE.qwen.write(PROFILE, dict(tag=TAG, teacher=str(teacher.relative_to(ROOT)), pins=source_pins(teacher),
                               data=inputs, script_checkpoint_writes=0))
    print("P109_CORRECTION_KL_SEAL", inputs["real_input_tokens"], inputs["padded_input_tokens"],
          inputs["target_by_language"], inputs["shared_lf_train"], flush=True)


def make_batch(rows):
    sizes = torch.tensor([len(r["x"]) for r in rows], device="cuda")
    valid = torch.arange(WIDTH, device="cuda").unsqueeze(0) < sizes.unsqueeze(1)
    x = torch.tensor([r["x"] + [CE.EOS] * (WIDTH - len(r["x"])) for r in rows], device="cuda")
    y = torch.tensor([r["y"] + [-100] * (WIDTH - len(r["y"])) for r in rows], device="cuda")
    assert not (y.ge(0) & ~valid).any() and (valid & y.eq(-100)).any()
    return x, y, valid


def actual_parity(model, teacher, x, y, valid):
    mask = y.ge(0)
    target = y[mask]
    distribution, _ = warm.teacher_logits(teacher, x, mask)
    alternate, _ = warm.teacher_logits(teacher, x.masked_fill(~valid, 0), mask)
    if not torch.equal(distribution, alternate):
        raise ValueError("Teacher's valid response positions change with the right padding")
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)[mask]
    hidden = hidden.detach().requires_grad_()
    params = (hidden, model.emb.weight, model.emb_up.weight)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        scores = model._head_logits(hidden)[:, :CE.ASSIGNED].float()
        dense_ce = F.cross_entropy(scores, target)
        dense_kl = warm._kl(scores, distribution, warm.TEMPERATURE, "batchmean") * warm.TEMPERATURE**2
        tiled_ce, tiled_kl = warm.tiled_loss(model, hidden, target, distribution)
    dense = torch.autograd.grad(dense_ce + warm.ALPHA * dense_kl, params)
    tiled = torch.autograd.grad(tiled_ce + warm.ALPHA * tiled_kl, params)
    rel = [float((a.float() - b.float()).norm() / a.float().norm().clamp_min(1e-12))
           for a, b in zip(dense, tiled, strict=True)]
    errors = [abs(float((a - b).detach())) for a, b in ((dense_ce, tiled_ce), (dense_kl, tiled_kl))]
    model.clear_quant()
    if max(errors) > 0.001 or max(rel) > 0.01:
        raise ValueError(f"Actual response head parity gate failed: {errors=} {rel=}")
    return dict(padding_true_count=int((~valid).sum()), context_count=int((valid & ~mask).sum()),
                supervised=int(mask.sum()), right_pad_same=True, ce_kl_abs=errors, gradient_l2_rel=rel)


@torch.inference_mode()
def held_scores(model, pairs):
    metrics = {lang: dict(n=0, nll_sum=0., top1=0, eot_n=0, eot_top1=0) for lang in ("en", "ko")}
    model.eval()
    model.freeze_quant()
    try:
        for pair in pairs:
            gate(device=True)
            x, y, _ = make_batch(pair)
            hidden = model(x, return_hidden=True)
            for i, item in enumerate(pair):
                positions = y[i].ge(0)
                ids = y[i, positions]
                scores = model._head_logits(hidden[i, positions])[:, :CE.ASSIGNED].float()
                right = scores.argmax(1).eq(ids)
                eot = ids.eq(EOT)
                cell = metrics[item["language"]]
                cell["n"] += len(ids)
                cell["nll_sum"] += float(F.cross_entropy(scores, ids, reduction="sum"))
                cell["top1"] += int(right.sum())
                cell["eot_n"] += int(eot.sum())
                cell["eot_top1"] += int((right & eot).sum())
    finally:
        model.clear_quant()
        model.train()
    for row in metrics.values():
        row["nll"] = row["nll_sum"] / row["n"]
    return metrics


def learn(name, data, teacher_path=None):
    teacher = warm.load_teacher(teacher_path) if teacher_path else None
    torch.manual_seed(652017)
    model = CE.initialize()
    before_hash = state_fingerprint(model)
    before = held_scores(model, data["held"])
    parity = actual_parity(model, teacher, *make_batch(data["draws"][0])) if teacher else None
    routes = CE.build_experimental_optimizers(model, "muon_matched", lr=CE.LR, matrix_lr_mult=CE.MATRIX_MULT)
    optimizers = (routes.adamw, routes.matrix)
    CE.keep_active_groups(optimizers)
    rates = [[group["lr"] for group in opt.param_groups] for opt in optimizers]
    trace = []
    torch.cuda.reset_peak_memory_stats()
    for step, pair in enumerate(data["draws"], 1):
        gate(device=True)
        scale = CE.lr_factor(step - 1, WARMUP, STEPS, "cosine")
        for opt, rate in zip(optimizers, rates, strict=True):
            for group, base in zip(opt.param_groups, rate, strict=True):
                group["lr"] = base * scale
        x, y, _ = make_batch(pair)
        mask = y.ge(0)
        labels = y[mask]
        start = perf_counter()
        distribution = warm.teacher_logits(teacher, x, mask)[0] if teacher else None
        with torch.autocast("cuda", dtype=torch.bfloat16):
            hidden = model(x, return_hidden=True)[mask]
            if distribution is None:
                logits = model._head_logits(hidden)[:, :CE.ASSIGNED].float()
                primary = F.cross_entropy(logits, labels)
                kl = None
            else:
                primary, kl = warm.tiled_loss(model, hidden, labels, distribution)
        loss = primary if kl is None else primary + warm.ALPHA * kl
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        torch.cuda.synchronize()
        trace.append(dict(step=step, n=len(labels), ce=float(primary.detach()),
                          kl=None if kl is None else float(kl.detach()), grad=float(norm), seconds=perf_counter() - start))
    peak = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
    after = held_scores(model, data["held"])
    after_hash = state_fingerprint(model)
    if (len(trace) != STEPS or sum(r["n"] for r in trace) != sum(data["target_by_language"].values())
            or before_hash == after_hash):
        raise ValueError("Actual updates or target membership differ")
    return dict(arm=name, start_hash=before_hash, end_hash=after_hash, before=before, after=after,
                first_actual_parity=parity, trace=trace, peak_bytes=peak,
                median_update_seconds=median(r["seconds"] for r in trace[WARMUP:]))


def execute(profile, teacher):
    if compile_inputs(teacher) != profile["data"]:
        raise ValueError("Sealed authored data changed")
    results = {}
    for name, path in (("DIRECT_KL", teacher), ("CE", None)):
        results[name] = learn(name, profile["data"], path)
        CE.qwen.write(OUT / f"{name}.json", results[name])
        print("P109_CORRECTION_KL_ARM", name, results[name]["after"], flush=True)
        gc.collect()
        torch.cuda.empty_cache()
    if (results["CE"]["start_hash"] != results["DIRECT_KL"]["start_hash"]
            or results["CE"]["before"] != results["DIRECT_KL"]["before"]):
        raise ValueError("The two sessions did not start from the same student")
    return dict(arms=results, optimizer_updates=sum(len(r["trace"]) for r in results.values()),
                checkpoint_writes=0, pool_kind="AUTHORED_DISJOINT_CORRECTION_FIXTURES")


def run():
    gate(900)
    profile = CE.qwen.load(PROFILE)
    teacher = ROOT / profile["teacher"]
    if source_pins(teacher) != profile["pins"] or CE.qwen.digest(OUT / "plan_at_execution.md") != profile["pins"][str(PLAN.relative_to(ROOT))]:
        raise ValueError("The exact source or asset changed")
    entry = require_idle_gpu()
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    trace = OUT / "device_100ms.csv"
    with trace.open("xb") as file:
        monitor = subprocess.Popen((*CE.DEVICE, "--loop-ms=100"), stdout=file)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                result = execute(profile, teacher)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    gc.collect()
    close_owned_cuda(torch, result)
    samples = CE.read_samples(trace)
    if not samples or source_pins(teacher) != profile["pins"]:
        raise ValueError("Missing device samples or changed source")
    result.update(tag=TAG, entry=entry, resource_samples=len(samples),
                  resource_peak=max(r["occupied_mib"] for r in samples), profile_sha256=CE.qwen.digest(PROFILE))
    CE.qwen.write(OUT / "report.json", result)
    print("P109_CORRECTION_KL_RESULT", result["optimizer_updates"], result["resource_peak"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    mode = parser.parse_args().phase
    expected = "0" if mode == "run" else ""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected or (expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8"):
        parser.error("Use the explicit isolated CPU/approved CUDA environment")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (run if expected else prepare)()
