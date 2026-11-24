"""Check both compact text stages in the full-width G4 request."""

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
from tokenizers import Tokenizer

from scripts import diag_p077_compact_chat32_request as mapped
from scripts import diag_p077_g4_full_width_prefill as full
from scripts import p109_compact_qwen_tokenizer as wire


TAG = "p077_full_width_compact_text_cpu_v1_20261121"
OUT = full.OUT.with_name(TAG)
trial,base,bounded = full.trial,full.base,full.bounded
packed_output = mapped.request.byte_table


def prepare():
    upstream,(fixtures,legacy,reference,wires,src,_) = full.prepare()
    timed_path = full.OUT/"report.json"
    timed = trial.read_json(timed_path)
    if timed["plan"]!=upstream or not all(row["unchanged"] for row in timed["rows"]):
        raise ValueError("requires the completed full-width CPU timing")
    source = full.codec.TOK.read_bytes()
    if sha256(source).hexdigest().upper()!=upstream["tokenizer_sha256"]:
        raise ValueError("the wide tokenizer changed")
    chosen = mapped.wide.render(src,"online8")
    return dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),fixture=upstream,
                timed_sha256=trial.file_sha(timed_path),engine_sha256=sha256(chosen).hexdigest().upper()), (
                fixtures,legacy,reference,wires,source,chosen,timed)


def binary(src):
    saved = trial.read_json(full.OUT/"online8"/"compiler.json")
    entry = saved["binaries"]["64"][1]
    if saved["source_sha256"]!=sha256(src).hexdigest().upper():
        raise ValueError("the known full-width engine source changed")
    original = Path(entry["path"])
    if original.is_file() and base.SHA(original)==entry["sha256"]:
        trial.publish(OUT/"compiler.json",saved)
        return original
    with patch.object(bounded,"OUT",OUT):
        return bounded.build(src,caps=(64,))[64][1]


def run(plan,deadline):
    if (os.environ.get("CUDA_VISIBLE_DEVICES")!="" or not deadline.tzinfo or deadline>mapped.compact.AUTHORIZATION_END
            or OUT.exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<230):
        raise ValueError("requires a new CPU output and an adequate authorized window")
    checked,(fixtures,legacy,reference,wires,tokenizer,engine,timed) = prepare()
    if checked!=plan:
        raise ValueError("the original wide text fixture changed")
    cpu = timed["cpu"]
    if cpu not in os.sched_getaffinity(0):
        raise ValueError("the measured CPU core is unavailable")
    os.sched_setaffinity(0,{cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    bin_path = binary(engine)
    source = json.loads(tokenizer)
    official = Tokenizer.from_buffer(tokenizer)
    encode_table,decode_table = (OUT/file for file in ("input_table.bin","output_table.bin"))
    mapped.compact.pack_chat32(source,encode_table)
    with wire.CompactQwenTokenizer(encode_table) as loader:
        verified_input = mapped.compact.verify(official,loader,[fixtures["inputs"][task]["1792"]["prompt"]
                                                                for task in full.TASKS])
    decode = packed_output.pack(source["model"]["vocab"],{r["id"] for r in source["added_tokens"]})
    output = packed_output.OutputTable(decode)
    for task in full.TASKS:
        ids = reference[task]["generated_ids"]
        if output.decode(ids)!=official.decode(ids,skip_special_tokens=True):
            raise ValueError("the wide output bytes changed")
    decode_table.write_bytes(decode)
    reference_wrapper = full.texts.wrapper(OUT/"with_old_input.py",1792,128)
    mapped.request.render_decoder(reference_wrapper,decode_table)
    wrapper = OUT/"compact_text.py"
    mapped.render_input(wrapper,reference_wrapper,encode_table)
    with ExitStack() as stack:
        r4,r5,vocab,merges = [base.memfile(f"p077-wide-compact-{name}") for name in ("r4","r5","vocab","merges")]
        for fd in (r4,r5,vocab,merges):
            stack.callback(os.close,fd)
        pin = base.READ(bounded.text.OUT/"profile.json")["pins"]["candidate"]
        model = base.prior.load_candidate(pin)
        old = base.model_blob(model,r4,pin["model_tensor_bytes"])
        now = full.native.extend_positions(r4,r5,model)
        del model
        if old!=legacy["r4"] or now!=legacy["r5"]:
            raise ValueError("the archived full-width artifact changed")
        for fd,blob in zip((vocab,merges),wires,strict=True):
            bounded.text.store(fd,blob)
            fcntl.fcntl(fd,base.prior.DEPLOY.F_ADD_SEALS,base.prior.DEPLOY.SEALS)
        assets = {2048:((r5,vocab,merges),now["artifact_bytes"])}
        rows = []
        for task in full.TASKS:
            if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<160:
                raise TimeoutError("the full-width request stopped at its deadline")
            row = full.texts.request(full.MODE,task,fixtures["inputs"][task]["1792"],{2048:bin_path},
                                     {full.MODE:wrapper},assets,legacy["stop_ids"],OUT)
            match = row["generated_ids"]==reference[task]["generated_ids"]
            raw = trial.read_json(OUT/f"{task}-{full.MODE}.json")
            old_raw = trial.read_json(full.texts.OUT/f"{task}-{full.MODE}.json")
            if not match or raw["decoding"]["text"]!=old_raw["decoding"]["text"]:
                raise ValueError("the wide request output changed")
            row["archived_match"] = match
            rows.append(row)
            print(json.dumps({key:row[key] for key in ("task","peak_rss","seconds","archived_match")}),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,rows=rows,input_sequences=verified_input,
                  input_sha256=trial.file_sha(encode_table),output_sha256=trial.file_sha(decode_table),cpu=cpu))
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
        parser.error("requires the sealed full-width request and authorized cutoff")
    return run(plan,args.stop_by)


if __name__=="__main__":
    sys.exit(main())
