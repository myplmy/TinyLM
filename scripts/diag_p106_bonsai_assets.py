#!/usr/bin/env python3
"""P106 G0a user-run metadata-only Bonsai 2 GGUF/Prism runtime preflight.

No model weights are loaded or generated. An exit-8 HOLD is a valid asset result,
not a teacher-quality failure. License text and CUDA behavior need separate review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "HF/models--prism-ml--Ternary-Bonsai-2-27B-gguf"
MODEL = MODEL_DIR / "Ternary-Bonsai-2-27B-PTQ1_0.gguf"
CPU_DIR = Path("/home/uranus/llama-prism-b10735-842b188-bin-ubuntu-x64-cpu/llama-prism-b10735-842b188")
CUDA_DIR = Path("/home/uranus/llama-prism-b10735-842b188-bin-ubuntu-x64-cuda133/llama-prism-b10735-842b188")


def gguf_version(header: bytes) -> int:
    if len(header) != 8 or header[:4] != b"GGUF":
        raise ValueError("model is not an eight-byte GGUF header")
    version = struct.unpack("<I", header[4:])[0]
    if version != 3:
        raise ValueError(f"expected GGUF v3, got v{version}")
    return version


def regular(path: Path) -> bool:
    return not path.is_symlink() and path.is_file()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def version_text(stdout: str, stderr: str) -> str:
    body = stdout.strip() or stderr.strip()
    if "842b188" not in body:
        raise ValueError("Prism runtime version does not match pinned fork 842b188")
    return " | ".join(body.splitlines()[:2])


def runtime_version(path: Path) -> str:
    if not regular(path) or not os.access(path, os.X_OK):
        raise ValueError(f"Prism CLI missing, linked or not executable: {path}")
    with path.open("rb") as stream:
        if stream.read(4) != bytes((0x7F, 0x45, 0x4C, 0x46)):
            raise ValueError(f"Prism CLI is not ELF: {path}")
    completed = subprocess.run([str(path), "--version"], capture_output=True,
                               text=True, timeout=10, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Prism CLI --version exit={completed.returncode}: {path}")
    return version_text(completed.stdout, completed.stderr)


def self_test() -> None:
    assert gguf_version(b"GGUF" + struct.pack("<I", 3)) == 3
    for bad in (b"GGUF", b"NOPE" + struct.pack("<I", 3),
                b"GGUF" + struct.pack("<I", 2)):
        try:
            gguf_version(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid GGUF header accepted")
    assert version_text("", "version: 0.2.0-dev (build 10735, commit 842b18804)").startswith("version:")
    print("[PASS] P106 GGUF v3/negative header and stderr-version contract; teacher/model NOT_RUN")


def audit() -> int:
    if MODEL_DIR.is_symlink() or not regular(MODEL):
        raise ValueError("exact local PTQ1_0 GGUF absent or linked")
    size = MODEL.stat().st_size
    if size < 5_000_000_000:
        raise ValueError(f"PTQ1_0 file is unexpectedly small: {size} bytes")
    with MODEL.open("rb") as stream:
        version = gguf_version(stream.read(8))
    cpu_version = runtime_version(CPU_DIR / "llama-cli")
    cuda_version = runtime_version(CUDA_DIR / "llama-cli")
    cuda_plugins = sorted(path.name for path in CUDA_DIR.glob("libggml-cuda.so*")
                          if regular(path))
    licenses = sorted(path.name for path in MODEL_DIR.glob("LICENSE*") if regular(path))
    notices = sorted(path.name for path in MODEL_DIR.glob("NOTICE*") if regular(path))
    cards = sorted(path.name for path in MODEL_DIR.glob("README*") if regular(path))
    reasons = []
    if not licenses:
        reasons.append("exact revision license text is absent")
    if not cards:
        reasons.append("exact revision model card/template is absent")
    if not cuda_plugins:
        reasons.append("CUDA package has no libggml-cuda.so plugin; GPU capability unverified")
    # Hashing 5.9 GB is deferred while legal/runtime preconditions already HOLD.
    pinned_sha = sha256_file(MODEL) if not reasons else "NOT_RUN_HOLD"
    result = {
        "schema": "P106_G0A_BONSAI_ASSET_V1",
        "model": MODEL.relative_to(ROOT).as_posix(), "model_bytes": size,
        "gguf_version": version, "model_sha256": pinned_sha,
        "cpu_runtime_version": cpu_version, "cuda_runtime_version": cuda_version,
        "cuda_plugins": cuda_plugins, "license_files": licenses,
        "notice_files": notices, "model_cards": cards,
        "license_rights_review": "NOT_RUN", "prompt_template_review": "NOT_RUN",
        "teacher_generation": "NOT_RUN", "reasons": reasons,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if reasons:
        print("[GATE HOLD] asset metadata alone cannot authorize teacher inference or training")
        return 8
    print("[ASSET CANDIDATE] files are present; human license/template and bounded model E2E remain separate")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.check_only:
        print("[CHECK_ONLY] P106 pinned GGUF/CPU/CUDA paths; files, model and runtime NOT_READ")
        return 0
    try:
        return audit()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] P106 asset preflight: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
