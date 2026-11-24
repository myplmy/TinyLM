"""Count exact held-out local context exposure in three sealed raw schedules."""

import argparse
from datetime import datetime
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts import eval_p107_v11_causal_groups_cpu as validation
from scripts import p109c_native_curriculum as curriculum
from scripts import run_p109c_v2_raw_nonoverlap as original


PREP, NATIVE = curriculum.prep, curriculum.supervised.native
VAL = PREP.ROOT / "data_cache/p107_v11_causal_group_profile_v1_20261121.json"
VAL_RUN = PREP.EVIDENCE / "p109c_v2_raw_nonoverlap_recovery_same_raw_val_cpu_v1_20261124/report.json"
BITS = 15
CHUNK = 4096


def packed4(a):
    return (((a[:, :-3] << BITS) | a[:, 1:-2]) << (2 * BITS)) | (a[:, 2:-1] << BITS) | a[:, 3:]


def frames():
    profile = PREP.read_json(VAL)
    run = PREP.read_json(VAL_RUN)
    if (run["status"] != "SAME_DOCUMENT_VAL_COMPLETE" or run["profile_sha256"] != PREP.sha(VAL)
            or PREP.sha(Path(validation.__file__)) != profile["source_sha256"]):
        raise ValueError("the same completed and frozen raw validation is required")
    index = validation.pair.load_index(Path(profile["index_profile"]), profile["index_sha256"])
    windows = validation.validation(index)
    if validation.frame_sha(windows) != run["window_sha256"]:
        raise ValueError("the actual evaluation document windows changed")
    output = []
    for tokens, documents in windows:
        x = tokens.numpy().astype(np.uint64)
        d = documents.numpy()
        mask = (d[:, :-3] == d[:, 1:-2]) & (d[:, :-3] == d[:, 2:-1]) & (d[:, :-3] == d[:, 3:])
        output.append(packed4(x)[mask])
    keys = np.concatenate(output)
    terminal = keys & ((1 << BITS) - 1)
    categories = {name: np.isin(terminal, profile["groups"][name]) for name in ("hangul", "latin", "decimal")}
    categories["all"] = np.ones(len(keys), dtype=bool)
    return keys, categories, run["window_sha256"]


def collect_counts(keys, rows, counts):
    selected = np.searchsorted(keys, rows)
    within = selected < len(keys)
    indexes, values = selected[within], rows[within]
    found = keys[indexes] == values
    counts += np.bincount(indexes[found], minlength=len(keys))


def exposure(bundle, mode, keys4, keys3, deadline):
    choice = curriculum.select_raw_windows(bundle, mode)
    counts4, counts3 = np.zeros(len(keys4), dtype=np.int64), np.zeros(len(keys3), dtype=np.int64)
    starts = bundle.starts.ravel()
    offsets = np.arange(PREP.WIDTH + 1, dtype=np.int64)
    for start in range(0, len(starts), CHUNK):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("the authorized raw-context inspection reached its cutoff")
        block = bundle.raw[starts[start:start + CHUNK, None] + offsets].astype(np.uint64)
        joined = packed4(block).ravel()
        collect_counts(keys4, joined, counts4)
        collect_counts(keys3, joined >> BITS, counts3)
    bundle.unchanged()
    return choice, counts4, counts3


def group_masks(categories, base, candidate):
    result = {}
    for name, mask in categories.items():
        a, b = base[mask], candidate[mask]
        a_seen, b_seen = a > 0, b > 0
        result[name] = dict(target_positions=len(a), seen_both=int((a_seen & b_seen).sum()),
                            seen_v2_only=int((a_seen & ~b_seen).sum()), seen_candidate_only=int((b_seen & ~a_seen).sum()),
                            seen_neither=int((~a_seen & ~b_seen).sum()),
                            exposure_sum_v2=int(a.sum()), exposure_sum_candidate=int(b.sum()),
                            median_v2=float(np.median(a)), median_candidate=float(np.median(b)))
    return result


def measure(deadline):
    stamp = perf_counter()
    targets, categories, window_sha = frames()
    keys4, rev4 = np.unique(targets, return_inverse=True)
    keys3, rev3 = np.unique(targets >> BITS, return_inverse=True)
    training = PREP.read_json(original.WINDOWS / "profile.json")["original_manifest_sha256"]
    bundle = original.mixed.Bundle(original.MANIFEST, training)
    summaries, sources, base = {}, {}, None
    for mode in curriculum.ORIGINAL_CHOICES:
        choice, four, three = exposure(bundle, mode, keys4, keys3, deadline)
        if base is None:
            base = four, three
        summaries[mode] = dict(context_and_target=group_masks(categories, base[0][rev4], four[rev4]),
                               context_without_target=group_masks(categories, base[1][rev3], three[rev3]))
        sources[mode] = choice
        print(mode, summaries[mode]["context_and_target"]["all"], flush=True)
    return dict(status="EXACT_RAW_CONTEXT_EXPOSURE_CPU_COMPLETE", val_window_sha256=window_sha,
                val_profile_sha256=PREP.sha(VAL), training_manifest_sha256=bundle.digest, target_positions=len(targets),
                exact_context_and_target_types=len(keys4), exact_context_types=len(keys3),
                raw_sources=sources, model_runs=0, seconds=perf_counter()-stamp, results=summaries,
                source_sha256=PREP.sha(Path(__file__).resolve()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None:
        parser.error("the experimental cutoff requires an explicit time zone")
    result = measure(args.stop_by)
    NATIVE.publish(args.output.absolute(), result)
    print(result["status"], result["target_positions"], flush=True)


if __name__ == "__main__":
    main()
