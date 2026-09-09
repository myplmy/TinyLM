"""A01: 버전 고정 held-out 로더. schema 통과는 의미 정답성의 증명이 아니다."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .audit_io import read_records, sha256_file, write_json_new, write_jsonl_new

VERSIONS = {"2.7": (300, "stage1_heldout_benchmark_v2.7_300.json"),
            "2.8": (4500, "stage1_heldout_benchmark_v2.8.json")}


def normalize_version(version):
    version = str(version).removeprefix("v")
    if version not in VERSIONS:
        raise ValueError(f"미등록 held-out 버전 {version!r}; 자동 최신 선택은 하지 않음")
    return version


def adapt_heldout(row):
    if all(k in row for k in ("ctx", "choices", "gold")):
        ctx, choices, gold = row["ctx"], row["choices"], row["gold"]
    elif all(k in row for k in ("prompt", "candidates", "correct_index")):
        ctx, choices, gold = row["prompt"], row["candidates"], row["correct_index"]
    else:
        raise ValueError("held-out schema: ctx/choices/gold 또는 prompt/candidates/correct_index 필요")
    if not isinstance(ctx, str) or not ctx.strip():
        raise ValueError("빈/비문자열 context")
    if not isinstance(choices, list) or len(choices) != 4:
        raise ValueError("4개의 선택지 필요")
    if any(not isinstance(c, str) or not c.strip() for c in choices):
        raise ValueError("빈/비문자열 선택지")
    if len({re.sub(r"\s+", " ", c).strip() for c in choices}) != 4:
        raise ValueError("문자열 정규화 후 중복 선택지")
    if isinstance(gold, bool) or not isinstance(gold, int) or not 0 <= gold < 4:
        raise ValueError("gold는 0..3의 정수여야 함")
    result = dict(row)
    result.update(ctx=ctx, choices=choices, gold=gold)
    return result


def source_path(root, version):
    version = normalize_version(version)
    return (Path(root) / "datasets" / "TinyDataset" / "stage1_dataset"
            / f"held-out_v{version}" / VERSIONS[version][1])


def cache_path(root, version):
    version = normalize_version(version)
    return Path(root) / "datasets" / "bench" / f"stage1_heldout.v{version}.jsonl"


def validate_rows(rows, version):
    expected = VERSIONS[normalize_version(version)][0]
    if len(rows) != expected:
        raise ValueError(f"v{version}: 예상 {expected}건, 실제 {len(rows)}건")
    out, seen = [], set()
    for row in rows:
        r = adapt_heldout(row)
        ident = r.get("id")
        if ident is None or not str(ident).strip():
            raise ValueError("held-out의 고유 id가 없음")
        ident = str(ident)
        if ident in seen:
            raise ValueError(f"중복 id: {ident}")
        seen.add(ident)
        r["id"] = ident
        out.append(r)
    return out


def export_cache(root, version="2.7", expected_source_sha256=None):
    version = normalize_version(version)
    source = source_path(root, version)
    source_sha = sha256_file(source)
    if expected_source_sha256 and source_sha != expected_source_sha256.lower():
        raise ValueError("요청한 source SHA-256과 실제 파일이 다름")
    rows = validate_rows(read_records(source), version)
    if version == "2.7":
        # v2.7용 기존 의미 검사를 유지한다. 새 schema에 이 검사를 적용하지 않는다.
        import sys
        sys.path.insert(0, str(Path(root) / "scripts"))
        from check_heldout_defects import scan, d6_two_answers
        legacy = read_records(source)
        scanned = scan(source.parent)
        if scanned[0] is None:
            raise ValueError("v2.7 기존 D1 검사에서 읽은 문항이 없음")
        d1 = scanned[0]
        d6 = d6_two_answers(legacy)
        if d1 or d6:
            raise ValueError(f"v2.7 기존 검사 실패: D1={len(d1)}, D6={len(d6)}")
        semantic_status = "legacy_v27_D1_D6_checked"
    else:
        semantic_status = "documented_audit_with_warnings_not_independent_semantic_proof"
    dest = cache_path(root, version)
    meta_path = dest.with_suffix(".meta.json")
    if dest.exists() or meta_path.exists():
        cached, meta = load_cache(root, version, expected_source_sha256=source_sha)
        return dest, len(cached), meta
    for r in rows:
        r["_heldout_version"] = version
        r["_source_sha256"] = source_sha
    write_jsonl_new(dest, rows)
    meta = {"schema": "tinylm.heldout-cache.v1", "version": version,
            "source": str(source.resolve()), "source_sha256": source_sha,
            "cache_sha256": sha256_file(dest), "count": len(rows),
            "semantic_status": semantic_status}
    write_json_new(meta_path, meta)
    return dest, len(rows), meta


def load_cache(root, version="2.7", expected_source_sha256=None):
    version = normalize_version(version)
    path = cache_path(root, version)
    meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    if meta.get("schema") != "tinylm.heldout-cache.v1" or meta.get("version") != version:
        raise ValueError("held-out cache metadata/schema/version 불일치")
    if sha256_file(path) != meta.get("cache_sha256"):
        raise ValueError("held-out cache hash 불일치")
    source_sha = sha256_file(source_path(root, version))
    if source_sha != meta.get("source_sha256"):
        raise ValueError("held-out 원본이 cache 생성 이후 변경됨")
    if expected_source_sha256 and source_sha != expected_source_sha256.lower():
        raise ValueError("명시한 held-out source hash 불일치")
    rows = validate_rows(read_records(path), version)
    if meta.get("count") != len(rows):
        raise ValueError("held-out cache count 불일치")
    if any(r.get("_heldout_version") != version or r.get("_source_sha256") != source_sha
           for r in rows):
        raise ValueError("held-out row provenance 불일치")
    return rows, meta
