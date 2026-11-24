"""Measure the mapped ChatML input in the full R6 CPU request."""

import argparse
from contextlib import ExitStack
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch

from scripts import diag_p077_compact_chat32_input as compact
from scripts import diag_p077_g4_wide_query_prefill as wide


TAG = "p077_compact_chat32_request_cpu_v1_20261121"
OUT = compact.OUT.with_name(TAG)
native,request,trial = wide.native,wide.request,wide.trial


def prepare():
    profile,(tok,special,texts,refs,model,output) = request.prepare()
    word_table = compact.OUT/"chat32_input.bin"
    report = compact.OUT/"report.json"
    proof = trial.read_json(report)
    timing = trial.read_json(wide.OUT/"report.json")
    measured = [row for row in timing["rows"] if row["arm"]=="online8"]
    tokenizer = trial.on_disk(trial.read_json(trial.DATA/"report.json")["tokenizer"])
    if (proof["source_sha256"]!=trial.file_sha(Path(compact.__file__))
            or proof["packer_sha256"]!=trial.file_sha(compact.PACKER)
            or proof["packed_sha256"]!=trial.file_sha(word_table)
            or proof["matched"]<1000 or len(proof["rows"])!=8
            or proof["tokenizer_sha256"]!=trial.file_sha(tokenizer)
            or len(measured)!=4 or not all(row["ids_equal"] and row["text_equal"] for row in measured)):
        raise ValueError("requires the verified input table and CPU engine")
    result = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),native=profile,
                  input_proof_sha256=trial.file_sha(report),input_sha256=proof["packed_sha256"],
                  cases=list(wide.CASES),engine_proof_sha256=trial.file_sha(wide.OUT/"report.json"))
    return result,(tok,special,texts,refs,model,output,word_table)


def render_input(path,base,table):
    original = (
        "    tok, version, module = tokenizer(vocab, merges)\n"
        "    loaded = snapshot()\n"
        '    ids = tok.encode(raw.decode("utf-8"), add_special_tokens=False).ids\n'
    )
    replacement = f'''    import runpy
    import sysconfig

    sys.path.append(sysconfig.get_path("purelib"))
    import tokenizers
    version, module = tokenizers.__version__, tokenizers.__file__
    library = runpy.run_path({str(compact.PACKER)!r})
    with library["CompactQwenTokenizer"]({str(table)!r}) as encoder:
        loaded = snapshot()
        ids = encoder.encode(raw.decode("utf-8")).ids
'''
    path.write_bytes(native.port.replace_once(base.read_bytes(),original.encode(),replacement.encode()))


def binary(source):
    receipt = trial.read_json(wide.OUT/"online8"/"compiler.json")
    entry = receipt["binaries"]["64"][1]
    found = Path(entry["path"])
    candidate = wide.render(source,"online8")
    if sha256(candidate).hexdigest().upper()!=receipt["source_sha256"]:
        raise ValueError("the measured width-8 engine changed")
    if found.is_file() and native.base.SHA(found)==entry["sha256"]:
        trial.publish(OUT/"compiler.json",receipt)
        return found
    with patch.object(native.bounded,"OUT",OUT):
        return native.bounded.build(candidate,caps=(64,))[64][1]


def run(plan,deadline):
    if (os.environ.get("CUDA_VISIBLE_DEVICES")!="" or OUT.exists() or not deadline.tzinfo
            or deadline>compact.AUTHORIZATION_END or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<240):
        raise ValueError("requires a new CPU request in the authorized window")
    checked,(tok,special,texts,refs,model,decode_table,word_table) = prepare()
    if checked!=plan:
        raise ValueError("the sealed request changed")
    cpus = set(model["cpus"])&os.sched_getaffinity(0)
    if not cpus:
        raise ValueError("none of the previous CPU lanes are available")
    cpu = min(cpus)
    os.sched_setaffinity(0,{cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    stop = (special["<|im_end|>"],tok.token_to_id("<eos>"))
    engine = binary(native.tiled_rope.render(native.source_for(2048,3,*stop)))
    normal,parts = native.text_codec(OUT)
    request.render_decoder(normal,decode_table)
    variant = OUT/"mapped_request.py"
    render_input(variant,normal,word_table)
    with ExitStack() as stack:
        with patch.object(request,"OUT",OUT):
            image = request.pack_model(stack,plan["native"]["native"]["state_sha256"],model)
        descriptors = [image]
        for i,blob in enumerate(parts):
            fd = native.base.memfile(f"p077-mapped-full-{i}")
            stack.callback(os.close,fd)
            native.bounded.text.store(fd,blob)
            fcntl.fcntl(fd,native.base.prior.DEPLOY.F_ADD_SEALS,native.base.prior.DEPLOY.SEALS)
            descriptors.append(fd)
        results = []
        for i,case in enumerate(wide.CASES):
            ordering = ("existing","mapped") if (i//2)%2==0 else ("mapped","existing")
            for arm in ordering:
                if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<160:
                    raise TimeoutError("the paired request stopped at its deadline")
                wrapper = normal if arm=="existing" else variant
                output = OUT/f"case_{case}_{arm}.json"
                stats = native.port.request(engine,descriptors,texts[case]["text"].encode("utf-8"),
                                            output,refs[case],wrapper=wrapper)
                if not stats["ids_equal"] or not stats["text_equal"]:
                    raise ValueError("the existing generated answer changed")
                data = trial.read_json(output)
                row = dict(case=case,arm=arm,seconds=stats["seconds"],peak_rss=stats["peak_rss"],
                           encode_seconds=data["encoding"]["seconds"],first_token=data["native"]["seconds"][0],
                           ids_equal=stats["ids_equal"],text_equal=stats["text_equal"])
                results.append(row)
                print(json.dumps(row),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,rows=results,cpu=cpu))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires a sealed full input request and authorized cutoff")
    return run(plan,args.stop_by)


if __name__=="__main__":
    sys.exit(main())
