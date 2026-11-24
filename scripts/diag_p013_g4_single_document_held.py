"""Recover the Stage7W weights to test unseen single-document 1024-token context."""

import argparse
from datetime import datetime
import gc
import os
from pathlib import Path
import subprocess
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel
from tokenizers import Tokenizer

from scripts import diag_p013_g4_document_context as original
from scripts.diag_p107_hybrid_mntp import close_owned_cuda


ROOT = original.ROOT
TAG = "p013_g4_single_document_held_v1_20261119"
OUT = original.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
WIDTH, TAIL, SHORT, PROMPT, MAX_NEW = 1024, 64, 128, 992, 32
CASES = {
    "en": ("copper heron", "\n\nIn the North Basin operator's book, the exact two-word name of the card exchange procedure was"),
    "ko": ("푸른 등대", "\n\n관측소 일지에서 정전 뒤 시각을 다음 교대에 넘기는 절차의 정식 이름은"),
}
ARCHIVE = {
    "profile.json": "F32AE672E477A5EE3838B7E0387BECB756886D2515F6AB066DE361BE123ECF5F",
    "report.json": "615848FBEC183D26463DB978F96016B810075BC3C2B0B1775089D43B905594D5",
    "draws.npz": "D629A7CC7A09BCE5B9C47D31DA354D65C500AD5B0EE43889C307DC445B3D65A2",
    "plan_at_execution.md": "01CD9C1B49C3C7498B9B533881223D3532F6530C2249B39CB71CE785C12645E4",
}
REVIEWED_LIVE_PINS = {
    "tinylm/train/document_context_curriculum.py": "417D9F6C7CC54A185966335A97E067ADA2EEE4C4E35E56CEC2A061B6FF1AC39D",
    "tinylm/model/transformer.py": "75F305C23CB7C5E0D03926F8D1B81A06A7FFE7F5738ACF002D24160E76E374A9",
    "tinylm/model/visibility.py": "73DCF0B8E7279B614F9758556A80F2EE4B97CD3B66D0E201A17E7AAB19736FBB",
}


def gate(reserve=0):
    if (OUT / "STOP").exists() or (original.END - datetime.now(original.END.tzinfo)).total_seconds() <= reserve:
        raise TimeoutError("User 177 time window or local stop reached")


def verify_sources():
    archived = {original.OUT / name: expected for name, expected in ARCHIVE.items()}
    for path, expected in archived.items():
        if original.manual.file_sha(path) != expected:
            raise ValueError(f"Stage7W archive differs: {path.name}")
    old = original.read(original.PROFILE)
    previous = original.read(original.OUT / "report.json")
    if previous["profile_sha256"] != ARCHIVE["profile.json"] or not previous["source_preserved"] or previous["checkpoint_writes"]:
        raise ValueError("Stage7W must be a completed no-checkpoint comparison")
    live = original.sources()
    expected_live = old["sources"] | REVIEWED_LIVE_PINS
    plan_key = original.PLAN.relative_to(ROOT).as_posix()
    expected_live[plan_key] = live[plan_key]
    if live != expected_live:
        raise ValueError(f"Unknown Stage7W source changes: {sorted(key for key in live if live[key] != expected_live.get(key))}")
    if original.manual.file_sha(original.warm.PARENT) != old["parent_sha256"]:
        raise ValueError("P079 parent differs")
    paths = (
        Path(__file__), Path(close_owned_cuda.__code__.co_filename),
        *(ROOT / name for name in original.warm.SOURCES),
        *(OUT / f"held_{lang}.txt" for lang in CASES),
    )
    live.update({path.resolve().relative_to(ROOT).as_posix(): original.manual.file_sha(path) for path in paths})
    return old, previous, live


def windows(ids, size):
    return {tuple(ids[index:index + size]) for index in range(len(ids) - size + 1)}


def build_cases(tokenizer):
    documents = original.read(original.SOURCE / "profile.json")["data"]["documents"]
    train = [row for row in documents if row["split"] == "train"]
    if len(train) != 768:
        raise ValueError("Original source split differs")
    train_windows = set().union(*(windows(tokenizer.encode(row["text"], add_special_tokens=False).ids, 16) for row in train))
    result = {}
    for language, (answer, query) in CASES.items():
        source = (OUT / f"held_{language}.txt").read_text(encoding="utf-8")
        ids = tokenizer.encode(source, add_special_tokens=False).ids
        query_ids = tokenizer.encode(query, add_special_tokens=False).ids
        prompt = ids[:PROMPT - len(query_ids)] + query_ids
        if len(ids) <= WIDTH or len(prompt) != PROMPT or len(set(ids[:WIDTH])) < WIDTH // 8:
            raise ValueError(f"{language}: a substantial unpadded single document is required, found {len(ids)} tokens")
        overlap = len(windows(ids, 16) & train_windows)
        extended = tokenizer.decode(prompt, skip_special_tokens=False)
        short = tokenizer.decode(prompt[-SHORT:], skip_special_tokens=False)
        if overlap or extended.casefold().count(answer) != 1 or answer in short.casefold():
            raise ValueError(f"{language}: document separation or distant answer contract failed")
        result[language] = dict(total_tokens=len(ids), validation_ids=ids[:WIDTH + 1], prompt_ids=prompt,
                                query=query, answer=answer, train_shared_16grams=overlap)
    return result


def prepare():
    gate()
    old, _, live = verify_sources()
    tokenizer = Tokenizer.from_file(str(original.TOKENIZER))
    cases = build_cases(tokenizer)
    if torch.cuda.is_initialized():
        raise ValueError("CPU preparation must not initialize CUDA")
    with (OUT / "plan_at_execution.md").open("xb") as file:
        file.write(original.PLAN.read_bytes())
    profile = dict(tag=TAG, user_directive=177, sources=live, archive=ARCHIVE, cases=cases,
                   parent_sha256=old["parent_sha256"], eos_id=tokenizer.token_to_id("<eos>"),
                   full_context=WIDTH, short_context=SHORT, shared_tail_targets=TAIL,
                   prompt_tokens=PROMPT, generation_cap=MAX_NEW, checkpoint_writes=0, official_quality=False)
    original.write(PROFILE, profile)
    print("P013_SINGLE_DOCUMENT_SEAL", {key: row["total_tokens"] for key, row in cases.items()}, flush=True)


def causal_logits(model, inputs):
    mask = original.document_visibility(torch.zeros_like(inputs), bidirectional=False)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        return model(inputs, attention_mask=mask)


@torch.no_grad()
def evaluate(model, profile, tokenizer):
    model.eval()
    torch.cuda.synchronize()
    start = perf_counter()
    rows = {}
    for language, case in profile["cases"].items():
        gate(25)
        ids = torch.tensor([case["validation_ids"]], device="cuda")
        targets = ids[0, -TAIL:]
        results = {}
        for width in (WIDTH, SHORT):
            tokens = ids[:, -(width + 1):-1]
            logits = causal_logits(model, tokens)[0, -TAIL:].float()
            losses = F.cross_entropy(logits, targets, reduction="none")
            predicted = logits.argmax(dim=-1)
            results[str(width)] = dict(nll=float(losses.mean()), correct=int(predicted.eq(targets).sum()),
                                       last_nll=float(losses[-1]), last_prediction_id=int(predicted[-1]))
        prompt = torch.tensor([case["prompt_ids"]], device="cuda")
        answer_ids = []
        stop = "length"
        for _ in range(MAX_NEW):
            suffix = causal_logits(model, prompt)[:, -1, :].argmax(dim=-1, keepdim=True)
            token = int(suffix.item())
            answer_ids.append(token)
            prompt = torch.cat((prompt, suffix), dim=1)
            if token == profile["eos_id"]:
                stop = "eos"
                break
        rows[language] = dict(target_count=TAIL, final_target_id=case["validation_ids"][-1], metrics=results,
                              expected=case["answer"], generated_ids=answer_ids, stop=stop,
                              generated_text=tokenizer.decode(answer_ids, skip_special_tokens=False),
                              final_prefix_and_output_tokens=prompt.shape[1])
    torch.cuda.synchronize()
    return dict(rows=rows, wall_seconds=perf_counter() - start)


def recover_arms(profile, old, previous, tokenizer):
    arms = {}
    parent = None
    with (np.load(original.BATCHES, allow_pickle=False) as arrays,
          patch.object(original.transformer, "prepare_visibility", original.r2.prepare_r2),
          sdpa_kernel(SDPBackend.MATH)):
        for name, plan in (("fixed", original.FIXED), ("staged", original.STAGED)):
            gate(90)
            expected = previous["arms"][name]

            def readback(model, _arrays, generate=False):
                nonlocal parent
                state = original.manual.state_fingerprint(model)
                if state != expected["final" if generate else "initial"]:
                    raise ValueError(f"{name}: old weight fingerprint differs before new evaluation")
                if generate:
                    return evaluate(model, profile, tokenizer)
                if parent is None:
                    parent = evaluate(model, profile, tokenizer)
                    original.write(OUT / "parent.json", parent)
                return {"reused_parent": True}

            with patch.object(original, "held_readback", readback):
                result = original.train(name, plan, old, arrays)
            if [row["targets"] for row in result["history"]] != [row["targets"] for row in expected["history"]]:
                raise ValueError(f"{name}: replay target sequence differs")
            arms[name] = dict(initial=result["initial"], final=result["final"], updates=result["updates"],
                              history=result["history"], training_peak=result["training_peak"], long_held=result["held_after"])
            original.write(OUT / f"{name}.json", arms[name])
            gc.collect()
            torch.cuda.empty_cache()
    return parent, arms


def actual():
    gate(240)
    profile = original.read(PROFILE)
    old, previous, live = verify_sources()
    if profile["sources"] != live or profile["archive"] != ARCHIVE:
        raise ValueError("The new held data or execution sources differ from CPU preflight")
    if original.manual.file_sha(OUT / "plan_at_execution.md") != live[original.PLAN.relative_to(ROOT).as_posix()]:
        raise ValueError("Execution plan snapshot differs")
    tokenizer = Tokenizer.from_file(str(original.TOKENIZER))
    if profile["cases"] != build_cases(tokenizer):
        raise ValueError("Sealed long inputs differ")
    entry = original.manual.require_idle_gpu()
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 10 * (1 << 30):
        raise MemoryError("The single GPU needs at least 10 GiB free")
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    csv = OUT / "device_100ms.csv"
    with csv.open("xb") as stream:
        sampler = subprocess.Popen((*original.sampling.DEVICE, "--loop-ms=100"), stdout=stream)
        try:
            parent, arms = recover_arms(profile, old, previous, tokenizer)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = original.sampling.read_samples(csv)
    report = dict(tag=TAG, profile_sha256=original.manual.file_sha(PROFILE), entry=entry,
                  parent=parent, arms=arms, sampled_card_peak=max(row["occupied_mib"] for row in samples),
                  sample_count=len(samples), short_held_reexecutions=0, checkpoint_writes=0)
    close_owned_cuda(torch, report)
    report["source_preserved"] = verify_sources()[2] == live
    if not report["source_preserved"]:
        raise ValueError("An original or new input differs after execution")
    original.write(OUT / "report.json", report)
    print("P013_SINGLE_DOCUMENT_RESULT", report["sampled_card_peak"], [x["final"] for x in arms.values()], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual"))
    args = parser.parse_args()
    device = "0" if args.phase == "actual" else ""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != device:
        parser.error("Use isolated CPU preparation and the authorized CUDA device")
    if device and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS is required")
    (actual if device else prepare)()


if __name__ == "__main__":
    main()
