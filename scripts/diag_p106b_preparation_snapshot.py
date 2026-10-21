#!/usr/bin/env python3
"""Small immutable metadata and bounded human-readable QA; no raw corpus/weights."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SOURCES = (
    "data_cache/ko-en_1200000000/meta.json",
    "data_cache/ko-en_601000000_chat32/meta.json",
    "data_cache/p106b_native_expansion_v1_s1337/meta.json",
    "data_cache/p106b_native_cleanup_v1_s1337/report.json",
    "HF/sft_ready/p101a_sft_mtp_cleanbilingual_v3_s1337/corpus/report.json",
    "HF/sft_ready/p101a_sft_mtp_verified_direct_v3_s1337/corpus/report.json",
    "HF/sft_ready/p101a_sft_mtp_verified_trace_v3_s1337/corpus/report.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/manifest.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/job_manifest.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/batch_000001/manifest.json",
    "HF/sft_ready/p106b_luna_augmentation_v1_s1337/batch_000001/revision_manifest.json",
    "HF/sft_ready/p106b_supported_production8h_v1_s1337_pilot/batch_000000/report.json",
    "HF/sft_ready/p106b_supported_production8h_v2_s1337_pilot/batch_000000/report.json",
    "HF/sft_ready/p106b_supported_production8h_v3_s1337_pilot/batch_000000/report.json",
    "data_cache/p078_router_holdout_v2_s1337/report.json",
    "data_cache/p078_router_holdout_v2_s1337/activity.json",
    "data_cache/p078_router_holdout_bootstrap_v3_s1337/report.json",
    "data_cache/p078_router_holdout_bootstrap_v3_s1337/activity.json",
)


def supported_review():
    from scripts.diag_p106b_supported_production8h import PILOT, VERSION, require_pilot
    path = PILOT / "batch_000000/report.json"
    if not path.is_file(): return None
    report = json.loads(path.read_text(encoding="utf-8"))
    require_pilot(report["input"])
    target = ROOT / "review_request/20261021_Gemma_근거문맥4개_검수요청.md"
    if target.exists():
        return dict(path=str(target.relative_to(ROOT)), reused_existing=True,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest().upper())
    lines = ["# Gemma 근거문맥 4개 실제 생성자료 — 원문 검수 요청", "",
        "검수 대상은 학생이 실제로 볼 질문(참고자료 포함)과 교사가 쓴 학습 답입니다.",
        "4개 기술 저장·마스크 통과는 내용 정답성이나 자연스러운 한국어의 승인과 다릅니다.",
        "생성 사고는 학습 답에 포함되지 않으며, 아래에는 최종 질문·답만 표시합니다.",
        f"생산 계약: {VERSION}. 사람 의미 검수: 미완료. 학생 학습: 미실행.", ""]
    for part in report["candidate_manifest"]["shards"]:
        for raw in (path.parent / part["path"]).read_text(encoding="utf-8").splitlines():
            row = json.loads(raw); meta = row["meta"]
            lines.extend([f"## {meta['source_id']}", "",
                f"언어: {meta['language']} / 과제: {meta['task_profile']} / 원천: {meta['source_family']}",
                "", "### 학생 질문과 공개 참고자료", ""])
            for message in row["messages"]:
                if message["role"] == "assistant": lines.extend(["### 교사 학습 답", ""])
                body = message["content"]
                lines.extend([body if isinstance(body, str) else "".join(b["text"] for b in body), ""])
            lines.extend(["검수 메모: 답의 대상·주어진 근거와의 일치·표현의 자연스러움을 확인해 주세요.",
                          "자동 형식 통과를 사실성 합격으로 해석하지 않습니다.", ""])
    body = "\n".join(lines)
    if len(body.encode()) >= 20_000_000: raise ValueError("bounded review exceeds20MB")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream: stream.write(body)
    return dict(path=str(target.relative_to(ROOT)), reused_existing=False,
                sha256=hashlib.sha256(body.encode()).hexdigest().upper())


def collect():
    from scripts.p106b_source_cleanup import safe
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = safe(ROOT / "test_result/evidence" / ("p106b_oct21_preparation_" + stamp))
    destination.mkdir(parents=True, exist_ok=False)
    entries = []
    for index, relative in enumerate(SOURCES):
        path = safe(ROOT / relative)
        if not path.is_file():
            entries.append(dict(source=relative, status="ABSENT_AT_SNAPSHOT_NOT_A_FAILURE")); continue
        before = path.stat(); raw = path.read_bytes()
        if len(raw) >= 2_000_000: raise ValueError("small metadata only; no raw/weight copying")
        json.loads(raw.decode("utf-8"))
        if (before.st_size, before.st_mtime_ns) != (path.stat().st_size, path.stat().st_mtime_ns):
            raise ValueError("metadata changed during read")
        name = f"{index:02d}_metadata.json"
        with (destination / name).open("xb") as stream: stream.write(raw)
        entries.append(dict(source=relative, snapshot=name, bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest().upper(), status="COPIED_METADATA_ONLY"))
    report = dict(schema="P106B_PREPARATION_METADATA_SNAPSHOT_V1", created_at=stamp,
        entries=entries, models_loaded=0, gpu_calls=0, raw_dataset_copied=False,
        readable_supported_qa=supported_review(),
        semantic_quality="NOT_ESTABLISHED_BY_METADATA_SNAPSHOT",
        original_writes=0, snapshot_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper())
    body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    with (destination / "report.json").open("x", encoding="utf-8") as stream: stream.write(body)
    print(json.dumps(dict(snapshot=str(destination.relative_to(ROOT)),
        copied=sum(e["status"] == "COPIED_METADATA_ONLY" for e in entries),
        absent=[e["source"] for e in entries if e["status"] != "COPIED_METADATA_ONLY"],
        models_loaded=0, original_writes=0), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true"); group.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps(dict(source_count=len(SOURCES), source_reads=0, model_loading=False)))
    else: collect()


if __name__ == "__main__": main()
