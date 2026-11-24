"""Produce resumable, unscored IFEval replies using the pinned native G4 body."""

import argparse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import monotonic

import torch
from tokenizers import Tokenizer

from scripts.diag_p102a_g4_joint_ce_kl_batch8 import DEVICE, read_samples
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.diag_p109_warm_visit_routes import PARENT
from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
from tinylm.infer.generate import load_model, sample
from tinylm.model.modules import build_rope


ROOT = Path(__file__).resolve().parents[1]
TAG = "p106b_ifeval_p079_runtime1280_v1_20261120"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
PARTS = OUT / "parts"
PLAN = ROOT / "test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md"
ASSETS = ROOT / "data_cache/p106b_official_eval_assets/ifeval_google_966cd895_20261117"
AUDIT = ROOT / "handoff/audit/research_20261118_01a1e647/IFEVAL541_DATA_ADMISSION_v1.json"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768.json"
DEADLINE = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
OUTPUT_CAP, MAX_BATCH, EOS = 1280, 24, 2


def digest(path):
    stamp = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            stamp.update(chunk)
    return stamp.hexdigest().upper()


def load(path):
    if path.is_symlink():
        raise ValueError(f"Symbolic receipt refused: {path.name}")
    return json.loads(path.read_bytes())


def publish(path, payload):
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent) as f:
        json.dump(payload, f, ensure_ascii=False, allow_nan=False)
        print(file=f)
        f.flush()
        os.fsync(f.fileno())
        os.link(f.name, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def pins():
    source = [
        Path(__file__), AUDIT, ASSETS / "manifest.json", ASSETS / "ifeval_input_data.jsonl", TOKENIZER, PARENT,
        ROOT / "tinylm/infer/generate.py", ROOT / "tinylm/model/transformer.py",
        ROOT / "tinylm/model/modules.py", ROOT / "tinylm/model/ternary.py", ROOT / "tinylm/config.py",
    ]
    manifest = load(ASSETS / "manifest.json")
    for name, expected in manifest["local_scorer_source_pins"].items():
        if name.endswith("/ifeval.yaml"):
            task = ROOT / name
            fields = set(task.read_text(encoding="utf-8").splitlines())
            expected_fields = {"task: ifeval", "doc_to_text: prompt", "num_fewshot: 0", "  until: []",
                               "  do_sample: false", "  temperature: 0.0", f"  max_gen_toks: {OUTPUT_CAP}"}
            if expected != digest(task) or not expected_fields <= fields:
                raise ValueError("Pinned official generation settings differ")
            source.append(task)
            break
    else:
        raise ValueError("Pinned IFEval task source is absent")
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in source}


def prepare():
    audit = load(AUDIT)
    manifest = load(ASSETS / "manifest.json")
    owned = pins()
    raw_path = ASSETS / "ifeval_input_data.jsonl"
    if (owned[(ASSETS / "manifest.json").relative_to(ROOT).as_posix()] != audit["asset_manifest_sha256"]
            or owned[raw_path.relative_to(ROOT).as_posix()] != audit["dataset_sha256"]
            or manifest["usage"] != "EVALUATION_ONLY" or manifest["revision"] != audit["revision"]):
        raise ValueError("Exact previously admitted evaluation-only input required")
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    if tokenizer.get_vocab_size() != 32768 or tokenizer.token_to_id("<eos>") != EOS:
        raise ValueError("Expected pinned P079 tokenizer and EOS")
    groups = defaultdict(list)
    seen = set()
    for line in raw_path.read_bytes().splitlines():
        row = json.loads(line)
        prompt, key = row["prompt"], row["key"]
        ids = tokenizer.encode(prompt, add_special_tokens=False).ids
        if key in seen or not ids or tokenizer.encode(prompt).ids != ids:
            raise ValueError("Duplicate key or implicit prompt token")
        seen.add(key)
        groups[len(ids)].append(dict(key=key, ids=ids))
    if len(seen) != 541:
        raise ValueError("No evaluation row may be added, dropped or reordered within a group")
    batches = [rows[i:i + MAX_BATCH] for _, rows in sorted(groups.items(), reverse=True)
               for i in range(0, len(rows), MAX_BATCH)]
    plan = PLAN.read_bytes()
    OUT.mkdir()
    PARTS.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(plan)
    assert not torch.cuda.is_initialized()
    publish(PROFILE, dict(tag=TAG, approval="WIP177_EVAL_ONLY", pins=owned,
                          plan_sha256=sha256(plan).hexdigest().upper(), revision=audit["revision"],
                          capacity=max(groups) + OUTPUT_CAP, generation_cap=OUTPUT_CAP,
                          groups=batches, rows=len(seen), lengths=[min(groups), max(groups)]))
    print("IFEVAL_SEALED", len(seen), len(batches), min(groups), max(groups), max(groups)+OUTPUT_CAP, flush=True)


class WindowEnded(RuntimeError):
    pass


class Window:
    def __init__(self):
        self.end = monotonic() + 3500

    def check(self):
        if monotonic() >= self.end or datetime.now(DEADLINE.tzinfo) >= DEADLINE or (OUT / "STOP").exists():
            raise WindowEnded("Window, deadline or stop marker")
        free, total = torch.cuda.mem_get_info()
        if total - free > 13_000_000_000:
            raise WindowEnded("13 GB occupancy boundary")


@contextmanager
def execution_context(model, capacity):
    cfg = model.cfg
    native = cfg.max_seq_len
    old_cos, old_sin = model.rope_cos, model.rope_sin
    cos, sin = (x.to(old_cos.device) for x in build_rope(cfg.head_dim, capacity, cfg.rope_theta))
    if not (torch.equal(old_cos, cos[:native]) and torch.equal(old_sin, sin[:native])):
        raise ValueError("Extended RoPE changed the original positions")
    cfg.max_seq_len = capacity
    model.rope_cos, model.rope_sin = cos, sin
    try:
        yield
    finally:
        cfg.max_seq_len = native
        model.rope_cos, model.rope_sin = old_cos, old_sin


def past_length(past):
    return next(iter(past.values()))[0].shape[2]


@torch.inference_mode()
def replies(model, tokenizer, cases, limit, window):
    lengths = {len(r["ids"]) for r in cases}
    if len(lengths) != 1:
        raise ValueError("Aligned unpadded input required")
    prompt_length = next(iter(lengths))
    if prompt_length + limit > model.cfg.max_seq_len:
        raise ValueError("Aligned unpadded input and full generation window required")
    xin = torch.tensor([item["ids"] for item in cases], device="cuda")
    out, done = [[] for _ in cases], [False] * len(cases)
    past = None
    last_context = 0
    for step in range(limit):
        if step % 16 == 0:
            window.check()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits, past = model(xin, past_kv=past, use_cache=True, logits_last_only=True)
        last_context = past_length(past)
        if last_context != prompt_length + step:
            raise ValueError("Unexpected context or cache reset")
        next_token = logits[:, -1, :].float().argmax(-1)
        for i, token in enumerate(next_token.tolist()):
            if not done[i]:
                out[i].append(token)
                done[i] = token == EOS
        if all(done):
            break
        xin = next_token.unsqueeze(1)
    return [
        dict(key=case["key"], output_ids=ids,
             answer=tokenizer.decode(ids, skip_special_tokens=True), finish="EOS" if stop else "MAX_NEW",
             prompt_tokens=len(case["ids"]))
        for case, ids, stop in zip(cases, out, done, strict=True)
    ], last_context


@torch.inference_mode()
def boundary_proof(model, case, capacity):
    ids = case["ids"] + [case["ids"][-1]] * (capacity - len(case["ids"]))
    x = torch.tensor([ids], device="cuda")
    with torch.autocast("cuda", dtype=torch.bfloat16):
        _, cache = model(x[:, :-1], use_cache=True, logits_last_only=True)
        before = past_length(cache)
        logits, cache = model(x[:, -1:], past_kv=cache, use_cache=True, logits_last_only=True)
    if before != capacity - 1 or past_length(cache) != capacity or not bool(logits.isfinite().all()):
        raise ValueError("Actual long-context cache proof failed")
    return dict(forced_prefix_positions=before, final_cached_positions=past_length(cache),
                prefix_is_technical_control=True, argmax=int(logits[0,-1].argmax()))


def read_part(path, cases, tokenizer, profile_sha):
    d = load(path)
    if d["profile_sha256"] != profile_sha or [r["key"] for r in d["rows"]] != [r["key"] for r in cases]:
        raise ValueError(f"Wrong profile or row ordering in {path.name}")
    for row, case in zip(d["rows"], cases, strict=True):
        ids = row["output_ids"]
        if (not 0 < len(ids) <= OUTPUT_CAP or EOS in ids[:-1]
                or any(type(token) is not int or not 0 <= token < 32768 for token in ids)
                or row["finish"] != ("EOS" if ids[-1] == EOS else "MAX_NEW")
                or (row["finish"] == "MAX_NEW" and len(ids) != OUTPUT_CAP)
                or row["prompt_tokens"] != len(case["ids"])
                or row["answer"] != tokenizer.decode(ids, skip_special_tokens=True)):
            raise ValueError(f"Corrupt generation evidence in {path.name}")
    return d


def execute(profile, window):
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    model, cfg, dev = load_model(ckpt_path=PARENT, device="cuda", mtp_heads="off")
    if (cfg.max_seq_len, cfg.vocab_size, cfg.mlp_group, cfg.cla_group, len(model.visit_schedule())) != (1024, 32768, 4, 2, 28):
        raise ValueError("Exact native1024 32K G4 R2 parent required")
    check_cases = max(profile["groups"], key=len)[:4]
    check_item = check_cases[0]
    original_rows = {row["key"]: row for row in
                     (json.loads(line) for line in (ASSETS / "ifeval_input_data.jsonl").read_bytes().splitlines())}
    original_text, original_meta = sample(model, cfg, tokenizer, original_rows[check_item["key"]]["prompt"],
                                          max_new=12, temperature=0., top_k=0, device=dev,
                                          logits_last_only=True, return_metadata=True)
    baseline, _ = replies(model,tokenizer,[check_item],12,window)
    baseline_ids = baseline[0]["output_ids"]
    if (original_text != tokenizer.decode(check_item["ids"] + baseline_ids)
            or original_meta["generated_tokens"] != len(baseline_ids) or original_meta["finish_reason"] != baseline[0]["finish"]):
        raise ValueError("Batch implementation differs from the native generation entry point")
    signature = state_fingerprint(model)
    emitted, reused, stop = 0, 0, None
    profile_sha = digest(PROFILE)
    with execution_context(model, profile["capacity"]):
        for_batch, _ = replies(model,tokenizer,check_cases,12,window)
        alone = [replies(model,tokenizer,[case],12,window)[0][0] for case in check_cases]
        if baseline[0] != alone[0] or for_batch != alone:
            raise ValueError("Existing-position, native or same-length batch parity differs")
        proof = boundary_proof(model, profile["groups"][0][0], profile["capacity"])
        print("IFEVAL_CONTEXT_PROOF", proof["final_cached_positions"], "short native/extended/batch parity", flush=True)
        for i, cases in enumerate(profile["groups"]):
            path = PARTS / f"part_{i:03d}.json"
            if path.exists() or path.is_symlink():
                read_part(path, cases, tokenizer, profile_sha)
                reused += len(cases)
                continue
            try:
                window.check()
                started = monotonic()
                answers, actual_context = replies(model, tokenizer, cases, OUTPUT_CAP, window)
            except WindowEnded as exc:
                stop = str(exc)
                break
            publish(path, dict(index=i, profile_sha256=profile_sha, rows=answers,
                               last_context=actual_context, seconds=monotonic()-started))
            emitted += len(cases)
            print("IFEVAL_GROUP", i, len(cases), emitted + reused, actual_context,
                  round(monotonic()-started,3), flush=True)
    if cfg.max_seq_len != 1024 or state_fingerprint(model) != signature:
        raise ValueError("Inference changed the original checkpoint state")
    parts = [p for p in sorted(PARTS.glob("part_*.json"))]
    joined = []
    model_max_context = 0
    for path in parts:
        index = int(path.stem.split("_")[-1])
        part = read_part(path, profile["groups"][index], tokenizer, profile_sha)
        joined.extend(part["rows"])
        model_max_context = max(model_max_context, part["last_context"])
    if len({r["key"] for r in joined}) != len(joined) or len(joined) != emitted + reused:
        raise ValueError("Duplicate or inconsistent published row count")
    return dict(profile_sha256=profile_sha, model_state_sha256=signature, state_restored=True,
                short_native_matches_extended_and_batch=True, generated_new=emitted, reused=reused,
                verified_rows=len(joined), published_parts=len(parts), stop_reason=stop,
                full_response_count=len(joined) == profile["rows"], forced_position_proof=proof,
                actual_max_cached_positions=model_max_context, scorer_metrics=None,
                n_eos=sum(r["finish"]=="EOS" for r in joined),
                n_max_new=sum(r["finish"]=="MAX_NEW" for r in joined), checkpoint_writes=0)


def run():
    if (DEADLINE - datetime.now(DEADLINE.tzinfo)).total_seconds() < 100:
        raise WindowEnded("Insufficient time to start the approved GPU window")
    profile = load(PROFILE)
    if pins() != profile["pins"] or digest(OUT / "plan_at_execution.md") != profile["plan_sha256"]:
        raise ValueError("Sealed model, data, sources or plan differ")
    entry = require_idle_gpu()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    stamp = datetime.now(DEADLINE.tzinfo).strftime("%H%M%S_%f")
    trace = OUT / f"device_{stamp}.csv"
    with trace.open("xb") as stream:
        watcher = subprocess.Popen((*DEVICE,"--loop-ms=250"),stdout=stream)
        try:
            result = execute(profile, Window())
        finally:
            if watcher.poll() is None:
                watcher.terminate()
            watcher.wait(timeout=8)
    gc.collect()
    close_owned_cuda(torch, result)
    samples = read_samples(trace)
    if not samples or pins() != profile["pins"]:
        raise ValueError("Missing resource observations or changed sealed inputs")
    result.update(tag=TAG, entry=entry, sample_file=trace.name, gpu_samples=len(samples),
                  gpu_peak_mib=max(s["occupied_mib"] for s in samples))
    publish(OUT / f"window_{stamp}.json", result)
    print("IFEVAL_RESULT",result["verified_rows"],result["full_response_count"],
          result["actual_max_cached_positions"],result["gpu_peak_mib"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    mode = parser.parse_args().phase
    if os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if mode == "run" else ""):
        parser.error("Select the authorized GPU or intentionally isolated CPU mode")
    if mode == "run" and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Select the pinned deterministic CUDA workspace")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (run if mode == "run" else prepare)()
