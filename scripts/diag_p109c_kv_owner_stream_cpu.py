"""Compare deferred KV conversion with per-owner FP32 work and persistent BF16."""

from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from time import monotonic

import torch
from torch.nn import functional as F

from scripts import diag_p109c_kv_length_cpu as previous
from tinylm.model.modules import build_rope


TAG = "p109c_kv_owner_stream_cpu_20261125"
RECORD = previous.reference.EVIDENCE / TAG
PROFILE = previous.reference.EVIDENCE / f"{TAG}_profile.json"
ARMS = ("short_fp32", "long_bf16", "long_bf16_owner_stream")


class OwnerStream:
    """Restricted CPU inference path for the frozen G4 R2 owner schedule."""

    def __init__(self, model):
        cfg = model.cfg
        ordering = model.visit_schedule()
        if (model.training or not model._quant_frozen or cfg.n_modes != 1
                or len(ordering) != 28 or cfg.max_seq_len != 2048 or cfg.kv_dtype != "bf16"
                or cfg.repeat_kv_reuse or getattr(cfg, "reuse_attn_on_dup", False)
                or getattr(cfg, "repeat_embed_reinject", False) or getattr(model, "_unpack_cache", False)
                or cfg.attn_kind != "softmax_cla" or getattr(model, "_emb_fmt", None) is not None):
            raise ValueError("the isolated path requires the frozen G4 R2 CPU model")
        self.model = model
        self.visits = []
        seen = Counter()
        for index in ordering:
            owner = model.owner[index]
            creates = index == owner
            if creates:
                seen[owner] += 1
            if not seen[owner]:
                raise ValueError("the owner must precede every one of its consumers")
            self.visits.append((index, (owner, seen[owner] - 1), creates))
        self.last_visit = {key: step for step, (_, key, _) in enumerate(self.visits)}
        self.store = {}
        self.past = None
        self.length = 0

    def __call__(self, tokens, *, past_kv, use_cache, logits_last_only):
        if (not torch.is_inference_mode_enabled() or not use_cache or not logits_last_only
                or tokens.device.type != "cpu" or tokens.shape[0] != 1):
            raise ValueError("the isolated experiment requires single-request CPU greedy inference")
        if past_kv is None:
            self.length, self.past = 0, None
        elif past_kv is not self.past:
            raise ValueError("the caller supplied a different request state")
        start = self.length
        end = start + tokens.shape[1]
        model = self.model
        if end > model.cfg.max_seq_len:
            raise ValueError("the request would exceed the fixed buffer")
        cos, sin = model.rope_cos[start:end], model.rope_sin[start:end]
        hidden = F.embedding(tokens, model._emb_w())
        if model.emb_up is not None:
            hidden = F.linear(hidden, model._emb_up_w())
        working = {}
        for step, (index, key, creates) in enumerate(self.visits):
            layer = model.layers[index]
            if creates:
                fresh = layer.attn_mod.compute_kv(hidden, cos, sin)
                if key not in self.store:
                    self.store[key] = tuple(value.new_empty((*value.shape[:2], model.cfg.max_seq_len, value.shape[-1]),
                                                            dtype=torch.bfloat16) for value in fresh)
                # copy_ casts directly into the attention workspace and the persistent
                # owner cache. This avoids retaining a FP32 bank across all owners.
                segments = []
                for stored, new in zip(self.store[key], fresh, strict=True):
                    full = new.new_empty((*new.shape[:2], end, new.shape[-1]))
                    if start:
                        full[:, :, :start].copy_(stored[:, :, :start])
                    full[:, :, start:end].copy_(new)
                    stored[:, :, start:end].copy_(new)
                    segments.append(full)
                working[key] = tuple(segments)
                del fresh, full, new, stored, segments
            hidden = layer(hidden, working[key], cos, sin, None)
            if self.last_visit[key] == step:
                del working[key]
        normalized = model.norm_f(hidden[:, -1:, :]) * model.norm_f_scale
        logits = model._head_logits(normalized)
        self.length = end
        self.past = {key: tuple(value[:, :, :end] for value in pair) for key, pair in self.store.items()}
        return logits, self.past

    def allocated_bytes(self):
        return previous.cache_size(self.store)


def profile():
    old = previous.completed.read_json(previous.PROFILE)
    if old["source_sha256"] != previous.source_pins():
        raise ValueError("the original model or document paths differ")
    return dict(tag=TAG, old_profile_sha256=previous.reference.file_sha(previous.PROFILE),
                source_sha256=previous.reference.file_sha(Path(__file__).resolve()),
                checkpoint_sha256=previous.reference.CHECKPOINT_SHA256,
                arms=list(ARMS), cases=len(old["cases"]), cpu_affinity=[14],
                cutoff_policy="CPU only within authorized window",
                canary_max_logit_error=0.00005), old["cases"]


def model_for(arm):
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1337)
    model = previous.completed.load_model(previous.reference.checkpoint(), 2942, "cpu")
    if arm != "short_fp32":
        cfg = model.cfg
        cos, sin = build_rope(cfg.head_dim, 2048, cfg.rope_theta)
        if not (torch.equal(cos[:1024], model.rope_cos) and torch.equal(sin[:1024], model.rope_sin)):
            raise ValueError("the common RoPE frequencies differ")
        model.rope_cos, model.rope_sin = cos, sin
        model.cfg.max_seq_len, model.cfg.kv_dtype = 2048, "bf16"
    return model


def read_seal(stamp, cutoff):
    previous.deadline_check(cutoff)
    live, cases = profile()
    if stamp != previous.reference.file_sha(PROFILE) or previous.completed.read_json(PROFILE) != live:
        raise ValueError("the owner-stream profile and live inputs differ")
    return live, cases


@torch.inference_mode()
def canary(cases, tolerance, cutoff):
    model = model_for("long_bf16")
    stream = OwnerStream(model)
    largest = 0.
    count = 0
    for case in cases[:2]:
        a = b = None
        ids = case["inputs"]["long"]
        blocks = [ids[i:i + 128] for i in range(0, len(ids), 128)] + [[7], [5], [11], [13]]
        for block in blocks:
            previous.deadline_check(cutoff)
            tokens = torch.tensor([block])
            x, a = model(tokens, past_kv=a, use_cache=True, logits_last_only=True)
            y, b = stream(tokens, past_kv=b, use_cache=True, logits_last_only=True)
            largest = max(largest, float((x-y).abs().max()))
            if (largest > tolerance or x.argmax().item() != y.argmax().item() or a.keys() != b.keys()
                    or not all(torch.equal(i, j) for key in a for i, j in zip(a[key], b[key], strict=True))):
                raise ValueError("isolated streamed KV, logits or choice differs from the reference")
            count += 1
    previous.native.publish(RECORD / "canary.json", dict(calls=count, max_logit_error=largest,
                            exact_cache=True, matching_argmax=True))


@torch.inference_mode()
def worker(arm, cases, cutoff):
    import statistics

    before_load = previous.memory()
    model = model_for(arm)
    tokenizer = previous.completed.load_tokenizer()
    wrapped = OwnerStream(model) if arm == "long_bf16_owner_stream" else model
    after_load = previous.memory()
    peak = 0

    def sample_rss(*_):
        nonlocal peak
        peak = max(peak, previous.memory()["VmRSS"])

    handles = [layer.register_forward_hook(sample_rss) for layer in model.layers]
    rows = []
    source = "short" if arm == "short_fp32" else "long"
    try:
        for case in cases:
            peak = 0
            row = previous.generate(wrapped, torch, tokenizer, case["inputs"][source], cutoff)
            row.update(id=case["id"], in_request_rss_sample_peak=max(peak, row["process"]["VmRSS"]),
                       reference_match=previous.final.reference_match(row["answer"], case))
            rows.append(row)
            print(f"{arm} {case['id']} {row['elapsed_seconds']:.2f}s "
                  f"rss_sample={row['in_request_rss_sample_peak']}", flush=True)
    finally:
        for handle in handles:
            handle.remove()
    previous.native.publish(RECORD / f"{arm}.json", dict(arm=arm, rows=rows,
                            before_load=before_load, after_load=after_load,
                            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                            actual_sample_peak=max(row["in_request_rss_sample_peak"] for row in rows),
                            allocated_static_cache=wrapped.allocated_bytes() if isinstance(wrapped, OwnerStream) else None,
                            median_seconds=statistics.median(row["elapsed_seconds"] for row in rows)))


def run(stamp, cases, cutoff):
    RECORD.mkdir(exist_ok=False)
    started = monotonic()
    for arm in ("canary", *ARMS):
        previous.deadline_check(cutoff)
        subprocess.run([sys.executable, "-B", "-m", "scripts.diag_p109c_kv_owner_stream_cpu",
                        "worker", "--arm", arm, "--profile-sha256", stamp, "--stop-by", cutoff.isoformat()],
                       check=True, timeout=(cutoff - datetime.now().astimezone()).total_seconds())
    arms = {arm: previous.completed.read_json(RECORD / f"{arm}.json") for arm in ARMS}
    reference, candidate = arms["long_bf16"], arms["long_bf16_owner_stream"]
    matched = sum(a["metadata"]["generated_ids"] == b["metadata"]["generated_ids"]
                  for a, b in zip(reference["rows"], candidate["rows"], strict=True))
    reduced = reference["actual_sample_peak"] - candidate["actual_sample_peak"]
    within_short = candidate["actual_sample_peak"] <= arms["short_fp32"]["actual_sample_peak"]
    previous.native.publish(RECORD / "report.json", dict(profile_sha256=stamp, matched_ids=matched,
                            requests=len(cases), reduced_long_in_request_sample_bytes=reduced,
                            short_memory_sample_gate=within_short, elapsed=monotonic()-started,
                            arms={arm: {key: value for key, value in stats.items() if key != "rows"}
                                  for arm, stats in arms.items()}))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", "run", "worker"))
    parser.add_argument("--arm", choices=("canary", *ARMS))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    previous.deadline_check(args.stop_by)
    if args.mode == "seal":
        if PROFILE.exists():
            parser.error("the fixed profile already exists")
        previous.native.publish(PROFILE, profile()[0])
        print(previous.reference.file_sha(PROFILE), flush=True)
        return
    live, cases = read_seal(args.profile_sha256, args.stop_by)
    if args.mode == "run":
        run(args.profile_sha256, cases, args.stop_by)
    elif args.arm == "canary":
        canary(cases, live["canary_max_logit_error"], args.stop_by)
    elif args.arm in ARMS:
        worker(args.arm, cases, args.stop_by)
    else:
        parser.error("a worker requires one fixed arm")


if __name__ == "__main__":
    main()
