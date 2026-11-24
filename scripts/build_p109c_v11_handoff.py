"""Read or tokenize the admitted v1.1 TXT and its final additional decisions."""

import argparse
from bisect import bisect_left
from collections import Counter
from contextlib import ExitStack
from datetime import datetime
import gzip
from hashlib import sha256
from itertools import chain
import json
import mmap
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from tokenizers import Tokenizer

from scripts import build_p109c_position_cache as position_cache
from tinylm.data.prepare import verify_chat_tokenizer
from tinylm.train.context_training_state import cache_identity


SCHEMA = "P109C_ADOPTED_V11_HANDOFF_V1"
ENTRY = position_cache.entry


def pin_text(root, item):
    path = root / item["file"]
    if os.path.lexists(path):
        file, stamp = position_cache.pinned_file(root, item)
        return (file, stamp), stamp[2]
    compressed = path.with_name(path.name + ".gz")
    position_cache.regular_file(compressed)
    stamp = ENTRY.file_stamp(compressed)
    digest, length = sha256(), 0
    with gzip.open(compressed, "rb") as source:
        for block in iter(lambda: source.read(8 << 20), b""):
            digest.update(block)
            length += len(block)
    if digest.hexdigest().upper() != ENTRY.digest(item["sha256"]) or ENTRY.file_stamp(compressed) != stamp:
        raise ValueError(f"restored content or file identity differs: {path.name}")
    return (compressed, stamp), length


class CompressedText:
    def __init__(self, stream, length):
        self.stream = stream
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, interval):
        self.stream.seek(interval.start)
        length = interval.stop - interval.start
        data = self.stream.read(length)
        if len(data) != length:
            raise ValueError("the restored TXT ends before the published document boundary")
        return data


class ReleasedText:
    def __init__(self, baseline, additions):
        self.baseline = baseline
        self.additions = additions

    def __getitem__(self, interval):
        boundary = len(self.baseline)
        if interval.stop <= boundary:
            return self.baseline[interval]
        if interval.start < boundary:
            raise ValueError("a document crosses the boundary between the two text files")
        return self.additions[interval.start - boundary:interval.stop - boundary]


def read_additions(path, state, scope, ends, names):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        header = json.loads(next(stream))
        if (header["kind"], header["revision"], header["v1_1_bytes"]) != (
                "기준", state["revision"], state["output_bytes"]):
            raise ValueError("the supplemental decisions belong to a different text revision")
        items = {item[0]: item for item in header["items"]}
        if len(items) != len(header["items"]):
            raise ValueError("duplicate supplemental scope position")
        decisions = {}
        for raw in stream:
            row = json.loads(raw)
            if row["kind"] == "범위보완":
                for item in row["items"]:
                    if item[0] in items:
                        raise ValueError("repeated supplemental scope position")
                    items[item[0]] = item
                continue
            number = row["number"]
            if row["kind"] != "정제" or number in decisions:
                raise ValueError("invalid or repeated supplemental decision")
            decisions[number] = row
    if decisions.keys() != items.keys():
        raise ValueError("the supplemental decisions do not cover their exact scope")

    body, records, counts, excluded = bytearray(), [], Counter(), set()
    for number, row in sorted(decisions.items()):
        if type(number) is not int or not 0 < number <= ends[-1]:
            raise ValueError("a supplemental source position is out of range")
        slot = bisect_left(ends, number)
        item = items[number]
        if not 0 <= item[1] < item[2] <= scope["inputs"][slot]["bytes"]:
            raise ValueError(f"invalid supplemental original span at {number}")
        decision = row["decision"]
        counts[decision] += 1
        if decision in ("HOLD", "EXCLUDE") and "text" not in row:
            excluded.add(number)
            continue
        if decision != "EDIT" or item[6] or not row["text"].strip():
            raise ValueError(f"invalid supplemental admission at {number}")
        data = row["text"].encode("utf-8")
        if b"\0" in data or sha256(data).hexdigest().upper() != ENTRY.digest(row["text_sha256"]):
            raise ValueError(f"supplemental text hash or content differs at {number}")
        start = state["output_bytes"] + len(body)
        body.extend(data)
        body.extend(position_cache.SEPARATOR)
        records.append((number, names[slot], start, state["output_bytes"] + len(body)))
    return body, records, counts, excluded


def run_handoff(manifest, manifest_sha256, cache_name=None, stop_by=None):
    position_cache.regular_file(manifest)
    spec = json.loads(ENTRY.manifest_bytes(manifest, manifest_sha256))
    if (spec["schema"], spec["source_release"]) != (SCHEMA, ENTRY.RELEASE) or not spec["admission"].strip():
        raise ValueError("the final v1.1 handoff and an admission reference are required")
    root = manifest.parent
    pins = {key: position_cache.pinned_file(root, spec[key])
            for key in ("positions", "split_scope", "tokenizer")}
    pins["text"], text_length = pin_text(root, spec["text"])
    pins["supplement"], _ = pin_text(root, spec["supplement"])
    state, records = position_cache.release_positions(pins["positions"][0].read_bytes())
    text_path = pins["text"][0]
    if text_length != state["output_bytes"]:
        raise ValueError("the released TXT length differs from the position table")
    scope = json.loads(pins["split_scope"][0].read_bytes())
    ends, names = position_cache.split_ends(scope)
    additions, extra_docs, counts, barred = read_additions(pins["supplement"][0], state, scope, ends, names)
    excluded = set(spec.get("excluded_positions", ()))
    if any(type(number) is not int or not 0 < number <= ends[-1] for number in excluded):
        raise ValueError("invalid final exclusion position")
    excluded.update(barred)
    extra_docs = [row for row in extra_docs if row[0] not in excluded]
    incoming = {row[0] for row in extra_docs}

    def baseline_docs():
        return position_cache.indexed_documents(state, records, ends, names, excluded)

    documents = Counter(row[1] for row in extra_docs)
    for number, split, _, _ in baseline_docs():
        if number in incoming:
            raise ValueError(f"a supplemental admission repeats a published position: {number}")
        documents[split] += 1
    if counts != spec["additional_decisions"] or documents != spec["admitted_documents"]:
        raise ValueError("the final selection counts differ from the handoff")

    tokenizer = Tokenizer.from_file(str(pins["tokenizer"][0]))
    eos = verify_chat_tokenizer(tokenizer, ENTRY.VOCAB)["<eos>"]
    with ExitStack() as stack:
        if text_path.suffix == ".gz":
            stream = stack.enter_context(gzip.open(text_path, "rb"))
            baseline = CompressedText(stream, text_length)
        else:
            stream = stack.enter_context(text_path.open("rb"))
            baseline = stack.enter_context(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
        source = ReleasedText(baseline, additions)
        if cache_name is None:
            extra_tokens = 0
            for start in range(0, len(extra_docs), 256):
                batch = extra_docs[start:start + 256]
                texts = [source[lo:hi][:-len(position_cache.SEPARATOR)].decode("utf-8") for _, _, lo, hi in batch]
                for row in tokenizer.encode_batch(texts, add_special_tokens=False):
                    if not row.ids or eos in row.ids:
                        raise ValueError("an admitted supplemental text is empty or contains EOS")
                    extra_tokens += len(row.ids) + 1
            if any(ENTRY.file_stamp(file) != stamp for file, stamp in pins.values()):
                raise ValueError("an admitted input changed during verification")
            return dict(documents=documents, additional_documents=len(extra_docs), additional_tokens=extra_tokens)

        directory = root / cache_name
        if os.path.lexists(directory):
            raise FileExistsError(directory)
        with TemporaryDirectory(prefix=".p109c-adopted-", dir=root) as temp:
            staging = Path(temp)
            val_text, val_tokens = set(), set()
            splits = {}
            for split in ("val", "train"):
                docs = chain(baseline_docs(), extra_docs)
                splits[split] = position_cache.write_split(staging, split, tokenizer, eos, source, docs,
                                                          val_text, val_tokens, 256, stop_by)
                if splits[split]["documents"] != documents[split]:
                    raise ValueError("the output document counts differ from the handoff")
            train, val = splits["train"]["tokens"], splits["val"]["tokens"]
            if train < 2 * ENTRY.STEPS * ENTRY.MICRO * ENTRY.ACCUM * ENTRY.WIDTH or val <= ENTRY.WIDTH + 1:
                raise ValueError("the output is too small for the exact 330M run")
            if any(ENTRY.file_stamp(file) != stamp for file, stamp in pins.values()):
                raise ValueError("an admitted input changed during tokenization")
            meta = dict(schema=position_cache.SCHEMA, data="ko-en", vocab=ENTRY.VOCAB, token_dtype="uint16",
                        tokenizer_lineage="chat32", tokenizer_sha256=ENTRY.digest(spec["tokenizer"]["sha256"]),
                        eos_id=eos, dir=str(directory), tokens=train + val, train=train, val=val,
                        train_documents=documents["train"], val_documents=documents["val"],
                        bytes_per_token=sum(row["text_bytes"] for row in splits.values()) / (train + val),
                        bytes_per_token_val=splits["val"]["text_bytes"] / val, source_release=ENTRY.RELEASE,
                        raw_manifest_sha256=ENTRY.digest(manifest_sha256), position_revision=state["revision"],
                        excluded_positions=sorted(excluded), splits=splits, complete_train_val_overlap=0,
                        additional_documents=len(extra_docs),
                        additional_decisions_sha256=ENTRY.digest(spec["supplement"]["sha256"]))
            ENTRY.publish(staging / "meta.json", meta)
            files = cache_identity(staging)["files"]
            directory.mkdir()
            installed = []
            try:
                for name in ("train.bin", "val.bin", "meta.json"):
                    path = directory / name
                    os.replace(staging / name, path)
                    installed.append(path)
            except BaseException:
                for path in reversed(installed):
                    path.unlink()
                directory.rmdir()
                raise
    return dict(directory=cache_name, sha256={name: row["sha256"] for name, row in files.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--cache-name")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.cache_name is not None:
        if Path(args.cache_name).name != args.cache_name or not args.cache_name.endswith("_chat32"):
            parser.error("--cache-name must be a new relative *_chat32 directory name")
        if not args.stop_by or args.stop_by.tzinfo is None or datetime.now(args.stop_by.tzinfo) >= args.stop_by:
            parser.error("cache creation requires a future timezone-aware --stop-by")
    print(json.dumps(run_handoff(args.manifest.absolute(), args.manifest_sha256,
                                args.cache_name, args.stop_by), ensure_ascii=False))


if __name__ == "__main__":
    main()
