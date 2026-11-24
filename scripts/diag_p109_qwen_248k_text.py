"""Measure full text requests for the trained 248K R2 G4 witness."""

from contextlib import ExitStack
from datetime import datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
from statistics import median
import struct
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_g270_text as engine
from scripts import diag_p109_qwen_248k_warm_ce as learned
from scripts import p109_qwen_248k_text_exec as text
from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer


ROOT, io = engine.ROOT, engine.io
TAG = "p109_qwen_248k_same_pid_text_v1_20261119"
OUT = learned.OUT.with_name(TAG)
WRAPPER = ROOT / "scripts/p109_qwen_248k_text_exec.cpp"
TOKENIZER = io.OUT / "qwen.qbpe"
G270_RENDER = engine.render


def render():
    models = []
    for source in G270_RENDER():
        for before, after in (
            (b"constexpr int D = 768, E = 256, F = 2048, V = 262144;",
             b"constexpr int D = 768, E = 256, F = 2048, V = 248320, ActiveV = 248066;"),
            (b"constexpr int Layers = 20, Mlps = 6, Visits = 20, Slots = 10, Limit = 1024;",
             b"constexpr int Layers = 16, Mlps = 7, Visits = 28, Slots = 14, Limit = 1024;"),
            (b'"TLMG2701"', b'"TLMG2481"'),
            (b"logits(trace ? V : 0)", b"logits(trace ? ActiveV : 0)"),
            (b"require(token < V,", b"require(token < ActiveV,"),
            (b"for (int token = 0; token < V; ++token)", b"for (int token = 0; token < ActiveV; ++token)"),
            (b"logits_fd < 0 && ids[i] == 1", b"logits_fd < 0 && ids[i] == 248044"),
        ):
            source = engine.replace(source, before, after)
        models.append(source)
    return models


def serialize(model, fd):
    cfg = model.cfg
    assert (cfg.dim,cfg.ffn_dim,cfg.emb_rank,cfg.vocab_size,cfg.n_q_heads,cfg.n_kv_heads,cfg.head_dim,
            cfg.max_seq_len,cfg.norm_eps) == (768,2048,256,learned.VOCAB,12,3,64,1024,1e-5)
    assert cfg.attn_kind=="softmax_cla" and cfg.train_repeat==2. and cfg.infer_repeat==1.
    assert model._anneal.item()==1. and not (cfg.repeat_kv_reuse or cfg.repeat_embed_reinject or cfg.reuse_attn_on_dup)
    table = model.packed_embedding
    assert table.packed_codes.shape==(learned.VOCAB,1,52) and table.group_scales.shape==(learned.VOCAB,1)
    assert int(table.packed_codes.max()) <= 242
    route = list(model.visit_schedule())
    assert route==list(range(14))+list(range(2,16))
    mlps = [*model.pre_mlps,*model.mid_mlps,*model.coda_mlps]
    assert len(mlps)==7 and model.owner==[n-n%2 for n in range(16)]
    aliases=[mlps.index(layer.mlp[0]) for layer in model.layers]
    stored=set()
    digest=sha256()
    with os.fdopen(os.dup(fd),"wb") as stream:
        def append(raw):
            stream.write(raw)
            digest.update(raw)

        def save(tensor,dtype=torch.float32):
            assert tensor.device.type=="cpu" and tensor.dtype==dtype and tensor.is_contiguous()
            append(memoryview(tensor.detach().numpy()).cast("B"))

        def matrix(layer,n,k):
            assert id(layer) not in stored and (layer.out_f,layer.in_f,layer.group)==(n,k,128)
            assert layer.packed_codes.shape==(n,k//128,26) and layer.group_scales.shape==(n,k//128)
            stored.add(id(layer))
            save(layer.packed_codes,torch.uint8)
            save(layer.group_scales)

        append(b"TLMG2481")
        append(struct.pack("<60i",*route,*model.owner,*aliases))
        save(table.packed_codes,torch.uint8)
        save(table.group_scales)
        for value in (model.emb_up.weight, model.rope_cos, model.rope_sin, model.norm_f_scale):
            save(value)
        for index,layer in enumerate(model.layers):
            assert not (layer.has_lrm or layer.has_lora or layer.has_film or layer.use_mode_ln)
            a=layer.attn_mod
            assert a.qk_gain_logit is None and a.owns_kv==(model.owner[index]==index)
            for value in (layer.a_scale,layer.a_shift,layer.m_scale,layer.m_shift,layer.gates):
                save(value)
            matrix(a.q_proj,768,768)
            matrix(a.o_proj,768,768)
            if a.owns_kv:
                matrix(a.k_proj,192,768)
                matrix(a.v_proj,192,768)
        for mlp in mlps:
            matrix(mlp.gate_proj,2048,768)
            matrix(mlp.up_proj,2048,768)
            matrix(mlp.down_proj,768,2048)
    assert len(stored)==69 and 0<os.fstat(fd).st_size<30_000_000
    engine.seal(fd)
    return dict(bytes=os.fstat(fd).st_size,sha256=digest.hexdigest().upper(),physical_matrices=len(stored),
                route=route,owners=model.owner,mlps=aliases,assigned=learned.ASSIGNED)


def oracle(model, ids):
    with sdpa_kernel(SDPBackend.MATH):
        seen,choices=[],[]
        x=torch.tensor([ids])
        cache=None
        for _ in range(4):
            result,cache=model(x,past_kv=cache,use_cache=True,logits_last_only=True)
            assert len(cache)==14 and all(k.dtype==torch.float32 for k,v in cache.values())
            scores=result[0,0,:learned.ASSIGNED].contiguous()
            seen.append(scores.clone())
            choice=int(scores.argmax())
            choices.append(choice)
            x=torch.tensor([[choice]])
    return torch.stack(seen).numpy(),choices


@torch.inference_mode()
def run(expected_updates=88):
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==""
    cutoff=learned.parent.CUTOFF
    assert datetime.now(cutoff.tzinfo)+timedelta(seconds=500)<cutoff
    training=io.load(learned.OUT/"report.json")
    payload_sha=io.digest(learned.EXPORT)
    assert training["source_preserved"] and len(training["history"])==expected_updates
    assert payload_sha==training["packed_sha256"]
    assert io.digest(TOKENIZER)==io.load(io.OUT/"profile.json")["compact_sha256"]
    files=[Path(__file__),Path(text.__file__),Path(engine.__file__),engine.BODY,engine.SCALAR,engine.LOOKUP,
           engine.EXTENSION,WRAPPER,TOKENIZER,io.LONG,learned.PROFILE,learned.OUT/"report.json",
           Path(engine.prefill.__file__),ROOT/"scripts/p109_g4_grouped_int8_cache.hpp"]
    pins={str(p.relative_to(ROOT)):io.digest(p) for p in files}
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    io.write(OUT/"profile.json",dict(tag=TAG,pins=pins,train_packed_sha256=payload_sha,
        vocab=learned.VOCAB,assigned=learned.ASSIGNED,train_updates=expected_updates,fp32_logit_gate=0.001))
    numbers,control,runs={}, {}, []
    with ExitStack() as stack:
        def descriptor(label):
            fd=engine.prefill.base.memfile(label)
            stack.callback(os.close,fd)
            return fd

        model_fd, tok_fd = descriptor("qwen248_g4"),descriptor("qwen248_tok")
        engine.text.store(tok_fd,TOKENIZER.read_bytes())
        engine.seal(tok_fd)
        payload=torch.load(learned.EXPORT,map_location="cpu",weights_only=True)
        assert payload["provenance"]["profile_sha256"]==training["profile_sha256"]
        model=learned.load_payload(payload,device="cpu",tile_rows=4096)
        model.cfg.kv_dtype="fp32"
        artifact=serialize(model,model_fd)
        del payload
        with patch.object(engine,"OUT",OUT), patch.object(engine,"render",render), patch.object(engine,"WRAPPER",WRAPPER):
            baseline,approx,binary=engine.compile_binaries()
        bad=subprocess.run([str(approx),str(model_fd),"-1"],input=struct.pack("<3I",1,1,learned.ASSIGNED),
            pass_fds=(model_fd,),timeout=8,capture_output=True)
        assert bad.returncode!=0 and b"token outside vocabulary" in bad.stderr
        prompts=io.load(io.LONG)["runs"]["split_model"][0]["outputs"]
        with CompactQwenTokenizer(TOKENIZER) as tokenizer:
            for lang,size in (("english",128),("korean",512)):
                ids=tokenizer.encode(prompts[lang]["decoded"]).ids[:size]
                assert len(ids)==size and all(0<=i<learned.ASSIGNED for i in ids)
                truth,choices=oracle(model,ids)
                with patch.object(engine,"VOCAB",learned.ASSIGNED):
                    full,l=engine.native(baseline,model_fd,ids,4,True)
                    narrow,r=engine.native(approx,model_fd,ids,4,True)
                assert np.isfinite(l).all() and np.isfinite(r).all()
                numbers[lang]=dict(context=size,fp32=engine.same_history(truth,choices,full,l),
                    int8=engine.same_history(truth,choices,narrow,r),ids=choices)
                print("P109_248K_NATIVE_NUMERIC",lang,numbers[lang],flush=True)
            del model
            for lang in ("english","korean"):
                sequence=tokenizer.encode((prompts[lang]["decoded"]+"\n")*3).ids
                for n in range(1017,1000,-1):
                    ids=sequence[:n]
                    document=tokenizer.decode(ids,skip_special_tokens=False)
                    if len(ids)==n and tokenizer.encode(document).ids==ids:
                        break
                else:
                    raise ValueError("native 1K input cannot be reproduced")
                old,_=engine.native(baseline,model_fd,ids,text.GEN)
                answer=tokenizer.decode(old["ids"],skip_special_tokens=True)
                control[lang]=dict(tokens=len(ids),ids=old["ids"],text=answer,native_seconds=sum(old["seconds"]),
                    input_sha256=sha256(document.encode("utf-8")).hexdigest().upper(),
                    native_peak=max(v for stage in ("loaded","prefilled","complete") for k,v in old[stage].items() if k in ("rss","vm_hwm")))
                for index in (1,2):
                    with patch.object(engine,"OUT",OUT),patch.object(engine,"text",text):
                        row=engine.full_request(binary,(model_fd,tok_fd),document.encode("utf-8"),lang,index)
                    assert row.pop("source_ids")==ids and row["model_bytes"]==artifact["bytes"]
                    row["same_output"]=row["ids"]==old["ids"] and row["text"]==answer
                    runs.append(row)
                    print("P109_248K_FULL_TEXT",lang,index,row["peak"],row["same_output"],row["seconds"],flush=True)
    assert not torch.cuda.is_initialized() and io.digest(learned.EXPORT)==payload_sha
    assert all(io.digest(ROOT/p)==h for p,h in pins.items())
    numeric_ok=all(x["fp32"]["choices_equal"] and x["fp32"]["max_abs"]<=0.001 for x in numbers.values())
    peak=max(r["peak"] for r in runs)
    outputs_equal=all(r["same_output"] for r in runs)
    io.write(OUT/"report.json",dict(numeric=numbers,runs=runs,full_controls=control,peak=peak,under_40mb=peak<=40_000_000,
        native_fp32_reproduced=numeric_ok,outputs_equal=outputs_equal,invalid_id_rejected=True,artifact=artifact,
        medians={lang:median(r["seconds"] for r in runs if r["case"]==lang) for lang in control},
        profile_sha256=io.digest(OUT/"profile.json"),checkpoint_writes=0))
    return 0 if numeric_ok and peak<=40_000_000 and outputs_equal else 8


if __name__=="__main__":
    sys.exit(run())
