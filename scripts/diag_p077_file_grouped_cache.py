"""Measure exact file-backed KV with the existing whole native P077 model request."""

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

from scripts import diag_p077_native_chat32_kv_quality as quality


TAG = "p077_file_grouped_cache_cpu_v1_20261124"
OUT = quality.OUT.with_name(TAG)
AUTHORIZATION_END = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
native, trial, mapped, codec = quality.native, quality.trial, quality.mapped, quality.codec
HEADER = codec.SCRIPTS / "p077_file_grouped_cache.hpp"


def engine_for(control):
    replace = native.port.replace_once
    control = replace(control, b'#include <fcntl.h>', b'#include <fcntl.h>\n#include <memory>')
    anchor = b'#include "p077_rope_tile.hpp"'
    control = replace(control, anchor, anchor + b'\n#include "p077_file_grouped_cache.hpp"')
    control = replace(control, b'    GroupedInt8Cache cache;', b'    FileGroupedInt8Cache cache;')
    anchor = b'        print_memory("before", before);'
    report = br'''        printf(",\"kv_backing_bytes\":%zu,\"kv_file_allocated_bytes\":%zu,"
               "\"kv_read_bytes\":%zu,\"kv_written_bytes\":%zu", runtime.cache.backing_bytes(),
               runtime.cache.allocated_file_bytes(), runtime.cache.bytes_read(), runtime.cache.bytes_written());
'''
    return replace(control, anchor, report + anchor)


def prepare():
    old, (tokenizer, longer, identity, _, executable, source) = quality.prepare()
    _, (_, _, shorter, _, _, _, _) = mapped.prepare()
    cases = [
        dict(shorter[0], case="short-ko", kind="2048", old=None),
        dict(shorter[4], case="short-en", kind="2048", old=None),
        dict(longer[1], case="long-ko", kind="4096", old=quality.OUT / "request_01.json"),
        dict(longer[5], case="long-en", kind="4096", old=quality.OUT / "request_05.json"),
    ]
    if len({tuple(row["ids"]) for row in cases}) != len(cases):
        raise ValueError("the long and short requests must be distinct")
    candidate = engine_for(source)
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), cache_header=trial.file_sha(HEADER),
                prior=old, control_sha256=sha256(source).hexdigest(), file_sha256=sha256(candidate).hexdigest(),
                requests=[dict(case=row["case"], language=row["language"], tokens=len(row["ids"]),
                               text_sha256=sha256(row["text"].encode("utf-8")).hexdigest(),
                               old_sha256=trial.file_sha(row["old"]) if row["old"] else None) for row in cases])
    return plan, (tokenizer, identity, cases, executable, source, candidate)


def request(output, case, name, exe, engine, model, archive, deadline):
    seconds_left = (deadline-datetime.now(deadline.tzinfo)).total_seconds()
    if seconds_left < 90:
        raise TimeoutError("the native KV request is outside the approved window")
    started = perf_counter()
    process = subprocess.run([exe, "encode", engine, str(model), str(archive)],
                             pass_fds=(model, archive), input=case["text"].encode("utf-8"),
                             capture_output=True, timeout=min(125, seconds_left))
    if process.returncode:
        print(process.stderr.decode("utf-8", "replace"), flush=True)
        process.check_returncode()
    elapsed = perf_counter() - started
    row = json.loads(process.stdout)
    if (row["encoding"]["ids"] != case["ids"]
            or row["native_pid"] != row["encoding"]["pid"] or row["native_pid"] != row["decoding"]["pid"]):
        raise ValueError("the given request changed or left the same-process native path")
    trial.publish(output / f"{case['case']}_{name}.json", row)
    return row, elapsed


def run(plan, deadline):
    checked, (tokenizer, identity, cases, codec_request, control, candidate) = prepare()
    if (plan != checked or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 360):
        raise ValueError("the file-backed experiment requires the sealed CPU run and cutoff")
    cpu = min(set(identity["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    OUT.mkdir()
    folder = OUT / "file"
    folder.mkdir()
    with patch.object(native.bounded, "OUT", folder):
        file_engine = native.bounded.build(candidate, caps=(64,))[64][1]
    existing = trial.read_json(quality.OUT / "compiler.json")
    entry = existing["binaries"]["64"][1]
    path = Path(entry["path"])
    if existing["source_sha256"] != checked["control_sha256"].upper():
        raise ValueError("the archived INT8 compiler receipt has the wrong source")
    if path.is_file() and native.base.SHA(path) == entry["sha256"]:
        base_engine = path
    else:
        folder = OUT / "ram"
        folder.mkdir()
        with patch.object(native.bounded, "OUT", folder):
            base_engine = native.bounded.build(control, caps=(64,))[64][1]

    results = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            body_sha = checked["prior"]["prior"]["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, body_sha, identity)
        archive = os.open(codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for index, case in enumerate(cases):
            arms = (("ram", base_engine), ("file", file_engine))
            if index % 2:
                arms = tuple(reversed(arms))
            captures = {arm:request(OUT, case, arm, codec_request, engine, model, archive, deadline)
                        for arm, engine in arms}
            ram, ram_elapsed = captures["ram"]
            file, file_elapsed = captures["file"]
            if ram["native"]["model_bytes"] != file["native"]["model_bytes"]:
                raise ValueError("the compared KV backends used unequal model bytes")
            got = file["native"]
            if (got["kv_written_bytes"] <= 0 or got["kv_read_bytes"] <= 0
                    or got["kv_file_allocated_bytes"] <= 0 or got["kv_written_bytes"] > got["kv_backing_bytes"]):
                raise ValueError("the purported external KV did not perform bounded file I/O")
            archived = trial.read_json(case["old"])["native"]["ids"] if case["old"] else None
            result = dict(case=case["case"], language=case["language"], input_tokens=len(case["ids"]),
                          ids_equal=ram["native"]["ids"] == got["ids"],
                          archived_equal=archived == ram["native"]["ids"] if archived is not None else None,
                          ram_output=ram["decoding"]["text"], file_output=file["decoding"]["text"],
                          gold=case["gold"], ram_rss=native.bounded.prior.peak(ram),
                          file_rss=native.bounded.prior.peak(file), ram_kv_bytes=ram["native"]["kv_bytes"],
                          ram_first=ram["native"]["seconds"][0], file_first=got["seconds"][0],
                          ram_seconds=ram_elapsed, file_seconds=file_elapsed,
                          file_stats={key:value for key,value in got.items() if key.startswith("kv_")})
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(plan=plan, cpu=cpu, results=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        plan, _ = prepare()
        trial.publish(args.receipt, plan)
        print(trial.file_sha(args.receipt), plan["requests"], flush=True)
        return 0
    if args.stop_by is None or args.stop_by.tzinfo is None or args.stop_by > AUTHORIZATION_END:
        parser.error("an authorized cutoff with a timezone is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
