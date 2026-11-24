"""Compare online query group widths in the same small G4 K4/V3 runtime."""

import argparse
from contextlib import ExitStack
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p077_g4_output_byte_request as request
from scripts import diag_p077_grounded_near_native as native


TAG = "p077_g4_wide_query_prefill_cpu_v1_20261121"
OUT = native.ROPE_OUT.with_name(TAG)
ATTENTION = Path(__file__).with_name("p077_g4_grouped_attention.hpp")
trial = native.trial
ARMS = {"full2": 2, "online2": 2, "online4": 4, "online8": 8}
ORDERS = (
    ("full2", "online2", "online8", "online4"),
    ("online2", "online4", "full2", "online8"),
    ("online4", "online8", "online2", "full2"),
    ("online8", "full2", "online4", "online2"),
)
CASES = (0, 4, 3, 7)
BOUNDARIES = (1, 7, 63, 64, 65, 71, 72, 73, 127, 128, 129)


def render(source, name):
    if name == "full2":
        return source
    header = ATTENTION.read_bytes()
    swap = native.port.replace_once
    header = swap(header, b"    static constexpr int PrefillQueries = KvHeads;",
                  f"    static constexpr int PrefillQueries = {ARMS[name]};\n".encode()
                  + b"    static constexpr int ScoreHeads = std::max(Heads, PrefillQueries * HeadsPerKv);")
    header = swap(header, b"scores_(Heads * score_rows_)", b"scores_(ScoreHeads * score_rows_)")
    old_arrays = b"std::array<float, Heads> largest, denom{};"
    if header.count(old_arrays) != 3:
        raise ValueError("the attention reduction workspace changed")
    header = header.replace(old_arrays, b"std::array<float, ScoreHeads> largest, denom{};")
    source = swap(source, b'#include "p077_g4_grouped_attention.hpp"', header)
    return swap(source, b"attention_workspace(capacity)", b"attention_workspace(capacity, true)")


def build(source, name):
    candidate = render(source, name)
    if name == "full2":
        receipt = trial.read_json(native.ROPE_OUT / "tile_rope_2048" / "compiler.json")
        files = [Path(entry["path"]) for entry in receipt["binaries"]["64"]]
        if (receipt["source_sha256"] == sha256(candidate).hexdigest().upper()
                and all(path.is_file() and native.base.SHA(path) == entry["sha256"]
                        for path, entry in zip(files, receipt["binaries"]["64"], strict=True))):
            trial.publish(OUT / "original_compiler.json", receipt)
            return files
    folder = OUT / name
    folder.mkdir()
    with patch.object(native.bounded, "OUT", folder):
        return native.bounded.build(candidate, caps=(64,))[64]


def rounding_probe(source, arm):
    engine = OUT / f"rounding_{arm}.cpp"
    fixture = rb"""
#undef main
int main() {
    GroupedInt8Cache cache(64, 0, 4, 3);
    GroupedBlockAttention work(64, USE_ONLINE);
    std::array<float, 3 * D> q{}, result{};
    std::array<float, 3 * Kv> k{}, v{};
    v[0] = 1.F;
    v[Kv] = 2.F;
    v[2 * Kv] = -3.F;
    work.compute_prefill(cache, 0, 0, q.data(), k.data(), v.data(), 1, 3, result.data());
    std::printf("%.12g %.12g %.12g\n", double(result[0]), double(result[D]), double(result[2 * D]));
    return 0;
}
"""
    full = b"#define main original_request_cli\n" + render(source, arm)
    engine.write_bytes(full + fixture.replace(b"USE_ONLINE", b"false" if arm == "full2" else b"true"))
    exe = OUT / f"rounding_{arm}"
    native.native_test.compile_probe(engine, exe, ("-DP109_PREFILL_TOKENS=64",))
    row = [float(x) for x in subprocess.check_output([exe], timeout=20).split()]
    if len(row) != 3 or not np.isfinite(row).all():
        raise ValueError("the three visible rows should have finite outputs")
    return row


def restored_rows(length, width):
    return sum(past * math.ceil(min(length-past, 64)/width) for past in range(0, length, 64))


def prepare():
    profile, inputs = request.prepare()
    cases = inputs[2]
    if len(cases) != 8 or [cases[i]["language"] for i in CASES] != ["ko", "en", "ko", "en"]:
        raise ValueError("requires the four balanced sealed text cases")
    result = dict(tag=TAG, profile=profile, order=[list(row) for row in ORDERS], cases=list(CASES),
                  lengths=[len(cases[i]["ids"]) for i in CASES], boundaries=list(BOUNDARIES),
                  source_sha256=trial.file_sha(Path(__file__)), header_sha256=trial.file_sha(ATTENTION))
    return result, inputs


def compare_boundaries(binaries, model_fd, ids):
    rows = []
    for length in BOUNDARIES:
        control, _, left = native.token_request(binaries["full2"][0], model_fd, ids[:length], 2, trace=True)
        arms = {}
        for arm in ("online2", "online4", "online8"):
            result, _, right = native.token_request(binaries[arm][0], model_fd, ids[:length], 2, trace=True)
            # The second token is only compared if it followed the same first token.
            common = min(len(result["ids"]), len(control["ids"]))
            if not common:
                raise ValueError("the trace did not generate a token")
            values = 32768 * (common if result["ids"][0] == control["ids"][0] else 1)
            if (right is None or left is None or min(len(right),len(left))<values
                    or not np.isfinite(right).all() or not np.isfinite(left).all()):
                raise ValueError("the boundary trace did not return finite vocabulary scores")
            arms[arm] = dict(ids=result["ids"], matched_control=result["ids"]==control["ids"],
                             common_values=values, max_abs=float(np.max(np.abs(left[:values]-right[:values]))))
        rows.append(dict(length=length, control=control["ids"], arms=arms))
    return rows


def run(profile, stop_by):
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or OUT.exists() or stop_by.tzinfo is None
            or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds()<450
            or stop_by>request.byte_table.AUTHORIZATION_END):
        raise ValueError("requires a fresh CPU comparison in the authorized window")
    checked, (tok,special,queries,refs,previous,asset) = prepare()
    if checked != profile:
        raise ValueError("the source or inputs changed")
    cpus = set(previous["cpus"])&os.sched_getaffinity(0)
    if not cpus:
        raise ValueError("no previously approved CPU lanes remain")
    cpu = max(cpus)
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    stop = (special["<|im_end|>"], tok.token_to_id("<eos>"))
    original = native.tiled_rope.render(native.source_for(2048,3,*stop))
    binaries = {arm:build(original,arm) for arm in ARMS}
    rounding = {arm:rounding_probe(original,arm) for arm in ARMS}
    trial.publish(OUT / "rounding.json", rounding)
    wrapper, blobs = native.text_codec(OUT)
    request.render_decoder(wrapper, asset)
    with ExitStack() as stack:
        with patch.object(request, "OUT", OUT):
            fd = request.pack_model(stack, profile["profile"]["native"]["state_sha256"], previous)
        bind = [fd]
        for i, blob in enumerate(blobs):
            codec = native.base.memfile(f"p077-wide-decode-{i}")
            stack.callback(os.close, codec)
            native.bounded.text.store(codec, blob)
            fcntl.fcntl(codec, native.base.prior.DEPLOY.F_ADD_SEALS, native.base.prior.DEPLOY.SEALS)
            bind.append(codec)
        edges = compare_boundaries(binaries, fd, queries[CASES[0]]["ids"])
        trial.publish(OUT / "boundaries.json", edges)
        print(json.dumps(dict(boundaries=len(edges))),flush=True)
        rows = []
        for j,(case,arms) in enumerate(zip(CASES,ORDERS,strict=True)):
            for order,arm in enumerate(arms):
                if (OUT / "STOP").exists() or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds()<160:
                    raise TimeoutError("the comparison stopped at the deadline")
                path = OUT / f"case_{case}_{arm}.json"
                caller = queries[case]
                stats = native.port.request(binaries[arm][1], bind, caller["text"].encode("utf-8"), path,
                                            refs[case], wrapper=wrapper)
                raw = trial.read_json(path)["native"]
                row = dict(case=case, language=caller["language"], arm=arm, lane_order=j, arm_order=order,
                           first_seconds=raw["seconds"][0], ids=raw["ids"], prefill_rss=raw["prefilled"]["rss"],
                           cached_rows_per_visit=restored_rows(len(caller["ids"]),ARMS[arm]), **stats)
                rows.append(row)
                print(json.dumps(row),flush=True)
    trial.publish(OUT / "report.json", dict(profile=profile, cpu=cpu, rows=rows,
                  boundaries_sha256=trial.file_sha(OUT / "boundaries.json"),
                  rounding_sha256=trial.file_sha(OUT / "rounding.json")))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check","run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("run requires the sealed comparison and authorized cutoff")
    return run(plan,args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
