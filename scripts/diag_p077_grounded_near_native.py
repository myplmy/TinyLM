"""Compare the small grounded G4 through real native KV and text requests."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p077_lowbit_full_text as text_test
from scripts import diag_p077_lowbit_native as native_test
from scripts import p077_rope_tile as tiled_rope
from scripts import run_p077_grounded_context_training as training


wide = training.wide
trial = training.trial
port = wide.choices.native
bounded = port.bounded
base = bounded.base
TAG = "p077_grounded_small_native_kv_cpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)
ARMS = {"int8_1024": (1024, 0), "int8_2048": (2048, 0), "k4v2_2048": (2048, 2)}
V3_TAG = "p077_grounded_small_native_k4v3_cpu_v1_20261121"
V3_OUT = wide.OUT.with_name(V3_TAG)
V3_ARMS = {"k4v3_2048": (2048, 3)}
ROPE_TAG = "p077_grounded_small_native_rope_tile_cpu_v1_20261121"
ROPE_OUT = wide.OUT.with_name(ROPE_TAG)
ROPE_ARMS = {"table_rope_2048": (2048, 3), "tile_rope_2048": (2048, 3)}
GEN = trial.GENERATION


def canonical_text(tok, row, side, limit):
    head, table, query = wide.parts(tok,row,side)
    width = limit-GEN+1
    filler = training.controls.diverse_filler(tok,row["language"],width-len(head)-len(table)-len(query))
    for trim in range(32):
        text = tok.decode(head+filler[trim:]+table+query,skip_special_tokens=False)
        if "\ufffd" in text:
            continue
        ids = tok.encode(text,add_special_tokens=False).ids
        if width-32 <= len(ids) <= width and tok.decode(ids,skip_special_tokens=False)==text:
            return dict(text=text,ids=ids,gold=row["gold"][side],language=row["language"],root=row["root"],side=side)
    raise ValueError("could not seal a whole UTF-8 document")


def prepare(v3=False, rope=False):
    export = training.EXPORT_OUT
    report = trial.read_json(export/"report.json")
    final = trial.read_json(export/"supervisor.json")
    file = export/"near_only.pt"
    if (report["tag"]!=training.EXPORT_TAG or final["returncode"] or final["stop_reason"]
            or report["evaluated"] or trial.file_sha(file)!=report["checkpoint_sha256"]):
        raise ValueError("requires one saved and completed near-only endpoint")
    _, (tok,special,rows,fixtures) = training.controls.prepare()
    archive = trial.read_json(training.OUT/"near_only.json")["raw"]["2048_near_diverse"]["rows"]
    positive = {r["root"] for r in archive if r["both"]}
    roots = {lang:sorted((r for r in rows if r["language"]==lang and r["root"] in positive),key=lambda r:r["root"])[:2]
             for lang in ("ko","en")}
    if any(len(v)!=2 for v in roots.values()):
        raise ValueError("requires two fixed text cases per language")
    chosen = [r for v in roots.values() for r in v]
    text = {str(length):[canonical_text(tok,r,side,length) for r in chosen for side in range(2)] for length in (1024,2048)}
    source = [Path(__file__), Path(port.__file__), Path(bounded.__file__), Path(base.__file__),Path(bounded.token.__file__),
              trial.ROOT/base.CPP, trial.ROOT/bounded.text.WRAPPER, trial.ROOT/bounded.text.SCRIPT,
              trial.ROOT/"scripts/p109_g4_grouped_int8_cache.hpp", trial.ROOT/"scripts/p077_g4_grouped_attention.hpp",
              Path(text_test.__file__)]
    plan = dict(tag=TAG,checkpoint_sha256=report["checkpoint_sha256"],state_sha256=report["state_sha256"],
                archived_state_sha256=report["expected_state_sha256"],sources=native_test.seal(source),
                quality_pairs=len(rows),text_pairs=len(chosen),arms=list(ARMS),
                text_sha256=training.data.authored.digest(text),quality_sha256=training.data.authored.digest(fixtures["2048_near_diverse"]))
    if v3 or rope:
        reference = (V3_OUT if rope else OUT)/"report.json"
        old = trial.read_json(reference)
        keys = ("checkpoint_sha256","state_sha256","text_sha256","quality_sha256")
        if len(old["quality"])!=len(rows) or any(old["plan"][key]!=plan[key] for key in keys):
            raise ValueError("the new precision arm needs the completed exact same reference inputs")
        tag,arms = (ROPE_TAG,ROPE_ARMS) if rope else (V3_TAG,V3_ARMS)
        plan.update(tag=tag,arms=list(arms),reference_sha256=trial.file_sha(reference))
        if rope:
            plan["sources"].update(native_test.seal((Path(tiled_rope.__file__),tiled_rope.HEADER)))
    return plan,(tok,special,rows,fixtures["2048_near_diverse"],text)


def source_for(context, value_bits, eot, eos):
    source = text_test.render_engine((trial.ROOT/base.CPP).read_bytes(),context,eot,eos)
    if context==2048 and value_bits!=2:
        cache = f"cache(capacity, 1920, 4, {value_bits})".encode() if value_bits else b"cache(capacity)"
        source = port.replace_once(source,b"cache(capacity, 1920, 4, 2)",cache)
    source = port.replace_once(source,b"constexpr int D = 768, E = 256, F = 2048, V = 32768;",
                               b"constexpr int D = 256, E = 128, F = 768, V = 32768;")
    return port.replace_once(source,b"constexpr int Heads = 12, Head = 64, Kv = 3 * Head;",
                             b"constexpr int Heads = 4, Head = 64, Kv = 2 * Head;")


def check_mapping(source, directory):
    core = directory/"small_grouped.cpp"
    core.write_bytes(source)
    fixture = directory/"heads.cpp"
    fixture.write_text('''#define main compact_cli
#include "small_grouped.cpp"
#undef main
int main() {
    GroupedInt8Cache cache(32);
    GroupedBlockAttention work(32);
    std::array<float,2*D> q{}, out{};
    std::array<float,2*Kv> k{}, v{};
    for (int row = 0; row < 2; ++row) {
        std::fill_n(v.data()+row*Kv, Head, 1.F);
        std::fill_n(v.data()+row*Kv+Head, Head, 2.F);
    }
    work.compute_prefill(cache, 0, 0, q.data(), k.data(), v.data(), 1, 2, out.data());
    for (int r = 0; r < 2; ++r)
        for (int h = 0; h < Heads; ++h)
            for (int i = 0; i < Head; ++i)
                if (out[r*D+h*Head+i] != float(1+h/2)) return 1;
    return 0;
}
''',encoding="utf-8")
    binary = directory/"heads"
    native_test.compile_probe(fixture,binary,("-DP109_PREFILL_TOKENS=64",))
    subprocess.run([binary],check=True,timeout=30)
    return dict(head_outputs=[1,1,2,2],queries=2,source_sha256=trial.file_sha(fixture))


def cache_bytes(length, value_bits):
    packed = length//32*32
    old = min(packed,1920) if value_bits else 0
    code = packed*128*2 - old*128*(12-value_bits)//8
    minima = old*2 if value_bits==2 else 0
    fp16 = (packed//32)*128 + packed*2 + minima + min(length,31)*128*2
    return 14*(code+2*fp16)


def text_codec(directory):
    book = trial.read_json(trial.DATA/"report.json")
    model = trial.read_json(trial.on_disk(book["tokenizer"]))
    names = tuple(token["content"] for token in model["added_tokens"])
    parts = bounded.token.wire(model,special_tokens=names)
    wrapper = text_test.wrapper(directory/"text_request.py",2041,GEN)
    source = port.replace_once(wrapper.read_bytes(),b'for name in ("<pad>", "<bos>", "<eos>")])',
                               f"for name in {names!r}])".encode("ascii"))
    source = port.replace_once(source,b'assert [tok.token_to_id(s) for s in ("<pad>", "<bos>", "<eos>")] == [0, 1, 2]',
                               f"assert [tok.token_to_id(s) for s in {names!r}] == list(range({len(names)}))".encode("ascii"))
    wrapper.write_bytes(source)
    return wrapper,parts


def token_request(binary, model, prompt, max_new, *, trace=False):
    payload = struct.pack(f"<{len(prompt)+2}I",len(prompt),max_new,*prompt)
    with ExitStack() as stack:
        command = [binary,str(model),"-1"]
        descriptors = [model]
        if trace:
            fd = base.memfile("p077-small-first-logits")
            stack.callback(os.close,fd)
            descriptors.append(fd)
            command[-1] = str(fd)
        start = perf_counter()
        result = subprocess.run(command,pass_fds=descriptors,input=payload,capture_output=True,timeout=120,check=True)
        elapsed = perf_counter()-start
        row = json.loads(result.stdout)
        scores = np.frombuffer(os.pread(fd,os.fstat(fd).st_size,0),dtype="<f4") if trace else None
    return row,elapsed,scores


def decoded(tok, row, gold, stop):
    ids = row["ids"]
    ended = ids[-1] in stop
    answer = tok.decode(ids[:-1] if ended else ids,skip_special_tokens=False).strip()
    return dict(ids=ids,answer=answer,eot=ids[-1]==stop[0],exact=ids[-1]==stop[0] and answer==gold)


def run(plan, stop_by, *, v3=False, rope=False):
    directory, arms = (V3_OUT,V3_ARMS) if v3 else (OUT,ARMS)
    if rope:
        directory, arms = ROPE_OUT, ROPE_ARMS
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="" or directory.exists():
        raise ValueError("requires a new CPU-only comparison")
    verified,(tok,special,rows,quality,text) = prepare(v3,rope)
    if verified!=plan:
        raise ValueError("native inputs changed")
    cpus = sorted(set(wide.choices.CPU_CORES)&os.sched_getaffinity(0))
    if not cpus:
        raise ValueError("no CPU cores selected for the native comparison")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    directory.mkdir()
    stop = (special["<|im_end|>"],tok.token_to_id("<eos>"))
    if stop[1] is None:
        raise ValueError("the native renderer needs a document end token")
    sources = {name:source_for(length,value_bits,*stop) for name,(length,value_bits) in arms.items()}
    if rope:
        sources["tile_rope_2048"] = tiled_rope.render(sources["tile_rope_2048"])
    mapping = check_mapping(sources[next(arm for arm in arms if arms[arm][1])],directory)
    binaries = {}
    for arm,source in sources.items():
        folder = directory/arm
        folder.mkdir()
        with patch.object(bounded,"OUT",folder):
            binaries[arm] = bounded.build(source,caps=(64,))[64]
    wrapper,codec = text_codec(directory)
    with ExitStack() as stack:
        r4,r5,vocab,merges = [base.memfile(f"p077-small-{name}") for name in ("r4","r5","vocab","merges")]
        for fd in (r4,r5,vocab,merges):
            stack.callback(os.close,fd)
        export = torch.load(training.EXPORT_OUT/"near_only.pt",weights_only=True,map_location="cpu")
        if trial.state_sha(export["model"])!=plan["state_sha256"]:
            raise ValueError("exported state changed")
        original = wide.TiedMLPTransformer(replace(wide.TMTConfig(**export["config"]),max_seq_len=1024))
        original.load_state_dict(export["model"])
        original.eval()
        original.freeze_quant()
        pack = base.prior.embedding.PACK
        packed = pack.load_payload(pack.export_payload(original,provenance={"tag":TAG},head_rows=128))
        packed.quantize_embedding("int8")
        packed.eval()
        del original,export
        size = base.prior.model_storage(packed)["unique_storage_bytes"]
        model4 = base.model_blob(packed,r4,size,small=True)
        model5 = port.extend_positions(r4,r5,packed)
        if (v3 or rope) and model5!=trial.read_json((V3_OUT if rope else OUT)/"identity.json")["model5"]:
            raise ValueError("new precision arm packed a different model")
        for fd,blob in zip((vocab,merges),codec,strict=True):
            bounded.text.store(fd,blob)
            fcntl.fcntl(fd,base.prior.DEPLOY.F_ADD_SEALS,base.prior.DEPLOY.SEALS)
        assets = {1024:(r4,model4),2048:(r5,model5)}
        bindings = {arm:assets[length] for arm,(length,_) in arms.items()}
        calibration = []
        compact_model = None
        if rope:
            r6 = base.memfile("p077-small-r6")
            stack.callback(os.close,r6)
            compact_model = tiled_rope.pack(r5,r6,packed.cfg,directory)
            bindings["tile_rope_2048"] = (r6,compact_model)
            for length in (63,64,65,127,128,129):
                ids = quality[0][:length]
                a,_,one = token_request(binaries["table_rope_2048"][0],r5,ids,2,trace=True)
                b,_,other = token_request(binaries["tile_rope_2048"][0],r6,ids,2,trace=True)
                count = min(len(a["ids"]),len(b["ids"])) * 32768
                if not count or not np.isfinite(other).all():
                    raise ValueError("the native boundary trace did not return finite vocabulary scores")
                calibration.append(dict(length=length,old_ids=a["ids"],new_ids=b["ids"],
                                        compared_values=count,max_abs=float(np.abs(one[:count]-other[:count]).max())))
        else:
            calibration_arm = next(iter(arms))
            calibration_model = bindings[calibration_arm][0]
            with torch.inference_mode():
                for row in rows[:6]:
                    ids = row["prompts"][0]
                    left = packed(torch.tensor([ids]),logits_last_only=True).reshape(-1).float().numpy()
                    _,_,right = token_request(binaries[calibration_arm][0],calibration_model,ids,1,trace=True)
                    if right is None or right.shape!=left.shape or not np.isfinite(right).all():
                        raise ValueError("native first prediction lacks the expected finite vocabulary")
                    relative = float(np.linalg.norm(left-right)/max(np.linalg.norm(left),1e-9))
                    calibration.append(dict(length=len(ids),relative_l2=relative,matching_greedy=bool(left.argmax()==right.argmax())))
        del packed
        trial.publish(directory/"identity.json",dict(preflight=plan,model4=model4,model5=model5,compact_model=compact_model,
                      heads=mapping,calibration=calibration,cpus=cpus))
        print(json.dumps(dict(heads=mapping,calibration=calibration,model_bytes=model5["artifact_bytes"])),flush=True)

        def ensure_open():
            if (directory/"STOP").exists() or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds()<180:
                raise TimeoutError("native comparison stopped before the deadline")

        def quality_job(i):
            result = dict(root=rows[i]["root"],language=rows[i]["language"],gold=rows[i]["gold"],arms={})
            order = ("tile_rope_2048",) if rope else tuple(arm for arm in arms if arms[arm][0]==2048)
            for arm in (order if i%2==0 else order[::-1]):
                ensure_open()
                made = []
                for ids,gold in zip(quality[2*i:2*i+2],rows[i]["gold"],strict=True):
                    raw,time,_ = token_request(binaries[arm][0],bindings[arm][0],ids,GEN)
                    if raw["kv_bytes"]!=cache_bytes(2048,arms[arm][1]):
                        raise ValueError("numeric context capacity differs")
                    made.append(dict(decoded(tok,raw,gold,stop),seconds=time))
                result["arms"][arm]=made
            return result

        def text_job(i):
            result = dict(root=text["2048"][i]["root"],side=text["2048"][i]["side"],arms={})
            for arm in (list(arms) if i%2==0 else list(arms)[::-1]):
                ensure_open()
                length,value_bits = arms[arm]
                fd,model = bindings[arm]
                row = text[str(length)][i]
                spec = dict(encoding=dict(ids=row["ids"]),native=dict(model_bytes=model["artifact_bytes"],
                            kv_bytes=cache_bytes(len(row["ids"])+GEN-1,value_bits)))
                path = directory/f"text_{i}_{arm}.json"
                stats = port.request(binaries[arm][1],(fd,vocab,merges),row["text"].encode("utf-8"),path,spec,wrapper=wrapper)
                raw = trial.read_json(path)["native"]
                result["arms"][arm] = dict(decoded(tok,raw,row["gold"],stop),length=len(row["ids"]),total=stats["seconds"],
                    kv=stats["kv_bytes"],first=raw["seconds"][0],rss=raw["prefilled"]["rss"],peak=stats["peak_rss"])
            return result

        def works(worker, entries, prefix):
            def lane(cpu, indices):
                os.sched_setaffinity(0,{cpu})
                for i in indices:
                    row = worker(i)
                    trial.publish(directory/f"{prefix}_{i}.json",row)
            with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
                tasks = [pool.submit(lane,cpu,range(k,entries,len(cpus))) for k,cpu in enumerate(cpus)]
                for task in tasks:
                    task.result()
            return [trial.read_json(directory/f"{prefix}_{i}.json") for i in range(entries)]

        full = works(text_job,len(text["2048"]),"request")
        print(json.dumps(dict(phase="text_complete",requests=len(full)*len(arms))),flush=True)
        quality_rows = works(quality_job,len(rows),"quality")
    trial.publish(directory/"report.json",dict(plan=plan,full=full,quality=quality_rows))
    print(json.dumps(dict(phase="quality_complete",pairs=len(quality_rows))),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument("--v3",action="store_true")
    variants.add_argument("--rope",action="store_true")
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare(args.v3,args.rope)
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return
    if (args.receipt is None or trial.read_json(args.receipt)!=plan or args.stop_by is None
            or args.stop_by.tzinfo is None or args.stop_by>trial.CUTOFF
            or (args.stop_by-datetime.now(args.stop_by.tzinfo)).total_seconds()<600):
        parser.error("requires the sealed native inputs and a sufficient authorized window")
    run(plan,args.stop_by,v3=args.v3,rope=args.rope)


if __name__=="__main__":
    main()
