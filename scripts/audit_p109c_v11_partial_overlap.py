"""Find long contiguous TRAIN matches in admitted v1.1 validation documents."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np

from scripts import eval_p109c_completed as evaluation
from scripts import run_p109c_scratch330 as entry


ANCHOR, MIN_VAL, CHUNK = 32, 128, 4_194_304
LOW_BITS = np.uint64(2**20 - 1)
HASH_MULTIPLIER = np.uint64(11400714819323198485)


def keys(data, starts):
    code = data[starts].astype(np.uint64)
    for index in (1, 2, 3):
        code <<= np.uint64(15)
        code |= data[starts + index]
    suffix = (data[starts + 4].astype(np.uint64) << np.uint64(15)) | data[starts + 5]
    return code ^ (suffix * HASH_MULTIPLIER)


def split(receipt):
    files = [receipt[key] for key in ("binary", "index")]
    for value in files:
        path = evaluation.regular_file(Path(value["path"]))
        if (path.stat().st_size != value["bytes"] or evaluation.core6.digest(path) != value["sha256"]):
            raise ValueError("the admitted split binary or document index changed")
    tokens = np.memmap(files[0]["path"], mode="r", dtype="<u2")
    ends = np.load(files[1]["path"], mmap_mode="r", allow_pickle=False)
    starts = np.r_[0, ends[:-1].astype(np.int64) + 1]
    if (len(tokens), len(ends), int(ends[-1])) != (receipt["tokens"], receipt["documents"], len(tokens)-1):
        raise ValueError("the exact length and document count differ from the admission receipt")
    return tokens, starts, ends


def agreement(left, right):
    different = np.flatnonzero(left != right)
    return int(different[0]) if different.size else len(left)


def extent(train, val, a, b, t_start, t_end, v_start, v_end):
    before = min(a-t_start, b-v_start)
    after = min(t_end-a, v_end-b)
    left = agreement(train[a-before:a][::-1], val[b-before:b][::-1])
    right = agreement(train[a:a+after], val[b:b+after])
    return a-left, b-left, left+right


def scan(train, val, cutoff):
    t, t_start, t_end = train
    v, v_start, v_end = val
    v_lengths = v_end - v_start
    eligible = np.flatnonzero(v_lengths >= MIN_VAL)
    if not eligible.size:
        raise ValueError("the admitted validation split has no documents in the requested length scope")
    anchors = v_start[eligible] + (v_lengths[eligible]-ANCHOR)//2
    anchor_keys = keys(v, anchors)
    directory = {}
    for doc, position, code in zip(eligible, anchors, anchor_keys, strict=True):
        directory.setdefault(int(code), []).append((int(doc), int(position)))
    sorted_keys = np.asarray(sorted(directory), dtype=np.uint64)
    lookup = np.zeros(int(LOW_BITS)+1, dtype=bool)
    lookup[sorted_keys & LOW_BITS] = True
    matches, candidates = [], 0
    for low in range(0, len(t)-5, CHUNK):
        if time.time() >= cutoff:
            raise TimeoutError("the authorized CPU window elapsed before the complete scan")
        high = min(len(t)-5, low+CHUNK)
        local = np.arange(low, high, dtype=np.int64)
        code = keys(t, local)
        filtered = np.flatnonzero(lookup[code & LOW_BITS])
        # Search in a sorted table only after rejecting most starts cheaply.
        values = code[filtered]
        indices = np.minimum(np.searchsorted(sorted_keys, values), len(sorted_keys)-1)
        hits = filtered[sorted_keys[indices] == values]
        train_positions = hits + low
        train_docs = np.searchsorted(t_end, train_positions, side="left")
        candidates += len(hits)
        for td, tp, found in zip(train_docs, train_positions, code[hits], strict=True):
            if tp+ANCHOR > int(t_end[td]):
                continue
            for vd, vp in directory[int(found)]:
                if not np.array_equal(t[tp:tp+ANCHOR], v[vp:vp+ANCHOR]):
                    continue
                ts, vs, length = extent(t, v, int(tp), vp, int(t_start[td]), int(t_end[td]),
                                        int(v_start[vd]), int(v_end[vd]))
                if length*5 >= int(v_lengths[vd])*4:
                    matches.append(dict(train_ordinal=int(td), val_ordinal=vd, train_start=ts, val_start=vs,
                        matched_tokens=length, val_document_tokens=int(v_lengths[vd]),
                        train_document_tokens=int(t_end[td]-t_start[td])))
        if low // CHUNK % 32 == 31:
            print("P109C_V11_OVERLAP_SCAN", high, candidates, len(matches), flush=True)
    return dict(train_positions_scanned=len(t)-5, val_documents_total=len(v_end),
                val_documents_checked=len(eligible), candidate_anchor_hits=candidates,
                matched_document_pairs=len(matches), matched_val_documents=len({row["val_ordinal"] for row in matches}),
                matches=matches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--index-sha256", required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None:
        parser.error("the scoped deadline requires a UTC offset")
    raw = entry.manifest_bytes(args.index.absolute(), args.index_sha256)
    profile = json.loads(raw)
    if profile["schema"] != "P107_V11_BINARY_DOCUMENTS_V1" or set(profile["splits"]) != {"train", "val"}:
        raise ValueError("the adopted v1.1 document index is required")
    started = time.monotonic()
    files = [Path(receipt[key]["path"]) for receipt in profile["splits"].values() for key in ("binary", "index")]
    stamps = [entry.file_stamp(path) for path in files]
    train, val = (split(profile["splits"][name]) for name in ("train", "val"))
    result = scan(train, val, args.stop_by.timestamp())
    if [entry.file_stamp(path) for path in files] != stamps:
        raise ValueError("a sealed split changed during the overlap scan")
    args.record.mkdir(exist_ok=False)
    entry.publish(args.record / "report.json", dict(index_sha256=entry.digest(args.index_sha256),
        source_release_sha256=profile["source_release_sha256"], validation_minimum_body_tokens=MIN_VAL,
        threshold_validation_fraction=.8, anchor_tokens=ANCHOR, elapsed_seconds=time.monotonic()-started,
        scope="EXACT_CONTIGUOUS_MATCH_ONLY_NO_EDITED_OR_SEMANTIC_NEAR_MATCH_CLAIM", **result))
    print("P109C_V11_OVERLAP_COMPLETE", result["matched_document_pairs"], result["matched_val_documents"], flush=True)


if __name__ == "__main__":
    main()
