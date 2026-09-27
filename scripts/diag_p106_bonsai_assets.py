#!/usr/bin/env python3
"""P106 G0a/G0b metadata-only Bonsai 2 GGUF/Prism runtime preflight.

No model weights are loaded or generated. The exact model SHA is checked against
the published PTQ1_0 blob; public license/card links are evidence, not a claim
about redistribution or teacher-answer quality. CUDA execution is a separate gate.
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
CUDA_DIR = Path("/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe")
CPU_DIR = CUDA_DIR  # one verified fork binary; --gpu-layers 0 selects CPU-only execution
MODEL_SHA256 = "53107F530AA52EB00912263AB1EE29BD199261C87CD7B4AD4CA1318C1FE33EE3"
MODEL_BLOB_URL = (
    "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/"
    "blob/main/Ternary-Bonsai-2-27B-PTQ1_0.gguf"
)
LICENSE_URL = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/LICENSE"
NOTICE_URL = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/NOTICE.txt"
CARD_URL = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/README.md"


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


def version_text(stdout: str, stderr: str, expected_commit: str) -> str:
    lines = [line.strip() for line in (stdout + "\n" + stderr).splitlines()]
    version_lines = [line for line in lines if line.startswith(("version:", "built with "))]
    if not version_lines or expected_commit not in " ".join(version_lines):
        raise ValueError(f"Prism runtime version does not match pinned fork {expected_commit}")
    return " | ".join(version_lines[:2])


def runtime_version(path: Path, expected_commit: str) -> str:
    if not regular(path) or not os.access(path, os.X_OK):
        raise ValueError(f"Prism CLI missing, linked or not executable: {path}")
    with path.open("rb") as stream:
        if stream.read(4) != bytes((0x7F, 0x45, 0x4C, 0x46)):
            raise ValueError(f"Prism CLI is not ELF: {path}")
    completed = subprocess.run([str(path), "--version"], capture_output=True,
                               text=True, timeout=10, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Prism CLI --version exit={completed.returncode}: {path}")
    return version_text(completed.stdout, completed.stderr, expected_commit)


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
    assert version_text("", "version: 0.2.0-dev (build 10735, commit 842b18804)", "842b188").startswith("version:")
    assert version_text("", "version: 0.2.0-dev (build 10743, commit adfffbe41)", "adfffbe").startswith("version:")
    assert version_text("", "ggml_cuda_init: sandbox denied\nversion: 0.2.0-dev (build 10743, commit adfffbe41)", "adfffbe").startswith("version:")
    try:
        version_text("version: 0.2.0-dev (build 10735, commit 842b18804)", "", "adfffbe")
    except ValueError:
        pass
    else:
        raise AssertionError("old CUDA runtime accepted as new release")
    print("[PASS] P106 GGUF v3/negative header and stderr-version contract; teacher/model NOT_RUN")


def audit() -> int:
    if MODEL_DIR.is_symlink() or not regular(MODEL):
        raise ValueError("exact local PTQ1_0 GGUF absent or linked")
    size = MODEL.stat().st_size
    if size < 5_000_000_000:
        raise ValueError(f"PTQ1_0 file is unexpectedly small: {size} bytes")
    with MODEL.open("rb") as stream:
        version = gguf_version(stream.read(8))
    cpu_version = runtime_version(CPU_DIR / "llama-cli", "adfffbe")
    cuda_version = runtime_version(CUDA_DIR / "llama-cli", "adfffbe")
    cuda_plugins = sorted(path.name for path in CUDA_DIR.glob("libggml-cuda.so*")
                          if regular(path))
    licenses = sorted(path.name for path in MODEL_DIR.glob("LICENSE*") if regular(path))
    notices = sorted(path.name for path in MODEL_DIR.glob("NOTICE*") if regular(path))
    cards = sorted(path.name for path in MODEL_DIR.glob("README*") if regular(path))
    reasons = []
    if not cuda_plugins:
        reasons.append("selected CUDA package has no libggml-cuda.so plugin")
    pinned_sha = sha256_file(MODEL)
    if pinned_sha != MODEL_SHA256:
        raise ValueError("local PTQ1_0 SHA-256 differs from the published model blob")
    result = {
        "schema": "P106_G0A_BONSAI_ASSET_V1",
        "model": MODEL.relative_to(ROOT).as_posix(), "model_bytes": size,
        "gguf_version": version, "model_sha256": pinned_sha,
        "cpu_runtime_version": cpu_version, "cuda_runtime_version": cuda_version,
        "cuda_runtime_dir": str(CUDA_DIR),
        "cuda_plugins": cuda_plugins, "license_files": licenses,
        "notice_files": notices, "model_cards": cards,
        "official_model_blob_sha256": MODEL_SHA256,
        "official_model_blob_url": MODEL_BLOB_URL,
        "official_license_url": LICENSE_URL, "official_notice_url": NOTICE_URL,
        "official_model_card_url": CARD_URL,
        "license_rights_review": "PUBLIC_APACHE2_SOURCE_IDENTIFIED_LOCAL_TEST_ONLY",
        "redistribution_review": "NOT_RUN",
        "prompt_template_review": "NOT_RUN",
        "teacher_generation": "NOT_RUN", "reasons": reasons,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if reasons:
        print("[GATE HOLD] asset metadata alone cannot authorize teacher inference or training")
        return 8
    print("[ASSET PASS] published blob SHA, new Prism CLI and CUDA plugin present; actual CUDA/model behavior NOT_RUN")
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
