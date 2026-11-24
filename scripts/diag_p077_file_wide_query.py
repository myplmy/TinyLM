"""Reuse each historic file KV tile across 32 queries in the native CPU runtime."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_file_grouped_cache as files
from scripts import diag_p077_g4_wide_query_prefill as wider


native, trial, mapped = files.native, files.trial, files.mapped
TAG = "p077_file_wide_query_cpu_v1_20261124"
OUT = files.OUT.with_name(TAG)


def prepare():
    source_receipt, (_, model_profile, cases, text_request, _, control) = files.prepare()
    swap = native.port.replace_once
    candidate = swap(control, b"    static constexpr int PrefillQueries = 8;",
                     b"    static constexpr int PrefillQueries = 32;")
    evidence = files.OUT / "report.json"
    original = trial.read_json(evidence)
    if original["plan"] != source_receipt or len(cases) != 4:
        raise ValueError("the prior file execution and source plan must match")
    long = [row for row in cases if row["kind"] == "4096"]
    plan = dict(tag=TAG, sources={p.name: trial.file_sha(p) for p in
                                (Path(__file__), Path(wider.__file__), wider.ATTENTION, evidence)},
                source_receipt=source_receipt, previous_file_result=trial.file_sha(evidence),
                control_sha256=sha256(control).hexdigest().upper(),
                candidate_sha256=sha256(candidate).hexdigest().upper(),
                order=[["file", "wide32"], ["wide32", "file"]],
                cases=[dict(case=case["case"], input_tokens=len(case["ids"])) for case in long])
    return plan, (model_profile, long, text_request, control, candidate)


def executable(source, kind):
    if kind == "file":
        receipt = trial.read_json(files.OUT / "file" / "compiler.json")
        evidence = receipt["binaries"]["64"][1]
        binary = Path(evidence["path"])
        if (receipt["source_sha256"] == sha256(source).hexdigest().upper() and binary.is_file()
                and native.base.SHA(binary) == evidence["sha256"]):
            return binary
    folder = OUT / kind
    folder.mkdir()
    with patch.object(native.bounded, "OUT", folder):
        return native.bounded.build(source, caps=(64,))[64][1]


def run(plan, stop_by):
    actual, (identity, cases, cli, control, candidate) = prepare()
    if (actual != plan or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or stop_by.tzinfo is None or stop_by > files.AUTHORIZATION_END
            or (stop_by - datetime.now(stop_by.tzinfo)).total_seconds() < 360):
        raise ValueError("the sealed CPU comparison needs its own output and authorized interval")
    cpu = max(set(identity["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    engines = {"file": executable(control, "file"), "wide32": executable(candidate, "wide32")}
    prior = trial.read_json(files.OUT / "report.json")
    rows = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            model_sha = plan["source_receipt"]["prior"]["prior"]["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, model_sha, identity)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for case, order in zip(cases, plan["order"], strict=True):
            answers = {arm: files.request(OUT, case, arm, cli, engines[arm], model, archive, stop_by) for arm in order}
            left, right = [answers[arm][0]["native"] for arm in ("file", "wide32")]
            original = trial.read_json(files.OUT / f"{case['case']}_file.json")["native"]
            if (left["model_bytes"] != right["model_bytes"] or left["ids"] != original["ids"]
                    or left["kv_read_bytes"] != original["kv_read_bytes"]
                    or left["kv_written_bytes"] != right["kv_written_bytes"]):
                raise ValueError("the file control did not reproduce the earlier model, I/O and answers")
            row = dict(case=case["case"], answer_equal=left["ids"] == right["ids"], gold=case["gold"],
                       output=[answers[arm][0]["decoding"]["text"] for arm in ("file", "wide32")],
                       elapsed=[answers[arm][1] for arm in ("file", "wide32")],
                       first=[item["seconds"][0] for item in (left, right)],
                       read_bytes=[item["kv_read_bytes"] for item in (left, right)],
                       rss_bytes=[native.bounded.prior.peak(answers[arm][0]) for arm in ("file", "wide32")])
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(plan=plan, cpu=cpu, rows=rows,
                  archived_result_sha256=plan["previous_file_result"], previous_requests=len(prior["results"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        plan, _ = prepare()
        trial.publish(args.receipt, plan)
        print(trial.file_sha(args.receipt), plan["cases"], flush=True)
        return 0
    if args.stop_by is None:
        parser.error("the exact time approval is required for model execution")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
