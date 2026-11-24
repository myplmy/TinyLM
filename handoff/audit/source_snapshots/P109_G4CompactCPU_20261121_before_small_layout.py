"""Compare the independent P083 R4 process against the admitted INT8 G4 reference."""

import ctypes
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from time import perf_counter

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_g4_int8_kv1024 as prior
from tinylm.data.prepare import load_tokenizer


TAG = "p109_g4_compact_cpu_r4_v1_20261119"
ROOT = prior.ORIGIN.ROOT
OUT = prior.OUT.with_name(TAG)
REFERENCE_PATH = prior.OUT / "report.json"
PROFILE_PATH = prior.OUT / "profile.json"
CPP = "scripts/p109_g4_compact_cpu.cpp"
C = "scripts/p014e_direct_cpu.c"
ME = "scripts/diag_p109_g4_compact_cpu.py"
METADATA_BYTES = 8 + (28 + 16 + 16) * 4
GEN = 8
SHORT = 41
MAX_LOGIT_DELTA = 0.001
SHA = prior.embedding.SHA
READ = prior.embedding.READ
WRITE = prior.embedding.WRITE


def memfile(name):
    create = ctypes.CDLL(None, use_errno=True).memfd_create
    create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    create.restype = ctypes.c_int
    fd = create(name.encode("ascii"), prior.DEPLOY.MFD_CLOEXEC | prior.DEPLOY.MFD_ALLOW_SEALING)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "memfd_create")
    return fd


def pins():
    contract = prior.contract()
    actual = READ(REFERENCE_PATH)
    assert actual["profile_sha256"] == SHA(PROFILE_PATH)
    assert all(SHA(ROOT / file) == digest for file, digest in contract["sources"].items())
    assert actual["native_body"]["runtime_closed"] and not actual["cuda_initialized"]
    return dict(
        tag=TAG,
        previous_report=SHA(REFERENCE_PATH),
        previous_profile=SHA(PROFILE_PATH),
        candidate=contract,
        sources={name: SHA(ROOT / name) for name in (C, CPP, ME)},
        short_rng=284630,
        short=SHORT,
        generation=GEN,
        max_logit_difference=MAX_LOGIT_DELTA,
    )


def build():
    scratch = Path(tempfile.mkdtemp(prefix="p109_g4_compact_", dir="/tmp"))
    obj, binary = scratch / "p014e_lookup.o", scratch / "g4"
    commands = [
        ["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
         "-c", C, "-o", str(obj)],
        ["/usr/bin/g++", "-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c",
         "-ffp-contract=off", "-Wall", "-Wextra", "-Werror", CPP, str(obj), "-o", str(binary)],
    ]
    for args in commands:
        subprocess.run(args, cwd=ROOT, check=True, timeout=90)
    compiler = subprocess.check_output(["/usr/bin/g++", "--version"], text=True).splitlines()[0]
    WRITE(OUT / "compiler.json", {
        "compiler": compiler, "commands": commands, "binary": str(binary),
        "binary_bytes": binary.stat().st_size, "binary_sha256": SHA(binary),
    })
    return binary


def model_blob(model, fd, expected_bytes):
    cfg = model.cfg
    assert (cfg.dim, cfg.ffn_dim, cfg.emb_rank, cfg.vocab_size, cfg.n_q_heads,
            cfg.n_kv_heads, cfg.head_dim, cfg.max_seq_len, cfg.norm_eps) == (
               768, 2048, 256, 32768, 12, 3, 64, 1024, 1e-5)
    assert cfg.attn_kind == "softmax_cla" and not cfg.reuse_attn_on_dup
    assert not cfg.repeat_kv_reuse and not cfg.repeat_embed_reinject
    assert model._anneal.dtype == torch.float32 and model._anneal.item() == 1.0
    assert model.embedding_quantized() == "int8"
    assert model._emb_code.dtype == torch.int8 and tuple(model._emb_code.shape) == (32768, 256)
    assert model._emb_scale.numel() == 32768
    route = list(model.visit_schedule())
    assert route == list(range(14)) + list(range(2, 16))
    mlps = [*model.pre_mlps, *model.mid_mlps, *model.coda_mlps]
    assert len(mlps) == 7 and len({id(m) for m in mlps}) == 7
    mlp_indices = [mlps.index(layer.mlp[0]) for layer in model.layers]
    assert len(model.layers) == len(model.owner) == 16
    assert model.owner == [index - index % 2 for index in range(16)]
    hashes = sha256()
    projections = set()
    with os.fdopen(os.dup(fd), "wb") as binary:
        def put(raw):
            binary.write(raw)
            hashes.update(raw)

        def tensor(value, dtype=torch.float32):
            assert value.dtype == dtype and value.device.type == "cpu" and value.is_contiguous()
            put(memoryview(value.detach().numpy()).cast("B"))

        def matrix(layer, rows, columns):
            assert id(layer) not in projections
            projections.add(id(layer))
            assert (layer.out_f, layer.in_f, layer.group) == (rows, columns, 128)
            assert tuple(layer.packed_codes.shape) == (rows, columns // 128, 26)
            assert tuple(layer.group_scales.shape) == (rows, columns // 128)
            tensor(layer.packed_codes, torch.uint8)
            tensor(layer.group_scales)

        put(b"TLMG4R4" + bytes(1))
        put(struct.pack("<60i", *route, *model.owner, *mlp_indices))
        tensor(model._emb_code, torch.int8)
        tensor(model._emb_scale)
        tensor(model.emb_up.weight)
        tensor(model.rope_cos)
        tensor(model.rope_sin)
        tensor(model.norm_f_scale)
        for index, layer in enumerate(model.layers):
            assert not (layer.has_lrm or layer.has_lora or layer.has_film or layer.use_mode_ln)
            attn = layer.attn_mod
            assert attn.qk_gain_logit is None and attn.owns_kv == (model.owner[index] == index)
            for value in (layer.a_scale, layer.a_shift, layer.m_scale, layer.m_shift, layer.gates):
                tensor(value)
            matrix(attn.q_proj, 768, 768)
            matrix(attn.o_proj, 768, 768)
            if attn.owns_kv:
                matrix(attn.k_proj, 192, 768)
                matrix(attn.v_proj, 192, 768)
        for mlp in mlps:
            matrix(mlp.gate_proj, 2048, 768)
            matrix(mlp.up_proj, 2048, 768)
            matrix(mlp.down_proj, 768, 2048)
    assert len(projections) == 69
    size = os.fstat(fd).st_size
    assert size == expected_bytes - model._anneal.element_size() + METADATA_BYTES
    fcntl.fcntl(fd, prior.DEPLOY.F_ADD_SEALS, prior.DEPLOY.SEALS)
    assert fcntl.fcntl(fd, prior.DEPLOY.F_GET_SEALS) == prior.DEPLOY.SEALS
    return dict(artifact_bytes=size, artifact_sha256=hashes.hexdigest().upper(), physical_matrices=len(projections),
                fixed_anneal=1.0, metadata_bytes=METADATA_BYTES,
                visit_schedule=route, cla_owner=model.owner, mlp_group_indices=mlp_indices)


def short_oracle(model, ids, tok):
    scores = []
    model.cfg.kv_dtype = "fp16"

    def capture(_model, _args, output):
        logits, cache = output
        assert logits.shape == (1, 1, 32768) and len(cache) == 14
        assert all(t.dtype == torch.float16 for pair in cache.values() for t in pair)
        scores.append(logits[0, 0].detach().clone())

    with prior.DEPLOY.native_unpack(model), sdpa_kernel(SDPBackend.MATH), model.register_forward_hook(capture):
        output = prior.DEPLOY.request(
            model, prior.DEPLOY.PreparedPrompt(ids, tok), "", max_new=GEN, stop=False, audit=False
        )
    return torch.stack(scores), output["ids"]


def run_native(binary, model_fd, ids, *, scores=False):
    log_fd = memfile("g4_reference_logits") if scores else -1
    fds = (model_fd, log_fd) if scores else (model_fd,)
    try:
        start = perf_counter()
        cmd = [str(binary), str(model_fd), str(log_fd)]
        request = struct.pack(f"<{len(ids) + 2}I", len(ids), GEN, *ids)
        result = subprocess.run(cmd, input=request, capture_output=True, pass_fds=fds, timeout=300, cwd=ROOT)
        if result.returncode:
            print("P109_COMPACT_NATIVE_ERROR", result.returncode, result.stderr.decode("utf-8", "replace"),
                  flush=True)
            raise RuntimeError("native child failed")
        row = json.loads(result.stdout)
        row["process_seconds"] = perf_counter() - start
        assert len(row["ids"]) == len(row["seconds"]) == GEN
        assert row["kv_bytes"] == (len(ids) + GEN - 1) * 14 * 2 * 3 * 64 * 2
        row["peak_rss_observed_bytes"] = max(
            row[stage][key]
            for stage in ("before", "loaded", "prefilled", "complete")
            for key in ("vm_hwm", "rss")
        )
        row["within_40000000"] = row["peak_rss_observed_bytes"] <= 40_000_000
        row["within_40_mib"] = row["peak_rss_observed_bytes"] <= 40 * 2**20
        array = None
        if scores:
            with os.fdopen(os.dup(log_fd), "rb") as source:
                source.seek(0)
                array = np.frombuffer(source.read(), dtype="<f4").copy().reshape(GEN, 32768)
        return row, array
    finally:
        if scores:
            os.close(log_fd)


@torch.inference_mode()
def run():
    cpu = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile = pins()
    OUT.mkdir(exist_ok=False)
    WRITE(OUT / "profile.json", dict(**profile, cpu=cpu))
    binary = build()
    tokenizer = load_tokenizer("ko-en", 32768)
    model = prior.load_candidate(profile["candidate"])
    fd = memfile("p109_g4_compact_model")
    try:
        source = model_blob(model, fd, profile["candidate"]["model_tensor_bytes"])
        WRITE(OUT / "blob.json", source)
        short = torch.randint(35, 32768, (SHORT,), generator=torch.Generator().manual_seed(profile["short_rng"])).tolist()
        expected, ids = short_oracle(model, short, tokenizer)
        del model
        result, scores = run_native(binary, fd, short, scores=True)
        maximum = float(np.max(np.abs(scores - expected.numpy())))
        result.update(reference_ids=ids, short_input_ids=short, max_abs_logit_difference=maximum,
                      same_ids=result["ids"] == ids,
                      numerical_gate_passed=result["ids"] == ids and maximum <= MAX_LOGIT_DELTA)
        WRITE(OUT / "short.json", result)
        print("P109_COMPACT_41", result["same_ids"], maximum, result["peak_rss_observed_bytes"], flush=True)
        if not result["numerical_gate_passed"]:
            return 8

        prior_profile = READ(PROFILE_PATH)
        prior_report = READ(REFERENCE_PATH)
        cases = {}
        for name in ("synthetic", "english", "korean"):
            tokens = prior_profile["cases"][name]["ids"]
            case, _ = run_native(binary, fd, tokens)
            case["reference_ids"] = prior_report["requests"][name]["fp16"]["ids"]
            case["same_ids"] = case["ids"] == case["reference_ids"]
            assert case["model_bytes"] == source["artifact_bytes"]
            WRITE(OUT / f"{name}.json", case)
            cases[name] = case
            print("P109_COMPACT_1024", name, case["same_ids"], case["peak_rss_observed_bytes"],
                  case["seconds"][0], sum(case["seconds"][1:]), flush=True)
    finally:
        os.close(fd)
    assert pins() == profile and not torch.cuda.is_initialized()
    WRITE(OUT / "report.json", dict(
        short=result, cases=cases, artifact=source, profile_sha256=SHA(OUT / "profile.json"),
        binary_sha256=SHA(binary), read_only_model_fd_released=True, checkpoint_writes=0, cuda_initialized=False,
        tokenizer_in_native_child=False,
    ))
    return 0 if all(case["same_ids"] for case in cases.values()) else 8


if __name__ == "__main__":
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    if datetime.now(prior.ORIGIN.CUTOFF.tzinfo) + timedelta(seconds=1200) >= prior.ORIGIN.CUTOFF:
        raise RuntimeError("insufficient time in the authorized window")
    sys.exit(run())
