"""Compare a decode-only ByteLevel table with the existing ChatML decoder."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
from itertools import chain, islice, product
import json
import mmap
import os
from pathlib import Path
from random import Random
import runpy
import struct
import subprocess
import sys
from time import perf_counter


TAG = "p077_g4_output_byte_table_cpu_v1_20261121"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test_result/evidence" / TAG
MAGIC = b"TLMOUT1\0"
HEADER = struct.Struct("<8sI")
OFFSET = struct.Struct("<I")
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")


def byte_to_char():
    direct = set(chain(range(33, 127), range(161, 173), range(174, 256)))
    table = {}
    extra = 256
    for byte in range(256):
        if byte in direct:
            table[byte] = chr(byte)
        else:
            table[byte] = chr(extra)
            extra += 1
    return table


def pack(vocabulary, special):
    if sorted(vocabulary.values()) != list(range(len(vocabulary))):
        raise ValueError("requires a dense token ID space")
    reverse = {char: byte for byte, char in byte_to_char().items()}
    pieces = bytearray()
    offsets = bytearray(OFFSET.pack(0))
    for text, token_id in sorted(vocabulary.items(), key=lambda item: item[1]):
        if token_id not in special:
            pieces.extend(reverse[char] for char in text)
        offsets.extend(OFFSET.pack(len(pieces)))
    return b"".join((HEADER.pack(MAGIC, len(vocabulary)), offsets, pieces))


class OutputTable:
    def __init__(self, raw):
        magic, size = HEADER.unpack_from(raw)
        self.raw = raw
        self.size = size
        self.start = HEADER.size + (size + 1) * OFFSET.size
        if magic != MAGIC or self.start > len(raw) or self._offset(size) != len(raw):
            raise ValueError("invalid output table")

    def _offset(self, token_id):
        return self.start + OFFSET.unpack_from(self.raw, HEADER.size + token_id * OFFSET.size)[0]

    def decode(self, ids):
        pieces = []
        for token_id in ids:
            if not 0 <= token_id < self.size:
                raise ValueError(f"token ID out of range: {token_id}")
            start, end = self._offset(token_id), self._offset(token_id + 1)
            if not self.start <= start <= end <= len(self.raw):
                raise ValueError("invalid token byte range")
            pieces.append(self.raw[start:end])
        return b"".join(pieces).decode("utf-8", errors="replace")


def verify(tok, raw, traces):
    candidate = OutputTable(raw)
    byte_tokens = [tok.token_to_id(char) for char in byte_to_char().values()]
    if None in byte_tokens or len(set(byte_tokens)) != 256:
        raise ValueError("the tokenizer must contain one ID for each raw byte")
    rng = Random(229935)
    cases = iter(chain(
        ((i,) for i in range(candidate.size)),
        product(byte_tokens, repeat=2),
        ([rng.randrange(candidate.size) for _ in range(128)] for _ in range(2048)),
        traces,
    ))
    count = 0
    while batch := list(islice(cases, 512)):
        truth = tok.decode_batch([list(ids) for ids in batch], skip_special_tokens=True)
        for ids, expected in zip(batch, truth, strict=True):
            actual = candidate.decode(ids)
            if actual != expected:
                raise ValueError(f"decoder mismatch for {ids!r}: {actual!r} vs {expected!r}")
        count += len(batch)
    return count


def decode_worker(mode, wrapper, vocab, merges, table):
    wire = runpy.run_path(wrapper)
    snapshot = wire["snapshot"]
    start = perf_counter()
    points = dict(startup=snapshot())
    ids = json.load(sys.stdin)
    if mode == "existing":
        tok, _, _ = wire["tokenizer"](vocab, merges)
        points["loaded"] = snapshot()
        text = tok.decode(ids, skip_special_tokens=True)
    elif mode == "output":
        with mmap.mmap(table, 0, access=mmap.ACCESS_READ) as raw:
            decoder = OutputTable(raw)
            points["loaded"] = snapshot()
            text = decoder.decode(ids)
            points["processed"] = snapshot()
    else:
        raise ValueError("unknown decoder arm")
    points["complete"] = snapshot()
    print(json.dumps(dict(text=text, points=points, wall_seconds=perf_counter()-start,
                          peak_bytes=max(value for point in points.values() for value in point.values())),
                     ensure_ascii=False))


def run(stop_by):
    from tokenizers import Tokenizer
    from scripts import diag_p077_grounded_near_native as native

    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or stop_by.tzinfo is None or stop_by > AUTHORIZATION_END
            or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds() < 120 or OUT.exists()):
        raise ValueError("requires a new CPU output and an adequate authorized window")
    previous = native.ROPE_OUT
    report = native.trial.read_json(previous / "report.json")
    old = [native.trial.read_json(previous / f"text_{i}_tile_rope_2048.json") for i in range(len(report["full"]))]
    book = native.trial.read_json(native.trial.DATA / "report.json")
    tokenizer_path = native.trial.on_disk(book["tokenizer"])
    source = tokenizer_path.read_bytes()
    model = json.loads(source)
    tok = Tokenizer.from_buffer(source)
    traces = [row["native"]["ids"] for row in old]
    traces.extend(item["ids"] for pair in report["quality"] for item in pair["arms"]["tile_rope_2048"])
    table = pack(model["model"]["vocab"], {row["id"] for row in model["added_tokens"]})
    OUT.mkdir()
    wrapper, blobs = native.text_codec(OUT)
    count = verify(tok, table, traces)
    print(json.dumps(dict(phase="equivalence", sequences=count, artifact_bytes=len(table))), flush=True)
    (OUT / "output_table.bin").write_bytes(table)
    rows = []
    allowed_cpus = set(native.wide.choices.CPU_CORES)&os.sched_getaffinity(0)
    if not allowed_cpus:
        raise ValueError("no CPU available for the decoder order comparison")
    cpu = min(allowed_cpus)
    os.sched_setaffinity(0, {cpu})
    with ExitStack() as stack:
        fds = []
        for i, blob in enumerate((*blobs, table)):
            fd = native.base.memfile(f"p077-output-table-{i}")
            stack.callback(os.close, fd)
            native.bounded.text.store(fd, blob)
            fds.append(fd)
        for i, request in enumerate(old):
            if (OUT / "STOP").exists() or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds() < 40:
                raise TimeoutError("decoder measurement ended at the authorized boundary")
            arms = {}
            order = ("existing", "output") if i%2 == 0 else ("output", "existing")
            for mode in order:
                child = subprocess.run(
                    [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(Path(__file__).resolve()),
                     "worker", mode, str(wrapper), *map(str, fds)],
                    input=json.dumps(request["native"]["ids"]).encode(), capture_output=True,
                    pass_fds=fds, timeout=25, check=True,
                )
                row = json.loads(child.stdout)
                if row["text"] != request["decoding"]["text"]:
                    raise ValueError("the decoder differs from the archived actual response")
                arms[mode] = row
            rows.append(dict(request=i, order=order, ids=request["native"]["ids"], arms=arms))
    data = dict(tag=TAG, tokenizer_sha256=sha256(source).hexdigest(),
                source_sha256=native.trial.file_sha(Path(__file__)),
                reference_sha256=native.trial.file_sha(previous / "report.json"),
                cpu=cpu, sequences=count, packed_bytes=len(table), old_wire_bytes=sum(map(len, blobs)),
                packed_sha256=sha256(table).hexdigest(), requests=rows)
    native.trial.publish(OUT / "report.json", data)
    print(json.dumps(dict(phase="complete", requests=len(rows))), flush=True)


def main():
    if sys.argv[1:2] == ["worker"] and len(sys.argv) == 7:
        decode_worker(sys.argv[2], sys.argv[3], *map(int, sys.argv[4:]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    run(args.stop_by)
    return 0


if __name__ == "__main__":
    sys.exit(main())
