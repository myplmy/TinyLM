"""Pinned public metadata for P101A's immutable local M0 parent; no model load."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEM = "m100s12_ko-en_1200M_d16_cla2_norecur_rms4_t1200"
PARENT = ROOT / "runs" / "ckpt" / f"{STEM}.pt"
RUN_JSON = ROOT / "runs" / "logs" / f"{STEM}.json"
TOKENIZER = ROOT / "data_cache" / "tok-ko-en-32768.json"
CACHE = ROOT / "data_cache" / "ko-en_1200000000"
EXPECTED = {
    PARENT: "00B107DA3DD9076C5A652F947F0E3AE4885B6AFC4C79C20042916211C432FB3D",
    TOKENIZER: "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3",
    CACHE / "meta.json": "62871E90D121D4FC0712B2FB074F3C5B671F55972BF1B3D24B3E43356CD3B366",
}


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or linked P101A asset: {path}")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            sha.update(block)
    return sha.hexdigest().upper()

def validate_m0_cache_meta(meta: dict) -> None:
    """Pure metadata gate: prevent prepare(exact) from backfilling the pinned file."""
    if (meta.get("data") != "ko-en" or meta.get("train") != 1194000000
            or meta.get("val") != 6000000 or meta.get("vocab") != 32768):
        raise ValueError("M0 cache metadata differs")
    bpt = meta.get("bytes_per_token")
    if isinstance(bpt, bool) or not isinstance(bpt, (int, float)) or not math.isfinite(bpt) or bpt <= 0:
        raise ValueError("M0 cache bytes_per_token missing/invalid; prepare would backfill pinned metadata")
    if meta.get("token_dtype", "uint16") != "uint16":
        raise ValueError("M0 cache dtype differs from pinned uint16")



def verify_m0_assets() -> dict:
    """Fail closed on parent/tokenizer/cache identity; do not read model tensors."""
    if CACHE.is_symlink():
        raise ValueError("M0 cache directory is linked")
    for path, expected in EXPECTED.items():
        actual = _digest(path)
        if actual != expected:
            raise ValueError(f"P101A pinned asset SHA differs: {path.name}: {actual}")
    if RUN_JSON.is_symlink() or not RUN_JSON.is_file():
        raise ValueError("M0 run JSON is missing or linked")
    run = json.loads(RUN_JSON.read_text(encoding="utf-8"))
    meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    required = {"arch": "dense", "preset": "m100s12", "data": "ko-en",
                "tag": STEM, "steps": 9156, "pool_tokens": 1200000000,
                "exact_cache": True, "optimizer": "muon", "muon_scale": "rms"}
    if any(run.get(key) != value for key, value in required.items()):
        raise ValueError("M0 run metadata differs from the approved parent contract")
    validate_m0_cache_meta(meta)
    train_file, val_file = CACHE / "train.bin", CACHE / "val.bin"
    if any(path.is_symlink() or not path.is_file() for path in (train_file, val_file)):
        raise ValueError("M0 train/val cache files are missing or linked")
    if (train_file.stat().st_size != 2 * meta["train"]
            or val_file.stat().st_size != 2 * meta["val"]):
        raise ValueError("M0 uint16 cache byte lengths differ")
    return run
