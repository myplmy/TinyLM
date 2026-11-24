"""Measure the exact native ChatML codec through one full model request PID."""

import argparse
from contextlib import ExitStack
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
from unittest.mock import patch

from scripts import diag_p077_g4_evidence_window as window
from scripts import diag_p077_native_chat32_codec as codec


TAG = "p077_native_chat32_request_cpu_v1_20261121"
OUT = codec.OUT.with_name(TAG)
full, trial, native, mapped = window.full, codec.trial, window.native, codec.mapped
DRIVER = codec.SCRIPTS / "p077_native_qbpe_request.cpp"


def prepare():
    measured = codec.OUT / "report.json"
    proof = trial.read_json(measured)
    known, _ = codec.prepare()
    generated = codec.OUT / "p077_qbpe_generated.hpp"
    if (proof["plan"] != known or proof["mismatch_count"] or proof["native_sha256"] != proof["expected_sha256"]
            or trial.file_sha(generated) != known["generate"]):
        raise ValueError("requires the completed native codec equivalence proof")
    long_plan, (tok, longer, identity, _, _) = full.prepare()
    _, (_, _, shorter, _, _, _, _) = mapped.prepare()
    cases = []
    for label, samples, original in (("2048", shorter, mapped.OUT), ("4096", longer, full.OUT)):
        for index in (0, 4):
            name = f"case_{index}_mapped.json" if label == "2048" else f"k4v3_{index:02d}.json"
            file = original / name
            measured = trial.read_json(file)
            row = samples[index]
            if measured["encoding"]["ids"] != row["ids"]:
                raise ValueError("requires the already measured same-text full request")
            cases.append(dict(length=label, index=index, language=row["language"], text=row["text"],
                              sha256=trial.file_sha(file), known=measured))
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), driver=trial.file_sha(DRIVER),
                equivalence=trial.file_sha(codec.OUT/"report.json"), compiled_header=trial.file_sha(generated),
                proof=long_plan, cases=[{k:v for k,v in row.items() if k not in ("text","known")} for row in cases])
    return plan, (tok, identity, cases)


def run(plan, deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not deadline.tzinfo
            or deadline > mapped.compact.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 240):
        raise ValueError("requires a new authorized CPU request")
    checked, (_, identity, cases) = prepare()
    if checked != plan:
        raise ValueError("the sealed artifacts changed")
    cpu = min(set(identity["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    OUT.mkdir()
    binary = OUT/"codec_request"
    compile_cli = ["/usr/bin/g++","-std=c++17","-O3","-Wall","-Wextra","-Werror",
                   "-I",str(codec.OUT),"-I",str(codec.SCRIPTS),str(DRIVER),"-ldl","-o",str(binary)]
    subprocess.run(compile_cli, check=True, timeout=65)
    with patch.object(window, "OUT", OUT):
        engine = window.get_binary(plan)
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            state = plan["proof"]["native"]["native"]["native"]["state_sha256"]
            image = mapped.request.pack_model(stack, state, identity)
        archive = os.open(codec.ASSET, os.O_RDONLY)
        stack.callback(os.close,archive)
        comparisons = []
        for row in cases:
            if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 90:
                raise TimeoutError("the full native request comparison reached its boundary")
            start = perf_counter()
            proc = subprocess.run([binary,"encode",engine,str(image),str(archive)],
                                  input=row["text"].encode("utf-8"), pass_fds=(image,archive),
                                  capture_output=True, timeout=95)
            seconds = perf_counter()-start
            if proc.returncode:
                print(proc.stderr.decode("utf-8","replace"),flush=True)
                proc.check_returncode()
            got = json.loads(proc.stdout)
            old = row["known"]
            same = (got["encoding"]["ids"] == old["encoding"]["ids"]
                    and got["native"]["ids"] == old["native"]["ids"]
                    and got["decoding"]["text"] == old["decoding"]["text"]
                    and all(got["native"][k]==old["native"][k] for k in ("kv_bytes","model_bytes")))
            if not same or got["encoding"]["pid"] != got["decoding"]["pid"] or got["native_pid"] != got["encoding"]["pid"]:
                raise ValueError("a native whole request changed the input, output or process ID")
            filename = f'case_{row["length"]}_{row["index"]}.json'
            trial.publish(OUT/filename, got)
            peak = native.bounded.prior.peak
            info = dict(length=row["length"], index=row["index"], language=row["language"],
                        input_tokens=len(got["encoding"]["ids"]), same=True, old_rss=peak(old), rss=peak(got),
                        old_input_seconds=old["encoding"]["seconds"], input_seconds=got["encoding"]["seconds"],
                        old_first=old["native"]["seconds"][0], first=got["native"]["seconds"][0],
                        seconds=seconds, output=got["decoding"]["text"])
            comparisons.append(info)
            print(json.dumps(info,ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan, comparisons=comparisons, cpu=cpu, compiler=compile_cli,
                                         binary_sha256=trial.file_sha(binary)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires sealed exact requests and an authorized cutoff")
    run(plan,args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
