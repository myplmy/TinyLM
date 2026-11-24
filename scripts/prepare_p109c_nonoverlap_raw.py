"""Prepare matched, nonoverlapping raw windows from the sealed P109C source."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np


WINDOW = 1024
SEED = 20261123
GROUPS = 64
LONG_TAIL = 7


def read_pinned(path, stamp):
    data = path.read_bytes()
    if sha256(data).hexdigest().upper() != stamp.upper():
        raise ValueError(f"the frozen source differs: {path}")
    return json.loads(data)


def read_array(path, stamp):
    if sha256(path.read_bytes()).hexdigest().upper() != stamp.upper():
        raise ValueError(f"the frozen array differs: {path}")
    return np.load(path, allow_pickle=False)


def crossings(starts, ends):
    return np.searchsorted(ends, starts + WINDOW, side="left") - np.searchsorted(ends, starts, side="left")


def assign(starts, ends):
    raw = starts.ravel()
    source_edges = np.linspace(0, ends[-1]+1, GROUPS+1, dtype=np.int64)
    ranges = np.searchsorted(source_edges[1:], raw, side="right")
    before = crossings(raw, ends)
    bins = np.minimum(before, LONG_TAIL)
    rng = np.random.default_rng(SEED)
    selected = np.full_like(raw, -1)
    stride = WINDOW + 1
    for group, (lo, hi) in enumerate(zip(source_edges[:-1], source_edges[1:], strict=True)):
        demand = np.bincount(bins[ranges == group], minlength=LONG_TAIL+1)
        for offset in rng.permutation(stride)[:64]:
            available = np.arange(lo+offset, hi-stride+1, stride, dtype=np.int64)
            available_bins = np.minimum(crossings(available, ends), LONG_TAIL)
            if (np.bincount(available_bins, minlength=LONG_TAIL+1) >= demand).all():
                break
        else:
            raise ValueError(f"no local phase supplies the requested boundary bins for range {group}")
        for key in range(LONG_TAIL+1):
            indices = np.flatnonzero((ranges == group) & (bins == key))
            positions = available[available_bins == key]
            selected[indices] = positions[rng.permutation(len(positions))[:len(indices)]]
    after = crossings(selected, ends)
    if ((selected < 0).any() or (np.diff(np.sort(selected)) < stride).any()
            or not np.array_equal(np.searchsorted(source_edges[1:], selected, side="right"), ranges)
            or not np.array_equal(np.minimum(after, LONG_TAIL), bins)):
        raise ValueError("new windows overlap or change the assigned source and boundary bins")
    return selected.reshape(starts.shape).astype("<i8", copy=False), int(before.sum()), int(after.sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--document-index", required=True, type=Path)
    parser.add_argument("--document-index-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    options = parser.parse_args()
    manifest = read_pinned(options.manifest, options.manifest_sha256)
    indexed = read_pinned(options.document_index, options.document_index_sha256)["splits"]["train"]
    binary = indexed["binary"]
    if (manifest["cache"]["files"]["train.bin"] != {key: binary[key] for key in ("bytes", "sha256")}
            or Path(binary["path"]).parent != Path(manifest["cache"]["cache_dir"])):
        raise ValueError("the existing raw tokens and document boundaries must refer to the same release")
    source = options.manifest.with_name("raw_starts.npy")
    starts = read_array(source, manifest["raw_starts_sha256"])
    ends = read_array(Path(indexed["index"]["path"]), indexed["index"]["sha256"]).astype(np.int64)
    if (starts.dtype != np.dtype("<i8") or starts.ndim != 2 or starts.shape[1] != 4
            or starts.size * WINDOW != manifest["raw_tokens"] or starts.min() < 0
            or len(ends) != indexed["documents"] or ends[-1]+1 != indexed["tokens"]
            or (np.diff(ends) <= 0).any() or starts.max()+WINDOW > ends[-1]):
        raise ValueError("the raw windows or document boundaries do not close their exact extents")
    replacement, before, after = assign(starts, ends)
    options.record.mkdir(exist_ok=False)
    output = options.record / "raw_starts.npy"
    with output.open("xb") as stream:
        np.save(stream, replacement, allow_pickle=False)
    identity = sha256(replacement.tobytes()).hexdigest().upper()
    file_sha = sha256(output.read_bytes()).hexdigest().upper()
    report = dict(status="NONOVERLAP_PROFILE_READY", original_manifest_sha256=options.manifest_sha256.upper(),
                  original_starts_sha256=manifest["raw_starts_sha256"],
                  document_index_sha256=options.document_index_sha256.upper(),
                  raw_positions_sha256=identity, stored_npy_sha256=file_sha,
                  seed=SEED, source_ranges=GROUPS, last_boundary_bin=LONG_TAIL,
                  unique_input_tokens=replacement.size*WINDOW, baseline_boundary_targets=before,
                  candidate_boundary_targets=after, minimum_span_between_starts=WINDOW+1,
                  source_sha256=sha256(Path(__file__).read_bytes()).hexdigest().upper(),
                  model_training_or_evaluation_run=False)
    with (options.record / "profile.json").open("x", encoding="utf-8") as stream:
        print(json.dumps(report, indent=2), file=stream)
    print("P109C_RAW_NONOVERLAP", identity, file_sha, flush=True)


if __name__ == "__main__":
    main()
