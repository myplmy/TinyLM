#!/usr/bin/env python3
"""Compare two held-out census artifacts on one model panel without loading models.

The comparison is paired by item ID. A different dataset version is the intended
independent variable; model tags, checkpoints and evaluation settings must otherwise
match. Legacy JSON may be used only with an explicit opt-in and is reported as a
metadata gap, never silently promoted to a full condition-signature match.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import census_heldout_discrimination as census


class ComparisonError(ValueError):
    """Raised when two artifacts cannot support a paired version comparison."""


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"JSON을 읽을 수 없다: {path} ({exc})") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"JSON 최상위가 객체가 아니다: {path}")
    return value


def _validated_vectors(doc: dict, label: str) -> tuple[list, list[str], list[float], dict]:
    ids = doc.get("ids")
    models = doc.get("models")
    per_ok = doc.get("per_ok")
    if not isinstance(ids, list) or not ids:
        raise ComparisonError(f"{label}: ids가 없거나 비었다")
    if any(not isinstance(item_id, str) or not item_id for item_id in ids):
        raise ComparisonError(f"{label}: ids가 비어 있거나 문자열이 아니다")
    if len(set(ids)) != len(ids):
        raise ComparisonError(f"{label}: ids가 중복이다")
    if not isinstance(models, list) or len(models) < 2 or len(set(models)) != len(models):
        raise ComparisonError(f"{label}: models가 없거나 중복이다")
    if not isinstance(per_ok, dict) or set(per_ok) != set(models):
        raise ComparisonError(f"{label}: per_ok 키가 models와 다르다")
    n = len(ids)
    if doc.get("n") != n:
        raise ComparisonError(f"{label}: n={doc.get('n')!r}이 ids 길이 {n}과 다르다")
    if doc.get("n_ckpt") != len(models):
        raise ComparisonError(
            f"{label}: n_ckpt={doc.get('n_ckpt')!r}이 models 길이 {len(models)}와 다르다"
        )
    normalized = {}
    for model in models:
        values = per_ok.get(model)
        if not isinstance(values, list) or len(values) != n:
            raise ComparisonError(f"{label}: {model} per_ok 길이가 ids와 다르다")
        if any(value not in (True, False, 0, 1) for value in values):
            raise ComparisonError(f"{label}: {model} per_ok에 bool이 아닌 값이 있다")
        normalized[model] = [bool(value) for value in values]
    rates = [sum(normalized[model][i] for model in models) / len(models) for i in range(n)]
    recorded = doc.get("per_item_rate")
    if recorded is not None:
        if not isinstance(recorded, list) or len(recorded) != n:
            raise ComparisonError(f"{label}: per_item_rate 길이가 ids와 다르다")
        if any(not math.isclose(float(a), b, abs_tol=1e-12)
               for a, b in zip(recorded, rates)):
            raise ComparisonError(f"{label}: per_item_rate가 per_ok 재계산과 다르다")
    return ids, models, rates, normalized


def _summary(rates: list[float]) -> dict:
    n = len(rates)
    b1 = sum(rate == 1.0 for rate in rates)
    b2 = sum(rate == 0.0 for rate in rates)
    b3 = sum(census.BAND[0] <= rate <= census.BAND[1] for rate in rates)
    bits = sum(census.h2(rate) for rate in rates)
    return {
        "n": n,
        "b1_saturated": b1,
        "b2_floor": b2,
        "working_items": n - b1 - b2,
        "b3_band": b3,
        "d9": b3 / n,
        "zero_info": b1 + b2,
        "zero_info_rate": (b1 + b2) / n,
        "bits_total": bits,
        "bits_mean": bits / n,
    }


def _source_hashes(signature: dict) -> dict:
    return signature.get("code_revision") or {}


def _model_identities(signature: dict) -> list[dict]:
    identities = []
    for model in signature.get("models") or []:
        identities.append({
            key: model.get(key)
            for key in ("tag", "preset", "checkpoint", "checkpoint_size_bytes")
        })
    return identities


def _strict_signature_mismatches(baseline: dict, candidate: dict) -> list[str]:
    base_sig = baseline["condition_signature"]
    cand_sig = candidate["condition_signature"]
    checks = {
        "dataset.task": (
            base_sig.get("dataset", {}).get("task"),
            cand_sig.get("dataset", {}).get("task"),
        ),
        "dataset.ids_sha256": (
            base_sig.get("dataset", {}).get("ids_sha256"),
            cand_sig.get("dataset", {}).get("ids_sha256"),
        ),
    }
    for field in ("actual_n", "source_rows", "seed", "covers_all_rows"):
        checks[f"sample.{field}"] = (
            base_sig.get("sample", {}).get(field),
            cand_sig.get("sample", {}).get(field),
        )
    for field in ("data", "tokens", "seq_max", "pmi", "device"):
        checks[f"evaluation.{field}"] = (
            base_sig.get("evaluation", {}).get(field),
            cand_sig.get("evaluation", {}).get(field),
        )
    checks["models"] = (_model_identities(base_sig), _model_identities(cand_sig))
    checks["evaluation_source_hashes"] = (
        _source_hashes(base_sig), _source_hashes(cand_sig),
    )
    return [f"{name}: {left!r} != {right!r}"
            for name, (left, right) in checks.items() if left != right]


def _project_by_baseline_label(
    baseline_ids: list,
    baseline_rates: list[float],
    candidate_rates: list[float],
    labels: list,
    field: str,
) -> dict:
    if not isinstance(labels, list) or len(labels) != len(baseline_ids):
        return {"status": "NOT_AVAILABLE", "reason": "baseline item_labels missing or misaligned"}
    groups = defaultdict(list)
    for index, label in enumerate(labels):
        if not isinstance(label, dict) or label.get("id") != baseline_ids[index]:
            return {"status": "NOT_AVAILABLE", "reason": "baseline item_labels ID mismatch"}
        groups[str(label.get(field) or "(없음)")].append(index)
    output = {}
    for name, indices in sorted(groups.items()):
        base = _summary([baseline_rates[index] for index in indices])
        cand = _summary([candidate_rates[index] for index in indices])
        output[name] = {
            "n": len(indices),
            "baseline": base,
            "candidate": cand,
            "delta": {
                "d9": cand["d9"] - base["d9"],
                "zero_info_rate": cand["zero_info_rate"] - base["zero_info_rate"],
                "bits_total": cand["bits_total"] - base["bits_total"],
            },
        }
    return {
        "status": "AVAILABLE_BASELINE_LABEL_PROJECTION",
        "warning": f"candidate rows are grouped by the baseline version's {field} label",
        "groups": output,
    }


def compare_documents(baseline: dict, candidate: dict, *, allow_legacy: bool = False) -> dict:
    base_ids, base_models, base_rates, base_ok = _validated_vectors(baseline, "baseline")
    cand_ids, cand_models, cand_rates_raw, cand_ok_raw = _validated_vectors(candidate, "candidate")
    if base_models != cand_models:
        raise ComparisonError("모델 패널 또는 순서가 다르다")
    if baseline.get("task") != candidate.get("task"):
        raise ComparisonError(
            f"task가 다르다: {baseline.get('task')!r} != {candidate.get('task')!r}"
        )
    if baseline.get("heldout_version") == candidate.get("heldout_version"):
        raise ComparisonError("서로 다른 held-out 판본이 아니다")
    if set(base_ids) != set(cand_ids):
        missing = len(set(base_ids) - set(cand_ids))
        added = len(set(cand_ids) - set(base_ids))
        raise ComparisonError(f"문항 ID 집합이 다르다: baseline_only={missing}, candidate_only={added}")

    candidate_index = {item_id: index for index, item_id in enumerate(cand_ids)}
    order = [candidate_index[item_id] for item_id in base_ids]
    cand_rates = [cand_rates_raw[index] for index in order]
    cand_ok = {
        model: [cand_ok_raw[model][index] for index in order]
        for model in cand_models
    }

    base_sig = baseline.get("condition_signature")
    cand_sig = candidate.get("condition_signature")
    if base_sig is not None and cand_sig is not None:
        mismatches = _strict_signature_mismatches(baseline, candidate)
        if mismatches:
            raise ComparisonError("조건 서명이 다르다: " + "; ".join(mismatches))
        comparison_status = "FULL_SIGNATURE_MATCH"
        metadata_gaps = []
    else:
        metadata_gaps = []
        if base_sig is None:
            metadata_gaps.append("baseline.condition_signature")
        if cand_sig is None:
            metadata_gaps.append("candidate.condition_signature")
        if not allow_legacy:
            raise ComparisonError(
                "레거시 JSON에 조건 서명이 없다. 원 실행 근거를 확인한 뒤에만 "
                "--allow-legacy-metadata-gap을 명시한다: " + ", ".join(metadata_gaps)
            )
        comparison_status = "CORE_MATCH_LEGACY_METADATA_GAP"
        metadata_gaps.extend([
            "legacy evaluation data/tokens/seq_max/pmi/device not artifact-verified",
            "legacy sample seed/source_rows not artifact-verified",
            "legacy model preset/checkpoint identity not artifact-verified",
            "legacy evaluation source hashes not artifact-verified",
            "legacy dataset content hash not artifact-verified",
        ])

    base_summary = _summary(base_rates)
    cand_summary = _summary(cand_rates)
    deltas = {
        "d9": cand_summary["d9"] - base_summary["d9"],
        "zero_info_rate": cand_summary["zero_info_rate"] - base_summary["zero_info_rate"],
        "bits_total": cand_summary["bits_total"] - base_summary["bits_total"],
        "bits_relative": (
            cand_summary["bits_total"] / base_summary["bits_total"] - 1.0
            if base_summary["bits_total"] else None
        ),
    }
    nonregression = {
        "d9_not_lower": cand_summary["d9"] >= base_summary["d9"],
        "zero_info_not_higher": cand_summary["zero_info"] <= base_summary["zero_info"],
        "bits_not_lower": cand_summary["bits_total"] >= base_summary["bits_total"],
    }
    worse = {
        "d9_lower": cand_summary["d9"] < base_summary["d9"],
        "zero_info_higher": cand_summary["zero_info"] > base_summary["zero_info"],
        "bits_lower": cand_summary["bits_total"] < base_summary["bits_total"],
    }
    if all(nonregression.values()):
        directional = "NO_CORE_REGRESSION"
    elif all(worse.values()):
        directional = "CORE_REGRESSION"
    else:
        directional = "MIXED_CORE_DIRECTIONS"

    transitions = []
    for index, item_id in enumerate(base_ids):
        base_rate, cand_rate = base_rates[index], cand_rates[index]
        transitions.append({
            "id": item_id,
            "baseline_correct_models": round(base_rate * len(base_models)),
            "candidate_correct_models": round(cand_rate * len(base_models)),
            "baseline_rate": base_rate,
            "candidate_rate": cand_rate,
            "rate_delta": cand_rate - base_rate,
            "baseline_bits": census.h2(base_rate),
            "candidate_bits": census.h2(cand_rate),
            "baseline_in_d9": census.BAND[0] <= base_rate <= census.BAND[1],
            "candidate_in_d9": census.BAND[0] <= cand_rate <= census.BAND[1],
        })

    model_accuracy = {}
    for model in base_models:
        base_acc = sum(base_ok[model]) / len(base_ids)
        cand_acc = sum(cand_ok[model]) / len(base_ids)
        model_accuracy[model] = {
            "baseline": base_acc,
            "candidate": cand_acc,
            "delta": cand_acc - base_acc,
        }

    base_labels = baseline.get("item_labels")
    return {
        "schema_version": 1,
        "comparison_status": comparison_status,
        "metadata_gaps": metadata_gaps,
        "baseline_version": baseline.get("heldout_version"),
        "candidate_version": candidate.get("heldout_version"),
        "dataset_identity": {
            "baseline_ids_sha256": (
                (base_sig or {}).get("dataset", {}).get("ids_sha256")
            ),
            "candidate_ids_sha256": (
                (cand_sig or {}).get("dataset", {}).get("ids_sha256")
            ),
            "baseline_content_sha256": (
                (base_sig or {}).get("dataset", {}).get("content_sha256")
            ),
            "candidate_content_sha256": (
                (cand_sig or {}).get("dataset", {}).get("content_sha256")
            ),
        },
        "models": base_models,
        "ids_equal_as_set": True,
        "ids_equal_in_order": base_ids == cand_ids,
        "baseline": base_summary,
        "candidate": cand_summary,
        "delta_candidate_minus_baseline": deltas,
        "directional_nonregression": nonregression,
        "directional_verdict": directional,
        "policy_verdict": "NOT_SET_G0_DIAGNOSTIC_ONLY",
        "model_accuracy": model_accuracy,
        "baseline_label_projection": {
            "relation": _project_by_baseline_label(
                base_ids, base_rates, cand_rates, base_labels, "relation"
            ),
            "difficulty": _project_by_baseline_label(
                base_ids, base_rates, cand_rates, base_labels, "difficulty"
            ),
            "relation_subtype": _project_by_baseline_label(
                base_ids, base_rates, cand_rates, base_labels, "relation_subtype"
            ),
            "family_id": _project_by_baseline_label(
                base_ids, base_rates, cand_rates, base_labels, "family_id"
            ),
        },
        "per_item_transition": transitions,
    }


def _pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="held-out census 동일 패널 판본 비교 (GPU 0)")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--allow-legacy-metadata-gap", action="store_true",
        help="조건 서명이 없는 과거 JSON을 핵심 지표 한정으로 비교(명시적 1회성 호환)",
    )
    args = parser.parse_args(argv)
    try:
        baseline_path = Path(args.baseline)
        candidate_path = Path(args.candidate)
        report = compare_documents(
            _load(baseline_path), _load(candidate_path),
            allow_legacy=args.allow_legacy_metadata_gap,
        )
        report["inputs"] = {
            "baseline": str(baseline_path),
            "candidate": str(candidate_path),
        }
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=1)
            stream.write("\n")
    except (ComparisonError, FileExistsError, OSError) as exc:
        print(f"[compare_heldout_census] ERROR: {exc}", file=sys.stderr)
        return 2

    delta = report["delta_candidate_minus_baseline"]
    print("=" * 96)
    print("  held-out census 동일 패널 판본 비교 — GPU 0")
    print("=" * 96)
    print(f"  상태: {report['comparison_status']}")
    print(f"  baseline v{report['baseline_version']} -> candidate v{report['candidate_version']}")
    print(f"  모델 {len(report['models'])}개 · 문항 {report['baseline']['n']}개")
    print(f"  D9: {_pct(report['baseline']['d9'])} -> {_pct(report['candidate']['d9'])} "
          f"({delta['d9'] * 100:+.2f}pp)")
    print(f"  정보 0: {_pct(report['baseline']['zero_info_rate'])} -> "
          f"{_pct(report['candidate']['zero_info_rate'])} "
          f"({delta['zero_info_rate'] * 100:+.2f}pp)")
    print(f"  정보 합: {report['baseline']['bits_total']:.1f} -> "
          f"{report['candidate']['bits_total']:.1f} bit ({delta['bits_total']:+.1f})")
    print(f"  방향 판정: {report['directional_verdict']}")
    print("  정책 승격 판정: NOT_SET — G0 원인분리 진단이며 결과를 본 뒤 임계값을 만들지 않는다")
    if report["metadata_gaps"]:
        print("  경고: 레거시 JSON 조건 메타데이터 공백 = " + ", ".join(report["metadata_gaps"]))
    print(f"  저장: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
