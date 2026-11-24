"""Compare a mapped BPE input encoder with the current 32K ChatML encoder."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from random import Random
import runpy
import subprocess
import sys
import sysconfig
from time import perf_counter


TAG = "p077_compact_chat32_input_cpu_v1_20261121"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"test_result/evidence"/TAG
PACKER = ROOT/"scripts/p109_compact_qwen_tokenizer.py"
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")


def pack_chat32(model,path):
    from tokenizers import pre_tokenizers
    from scripts import p109_compact_qwen_tokenizer as wire
    from scripts import diag_p109_g4_tokenizer_budget as codec

    special = {row["content"]:row["id"] for row in model["added_tokens"]}
    codec.wire(model,special_tokens=tuple(special))
    vocabulary = model["model"]["vocab"]
    alphabet = {key:vocabulary[key] for key in pre_tokenizers.ByteLevel.alphabet()}
    if (len(alphabet)!=256 or set(alphabet)&set(special) or any(vocabulary[k]!=v for k,v in special.items())
            or set(vocabulary.values())!=set(range(len(vocabulary)))):
        raise ValueError("unexpected ChatML ByteLevel vocabulary layout")
    scaffold = dict(model,model=dict(model["model"],vocab=alphabet|special,merges=[]))
    minimal = json.dumps(scaffold,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    pieces = bytearray()
    offsets = bytearray(wire.OFFSET.pack(0))
    for token,_ in sorted(vocabulary.items(),key=lambda item:item[1]):
        pieces.extend(token.encode("utf-8"))
        offsets.extend(wire.OFFSET.pack(len(pieces)))
    pairs = [(vocabulary[a]<<32|vocabulary[b],rank,vocabulary[a+b])
             for rank,(a,b) in enumerate(model["model"]["merges"])]
    pairs.sort()
    if len({pair for pair,_,_ in pairs})!=len(pairs):
        raise ValueError("a pair has multiple BPE ranks")
    with path.open("xb") as file:
        file.write(wire.HEADER.pack(wire.MAGIC,len(vocabulary),len(vocabulary),len(pairs),len(minimal),len(pieces)))
        file.write(offsets)
        for row in pairs:
            file.write(wire.MERGE.pack(*row))
        file.write(minimal)
        file.write(pieces)


def verify(original,candidate,real):
    fragments = (" 토큰","한\u1100\u1161","#127","é","e\u0301","😺","good!"," \r\n","\t","a  b","가","  ","b’c")
    rng = Random(302901)
    synthetic = ["".join(rng.choices(fragments,k=(i%15)+1)) for i in range(512)]
    markers = [candidate.id_to_token(i) for i in sorted(candidate.special)]
    synthetic.extend(f"{before}{marker}{after}" for marker in markers
                     for before,after in (("",""),("abc","끝"),(" \n","\t  ")))
    # Decode mixed byte groups first, then validate the exact UTF-8 input that exists.
    tokens = [[rng.randrange(candidate.size) for _ in range(i%8+1)] for i in range(1024)]
    synthetic.extend(original.decode_batch(tokens,skip_special_tokens=False))
    for i,text in enumerate(real+synthetic):
        expected = original.encode(text,add_special_tokens=False)
        actual = candidate.encode(text)
        if actual.ids!=expected.ids or actual.offsets!=expected.offsets or actual.word_ids!=expected.word_ids:
            raise ValueError(f"input encoder differs on fixture {i}: {text[:100]!r}")
        if candidate.decode(actual.ids)!=original.decode(expected.ids):
            raise ValueError(f"decoded text changed on fixture {i}")
    return len(real)+len(synthetic)


def worker(method,wrapper,pack_file,vocab,merges):
    sys.path.append(sysconfig.get_path("purelib"))
    runtime = runpy.run_path(wrapper)
    snapshot = runtime["snapshot"]
    data = sys.stdin.buffer.read().decode("utf-8")
    timeline = dict(startup=snapshot())
    started = perf_counter()
    with ExitStack() as stack:
        if method=="existing":
            tokenizer,_,_ = runtime["tokenizer"](vocab,merges)
        elif method=="mapped":
            library = runpy.run_path(str(PACKER))
            tokenizer = stack.enter_context(library["CompactQwenTokenizer"](pack_file))
        else:
            raise ValueError("unknown input encoder")
        load_seconds = perf_counter()-started
        timeline["loaded"] = snapshot()
        started = perf_counter()
        enc = tokenizer.encode(data,add_special_tokens=False) if method=="existing" else tokenizer.encode(data)
        encode_seconds = perf_counter()-started
        timeline["complete"] = snapshot()
    print(json.dumps(dict(ids=enc.ids,offsets=enc.offsets,process=timeline,load_seconds=load_seconds,
                          encode_seconds=encode_seconds,max_rss=max(v for stage in timeline.values() for v in stage.values()))))


def run(deadline):
    from tokenizers import Tokenizer
    from scripts import diag_p077_grounded_near_native as near
    from scripts import p109_compact_qwen_tokenizer as wire

    if (os.environ.get("CUDA_VISIBLE_DEVICES")!="" or not deadline.tzinfo or deadline>AUTHORIZATION_END
            or OUT.exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<130):
        raise ValueError("requires a fresh CPU comparison in the authorized window")
    provenance,(tok,_,_,_,inputs) = near.prepare(rope=True)
    receipt = near.trial.read_json(near.ROPE_OUT/"identity.json")
    source = near.trial.on_disk(near.trial.read_json(near.trial.DATA/"report.json")["tokenizer"])
    raw = source.read_bytes()
    official = Tokenizer.from_buffer(raw)
    if provenance!=receipt["preflight"]:
        raise ValueError("the existing text requests changed")
    rows = inputs["2048"]
    messages = [r["text"] for r in rows]
    OUT.mkdir()
    path = OUT/"chat32_input.bin"
    pack_chat32(json.loads(raw),path)
    with wire.CompactQwenTokenizer(path) as candidate:
        verified = verify(official,candidate,messages)
    print(json.dumps(dict(equivalent=verified,bytes=path.stat().st_size)),flush=True)
    wrapper,parts = near.text_codec(OUT)
    cpus = set(receipt["cpus"])&os.sched_getaffinity(0)
    if not cpus:
        raise ValueError("the prior CPU lanes are unavailable")
    cpu = min(cpus)
    os.sched_setaffinity(0,{cpu})
    observations = []
    with ExitStack() as stack:
        descriptors = []
        for i,blob in enumerate(parts):
            fd = near.base.memfile(f"p077-encoder-{i}")
            stack.callback(os.close,fd)
            near.bounded.text.store(fd,blob)
            descriptors.append(fd)
        for i,row in enumerate(rows):
            if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<50:
                raise TimeoutError("encoder measurement stopped at its deadline")
            arms = ("existing","mapped") if i%2==0 else ("mapped","existing")
            data = row["text"].encode("utf-8")
            expected = tok.encode(row["text"])
            request = dict(index=i,arms={},order=arms)
            for arm in arms:
                child = subprocess.run([sys.executable,"-I","-S","-B","-X","utf8",str(Path(__file__).resolve()),
                                        "worker",arm,str(wrapper),str(path),*map(str,descriptors)],
                                       input=data,capture_output=True,pass_fds=descriptors,timeout=25,check=True)
                item = json.loads(child.stdout)
                if item.pop("ids")!=row["ids"] or item.pop("offsets")!=[list(v) for v in expected.offsets]:
                    raise ValueError("actual isolated text input changed")
                request["arms"][arm] = item
            observations.append(request)
    result = dict(tag=TAG,source_sha256=near.trial.file_sha(Path(__file__)),packer_sha256=near.trial.file_sha(PACKER),
                  tokenizer_sha256=sha256(raw).hexdigest(),packed_sha256=near.trial.file_sha(path),
                  bytes=path.stat().st_size,old_wire_bytes=sum(map(len,parts)),matched=verified,cpu=cpu,rows=observations)
    near.trial.publish(OUT/"report.json",result)
    print(json.dumps(dict(requests=len(observations))),flush=True)


def main():
    if sys.argv[1:2]==["worker"] and len(sys.argv)==7:
        worker(*sys.argv[2:5],*map(int,sys.argv[5:]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by",required=True,type=datetime.fromisoformat)
    run(parser.parse_args().stop_by)
    return 0


if __name__=="__main__":
    sys.exit(main())
