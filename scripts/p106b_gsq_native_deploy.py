"""Exact deterministic GSQ bank export for the dense14 compact CPU engine."""

from hashlib import sha256
import os
from pathlib import Path
import struct
import subprocess
import tempfile

import torch

from scripts import diag_p109_g4_bounded_prefill as prefill
from scripts import p014e_packed_g128 as codec


ROOT = prefill.ROOT
MAGIC = b"TLMD14G1"
LAYERS, GROUP = 14, 128
MODEL_BYTES = 22_770_976
PREFILL = 256


def checked_replace(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Compact CPU source anchor changed: {before!r}")
    return source.replace(before, after, 1)


def render_engine():
    reuse = prefill.prior.avx.tile
    source = checked_replace((ROOT / prefill.base.CPP).read_bytes(), reuse.ORIGINAL, reuse.CHANGED)
    for before, after in prefill.ANCHORS:
        if before == b"value(capacity * Kv), cache(capacity) {}":
            before = (b"value(capacity * Kv), kept_key(Slots * capacity * Kv),\n"
                      b"          kept_value(Slots * capacity * Kv) {}")
            after = before[:-3] + b", logits(trace ? V : 0) {}"
        source = checked_replace(source, before, after)

    substitutions = (
        (b"Layers = 16, Mlps = 7, Visits = 28, Slots = 14", b"Layers = 14, Mlps = 14, Visits = 14, Slots = 14"),
        (b'"TLMG4R4"', b'"' + MAGIC + b'"'),
        (b"        codes = in.take<int8_t>(V * E);\n        scales = in.take<float>(V);\n"
         b"        embed_up = in.take<float>(D * E);",
         b"        table = matrix(in, V, E);\n"
         b"        const Matrix projection = matrix(in, D, E);\n"
         b"        for (int64_t row = 0; row < D; ++row) {\n"
         b"            require(p014e_cpu_lookup(projection.codes, projection.scales, &row, embed_up.data()+row*E,\n"
         b'                                     1, D, E, Group) == 0, "invalid embedding projection");\n'
         b"        }"),
        (b"    const int8_t* codes;\n    const float *scales, *embed_up, *cos, *sin, *norm_f;",
         b"    Matrix table{};\n    std::array<float, D*E> embed_up{};\n    const float *cos, *sin, *norm_f;"),
        (b"            for (int j = 0; j < E; ++j) hidden[j] = static_cast<float>(model.codes[token*E+j]) * model.scales[token];",
         b"            const int64_t row = token;\n"
         b"            require(p014e_cpu_lookup(model.table.codes, model.table.scales, &row, hidden.data(),\n"
         b'                                     1, V, E, Group) == 0, "invalid embedding row");'),
        (b"dot(hidden.data(), model.embed_up + j*E, E)", b"dot(hidden.data(), model.embed_up.data() + j*E, E)"),
        (b"            const auto* row = model.codes + token*E;\n"
         b"            const __m256 scale = _mm256_set1_ps(model.scales[token]);\n"
         b"            __m256 total = _mm256_setzero_ps();\n"
         b"            for (int j = 0; j < E; j += 8) {\n"
         b"                const __m128i bytes = _mm_loadl_epi64(reinterpret_cast<const __m128i*>(row+j));\n"
         b"                const __m256 w = _mm256_mul_ps(_mm256_cvtepi32_ps(_mm256_cvtepi8_epi32(bytes)), scale);\n"
         b"                total = _mm256_fmadd_ps(_mm256_loadu_ps(hidden.data()+j), w, total);\n"
         b"            }\n"
         b"            const float score = reduce(total);",
         b"            const int64_t row = token;\n"
         b"            require(p014e_cpu_lookup(model.table.codes, model.table.scales, &row, weight.data(),\n"
         b'                                     1, V, E, Group) == 0, "invalid head row");\n'
         b"            const float score = dot(hidden.data(), weight.data(), E);"),
    )
    for before, after in substitutions:
        source = checked_replace(source, before, after)
    return source


def build_engine():
    source = render_engine()
    folder = Path(tempfile.mkdtemp(prefix="p106b_gsq_dense14_", dir="/tmp"))
    scalar, avx, core = (str(folder / name) for name in ("scalar.o", "avx2.o", "engine.o"))
    numeric, full = (str(folder / name) for name in ("gsq_numeric", "gsq_text"))
    flags = ["/usr/bin/g++", "-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
             "-Wall", "-Wextra", "-Werror"]
    commands = (
        (["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Werror", "-Dp014e_cpu_lookup=p014e_scalar_lookup",
          "-c", prefill.base.C, "-o", scalar], None),
        ([*flags, "-c", prefill.prior.avx.LOOKUP, "-o", avx], None),
        ([*flags, f"-DP109_PREFILL_TOKENS={PREFILL}", "-Dmain=run_compact_g4", "-x", "c++", "-", "-c", "-o", core], source),
        ([*flags, "-x", "c++", "-", "-x", "none", core, scalar, avx, "-static", "-o", numeric],
         b"int run_compact_g4(int, char**);\nint main(int n, char** a) { return run_compact_g4(n, a); }\n"),
        ([*flags, prefill.text.WRAPPER, core, scalar, avx, "-static", "-o", full], None),
    )
    for command, stdin in commands:
        subprocess.run(command, input=stdin, cwd=ROOT, timeout=80, check=True)
    outputs = {}
    for name, file in (("numeric", numeric), ("text", full)):
        if "INTERP" in subprocess.check_output(["/usr/bin/readelf", "-l", file], text=True):
            raise ValueError("Deployment RSS probe requires the static CPU binary")
        outputs[name] = dict(path=file, sha256=prefill.base.SHA(Path(file)))
    return dict(binaries=outputs, source_sha256=sha256(source).hexdigest().upper(),
                commands=[command for command, _ in commands], prefill=PREFILL)


@torch.no_grad()
def save_banks(bridge, path, expected_codes):
    model = bridge.model
    cfg = model.cfg
    geometry = (cfg.n_layers, cfg.dim, cfg.ffn_dim, cfg.emb_rank, cfg.vocab_size,
                cfg.n_q_heads, cfg.n_kv_heads, cfg.head_dim, cfg.max_seq_len, cfg.norm_eps)
    sequential = tuple(range(LAYERS))
    if (geometry != (14, 768, 2048, 256, 32768, 12, 3, 64, 1024, 1e-5)
            or tuple(model.visit_schedule()) != sequential or tuple(model.owner) != sequential
            or cfg.tie_mlp or cfg.qk_gain_learnable or cfg.attn_kind != "softmax_cla"
            or bridge.arm != "gsq" or bridge.banks.training or model.training):
        raise ValueError("Deterministic dense14 R1 GSQ shape and inference path required")

    hashes = {name: sha256() for name in ("codes", "scales", "artifact")}
    packed = {}
    for key, bank in bridge.banks.items():
        code, scale = bank.code_scale()
        code = code.cpu().contiguous()
        scale = scale.squeeze(-1).cpu().contiguous()
        if bank.group != GROUP or scale.dtype != torch.float32 or not bool((scale > 0).all()):
            raise ValueError("Original positive FP32 group128 scales required")
        for label, tensor in (("codes", code), ("scales", scale)):
            hashes[label].update(key.encode("ascii"))
            hashes[label].update(memoryview(tensor.numpy()).cast("B"))
        chunks = []
        for start in range(0, bank.out_f, 128):
            reference = code[start:start + 128]
            value, group = codec.strict_pack(reference)
            if group != GROUP or not torch.equal(codec.unpack_trits(value, GROUP), reference):
                raise ValueError("Packed codes do not preserve the exact final GSQ trits")
            chunks.append(value)
        packed[key] = (torch.cat(chunks), scale)
    if len(packed) != 100 or hashes["codes"].hexdigest().upper() != expected_codes:
        raise ValueError("The trained physical bank count or deterministic code digest changed")

    keys = {id(layer): key for layer, key in bridge.bindings}
    with path.open("xb") as output:
        def put(raw):
            output.write(raw)
            hashes["artifact"].update(raw)

        def floats(value):
            if value.dtype != torch.float32 or not bool(torch.isfinite(value).all()):
                raise ValueError("The compact format requires finite FP32 non-ternary values")
            put(memoryview(value.detach().cpu().contiguous().numpy()).cast("B"))

        def bank(key):
            codes, scales = packed.pop(key)
            put(memoryview(codes.numpy()).cast("B"))
            floats(scales)

        put(MAGIC)
        put(struct.pack("<42i", *(sequential * 3)))
        bank(bridge.embedding)
        bank(bridge.embedding_up)
        for value in (model.rope_cos, model.rope_sin, model.norm_f_scale):
            floats(value)
        for layer in model.layers:
            attn = layer.attn_mod
            if not attn.owns_kv or layer.has_lrm or layer.has_lora or layer.has_film or layer.use_mode_ln:
                raise ValueError("Unshared K/V and plain dense layer required")
            for value in (layer.a_scale, layer.a_shift, layer.m_scale, layer.m_shift, layer.gates):
                floats(value)
            for linear in (attn.q_proj, attn.o_proj, attn.k_proj, attn.v_proj):
                bank(keys[id(linear)])
        for layer in model.layers:
            mlp = layer.mlp[0]
            for linear in (mlp.gate_proj, mlp.up_proj, mlp.down_proj):
                bank(keys[id(linear)])
        if packed or output.tell() != MODEL_BYTES:
            raise ValueError("The compact layout must consume all banks at the expected byte count")
        output.flush()
        os.fsync(output.fileno())
    return dict(bytes=MODEL_BYTES, banks=100, **{f"{k}_sha256": v.hexdigest().upper() for k,v in hashes.items()})
