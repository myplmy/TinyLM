"""Reuse three projection tiles for packed-file INT8 attention."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p077_file_int8_blocks as prior


files, native, trial, mapped = prior.files, prior.native, prior.trial, prior.mapped
TAG = "p077_file_int8_staged24_cpu_v1_20261124"
OUT = prior.OUT.with_name(TAG)
BOUNDARIES = (7, 8, 9, 15, 16, 17, 23, 24, 25, 31, 32, 33, 63, 64, 65, 127, 128, 129)
ORDERS = (("width16", "width24"), ("width24", "width16"))


def render(source):
    swap = native.port.replace_once
    for old, new in ((b"    static constexpr int PrefillQueries = 16;", b"    static constexpr int PrefillQueries = 24;"),
                     (b"static_assert(Tile == 8 && F >= 2 * D);", b"static_assert(Tile == 8 && F >= 3 * D);"),
                     (b"constexpr int QueryRows = 2 * Tile;", b"constexpr int QueryRows = 3 * Tile;")):
        source = swap(source, old, new)
    return source


def prepare():
    previous, (identity, cases, cli, _, source) = prior.prepare()
    archived = prior.OUT / "report.json"
    report = trial.read_json(archived)
    compiler = prior.OUT / "int8" / "compiler.json"
    compilation = trial.read_json(compiler)
    binaries = compilation["binaries"]["64"]
    if (previous != report["profile"] or [row["case"] for row in report["rows"]] != [case["case"] for case in cases]
            or compilation["source_sha256"].upper() != sha256(source).hexdigest().upper()
            or any(trial.file_sha(Path(entry["path"])).upper() != entry["sha256"].upper() for entry in binaries)):
        raise ValueError("the original INT8 engine, source and real long results must match")
    candidate = render(source)
    profile = dict(tag=TAG, prior=previous, baseline_report=trial.file_sha(archived), compiler=trial.file_sha(compiler),
                   source=trial.file_sha(Path(__file__)), width16=sha256(source).hexdigest().upper(),
                   width24=sha256(candidate).hexdigest().upper(), cpu=previous["cpu"],
                   boundaries=list(BOUNDARIES), request_order=[list(order) for order in ORDERS])
    baseline = tuple(Path(entry["path"]) for entry in binaries)
    return profile, (identity, cases, cli, baseline, candidate)


def boundary_logits(cases, engines, model, deadline):
    rows = []
    for case in cases:
        for length in BOUNDARIES:
            if datetime.now(deadline.tzinfo) >= deadline:
                raise TimeoutError("the CPU boundary checks reached their cutoff")
            left, _, a = native.token_request(engines["width16"][0], model, case["ids"][:length], 1, trace=True)
            right, _, b = native.token_request(engines["width24"][0], model, case["ids"][:length], 1, trace=True)
            rows.append(dict(case=case["case"], length=length, prior_ids=left["ids"], candidate_ids=right["ids"],
                             logits=len(a.ravel()), exact=int(np.equal(a, b).sum()),
                             max_abs=float(np.max(np.abs(a - b)))))
    return rows


def run(profile, deadline):
    checked, (identity, cases, cli, baseline, candidate) = prepare()
    if (checked != profile or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > files.AUTHORIZATION_END
            or datetime.now(deadline.tzinfo) >= deadline):
        raise ValueError("the exact CPU scope and authorized cutoff are required")
    os.sched_setaffinity(0, {profile["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    with patch.object(prior, "OUT", OUT):
        engines = dict(width16=baseline, width24=prior.compile_pair("width24", candidate))
    rows = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            ancestor = profile["prior"]["previous"]["prior"]["source_receipt"]["prior"]["prior"]
            model = mapped.request.pack_model(stack, ancestor["native"]["native"]["native"]["state_sha256"], identity)
        boundaries = boundary_logits(cases, engines, model, deadline)
        trial.publish(OUT / "boundaries.json", boundaries)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for case, order in zip(cases, ORDERS, strict=True):
            captures = {arm: files.request(OUT, case, arm, cli, engines[arm][1], model, archive, deadline) for arm in order}
            old = trial.read_json(prior.OUT / f"{case['case']}_int8.json")["native"]
            stored = captures["width16"][0]["native"]
            if stored["ids"] != old["ids"] or stored["kv_read_bytes"] != old["kv_read_bytes"]:
                raise ValueError("contemporaneous reference must reproduce the archived width-16 request")
            measurement = {}
            for arm, (capture, elapsed) in captures.items():
                stats = capture["native"]
                measurement[arm] = dict(ids=stats["ids"], text=capture["decoding"]["text"], first=stats["seconds"][0],
                                        elapsed=elapsed, rss=native.bounded.prior.peak(capture),
                                        scratch=stats["scratch_bytes"], model_bytes=stats["model_bytes"],
                                        **{k: v for k, v in stats.items() if k.startswith("kv_")})
            rows.append(dict(case=case["case"], input_tokens=len(case["ids"]), gold=case["gold"], order=order,
                             ids_equal=measurement["width16"]["ids"] == measurement["width24"]["ids"],
                             arms=measurement))
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(profile=profile, rows=rows, boundary_cases=len(boundaries),
                                          exact_boundary_logits=sum(row["exact"] for row in boundaries),
                                          total_boundary_logits=sum(row["logits"] for row in boundaries)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        profile, _ = prepare()
        trial.publish(args.receipt, profile)
        print(trial.file_sha(args.receipt), flush=True)
        return 0
    if args.stop_by is None:
        parser.error("a user-authorized time cutoff is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
