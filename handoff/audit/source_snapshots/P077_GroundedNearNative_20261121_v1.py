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
from scripts import run_p077_grounded_context_training as training


wide = training.wide
trial = training.trial
port = wide.choices.native
bounded = port.bounded
base = bounded.base
TAG = "p077_grounded_small_native_kv_cpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)
ARMS = {"int8_1024": (1024, False), "int8_2048": (2048, False), "k4v2_2048": (2048, True)}
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


def prepare():
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
    return plan,(tok,special,rows,fixtures["2048_near_diverse"],text)


def source_for(context, compressed, eot, eos):
    source = text_test.render_engine((trial.ROOT/base.CPP).read_bytes(),context,eot,eos)
    if context==2048 and not compressed:
        source = port.replace_once(source,b"cache(capacity, 1920, 4, 2)",b"cache(capacity)")
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


def cache_bytes(length, compressed):
    packed = length//32*32
    old = min(packed,1920) if compressed else 0
    code = packed*128*2 - old*128*10//8
    fp16 = (packed//32)*128 + packed*2 + old*2 + min(length,31)*128*2
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


def run(plan, stop_by):
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="" or OUT.exists():
        raise ValueError("requires a new CPU-only comparison")
    verified,(tok,special,rows,quality,text) = prepare()
    if verified!=plan:
        raise ValueError("native inputs changed")
    cpus = sorted(set(wide.choices.CPU_CORES)&os.sched_getaffinity(0))
    if not cpus:
        raise ValueError("no CPU cores selected for the native comparison")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    stop = (special["<|im_end|>"],tok.token_to_id("<eos>"))
    if stop[1] is None:
        raise ValueError("the native renderer needs a document end token")
    sources = {name:source_for(length,low,*stop) for name,(length,low) in ARMS.items()}
    mapping = check_mapping(sources["k4v2_2048"],OUT)
    binaries = {}
    for arm,source in sources.items():
        folder = OUT/arm
        folder.mkdir()
        with patch.object(bounded,"OUT",folder):
            binaries[arm] = bounded.build(source,caps=(64,))[64]
    wrapper,codec = text_codec(OUT)
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
        for fd,blob in zip((vocab,merges),codec,strict=True):
            bounded.text.store(fd,blob)
            fcntl.fcntl(fd,base.prior.DEPLOY.F_ADD_SEALS,base.prior.DEPLOY.SEALS)
        assets = {1024:(r4,model4),2048:(r5,model5)}
        calibration = []
        with torch.inference_mode():
            for row in rows[:6]:
                ids = row["prompts"][0]
                left = packed(torch.tensor([ids]),logits_last_only=True).reshape(-1).float().numpy()
                _,_,right = token_request(binaries["int8_1024"][0],r4,ids,1,trace=True)
                if right is None or right.shape!=left.shape or not np.isfinite(right).all():
                    raise ValueError("native first prediction lacks the expected finite vocabulary")
                relative = float(np.linalg.norm(left-right)/max(np.linalg.norm(left),1e-9))
                calibration.append(dict(length=len(ids),relative_l2=relative,matching_greedy=bool(left.argmax()==right.argmax())))
        del packed
        trial.publish(OUT/"identity.json",dict(preflight=plan,model4=model4,model5=model5,heads=mapping,calibration=calibration,cpus=cpus))
        print(json.dumps(dict(heads=mapping,calibration=calibration,model_bytes=model5["artifact_bytes"])),flush=True)

        def ensure_open():
            if (OUT/"STOP").exists() or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds()<180:
                raise TimeoutError("native comparison stopped before the deadline")

        def quality_job(i):
            result = dict(root=rows[i]["root"],language=rows[i]["language"],gold=rows[i]["gold"],arms={})
            order = ("int8_2048","k4v2_2048")
            for arm in (order if i%2==0 else order[::-1]):
                ensure_open()
                made = []
                for ids,gold in zip(quality[2*i:2*i+2],rows[i]["gold"],strict=True):
                    raw,time,_ = token_request(binaries[arm][0],r5,ids,GEN)
                    if raw["kv_bytes"]!=cache_bytes(2048,ARMS[arm][1]):
                        raise ValueError("numeric context capacity differs")
                    made.append(dict(decoded(tok,raw,gold,stop),seconds=time))
                result["arms"][arm]=made
            return result

        def text_job(i):
            result = dict(root=text["2048"][i]["root"],side=text["2048"][i]["side"],arms={})
            for arm in (list(ARMS) if i%2==0 else list(ARMS)[::-1]):
                ensure_open()
                length,low = ARMS[arm]
                fd,model = assets[length]
                row = text[str(length)][i]
                spec = dict(encoding=dict(ids=row["ids"]),native=dict(model_bytes=model["artifact_bytes"],
                            kv_bytes=cache_bytes(len(row["ids"])+GEN-1,low)))
                path = OUT/f"text_{i}_{arm}.json"
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
                    trial.publish(OUT/f"{prefix}_{i}.json",row)
            with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
                tasks = [pool.submit(lane,cpu,range(k,entries,len(cpus))) for k,cpu in enumerate(cpus)]
                for task in tasks:
                    task.result()
            return [trial.read_json(OUT/f"{prefix}_{i}.json") for i in range(entries)]

        full = works(text_job,len(text["2048"]),"request")
        print(json.dumps(dict(phase="text_complete",requests=len(full)*len(ARMS))),flush=True)
        quality_rows = works(quality_job,len(rows),"quality")
    trial.publish(OUT/"report.json",dict(plan=plan,full=full,quality=quality_rows))
    print(json.dumps(dict(phase="quality_complete",pairs=len(quality_rows))),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return
    if (args.receipt is None or trial.read_json(args.receipt)!=plan or args.stop_by is None
            or args.stop_by.tzinfo is None or args.stop_by>trial.CUTOFF
            or (args.stop_by-datetime.now(args.stop_by.tzinfo)).total_seconds()<600):
        parser.error("requires the sealed native inputs and a sufficient authorized window")
    run(plan,args.stop_by)


if __name__=="__main__":
    main()
