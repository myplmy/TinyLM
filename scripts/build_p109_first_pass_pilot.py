"""Build the mapped, cache18 subset of the 2026-11-20 first-pass corpus."""

import hashlib
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_cache"
FIRST_PASS = DATA / "p106b_hold_resolution_v1_20261027_goalc"
COMBINED = FIRST_PASS / "hold_first_pass_combined.txt"
WORK = FIRST_PASS / "hold_first_pass.txt.work"
SOURCE = FIRST_PASS / "cache_reviewed_partial_v18"
TOKENIZER = DATA / "tok-ko-en-32768-chat32.json"
OUTPUT = DATA / "20261120_정제데이터셋1차"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def checked_shard(directory, spec):
    name = Path(spec["path"])
    path = directory / name
    if name.name != str(name) or path.is_symlink():
        raise ValueError(f"unexpected shard path {name}")
    block = path.read_bytes()
    if len(block) != spec["bytes"] or sha(block) != spec["sha256"].lower():
        raise ValueError(f"shard integrity failed for {path}")
    return block


def selection():
    work_sha = file_sha(WORK)
    records = {}
    with WORK.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if isinstance(record, dict):
                records[record["type"]] = record

    combined = records["combined"]
    span = records["legacy_cache_span"]
    if (COMBINED.stat().st_size != combined["bytes"] or file_sha(COMBINED) != combined["sha256"]
            or span["combined_sha256"] != combined["sha256"] or Path(span["cache"]) != SOURCE
            or file_sha(SOURCE / "built.json") != span["built_sha256"]):
        raise ValueError("the combined corpus and the cache18 position proof differ")
    if span["end"] > combined["previous_bytes"]:
        raise ValueError("the pilot must stay outside the appended first-pass review rows")
    built = read(SOURCE / "built.json")
    verified = read(SOURCE / "verified.json")
    if (not verified["every_adopted_document_regenerated"] or verified["exact_train_val_text_overlap"] != 0
            or any(built["accepted"][split]["documents"] != span["counts"][split] for split in ("train", "val"))
            or file_sha(TOKENIZER).upper() != built["lineage"]["tokenizer_sha256"]):
        raise ValueError("the cache18 split or tokenizer proof changed")

    # The work index uses one-based positions in the expanded source. The
    # cache ledger lists all original validation rows before expanded TRAIN.
    held = set(records["legacy_admission_hold"]["documents"])
    proof = read(SOURCE / "prior_safe_derivative_reuse_verified.json")
    expected = {f"expanded_train:{index - 1}" for index in held}
    if not expected or expected != {row["id"] for row in proof["bodies"]}:
        raise ValueError("unresolved legacy exclusion coordinates")
    base = built["sources"]["validation"]["documents"]
    targets = {base + index - 1: f"expanded_train:{index - 1}" for index in held}
    ledger = SOURCE / "ledger"
    offset = 0
    exclusions = []
    for spec in read(ledger / "decisions_shards_manifest.json")["shards"]:
        end = offset + spec["rows"]
        needed = {index for index in targets if offset <= index < end}
        if needed:
            rows = checked_shard(ledger, spec).splitlines()
            for index in sorted(needed):
                row = json.loads(rows[index - offset])
                if row["id"] != targets[index] or row["split"] != "train":
                    raise ValueError("legacy exclusion resolved to the wrong source document")
                exclusions.append({"id": row["id"], **row["cache"]})
        offset = end
    if len(exclusions) != len(held):
        raise ValueError("missing legacy exclusions")
    return records, built, exclusions, work_sha


def write_split(staging, split, exclusions):
    directory = SOURCE / "tokens" / split
    manifest = read(directory / "manifest.json")
    if (manifest["token_dtype"], manifest["byte_order"], manifest["eos_id"]) != ("uint16", "little", 2):
        raise ValueError("unexpected token format")
    before = hashlib.sha256()
    after = hashlib.sha256()
    output = staging / f"{split}.bin"
    ids = 0
    removed = 0
    with output.open("xb") as out:
        for spec in manifest["shards"]:
            block = checked_shard(directory, spec)
            before.update(block)
            if spec["first_id"] != ids or len(block) != 2 * spec["ids"]:
                raise ValueError("token shard order or size changed")
            position = 0
            for record in sorted((r for r in exclusions if r["shard"] == spec["path"]), key=lambda r: r["local_id"]):
                start = 2 * record["local_id"]
                end = start + 2 * record["ids"]
                if (not position <= start < end <= len(block)
                        or record["offset_ids"] != ids + start // 2
                        or sha(block[start:end]).upper() != record["ids_sha256"]
                        or int.from_bytes(block[end - 2:end], "little") != 2):
                    raise ValueError("excluded document token range changed")
                out.write(block[position:start])
                after.update(block[position:start])
                removed += record["ids"]
                position = end
            out.write(block[position:])
            after.update(block[position:])
            ids += spec["ids"]
    if (ids != manifest["ids"] or before.hexdigest().upper() != manifest["concat_sha256"]
            or removed != sum(r["ids"] for r in exclusions) or output.stat().st_size != 2 * (ids - removed)
            or file_sha(output) != after.hexdigest()):
        raise ValueError("output verification failed")
    return {"tokens": ids - removed, "sha256": after.hexdigest(), "removed_tokens": removed}


def main():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    records, built, exclusions, work_sha = selection()
    staging = Path(tempfile.mkdtemp(prefix=".p109_first_pass_", dir=DATA))
    train = write_split(staging, "train", exclusions)
    val = write_split(staging, "val", [])
    if train["tokens"] < 2 * (2289 * 8 * 16 * 1024):
        raise ValueError("mapped pilot does not cover the planned training budget")
    span = records["legacy_cache_span"]
    meta = {
        "schema": "P109_FIRST_PASS_MAPPED_PILOT_V1",
        "data": "ko-en", "vocab": 32768, "token_dtype": "uint16", "dir": str(OUTPUT),
        "tokens": train["tokens"] + val["tokens"], "train": train["tokens"], "val": val["tokens"],
        "train_documents": span["counts"]["train"] - len(exclusions), "val_documents": span["counts"]["val"],
        "tokenizer_lineage": "chat32", "tokenizer_sha256": built["lineage"]["tokenizer_sha256"],
        "source_combined_sha256": records["combined"]["sha256"], "source_position_index_sha256": work_sha,
        "combined_byte_range": [span["start"], span["end"]], "source_cache_receipt_sha256": span["built_sha256"],
        "excluded_train_documents": exclusions, "first_pass_append_pair": records["admission_hold"],
        "append_scope": "OUTSIDE_PILOT_FOR_BOTH_SPLITS", "split_receipts": {"train": train, "val": val},
        "source_collections": ["wikimedia/wikipedia/20231101.ko", "HuggingFaceFW/fineweb-edu/sample-10BT"],
        "independent_test": "SEPARATE_EVALUATION_ASSET", "status": "CPU_VERIFIED_PARTIAL_PILOT",
        "training_status": "NOT_RUN_300M_EXPOSURE_GATE",
    }
    if file_sha(WORK) != work_sha:
        raise ValueError("the position index changed during pilot construction")
    (staging / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    staging.rename(OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "train": train, "val": val, "excluded": [r["id"] for r in exclusions]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
