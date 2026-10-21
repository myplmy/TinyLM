#!/usr/bin/env python3
"""동일 조건의 기존 비용 측정만 읽기 검산한다. 모델·GPU·쓰기 없음.

0=검산된 측정 재사용, 8=측정 없음(런처가 최초 측정), 9=기존 증거 불일치.
학습 자체의 원래 same-code/corpus 검사도 그대로 유지한다.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))


def validate(cost, metadata, corpus_sha, arm, updates):
    excluded = {"model_loading", "meaningful_training", "max_wall_sec"}
    for key, expected in metadata.items():
        if key not in excluded and cost.get(key) != expected:
            raise ValueError("기존 비용 측정의 조건 불일치: " + key)
    if (cost.get("status") != "COST_CALIBRATION_COMPLETE"
            or cost.get("arm") != arm or cost.get("corpus_sha256") != corpus_sha
            or cost.get("updates") != 32 or cost.get("expected_full_updates") != updates
            or cost.get("checkpoint_saved") is not False):
        raise ValueError("완결된 동일 팔 32업데이트 비용 영수증이 아니다")
    seconds = cost.get("update_seconds")
    if (not isinstance(seconds, list) or len(seconds) != 32
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in seconds)):
        raise ValueError("32회의 실제 업데이트 시간 증거가 필요하다")
    for key in ("whole_wall_sec", "actual_processed_x_tokens", "assistant_targets"):
        value = cost.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("비용 측정 분모 누락: " + key)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("mtp", "direct", "trace"), required=True)
    parser.add_argument("--arm", choices=("scratch_ntp", "scratch_mtp", "parent_ntp", "parent_mtp"), required=True)
    parser.add_argument("--check-only", action="store_true", required=True)
    args = parser.parse_args()
    if args.family != "mtp" and args.arm != "parent_ntp": parser.error("추론 대조는 parent_ntp만 사용한다")
    from scripts import diag_p101a_clean_bilingual as clean
    from scripts import diag_p101a_sft_mtp as engine
    args.tag = clean.TAGS[args.family]; args.max_wall_sec = 1200
    corpus, evidence = engine.paths(args.tag)
    target = engine.report_path(evidence, args.arm, True)
    if not target.exists():
        print("[COST_MISSING] 최초 비용 측정 필요: " + str(target.relative_to(ROOT)))
        return 8
    if target.is_symlink() or target.stat().st_size >= 20_000_000:
        raise ValueError("연결되거나 20MB 이상인 증거는 재사용하지 않는다")
    report = engine.corpus_report(corpus)
    if (report.get("preparation_schema") != clean.VERSION
            or report.get("code_sha256", {}).get("scripts/diag_p101a_clean_bilingual.py") != clean.digest(clean.__file__)):
        raise ValueError("현재 준비 코드와 자료의 서명이 다르다")
    cost = json.loads(target.read_text(encoding="utf-8"))
    validate(cost, clean.info(args, report), clean.digest(corpus / "report.json"), args.arm, report["learning_updates"])
    print("[COST_REUSED_READ_ONLY] " + json.dumps(dict(family=args.family, arm=args.arm,
        report=str(target.relative_to(ROOT)), sha256=clean.digest(target), updates=32,
        model_loads=0, gpu_calls=0, writes=0, quality_claim="NOT_RUN"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print("[COST_INVALID] " + type(exc).__name__ + ": " + str(exc), flush=True)
        raise SystemExit(9)
