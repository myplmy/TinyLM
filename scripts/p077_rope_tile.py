"""Build and check a bounded RoPE table in the small native engine."""

import fcntl
from hashlib import sha256
import os
from pathlib import Path
import subprocess

import numpy as np
import torch

from scripts import diag_p077_lowbit_native as native_test
from scripts import p077_g4_blocked_runtime as native


HEADER = Path(__file__).with_suffix(".hpp")
LIMIT = 2048
PAIRS = 32


def render(source):
    changes = (
        (b'"TLMG4R5"',b'"TLMG4R6"'),
        (b"        cos = in.take<float>(Limit * Head / 2);\n        sin = in.take<float>(Limit * Head / 2);",
         b"        rope_frequencies = in.take<float>(Head / 2);"),
        (b"const float *scales, *embed_up, *cos, *sin, *norm_f;",
         b"const float *scales, *embed_up, *rope_frequencies, *norm_f;"),
        (b"constexpr int PrefillTokens = P109_PREFILL_TOKENS;",
         b'#include "p077_rope_tile.hpp"\n\nconstexpr int PrefillTokens = P109_PREFILL_TOKENS;'),
        (b"const int pos = (past + base + i) * (Head / 2);\n                rotate(k + i * Kv, model.cos + pos, model.sin + pos, Kv);",
         b"const int pos = (base + i) * (Head / 2);\n                rotate(k + i * Kv, rope_cos.data() + pos, rope_sin.data() + pos, Kv);"),
        (b"                const int pos = past + base + t;\n"
         b"                rotate(query_buffer + t*D, model.cos + pos*(Head/2), model.sin + pos*(Head/2), D);",
         b"                const int pos = (base + t) * (Head / 2);\n"
         b"                rotate(query_buffer + t*D, rope_cos.data() + pos, rope_sin.data() + pos, D);"),
        (b'require(past + count <= capacity && count > 0 && past >= 0, "context exceeds allocation");',
         b'require(past + count <= capacity && count > 0 && past >= 0, "context exceeds allocation");\n'
         b"        fill_rope_tile<Head / 2>(model.rope_frequencies, past, count, rope_cos.data(), rope_sin.data());"),
        (b"    std::vector<float> logits;",b"    std::vector<float> logits;\n"
         b"    std::array<float, PrefillTokens * Head / 2> rope_cos{}, rope_sin{};"),
    )
    for before,after in changes:
        source = native.replace_once(source,before,after)
    return source


def compare(directory, frequencies, expected):
    source = directory/"rope_probe.cpp"
    source.write_text('''#include <array>
#include <cstdio>
#include "p077_rope_tile.hpp"

int main() {
    constexpr int Pairs = 32, Limit = 2048;
    std::array<float,Pairs> frequencies{};
    if (std::fread(frequencies.data(), sizeof(float), Pairs, stdin) != Pairs) return 2;
    std::array<float,Limit*Pairs> cosine{}, sine{};
    int past = 0;
    while (past < Limit) {
        const int candidate = (past % 3 == 0 ? 64 : (past % 3 == 1 ? 1 : 31));
        const int count = candidate < Limit - past ? candidate : Limit - past;
        fill_rope_tile<Pairs>(frequencies.data(), past, count, cosine.data()+past*Pairs, sine.data()+past*Pairs);
        past += count;
    }
    if (std::fwrite(cosine.data(), sizeof(float), cosine.size(), stdout) != cosine.size()) return 3;
    if (std::fwrite(sine.data(), sizeof(float), sine.size(), stdout) != sine.size()) return 3;
    return 0;
}
''',encoding="utf-8")
    binary = directory/"rope_probe"
    native_test.compile_probe(source,binary)
    found = subprocess.check_output([binary],input=frequencies,timeout=30)
    original,computed = [np.frombuffer(raw,dtype="<f4") for raw in (expected,found)]
    if computed.shape!=original.shape or not np.isfinite(computed).all():
        raise ValueError("the bounded RoPE probe did not return all positions")
    return dict(values=len(computed),bit_equal=int(np.count_nonzero(original.view("<u4")==computed.view("<u4"))),
                max_abs=float(np.max(np.abs(original-computed))),computed_sha256=sha256(found).hexdigest())


def pack(r5, r6, cfg, directory):
    size = os.fstat(r5).st_size
    raw = os.pread(r5,size,0)
    base = native.bounded.base
    offset = base.METADATA_BYTES + cfg.vocab_size*(cfg.emb_rank+4) + cfg.dim*cfg.emb_rank*4
    end = offset + LIMIT*PAIRS*8
    if cfg.head_dim!=2*PAIRS or len(raw)!=size or not raw.startswith(b"TLMG4R5\x00") or end>=size:
        raise ValueError("expected the exact 2,048-token float32 table payload")
    inv = 1.0/(cfg.rope_theta**(torch.arange(0,cfg.head_dim,2).float()/cfg.head_dim))
    frequencies = inv.numpy().astype("<f4",copy=False).tobytes()
    numerics = compare(directory,frequencies,raw[offset:end])
    model = b"TLMG4R6\x00" + raw[8:offset] + frequencies + raw[end:]
    native.bounded.text.store(r6,model)
    deploy = base.prior.DEPLOY
    fcntl.fcntl(r6,deploy.F_ADD_SEALS,deploy.SEALS)
    return dict(artifact_bytes=len(model),artifact_sha256=sha256(model).hexdigest().upper(),
                total_positions=LIMIT,frequency_bytes=len(frequencies),reduced_bytes=size-len(model),numerics=numerics)
