"""Audit English Aya SODA input dialogues against the pinned Ai2 release."""

import argparse
from collections import Counter
from contextlib import ExitStack, contextmanager
from hashlib import sha256
import json
from pathlib import Path
from os import fstat
from unicodedata import normalize

from scripts.p106b_soda_dialogue_view import input_dialogue_view


REPO = "allenai/soda"
REVISION = "fdc848ab0183208ea7808206c91c724414d0a071"
RELEASE = {
    "train": (1191582, "b21314575fdc4cbf9fc74f7af4854d55fba8cc9ba72f2f3791ae2df8b23032c4"),
    "valid": (146346, "3e813e5b14c4edca5849cb7922f9c38568ecb71f27931a7c4c29ec1160bd0d1c"),
    "test": (148968, "edd0a57b460fa7faa3782b332327f3a4bc9681dcaaec88e77727c47fd5870180"),
}
COLUMNS = ("split", "original_index", "narrative", "speakers", "dialogue")
SPLIT_BITS = {part: 1 << i for i, part in enumerate(RELEASE)}


def hash_json(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest().upper()


def text_key(value):
    return normalize("NFC", value.strip()) if isinstance(value, str) else ""


def dialogue_key(narrative, turns):
    return hash_json([narrative, turns])


def aya_probes(rows):
    result = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] in result:
            raise ValueError("Supply distinct, explicit Aya row IDs")
        info = dict(aya_id=row["id"], aya_row_sha256=hash_json(row), status="HOLD_UNSUPPORTED_AYA_INPUT")
        result[row["id"]] = info
        try:
            view = input_dialogue_view(row)
        except ValueError:
            continue
        narrative = text_key(row["targets"])
        if narrative:
            turns = [[text_key(part) for part in block.split(": ", 1)] for block in view.dialogue.split("\n\n")]
            info.update(narrative=narrative, content_sha256=dialogue_key(narrative, turns))
    if not result:
        raise ValueError("At least one explicit Aya row is required")
    return list(result.values())


def read_aya(path, expected_sha256):
    stamp = sha256()
    with path.open("rb") as stream:
        def rows():
            for line in stream:
                stamp.update(line)
                value = json.loads(line)
                yield value.get("raw_row", value) if isinstance(value, dict) else value

        result = aya_probes(rows())
    if stamp.hexdigest() != expected_sha256.lower():
        raise ValueError("The declared local Aya JSONL digest disagrees")
    return result


def _fingerprint(stream):
    state = fstat(stream.fileno())
    return state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns, state.st_ctime_ns


@contextmanager
def pinned_rows(path, count, expected_sha256):
    import pyarrow.parquet as pq

    with path.open("rb") as stream:
        before = _fingerprint(stream)
        h = sha256()
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
        if h.hexdigest() != expected_sha256 or _fingerprint(stream) != before:
            raise ValueError(f"Release SHA-256 differs for {path.name}")
        stream.seek(0)
        parquet = pq.ParquetFile(stream)
        try:
            if parquet.metadata.num_rows != count or not set(COLUMNS) <= set(parquet.schema_arrow.names):
                raise ValueError(f"Release row count or columns differ for {path.name}")
            batches = parquet.iter_batches(8192, columns=list(COLUMNS), use_threads=False)
            yield (row for batch in batches for row in batch.to_pylist())
            if _fingerprint(stream) != before:
                raise ValueError(f"Release file changed during scan: {path.name}")
        finally:
            parquet.close()


def match_exact(probes, partitions):
    """Scan all three split streams before resolving any requested Aya keys."""
    if set(partitions) != set(RELEASE):
        raise ValueError("All official split streams are necessary for root grouping")
    wanted = {item["content_sha256"] for item in probes if "content_sha256" in item}
    narratives = {item["narrative"] for item in probes if "narrative" in item}
    seen_splits, matches, counts, skipped = {}, {}, Counter(), Counter()
    for split, bit in SPLIT_BITS.items():
        for ordinal, row in enumerate(partitions[split]):
            counts[split] += 1
            if row["split"] != split:
                raise ValueError(f"Declared split disagrees with file at {split}:{ordinal}")
            original = row["original_index"]
            if type(original) is not int or original < 0:
                skipped["invalid_original_index"] += 1
                original = None
            else:
                seen_splits[original] = seen_splits.get(original, 0) | bit
            narrative = text_key(row["narrative"])
            if narrative not in narratives:
                continue
            speakers, dialogue = row["speakers"], row["dialogue"]
            if not isinstance(speakers, list) or not isinstance(dialogue, list) or len(speakers) != len(dialogue):
                skipped["unusable_requested_narrative_dialogue"] += 1
                continue
            turns = [[text_key(name), text_key(answer)] for name, answer in zip(speakers, dialogue, strict=True)]
            if len(turns) < 2 or any(not name or not utterance for name, utterance in turns):
                skipped["unusable_requested_narrative_dialogue"] += 1
                continue
            key = dialogue_key(narrative, turns)
            if key not in wanted:
                continue
            if key in matches:
                matches[key]["count"] += 1
            else:
                matches[key] = dict(count=1, original_index=original, official_split=split,
                                    row_ordinal=ordinal, source_columns_sha256=hash_json(row))

    receipts = []
    for item in probes:
        lookup = item.get("content_sha256")
        evidence = {k: v for k, v in item.items() if k != "narrative"}
        if lookup is None:
            receipts.append(evidence)
            continue
        match = matches.get(lookup)
        if match is None:
            evidence["status"] = "HOLD_NO_EXACT_MATCH"
        elif match["count"] != 1:
            evidence.update(status="HOLD_MULTIPLE_ORIGINAL_ROWS", match_count=match["count"])
        elif match["original_index"] is None:
            evidence["status"] = "HOLD_INVALID_ORIGINAL_INDEX"
        else:
            index = match["original_index"]
            flags = seen_splits[index]
            all_splits = [name for name, bit in SPLIT_BITS.items() if flags & bit]
            if len(all_splits) != 1:
                evidence.update(status="HOLD_ORIGINAL_INDEX_SPLIT_CONFLICT", original_index=index, root_splits=all_splits)
            else:
                split = match["official_split"]
                evidence.update(match, source_group_id=hash_json([REPO, REVISION, index]), root_splits=all_splits,
                                status="EXACT_TRAIN_LINK" if split == "train" else "EXACT_EVALUATION_LINK")
        receipts.append(evidence)
    return dict(rows=receipts, status_counts=dict(Counter(r["status"] for r in receipts)),
                official_rows_seen={split: counts[split] for split in RELEASE}, source_anomalies=dict(skipped),
                corpus_admitted_rows=0, teacher_calls=0)


def audit_release(directory, probes):
    with ExitStack() as stack:
        partitions = {split: stack.enter_context(pinned_rows(directory / f"{split}.parquet", count, digest))
                      for split, (count, digest) in RELEASE.items()}
        receipt = match_exact(probes, partitions)
        if receipt["official_rows_seen"] != {split: count for split, (count, _) in RELEASE.items()}:
            raise ValueError("A split ended before its declared physical extent")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-dir", type=Path, required=True, help="authorized local Ai2 release directory")
    parser.add_argument("--aya-rows", type=Path, required=True, help="explicit local Aya slice in JSONL")
    parser.add_argument("--aya-sha256", required=True, help="known digest of the local Aya slice")
    parser.add_argument("--report", type=Path, required=True, help="new JSON audit file")
    args = parser.parse_args()
    probes = read_aya(args.aya_rows, args.aya_sha256)
    report = audit_release(args.original_dir, probes)
    report.update(schema="P106B_SODA_ORIGINAL_LINEAGE_AUDIT_V1", repo=REPO, revision=REVISION,
                  public_release_files=RELEASE, aya_slice_sha256=args.aya_sha256.upper(),
                  verified_original_files=True, rights_admitted=False, split_mutations=0)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        print(file=stream)


if __name__ == "__main__":
    main()
