"""Check the measured eight-query candidate against 64 archived response pairs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch

from scripts import diag_p077_g4_wide_query_prefill as prefill


TAG = "p077_g4_wide_query_quality_cpu_v1_20261121"
OUT = prefill.OUT.with_name(TAG)
native,request,trial = prefill.native,prefill.request,prefill.trial
ARM = "online8"


def prepare():
    earlier,_ = prefill.prepare()
    source = prefill.OUT / "report.json"
    timing = trial.read_json(source)
    selected = [row for row in timing["rows"] if row["arm"]==ARM]
    if (timing["profile"]!=earlier or len(selected)!=4
            or not all(row["ids_equal"] and row["text_equal"] for row in selected)):
        raise ValueError("requires the completed width comparison without changed outputs")
    plan,(tok,special,rows,quality,_) = native.prepare(rope=True)
    baseline = native.ROPE_OUT / "report.json"
    original = trial.read_json(baseline)["quality"]
    if (len(original)!=64 or len(quality)!=128
            or any(a["root"]!=b["root"] or a["gold"]!=b["gold"] for a,b in zip(rows,original,strict=True))):
        raise ValueError("the fixed token questions no longer match result 065")
    profile = dict(tag=TAG, source_sha256=trial.file_sha(Path(__file__)), timing_sha256=trial.file_sha(source),
                   archived_sha256=trial.file_sha(baseline), quality_sha256=plan["quality_sha256"],
                   candidate=ARM, native=plan)
    return profile,(tok,special,rows,quality,original)


def binary(source):
    receipt = trial.read_json(prefill.OUT / ARM / "compiler.json")
    entry = receipt["binaries"]["64"][0]
    path = Path(entry["path"])
    candidate = prefill.render(source,ARM)
    if (receipt["source_sha256"]!=sha256(candidate).hexdigest().upper()):
        raise ValueError("the measured online engine source changed")
    if path.is_file() and native.base.SHA(path)==entry["sha256"]:
        trial.publish(OUT / "timing_compiler.json", receipt)
        return path
    with patch.object(native.bounded,"OUT",OUT):
        return native.bounded.build(candidate,caps=(64,))[64][0]


def run(profile,deadline):
    if (not deadline.tzinfo or deadline>request.byte_table.AUTHORIZATION_END or OUT.exists()
            or os.environ.get("CUDA_VISIBLE_DEVICES")!="" or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<360):
        raise ValueError("requires sufficient CPU time in the authorized window and a fresh output")
    checked,(tok,special,cases,ids,baseline) = prepare()
    if checked!=profile:
        raise ValueError("the quality run inputs changed after preflight")
    previous = trial.read_json(native.ROPE_OUT / "identity.json")
    cpus = sorted(set(previous["cpus"])&os.sched_getaffinity(0))
    if not cpus:
        raise ValueError("no CPU lane from the previous paired run is available")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    stop = (special["<|im_end|>"],tok.token_to_id("<eos>"))
    source = native.tiled_rope.render(native.source_for(2048,3,*stop))
    engine = binary(source)
    with ExitStack() as stack:
        with patch.object(request,"OUT",OUT):
            asset = request.pack_model(stack,profile["native"]["state_sha256"],previous)

        def lane(cpu,offset):
            os.sched_setaffinity(0,{cpu})
            for i in range(offset,len(cases),len(cpus)):
                legacy = baseline[i]["arms"]["tile_rope_2048"]
                payload = cases[i]
                paired = []
                for side,(query,gold) in enumerate(zip(ids[2*i:2*i+2],payload["gold"],strict=True)):
                    if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<135:
                        raise TimeoutError("the quality pass stopped at its deadline")
                    output,elapsed,_ = native.token_request(engine,asset,query,native.GEN)
                    if output["kv_bytes"]!=native.cache_bytes(len(query)+native.GEN-1,3):
                        raise ValueError("KV capacity changed")
                    got = native.decoded(tok,output,gold,stop)
                    paired.append(dict(current=got,archived=legacy[side],same_ids=got["ids"]==legacy[side]["ids"],seconds=elapsed))
                trial.publish(OUT/f"pair_{i:02d}.json",dict(root=payload["root"],language=payload["language"],sides=paired))

        with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
            tasks = [pool.submit(lane,cpu,offset) for offset,cpu in enumerate(cpus)]
            for task in tasks:
                task.result()
    rows = [trial.read_json(OUT/f"pair_{i:02d}.json") for i in range(64)]
    counts = {}
    for lang in ("ko","en"):
        selected = [r["sides"] for r in rows if r["language"]==lang]
        cases = [x for pair in selected for x in pair]
        counts[lang] = dict(pairs=len(selected),archived_both=sum(all(x["archived"]["exact"] for x in pair) for pair in selected),
                           current_both=sum(all(x["current"]["exact"] for x in pair) for pair in selected),
                           same_ids=sum(r["same_ids"] for r in cases),ended=sum(r["current"]["eot"] for r in cases),
                           before=sum(r["archived"]["exact"] for r in cases),after=sum(r["current"]["exact"] for r in cases),
                           gained=sum(not r["archived"]["exact"] and r["current"]["exact"] for r in cases),
                           lost=sum(r["archived"]["exact"] and not r["current"]["exact"] for r in cases))
    trial.publish(OUT/"report.json",dict(plan=profile,counts=counts,rows=rows))
    print(json.dumps(counts),flush=True)
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
        parser.error("requires sealed quality inputs and a future authorized cutoff")
    return run(plan,args.stop_by)


if __name__=="__main__":
    sys.exit(main())
