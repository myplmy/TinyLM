"""Apply existing GSQ coordinate scaling to real ACTD, then deploy its learned banks."""

import argparse
from contextlib import ExitStack
import fcntl
from functools import partial
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
from tokenizers import Tokenizer

from scripts import diag_p106b_gsq_actual_actd_start as original
from scripts import p106b_gsq_coordinates as coordinates
from scripts import p106b_gsq_native_deploy as native
from scripts import p106b_gsq_objective as objective


ROOT = original.ROOT
TAG = "p106b_gsq_scaled_actd_deploy_v1_20261119"
OUT = original.OUT.with_name(TAG)
BASE, CPU, TOKEN = native.prefill.base, native.prefill.text, native.prefill.token
PROMPTS = TOKEN.OUT / "report.json"
DEPLOY = OUT / "dense14_5trit.bin"
GAIN = 4096.
LIMIT = 150
GEN = 8
ATOL = 0.001


def gate(reserve=0):
    original.time_gate(reserve)
    if (OUT / "STOP").exists():
        raise TimeoutError("GSQ deploy run local STOP")


def read(path):
    return original.input_cache.read(path)


def write(path, value):
    with path.open("x", encoding="utf-8") as result:
        json.dump(value, result, ensure_ascii=False, allow_nan=False, indent=2)
        result.write("\n")


def contract():
    current, groups, config = original.sources()
    previous_path = original.OUT / "profile.json"
    previous = read(previous_path)
    control_path = original.OUT / "report.json"
    control = read(control_path)
    if (any(current[k] != previous[k] for k in previous if k != "plan_sha256")
            or not control["result_complete"] or not control["paired_initial_match"]
            or control["profile_sha256"] != BASE.SHA(previous_path)):
        raise ValueError("Exact archived GSQ inputs and completed control required")
    inputs = read(PROMPTS)["runs"]["split_model"][0]["outputs"]
    tok = Tokenizer.from_file(str(TOKEN.TOK))
    long_ids = {key: tok.encode(inputs[key]["decoded"], add_special_tokens=False).ids
                for key in ("english", "korean")}
    if (BASE.SHA(TOKEN.TOK) != TOKEN.EXPECTED_SHA
            or any(len(ids) != 1017 or ids != inputs[key]["ids"] for key, ids in long_ids.items())):
        raise ValueError("Long requests must preserve the original 1,017-token tokenizer comparison")
    short = np.random.default_rng(6414).integers(35, 32768, size=(2, 41)).tolist()
    requests = {"short_0": short[0], "short_1": short[1], **long_ids}
    files = (Path(__file__), Path(native.__file__), Path(coordinates.__file__), Path(TOKEN.__file__),
             Path(native.prefill.__file__), Path(native.codec.__file__),
             *(ROOT / name for name in (BASE.CPP, BASE.C, native.prefill.prior.avx.LOOKUP, CPU.SCRIPT, CPU.WRAPPER)),
             previous_path, control_path, PROMPTS, TOKEN.TOK)
    pins = dict(current["source_pins"])
    pins.update({path.resolve().relative_to(ROOT).as_posix(): BASE.SHA(path) for path in files})
    profile = dict(current, tag=TAG, source_pins=pins, coordinate_gain=GAIN,
                   initial_coordinate_margin=4.6/GAIN, prior_adam_bound=0.0016175,
                   run_order=["scaled_gsq"], reused_control=original.TAG,
                   requests=requests, generation_tokens=GEN, numeric_atol=ATOL,
                   deployment_model_bytes=native.MODEL_BYTES, deployment_file_writes=1,
                   checkpoint_writes=0)
    return profile, groups, config


def verified():
    profile = read(OUT / "profile.json")
    current, groups, config = contract()
    if profile != current or BASE.SHA(OUT / "plan_at_execution.md") != profile["plan_sha256"]:
        raise ValueError("GSQ run source seal or lookup plans changed")
    compiler = read(OUT / "compiler.json")
    if (compiler["source_sha256"] != sha256(native.render_engine()).hexdigest().upper()
            or compiler["prefill"] != native.PREFILL):
        raise ValueError("Native engine source or bounded prefill changed")
    for executable in compiler["binaries"].values():
        p = Path(executable["path"])
        if not p.is_relative_to(Path("/tmp")) or p.is_symlink() or BASE.SHA(p) != executable["sha256"]:
            raise ValueError("Built native binary changed")
    return profile, groups, config


def prepare():
    gate()
    if OUT.exists():
        raise FileExistsError(OUT)
    profile, _, _ = contract()
    compiler = native.build_engine()
    example = torch.arange(2 * 2 * native.GROUP, dtype=torch.int16).reshape(2,2,native.GROUP) % 3 - 1
    code, count = native.codec.strict_pack(example)
    if count != native.GROUP or not torch.equal(native.codec.unpack_trits(code, count), example):
        raise ValueError("CPU packed group proof failed")
    geometry = read(ROOT / "handoff/audit/research_20261118_01a1e647/GSQ_DENSE14_PACKED_GEOMETRY_READBACK_v1.json")
    expected = geometry["analytic_total_payload_bytes"] - 4 + len(native.MAGIC) + 3*4*native.LAYERS
    if expected != native.MODEL_BYTES:
        raise ValueError("Packed geometry plus route metadata differs")
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(original.PLAN.read_bytes())
    write(OUT / "compiler.json", compiler)
    write(OUT / "profile.json", profile)
    verified()
    print("GSQ_SCALED_PREPARED", profile["coordinate_gain"], compiler["source_sha256"], expected, flush=True)


@torch.inference_mode()
def reference_outputs(bridge, prompts):
    model = bridge.model
    model.eval()
    model.cfg.kv_dtype = "fp16"
    results, scores = {}, {}
    with bridge.installed(), bridge.realization(original.SEED, backward_expected=False), sdpa_kernel(SDPBackend.MATH):
        for name, ids in prompts.items():
            gate(10)
            tokens = torch.tensor([ids], dtype=torch.long, device=bridge.device)
            cache = None
            for window in tokens.split(native.PREFILL, dim=1):
                logits, cache = model(window, past_kv=cache, use_cache=True, logits_last_only=True)
            decoded, rows, margins = [], [], []
            for index in range(GEN):
                row = logits[0, 0].cpu()
                best, winner = row.topk(2)
                token = int(row.argmax())
                if not bool(torch.isfinite(row).all()) or int(winner[0]) != token:
                    raise ValueError("Reference needs finite scores and a reproducible top token")
                decoded.append(token)
                margins.append(float(best[0]-best[1]))
                if name.startswith("short_"):
                    rows.append(row.numpy())
                if index + 1 < GEN:
                    generated = torch.tensor([[token]], dtype=torch.long, device=tokens.device)
                    logits, cache = model(generated, past_kv=cache, use_cache=True, logits_last_only=True)
            if len(cache) != native.LAYERS or any(v.dtype != torch.float16 for pair in cache.values() for v in pair):
                raise ValueError("Dense14 reference FP16 cache contract differs")
            if rows:
                scores[name] = np.stack(rows)
            results[name] = dict(ids=decoded, margin_min=min(margins))
    return results, scores


def worker():
    from scripts.diag_p107_hybrid_mntp import close_owned_cuda

    gate(75)
    profile, groups, cfg = verified()
    original.manual.require_idle_gpu()
    bridge = None
    make_bridge = objective.ObjectiveBridge

    def build(model, arm, *, logit_strength):
        nonlocal bridge
        if arm != "gsq" or bridge is not None:
            raise ValueError("Only one isolated scaled GSQ arm belongs in this process")
        with patch.object(objective, "GSQBank", partial(coordinates.ScaledGSQBank, gain=GAIN)):
            bridge = make_bridge(model, arm, logit_strength=logit_strength)
        return bridge

    with patch.object(objective, "ObjectiveBridge", build):
        result = original.train_arm("gsq", profile, groups, cfg)
    control = read(original.OUT / "report.json")["arms"]["gsq"]
    fields = ("initial_core_sha256", "initial_codes", "deterministic_input_probe")
    if not all(result[field] == control[field] for field in fields):
        raise ValueError("Initial model, trit digest or fixed initial ACTD differs from the archived control")
    bridge.banks.zero_grad(set_to_none=True)
    bridge.model.zero_grad(set_to_none=True)
    bridge.model.eval()
    receipt = native.save_banks(bridge, DEPLOY, result["final_codes"]["sha256"])
    numeric, scores = reference_outputs(bridge, profile["requests"])
    with (OUT / "short_logits.npz").open("xb") as raw:
        np.savez(raw, **scores)
    material = dict(train=result, artifact=receipt, reference=numeric, initial_match=True,
                    short_logits_sha256=BASE.SHA(OUT / "short_logits.npz"))
    write(OUT / "worker_material.json", material)
    del bridge
    gc.collect()
    close_owned_cuda(torch, material)
    write(OUT / "worker.json", material)
    print("GSQ_SCALED_WORKER", result["optimizer_steps"], result["final_codes"]["counts"], receipt["bytes"], flush=True)


def gpu():
    gate(LIMIT)
    profile = read(OUT / "profile.json")
    entry = original.manual.require_idle_gpu()
    samples_path = OUT / "gpu_device_100ms.csv"
    with samples_path.open("xb") as stream:
        sampler = subprocess.Popen((*original.sampling.DEVICE, f"--loop-ms={original.sampling.INTERVAL_MS}"), stdout=stream)
        try:
            command = ["timeout", "--kill-after=8s", "125s", sys.executable, "-B", "-u", "-m",
                       "scripts.diag_p106b_gsq_scaled_actd_deploy", "worker"]
            called = subprocess.run(command, cwd=ROOT, check=False)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    released = original.manual.require_idle_gpu()
    samples = original.sampling.read_samples(samples_path)
    preserved = all(BASE.SHA(ROOT / path) == digest for path, digest in profile["source_pins"].items())
    write(OUT / "gpu_report.json", dict(exit=called.returncode, entry=entry, released=released,
         device_peak=max(samples, key=lambda row:row["occupied_mib"]) if samples else None,
         profile_sha256=BASE.SHA(OUT / "profile.json"), sources_preserved=preserved,
         worker_sha256=BASE.SHA(OUT / "worker.json") if called.returncode == 0 else None))
    return called.returncode if called.returncode else (0 if samples and preserved else 8)


def text_request(binary, assets, text, index):
    with ExitStack() as resources:
        documents = tuple(BASE.memfile(f"p106b_gsq_{index}_{stage}") for stage in range(3))
        for fd in documents:
            resources.callback(os.close, fd)
        fds = (*assets, *documents)
        command = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(ROOT / CPU.SCRIPT),
                   "encode", binary, *map(str, fds)]
        started = perf_counter()
        call = subprocess.run(command, input=text, pass_fds=fds, cwd=ROOT, capture_output=True, timeout=80)
        if call.returncode:
            print(call.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
            call.check_returncode()
        return json.loads(call.stdout), perf_counter() - started


def compare_deployment(profile, references, *, artifact_sha256, result_path):
    cpu = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    binary = {k: v["path"] for k, v in read(OUT / "compiler.json")["binaries"].items()}
    inputs = read(PROMPTS)["runs"]["split_model"][0]["outputs"]
    tok = Tokenizer.from_file(str(TOKEN.TOK))
    short, text = {}, {}
    with ExitStack() as resources, np.load(OUT / "short_logits.npz", allow_pickle=False) as scores:
        def allocate(name):
            fd = BASE.memfile(name)
            resources.callback(os.close, fd)
            return fd

        handles = [allocate(name) for name in ("gsq_packed", "gsq_vocab", "gsq_merges")]
        with DEPLOY.open("rb") as source, os.fdopen(os.dup(handles[0]), "wb") as destination:
            shutil.copyfileobj(source, destination, length=1 << 20)
        for fd, blob in zip(handles[1:], TOKEN.wire(json.loads(TOKEN.TOK.read_bytes())), strict=True):
            CPU.store(fd, blob)
        for fd in handles:
            fcntl.fcntl(fd, BASE.prior.DEPLOY.F_ADD_SEALS, BASE.prior.DEPLOY.SEALS)
            if fcntl.fcntl(fd, BASE.prior.DEPLOY.F_GET_SEALS) != BASE.prior.DEPLOY.SEALS:
                raise ValueError("Read-only memfd model and tokenizer are required")
        for name in ("short_0", "short_1"):
            actual, solver = BASE.run_native(binary["numeric"], handles[0], profile["requests"][name], scores=True)
            expected = references[name]["ids"]
            history = 0
            while history + 1 < GEN and actual["ids"][history] == expected[history]:
                history += 1
            error = float(np.max(np.abs(solver[:history+1] - scores[name][:history+1])))
            if not np.isfinite(error) or actual["model_bytes"] != native.MODEL_BYTES:
                raise ValueError("Short native path produced a nonfinite score or mismatched model")
            short[name] = dict(reference=expected, native=actual, max_abs_same_history=error,
                               comparable_rows=history+1, same_ids=actual["ids"]==expected,
                               passed=actual["ids"]==expected and error <= ATOL)
        for index, name in enumerate(("english", "korean")):
            actual, elapsed = text_request(binary["text"], handles, inputs[name]["decoded"].encode("utf-8"), index)
            write(OUT / f"{name}_text.json", actual)
            engine = actual["native"]
            if (actual["encoding"]["ids"] != profile["requests"][name]
                    or actual["decoding"]["text"] != tok.decode(engine["ids"], skip_special_tokens=True)
                    or not actual["encoding"]["pid"] == actual["native_pid"] == actual["decoding"]["pid"]
                    or engine["model_bytes"] != native.MODEL_BYTES or engine["kv_bytes"] != 11_010_048):
                raise ValueError("Full request input, output decoder, memory or PID contract differs")
            peak = max(*(engine[stage][key] for stage in ("before", "loaded", "prefilled", "complete")
                         for key in ("rss", "vm_hwm")),
                       *(value for side in ("encoding", "decoding") for stage in ("startup", "loaded", "complete")
                         for value in actual[side][stage].values()))
            text[name] = dict(peak_bytes=peak, within_40mb=peak <= 40_000_000, full_seconds=elapsed,
                              prefill_seconds=engine["seconds"][0], ids=engine["ids"],
                              reference=references[name]["ids"], same_ids=engine["ids"]==references[name]["ids"])
    passed = all(v["passed"] for v in short.values()) and all(v["same_ids"] and v["within_40mb"] for v in text.values())
    write(result_path, dict(cpu=cpu, short=short, text=text, passed=passed,
         model_bytes=native.MODEL_BYTES, profile_sha256=BASE.SHA(OUT / "profile.json"),
         source_unchanged=BASE.SHA(DEPLOY)==artifact_sha256))
    print("GSQ_SCALED_DEPLOY", passed, {k: v["max_abs_same_history"] for k,v in short.items()}, text, flush=True)
    return 0 if passed else 8


def deploy():
    gate(220)
    profile, _, _ = verified()
    prior = read(OUT / "gpu_report.json")
    trained = read(OUT / "worker.json")
    artifact_sha = trained["artifact"]["artifact_sha256"]
    if (prior["exit"] != 0 or not prior["sources_preserved"] or not trained["initial_match"]
            or prior["profile_sha256"] != BASE.SHA(OUT / "profile.json")
            or prior["worker_sha256"] != BASE.SHA(OUT / "worker.json")
            or BASE.SHA(DEPLOY) != artifact_sha
            or BASE.SHA(OUT / "short_logits.npz") != trained["short_logits_sha256"]):
        raise ValueError("Completed actual training and exact packed artifact required")
    return compare_deployment(profile, trained["reference"], artifact_sha256=artifact_sha,
                              result_path=OUT / "deployment_report.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "gpu", "worker", "deploy"))
    phase = parser.parse_args().phase
    gpu_phase = phase in ("gpu", "worker")
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if gpu_phase else "")
            or gpu_phase and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8"):
        parser.error("Set a CPU-only or authorized single-device environment")
    if gpu_phase:
        return gpu() if phase == "gpu" else worker()
    return prepare() if phase == "prepare" else deploy()


if __name__ == "__main__":
    raise SystemExit(main())
