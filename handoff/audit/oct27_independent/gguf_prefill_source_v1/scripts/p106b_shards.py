#!/usr/bin/env python3
"""Write-once JSONL shards below 20,000,000 bytes with lossless hash manifest.

The writer is for a new ignored HF corpus version. It never mutates prior
teacher records or prepares files for Git staging; export/publication needs a
separate provenance, rights and privacy decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

MAX_BYTES = 20_000_000


class ShardWriter:
    def __init__(self, directory: Path, stem: str, *, limit: int = MAX_BYTES):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError("shard directory absent/not a real directory")
        if not stem.isascii() or not stem.replace("_", "").isalnum():
            raise ValueError("shard stem must be safe ASCII")
        if not 64 <= limit <= MAX_BYTES:
            raise ValueError("shard byte limit invalid")
        directory.mkdir(parents=True, exist_ok=True)
        self.directory, self.stem, self.limit = directory, stem, limit
        self.manifest_path = directory / f"{stem}_shards_manifest.json"
        if self.manifest_path.exists() or self.manifest_path.is_symlink():
            raise FileExistsError("shard manifest already exists")
        self.shards: list[dict] = []
        self._file = None
        self._bytes = self._rows = 0
        self._sha = hashlib.sha256()
        self._concat = hashlib.sha256()
        self._total_rows = self._total_bytes = 0

    def _open(self) -> None:
        path = self.directory / f"{self.stem}_{len(self.shards):06d}.jsonl"
        self._file = path.open("xb")
        self._bytes = self._rows = 0
        self._sha = hashlib.sha256()

    def _finish(self) -> None:
        if self._file is None:
            return
        path = Path(self._file.name)
        self._file.flush()
        self._file.close()
        self.shards.append({"path": path.name, "bytes": self._bytes,
                            "rows": self._rows, "sha256": self._sha.hexdigest().upper()})
        self._file = None

    def append(self, row: dict) -> None:
        if not isinstance(row, dict):
            raise ValueError("JSONL row must be a dict")
        line = (json.dumps(row, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n").encode("utf-8")
        if len(line) > self.limit:
            raise ValueError("one record exceeds shard size; do not split a UTF-8 line")
        if self._file is None:
            self._open()
        if self._bytes + len(line) > self.limit:
            self._finish()
            self._open()
        assert self._file is not None
        self._file.write(line)
        self._sha.update(line)
        self._concat.update(line)
        self._bytes += len(line)
        self._rows += 1
        self._total_bytes += len(line)
        self._total_rows += 1

    def close(self, *, lineage: dict) -> dict:
        self._finish()
        if not self.shards:
            raise ValueError("empty sharded corpus is forbidden")
        manifest = {"schema": "P106B_WRITE_ONCE_SHARDS_V1",
                    "limit_bytes": self.limit, "rows": self._total_rows,
                    "bytes": self._total_bytes, "concat_sha256": self._concat.hexdigest().upper(),
                    "lineage": lineage, "shards": self.shards}
        with self.manifest_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        return manifest


def verify(directory: Path, manifest: dict) -> None:
    if directory.is_symlink() or manifest.get("schema") != "P106B_WRITE_ONCE_SHARDS_V1":
        raise ValueError("invalid shard directory or manifest schema")
    limit = manifest.get("limit_bytes")
    if not isinstance(limit, int) or limit > MAX_BYTES:
        raise ValueError("shard size contract differs")
    whole = hashlib.sha256()
    total_bytes = total_rows = 0
    for index, spec in enumerate(manifest.get("shards", [])):
        name = spec.get("path", "")
        if (not isinstance(name, str) or Path(name).name != name
                or not name.endswith(f"_{index:06d}.jsonl")):
            raise ValueError("shard sequence/name differs")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError("shard absent or linked")
        data = path.read_bytes()
        rows = data.count(b"\n")
        if (not data.endswith(b"\n") or len(data) > limit
                or len(data) != spec.get("bytes") or rows != spec.get("rows")
                or hashlib.sha256(data).hexdigest().upper() != spec.get("sha256")):
            raise ValueError("shard byte/line/hash contract differs")
        whole.update(data)
        total_bytes += len(data)
        total_rows += rows
    if (total_rows != manifest.get("rows") or total_bytes != manifest.get("bytes")
            or whole.hexdigest().upper() != manifest.get("concat_sha256")):
        raise ValueError("lossless reconstructed corpus hash differs")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="p106b_shards_") as temporary:
        directory = Path(temporary) / "versioned"
        writer = ShardWriter(directory, "canonical", limit=128)
        for index in range(9):
            writer.append({"id": index, "text": "한국어-english" + str(index)})
        manifest = writer.close(lineage={"source_sha256": "A" * 64})
        assert manifest["rows"] == 9 and len(manifest["shards"]) > 1
        verify(directory, manifest)
        assert all(shard["bytes"] <= 128 for shard in manifest["shards"])
        assert all(path.read_bytes().endswith(b"\n") for path in directory.glob("*.jsonl"))
    print("[PASS] write-once UTF-8 row-aligned shards, each <=20MB, exact reassembly SHA; model/GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("library only; use --self-test or a scoped producer")
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
