"""Audit the exact planned P109B crop stream using the historical text signals."""

import hashlib
import json
from collections import Counter
from pathlib import Path
import time

import numpy as np
from tokenizers import Tokenizer

from handoff.audit.oct26_research.audit_actual_exposure import file_sha, segment_ranges, target_span, window_signals


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data_cache/20261120_정제데이터셋1차"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
OUT = ROOT / "test_result/evidence/p109_firstpass_exposure_300m_v1_20261120"
LOADER = ROOT / "tinylm/data/loader.py"
SCANNER = ROOT / "handoff/audit/oct26_research/audit_actual_exposure.py"
STEPS, ACCUM, MICRO, SEQ = 2289, 16, 8, 1024
SEED, EOS = 1234, 2
CHUNK = 256


def crop_offsets(tokens):
    rng = np.random.default_rng(SEED)
    return np.concatenate([rng.integers(0, tokens - SEQ - 1, MICRO) for _ in range(STEPS * ACCUM)])


def audit(tokens, tokenizer, offsets, deadline):
    totals = Counter()
    windows = Counter()
    headings = Counter()
    target_digest = hashlib.sha256()
    for begin in range(0, len(offsets), CHUNK):
        if time.monotonic() >= deadline:
            raise TimeoutError("planned exposure audit budget exceeded")
        batch = offsets[begin:begin + CHUNK]
        arrays = [tokens[slice(*target_span(int(offset), len(tokens), SEQ))] for offset in batch]
        counts = [Counter() for _ in batch]
        parts = []
        owners = []
        for index, ids in enumerate(arrays):
            target_digest.update(ids.tobytes())
            eos_positions = np.flatnonzero(ids == EOS).tolist()
            totals["eos_target_tokens"] += len(eos_positions)
            for start, end, left, right in segment_ranges(len(ids), eos_positions):
                parts.append(ids[start:end].tolist())
                owners.append((index, left, right))
        decoded = tokenizer.decode_batch(parts, skip_special_tokens=False)
        for text, (index, left, right) in zip(decoded, owners, strict=True):
            result, titles, _ = window_signals(text, left_complete=left, right_complete=right)
            counts[index].update(result)
            headings.update(titles)
        for count in counts:
            totals.update(count)
            windows.update(key for key, value in count.items() if value > 0)
    return {"signal_totals": dict(totals), "windows_with_signal": dict(windows), "title_counts": dict(headings),
            "target_bytes_sha256": target_digest.hexdigest()}


def main():
    if OUT.exists() or OUT.is_symlink():
        raise FileExistsError(OUT)
    started = time.monotonic()
    meta_path = PILOT / "meta.json"
    train = PILOT / "train.bin"
    if any(path.is_symlink() for path in (PILOT, meta_path, train, TOKENIZER)):
        raise ValueError("expected the original verified pilot paths")
    meta = json.loads(meta_path.read_bytes())
    train_sha = file_sha(train).lower()
    tokenizer_sha = file_sha(TOKENIZER).lower()
    if (meta["status"] != "CPU_VERIFIED_PARTIAL_PILOT" or meta["tokenizer_lineage"] != "chat32"
            or train_sha != meta["split_receipts"]["train"]["sha256"]
            or train.stat().st_size != 2 * meta["train"]
            or tokenizer_sha != meta["tokenizer_sha256"].lower()):
        raise ValueError("the verified pilot or tokenizer changed")
    tokens = np.memmap(train, mode="r", dtype="<u2")
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    if tokenizer.token_to_id("<eos>") != EOS or tokenizer.get_vocab_size() != meta["vocab"]:
        raise ValueError("tokenizer EOS or vocabulary changed")
    offsets = crop_offsets(len(tokens))
    counts = audit(tokens, tokenizer, offsets, started + 900)
    result = {
        "status": "FULL_PLANNED_CROP_AUDIT", "actual_training": False,
        "crop_windows": len(offsets), "target_tokens": len(offsets) * SEQ,
        "steps": STEPS, "micro_bs": MICRO, "accum": ACCUM, "sequence": SEQ,
        "loader_seed": SEED, "offset_bytes_sha256": hashlib.sha256(offsets.astype("<i8").tobytes()).hexdigest(),
        "pool_tokens": len(tokens), "pilot_train_sha256": train_sha, "tokenizer_sha256": tokenizer_sha,
        "loader_sha256": file_sha(LOADER).lower(), "signal_reference_sha256": file_sha(SCANNER).lower(),
        "seconds": time.monotonic() - started, **counts,
    }
    OUT.mkdir(exist_ok=False)
    with (OUT / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps({key: result[key] for key in ("status", "crop_windows", "target_tokens", "windows_with_signal", "seconds")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
