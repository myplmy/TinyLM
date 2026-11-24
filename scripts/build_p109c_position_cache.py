"""Build the exact P109C chat32 cache from an admitted v1.1 text release."""

import argparse
from array import array
from base64 import b64decode
from bisect import bisect_left
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
from itertools import islice
import json
import mmap
import os
from pathlib import Path
from struct import Struct
import sys
import unicodedata
import zlib

from tokenizers import Tokenizer

from scripts import run_p109c_scratch330 as entry
from tinylm.data.prepare import verify_chat_tokenizer
from tinylm.train.context_training_state import cache_identity


SCHEMA = "P109C_RAW_POSITION_HANDOFF_V1"
POSITION, PROOF = Struct("<III"), Struct("<IIB")
SLOT_BYTES = 4096
INDEX_OFFSET = 2 * SLOT_BYTES
SEPARATOR = b"\n\n"
PROTECTED = Path(__file__).resolve().parents[1] / "datasets" / "TinyDataset"


def regular_file(path):
    if path.is_relative_to(PROTECTED) or ".." in path.parts:
        raise ValueError("the source must be an approved derivative outside the protected dataset")
    for ancestor in reversed(path.parents):
        if ancestor.is_symlink():
            raise ValueError(f"linked input directory: {ancestor.name}")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"an unlinked input file is required: {path.name}")


def pinned_file(root, item):
    path = root / item["file"]
    regular_file(path)
    stamp = entry.file_stamp(path)
    if entry.file_sha(path).upper() != entry.digest(item["sha256"]):
        raise ValueError(f"input digest differs: {path.name}")
    return path, stamp


def release_positions(raw):
    states = []
    for offset in (0, SLOT_BYTES):
        digest, _, payload = raw[offset:offset + SLOT_BYTES].rstrip(b"\0").partition(b"\n")
        if sha256(payload).hexdigest().encode("ascii") != digest:
            continue
        try:
            state = json.loads(payload)
            if "zlib_json" in state:
                state = json.loads(zlib.decompress(b64decode(state["zlib_json"], validate=True)))
            if type(state["revision"]) is int:
                states.append(state)
        except (ValueError, KeyError, TypeError, zlib.error):
            continue
    if not states:
        raise ValueError("no intact v1.1 position slot")
    state = max(states, key=lambda item: item["revision"])
    if (state.get("version"), state.get("stage"), state.get("index_offset"), state.get("index_format")) != (
            "1.1", "published", INDEX_OFFSET, POSITION.format):
        raise ValueError("the latest v1.1 position slot must be published")
    count = state["rows"]
    if type(count) is not int or count <= 0:
        raise ValueError("invalid v1.1 position count")
    end = INDEX_OFFSET + count * POSITION.size
    if end > len(raw):
        raise ValueError("truncated v1.1 positions")
    if proof := state.get("source_binding_proof"):
        size = proof["rows"] * PROOF.size
        trailer = raw[end:end + size]
        if (proof["offset"] != end or len(trailer) != size
                or sha256(trailer).hexdigest().upper() != entry.digest(proof["sha256"])):
            raise ValueError("source-binding proof differs")
    return state, memoryview(raw)[INDEX_OFFSET:end]


def split_ends(scope):
    ends, names, total = [], [], 0
    for source in scope["inputs"]:
        length = source["intervals"]
        split = source["split"]
        if type(length) is not int or length <= 0 or split not in ("train", "val"):
            raise ValueError("original ordered TRAIN/VAL source intervals are required")
        total += length
        ends.append(total)
        names.append(split)
    if set(names) != {"train", "val"}:
        raise ValueError("both original splits are required")
    return ends, names


def indexed_documents(state, records, ends, names, excluded):
    held = set(state.get("content_admission_hold", ()))
    for group in state.get("admission_review", {}).values():
        held.update(group)
    for repeat in ("exact_repeats", "article_ui_repeats", "registry_repeats", "boundary_repeats"):
        held.update(number for number, _ in state.get(repeat, ()))
    seen = bytearray(ends[-1] + 1)
    previous_bytes = cursor = linked = 0
    for number, before, width in POSITION.iter_unpack(records):
        start = cursor
        cursor += width
        previous_bytes += before
        if not width:
            continue
        if not 0 < number <= ends[-1] or seen[number] or number in held:
            raise ValueError(f"unlinked, duplicate, or held published position: {number}")
        if cursor > state["output_bytes"]:
            raise ValueError("document span exceeds the admitted text")
        seen[number] = 1
        linked += 1
        split = names[bisect_left(ends, number)]
        if number not in excluded:
            yield number, split, start, cursor
    if (cursor != state["output_bytes"] or previous_bytes != state["input_stamp"][2]
            or linked != state["stored_documents"]):
        raise ValueError("published position totals do not match the release")


def write_split(directory, split, tokenizer, eos, source, docs, val_text, val_tokens, batch_size, stop_by):
    records = (row for row in docs if row[1] == split)
    tokens = documents = text_bytes = 0
    next_report = 50_000
    with (directory / f"{split}.bin").open("xb", buffering=1024 * 1024) as stream:
        while batch := list(islice(records, batch_size)):
            if stop_by and datetime.now(stop_by.tzinfo) >= stop_by:
                raise TimeoutError("the cache build reached its cutoff")
            texts = []
            for number, _, start, end in batch:
                raw = source[start:end]
                if not raw.endswith(SEPARATOR) or len(raw) <= len(SEPARATOR):
                    raise ValueError(f"missing published document separator at position {number}")
                texts.append(raw[:-len(SEPARATOR)].decode("utf-8"))
                text_bytes += len(raw) - len(SEPARATOR)
            for (number, _, _, _), text, encoded in zip(batch, texts, tokenizer.encode_batch(texts, add_special_tokens=False), strict=True):
                ids = encoded.ids
                if not ids or eos in ids:
                    raise ValueError(f"empty or nested EOS document at position {number}")
                row = array("H", (*ids, eos))
                if sys.byteorder != "little":
                    row.byteswap()
                payload = row.tobytes()
                text_key = sha256(unicodedata.normalize("NFC", " ".join(text.split())).encode("utf-8")).digest()
                token_key = sha256(payload).digest()
                if split == "val":
                    val_text.add(text_key)
                    val_tokens.add(token_key)
                elif text_key in val_text or token_key in val_tokens:
                    raise ValueError(f"complete TRAIN/VAL document overlap at position {number}")
                stream.write(payload)
                tokens += len(row)
                documents += 1
            if documents >= next_report:
                print(f"P109C_RAW_PROGRESS {split} documents={documents} tokens={tokens}", flush=True)
                next_report = documents + 50_000
        stream.flush()
        os.fsync(stream.fileno())
    return dict(tokens=tokens, documents=documents, text_bytes=text_bytes)


def build_cache(path, sha256, name, *, batch_size=256, stop_by=None):
    if not path.is_absolute():
        raise ValueError("the admission manifest must have an absolute path")
    regular_file(path)
    spec = json.loads(entry.manifest_bytes(path, sha256))
    if (spec.get("schema") != SCHEMA or spec.get("source_release") != entry.RELEASE
            or not isinstance(spec.get("admission"), str) or not spec["admission"].strip()):
        raise ValueError("the exact raw derivative and its admission reference are required")
    if not name.endswith("_chat32") or Path(name).name != name or batch_size < 1:
        raise ValueError("a new relative *_chat32 cache name and a positive batch size are required")
    root = path.parent
    pins = {field: pinned_file(root, spec[field]) for field in ("positions", "split_scope", "tokenizer")}
    state, records = release_positions(pins["positions"][0].read_bytes())
    ends, names = split_ends(json.loads(pins["split_scope"][0].read_bytes()))
    excluded = set(spec.get("excluded_positions", ()))
    if any(type(number) is not int or not 0 < number <= ends[-1] for number in excluded):
        raise ValueError("invalid supplemental excluded position")
    tokenizer_path = entry.bundle_path(root, spec["tokenizer"]["file"])
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    eos = verify_chat_tokenizer(tokenizer, entry.VOCAB)["<eos>"]
    text_path, text_stamp = pins["text"] = pinned_file(root, spec["text"])
    if text_stamp[2] != state["output_bytes"]:
        raise ValueError("released text length does not match published positions")
    directory = root / name
    directory.mkdir(exist_ok=False)

    val_text, val_tokens = set(), set()
    splits = {}
    with ExitStack() as stack:
        stream = stack.enter_context(text_path.open("rb"))
        mapped = stack.enter_context(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
        for split in ("val", "train"):
            docs = indexed_documents(state, records, ends, names, excluded)
            splits[split] = write_split(directory, split, tokenizer, eos, mapped, docs,
                                        val_text, val_tokens, batch_size, stop_by)
            print(f"P109C_RAW_SPLIT {split} {splits[split]}", flush=True)

    train, val = (splits[split]["tokens"] for split in ("train", "val"))
    if train < 2 * entry.STEPS * entry.MICRO * entry.ACCUM * entry.WIDTH or val <= entry.WIDTH + 1:
        raise ValueError("the original splits are too small for the exact 330M cache")
    if any(entry.file_stamp(pinned) != stamp for pinned, stamp in pins.values()):
        raise ValueError("an admitted input changed during the cache build")
    for split, values in splits.items():
        if (directory / f"{split}.bin").stat().st_size != 2 * values["tokens"]:
            raise ValueError("written token count differs from the byte count")
    token_sha = entry.digest(spec["tokenizer"]["sha256"])
    meta = dict(schema=SCHEMA, data="ko-en", vocab=entry.VOCAB, token_dtype="uint16",
                tokenizer_lineage="chat32", tokenizer_sha256=token_sha, eos_id=eos, dir=str(directory),
                tokens=train + val, train=train, val=val, train_documents=splits["train"]["documents"],
                val_documents=splits["val"]["documents"],
                bytes_per_token=sum(values["text_bytes"] for values in splits.values()) / (train + val),
                bytes_per_token_val=splits["val"]["text_bytes"] / val, source_release=entry.RELEASE,
                raw_manifest_sha256=entry.digest(sha256), position_revision=state["revision"],
                excluded_positions=sorted(excluded), splits=splits, complete_train_val_overlap=0)
    entry.publish(directory / "meta.json", meta)
    files = cache_identity(directory)["files"]
    return dict(directory=name, sha256={name: item["sha256"] for name, item in files.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--cache-name", required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or datetime.now(args.stop_by.tzinfo) >= args.stop_by:
        parser.error("a future timezone-aware cutoff is required")
    print(json.dumps(build_cache(args.manifest.absolute(), args.manifest_sha256, args.cache_name,
                                 stop_by=args.stop_by), ensure_ascii=False))


if __name__ == "__main__":
    main()
