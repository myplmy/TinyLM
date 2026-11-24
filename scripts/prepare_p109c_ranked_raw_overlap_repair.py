"""Rank compatible replacements by retained original raw target positions."""

import argparse
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts import prepare_p109c_repair_raw_overlaps as repair


training, source, prep = repair.training, repair.source, repair.prep
exposure = repair.exposure
TAG = "p109c_v2_ranked_raw_overlap_repair_cpu_v1_20261124"
RECORD = prep.ROOT / "data_cache/p109c_v2_ranked_raw_overlap_repair_20261124"
OFFSETS = 24
STRIDE = repair.STRIDE


def original_coverage(starts):
    """Return a vectorized count of original raw target positions inside windows."""
    begin = np.sort(starts.ravel()) + 1
    stop = begin + source.WINDOW
    first = np.flatnonzero(np.r_[True, begin[1:] > stop[:-1]])
    stops = stop[np.r_[first[1:] - 1, len(begin) - 1]]
    begins = begin[first]
    prefix = np.r_[0, np.cumsum(stops - begins)]
    next_start = np.r_[begins, np.iinfo(np.int64).max]

    def integral(coordinates):
        index = np.searchsorted(stops, coordinates, side="right")
        return prefix[index] + np.maximum(0, coordinates - next_start[index])

    def count(positions):
        begin = positions + 1
        return integral(begin + source.WINDOW) - integral(begin)

    return count


def ranked_windows(starts, reference, ends, deadline):
    raw, incumbent = starts.ravel(), reference.ravel()
    kept = raw == incumbent
    if not np.array_equal(kept, repair.preserved_windows(raw)):
        raise ValueError("the exact maximum-retention set must come from the previous proof")
    fixed = np.r_[-STRIDE, np.sort(raw[kept]), np.iinfo(np.int64).max]
    edges = np.linspace(0, int(ends[-1]) + 1, source.GROUPS + 1, dtype=np.int64)
    groups = np.searchsorted(edges[1:], raw, side="right")
    classes = np.minimum(source.crossings(raw, ends), source.LONG_TAIL)
    rng = np.random.default_rng(source.SEED)
    replacements = incumbent.copy()
    count = original_coverage(raw)
    gains = []
    for group, (lo, hi) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        needed = np.flatnonzero((groups == group) & ~kept)
        if not len(needed):
            gains.append(0)
            continue
        by_class = [needed[classes[needed] == key] for key in range(source.LONG_TAIL + 1)]
        demand = np.array([len(indices) for indices in by_class])
        initial = best_score = int(count(incumbent[needed]).sum())
        best = [np.sort(incumbent[want]) for want in by_class]
        for offset in rng.permutation(STRIDE)[:OFFSETS]:
            if datetime.now(deadline.tzinfo) >= deadline:
                raise TimeoutError("the authorized CPU placement window ended")
            positions = np.arange(lo + offset, hi - STRIDE + 1, STRIDE, dtype=np.int64)
            adjacent = np.searchsorted(fixed[1:-1], positions)
            free = positions[(positions - fixed[adjacent] >= STRIDE)
                             & (fixed[adjacent + 1] - positions >= STRIDE)]
            bins = np.minimum(source.crossings(free, ends), source.LONG_TAIL)
            if (np.bincount(bins, minlength=len(demand)) < demand).any():
                continue
            scores = count(free)
            chosen, score = [], 0
            for key, size in enumerate(demand):
                if not size:
                    chosen.append(free[:0])
                    continue
                where = np.flatnonzero(bins == key)
                ranking = np.argsort(-scores[where], kind="stable")[:size]
                top = where[ranking]
                chosen.append(np.sort(free[top]))
                score += int(scores[top].sum())
            if score > best_score:
                best, best_score = chosen, score
        for wanted, selected in zip(by_class, best, strict=True):
            ordered = wanted[np.argsort(raw[wanted], kind="stable")]
            replacements[ordered] = selected
        gains.append(best_score - initial)
    crossings = source.crossings(replacements, ends)
    if (np.any(np.diff(np.sort(replacements)) < STRIDE) or not np.array_equal(replacements == raw, kept)
            or not np.array_equal(np.searchsorted(edges[1:], replacements, side="right"), groups)
            or not np.array_equal(np.minimum(crossings, source.LONG_TAIL), classes)
            or int(count(replacements).sum() - count(incumbent).sum()) != sum(gains)):
        raise ValueError("the ranked replacements violate the retained windows or grouped source contract")
    return replacements.reshape(starts.shape), gains, int(crossings.sum())


def prepare(deadline):
    prior_path = repair.RECORD / "profile.json"
    prior = prep.read_json(prior_path)
    manifest = source.read_pinned(training.MANIFEST, prior["source_manifest_sha256"])
    starts = source.read_array(training.MANIFEST.with_name("raw_starts.npy"), prior["old_start_sha256"])
    schedule = source.read_array(training.MANIFEST.with_name("schedule.npy"), prior["schedule_sha256"])
    reference = source.read_array(repair.RECORD / "raw_starts.npy", prior["stored_npy_sha256"])
    val = prep.read_json(exposure.VAL)
    index = exposure.validation.pair.load_index(Path(val["index_profile"]), prior["document_index_sha256"])
    train = index["splits"]["train"]
    corpus = prep.CACHE / "train.bin"
    ends = source.read_array(Path(train["index"]["path"]), train["index"]["sha256"]).astype(np.int64)
    if (prior["status"] != "CPU_MAXIMUM_RETENTION_NONOVERLAP_PLAN" or Path(train["binary"]["path"]) != corpus
            or prior["source_sha256"] != prep.sha(Path(repair.__file__))
            or manifest["cache"]["files"]["train.bin"] != {k: train["binary"][k] for k in ("bytes", "sha256")}
            or starts.shape != reference.shape or len(ends) != train["documents"] or ends[-1]+1 != train["tokens"]):
        raise ValueError("the previous unchanged-maximum layout and source index are required")

    ranked, gains, boundaries = ranked_windows(starts, reference, ends, deadline)
    paired = repair.shared_positions(starts, ranked)
    if (training.unique(ranked) != manifest["raw_tokens"]
            or paired["shared"] - prior["old_to_repair"]["shared"] != sum(gains)):
        raise ValueError("the ranked result must conserve exposure and recover the measured position gain")
    draws, unique = exposure.document_counts(ranked, ends)
    lengths = np.diff(np.r_[0, ends + 1])
    stamp = training.native.file_stamp(corpus)
    if exposure.validation.pair.documents.pin(corpus) != train["binary"]:
        raise ValueError("the approved distribution source differs from the sealed TRAIN file")
    raw = np.memmap(corpus, mode="r", dtype="<u2")
    total = np.zeros(exposure.VOCAB, dtype=np.int64)
    stages = []
    for phase in prior["stages"]:
        batch = schedule[phase["start"]-1:phase["stop"]]
        indices = batch[:, :, 1][batch[:, :, 0] == -1]
        a, b = starts[indices].ravel(), ranked[indices].ravel()
        changed = a != b
        delta = exposure.counts_for(raw, b[changed], deadline) - exposure.counts_for(raw, a[changed], deadline)
        total += delta
        stages.append(dict(start=phase["start"], stop=phase["stop"], retained=phase["retained"], windows=len(a),
                           vocabulary_total_variation=float(np.abs(delta).sum() / (2 * len(a) * source.WINDOW))))
    if stamp != training.native.file_stamp(corpus) or total.sum() != 0:
        raise ValueError("the matched raw token counts or approved cache changed")
    return ranked, dict(status="CPU_RANKED_MAXIMUM_RETENTION_NONOVERLAP_PLAN", tag=TAG,
                        source_sha256=prep.sha(Path(__file__)), prior_profile_sha256=prep.sha(prior_path),
                        same_schedule_sha256=prior["schedule_sha256"], retained_windows=prior["retained_windows"],
                        window_count=prior["window_count"], original_position_recovery=sum(gains),
                        source_ranges_improved=sum(delta > 0 for delta in gains), examined_offsets=OFFSETS,
                        old_to_ranked=paired, boundary_targets=[prior["boundary_targets"][0], boundaries],
                        target_positions=exposure.document_summary(draws, unique, lengths),
                        vocabulary_total_variation=float(np.abs(total).sum() / (2 * manifest["raw_tokens"])),
                        stages=stages, optimizer_updates=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
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
    print(result["status"], result["old_to_ranked"], result["original_position_recovery"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
