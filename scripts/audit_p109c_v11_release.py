"""Count the published v1.1 derivative by original split without creating a cache."""

import argparse
from array import array
from collections import Counter
from datetime import datetime
from hashlib import sha256
from itertools import islice
import json
import mmap
from pathlib import Path
import re
import sys
import unicodedata

from tokenizers import Tokenizer

from scripts import build_p109c_position_cache as cache
from scripts import run_p109c_scratch330 as entry
from tinylm.data.prepare import verify_chat_tokenizer


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "text": ("20261120_정제데이터셋v1.1.txt", "5524d68044e2c36468e41c6c2e9c02e6d5ba97bd0440cc54deff7f23c9452f8f"),
    "positions": ("20261120_정제데이터셋v1.1.txt.work", "dd19833e0c53d84ca05d79563aa3fb2b2682218fa10080630af30d6e345d3691"),
    "scope": ("p106b_hold_resolution_v1_20261027_goalc/scope.json", "5e64b3652c76353eb01be72f757bd8778eff15afbb465059c8b56bdf9abbd10a"),
    "tokenizer": ("tok-ko-en-32768-chat32.json", "9716f40e4c504d6af37dde76cca578e30b45e9ca86c8b6bb79b2fa095d3ac88e"),
}
OUT = ROOT / "test_result/evidence/p109c_v11_readonly_split_audit_v1_20261121"
AUTHORIZED_END = datetime.fromisoformat("2026-11-22T13:00:00+09:00")
HANGUL = re.compile("[가-힣]")


def deadline_passed(stop_by):
    if datetime.now(stop_by.tzinfo) >= stop_by:
        raise TimeoutError("the read-only count reached its cutoff")


def content_digests(text, ids, eos):
    text_key = sha256(unicodedata.normalize("NFC", " ".join(text.split())).encode("utf-8")).digest()
    tokens = array("H", (*ids, eos))
    if sys.byteorder != "little":
        tokens.byteswap()
    return text_key, sha256(tokens.tobytes()).digest()


def count_rows(instream, records, tokenizer, eos, stop_by, val_keys=None):
    counts = Counter(documents=0, tokens=0, text_bytes=0, has_hangul_documents=0,
                     has_hangul_tokens=0, val_body_overlap=0, val_tokens_overlap=0)
    keys = (set(), set())
    matched = []
    report_at = 100_000
    while batch := list(islice(records, 256)):
        deadline_passed(stop_by)
        texts = []
        for number, _, start, end in batch:
            raw = instream[start:end]
            if not raw.endswith(cache.SEPARATOR) or len(raw) <= len(cache.SEPARATOR):
                raise ValueError(f"invalid published document separator at {number}")
            body = raw[:-len(cache.SEPARATOR)]
            counts["text_bytes"] += len(body)
            texts.append(body.decode("utf-8"))
        encoded = tokenizer.encode_batch(texts, add_special_tokens=False)
        for (number, _, _, _), text, row in zip(batch, texts, encoded, strict=True):
            if not row.ids or eos in row.ids:
                raise ValueError(f"empty or nested EOS document at {number}")
            tokens = len(row.ids) + 1
            counts["documents"] += 1
            counts["tokens"] += tokens
            if HANGUL.search(text):
                counts["has_hangul_documents"] += 1
                counts["has_hangul_tokens"] += tokens
            raw_key, token_key = content_digests(text, row.ids, eos)
            if val_keys is None:
                keys[0].add(raw_key)
                keys[1].add(token_key)
            else:
                body_overlap = raw_key in val_keys[0]
                token_overlap = token_key in val_keys[1]
                counts["val_body_overlap"] += body_overlap
                counts["val_tokens_overlap"] += token_overlap
                if body_overlap or token_overlap:
                    matched.append(number)
        if counts["documents"] >= report_at:
            print(f"TRAIN documents={counts['documents']} tokens={counts['tokens']}", flush=True)
            report_at += 100_000
    return dict(counts), keys, matched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    stop_by = args.stop_by
    if stop_by.tzinfo is None or stop_by > AUTHORIZED_END:
        parser.error("provide an authorized timezone-aware stop time")
    deadline_passed(stop_by)
    files, stamps, digests = {}, {}, {}
    for key, (name, expected) in FILES.items():
        path = ROOT / "data_cache" / name
        cache.regular_file(path)
        files[key], stamps[key] = path, entry.file_stamp(path)
        if entry.file_sha(path).lower() != expected:
            raise ValueError(f"the saved release differs: {key}")
        digests[key] = expected

    state, records = cache.release_positions(files["positions"].read_bytes())
    ends, names = cache.split_ends(json.loads(files["scope"].read_bytes()))
    tokenizer = Tokenizer.from_file(str(files["tokenizer"]))
    eos = verify_chat_tokenizer(tokenizer, entry.VOCAB)["<eos>"]

    def documents(split):
        return (record for record in cache.indexed_documents(state, records, ends, names, set()) if record[1] == split)

    OUT.mkdir(exist_ok=False)
    with files["text"].open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as body:
        validation, val_keys, _ = count_rows(body, documents("val"), tokenizer, eos, stop_by)
        print(f"VAL documents={validation['documents']} tokens={validation['tokens']}", flush=True)
        train, _, matched = count_rows(body, documents("train"), tokenizer, eos, stop_by, val_keys)
    if any(entry.file_stamp(path) != stamps[key] for key, path in files.items()):
        raise ValueError("the published inputs changed during the read-only count")
    if (train["documents"] + validation["documents"] != state["stored_documents"]
            or train["text_bytes"] + validation["text_bytes"] + 2 * state["stored_documents"] != state["output_bytes"]):
        raise ValueError("the counted document coverage differs from the saved release")
    entry.publish(OUT / "report.json", dict(scope="PUBLISHED_BASE_REVISION_661_READ_ONLY", source_sha256=digests,
        producer_sha256=entry.file_sha(Path(__file__)), position_revision=state["revision"],
        original_indexed_train=train, original_indexed_val=validation, matched_train_source_positions=matched,
        tokenizer_eos=eos, total_tokens=train["tokens"] + validation["tokens"],
        training_admitted=False, cache_created=False, partial_overlap_checked=False))
    print(f"TRAIN documents={train['documents']} tokens={train['tokens']} body_overlap={train['val_body_overlap']} token_overlap={train['val_tokens_overlap']}", flush=True)


if __name__ == "__main__":
    main()
