"""Keep a maximum compatible set of original raw windows before replacing overlaps."""

import argparse
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts import audit_p109c_raw_window_coverage as exposure


training, source, prep = exposure.training, exposure.source, exposure.prep
TAG = "p109c_v2_raw_overlap_repair_cpu_v1_20261124"
RECORD = prep.ROOT / "data_cache/p109c_v2_raw_overlap_repair_20261124"
STRIDE = source.WINDOW + 1


def preserved_windows(raw):
    """Maximize the number retained, then favor earlier training addresses."""
    order = np.argsort(raw, kind="stable")
    ordered = raw[order]
    count = len(order)
    priority = count**2 + 1
    if (priority + count) * count > np.iinfo(np.int64).max:
        raise ValueError("the interval score exceeds the exact integer representation")
    before = np.searchsorted(ordered, ordered - STRIDE, side="right")
    best = np.zeros(count + 1, dtype=np.int64)
    used = np.zeros(count, dtype=np.bool_)
    for i, earlier in enumerate(before):
        with_window = best[earlier] + priority + count - order[i]
        if with_window > best[i]:
            best[i + 1] = with_window
            used[i] = True
        else:
            best[i + 1] = best[i]
    keep = np.zeros(count, dtype=np.bool_)
    cursor = count
    while cursor:
        i = cursor - 1
        if used[i]:
            keep[order[i]] = True
            cursor = int(before[i])
        else:
            cursor = i
    if keep.sum() != best[-1] // priority or np.any(np.diff(np.sort(raw[keep])) < STRIDE):
        raise ValueError("the reconstructed retained set is inconsistent")
    return keep


def replacement_windows(starts, ends, deadline):
    raw = starts.ravel()
    keep = preserved_windows(raw)
    fixed = np.r_[-STRIDE, np.sort(raw[keep]), np.iinfo(np.int64).max]
    edges = np.linspace(0, int(ends[-1]) + 1, source.GROUPS + 1, dtype=np.int64)
    groups = np.searchsorted(edges[1:], raw, side="right")
    cross = source.crossings(raw, ends)
    bins = np.minimum(cross, source.LONG_TAIL)
    rng = np.random.default_rng(source.SEED)
    selected = raw.copy()
    for group, (lo, hi) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        need = np.flatnonzero((groups == group) & ~keep)
        if not len(need):
            continue
        demand = np.bincount(bins[need], minlength=source.LONG_TAIL + 1)
        for offset in rng.permutation(STRIDE):
            if datetime.now(deadline.tzinfo) >= deadline:
                raise TimeoutError("the authorized CPU placement window ended")
            positions = np.arange(lo + offset, hi - STRIDE + 1, STRIDE, dtype=np.int64)
            adjacent = np.searchsorted(fixed[1:-1], positions)
            free = positions[(positions - fixed[adjacent] >= STRIDE)
                             & (fixed[adjacent + 1] - positions >= STRIDE)]
            available = np.minimum(source.crossings(free, ends), source.LONG_TAIL)
            if (np.bincount(available, minlength=source.LONG_TAIL + 1) >= demand).all():
                break
        else:
            raise ValueError(f"the retained intervals do not admit a matching lattice in source range {group}")
        for key in np.flatnonzero(demand):
            wanted = need[bins[need] == key]
            candidates = free[available == key]
            selected[wanted] = candidates[rng.permutation(len(candidates))[:len(wanted)]]
    after = source.crossings(selected, ends)
    if (not np.array_equal(np.minimum(after, source.LONG_TAIL), bins)
            or not np.array_equal(np.searchsorted(edges[1:], selected, side="right"), groups)
            or not np.array_equal(selected[keep], raw[keep]) or (selected == raw).sum() != keep.sum()
            or np.any(np.diff(np.sort(selected)) < STRIDE)):
        raise ValueError("the residual placement changed source composition or retained a collision")
    return selected.reshape(starts.shape), int(keep.sum()), (int(cross.sum()), int(after.sum()))


def shared_positions(a, b):
    unique_a, unique_b = training.unique(a), training.unique(b)
    common = unique_a + unique_b - training.unique(np.r_[a.ravel(), b.ravel()])
    return dict(shared=common, baseline_only=unique_a - common, alternative_only=unique_b - common)


def prepare(deadline):
    contract = prep.read_json(exposure.FULL)
    known = contract["inputs"]
    manifest = source.read_pinned(training.MANIFEST, known["original_manifest_sha256"])
    frozen = prep.read_json(exposure.VAL)
    index = exposure.validation.pair.load_index(Path(frozen["index_profile"]), known["document_index_sha256"])
    files = index["splits"]["train"]
    if (Path(files["binary"]["path"]) != prep.CACHE / "train.bin"
            or manifest["cache"]["files"]["train.bin"] != {k: files["binary"][k] for k in ("bytes", "sha256")}):
        raise ValueError("the exact adopted v1.1 cache and document index are required")
    ends = source.read_array(Path(files["index"]["path"]), files["index"]["sha256"]).astype(np.int64)
    starts = source.read_array(training.MANIFEST.with_name("raw_starts.npy"), manifest["raw_starts_sha256"])
    replaced = source.read_array(training.WINDOWS / "raw_starts.npy", known["stored_npy_sha256"])
    schedule = source.read_array(training.MANIFEST.with_name("schedule.npy"), manifest["schedule_sha256"])
    if (len(ends) != files["documents"] or ends[-1] + 1 != files["tokens"] or (np.diff(ends) <= 0).any()
            or manifest["steps"] != len(schedule) or starts.shape != replaced.shape
            or starts.min() < 0 or starts.max() + STRIDE > files["tokens"]
            or not np.array_equal(np.sort(schedule[:, :, 1][schedule[:, :, 0] == -1]), np.arange(len(starts)))):
        raise ValueError("the whole original training schedule and document bounds must close")

    repaired, kept, boundaries = replacement_windows(starts, ends, deadline)
    if training.unique(repaired) != manifest["raw_tokens"] or training.unique(replaced) != manifest["raw_tokens"]:
        raise ValueError("both alternative schedules must give the full count of unique raw targets")
    draws, unique = exposure.document_counts(repaired, ends)
    stages = []
    for lo, hi in zip(exposure.STAGES[:-1], exposure.STAGES[1:], strict=True):
        values = schedule[lo:hi]
        indices = values[:, :, 1][values[:, :, 0] == -1]
        a, b = starts[indices], repaired[indices]
        stages.append(dict(start=lo + 1, stop=hi, windows=a.size, retained=int(np.count_nonzero(a == b)),
                           positions=shared_positions(a, b)))
    return repaired, dict(status="CPU_MAXIMUM_RETENTION_NONOVERLAP_PLAN", tag=TAG, stages=stages,
                          source_sha256=prep.sha(Path(__file__)), source_manifest_sha256=known["original_manifest_sha256"],
                          schedule_sha256=manifest["schedule_sha256"], old_start_sha256=manifest["raw_starts_sha256"],
                          document_index_sha256=known["document_index_sha256"], source_seed=source.SEED,
                          window_count=starts.size, retained_windows=kept, old_to_repair=shared_positions(starts, repaired),
                          old_to_full_replace=shared_positions(starts, replaced),
                          full_replacement_exact_windows=int(np.count_nonzero(starts == replaced)),
                          minimum_gap=int(np.diff(np.sort(repaired.ravel())).min()), boundary_targets=list(boundaries),
                          target_positions=exposure.document_summary(draws, unique, np.diff(np.r_[0, ends + 1])),
                          full_replacement_profile_sha256=prep.sha(exposure.FULL), optimizer_updates=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or args.stop_by > training.STOP
            or datetime.now(args.stop_by.tzinfo) >= args.stop_by or RECORD.exists()):
        parser.error("the fixed output and authorized CPU interval must be available")
    started = perf_counter()
    positions, report = prepare(args.stop_by)
    RECORD.mkdir()
    path = RECORD / "raw_starts.npy"
    with path.open("xb") as stream:
        np.save(stream, positions, allow_pickle=False)
    result = dict(report, stored_npy_sha256=prep.sha(path), raw_positions_sha256=sha256(positions.tobytes()).hexdigest().upper(),
                  elapsed_seconds=perf_counter() - started)
    training.native.publish(RECORD / "profile.json", result)
    print(result["status"], result["retained_windows"], result["window_count"], result["old_to_repair"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
