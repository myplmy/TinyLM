"""Move the fixed automatic table route into the verified native request."""

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

from scripts import diag_p077_g4_table_retrieval as reference
from scripts import diag_p077_native_chat32_request as compact


TAG = "p077_native_table_retrieval_cpu_v1_20261121"
OUT = compact.OUT.with_name(TAG)
trial, native, mapped, full = compact.trial, compact.native, compact.mapped, compact.full
codec, window = compact.codec, compact.window
SELECTOR = codec.SCRIPTS / "p077_native_table_select.hpp"


def generated():
    replace = native.port.replace_once
    source = compact.DRIVER.read_bytes()
    changes = (
        (b'#include "p077_qbpe_generated.hpp"',b'#include "p077_qbpe_generated.hpp"\n#include "p077_native_table_select.hpp"'),
        (b"void encode(char* self, char* engine, char* model, char* archive_fd) {",
         b"void encode(char* self, char* engine, char* model, char* archive_fd, size_t tail_chars) {"),
        (b"        const auto input = tokenizer.encode(std::string_view(text.data(), bytes), scanner);",
         b"        const auto selected = p077_table::choose(std::string_view(text.data(), bytes),tail_chars);\n"
         b"        const auto input = tokenizer.encode(selected.text, scanner);"),
        (b' << ",\\"ids\\":";',
         b' << ",\\"chosen\\":" << selected.table << ",\\"ids\\":";'),
        (b'if (argc == 5 && std::strcmp(argv[1], "encode") == 0) encode(argv[0],argv[2],argv[3],argv[4]);',
         b'''if (argc == 6 && std::strcmp(argv[1], "encode") == 0) {
            size_t chars = 0;
            const auto end = argv[5] + std::strlen(argv[5]);
            const auto parsed = std::from_chars(argv[5],end,chars);
            check(parsed.ec == std::errc{} && parsed.ptr == end && chars > 0 && chars <= 65536,
                  "invalid recent window");
            encode(argv[0],argv[2],argv[3],argv[4],chars);
        }'''),
    )
    for before,after in changes:
        source = replace(source,before,after)
    return source


def prepare():
    original, (_, rows, model, _, _) = reference.prepare()
    report_path = reference.OUT / "report.json"
    saved = trial.read_json(report_path)
    if saved["plan"] != original or len(saved["results"]) != 24:
        raise ValueError("requires the previously completed identical long source")
    compact_plan,_ = compact.prepare()
    verified = compact.OUT/"report.json"
    checked = trial.read_json(verified)
    if checked["plan"] != compact_plan or len(checked["comparisons"]) != 4 or not all(r["same"] for r in checked["comparisons"]):
        raise ValueError("requires the verified complete native codec")
    prior = []
    for i,row in enumerate(rows):
        path = reference.OUT / f"case_{i}_automatic.json"
        old = trial.read_json(path)
        if old["encoding"]["ids"] != row["choices"]["automatic"]["ids"]:
            raise ValueError("the stored automatic branch has different inputs")
        prior.append((old,trial.file_sha(path)))
    cpp = generated()
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), selector=trial.file_sha(SELECTOR),
                codec=trial.file_sha(verified), reference=trial.file_sha(report_path),
                generated=sha256(cpp).hexdigest(), proof=original["proof"],
                original_requests=[digest for _,digest in prior])
    return plan, (rows,model,[a for a,_ in prior],cpp)


def run(plan, deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not deadline.tzinfo
            or deadline > mapped.compact.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 300):
        raise ValueError("requires a new bounded native request comparison")
    checked,(rows,model,prior,source) = prepare()
    if checked != plan:
        raise ValueError("the sealed source changed")
    cpu = min(set(model["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0,{cpu})
    OUT.mkdir()
    cpp = OUT/"codec_retrieval.cpp"
    cpp.write_bytes(source)
    binary = OUT/"codec_retrieval"
    command = ["/usr/bin/g++","-std=c++17","-O3","-Wall","-Wextra","-Werror",
               "-I",str(codec.OUT),"-I",str(codec.SCRIPTS),str(cpp),"-ldl","-o",str(binary)]
    subprocess.run(command,check=True,timeout=65)
    with patch.object(window,"OUT",OUT):
        engine = window.get_binary(plan)
    with ExitStack() as stack:
        with patch.object(mapped.request,"OUT",OUT):
            state = plan["proof"]["native"]["native"]["native"]["state_sha256"]
            image = mapped.request.pack_model(stack,state,model)
        archive = os.open(codec.ASSET,os.O_RDONLY)
        stack.callback(os.close,archive)
        results = []
        for i,(row,old) in enumerate(zip(rows,prior,strict=True)):
            if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 90:
                raise TimeoutError("the paired native retrieval reached its boundary")
            begin = perf_counter()
            proc = subprocess.run([binary,"encode",engine,str(image),str(archive),str(row["tail_chars"])],
                                  pass_fds=(image,archive),input=row["raw"].encode("utf-8"),
                                  capture_output=True,timeout=90)
            seconds = perf_counter()-begin
            if proc.returncode:
                print(proc.stderr.decode("utf-8","replace"),flush=True)
                proc.check_returncode()
            got = json.loads(proc.stdout)
            picked = row["choices"]["automatic"]["selected"]
            if (got["encoding"]["chosen"] != picked or got["encoding"]["ids"] != old["encoding"]["ids"]
                    or got["native"]["ids"] != old["native"]["ids"] or got["decoding"]["text"] != old["decoding"]["text"]
                    or any(got["native"][k]!=old["native"][k] for k in ("model_bytes","kv_bytes"))
                    or not got["native_pid"]==got["encoding"]["pid"]==got["decoding"]["pid"]):
                raise ValueError("the native selector, input, output or process changed")
            trial.publish(OUT/f"case_{i:02d}.json",got)
            peak = native.bounded.prior.peak
            summary = dict(case=i,language=row["language"],phrasing=row["phrasing"],chosen=picked,
                           exact=got["decoding"]["text"].strip()==row["gold"] and got["native"]["ids"][-1]==plan["proof"]["stop"][0],
                           old_rss=peak(old),rss=peak(got),seconds=seconds,input_seconds=got["encoding"]["seconds"],
                           first=got["native"]["seconds"][0])
            results.append(summary)
            print(json.dumps(summary,ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,cpu=cpu,results=results,commands=command,
                                        executable=trial.file_sha(binary)))


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
        parser.error("requires sealed exact requests and a bounded deadline")
    run(plan,args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
