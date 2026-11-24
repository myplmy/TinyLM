#!/usr/bin/env python3
"""Locate and restore byte-pinned research evidence from local archives."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PurePosixPath("test_result/evidence/_archive")
CATALOG_GLOB = "*_압축보관_목록.json"
SCHEMA = "TINYLM_RAW_EVAL_ARCHIVE_V1"
EVIDENCE_PREFIXES = ("test_result/", "handoff/audit/", "review_request/")
BLOCK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ArchivedFile:
    path: str
    size: int
    sha256: str
    bundle: str
    bundle_size: int
    bundle_sha256: str
    catalog: str


def _relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value or path == PurePosixPath(".") or path.is_absolute()
        or ".." in path.parts or path.as_posix() != value
        or any(char in value for char in ("\\", ":", "\0", "\r", "\n"))
    ):
        raise ValueError(f"보관 목록의 상대 경로가 잘못됐습니다. {value!r}")
    return path


def _size(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("보관 목록에 잘못된 바이트 크기가 있습니다.")
    return value


def _digest(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", value):
        raise ValueError("보관 목록에 잘못된 SHA-256이 있습니다.")
    return value.lower()


def load_index(root: Path) -> dict[str, list[ArchivedFile]]:
    index = defaultdict(list)
    for catalog in sorted((root / "test_result").glob(CATALOG_GLOB)):
        try:
            if catalog.is_symlink():
                raise ValueError("심볼릭 링크인 목록은 사용할 수 없습니다.")
            data = json.loads(catalog.read_text(encoding="utf-8"))
            if data["schema"] != SCHEMA or len(data["archives"]) != data["archive_count"]:
                raise ValueError("보관 목록의 형식 또는 묶음 수가 다릅니다.")
            seen = set()
            for entry in data["archives"]:
                bundle = _relative_path(entry["archive"]).relative_to(ARCHIVE_DIR)
                if len(bundle.parts) != 2 or not bundle.name.endswith(".tar.gz"):
                    raise ValueError("보관 묶음 경로가 올바르지 않습니다.")
                size = _size(entry["archive_bytes"])
                sha = _digest(entry["archive_sha256"])
                if len(entry["files"]) != entry["file_count"]:
                    raise ValueError("보관 묶음의 파일 수가 다릅니다.")
                for item in entry["files"]:
                    path = _relative_path(item["path"]).as_posix()
                    if path in seen or not path.startswith(EVIDENCE_PREFIXES):
                        raise ValueError(f"중복되거나 범위를 벗어난 원본 경로입니다. {path}")
                    seen.add(path)
                    index[path].append(ArchivedFile(
                        path, _size(item["size"]), _digest(item["sha256"]),
                        bundle.as_posix(), size, sha, catalog.relative_to(root).as_posix(),
                    ))
            if len(seen) != data["file_count"]:
                raise ValueError("보관 목록 전체 파일 수가 다릅니다.")
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{catalog.name} — {error}") from error
    return dict(index)


def lookup(index: dict[str, list[ArchivedFile]], query: str, sha256: str | None) -> ArchivedFile:
    path = _relative_path(query).as_posix()
    entries = index.get(path)
    if not entries and "/" not in path:
        matches = [name for name in index if PurePosixPath(name).name == path]
        if len(matches) > 1:
            choices = "\n".join(matches[:12])
            raise ValueError(f"같은 파일명이 {len(matches)}개 있습니다. 저장소 상대 경로를 지정하세요.\n{choices}")
        if matches:
            entries = index[matches[0]]
    if sha256:
        entries = [entry for entry in entries or [] if entry.sha256 == _digest(sha256)]
    if not entries:
        raise ValueError(f"보관 목록에서 찾을 수 없습니다. {query}")
    if len({entry.sha256 for entry in entries}) != 1:
        raise ValueError(f"여러 보관 버전이 있습니다. SHA-256을 지정하세요. {query}")
    return entries[-1]


def _local_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = root / _relative_path(relative)
    if candidate.resolve() != candidate or candidate.is_symlink():
        raise ValueError(f"심볼릭 링크를 포함한 경로입니다. {candidate}")
    return candidate


def _archive_roots(root: Path, specified: Path | None) -> list[Path]:
    if specified is not None:
        return [specified]
    roots = [root / ARCHIVE_DIR]
    backup = os.environ.get("TINYLM_EVIDENCE_ARCHIVE_ROOT")
    if not backup:
        configured = subprocess.run(
            ["git", "config", "--local", "--get", "tinylm.evidenceArchiveRoot"],
            cwd=root, capture_output=True, text=True, check=False,
        )
        if configured.returncode == 0:
            backup = configured.stdout.strip()
    if backup:
        roots.append(Path(backup))
    return roots


def _read_member(entry: ArchivedFile, roots: list[Path], output) -> tuple[Path, int, float]:
    errors = []
    for root in roots:
        try:
            path = _local_path(root, entry.bundle)
            with path.open("rb") as packed:
                if (
                    os.fstat(packed.fileno()).st_size != entry.bundle_size
                    or hashlib.file_digest(packed, "sha256").hexdigest() != entry.bundle_sha256
                ):
                    raise ValueError(f"압축 묶음 해시가 다릅니다. {path}")
                packed.seek(0)
                with tarfile.open(fileobj=packed, mode="r|gz") as archive:
                    for member in archive:
                        if member.name == entry.path:
                            if not member.isfile() or member.size != entry.size:
                                raise ValueError(f"보관 파일의 유형 또는 크기가 다릅니다. {entry.path}")
                            digest = hashlib.sha256()
                            output.seek(0)
                            output.truncate()
                            with archive.extractfile(member) as data:
                                while block := data.read(BLOCK_SIZE):
                                    digest.update(block)
                                    output.write(block)
                            if output.tell() != entry.size or digest.hexdigest() != entry.sha256:
                                raise ValueError(f"보관 파일의 내용이 다릅니다. {entry.path}")
                            output.seek(0)
                            return path, member.mode & 0o777, member.mtime
                raise ValueError(f"압축 묶음 안에 원본 경로가 없습니다. {entry.path}")
        except (OSError, tarfile.TarError, ValueError) as error:
            errors.append(str(error))
    raise ValueError("검증 가능한 압축 묶음을 찾지 못했습니다.\n" + "\n".join(errors))


def _restore(entry: ArchivedFile, source, destination: Path, mode: int, mtime: float) -> tuple[Path, str]:
    target = _local_path(destination, entry.path)
    if target.exists():
        if target.is_file() and target.stat().st_size == entry.size:
            with target.open("rb") as current:
                if hashlib.file_digest(current, "sha256").hexdigest() == entry.sha256:
                    return target, "already_present"
        raise FileExistsError(f"기존 내용이 다른 경로입니다. 빈 복원 위치를 지정하세요. {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".restore-", delete=False) as output:
        temp = Path(output.name)
        try:
            shutil.copyfileobj(source, output, BLOCK_SIZE)
            output.flush()
            os.fchmod(output.fileno(), mode)
            os.utime(temp, (mtime, mtime))
            os.fsync(output.fileno())
            os.link(temp, _local_path(destination, entry.path))
        finally:
            temp.unlink()
    return target, "restored"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="원시 평가와 검증 근거의 보관 위치를 찾거나 복원합니다.")
    parser.add_argument("action", choices=("locate", "verify", "restore"))
    parser.add_argument("path", help="원래 저장소 상대 경로 또는 고유한 파일명")
    parser.add_argument("--sha256", help="같은 경로의 여러 버전 중 하나를 선택합니다.")
    parser.add_argument("--archive-root", type=Path, help="지정한 별도 보관 위치만 사용합니다.")
    parser.add_argument("--destination", type=Path, default=ROOT, help="복원의 기준 디렉터리")
    args = parser.parse_args(argv)
    try:
        entry = lookup(load_index(ROOT), args.path, args.sha256)
        roots = _archive_roots(ROOT, args.archive_root)
        result = {"path": entry.path, "size": entry.size, "sha256": entry.sha256, "catalog": entry.catalog}
        if args.action == "locate":
            result["archives"] = [
                {"path": str(path), "present": path.is_file()}
                for path in (_local_path(root, entry.bundle) for root in roots)
            ]
        else:
            with tempfile.TemporaryFile() as source:
                path, mode, mtime = _read_member(entry, roots, source)
                result["archive"] = str(path)
                result["status"] = "verified"
                if args.action == "restore":
                    target, status = _restore(entry, source, args.destination, mode, mtime)
                    result.update(restored_path=str(target), status=status)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f"[E] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
