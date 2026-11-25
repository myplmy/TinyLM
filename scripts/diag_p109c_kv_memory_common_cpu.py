"""Recheck short and long cache memory against one resident P109C model."""

from argparse import ArgumentParser
import ctypes
from datetime import datetime
import gc
from pathlib import Path

import torch

from scripts import diag_p109c_kv_length_cpu as previous
from scripts import diag_p109c_kv_owner_stream_cpu as stream


TAG = "p109c_kv_memory_common_cpu_20261125"
PROFILE = previous.reference.EVIDENCE / f"{TAG}_profile.json"
OUT = previous.reference.EVIDENCE / f"{TAG}.json"
GROUPS = ("short_fp32", "long_bf16", "long_bf16_owner_stream")
ORDERS = (GROUPS + GROUPS[::-1], GROUPS[::-1] + GROUPS)
CASES = ("final_ko_format_00", "final_en_format_04")


def prepare():
    source = stream.RECORD / "report.json"
    report = previous.completed.read_json(source)
    if report["matched_ids"] != report["requests"] or report["requests"] != 8:
        raise ValueError("a completed parity-passing owner stream is required")
    with_profile, cases = stream.profile()
    if previous.completed.read_json(stream.PROFILE) != with_profile:
        raise ValueError("the verified stream source or profile changed")
    selected = [next(case for case in cases if case["id"] == name) for name in CASES]
    return dict(tag=TAG, cases=list(CASES), orders=[list(order) for order in ORDERS],
                source=previous.reference.file_sha(Path(__file__)),
                prior_experiment=previous.reference.file_sha(source),
                prior_profile=previous.reference.file_sha(stream.PROFILE),
                checkpoint_sha256=previous.reference.CHECKPOINT_SHA256,
                measurement="RSS sampled after each physical visit; identical loaded model; malloc_trim before each request"), selected


@torch.inference_mode()
def run(cases, stamp, cutoff):
    model = stream.model_for("long_bf16")
    tokenizer = previous.completed.load_tokenizer()
    trim = ctypes.CDLL(None).malloc_trim
    trim.argtypes, trim.restype = [ctypes.c_size_t], ctypes.c_int
    peak = 0

    def sample(*_):
        nonlocal peak
        peak = max(peak, previous.memory()["VmRSS"])

    hooks = [layer.register_forward_hook(sample) for layer in model.layers]
    records = {}
    try:
        for case, order in zip(cases, ORDERS, strict=True):
            rows = {arm: [] for arm in GROUPS}
            for arm in order:
                previous.deadline_check(cutoff)
                short = arm == "short_fp32"
                cfg = model.cfg
                cfg.max_seq_len, cfg.kv_dtype = (1024, "fp32") if short else (2048, "bf16")
                owner = stream.OwnerStream(model) if arm == "long_bf16_owner_stream" else model
                gc.collect()
                trim(0)
                before = previous.memory()["VmRSS"]
                peak = before
                row = previous.generate(owner, torch, tokenizer, case["inputs"]["short" if short else "long"], cutoff)
                used = max(peak, row["process"]["VmRSS"])
                rows[arm].append(dict(before=before, sampled_peak=used, growth=used-before,
                                      output=row["metadata"]["generated_ids"], reason=row["metadata"]["finish_reason"],
                                      seconds=row["elapsed_seconds"]))
                del owner
            records[case["id"]] = rows
            print(case["id"], {k: [x["growth"] for x in v] for k, v in rows.items()}, flush=True)
    finally:
        for hook in hooks:
            hook.remove()
    comparisons = {}
    for name, rows in records.items():
        short, standard, candidate = (rows[arm] for arm in GROUPS)
        long_outputs = {(tuple(row["output"]), row["reason"]) for row in standard+candidate}
        growth = {arm: max(row["growth"] for row in values) for arm, values in rows.items()}
        peak = {arm: max(row["sampled_peak"] for row in values) for arm, values in rows.items()}
        comparisons[name] = dict(identical_longs=len(long_outputs) == 1, max_growth=growth, max_sampled_rss=peak,
                                 growth_delta_vs_short=growth[GROUPS[2]]-growth[GROUPS[0]],
                                 growth_delta_vs_same_long=growth[GROUPS[2]]-growth[GROUPS[1]])
    previous.native.publish(OUT, dict(profile_sha256=stamp, comparisons=comparisons, records=records))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    previous.deadline_check(args.stop_by)
    profile, cases = prepare()
    if args.action == "seal":
        if PROFILE.exists():
            parser.error("the fixed profile already exists")
        previous.native.publish(PROFILE, profile)
        print(previous.reference.file_sha(PROFILE), flush=True)
        return
    if (args.profile_sha256 != previous.reference.file_sha(PROFILE) or previous.completed.read_json(PROFILE) != profile
            or OUT.exists()):
        parser.error("run requires the exact sealed profile and a fresh evidence path")
    run(cases, args.profile_sha256, args.stop_by)


if __name__ == "__main__":
    main()
