"""Compare the FP16 file KV with its original INT8 codes and scales on identical requests."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_file_staged_prefill as staged


files, native, trial, mapped = staged.files, staged.native, staged.trial, staged.mapped
TAG = "p077_file_int8_packed_cpu_v1_20261124"
OUT = staged.OUT.with_name(TAG)
HEADER = Path(__file__).with_name("p077_file_int8_blocks.hpp")
CODEC = Path(__file__).with_name("p109_g4_grouped_int8_cache.hpp")
BOUNDARIES = (31, 32, 33, 63, 64, 65, 95, 96, 97)
ORDERS = (("fp16", "int8"), ("int8", "fp16"))


def render(control):
    swap = native.port.replace_once
    codec = CODEC.read_bytes()
    anchor = b"class GroupedInt8Cache {"
    codec = swap(codec, anchor, anchor + b"\n    friend class PackedFileGroupedInt8Cache;")
    engine = swap(control, b'#include "p109_g4_grouped_int8_cache.hpp"', codec)
    engine = swap(engine, b'#include "p077_file_grouped_cache.hpp"', HEADER.read_bytes())
    return swap(engine, b"    FileGroupedInt8Cache cache;", b"    PackedFileGroupedInt8Cache cache;")


def prepare():
    previous, (identity, cases, cli, control) = staged.prepare()
    archive = staged.OUT / "report.json"
    existing = trial.read_json(archive)
    if (existing["profile"] != previous or len(cases) != len(ORDERS)
            or not all(row["answer_equal"] for row in existing["rows"])):
        raise ValueError("the packed file trial needs the completed staged file comparison")
    candidate = render(control)
    profile = dict(tag=TAG, source=trial.file_sha(Path(__file__)), previous=previous,
                   previous_report=trial.file_sha(archive), request_binary=trial.file_sha(cli),
                   control_sha256=sha256(control).hexdigest().upper(),
                   candidate_sha256=sha256(candidate).hexdigest().upper(),
                   archived_responses={case["case"]: trial.file_sha(staged.OUT / f"{case['case']}_staged16.json")
                                       for case in cases},
                   boundaries=list(BOUNDARIES), order=[list(order) for order in ORDERS], cpu=previous["cpu"])
    return profile, (identity, cases, cli, control, candidate)


def compile_pair(arm, source):
    folder = OUT / arm
    folder.mkdir()
    with patch.object(native.bounded, "OUT", folder):
        return native.bounded.build(source, caps=(64,))[64]


def compare_boundaries(cases, engines, model, deadline):
    rows = []
    for case in cases:
        for length in BOUNDARIES:
            seconds_left = (deadline - datetime.now(deadline.tzinfo)).total_seconds()
            if seconds_left < 260:
                raise TimeoutError("too little authorized time remains for paired logits")
            left, _, a = native.token_request(engines["fp16"][0], model, case["ids"][:length], 1, trace=True)
            right, _, b = native.token_request(engines["int8"][0], model, case["ids"][:length], 1, trace=True)
            rows.append(dict(case=case["case"], length=length, logits=int(a.size),
                             logits_equal=a.size == b.size == 32_768 and a.tobytes() == b.tobytes(),
                             logit_sha256=[sha256(a.tobytes()).hexdigest(), sha256(b.tobytes()).hexdigest()],
                             ids=[left["ids"], right["ids"]]))
    trial.publish(OUT / "boundaries.json", rows)
    if not all(row["logits_equal"] and row["ids"][0] == row["ids"][1] for row in rows):
        raise ValueError("the new file layout changed boundary logits or ids")
    return rows


def run(profile, deadline):
    checked, (identity, cases, cli, control, candidate) = prepare()
    if (checked != profile or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > files.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 390):
        raise ValueError("the comparison requires exact CPU inputs and a bounded authorization window")
    os.sched_setaffinity(0, {profile["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    engines = {name: compile_pair(name, source) for name, source in (("fp16", control), ("int8", candidate))}
    rows = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            ancestor = profile["previous"]["prior"]["source_receipt"]["prior"]["prior"]
            state_sha = ancestor["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, state_sha, identity)
        boundaries = compare_boundaries(cases, engines, model, deadline)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for case, order in zip(cases, ORDERS, strict=True):
            responses = {arm: files.request(OUT, case, arm, cli, engines[arm][1], model, archive, deadline)
                         for arm in order}
            old = trial.read_json(staged.OUT / f"{case['case']}_staged16.json")["native"]
            left, right = [responses[name][0]["native"] for name in ("fp16", "int8")]
            if (left["ids"] != old["ids"] or left["kv_read_bytes"] != old["kv_read_bytes"]
                    or left["model_bytes"] != right["model_bytes"] or not 0 < right["kv_written_bytes"] <= right["kv_backing_bytes"]):
                raise ValueError("the original comparison or packed file accounting failed")
            row = dict(case=case["case"], input_tokens=len(case["ids"]), gold=case["gold"], order=order,
                       ids_equal=left["ids"] == right["ids"], arms={},
                       model_bytes=left["model_bytes"])
            for arm, (capture, elapsed) in responses.items():
                stats = capture["native"]
                row["arms"][arm] = dict(text=capture["decoding"]["text"], elapsed=elapsed,
                                        first=stats["seconds"][0], rss=native.bounded.prior.peak(capture),
                                        scratch=stats["scratch_bytes"],
                                        **{k: v for k, v in stats.items() if k.startswith("kv_")})
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(profile=profile, rows=rows, boundary_cases=len(boundaries),
                                          exact_boundary_logits=sum(row["logits"] for row in boundaries)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        profile, _ = prepare()
        trial.publish(args.receipt, profile)
        print(trial.file_sha(args.receipt), flush=True)
        return 0
    if args.stop_by is None:
        parser.error("an authorized model execution cutoff is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
