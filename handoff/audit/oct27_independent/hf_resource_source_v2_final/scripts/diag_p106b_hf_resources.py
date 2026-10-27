#!/usr/bin/env python3
"""Closed external HF models: bounded inference resources, never training.

Reuse strict Core6 loaders and the installed Transformers generator. CPU lanes
have an initial strict CUDA load, so they are not CPU-only startup evidence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import gc
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import platform
import sys
import time
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tinylm  # noqa: F401 -- establish repository-local HF paths before HF imports.
from scripts import diag_p106b_resource_matrix as common
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p106b_official_core6 as official

SCHEMA = "P106B_HF_INFERENCE_RESOURCE_V1"
PROFILE = "P106B_HF_INFERENCE_RESOURCE_PROFILE_V1"
TAG = "p106b_hf_resources_v2_20261027"
MODELS = ("falcon90m", "gemma270", "qwen06", "gemma1b")
OWN = ("scripts/diag_p106b_hf_resources.py", "scripts/test_p106b_hf_resources.py")
need = common.need


def identity():
    files = dict(common.identity()["files"])
    files.update(external.identity()["files"])
    files.update({name: common.digest(common.safe(name)) for name in OWN})
    libraries = {}
    distribution = importlib.metadata.distribution("transformers")
    modules = ("generation/utils.py", "generation/streamers.py", "generation/configuration_utils.py",
        "generation/logits_process.py", "generation/stopping_criteria.py", "cache_utils.py", "__init__.py")
    for relative in modules:
        path = Path(distribution.locate_file("transformers/" + relative)).resolve(strict=True)
        libraries[str(path)] = common.digest(path)
    return dict(files=files, libraries=libraries, transformers_distribution_version=distribution.version,
        sha256=common.sha(dict(files=files, libraries=libraries, version=distribution.version)))


def error_record(exc):
    return dict(type=type(exc).__name__, message=str(exc)[:2000])


def persist_report(path, report):
    try:
        common.write_new(path, report)
        return True
    except BaseException as exc:
        report.update(status_before_persist_error=report["status"], status="HF_RESOURCE_REPORT_PERSIST_ERROR",
            report_persist_error=error_record(exc), returncode=9)
        print(json.dumps(dict(report_not_persisted=True, original_error=report.get("error"),
            report_persist_error=report["report_persist_error"])), flush=True)
        return False


def cache_tensors(value, prefix="cache", seen=None, depth=0):
    """Inspect official cache containers, including attention and SSM states."""
    import torch
    if value is None or isinstance(value, (str, bytes, int, float, bool)) or callable(value):
        return
    need(depth < 16, "cache container nesting exceeds declared bound")
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, torch.Tensor):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from cache_tensors(child, prefix + "." + str(key), seen, depth + 1)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from cache_tensors(child, prefix + "." + str(index), seen, depth + 1)
    elif type(value).__module__ == "transformers.cache_utils":
        for key, child in vars(value).items():
            if key in ("layer_class_to_replicate", "layer_init_kwargs"):
                continue
            if isinstance(child, torch.device) or isinstance(child, torch.dtype):
                continue
            yield from cache_tensors(child, prefix + "." + key, seen, depth + 1)
    else:
        raise TypeError("unsupported real cache object: " + type(value).__module__ + "." + type(value).__name__)


def cache_audit(cache):
    need(cache is not None, "generation returned no requested cache")
    audit = common.storage_audit(cache_tensors(cache))
    need(audit["unique_storage_bytes"] > 0, "empty cache storage is not a measurement")
    return audit


class Observer:
    """HF streamer timestamps actual selected tokens; first put is the prompt."""
    def __init__(self, model, device, budget):
        self.model, self.device, self.budget = model, device, budget
        self.prompt_seen = False
        self.prompt_ids, self.ids, self.times = [], [], []
        self.cache_max_bytes = 0
        self.logit_dtypes, self.logit_shapes = set(), set()
        self.handle = None
        self.started = None

    def put(self, value):
        import torch
        self.budget.check()
        ids = value.detach().cpu().reshape(-1).tolist()
        if not self.prompt_seen:
            self.prompt_ids = ids
            self.prompt_seen = True
            return
        need(len(ids) == 1 and self.started is not None, "one actual greedy token per streamer put required")
        if self.device == "cuda":
            torch.cuda.synchronize()
        self.ids.extend(ids)
        self.times.append(time.perf_counter() - self.started)

    def end(self):
        need(self.prompt_seen, "streamer never received its prompt")

    def hook(self, module, args, kwargs, output):
        import torch
        self.budget.check()
        logits = output.logits
        need(logits.dtype == torch.float32 and logits.ndim == 3, "actual HF logits must be FP32 rank3")
        self.logit_dtypes.add(str(logits.dtype))
        self.logit_shapes.add(tuple(logits.shape))
        need(kwargs.get("use_cache") is True, "actual generation did not request cache")
        self.cache_max_bytes = max(self.cache_max_bytes,
            cache_audit(output.past_key_values)["unique_storage_bytes"])

    def __enter__(self):
        self.handle = self.model.register_forward_hook(self.hook, with_kwargs=True)
        return self

    def __exit__(self, *_):
        if self.handle is not None:
            self.handle.remove()
        self.handle = self.model = None


def config_for(model, tokenizer, max_new, natural):
    from transformers import GenerationConfig
    eos = model.generation_config.eos_token_id
    if eos is None:
        eos = tokenizer.eos_token_id
    if isinstance(eos, int):
        eos = [eos]
    need(isinstance(eos, list) and eos and all(type(x) is int and x >= 0 for x in eos), "explicit natural EOS IDs required")
    pad = tokenizer.pad_token_id
    if pad is None:
        pad = eos[0]
    generation_options = GenerationConfig(do_sample=False, num_beams=1, max_new_tokens=max_new,
        use_cache=True, bos_token_id=tokenizer.bos_token_id, pad_token_id=pad,
        eos_token_id=eos if natural else None, return_dict_in_generate=True,
        output_scores=False, output_logits=False, disable_compile=True)
    need(generation_options.disable_compile and generation_options.use_cache and generation_options.do_sample is False,
        "eager cached greedy generation contract required")
    return generation_options, eos


def generate(model, tok, ids, device, max_new, natural, budget, observed):
    import torch
    generation_options, eos = config_for(model, tok, max_new, natural)
    # Explicit final kwargs keep EOS=None from being refilled by model defaults.
    # Passing a config object together with overrides is deprecated in this pin.
    options = {key: getattr(generation_options, key) for key in ("do_sample", "num_beams", "max_new_tokens", "use_cache",
        "bos_token_id", "pad_token_id", "eos_token_id", "return_dict_in_generate", "output_scores",
        "output_logits", "disable_compile")}
    inputs = torch.tensor([ids], dtype=torch.long, device=device)
    mask = torch.ones_like(inputs)
    observer = Observer(model, device, budget) if observed else None
    output = cache = None
    try:
        with torch.inference_mode(), torch.autocast(device, enabled=False):
            if device == "cuda":
                torch.cuda.synchronize()
            started = time.perf_counter()
            if observer is not None:
                observer.started = started
                with observer:
                    output = model.generate(input_ids=inputs, attention_mask=mask,
                        streamer=observer, **options)
            else:
                output = model.generate(input_ids=inputs, attention_mask=mask, **options)
            generated = output.sequences[0, len(ids):].detach().cpu().tolist()
            answer = tok.decode(generated, skip_special_tokens=False)
            if device == "cuda":
                torch.cuda.synchronize()
            seconds = time.perf_counter() - started
            cache = cache_audit(output.past_key_values)
        need(generated and len(generated) <= max_new and seconds > 0, "nonempty bounded actual generation required")
        if not natural:
            need(len(generated) == max_new, "forced-length generation ended early")
        reason = "EOS" if natural and generated[-1] in eos else "MAX_NEW" if natural else "MAX_NEW_EOS_DISABLED"
        result = dict(seconds=seconds, generated_ids=generated, answer=answer,
            generated_tokens=len(generated), finish_reason=reason, natural_eos_ids=eos,
            tokens_per_second=len(generated)/seconds,
            characters_per_second=len(answer)/seconds, utf8_bytes_per_second=len(answer.encode("utf-8"))/seconds,
            returned_cache=cache, logits_fp32_observed=bool(observed))
        result["generation_parameters"] = options
        if observer is not None:
            need(observer.prompt_ids == ids and observer.ids == generated and len(observer.times) == len(generated),
                "streamer prompt/token IDs differ from actual result")
            result.update(first_token_ms=1000*observer.times[0], token_timestamps=observer.times,
                max_forward_return_cache_bytes=observer.cache_max_bytes,
                actual_logit_dtypes=sorted(observer.logit_dtypes), actual_logit_shapes=sorted(observer.logit_shapes),
                measurement="OBSERVER_STREAMER_CPU_COPY_AND_CACHE_AUDIT_OVERHEAD_INCLUDED")
        else:
            result["measurement"] = "UNOBSERVED_INSTALLED_HF_GENERATE; INPUT_UPLOAD_EXCLUDED; OUTPUT_DECODE_INCLUDED"
        return result
    finally:
        if observer is not None and observer.handle is not None:
            observer.__exit__(None)
        output = inputs = mask = cache = observer = None


def pair(model, tok, ids, device, max_new, natural, budget, plain_first, failures=None):
    from scripts.bench_infer import _CpuWatch
    values = {}
    for observed in ((False, True) if plain_first else (True, False)):
        watch = _CpuWatch()
        watch.start()
        primary = None
        try:
            result = generate(model, tok, ids, device, max_new, natural, budget, observed)
        except BaseException as exc:
            primary = error_record(exc)
            raise
        finally:
            try:
                system, own, external_load = watch.stop()
            except BaseException as exc:
                if primary is None:
                    raise
                if failures is not None:
                    failures.append(dict(original_generation_error=primary, cpu_watch_exit_error=error_record(exc)))
        result["cpu_load"] = dict(system_percent=system, process_machine_percent=own, external_percent=external_load)
        values["observed" if observed else "unobserved"] = result
    need(values["observed"]["generated_ids"] == values["unobserved"]["generated_ids"]
        and values["observed"]["finish_reason"] == values["unobserved"]["finish_reason"],
        "observation changed actual token IDs or termination")
    values.update(actual_token_ids_and_stop_equal=True,
        order="PLAIN_THEN_OBSERVED" if plain_first else "OBSERVED_THEN_PLAIN")
    return values


@contextmanager
def runtime(model, torch, assets, proof):
    context = (official.model_runtime(model, torch) if model == "falcon90m"
        else external.model_runtime(model, torch, assets, proof=proof.setdefault("strict_loader", {})))
    try:
        with context as value:
            lm, measured = value
            proof["strict_loader"] = measured
            try:
                yield lm
            except BaseException as exc:
                proof["primary_body_error"] = error_record(exc)
                raise
    except BaseException as exc:
        observed = error_record(exc)
        if proof.get("primary_body_error") is not None and observed != proof["primary_body_error"]:
            proof["loader_exit_error"] = observed
        raise


def assets_for(model):
    if model != "falcon90m":
        return external.asset_identity(model)
    need(common.digest(official.FALCON_REFERENCE) == official.FALCON_REFERENCE_SHA, "closed Falcon asset receipt differs")
    reference = json.loads(official.FALCON_REFERENCE.read_text())["asset_sha256"]
    actual = {name: common.digest(official.FALCON/name) for name in reference}
    need(actual == reference, "closed Falcon source assets differ")
    return dict(path=str(official.FALCON), files=actual)


def closed_evidence(model, spec, closed):
    need(model in MODELS and spec["id"] == closed.get("model") == model,
        "closed evaluated model ID differs")
    need(closed["returncode"] == 0 and closed["status"].endswith("FULL_COMPLETE"),
        "closed original full evaluator report required")
    proof = closed["model_proof"]
    need(spec["core_sha256"] == proof["initial_core_sha256"] == proof["final_core_sha256"],
        "closed evaluated initial/final core differs")
    need(proof["source_assets_unchanged"] is True,
        "closed evaluated source assets were not unchanged")
    need(spec["model_source_sha256"] == proof["model_source_sha256"],
        "closed model implementation pin differs")
    if model == "falcon90m":
        need(spec["assets"]["files"] == proof["asset_sha256"], "closed Falcon assets differ")
    else:
        need(spec["assets"] == closed["assets"] and proof["body_unchanged"] is True,
            "closed HF assets/body differ")


def metadata(args):
    profile = common.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    source = identity()
    need(profile.get("schema") == PROFILE and profile.get("tag") == TAG
        and profile.get("root_approved") is True and profile.get("authority_directive") == 96,
        "current explicit external resource authority/profile required")
    need(profile.get("deadline") == common.DEADLINE.isoformat()
        and source["sha256"] == args.source_sha256 == profile["source_sha256"], "current source/deadline differs")
    need(profile["max_worker_seconds"] == args.max_wall_sec == 1800
        and profile["timing_repetitions"] == 3 and profile["forced_new_tokens"] == 32
        and profile["natural_max_new"] == 64, "exact bounded resource protocol required")
    candidates = [r for r in profile["models"] if r["id"] == args.model]
    need(len(candidates) == 1 and args.model in MODELS, "one closed external model required")
    spec = candidates[0]
    closed = common.read_ref(spec["closed_report"])
    closed_evidence(args.model, spec, closed)
    need(args.mode != "probe" or (args.model == "gemma270" and args.device == "cuda"), "one explicit shared HF probe only")
    output = common.safe(profile["output"]) / (args.model + "_" + args.device + ("_probe" if args.mode == "probe" else ""))
    need(str(output.parent.relative_to(ROOT)) == "test_result/evidence/" + TAG and not output.exists(), "new exact lane output required")
    return profile, spec, output, source


def execute(args, profile, spec, output, source):
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
    from scripts.diag_p102a_logit_margin import memory_point
    for key, value in official.OFFLINE.items():
        os.environ[key] = value
    torch.set_num_threads(1 if args.device == "cpu" else 2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    budget = common.Budget(args.max_wall_sec)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, tag=TAG, model=args.model, device=args.device, mode=args.mode,
        started_at=datetime.now(timezone.utc).isoformat(), status="STARTED", source=source,
        profile_sha256=args.profile_sha256, training_updates=0, checkpoint_writes=0, quality_claim=False,
        records=[], natural_answers=[], model_proof={}, observation_failures=[], gpu_points=[], rss_before=common.rss(),
        protocol="HF_GENERATE_FP32_EAGER; CACHE_ON; NO_ASSISTANT_OR_COMPILE; BASE_PLAIN",
        generation_use_cache=True, loader_model_config_use_cache=False,
        cpu_hardware=dict(machine=platform.machine(), kernel=platform.release(), logical_cpus=os.cpu_count(),
            affinity=sorted(os.sched_getaffinity(0)),
            model=next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")), "NOT_RECORDED")),
        cpu_lane_caveat="STRICT_LOADER_INITIAL_CUDA_LOAD; CPU_GENERATION_ONLY_NOT_CPU_STARTUP_PROOF",
        cpu_threads=torch.get_num_threads(), torch_version=torch.__version__)
    rc = 9
    lm = body = tok = model_ref = None
    try:
        with common.wall(args.max_wall_sec), sdpa_kernel(SDPBackend.MATH), torch.inference_mode():
            report["idle"] = require_idle_gpu()
            point = memory_point()
            report["gpu_points"].append(point)
            need(point["free_mib"] >= 10240, "strict validation load requires10GiB currently free")
            torch.cuda.init()
            properties = torch.cuda.get_device_properties(0)
            total = properties.total_memory
            report["gpu_hardware"] = dict(name=properties.name, total_bytes=total,
                capability=[properties.major, properties.minor], multiprocessors=properties.multi_processor_count)
            cap = min(int(total*.8), (point["free_mib"]-1024)*2**20)
            torch.cuda.set_per_process_memory_fraction(cap/total, 0)
            report["allocator_cap_bytes"] = cap
            torch.cuda.reset_peak_memory_stats()
            assets = assets_for(args.model)
            need(assets == spec["assets"], "current closed model assets differ from resource profile")
            report["assets"] = assets
            if args.mode == "full":
                probe_path = common.safe(profile["output"])/"gemma270_cuda_probe/report.json"
                probe = json.loads(probe_path.read_text(encoding="utf-8"))
                need(probe.get("status") == "HF_RUNTIME_PROBE_COMPLETE_NOT_QUALITY" and probe.get("returncode") == 0
                    and probe.get("source") == source and probe.get("profile_sha256") == args.profile_sha256
                    and probe.get("model_object_released") is True and probe.get("originals_unchanged") is True,
                    "closed same-source/cache full-runtime probe required before matrix")
                report["shared_probe_sha256"] = common.digest(probe_path)
            with runtime(args.model, torch, assets, report["model_proof"]) as lm:
                body, tok = lm.model, lm.tokenizer
                model_ref = weakref.ref(body)
                need(state_fingerprint(body) == spec["core_sha256"], "closed evaluated core differs")
                report.update(cuda_validation_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    cuda_validation_peak_reserved_bytes=torch.cuda.max_memory_reserved())
                body.to(args.device)
                need(all(p.dtype == torch.float32 and str(p.device).split(":")[0] == args.device for p in body.parameters()),
                    "complete FP32 body must be on requested inference device")
                report.update(held_after_load=common.model_storage(body), rss_loaded=common.rss(),
                    parameters=sum(p.numel() for p in body.parameters()),
                    model_source_path=inspect.getfile(type(body)),
                    validation_model_source_sha256=common.digest(inspect.getfile(type(body))))
                need(report["validation_model_source_sha256"] == spec["model_source_sha256"],
                    "installed model implementation differs from the closed evaluator")
                if args.device == "cpu":
                    torch.cuda.empty_cache()
                report["cuda_generation_start"] = dict(allocated_bytes=torch.cuda.memory_allocated(),
                    reserved_bytes=torch.cuda.memory_reserved())
                torch.cuda.reset_peak_memory_stats()
                workloads = profile["workloads"][:1] if args.mode == "probe" else profile["workloads"]
                cases = profile["answer_cases"][:1] if args.mode == "probe" else profile["answer_cases"]
                for workload in workloads:
                    ids = tok.encode(workload["text"], add_special_tokens=False)
                    need(ids and workload["prompt_tokens"] in (128, 512), "fixed workload token source required")
                    ids = (ids*((workload["prompt_tokens"]+len(ids)-1)//len(ids)))[:workload["prompt_tokens"]]
                    need(max(ids) < body.config.vocab_size, "workload ID exceeds actual head")
                    for repeat in range(4):
                        budget.check()
                        record = pair(body, tok, ids, args.device, 32, False, budget, repeat%2 == 0,
                            report["observation_failures"])
                        record.update(workload=workload["id"], prompt_ids=ids, warmup=repeat == 0,
                            repeat=repeat, rss=common.rss())
                        report["records"].append(record)
                    report["gpu_points"].append(memory_point())
                    print(json.dumps(dict(model=args.model, device=args.device, workload=workload["id"], complete=True)), flush=True)
                for case in cases:
                    ids = tok.encode(case["question"], add_special_tokens=False)
                    record = pair(body, tok, ids, args.device, 64, True, budget, True, report["observation_failures"])
                    report["natural_answers"].append(dict(case=case, prompt_ids=ids, generation=record))
                report.update(held_after_generation=common.model_storage(body), rss_after_generation=common.rss(),
                    cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                    cuda_peak_scope="GENERATION_INTERVAL_AFTER_VALIDATION_RESET; CPU_BASELINE_SEPARATE; RESERVED_NOT_DEMAND")
                need(state_fingerprint(body) == spec["core_sha256"] and all(p.grad is None for p in body.parameters()),
                    "read-only final model/gradient contract differs")
                body = tok = None
            lm = None
            report["final_model_source_sha256"] = common.digest(report["model_source_path"])
            need(report["final_model_source_sha256"] == spec["model_source_sha256"], "model implementation changed at exit")
            need(assets_for(args.model) == assets and identity() == source, "assets or inference source changed during execution")
            expected_records, expected_cases = (4, 1) if args.mode == "probe" else (16, 4)
            need(len(report["records"]) == expected_records and len(report["natural_answers"]) == expected_cases,
                "all declared probe/matrix records required")
            report.update(originals_unchanged=True,
                status="HF_RUNTIME_PROBE_COMPLETE_NOT_QUALITY" if args.mode == "probe" else "HF_RESOURCE_LANE_COMPLETE_NOT_QUALITY")
            rc = 0
    except BaseException as exc:
        actual_error = error_record(exc)
        report.update(status="HF_RESOURCE_LANE_ERROR", error=report["model_proof"].get("primary_body_error", actual_error))
        if report["error"] != actual_error:
            report["boundary_error"] = actual_error
        print(json.dumps(dict(original_error=report["error"])), flush=True)
        rc = 130 if isinstance(exc, KeyboardInterrupt) else 9
    finally:
        lm = body = tok = None
        gc.collect()
        report["model_object_released"] = model_ref is None or model_ref() is None
        report["rss_closed"] = common.rss()
        if not report["model_object_released"]:
            report["model_cleanup_error"] = "live model Python reference remains"
            report["status"] = "HF_RESOURCE_CLEANUP_ERROR"
            rc = 9
        if torch.cuda.is_initialized():
            report["cuda_owned_cleanup"] = {}
            try:
                common.close_cuda(torch, report["cuda_owned_cleanup"])
                need(report["cuda_owned_cleanup"]["allocated_bytes"] == report["cuda_owned_cleanup"]["reserved_bytes"] == 0,
                    "owned CUDA allocations remain after workspace cleanup")
            except Exception as exc:
                report["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                report["status"] = "HF_RESOURCE_CLEANUP_ERROR"
                rc = 9
        report.update(returncode=rc, seconds=time.monotonic()-budget.started, ended_at=datetime.now(timezone.utc).isoformat())
        if not persist_report(output/"report.json", report):
            rc = 9
        print(json.dumps(dict(status=report["status"], model=args.model, device=args.device, returncode=rc, seconds=report["seconds"])), flush=True)
    return rc


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", required=True)
    p.add_argument("--profile-sha256", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--model", choices=MODELS, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), required=True)
    p.add_argument("--mode", choices=("probe", "full"), default="full")
    p.add_argument("--max-wall-sec", type=int, default=1800)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    try:
        profile, spec, output, source = metadata(args)
        if args.check_only:
            print(json.dumps(dict(status="STATIC_ONLY", model_loads=0, gpu_calls=0,
                source_sha256=source["sha256"], output=str(output.relative_to(ROOT)))))
            return 0
        need(time.time()+args.max_wall_sec+120 < common.DEADLINE.timestamp(), "entire lane must fit current authority")
        return execute(args, profile, spec, output, source)
    except Exception as exc:
        print(json.dumps(dict(status="ENTRY_ERROR", type=type(exc).__name__, message=str(exc))), file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
