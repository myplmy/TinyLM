"""Recover the completed dense14 GSQ banks after a post-export cleanup failure."""

import ast
from hashlib import sha256
import os
from pathlib import Path
import struct

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_gsq_scaled_actd_deploy as job
from tinylm.config import TMTConfig
from tinylm.model.ternary import TLinear, ternary_g
from tinylm.model.transformer import TiedMLPTransformer


GPU_LOG = job.ROOT / "test_result/101_log_20261119_P106B_Stage7gsY_ScaledDeploy_GPU.txt"
STEPS = job.original.UPDATES


def inspect_transaction():
    profile_path = job.OUT / "profile.json"
    profile = job.read(profile_path)
    deployment = job.native.MODEL_BYTES
    report = job.read(job.OUT / "gpu_report.json")
    lines = GPU_LOG.read_text(encoding="utf-8").splitlines()
    if (profile["tag"] != job.TAG or deployment != job.DEPLOY.stat().st_size
            or report["profile_sha256"] != job.BASE.SHA(profile_path) or report["exit"] != 1
            or not report["sources_preserved"] or report["released"]["competing_compute_pids"]
            or not lines[-1].endswith("actual_exit=1") or not any("CUDA objects survive" in line for line in lines)
            or (job.OUT / "worker.json").exists()):
        raise ValueError("Require the original completed GPU updates and specific post-export cleanup failure")
    archived = Path(job.__file__).resolve().relative_to(job.ROOT).as_posix()
    if job.BASE.SHA(job.OUT / "plan_at_execution.md") != profile["plan_sha256"]:
        raise ValueError("Historical experiment plan differs")
    for name, digest in profile["source_pins"].items():
        path = job.OUT / "runner_at_execution.py" if name == archived else job.ROOT / name
        if job.BASE.SHA(path) != digest:
            raise ValueError(f"Historical source pin differs: {name}")
    compiler = job.read(job.OUT / "compiler.json")
    if compiler["source_sha256"] != sha256(job.native.render_engine()).hexdigest().upper():
        raise ValueError("Sealed dense14 engine source changed")
    for executable in compiler["binaries"].values():
        p = Path(executable["path"])
        if not p.is_relative_to(Path("/tmp")) or p.is_symlink() or job.BASE.SHA(p) != executable["sha256"]:
            raise ValueError("Sealed dense14 executable changed")
    prefix = "GSQ_ACTD_UPDATE gsq "
    updates = [ast.literal_eval(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    if ([row["step"] for row in updates] != list(range(1, STEPS+1))
            or sum(row["ce_targets"] for row in updates) != 1544
            or sum(row["actd_targets"] for row in updates) != 1222):
        raise ValueError("Completed optimizer updates and original denominators required")
    return profile, updates


@torch.inference_mode()
def restore(profile):
    cfg = TMTConfig(**profile["config"])
    torch.manual_seed(profile["seed"])
    model = TiedMLPTransformer(cfg).eval()
    control = job.read(job.original.OUT / "report.json")["arms"]["gsq"]
    if job.original.manual.state_fingerprint(model) != control["initial_core_sha256"]:
        raise ValueError("Initial CPU model reconstruction differs from the archived GPU arm")
    model.set_anneal(1.)
    model.cfg.kv_dtype = "fp16"
    model.refresh_quant = lambda: None
    body = [module for module in model.modules() if isinstance(module, TLinear)]
    keys = {id(module): f"weight_{i:04}" for i, module in enumerate((*body, model.emb, model.emb_up))}
    packed = {}

    with job.DEPLOY.open("rb") as payload:
        def raw(count):
            value = payload.read(count)
            if len(value) != count:
                raise ValueError("Truncated compact artifact")
            return value

        def floats(size):
            value = torch.from_numpy(np.frombuffer(raw(size * 4), dtype="<f4").copy())
            if not bool(torch.isfinite(value).all()):
                raise ValueError("Nonfinite weights in compact artifact")
            return value

        def bank(module):
            rows, cols = module.weight.shape
            g = cols // job.native.GROUP
            code = torch.from_numpy(np.frombuffer(raw(rows*g*26), dtype=np.uint8).copy()).reshape(rows,g,26)
            scale = floats(rows*g).reshape(rows,g,1)
            if not bool(((code <= 242).all()) and ((scale > 0).all())):
                raise ValueError("Invalid base243 code or FP32 GSQ scale")
            packed[keys[id(module)]] = (code, scale)

        sequence = tuple(range(job.native.LAYERS))*3
        if raw(8) != job.native.MAGIC or struct.unpack("<42i", raw(42*4)) != sequence:
            raise ValueError("Compact dense14 route and owners differ")
        for module in (model.emb, model.emb_up):
            bank(module)
        for value in (model.rope_cos, model.rope_sin, model.norm_f_scale):
            value.copy_(floats(value.numel()).reshape_as(value))
        for layer in model.layers:
            for value in (layer.a_scale, layer.a_shift, layer.m_scale, layer.m_shift, layer.gates):
                value.copy_(floats(value.numel()).reshape_as(value))
            a = layer.attn_mod
            for module in (a.q_proj, a.o_proj, a.k_proj, a.v_proj):
                bank(module)
        for layer in model.layers:
            m = layer.mlp[0]
            for module in (m.gate_proj, m.up_proj, m.down_proj):
                bank(module)
        if payload.read(1) or len(packed) != 100:
            raise ValueError("Exact payload end and physical banks required")

    before, after, scales = sha256(), sha256(), sha256()
    counts = {role: dict(elements=0, code_changes=0, scale_changes=0, negative=0, zero=0, positive=0)
              for role in ("body", "shared_embedding", "shared_embedding_projection")}
    for module in (*body, model.emb, model.emb_up):
        key = keys[id(module)]
        stored, scale = packed.pop(key)
        codes = job.native.codec.unpack_trits(stored, 130)
        if bool(codes[..., -2:].ne(0).any()):
            raise ValueError("Unused trits must be canonical zero")
        codes = codes[..., :128].contiguous().to(torch.int8)
        original = ternary_g(module.weight, job.native.GROUP, cfg).reshape_as(codes)
        original_codes = original.sign().to(torch.int8)
        original_scale = original.abs().amax(dim=-1,keepdim=True).clamp_min(1e-8)
        for digest, tensor in ((before, original_codes), (after,codes), (scales,scale)):
            digest.update(key.encode("ascii"))
            digest.update(memoryview(tensor.numpy()).cast("B"))
        if module is model.emb:
            role = "shared_embedding"
        elif module is model.emb_up:
            role = "shared_embedding_projection"
        else:
            role = "body"
        row = counts[role]
        row["elements"] += codes.numel()
        row["code_changes"] += int(codes.ne(original_codes).sum())
        row["scale_changes"] += int(scale.ne(original_scale).sum())
        for label, trit in (("negative",-1),("zero",0),("positive",1)):
            row[label] += int(codes.eq(trit).sum())
        decoded = (codes * scale).reshape_as(module.weight)
        if isinstance(module, TLinear):
            module._wq = decoded
            module.weight = torch.nn.Parameter(torch.empty(0), requires_grad=False)
        else:
            module.weight = torch.nn.Parameter(decoded, requires_grad=False)
    diffs = dict(codes_sha256=after.hexdigest().upper(), scales_sha256=scales.hexdigest().upper(), counts=counts,
                 initial_codes_sha256=before.hexdigest().upper(), control_codes_sha256=control["initial_codes"]["sha256"],
                 cpu_initial_codes_exact=before.hexdigest().upper()==control["initial_codes"]["sha256"])
    if diffs["codes_sha256"] == control["final_codes"]["sha256"]:
        raise ValueError("The recovered artifact does not contain a new deterministic code assignment")
    return model, diffs


@torch.inference_mode()
def long_reference(model, requests):
    refs = {}
    with sdpa_kernel(SDPBackend.MATH):
        for name in ("english", "korean"):
            prompt = torch.tensor([requests[name]], dtype=torch.long)
            cache = None
            for chunk in prompt.split(job.native.PREFILL, dim=1):
                logits, cache = model(chunk, past_kv=cache, use_cache=True, logits_last_only=True)
            generated = []
            for i in range(job.GEN):
                if not bool(torch.isfinite(logits).all()):
                    raise ValueError("Nonfinite restored CPU reference")
                winner = logits.argmax(-1)
                generated.append(int(winner))
                if i+1 < job.GEN:
                    logits, cache = model(winner, past_kv=cache, use_cache=True, logits_last_only=True)
            refs[name] = dict(ids=generated)
    return refs


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CPU-only evidence recovery is required")
    job.gate(220)
    torch.set_num_threads(4)
    profile, raw = inspect_transaction()
    artifact_sha = job.BASE.SHA(job.DEPLOY)
    model, recovered = restore(profile)
    print("GSQ_PACKED_BANK_RECOVERY", recovered, flush=True)
    references = long_reference(model, profile["requests"])
    del model
    with np.load(job.OUT / "short_logits.npz", allow_pickle=False) as arrays:
        for key in ("short_0", "short_1"):
            rows = arrays[key]
            if rows.shape != (job.GEN, 32768) or not np.isfinite(rows).all():
                raise ValueError("Saved short GPU reference is incomplete")
            references[key] = dict(ids=rows.argmax(axis=1).tolist())
    job.write(job.OUT / "cpu_reference_recovery.json", dict(artifact_sha256=artifact_sha,
        gpu_raw_sha256=job.BASE.SHA(GPU_LOG), gpu_original_exit=1, logged_updates=raw,
        recovered=recovered, reference=references, gpu_training_replays=0,
        short_reference="original_gpu_fp32_scores", long_reference="restored_cpu_fp32_fp16_kv"))
    return job.compare_deployment(profile, references, artifact_sha256=artifact_sha,
                                  result_path=job.OUT / "deployment_recovered.json")


if __name__ == "__main__":
    raise SystemExit(main())
