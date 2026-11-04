#!/usr/bin/env python3
"""Opt-in frozen TinyLM inference resources, never training or quality selection.

Reuse the product sampler and existing strict Q/F weight-route loader. Each
model/device runs in a fresh process. Forced-length timing is NOT a dialogue
quality score; natural EOS/EOT answers are retained separately.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import statistics
import sys
import time
import weakref
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "P106B_FROZEN_RESOURCE_MATRIX_V2"
PROFILE = "P106B_FROZEN_RESOURCE_PROFILE_V1"
TAG = "p106b_resource_matrix_v1_20261027"
RECOVERY_TAG = "p106b_resource_matrix_v2_20261027"
DEADLINE = datetime(2026, 10, 27, 8, tzinfo=timezone.utc)
OWN = ("scripts/diag_p106b_resource_matrix.py", "scripts/test_p106b_resource_matrix.py")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def safe(name):
    p = Path(name)
    need(not p.is_absolute() and ".." not in p.parts, "relative path required")
    need(not str(p).startswith(("datasets/TinyDataset", ".codex", ".agents", ".aws")), "protected path")
    value = ROOT / p
    need(not any(q.is_symlink() for q in (value, *value.parents)), "symlink path refused")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def identity():
    from scripts.interactive_research_infer import REQUIRED_SOURCES
    names = tuple(sorted(set((*OWN, *REQUIRED_SOURCES, "scripts/bench_infer.py",
        "scripts/diag_p102a_logit_margin.py", "tinylm/infer/dialogue.py"))))
    files = {name: digest(safe(name)) for name in names}
    return dict(files=files, sha256=sha(files))


def write_new(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + bytes([10])
    need(len(raw) < 20_000_000 and not path.exists(), "new evidence below20MB required")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def read_ref(ref):
    p = safe(ref["path"])
    need(p.is_file() and p.stat().st_size < 20_000_000, "small explicit JSON required")
    need(digest(p) == ref["sha256"], "reference changed: " + ref["path"])
    result = json.loads(p.read_bytes())
    need(digest(p) == ref["sha256"], "reference changed while reading")
    return result


class Budget:
    def __init__(self, seconds, deadline=DEADLINE):
        self.started = time.monotonic()
        self.seconds = seconds
        self.deadline = deadline

    def check(self):
        if time.monotonic() - self.started > self.seconds or datetime.now(timezone.utc) >= self.deadline:
            raise TimeoutError("owned resource window expired")


@contextmanager
def wall(seconds):
    previous = signal.getsignal(signal.SIGALRM)
    need(signal.getitimer(signal.ITIMER_REAL) == (0., 0.), "another timer is active")
    def expired(*_):
        raise TimeoutError("resource hard wall timer expired")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def summarize_times(times, started, ended, tokens):
    need(type(tokens) is int and tokens > 0 and len(times) == tokens, "every generated token needs one timestamp")
    need(all(math.isfinite(x) for x in [started, ended, *times]) and started < times[0] <= times[-1] <= ended,
         "finite monotonic token times required")
    need(all(a <= b for a, b in zip(times, times[1:])), "token timestamps moved backwards")
    tail = times[-1] - times[0]
    return dict(first_token_ms=1000 * (times[0] - started), total_seconds=ended - started,
        generated_tokens=tokens, end_to_end_tokens_per_second=tokens / (ended - started),
        decode_tokens_per_second=(tokens - 1) / tail if tokens > 1 and tail > 0 else None,
        token_timestamps_relative_seconds=[x - started for x in times])


def storage_audit(values):
    """Physical storage bytes, not numel; shared tensors/views count once."""
    import torch
    seen, totals, tensors = set(), {}, 0
    for category, value in values:
        if not isinstance(value, torch.Tensor):
            continue
        storage = value.untyped_storage()
        if storage.nbytes() == 0:
            continue
        key = (str(value.device), storage.data_ptr(), storage.nbytes())
        tensors += 1
        if key in seen:
            continue
        seen.add(key)
        name = category + ":" + str(value.device)
        totals[name] = totals.get(name, 0) + storage.nbytes()
    return dict(unique_storage_bytes=sum(totals.values()), by_kind_device=totals,
        tensor_references=tensors, unique_storages=len(seen))


def nested_tensors(value, seen=None):
    import torch
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, torch.Tensor):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from nested_tensors(item, seen)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from nested_tensors(item, seen)


def model_storage(model):
    values = [("parameter", p) for p in model.parameters()]
    values += [("buffer", p) for p in model.buffers()]
    for module in model.modules():
        for name, value in vars(module).items():
            if name not in ("_parameters", "_buffers", "_modules"):
                values += [("unregistered", t) for t in nested_tensors(value)]
    return storage_audit(values)


def rss():
    import psutil
    return dict(current_bytes=psutil.Process().memory_info().rss,
        process_lifetime_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)


def metadata(args):
    profile = read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    own = identity()
    need(profile.get("schema") == PROFILE and profile.get("tag") == RECOVERY_TAG
        and profile.get("source_sha256") == own["sha256"] == args.source_sha256
        and profile.get("deadline") == DEADLINE.isoformat()
        and profile.get("root_approved") is True and profile.get("training_updates") == 0,
        "exact current root profile/source/authority required")
    need(60 <= args.max_wall_sec <= profile["max_worker_seconds"] <= 3600, "bounded worker required")
    need(profile.get("timing_repetitions") == 3 and profile.get("forced_new_tokens") == 32
        and profile.get("natural_max_new") == 64 and len(profile.get("workloads", [])) == 4
        and len(profile.get("answer_cases", [])) == 4, "sealed full resource workload required")
    need({(w["language"], w["prompt_tokens"]) for w in profile["workloads"]}
        == {("ko", 128), ("en", 128), ("ko", 512), ("en", 512)}, "declared bilingual128/512 matrix differs")
    models = [m for m in profile["models"] if m["id"] == args.model]
    need(len(models) == 1 and args.device in ("cpu", "cuda"), "one declared model/device required")
    model = models[0]
    need(model["route"] in ("ternary", "float") and model["cfg"]["mtp_aux"] is False, "explicit Q/F model required")
    output = safe(profile["output"]) / (args.model + "_" + args.device)
    need(str(output.relative_to(ROOT)).startswith("test_result/evidence/" + RECOVERY_TAG + "/") and not output.exists(), "fresh exact output required")
    refs = profile["references"] + [profile["tokenizer"]]
    for ref in refs:
        need(digest(safe(ref["path"])) == ref["sha256"], "frozen metadata/tokenizer changed")
    return profile, model, output, own


@contextmanager
def frozen_model(spec, tokenizer, device, budget, proof=None):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts import p106b_weight_route as route_module
    from scripts.interactive_research_infer import state_fingerprint
    checkpoint = safe(spec["checkpoint"]["path"])
    model = payload = None
    proof = {} if proof is None else proof
    failed = False
    with checkpoint.open("rb") as stream:
        before = os.fstat(stream.fileno())
        h = hashlib.sha256()
        for part in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(part)
            budget.check()
        need(h.hexdigest().upper() == spec["checkpoint"]["sha256"], "checkpoint byte identity differs")
        stream.seek(0)
        payload = torch.load(stream, map_location="cpu", weights_only=True)
        after = os.fstat(stream.fileno())
        need((before.st_size, before.st_ino, before.st_mtime_ns) == (after.st_size, after.st_ino, after.st_mtime_ns), "checkpoint changed during read")
    need(sha(payload["cfg"]) == sha(spec["cfg"]) and payload["step"] == spec["updates"]
        and payload["tokenizer_sha256"] == tokenizer["sha256"], "checkpoint cfg/step/tokenizer differs")
    if "header_sha256" in spec:
        need(sha({k: v for k, v in payload.items() if k != "model"}) == spec["header_sha256"], "full checkpoint header differs")
    tok = Tokenizer.from_file(str(safe(tokenizer["path"])))
    cfg = TMTConfig(**payload["cfg"])
    need(cfg.vocab_size == tok.get_vocab_size() == 32768 and cfg.max_seq_len == 1024
        and cfg.train_repeat == cfg.infer_repeat == 1 and not cfg.tie_mlp
        and (tok.token_to_id("<eos>"), tok.token_to_id("<|im_end|>")) == (2, 4), "native dense14 chat32 contract differs")
    model = TiedMLPTransformer(cfg)
    try:
        with route_module.weight_route(model, spec["route"]) as route:
            route_module.load_routed_state(model, payload, spec["route"])
            payload = None
            need(state_fingerprint(model) == spec["core_sha256"], "full CPU model core differs")
            proof["initial_core_verified"] = True
            model.eval().to(device)
            model.set_anneal(1.)
            with torch.no_grad():
                model.freeze_quant()
            route.assert_active()
            need(all(p.dtype == torch.float32 for p in model.parameters()), "FP32 master required")
            try:
                yield model, cfg, tok, route
            except BaseException:
                failed = True
                raise
            finally:
                try:
                    route.assert_active()
                    proof["final_core_sha256"] = state_fingerprint(model)
                    proof["gradients_absent"] = all(p.grad is None for p in model.parameters())
                    proof["final_core_verified"] = proof["final_core_sha256"] == spec["core_sha256"]
                    need(proof["final_core_verified"] and proof["gradients_absent"], "frozen core/gradient changed")
                except Exception as exc:
                    proof["final_core_verification_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                    if not failed:
                        raise
    except BaseException:
        failed = True
        raise
    finally:
        try:
            if model is not None:
                model.clear_quant()
                model.to("cpu")
        except Exception as exc:
            proof["model_release_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
            if not failed:
                raise
        model = payload = None
        gc.collect()
        try:
            proof["checkpoint_bytes_unchanged"] = digest(checkpoint) == spec["checkpoint"]["sha256"]
            need(proof["checkpoint_bytes_unchanged"], "original checkpoint changed")
        except Exception as exc:
            proof["checkpoint_verification_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
            if not failed:
                raise


class FixedCapture:
    def __init__(self, tokenizer, ids):
        self.tokenizer, self.ids, self.decoded_ids = tokenizer, list(ids), None

    def token_to_id(self, text):
        return self.tokenizer.token_to_id(text)

    def encode(self, _):
        return SimpleNamespace(ids=list(self.ids))

    def decode(self, ids):
        self.decoded_ids = list(ids)
        return self.tokenizer.decode(ids, skip_special_tokens=False)


class FP32Forward:
    def __init__(self, model, device):
        self.model, self.device = model, device

    def __getattr__(self, name):
        return getattr(self.model, name)

    def __call__(self, *args, **kwargs):
        import torch
        from torch.nn.attention import sdpa_kernel, SDPBackend
        with torch.autocast(self.device, enabled=False), sdpa_kernel(SDPBackend.MATH):
            return self.model(*args, **kwargs)


class ObservedForward(FP32Forward):
    def __init__(self, model, device):
        super().__init__(model, device)
        self.kv_peak_bytes, self.kv_last_bytes, self.kv_prior_and_returned_peak_bytes = 0, 0, 0
        self.forward_calls = 0

    def __call__(self, *args, **kwargs):
        prior = list(nested_tensors(kwargs.get("past_kv")))
        result = super().__call__(*args, **kwargs)
        self.forward_calls += 1
        if isinstance(result, tuple):
            returned = list(nested_tensors(result[1]))
            value = storage_audit(("kv", t) for t in returned)["unique_storage_bytes"]
            both = storage_audit(("kv", t) for t in prior + returned)["unique_storage_bytes"]
            self.kv_last_bytes = value
            self.kv_peak_bytes = max(self.kv_peak_bytes, value)
            self.kv_prior_and_returned_peak_bytes = max(self.kv_prior_and_returned_peak_bytes, both)
        return result


def one_generation(model, cfg, tok, ids, device, count, *, natural, chatml, budget):
    import torch
    module = importlib.import_module("tinylm.infer.generate")
    original_pick = module._pick
    timed = ObservedForward(model, device)
    capture = FixedCapture(tok, ids)
    timestamps = []
    def synchronize():
        if device == "cuda":
            torch.cuda.synchronize()
    def pick(*args, **kwargs):
        result = original_pick(*args, **kwargs)
        synchronize()
        timestamps.append(time.perf_counter())
        budget.check()
        return result
    synchronize()
    started = time.perf_counter()
    with torch.no_grad(), patch.object(module, "_pick", pick):
        text, meta = module.sample(timed, cfg, capture, "FROZEN_TOKEN_IDS", max_new=count,
            temperature=0., top_k=1, device=device, use_cache=True, stop_at_eos=natural,
            eos_id=2, logits_last_only=True, return_metadata=True, mtp_tokens=1,
            stop_token_sequences=[[4]] if natural and chatml else None)
    synchronize()
    ended = time.perf_counter()
    need(module._pick is original_pick, "sampler observer was not restored")
    generated = capture.decoded_ids[len(ids):]
    need(len(generated) == meta["generated_tokens"] == timed.forward_calls
        and (natural or len(generated) == count), "generation/forward/token count mismatch")
    return dict(timing=summarize_times(timestamps, started, ended, len(generated)),
        prompt_ids=list(ids), generated_ids=generated, answer=tok.decode(generated, skip_special_tokens=False),
        full_text=text, metadata=meta, max_returned_kv_storage_bytes=timed.kv_peak_bytes,
        last_returned_kv_storage_bytes=timed.kv_last_bytes,
        max_prior_plus_returned_kv_storage_bytes=timed.kv_prior_and_returned_peak_bytes,
        cache_measurement="AT_FORWARD_RETURN_NOT_INTERNAL_PEAK; final length prompt+generated-1",
        forward_calls=timed.forward_calls,
        measurement="TTFT_AFTER_ACTUAL_PICK; SYNCHRONIZED_OBSERVER_OVERHEAD_INCLUDED; TOKENIZATION_EXCLUDED")


def unobserved_generation(model, cfg, tok, ids, device, count, *, natural=False, chatml=False):
    """Same product sampler/FP32 contract, no pick hook or KV traversal."""
    import torch
    from scripts.bench_infer import _CpuWatch
    module = importlib.import_module("tinylm.infer.generate")
    capture = FixedCapture(tok, ids)
    forward = FP32Forward(model, device)
    if device == "cuda":
        torch.cuda.synchronize()
    watch = _CpuWatch()
    need(watch.ps is not None, "CPU load watcher missing")
    watch.start()
    started = time.perf_counter()
    try:
        with torch.no_grad():
            _, meta = module.sample(forward, cfg, capture, "FROZEN_TOKEN_IDS", max_new=count,
                temperature=0., top_k=1, device=device, use_cache=True, stop_at_eos=natural,
                eos_id=2, logits_last_only=True, return_metadata=True, mtp_tokens=1,
                stop_token_sequences=[[4]] if natural and chatml else None)
        if device == "cuda":
            torch.cuda.synchronize()
        ended = time.perf_counter()
    finally:
        system, own, external = watch.stop()
    seconds = ended - started
    ids = capture.decoded_ids[len(ids):]
    need(len(ids) == meta["generated_tokens"] and len(ids) > 0 and (natural or len(ids) == count)
        and seconds > 0, "full unobserved generation required")
    return dict(seconds=seconds, generated_ids=ids, generated_tokens=len(ids),
        end_to_end_tokens_per_second=len(ids) / seconds, metadata=meta,
        cpu_load=dict(system_percent=system, process_machine_percent=own, external_percent=external),
        measurement="UNOBSERVED_PRODUCT_SAMPLER_FP32_MATH; TOKENIZATION_EXCLUDED; FIXED_LENGTH")


def close_cuda(torch_module, proof=None):
    """Clear only this fresh process's allocator and cuBLAS workspaces."""
    cuda = torch_module.cuda
    proof = {} if proof is None else proof
    try:
        proof["entry"] = dict(allocated_bytes=cuda.memory_allocated(), reserved_bytes=cuda.memory_reserved())
        gc.collect()
        cuda.synchronize()
        cuda.empty_cache()
        ordinary = dict(allocated_bytes=cuda.memory_allocated(), reserved_bytes=cuda.memory_reserved())
        proof["before_workspace_clear"] = ordinary
        clear = getattr(torch_module._C, "_cuda_clearCublasWorkspaces", None)
        proof.update(workspace_clear_available=callable(clear), workspace_clear_called=False)
        if ordinary["allocated_bytes"] and callable(clear):
            proof["workspace_clear_called"] = True
            clear()
            gc.collect()
            cuda.empty_cache()
            cuda.synchronize()
    except Exception as exc:
        proof["error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
        raise
    finally:
        try:
            proof.update(allocated_bytes=cuda.memory_allocated(), reserved_bytes=cuda.memory_reserved())
        except Exception as exc:
            proof["final_query_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
    return proof


def execute(args, profile, spec, output, source):
    import torch
    import psutil
    from scripts.bench_infer import _CpuWatch
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p102a_logit_margin import memory_point
    torch.set_num_threads(1 if args.device == "cpu" else 2)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    output.mkdir(parents=True, exist_ok=False)
    budget = Budget(args.max_wall_sec)
    report = dict(schema=SCHEMA, tag=profile["tag"], model=args.model, device=args.device, status="STARTED",
        input_profile_sha256=args.profile_sha256, source=source, checkpoint=spec["checkpoint"],
        training_updates=0, checkpoint_writes=0, quality_claim=False, records=[], natural_answers=[],
        torch_version=torch.__version__, psutil_version=psutil.__version__, cuda_build=torch.version.cuda,
        cpu_threads=torch.get_num_threads(), cpu_interop_threads=torch.get_num_interop_threads(),
        cpu_affinity="OS_SCHEDULED_UNPINNED", master_compute="FP32", attention="SDPA_MATH",
        use_cache=True, mtp=False, logits_last_only=True, sampling="GREEDY",
        rss_before=rss(), gpu_points=[], pid=os.getpid(), started_at=datetime.now(timezone.utc).isoformat())
    rc = 9
    model_ref = None
    model = cfg = tok = route = None
    try:
        with wall(args.max_wall_sec):
            if args.device == "cuda":
                report["idle_proof"] = require_idle_gpu()
                point = memory_point()
                need(point["free_mib"] >= 2048, "less than2GiB free; do not start model")
                report["gpu_points"].append(point)
                torch.cuda.init()
                total = torch.cuda.get_device_properties(0).total_memory
                cap = min(int(total * .8), (point["free_mib"] - 1024) * 2**20)
                torch.cuda.set_per_process_memory_fraction(cap / total, 0)
                report["allocator_cap_bytes"] = cap
                torch.cuda.reset_peak_memory_stats()
            started_load = time.perf_counter()
            proof = report["model_proof"] = {}
            with frozen_model(spec, profile["tokenizer"], args.device, budget, proof) as (model, cfg, tok, route):
                model_ref = weakref.ref(model)
                report["validation_load_seconds"] = time.perf_counter() - started_load
                report["rss_loaded"] = rss()
                report["held_after_load"] = model_storage(model)
                report["parameters"] = sum(p.numel() for p in model.parameters())
                report["route"] = route.metadata
                for workload in profile["workloads"]:
                    raw = tok.encode(workload["text"] * 40).ids
                    need(len(raw) >= workload["prompt_tokens"], "declared fixed prompt too short")
                    ids = raw[:workload["prompt_tokens"]]
                    for repeat in range(profile["timing_repetitions"] + 1):
                        budget.check()
                        plain = None
                        if repeat % 2 == 0:
                            plain = unobserved_generation(model, cfg, tok, ids, args.device, profile["forced_new_tokens"])
                        watch = _CpuWatch()
                        need(watch.ps is not None, "CPU load watcher missing")
                        watch.start()
                        try:
                            record = one_generation(model, cfg, tok, ids, args.device, profile["forced_new_tokens"],
                                natural=False, chatml=False, budget=budget)
                        finally:
                            system, own, external = watch.stop()
                        if plain is None:
                            plain = unobserved_generation(model, cfg, tok, ids, args.device, profile["forced_new_tokens"])
                        need(plain["generated_ids"] == record["generated_ids"], "observation changed actual selected tokens")
                        record.update(workload=workload["id"], language=workload["language"],
                            repeat=repeat, warmup=repeat == 0,
                            unobserved=plain, pair_order="PLAIN_THEN_OBSERVED" if repeat % 2 == 0 else "OBSERVED_THEN_PLAIN",
                            actual_token_ids_equal=True,
                            cpu_load=dict(system_percent=system, process_machine_percent=own, external_percent=external),
                            rss=rss())
                        report["records"].append(record)
                    route.assert_active()
                    if args.device == "cuda":
                        point = memory_point()
                        need(point["free_mib"] >= 512, "free VRAM dropped below512MiB")
                        report["gpu_points"].append(point)
                    print(json.dumps(dict(model=args.model, device=args.device, workload=workload["id"], done=True)), flush=True)
                for case in profile["answer_cases"]:
                    from tinylm.infer.dialogue import make_prompt
                    ids = tok.encode(make_prompt(case["question"], case["mode"])).ids
                    need(len(ids) + profile["natural_max_new"] <= cfg.max_seq_len, "natural question context overflow")
                    record = one_generation(model, cfg, tok, ids, args.device, profile["natural_max_new"],
                        natural=True, chatml=case["mode"] == "chatml", budget=budget)
                    plain = unobserved_generation(model, cfg, tok, ids, args.device, profile["natural_max_new"],
                        natural=True, chatml=case["mode"] == "chatml")
                    need(plain["generated_ids"] == record["generated_ids"]
                        and plain["metadata"] == record["metadata"], "natural observation changed output or termination")
                    record.update(unobserved=plain, actual_token_ids_and_stop_equal=True)
                    report["natural_answers"].append(dict(case=case, generation=record))
                report["held_after_generation"] = model_storage(model)
                report["rss_after_generation"] = rss()
                if args.device == "cuda":
                    report["cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
                    report["cuda_peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
                route.assert_active()
            need(identity() == source, "source changed during resource execution")
            for ref in profile["references"] + [profile["tokenizer"]]:
                need(digest(safe(ref["path"])) == ref["sha256"], "metadata/tokenizer changed during resource execution")
            expected = len(profile["workloads"]) * (1 + profile["timing_repetitions"])
            need(len(report["records"]) == expected and len(report["natural_answers"]) == len(profile["answer_cases"]), "incomplete matrix lane")
            report["status"] = "RESOURCE_LANE_COMPLETE_NOT_QUALITY"
            report["originals_unchanged"] = True
            rc = 0
    except BaseException as exc:
        report["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "RESOURCE_LANE_ERROR"
        report["error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
        print(json.dumps(dict(status=report["status"], original_error=report["error"])), flush=True)
        rc = 130 if isinstance(exc, KeyboardInterrupt) else 9
    finally:
        model = cfg = tok = route = None
        gc.collect()
        report["rss_closed"] = rss()
        report["model_object_released"] = model_ref is None or model_ref() is None
        if not report["model_object_released"]:
            report["model_cleanup_error"] = "model Python object remains alive after context release"
            if rc == 0:
                report["status"] = "RESOURCE_CLEANUP_ERROR"
            rc = 9
        if args.device == "cuda" and torch.cuda.is_initialized():
            try:
                report["cuda_owned_cleanup"] = {}
                close_cuda(torch, report["cuda_owned_cleanup"])
                if report["cuda_owned_cleanup"]["allocated_bytes"] or report["cuda_owned_cleanup"]["reserved_bytes"]:
                    raise RuntimeError("owned torch GPU allocations remain")
            except Exception as exc:
                report["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                if rc == 0:
                    report["status"] = "RESOURCE_CLEANUP_ERROR"
                rc = 9
        report.update(returncode=rc, ended_at=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic() - budget.started)
        write_new(output / "report.json", report)
        print(json.dumps(dict(status=report["status"], model=args.model, device=args.device, returncode=rc,
            seconds=report["seconds"], error=report.get("error"))), flush=True)
    return rc


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", required=True)
    p.add_argument("--profile-sha256", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--device", required=True, choices=("cpu", "cuda"))
    p.add_argument("--max-wall-sec", type=int, default=1800)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    try:
        profile, spec, output, own = metadata(args)
        if args.check_only:
            print(json.dumps(dict(status="STATIC_ONLY", model=args.model, device=args.device,
                output=str(output.relative_to(ROOT)), source_sha256=own["sha256"], model_loads=0, gpu_calls=0)))
            return 0
        need(datetime.now(timezone.utc).timestamp() + args.max_wall_sec + 120 < DEADLINE.timestamp(), "whole worker and cleanup must fit current authority")
        return execute(args, profile, spec, output, own)
    except Exception as exc:
        print(json.dumps(dict(status="ENTRY_OR_CLOSURE_ERROR", error=type(exc).__name__, message=str(exc))), file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
