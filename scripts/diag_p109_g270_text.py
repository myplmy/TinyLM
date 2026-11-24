"""Combine the existing 20-layer G270 payload and compact 262K tokenizer."""

from contextlib import ExitStack
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
import struct
import subprocess
import sys
import tempfile
from time import perf_counter

import numpy as np
import torch

from scripts import diag_p109_compact_qwen_tokenizer as io
from scripts import diag_p109_csr_gemma_tokenizer as tok
from scripts import diag_p109_g4_bounded_prefill as prefill
from scripts import p014e_packed_g128 as packed
from scripts import p109_g270_text_exec as text


ROOT = io.ROOT
TAG = "p109_g270_same_pid_text_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
VOCAB, E, SLOTS, KV = 262144, 256, 10, 192
ROW_BYTES = 52
BODY = ROOT / "scripts/p109_g4_compact_cpu.cpp"
WRAPPER = ROOT / "scripts/p109_g270_text_exec.cpp"
LOOKUP = ROOT / "scripts/p109_g4_avx2_lookup.cpp"
EXTENSION = ROOT / "scripts/p109_g270_table.inc"
SCALAR = ROOT / "scripts/p014e_direct_cpu.c"
PAYLOAD = ROOT / "runs/deploy/p014e_g270_large_vocab_v2_20261027/ternary5_existing_twn.pt"
PAYLOAD_SHA = "302CC5FA303585F4B0AB33DE58ED636E340DE1C37DF311EED0F8944B964CF185"
GOLD = PAYLOAD.parent / "oracle/cpu/ternary5_existing_twn"
CASES = ("ko128", "en128", "ko512", "en512")
QUANTIZED = (
    tok.sparse.previous.OUT / "gemma.qbpe", tok.sparse.OUT / "sparse.index", tok.OUT / "merges.csr",
)
RENDERED_FP32_CACHE = b"""
class FloatG270Cache {
public:
    explicit FloatG270Cache(int capacity)
        : capacity_(capacity), key_(Slots * capacity * Kv), value_(Slots * capacity * Kv) {}
    size_t bytes() const { return sizeof(float) * (key_.capacity() + value_.capacity()); }
    void restore(int slot, int past, float* k, float* v) const {
        std::copy_n(key_.data() + slot * capacity_ * Kv, past * Kv, k);
        std::copy_n(value_.data() + slot * capacity_ * Kv, past * Kv, v);
    }
    void append(int slot, int past, int count, const float* k, const float* v) {
        const auto start = (slot * capacity_ + past) * Kv;
        std::copy_n(k + past * Kv, count * Kv, key_.data() + start);
        std::copy_n(v + past * Kv, count * Kv, value_.data() + start);
    }
private:
    int capacity_;
    std::vector<float> key_, value_;
};
"""


def replace(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after, 1)


def render():
    tiled = replace(BODY.read_bytes(), prefill.prior.avx.tile.ORIGINAL, prefill.prior.avx.tile.CHANGED)
    source = prefill.render(prefill.prior.render(tiled))
    edits = (
        (b"constexpr int D = 768, E = 256, F = 2048, V = 32768;", b"constexpr int D = 768, E = 256, F = 2048, V = 262144;"),
        (b"constexpr int Layers = 16, Mlps = 7, Visits = 28, Slots = 14, Limit = 1024;",
         b"constexpr int Layers = 20, Mlps = 6, Visits = 20, Slots = 10, Limit = 1024;"),
        (b"namespace {", b'extern "C" bool p109_g270_expand_row(const uint8_t*, const float*, int, float*);\n\nnamespace {'),
        (b'"TLMG4R4"', b'"TLMG2701"'),
        (b"codes = in.take<int8_t>(V * E);", b"codes = in.take<uint8_t>(V * 52);"),
        (b"const int8_t* codes;", b"const uint8_t* codes;"),
        (b"            for (int j = 0; j < E; ++j) hidden[j] = static_cast<float>(model.codes[token*E+j]) * model.scales[token];",
         b'            require(p109_g270_expand_row(model.codes, model.scales, token, hidden.data()), "invalid embedding row");'),
        (b"        float best_score = -INFINITY;", b"        std::array<float, E> table_row{};\n        float best_score = -INFINITY;"),
        (b"        Memory prefilled{};", b"        Memory prefilled{};\n        uint32_t emitted = 0;"),
        (b"            if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);",
         b"            if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);\n"
         b"            ++emitted;\n            if (logits_fd < 0 && ids[i] == 1) break;"),
        (b'for (uint32_t i = 0; i < generate; ++i) printf("%s%u"',
         b'for (uint32_t i = 0; i < emitted; ++i) printf("%s%u"'),
        (b'for (uint32_t i = 0; i < generate; ++i) printf("%s%.9f"',
         b'for (uint32_t i = 0; i < emitted; ++i) printf("%s%.9f"'),
    )
    for before,after in edits:
        source = replace(source,before,after)
    left = source.index(b"            const auto* row = model.codes + token*E;")
    right = source.index(b"            require(std::isfinite(score)", left)
    source = source[:left] + (
        b'            require(p109_g270_expand_row(model.codes, model.scales, token, table_row.data()), "invalid head row");\n'
        b"            const float score = dot(hidden.data(), table_row.data(), E);\n"
    ) + source[right:]
    reference = replace(source,b'#include "p109_g4_grouped_int8_cache.hpp"',RENDERED_FP32_CACHE)
    reference = replace(reference,b"GroupedInt8Cache cache;",b"FloatG270Cache cache;")
    reference = replace(reference,b"void load_half(",b"[[maybe_unused]] void load_half(")
    reference = replace(reference,b"void store_half(",b"[[maybe_unused]] void store_half(")
    return reference,source


def compile_binaries():
    folder = Path(tempfile.mkdtemp(prefix="p109_g270_text_", dir="/tmp"))
    scalar, lookup, obj = (str(folder / n) for n in ("scalar.o", "lookup.o", "engine.o"))
    flags = ["-std=c++17","-O3","-mavx2","-mfma","-mf16c","-ffp-contract=off","-Wall","-Wextra","-Werror",
             "-I",str(ROOT/"scripts")]
    commands = []

    def call(argv, data=None):
        subprocess.run(argv,input=data,cwd=ROOT,timeout=80,check=True)
        commands.append(argv)

    call(["/usr/bin/gcc","-std=c11","-O3","-Wall","-Werror","-Dp014e_cpu_lookup=p014e_scalar_lookup",
          "-c",str(SCALAR),"-o",scalar])
    call(["/usr/bin/g++",*flags,"-x","c++","-","-c","-o",lookup],LOOKUP.read_bytes()+b"\n"+EXTENSION.read_bytes())
    full,candidate = render()
    reference, approx, end_to_end = (folder/n for n in ("g270_fp32","g270_int8","g270_text"))
    call(["/usr/bin/g++", *flags, "-DP109_PREFILL_TOKENS=1024","-x","c++","-","-x","none", lookup,scalar,
          "-static","-o",str(reference)],full)
    call(["/usr/bin/g++", *flags, "-DP109_PREFILL_TOKENS=256","-x","c++","-","-x","none", lookup,scalar,
          "-static","-o",str(approx)],candidate)
    call(["/usr/bin/g++", *flags, "-DP109_PREFILL_TOKENS=256","-Dmain=run_compact_g4","-x","c++","-","-c","-o",obj],candidate)
    call(["/usr/bin/g++", *flags,str(WRAPPER),obj,lookup,scalar,"-static","-o",str(end_to_end)])
    binaries = {name:dict(path=str(path),sha256=io.digest(path))
                for name,path in (("fp32",reference),("int8",approx),("text",end_to_end))}
    assert all("INTERP" not in subprocess.check_output(["/usr/bin/readelf","-l",v["path"]],text=True)
               for v in binaries.values())
    io.write(OUT/"compiler.json",dict(commands=commands,binaries=binaries,
        source_sha256=[sha256(s).hexdigest().upper() for s in (full,candidate)]))
    return reference,approx,end_to_end


def seal(fd):
    fcntl.fcntl(fd,text.F_ADD_SEALS,text.REQUIRED_SEALS)
    assert fcntl.fcntl(fd,text.F_GET_SEALS) == text.REQUIRED_SEALS


def export(fd):
    payload = torch.load(PAYLOAD,map_location="cpu",weights_only=True)
    model = packed.load_payload(payload,device="cpu")
    cfg = model.cfg
    assert (cfg.dim,cfg.ffn_dim,cfg.emb_rank,cfg.vocab_size,cfg.n_q_heads,cfg.n_kv_heads,cfg.head_dim,
            cfg.max_seq_len,cfg.norm_eps) == (768,2048,E,VOCAB,12,3,64,1024,1e-5)
    assert cfg.attn_kind == "softmax_cla" and cfg.infer_repeat == 1. and cfg.train_repeat == 1.
    assert not cfg.repeat_embed_reinject and not cfg.repeat_kv_reuse and not cfg.reuse_attn_on_dup
    assert model._anneal.item() == 1.
    assert model.packed_embedding.packed_codes.shape == (VOCAB,1,ROW_BYTES)
    assert model.packed_embedding.group_scales.shape == (VOCAB,1)
    assert int(model.packed_embedding.packed_codes.max()) <= 242
    route = list(model.visit_schedule())
    mlps = [*model.pre_mlps,*model.mid_mlps,*model.coda_mlps]
    assert route == list(range(20)) and len(mlps)==6 and len(model.layers)==20
    assert model.owner == [n-n%2 for n in range(20)]
    aliases = [mlps.index(layer.mlp[0]) for layer in model.layers]
    rows = set()
    digest = sha256()
    with os.fdopen(os.dup(fd),"wb") as out:
        def write(raw):
            out.write(raw)
            digest.update(raw)

        def tensor(value,dtype=torch.float32):
            assert value.device.type == "cpu" and value.dtype == dtype and value.is_contiguous()
            write(memoryview(value.detach().numpy()).cast("B"))

        def matrix(layer,n,k):
            assert id(layer) not in rows and (layer.in_f,layer.out_f,layer.group)==(k,n,128)
            assert layer.packed_codes.shape==(n,k//128,26) and layer.group_scales.shape==(n,k//128)
            rows.add(id(layer))
            tensor(layer.packed_codes,torch.uint8)
            tensor(layer.group_scales)

        write(b"TLMG2701")
        write(struct.pack("<60i",*route,*model.owner,*aliases))
        tensor(model.packed_embedding.packed_codes,torch.uint8)
        tensor(model.packed_embedding.group_scales)
        for value in (model.emb_up.weight,model.rope_cos,model.rope_sin,model.norm_f_scale):
            tensor(value)
        for index,layer in enumerate(model.layers):
            assert not (layer.has_lora or layer.has_lrm or layer.has_film or layer.use_mode_ln)
            attn = layer.attn_mod
            assert attn.qk_gain_logit is None and attn.owns_kv == (model.owner[index] == index)
            for value in (layer.a_scale,layer.a_shift,layer.m_scale,layer.m_shift,layer.gates):
                tensor(value)
            matrix(attn.q_proj,768,768)
            matrix(attn.o_proj,768,768)
            if attn.owns_kv:
                matrix(attn.k_proj,KV,768)
                matrix(attn.v_proj,KV,768)
        for mlp in mlps:
            matrix(mlp.gate_proj,2048,768)
            matrix(mlp.up_proj,2048,768)
            matrix(mlp.down_proj,768,2048)
    assert len(rows)==78 and 0 < os.fstat(fd).st_size < 30_000_000
    seal(fd)
    return dict(bytes=os.fstat(fd).st_size,sha256=digest.hexdigest().upper(),matrices=len(rows),
                route=route,owners=model.owner,mlps=aliases)


def memory(result):
    phase = {"native": max(result["native"][name][k] for name in ("loaded","prefilled","complete","before")
                           for k in ("vm_hwm","rss"))}
    for name in ("encoding","decoding"):
        phase[name] = max(v for key in ("startup","loaded","complete") for v in result[name][key].values())
    return phase


def native(binary, model_fd, ids, steps, trace=False):
    with ExitStack() as stack:
        fd = -1
        if trace:
            fd = prefill.base.memfile("g270_scores")
            stack.callback(os.close, fd)
        proc = subprocess.run([str(binary),str(model_fd),str(fd)],
            input=struct.pack(f"<{len(ids)+2}I",len(ids),steps,*ids),pass_fds=(model_fd,fd) if trace else (model_fd,),
            timeout=95,capture_output=True)
        if proc.returncode:
            print(proc.stderr.decode("utf-8","replace"),file=sys.stderr,flush=True)
            proc.check_returncode()
        model = json.loads(proc.stdout)
        logits = None
        if trace:
            os.lseek(fd,0,os.SEEK_SET)
            with os.fdopen(os.dup(fd),"rb") as stream:
                logits = np.frombuffer(stream.read(),dtype="<f4").reshape(steps,VOCAB)
    return model,logits


def same_history(target,ids,model,values):
    maximum, checkpoints = 0., []
    for i,(expected,got) in enumerate(zip(ids,model["ids"],strict=True)):
        error = float(np.abs(target[i]-values[i]).max())
        maximum = max(maximum,error)
        checkpoints.append(error)
        if expected != got:
            break
    return dict(max_abs=maximum,errors=checkpoints,choices_equal=model["ids"]==ids)


def full_request(binary,assets,text_bytes,case,serial):
    with ExitStack() as stack:
        children = tuple(prefill.base.memfile(f"g270_text_{n}") for n in range(3))
        for fd in children:
            stack.callback(os.close,fd)
        fds = (*assets,*children)
        args = [sys.executable,"-I","-S","-B","-X","utf8",str(Path(text.__file__)),"encode",str(binary),*map(str,fds)]
        started = perf_counter()
        proc = subprocess.run(args,input=text_bytes,pass_fds=fds,timeout=100,capture_output=True)
        elapsed = perf_counter()-started
        if case == "image_guard":
            assert proc.returncode != 0 and b"token outside the G270 model vocabulary" in proc.stderr
            return dict(exit=proc.returncode,rejection="TOKEN_OUTSIDE_MODEL",native_recorded=os.fstat(children[2]).st_size>0)
        if proc.returncode:
            print(proc.stderr.decode("utf-8","replace"),file=sys.stderr,flush=True)
            proc.check_returncode()
        result = json.loads(proc.stdout)
    assert result["encoding"]["pid"] == result["native_pid"] == result["decoding"]["pid"]
    io.write(OUT/f"request_{case}_{serial}.json",result)
    phase = memory(result)
    return dict(case=case,seconds=elapsed,peak=max(phase.values()),phase=phase,ids=result["native"]["ids"],
        source_ids=result["encoding"]["ids"],text=result["decoding"]["text"],finish=result["decoding"]["finish"],
        model_bytes=result["native"]["model_bytes"],kv_bytes=result["native"]["kv_bytes"],
        step_seconds=result["native"]["seconds"])


@torch.inference_mode()
def main():
    cutoff = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(cutoff.tzinfo)+timedelta(seconds=440) < cutoff
    assert io.digest(PAYLOAD) == PAYLOAD_SHA
    tokenizer = io.load(tok.OUT/"profile.json")
    assert [io.digest(p) for p in QUANTIZED] == [
        tokenizer["pins"][str(QUANTIZED[0].relative_to(ROOT))], tokenizer["pins"][str(QUANTIZED[1].relative_to(ROOT))],
        tokenizer["table_sha256"],
    ]
    source_paths = [BODY,WRAPPER,LOOKUP,EXTENSION,SCALAR,Path(__file__),Path(text.__file__),
        Path(prefill.__file__),Path(prefill.prior.__file__),Path(packed.__file__),Path(tok.__file__),
        Path(tok.sparse.__file__),io.CODEC,
        ROOT/"scripts/p109_g4_grouped_int8_cache.hpp", *QUANTIZED, *[GOLD/f"{c}.pt" for c in CASES],io.LONG]
    sources = {str(p.relative_to(ROOT)):io.digest(p) for p in source_paths}
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    io.write(OUT/"profile.json",dict(tag=TAG,sources=sources,payload_sha256=PAYLOAD_SHA,
        expected_shapes=dict(vocab=VOCAB,layers=20,slots=SLOTS,mlps=6,context=1024),numeric_tolerance=0.001))
    reference,candidate,command = compile_binaries()
    numeric_results, runs, long_controls = {}, [], {}
    with ExitStack() as stack:
        def new_fd(name):
            fd = prefill.base.memfile(name)
            stack.callback(os.close,fd)
            return fd

        model_fd = new_fd("g270_model")
        artifact = export(model_fd)
        tok_fds = tuple(new_fd(f"g270_tok_{i}") for i in range(3))
        for f,path in zip(tok_fds,QUANTIZED,strict=True):
            text.store(f,path.read_bytes())
            seal(f)
        for name in CASES:
            base = torch.load(GOLD/f"{name}.pt",map_location="cpu",weights_only=True)
            ids = base["input"]["ids"]
            assert len(ids)==int(name[2:]) and all(0<=v<VOCAB for v in ids)
            answer = base["teacher_ids"]
            scores = torch.stack(base["logits"]).reshape(4,VOCAB).numpy()
            normal,left = native(reference,model_fd,ids,4,True)
            low,right = native(candidate,model_fd,ids,4,True)
            assert normal["model_bytes"]==low["model_bytes"]==artifact["bytes"]
            assert np.isfinite(left).all() and np.isfinite(right).all()
            numeric_results[name] = dict(fp32=same_history(scores,answer,normal,left),
                int8=same_history(scores,answer,low,right),reference_ids=answer)
            print("G270_NUMERIC",name,numeric_results[name],flush=True)
        guard = full_request(command,(model_fd,*tok_fds),b"<image_soft_token>","image_guard",0)
        assert not guard["native_recorded"]
        inputs = io.load(io.LONG)["runs"]["split_model"][0]["outputs"]
        with tok.CsrGemma(*QUANTIZED) as preparer:
            for lang in ("english","korean"):
                whole = preparer.encode((inputs[lang]["decoded"]+"\n")*3).ids
                for n in range(1017,1000,-1):
                    request_ids=whole[:n]
                    document=preparer.decode(request_ids,skip_special_tokens=False)
                    if preparer.encode(document).ids==request_ids and len(request_ids)==n:
                        break
                else:
                    raise ValueError("could not establish the frozen 1K text prefix")
                assert all(0<=v<VOCAB for v in request_ids)
                fp32,_=native(reference,model_fd,request_ids,text.GEN)
                long_controls[lang]=dict(ids=fp32["ids"],text=preparer.decode(fp32["ids"]),
                    input_tokens=len(request_ids),input_sha256=sha256(document.encode("utf-8")).hexdigest().upper(),
                    model_peak=max(v for stage in ("prefilled","complete") for k,v in fp32[stage].items() if k in ("rss","vm_hwm")),
                    model_seconds=sum(fp32["seconds"]))
                for serial in (1,2):
                    row=full_request(command,(model_fd,*tok_fds),document.encode("utf-8"),lang,serial)
                    assert row.pop("source_ids")==request_ids and row["model_bytes"]==artifact["bytes"]
                    row["same_output"]=(row["ids"]==fp32["ids"] and row["text"]==long_controls[lang]["text"])
                    runs.append(row)
                    print("G270_TEXT",lang,serial,row["peak"],row["same_output"],row["seconds"],flush=True)
    assert not torch.cuda.is_initialized()
    assert io.digest(PAYLOAD)==PAYLOAD_SHA and all(io.digest(ROOT/p)==h for p,h in sources.items())
    fp32_pass = all(v["fp32"]["choices_equal"] and v["fp32"]["max_abs"]<=0.001 for v in numeric_results.values())
    mem_ok = all(row["peak"]<=40_000_000 for row in runs)
    ids_ok = all(row["same_output"] for row in runs)
    io.write(OUT/"report.json",dict(artifact=artifact,numeric=numeric_results,native_fp32_port_passed=fp32_pass,
        runs=runs,long_controls=long_controls,peak=max(row["peak"] for row in runs),memory_passed=mem_ok,
        outputs_equal=ids_ok,image_guard=guard,checkpoint_writes=0,profile_sha256=io.digest(OUT/"profile.json"),
        median_seconds={l:median(r["seconds"] for r in runs if r["case"]==l) for l in ("english","korean")}))
    return 0 if fp32_pass and mem_ok and ids_ok else 8


if __name__ == "__main__":
    sys.exit(main())
