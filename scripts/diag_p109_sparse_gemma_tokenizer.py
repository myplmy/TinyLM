"""Load only input-relevant Gemma symbols while preserving the frozen BPE rules."""

from datetime import datetime, timedelta
from hashlib import blake2b, sha256
from itertools import groupby
import json
import mmap
import os
from pathlib import Path
import re
from struct import Struct
import subprocess
import sys
import sysconfig
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.append(str(ROOT))
    sys.path.append(sysconfig.get_path("purelib"))

from tokenizers import Tokenizer

from scripts import diag_p109_compact_gemma_tokenizer as previous
from scripts import diag_p109_compact_qwen_tokenizer as evidence
from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer, Encoding, HEADER, MAGIC, MERGE, OFFSET


TAG = "p109_sparse_gemma_tokenizer_v2_20261119"
OUT = previous.OUT.with_name(TAG)
SIDE_MAGIC = b"TLGMSP1\0"
SIDE_HEADER = Struct("<8s3I")
SCALAR = Struct("<II")
MARKER = re.compile(r"<[^<>]*>")


def marker_key(text):
    return int.from_bytes(blake2b(text.encode("utf-8"), digest_size=8).digest(), "little")


def create_index(config, output):
    assert config["normalizer"] == {"type": "Replace", "pattern": {"String": " "}, "content": "\u2581"}
    assert all(not row[k] for row in config["added_tokens"]
               for k in ("single_word", "lstrip", "rstrip", "normalized"))
    model = config["model"]
    vocabulary = model["vocab"]
    core = {f"<0x{i:02X}>" for i in range(256)} | {model["unk_token"]}
    core.update(config["post_processor"]["special_tokens"])
    base = dict(config, added_tokens=[], model=dict(model, vocab={s: vocabulary[s] for s in core}, merges=[]))
    extras, markers = [], []
    for position, row in enumerate(config["added_tokens"]):
        name = row["content"]
        if MARKER.fullmatch(name):
            markers.append((marker_key(name), row["id"], 2 * position + int(row["special"])))
        else:
            extras.append((position, row))
    markers.sort()
    assert len({row[0] for row in markers}) == len(markers)
    chars = sorted((ord(piece), token_id) for piece, token_id in vocabulary.items() if len(piece) == 1)
    info = dict(base=base, extras=extras, special=[row["id"] for row in config["added_tokens"] if row["special"]])
    payload = json.dumps(info, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with output.open("xb") as stream:
        stream.write(SIDE_HEADER.pack(SIDE_MAGIC, len(chars), len(markers), len(payload)))
        for row in chars:
            stream.write(SCALAR.pack(*row))
        for row in markers:
            stream.write(MERGE.pack(*row))
        stream.write(payload)
    return dict(characters=len(chars), markers=len(markers), other_added=len(extras))


def map_file(path):
    with Path(path).open("rb") as stream:
        return mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)


class SparseGemma(CompactQwenTokenizer):
    def __init__(self, asset, sidecar):
        self.data = map_file(asset)
        try:
            self.index = map_file(sidecar)
            try:
                magic, self.size, ordinary, self.rule_count, prep, piece_size = HEADER.unpack_from(self.data)
                self.rule_start = HEADER.size + (self.size + 1) * OFFSET.size
                self.piece_start = self.rule_start + self.rule_count * MERGE.size + prep
                assert magic == MAGIC and ordinary == 262144 and self.size == 262145
                assert self.piece_start + piece_size == len(self.data)
                assert self._offset(0) == 0 and self._offset(self.size) == piece_size
                marker, self.char_count, self.marker_count, info_size = SIDE_HEADER.unpack_from(self.index)
                self.marker_start = SIDE_HEADER.size + self.char_count * SCALAR.size
                info_start = self.marker_start + self.marker_count * MERGE.size
                assert marker == SIDE_MAGIC and info_start + info_size == len(self.index)
                info = json.loads(self.index[info_start:])
                self.config, self.extras, self.special = info["base"], info["extras"], set(info["special"])
                self.scaffold = Tokenizer.from_str(json.dumps(self.config, ensure_ascii=False))
            except Exception:
                self.index.close()
                raise
        except Exception:
            self.data.close()
            raise

    def __exit__(self, *_exc):
        self.index.close()
        self.data.close()

    def find(self, key, start, count, record):
        i, j = 0, count
        while i < j:
            middle = (i + j) // 2
            row = record.unpack_from(self.index, start + middle * record.size)
            if row[0] == key:
                return row[1:]
            if row[0] < key:
                i = middle + 1
            else:
                j = middle
        return None

    def encode(self, text):
        selected = {order: row for order, row in self.extras if row["content"] in text}
        for name in set(MARKER.findall(text)):
            match = self.find(marker_key(name), self.marker_start, self.marker_count, MERGE)
            if match is None or self.id_to_token(match[0]) != name:
                continue
            token_id, bits = match
            selected[bits // 2] = dict(id=token_id, content=name, single_word=False,
                lstrip=False, rstrip=False, normalized=False, special=bool(bits & 1))
        added = [selected[n] for n in sorted(selected)]
        seed = dict(self.config["model"]["vocab"])
        seed.update((row["content"], row["id"]) for row in added)
        for symbol in set(text.replace(" ", "\u2581")):
            match = self.find(ord(symbol), SIDE_HEADER.size, self.char_count, SCALAR)
            if match is not None:
                seed[symbol] = match[0]
        scoped = dict(self.config, model=dict(self.config["model"], vocab=seed), added_tokens=added)
        small = Tokenizer.from_str(json.dumps(scoped, ensure_ascii=False))
        encoded = small.encode(text, add_special_tokens=False)
        result = Encoding([], [], [])
        for word, entries in groupby(zip(encoded.word_ids, encoded.ids, encoded.offsets, strict=True), key=lambda x: x[0]):
            _, ids, offsets = zip(*entries, strict=True)
            merged, positions = self._merge_word(list(ids), list(offsets))
            result.ids.extend(merged)
            result.offsets.extend(positions)
            result.word_ids.extend([word] * len(merged))
        return result


def worker(asset, sidecar, cases, scope, output):
    initial = evidence.snapshot()
    begin = perf_counter()
    with SparseGemma(asset, sidecar) as codec:
        load_time = perf_counter()-begin
        loaded = evidence.snapshot()
        records = []
        codec_seconds = 0.
        if scope == "vocab":
            vocabulary = evidence.vocab_check(codec, codec.size)
            assert codec.id_to_token(262144) == "<image_soft_token>" and codec.id_to_token(262145) is None
        else:
            vocabulary = None
            with Path(cases).open(encoding="utf-8") as stream:
                for line in stream:
                    name, text = json.loads(line)
                    start = perf_counter()
                    encoded = codec.encode(text)
                    fields = dict(ids=encoded.ids, offsets=encoded.offsets, words=encoded.word_ids,
                        kept=codec.decode(encoded.ids, skip_special_tokens=False), stripped=codec.decode(encoded.ids))
                    codec_seconds += perf_counter()-start
                    raw = json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    records.append(dict(case=name, tokens=len(encoded.ids), sha256=sha256(raw).hexdigest().upper()))
        complete = evidence.snapshot()
    peak = max(v for row in (initial, loaded, complete) for v in row.values())
    evidence.write(output, dict(records=records, vocabulary=vocabulary, peak=peak, load_seconds=load_time,
        codec_seconds=codec_seconds, history=dict(initial=initial, loaded=loaded, complete=complete)))
    print("SPARSE_GEMMA_WORKER", scope, peak, len(records), flush=True)


def main():
    cutoff = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=260) < cutoff
    prior_profile = evidence.load(previous.OUT / "profile.json")
    asset = previous.OUT / "gemma.qbpe"
    cases = previous.OUT / "cases.jsonl"
    resolver = evidence.load(previous.PROFILE)["tokenizer"]
    source = ROOT / resolver["path"]
    assert evidence.digest(source) == prior_profile["source_tokenizer_sha256"] == resolver["sha256"]
    assert evidence.digest(asset) == prior_profile["compact_sha256"]
    assert evidence.digest(cases) == prior_profile["cases_sha256"]
    OUT.mkdir(exist_ok=False)
    sidecar = OUT / "sparse.index"
    geometry = create_index(evidence.load(source), sidecar)
    reference_files = [previous.OUT / f"reference_{i}.json" for i in range(3)]
    profile = dict(tag=TAG, table_sha256=evidence.digest(asset), index_sha256=evidence.digest(sidecar),
        frozen_cases_sha256=evidence.digest(cases), references={p.name:evidence.digest(p) for p in reference_files},
        code_sha256=evidence.digest(Path(__file__)), structures=geometry, index_bytes=sidecar.stat().st_size)
    evidence.write(OUT / "profile.json", profile)
    results = []
    for i, scope in enumerate(("battery", "battery", "vocab")):
        output = OUT / f"mapped_{i}.json"
        subprocess.run([sys.executable, "-I", "-S", "-B", "-X", "utf8", str(Path(__file__)), "worker", str(asset),
            str(sidecar), str(cases), scope, str(output)], cwd=ROOT, timeout=55, check=True)
        results.append(evidence.load(output))
    old, new = evidence.load(reference_files[0])["records"], results[0]["records"]
    mismatch = [left["case"] for left, right in zip(old, new, strict=True) if left != right]
    assert old == evidence.load(reference_files[1])["records"] and new == results[1]["records"]
    vocab_ok = evidence.load(reference_files[2])["sha256"] == results[2]["vocabulary"]["sha256"]
    assert profile["references"] == {p.name:evidence.digest(p) for p in reference_files}
    assert profile["index_sha256"] == evidence.digest(sidecar) and profile["table_sha256"] == evidence.digest(asset)
    assert profile["code_sha256"] == evidence.digest(Path(__file__))
    peak = max(row["peak"] for row in results[:2])
    evidence.write(OUT / "report.json", dict(cases=len(old), mismatches=mismatch, vocab_equal=vocab_ok, peak=peak,
        vocabulary_peak=results[2]["peak"], reference_reused=True, source_sha256=evidence.digest(source),
        profile_sha256=evidence.digest(OUT / "profile.json")))
    print("SPARSE_GEMMA", len(old), len(mismatch), vocab_ok, peak, flush=True)
    return 0 if not mismatch and vocab_ok and peak <= 40_000_000 else 8


if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] == "worker":
        worker(*sys.argv[2:])
    else:
        sys.exit(main())
