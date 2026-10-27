#!/usr/bin/env python3
"""Frozen Native595 g128 deployment gate, never training or default adoption."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from dataclasses import asdict
import gc
import json
import os
from pathlib import Path
import statistics
import sys
import time
import weakref
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_resource_matrix as resource
from scripts import p014e_packed_g128 as packed

TAG = "p014e_native595_g128_v1_20261027"
SCHEMA = "P014E_FROZEN_PACKED_DEPLOYMENT_V1"
VARIANTS = ("fp32_unchanged", "ternary5_existing_twn")
MODES = ("prepare", "export", "baseline-cpu", "deploy-cpu", "baseline-cuda", "deploy-cuda", "readback")
OWN = ("scripts/diag_p014e_packed_deploy.py", "scripts/p014e_packed_g128.py",
       "scripts/test_p014e_packed_g128.py", "tinylm/model/lut.py")
need, safe, digest, sha = resource.need, resource.safe, resource.digest, resource.sha


def identity():
    files = dict(resource.identity()["files"])
    files.update({name: digest(safe(name)) for name in OWN})
    return dict(files=files, sha256=sha(files))


def write(path, value):
    resource.write_new(path, value)


def evidence():
    return safe("test_result/evidence/" + TAG)


def deploy_dir():
    return safe("runs/deploy/" + TAG)


def record_path(mode):
    return evidence() / (mode + ".json")


def closed(mode, profile):
    value = json.loads(record_path(mode).read_bytes())
    need(value.get("status") == "TECHNICAL_COMPLETE_NOT_QUALITY"
         and value.get("exit_code") == 0 and value.get("source") == identity()
         and value.get("phase") == mode and value.get("profile_sha256") == profile["_file_sha256"],
         "closed profile/source-matched phase required: " + mode)
    return value


def validate(profile, args):
    need(profile.get("schema") == SCHEMA and profile.get("tag") == TAG
         and profile.get("root_approved") is True and profile.get("authority_directive") == 96
         and profile.get("source_sha256") == identity()["sha256"], "current root/source profile required")
    need(profile.get("training_updates") == 0 and profile.get("additional_300m") is False
         and profile.get("variants") == list(VARIANTS) and profile.get("tile_rows") == 128
         and profile.get("head_rows") == 1024 and profile.get("forced_max_new") == 16
         and profile.get("natural_max_new") == 32 and profile.get("timing_repetitions") == 3,
         "fixed full deployment contract required")
    need(profile.get("deadline") == "2026-10-27T08:00:00+00:00"
         and datetime.now(timezone.utc) < resource.DEADLINE, "current authority expired")
    need(args.max_wall_sec == profile["phase_caps"][args.mode], "exact phase cap required")
    need((resource.DEADLINE - datetime.now(timezone.utc)).total_seconds() > args.max_wall_sec + 120,
         "whole phase plus closure cannot fit before deadline")
    base = resource.read_ref(profile["base_profile"])
    need(base["source_sha256"] == resource.identity()["sha256"], "original strict model route source differs")
    need([w["id"] for w in base["workloads"]] == ["ko128", "en128", "ko512", "en512"], "four frozen workloads required")
    spec = next(row for row in base["models"] if row["id"] == "native595-q")
    need(spec["route"] == "ternary" and spec["cfg"]["micro_group"] == 128, "native original-scale Q body required")
    need(digest(safe(base["tokenizer"]["path"])) == base["tokenizer"]["sha256"], "tokenizer changed")
    contract = profile["cpu_contract"]
    need(contract["actual_parent_exit"] == 0 and digest(safe(contract["path"])) == contract["sha256"],
         "actual CPU regression closure required")
    return base, spec


def sync(device):
    if device == "cuda":
        packed.torch.cuda.synchronize()


def assert_cuda_clean(proof):
    need(proof.get("allocated_bytes") == 0 and proof.get("reserved_bytes") == 0,
         "owned CUDA storage remains after cleanup")


@contextmanager
def reference_embedding(model, variant, rows):
    if variant == "fp32_unchanged":
        yield dict(retained_original_embedding_storage_bytes=0)
        return
    # Disposable runtime conversion only. Restore the original Parameter storage
    # before the strict source-core context checks it; no source checkpoint writes.
    original = model.emb.weight.detach()
    chunk = model.cfg.emb_chunk
    cpu_threads = packed.torch.get_num_threads()
    names = ("_emb_fmt", "_emb_code", "_emb_scale", "_emb_g")
    need(not any(hasattr(model, name) for name in names), "source embedding is already converted")
    try:
        # Export scales are made on CPU. Keep the reference quantizer on CPU
        # too, rather than attributing CPU/CUDA reduction drift to the codec.
        model.emb.weight.data = original.to("cpu")
        packed.torch.set_num_threads(1)
        model.quantize_embedding("ternary")
        packed.torch.set_num_threads(cpu_threads)
        if original.device.type != "cpu":
            model._emb_code = model._emb_code.to(original.device)
            model._emb_scale = model._emb_scale.to(original.device)
            model.emb.weight.data = model.emb.weight.data.to(original.device)
        model.cfg.emb_chunk = rows
        yield dict(retained_original_embedding_storage_bytes=original.untyped_storage().nbytes(),
                   retained_device=str(original.device), quantization_device="CPU_ONE_THREAD")
    finally:
        packed.torch.set_num_threads(cpu_threads)
        model.emb.weight.data = original
        model.cfg.emb_chunk = chunk
        for name in names:
            if hasattr(model, name):
                delattr(model, name)


def prompt_ids(base, tok):
    result = []
    for work in base["workloads"]:
        raw = tok.encode(work["text"] * 40).ids
        need(len(raw) >= work["prompt_tokens"], "frozen prompt too short")
        result.append(dict(id=work["id"], ids=raw[:work["prompt_tokens"]]))
    return result


def measured_suite(model, cfg, tok, base, profile, device, budget, oracle=None, progress=None):
    import torch
    from tinylm.infer.dialogue import make_prompt
    rows, tensors, allclose = [], [], []
    result = {} if progress is None else progress
    answers, probes = [], []
    result.update(status="SUITE_STARTED_NOT_COMPLETE", records=rows, answers=answers,
                  cost_probes=probes, oracle_errors=allclose)
    forward = resource.FP32Forward(model, device)
    prompts = prompt_ids(base, tok)
    # Cost gate uses both short/long contexts before opening the complete suite.
    for n in (0, 2):
        probes.append(resource.unobserved_generation(model, cfg, tok, prompts[n]["ids"], device, 2))
    forecast = max(x["seconds"] / 2 for x in probes) * (4 * (5 * 16 + 4) + 4 * 32) * 3 + 60
    remaining = min(budget.seconds - (time.monotonic() - budget.started),
                    (budget.deadline - datetime.now(timezone.utc)).total_seconds() - 120)
    if forecast > remaining:
        result.update(status="BUDGET_HOLD_NOT_FULL_SUITE", conservative_seconds=forecast,
                      remaining_seconds=remaining)
        return result, tensors
    for index, work in enumerate(prompts):
        budget.check()
        token = torch.tensor([work["ids"]], device=device)
        sequence, logits_kept = [], []
        with torch.no_grad():
            logits, kv = forward(token, use_cache=True, logits_last_only=True)
            for step in range(4):
                logits_kept.append(logits.detach().to("cpu").clone())
                chosen = int(logits.argmax(-1).item()) if oracle is None else oracle[index]["teacher_ids"][step]
                sequence.append(chosen)
                if step < 3:
                    logits, kv = forward(torch.tensor([[chosen]], device=device), past_kv=kv,
                                         use_cache=True, logits_last_only=True)
        del token, logits, kv
        if oracle is not None:
            expected = oracle[index]
            need(expected["id"] == work["id"] and expected["ids"] == work["ids"], "oracle input differs")
            for actual, wanted in zip(logits_kept, expected["logits"]):
                delta = (actual - wanted).abs()
                ok = bool(torch.allclose(actual, wanted, rtol=2e-5, atol=2e-6))
                allclose.append(dict(workload=work["id"], max_abs=float(delta.max()),
                                     mean_abs=float(delta.mean()), allclose=ok))
                need(ok, "same-device row-tile logits exceed declared tolerance")
        tensors.append(dict(**work, teacher_ids=sequence, logits=logits_kept))
        warm = resource.unobserved_generation(model, cfg, tok, work["ids"], device, 16)
        repeats = [resource.unobserved_generation(model, cfg, tok, work["ids"], device, 16)
                   for _ in range(profile["timing_repetitions"])]
        observed = resource.one_generation(model, cfg, tok, work["ids"], device, 16,
                                            natural=False, chatml=False, budget=budget)
        need(all(x["generated_ids"] == warm["generated_ids"] and x["metadata"] == warm["metadata"]
                 for x in repeats + [dict(generated_ids=observed["generated_ids"], metadata=observed["metadata"]) ]),
             "observed/unobserved or repeated generation differs")
        rows.append(dict(workload=work["id"], warmup=warm, repeats=repeats, observed=observed,
                         median_seconds=statistics.median(x["seconds"] for x in repeats)))
        print(json.dumps(dict(workload=work["id"], completed=True)), flush=True)
    for case in base["answer_cases"]:
        budget.check()
        ids = tok.encode(make_prompt(case["question"], case["mode"])).ids
        row = resource.one_generation(model, cfg, tok, ids, device, 32,
                                       natural=True, chatml=case["mode"] == "chatml", budget=budget)
        answers.append(dict(case=case, generation=row))
    result.update(status="FULL_TECHNICAL_SUITE_NOT_QUALITY", conservative_seconds=forecast,
                  storage=resource.model_storage(model), rss=resource.rss())
    return result, tensors


def export(base, spec, profile, budget, report):
    import torch
    proof, files = {}, []
    report.update(payloads=files, source_proof=proof)
    deploy_dir().mkdir(parents=True, exist_ok=False)
    with resource.frozen_model(spec, base["tokenizer"], "cpu", budget, proof) as loaded:
        model, cfg, tok, route = loaded
        ref = weakref.ref(model)
        for variant in VARIANTS:
            budget.check()
            data = packed.export_payload(model, provenance=dict(source_checkpoint=spec["checkpoint"],
                source_core=spec["core_sha256"], tokenizer=base["tokenizer"], route="ternary",
                source_sha256=identity()["sha256"], embedding_quality="UNCHANGED" if variant == VARIANTS[0]
                else "EXISTING_TWN_EMBEDDING_LOSS_MUST_BE_REVIEWED"), tile_rows=128,
                embedding_format=variant, head_rows=1024)
            path = deploy_dir() / (variant + ".pt")
            size = packed.save_new(data, path)
            files.append(dict(variant=variant, path=str(path.relative_to(ROOT)), bytes=size,
                              sha256=digest(path), storage=packed.payload_storage(data)))
            del data
            print(json.dumps(dict(exported=variant, bytes=size)), flush=True)
    del loaded, model, cfg, tok, route
    gc.collect()
    need(ref() is None, "source model remains referenced after export")
    report.update(payloads=files, source_proof=proof, source_model_released=True,
                  original_checkpoint_loads=1, original_checkpoint_writes=0)


def verified_reference_copy(source):
    """A separate ordinary Q model, never disable the source route guard."""
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts.interactive_research_infer import state_fingerprint
    with torch.random.fork_rng(devices=[]):
        reference = TiedMLPTransformer(TMTConfig(**asdict(source.cfg)))
    reference.load_state_dict(source.state_dict(), strict=True)
    reference.eval().requires_grad_(False)
    reference.freeze_quant()
    need(state_fingerprint(reference) == state_fingerprint(source), "independent reference core differs")
    originals, copies = list(source._tlinears()), list(reference._tlinears())
    need(len(originals) == len(copies)
         and all(torch.equal(a._wq, b._wq) for a, b in zip(originals, copies)),
         "independent ordinary Q weights differ from verified explicit Q route")
    return reference


def baseline(base, spec, profile, budget, report, device):
    import torch
    closed("export", profile)
    proof, data, records = {}, {}, []
    hold = False
    report.update(variants=records, source_proof=proof)
    cpu_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    with resource.frozen_model(spec, base["tokenizer"], "cpu", budget, proof) as loaded:
        source, _, tok, route = loaded
        source_ref = weakref.ref(source)
        model = verified_reference_copy(source)
    del loaded, source, route
    gc.collect()
    need(source_ref() is None, "source remains referenced after guarded copy")
    cfg = model.cfg
    torch.set_num_threads(cpu_threads)
    ref = weakref.ref(model)
    report.update(reference_path="SEPARATE_ORDINARY_Q_COPY_CORE_AND_FROZEN_WEIGHTS_EXACT",
                  source_model_released=True,
                  quantization_device="CPU_ONE_THREAD_FOR_BOTH_SOURCE_AND_PAYLOAD")
    try:
        if device != "cpu":
            model.to(device)
            for module in model._tlinears():
                module._wq = module._wq.to(device)
        for variant in VARIANTS:
            record = dict(variant=variant, result={})
            records.append(record)
            with reference_embedding(model, variant, 1024) as retention:
                record["conversion_retention"] = retention
                result, tensors = measured_suite(model, cfg, tok, base, profile, device, budget,
                                                  progress=record["result"])
                data[variant] = tensors
                if result["status"] != "FULL_TECHNICAL_SUITE_NOT_QUALITY":
                    hold = True
                    break
    finally:
        model.clear_quant()
        model.to("cpu")
        model = None
        gc.collect()
        report["reference_model_released"] = ref() is None
    need(report["reference_model_released"], "independent reference remains held")
    report.update(original_checkpoint_loads=1, original_checkpoint_writes=0)
    if hold:
        return 8
    path = deploy_dir() / ("baseline_" + device + "_oracle.pt")
    need(not path.exists(), "new oracle path required")
    with path.open("xb") as stream:
        torch.save(data, stream)
    need(path.stat().st_size < 20_000_000, "oracle must remain below20MB")
    report.update(variants=records, oracle=dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                  bytes=path.stat().st_size), source_proof=proof, source_model_released=True,
                  original_checkpoint_loads=1, original_checkpoint_writes=0)
    return 0


def deploy(base, spec, profile, budget, report, device):
    import torch
    from tokenizers import Tokenizer
    original_load = torch.load
    exported, baseline_report = closed("export", profile), closed("baseline-" + device, profile)
    need([(row["variant"], row["path"]) for row in exported["payloads"]]
         == [(variant, str((deploy_dir() / (variant + ".pt")).relative_to(ROOT))) for variant in VARIANTS],
         "export receipt payload namespace/variant differs")
    oracle_path = safe(baseline_report["oracle"]["path"])
    need(oracle_path == deploy_dir() / ("baseline_" + device + "_oracle.pt"),
         "oracle receipt device/namespace differs")
    need(digest(oracle_path) == baseline_report["oracle"]["sha256"], "oracle changed")
    allowed = {str(safe(row["path"])) for row in exported["payloads"]} | {str(oracle_path)}
    loads, records = [], []
    report.update(variants=records, torch_load_files=loads, original_checkpoint_loads=0,
                  original_checkpoint_writes=0)
    def guarded_load(file, *args, **kwargs):
        name = str(Path(getattr(file, "name", file)).absolute())
        need(name in allowed and kwargs.get("weights_only") is True, "only new payload/oracle tensor loads permitted")
        loads.append(name)
        return original_load(file, *args, **kwargs)
    tok = Tokenizer.from_file(str(safe(base["tokenizer"]["path"])))
    with patch.object(torch, "load", guarded_load):
        with oracle_path.open("rb") as stream:
            oracle = torch.load(stream, map_location="cpu", weights_only=True)
        for row in exported["payloads"]:
            variant, path = row["variant"], safe(row["path"])
            need(digest(path) == row["sha256"], "deployment payload changed")
            started = time.perf_counter()
            record = dict(variant=variant, load_attempted=True, load_completed=False, result={})
            records.append(record)
            model, ref = None, None
            try:
                model = packed.load_file(path, device=device)
                sync(device)
                ref = weakref.ref(model)
                record.update(load_completed=True, load_seconds=time.perf_counter() - started,
                              storage_after_load=resource.model_storage(model), rss_after_load=resource.rss())
                record["result"], tensors = measured_suite(model, model.cfg, tok, base, profile, device,
                                                            budget, oracle=oracle[variant], progress=record["result"])
                del tensors
                if device == "cuda":
                    sync(device)
                    record.update(cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                                  cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved())
                if record["result"]["status"] == "FULL_TECHNICAL_SUITE_NOT_QUALITY":
                    expected = next(x for x in baseline_report["variants"] if x["variant"] == variant)["result"]
                    for actual, wanted in zip(record["result"]["records"], expected["records"]):
                        need(actual["observed"]["generated_ids"] == wanted["observed"]["generated_ids"]
                             and actual["observed"]["metadata"] == wanted["observed"]["metadata"],
                             "packed forced IDs/termination differ from same-device source")
                    for actual, wanted in zip(record["result"]["answers"], expected["answers"]):
                        need(actual["generation"]["generated_ids"] == wanted["generation"]["generated_ids"]
                             and actual["generation"]["metadata"] == wanted["generation"]["metadata"],
                             "packed natural IDs/termination differ from same-device reference")
                    record["same_device_ids_and_stops_equal"] = True
                record["payload_bytes_unchanged"] = digest(path) == row["sha256"]
                need(record["payload_bytes_unchanged"], "new payload changed during execution")
            except BaseException as exc:
                record["error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
                raise
            finally:
                try:
                    if model is not None:
                        model.to("cpu")
                except Exception as exc:
                    record["release_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                finally:
                    model = None
                    gc.collect()
                    record["model_released"] = ref() is None if ref is not None else None
                    if device == "cuda":
                        try:
                            record["cleanup"] = resource.close_cuda(torch)
                            assert_cuda_clean(record["cleanup"])
                            torch.cuda.reset_peak_memory_stats()
                        except Exception as exc:
                            record["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
            need(record["model_released"] and "release_error" not in record
                 and "cleanup_error" not in record, "packed release/cleanup incomplete")
            if record["result"]["status"] != "FULL_TECHNICAL_SUITE_NOT_QUALITY":
                report.update(variants=records, torch_load_files=loads, original_checkpoint_loads=0,
                              original_checkpoint_writes=0)
                return 8
    report.update(variants=records, torch_load_files=loads, original_checkpoint_loads=0, original_checkpoint_writes=0)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--max-wall-sec", type=int, required=True)
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--execute", action="store_true")
    execution.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    base, spec = validate(profile, args)
    profile["_file_sha256"] = args.profile_sha256
    if args.check_only:
        print(json.dumps(dict(schema=SCHEMA, status="METADATA_ONLY_NOT_MODEL", mode=args.mode,
                              source_sha256=identity()["sha256"], model_loads=0, gpu_calls=0)))
        return 0
    import torch
    torch.set_num_threads(2 if args.mode.endswith("cuda") else 1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    budget, source = resource.Budget(args.max_wall_sec), identity()
    report = dict(schema=SCHEMA, tag=TAG, phase=args.mode, source=source, profile_sha256=args.profile_sha256,
                  started_at=datetime.now(timezone.utc).isoformat(), pid=os.getpid(), status="STARTED",
                  training_updates=0, additional_300m=False, quality_claim=False,
                  torch_version=torch.__version__, cpu_threads=torch.get_num_threads(),
                  cpu_affinity="OS_SCHEDULED_SHARED_HOST", use_cache=True, mtp=False,
                  attention="SDPA_MATH", compute="FP32", rss_before=resource.rss())
    rc, device = 9, "cuda" if args.mode.endswith("cuda") else "cpu"
    try:
        need(args.mode == "prepare" or args.execute, "actual model phase requires explicit execute")
        need(not record_path(args.mode).exists(), "phase already has evidence; new suffix required")
        with resource.wall(args.max_wall_sec):
            if device == "cuda":
                from scripts.interactive_research_infer import require_idle_gpu
                from scripts.diag_p102a_logit_margin import memory_point
                report["idle_proof"] = require_idle_gpu()
                report["memory_before"] = memory_point()
                need(report["memory_before"]["free_mib"] >= 2048, "less than2GiB free")
                torch.cuda.init()
                torch.cuda.reset_peak_memory_stats()
            else:
                need(not torch.cuda.is_initialized(), "CPU phase must not initialize CUDA")
            if args.mode == "prepare":
                report["original_checkpoint_loads"] = 0
            elif args.mode == "export":
                closed("prepare", profile)
                export(base, spec, profile, budget, report)
            elif args.mode.startswith("baseline-"):
                rc = baseline(base, spec, profile, budget, report, device)
            elif args.mode.startswith("deploy-"):
                rc = deploy(base, spec, profile, budget, report, device)
            else:
                report["phases"] = {}
                for mode in MODES:
                    if mode in ("prepare", "readback"):
                        continue
                    if record_path(mode).exists():
                        value = json.loads(record_path(mode).read_bytes())
                        need(value["source"] == source and value["phase"] == mode
                             and value["profile_sha256"] == args.profile_sha256, "readback profile/source mismatch")
                        report["phases"][mode] = dict(status=value["status"], exit_code=value["exit_code"])
                    else:
                        report["phases"][mode] = dict(status="NOT_RUN", exit_code=None)
                rc = 0 if all(row["exit_code"] == 0 for row in report["phases"].values()) else 8
            need(identity() == source, "deployment source changed during execution")
            if rc != 8:
                rc = 0
                report["status"] = "TECHNICAL_COMPLETE_NOT_QUALITY"
            else:
                report["status"] = "BUDGET_HOLD_NOT_FULL_SUITE"
    except BaseException as exc:
        report["status"] = "ERROR_NOT_COMPLETE"
        report["error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
        rc = 9
    finally:
        if device == "cuda" and torch.cuda.is_initialized():
            try:
                report["final_cuda_cleanup"] = resource.close_cuda(torch)
                assert_cuda_clean(report["final_cuda_cleanup"])
            except Exception as exc:
                report["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                report["status"], rc = "ERROR_NOT_COMPLETE", 9
        report.update(exit_code=rc, seconds=time.monotonic() - budget.started,
                      ended_at=datetime.now(timezone.utc).isoformat(), rss_after=resource.rss(),
                      cuda_initialized=torch.cuda.is_initialized())
        write(record_path(args.mode), report)
        print(json.dumps(dict(phase=args.mode, status=report["status"], exit_code=rc,
                              seconds=report["seconds"])), flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
