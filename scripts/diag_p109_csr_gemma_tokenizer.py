"""Check range-indexed compact Gemma BPE merges on the frozen tokenizer panel."""

from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from struct import Struct
import subprocess
import sys
import sysconfig
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.append(str(ROOT))
    sys.path.append(sysconfig.get_path("purelib"))

from scripts import diag_p109_compact_qwen_tokenizer as evidence
from scripts import diag_p109_sparse_gemma_tokenizer as sparse
from scripts.p109_compact_qwen_tokenizer import HEADER, MAGIC, MERGE, OFFSET


TAG = "p109_csr_gemma_tokenizer_v3_20261119"
OUT = sparse.OUT.with_name(TAG)
CSR_MAGIC = b"TLGMCSR1"
CSR_HEADER = Struct("<8s2I")
ROW = Struct("<Q")
BOUNDS = Struct("<II")
BITS = 19
MASK = (1 << BITS) - 1


def build(asset, destination):
    with sparse.map_file(asset) as data:
        magic, ids, ordinary, count, _scaffold, _pieces = HEADER.unpack_from(data)
        assert magic == MAGIC and ids == 262145 and ordinary == 262144 and count <= 1 << BITS
        merge_start = HEADER.size + (ids + 1) * OFFSET.size
        offset, entries = bytearray(), bytearray()
        previous_left, previous_pair = -1, -1
        for index in range(count):
            key, rank, merged = MERGE.unpack_from(data, merge_start + index * MERGE.size)
            left, right = key >> 32, key & ((1 << 32) - 1)
            assert previous_pair < key and left < ordinary and right < ordinary and merged < ordinary
            assert rank < count
            for _ in range(previous_left, left):
                offset.extend(OFFSET.pack(index))
            entries.extend(ROW.pack((right << (2 * BITS)) | (rank << BITS) | merged))
            previous_left, previous_pair = left, key
        for _ in range(previous_left, ids):
            offset.extend(OFFSET.pack(count))
    assert len(offset) == (ids+1)*OFFSET.size and len(entries) == count*ROW.size
    with destination.open("xb") as stream:
        stream.write(CSR_HEADER.pack(CSR_MAGIC, ids, count))
        stream.write(offset)
        stream.write(entries)


class CsrGemma(sparse.SparseGemma):
    def __init__(self, asset, sidecar, merges):
        super().__init__(asset, sidecar)
        try:
            self.merges = sparse.map_file(merges)
            try:
                magic, ids, rule_count = CSR_HEADER.unpack_from(self.merges)
                self.rows_at = CSR_HEADER.size + (ids + 1) * OFFSET.size
                assert magic == CSR_MAGIC and ids == self.size and rule_count == self.rule_count
                assert self.rows_at + rule_count * ROW.size == len(self.merges)
            except Exception:
                self.merges.close()
                raise
        except Exception:
            super().__exit__()
            raise

    def __exit__(self, *_exc):
        self.merges.close()
        super().__exit__()

    def _merge(self, left, right):
        low, high = BOUNDS.unpack_from(self.merges, CSR_HEADER.size + left * OFFSET.size)
        while low < high:
            middle = (low + high) // 2
            value = ROW.unpack_from(self.merges, self.rows_at + middle * ROW.size)[0]
            token = value >> (2 * BITS)
            if token == right:
                return (value >> BITS) & MASK, value & MASK
            if token < right:
                low = middle + 1
            else:
                high = middle
        return None


def worker(asset, sidecar, table, cases, scope, output):
    start = evidence.snapshot()
    opened = perf_counter()
    with CsrGemma(asset, sidecar, table) as codec:
        load_seconds = perf_counter()-opened
        loaded = evidence.snapshot()
        checks = []
        codec_seconds = 0.
        if scope == "vocab":
            check = evidence.vocab_check(codec, codec.size)
            assert codec.id_to_token(262144) == "<image_soft_token>"
        else:
            check = None
            with Path(cases).open(encoding="utf-8") as stream:
                for line in stream:
                    name, text = json.loads(line)
                    begun = perf_counter()
                    enc = codec.encode(text)
                    fields = dict(ids=enc.ids, offsets=enc.offsets, words=enc.word_ids,
                        kept=codec.decode(enc.ids, skip_special_tokens=False), stripped=codec.decode(enc.ids))
                    codec_seconds += perf_counter()-begun
                    raw = json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    checks.append(dict(case=name, tokens=len(enc.ids), sha256=sha256(raw).hexdigest().upper()))
        finished = evidence.snapshot()
    peak = max(v for row in (start, loaded, finished) for v in row.values())
    evidence.write(output, dict(records=checks, vocabulary=check, peak=peak, load_seconds=load_seconds,
        codec_seconds=codec_seconds, history=dict(initial=start, loaded=loaded, complete=finished)))
    print("CSR_GEMMA_WORKER",scope,peak,len(checks),flush=True)


def main():
    cutoff = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=240) < cutoff
    v1, v2 = sparse.previous.OUT, sparse.OUT
    original, prior = (evidence.load(d / "profile.json") for d in (v1, v2))
    asset, side, cases = v1 / "gemma.qbpe", v2 / "sparse.index", v1 / "cases.jsonl"
    assert original["compact_sha256"] == prior["table_sha256"] == evidence.digest(asset)
    assert original["cases_sha256"] == prior["frozen_cases_sha256"] == evidence.digest(cases)
    assert evidence.digest(side) == prior["index_sha256"]
    OUT.mkdir(exist_ok=False)
    table = OUT / "merges.csr"
    build(asset, table)
    inputs = [v1 / f"reference_{i}.json" for i in range(3)] + [asset, side, cases, Path(sparse.__file__), Path(__file__)]
    pins = {str(p.relative_to(ROOT)):evidence.digest(p) for p in inputs}
    table_sha = evidence.digest(table)
    evidence.write(OUT / "profile.json",dict(tag=TAG,pins=pins,table_sha256=table_sha,
        table_bytes=table.stat().st_size,index_bits=BITS,prior_scope="FROZEN_1414_CASES"))
    reports = []
    for index, scope in enumerate(("battery", "battery", "vocab")):
        output = OUT / f"mapped_{index}.json"
        subprocess.run([sys.executable,"-I","-S","-B","-X","utf8",str(Path(__file__)),"worker",str(asset),
                        str(side),str(table),str(cases),scope,str(output)],cwd=ROOT,timeout=50,check=True)
        reports.append(evidence.load(output))
    reference = evidence.load(inputs[0])["records"]
    assert reference == evidence.load(inputs[1])["records"] and reports[0]["records"] == reports[1]["records"]
    mismatches = [a["case"] for a,b in zip(reference,reports[0]["records"],strict=True) if a!=b]
    vocabulary_ok = evidence.load(inputs[2])["sha256"] == reports[2]["vocabulary"]["sha256"]
    peak = max(r["peak"] for r in reports[:2])
    assert table_sha == evidence.digest(table) and pins == {str(p.relative_to(ROOT)):evidence.digest(p) for p in inputs}
    evidence.write(OUT / "report.json",dict(peak=peak,cases=len(reference),mismatches=mismatches,
        vocab_equal=vocabulary_ok,vocab_peak=reports[2]["peak"],reused_reference=True,
        source_sha256=original["source_tokenizer_sha256"],profile_sha256=evidence.digest(OUT / "profile.json")))
    print("CSR_GEMMA",len(reference),len(mismatches),vocabulary_ok,peak,table.stat().st_size,flush=True)
    return 0 if not mismatches and vocabulary_ok and peak <= 40_000_000 else 8


if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] == "worker":
        worker(*sys.argv[2:])
    else:
        sys.exit(main())
