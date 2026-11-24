"""Spend the lower tokenizer RSS on higher-precision KV in the same 4,096 requests."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
from unittest.mock import patch

from scripts import diag_p077_native_chat32_request as compact


TAG = "p077_native_chat32_kv_quality_cpu_v1_20261121"
OUT = compact.OUT.with_name(TAG)
trial, full, mapped, native, codec = compact.trial, compact.full, compact.mapped, compact.native, compact.codec
BITS = (8, 8)


def prepare():
    native_report = compact.OUT / "report.json"
    proof = trial.read_json(native_report)
    exe = compact.OUT / "codec_request"
    if (len(proof["comparisons"]) != 4 or not all(r["same"] for r in proof["comparisons"])
            or trial.file_sha(exe) != proof["binary_sha256"]):
        raise ValueError("requires the verified whole native ChatML request")
    prior_plan, (tok, cases, model, _, _) = full.prepare()
    reference = full.OUT / "report.json"
    older = trial.read_json(reference)
    if older["plan"] != prior_plan or len(older["results"]) != 16:
        raise ValueError("requires the exact quality comparison to the old K4V3 requests")
    baseline = []
    for i,row in enumerate(cases):
        req = full.OUT / f"k4v3_{i:02d}.json"
        saved = trial.read_json(req)
        if saved["encoding"]["ids"] != row["ids"]:
            raise ValueError("the existing holdout input changed")
        baseline.append(dict(sha256=trial.file_sha(req), result=saved))
    cpp = full.source_for(prior_plan["stop"], BITS)
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), requests=trial.file_sha(reference),
                native=trial.file_sha(native_report), tokenizer=proof["binary_sha256"], bits=list(BITS),
                engine=sha256(cpp).hexdigest(), baseline=[r["sha256"] for r in baseline], prior=prior_plan)
    return plan, (tok,cases,model,[r["result"] for r in baseline],exe,cpp)


def run(plan, deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not deadline.tzinfo
            or deadline > mapped.compact.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 360):
        raise ValueError("requires a new bounded CPU model use")
    checked,(tok,cases,model,baseline,exe,cpp) = prepare()
    if checked != plan:
        raise ValueError("the source or request changed")
    cpu = min(set(model["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    OUT.mkdir()
    with patch.object(native.bounded,"OUT",OUT):
        engine = native.bounded.build(cpp, caps=(64,))[64][1]
    results = []
    with ExitStack() as stack:
        with patch.object(mapped.request,"OUT",OUT):
            state = plan["prior"]["native"]["native"]["native"]["state_sha256"]
            image = mapped.request.pack_model(stack, state, model)
        archive = os.open(codec.ASSET,os.O_RDONLY)
        stack.callback(os.close,archive)
        for i,(row,old) in enumerate(zip(cases,baseline,strict=True)):
            if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 100:
                raise TimeoutError("the precision comparison reached its deadline")
            start = perf_counter()
            proc = subprocess.run([exe,"encode",engine,str(image),str(archive)], pass_fds=(image,archive),
                                  input=row["text"].encode("utf-8"),capture_output=True,timeout=100)
            seconds = perf_counter()-start
            if proc.returncode:
                print(proc.stderr.decode("utf-8","replace"),flush=True)
                proc.check_returncode()
            got = json.loads(proc.stdout)
            kv = full.cache_size(len(row["ids"])+native.GEN-1, BITS)
            if (got["encoding"]["ids"] != row["ids"] or got["native"]["model_bytes"] != old["native"]["model_bytes"]
                    or got["native"]["kv_bytes"] != kv or got["native_pid"] != got["encoding"]["pid"]
                    or got["native_pid"] != got["decoding"]["pid"]):
                raise ValueError("model, context, or process identity differs")
            trial.publish(OUT/f"request_{i:02d}.json",got)
            info = dict(case=i, language=row["language"], place=row["place"], gold=row["gold"],
                        seconds=seconds, peak_rss=native.bounded.prior.peak(got), kv_bytes=kv,
                        old=native.decoded(tok,old["native"],row["gold"],plan["prior"]["stop"]),
                        current=native.decoded(tok,got["native"],row["gold"],plan["prior"]["stop"]))
            results.append(info)
            print(json.dumps(info,ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,cpu=cpu,results=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode == "check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires the sealed requests and an authorized deadline")
    run(plan,args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
